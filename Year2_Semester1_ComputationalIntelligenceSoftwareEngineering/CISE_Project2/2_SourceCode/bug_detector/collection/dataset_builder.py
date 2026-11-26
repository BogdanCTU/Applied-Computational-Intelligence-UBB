"""Orchestrates multi-source dataset construction, validation, auditing, and persistence."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from bug_detector.collection.deduplicator import deduplicate_and_validate_records
from bug_detector.collection.github_bugfix_collector import GitHubBugFixCollector
from bug_detector.collection.hard_negative_collector import HardNegativeCollector
from bug_detector.collection.inferredbugs_ingestor import InferredBugsIngestor
from bug_detector.collection.models import DatasetAuditReport, DatasetSampleRecord, ExclusionRecord
from bug_detector.config.settings import AppConfig, load_config
from bug_detector.db import BugDetectorRepository, DatabaseManager
from bug_detector.db.repository import sha256_text
from bug_detector.logging_utils import get_logger
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient

logger = get_logger(__name__)

REQUIRED_METADATA_FIELDS = [
    "sample_id",
    "repository_id",
    "repository_url",
    "commit_sha",
    "parent_commit_sha",
    "file_path",
    "class_name",
    "method_name",
    "method_signature",
    "source_code",
    "label",
    "label_source",
    "verification_status",
    "bug_type",
    "bug_fix_reference",
    "source_hash",
    "collection_timestamp",
    "dataset_version",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DatasetBuilder:
    """Builds, validates, deduplicates, audits, and exports versioned v5 datasets."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.repo = BugDetectorRepository(DatabaseManager(self.config.db_path))

    def build(
        self,
        dataset_version: str | None = None,
        inferredbugs_max: int | None = None,
        github_max_repos: int | None = None,
        hard_negatives_max_repos: int | None = None,
        resume_github: bool = False,
    ) -> DatasetAuditReport:
        dver = dataset_version or self.config.dataset_version
        all_raw_samples: list[DatasetSampleRecord] = []
        all_exclusions: list[ExclusionRecord] = []
        repos_by_id: dict[str, dict[str, Any]] = {}

        with RoslynPreprocessorClient(self.config) as client:
            client.ensure_built()

            # 1. Primary source: Microsoft InferredBugs (C#)
            ib_ingestor = InferredBugsIngestor(self.config)
            ib_samples, ib_excl, ib_repos = ib_ingestor.ingest(
                max_records=inferredbugs_max,
                dataset_version=dver,
                roslyn_client=client,
            )
            all_raw_samples.extend(ib_samples)
            all_exclusions.extend(ib_excl)
            for r in ib_repos:
                repos_by_id[r["repository_id"]] = r

            # 2. Additional source: Verified GitHub bug-fix pairs
            ib_short_names = {r["full_name"].split("/")[-1].lower() for r in repos_by_id.values()}
            gh_collector = GitHubBugFixCollector(self.config)
            gh_samples, gh_excl, gh_repos = gh_collector.collect_from_local_mirrors(
                max_repos=github_max_repos,
                exclude_repo_ids=set(repos_by_id.keys()),
                exclude_short_names=ib_short_names,
                resume=resume_github,
                dataset_version=dver,
                roslyn_client=client,
            )
            all_raw_samples.extend(gh_samples)
            all_exclusions.extend(gh_excl)
            for r in gh_repos:
                repos_by_id[r["repository_id"]] = r

            # 3. Hard negatives: Test-backed verified complex-but-correct methods from disjoint repos
            used_repos = set(repos_by_id.keys())
            used_short_names = {r["full_name"].split("/")[-1].lower() for r in repos_by_id.values()}
            hn_collector = HardNegativeCollector(self.config)
            hn_samples, hn_excl, hn_repos = hn_collector.collect(
                max_repos=hard_negatives_max_repos,
                exclude_repo_ids=used_repos,
                exclude_short_names=used_short_names,
                dataset_version=dver,
                roslyn_client=client,
            )
            all_raw_samples.extend(hn_samples)
            all_exclusions.extend(hn_excl)
            for r in hn_repos:
                repos_by_id[r["repository_id"]] = r

        # 4. Validate and deduplicate
        valid_samples, dedup_excl, dup_stats = deduplicate_and_validate_records(all_raw_samples)
        all_exclusions.extend(dedup_excl)

        # Assign dedicated hard_negative_test partition for disjoint hard-negative evaluation repos
        hn_repo_ids = sorted(
            {s.repository_id for s in valid_samples if s.label_source == "verified_hard_negative"}
        )
        n_hn_test = min(self.config.validation.hard_negative_test_repos, max(1, len(hn_repo_ids) // 2)) if hn_repo_ids else 0
        hn_test_repos = set(hn_repo_ids[:n_hn_test])
        for s in valid_samples:
            if s.repository_id in hn_test_repos:
                s.split_partition = "hard_negative_test"

        # 5. Export Parquet + CSV + Audit Report
        out_dir = self.config.datasets_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / f"csharp_bug_detection_{dver}.parquet"
        csv_path = out_dir / f"csharp_bug_detection_{dver}.csv"
        audit_path = out_dir / f"dataset_audit_report_{dver}.json"

        rows = []
        missing_counts = {f: 0 for f in REQUIRED_METADATA_FIELDS}
        for s in valid_samples:
            row = {
                "sample_id": s.sample_id,
                "repository_id": s.repository_id,
                "repository_url": s.repository_url,
                "commit_sha": s.commit_sha,
                "parent_commit_sha": s.parent_commit_sha,
                "file_path": s.file_path,
                "class_name": s.class_name,
                "method_name": s.method_name,
                "method_signature": s.method_signature,
                "source_code": s.source_code,
                "normalized_source": s.normalized_source,
                "label": s.label,
                "label_source": s.label_source,
                "verification_status": s.verification_status,
                "bug_type": s.bug_type,
                "bug_fix_reference": s.bug_fix_reference,
                "source_hash": s.source_hash,
                "structural_hash": s.structural_hash,
                "pair_id": s.pair_id,
                "commit_timestamp": s.commit_timestamp,
                "collection_timestamp": s.collection_timestamp,
                "dataset_version": s.dataset_version,
                "extraction_mode": s.extraction_mode,
                "split_partition": s.split_partition,
                "features_json": json.dumps(s.features_payload),
            }
            for f in REQUIRED_METADATA_FIELDS:
                if row.get(f) in (None, "") and f not in {"parent_commit_sha", "bug_fix_reference"}:
                    missing_counts[f] += 1
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False)
        dataset_sha256 = sha256_text(csv_path.read_text(encoding="utf-8", errors="replace"))

        bug_count = sum(1 for s in valid_samples if s.label == 1)
        clean_count = sum(1 for s in valid_samples if s.label == 0)
        active_repo_ids = {s.repository_id for s in valid_samples}
        active_repos = [r for rid, r in repos_by_id.items() if rid in active_repo_ids]

        repo_origins = Counter(r.get("source_origin", "unknown") for r in active_repos)
        label_sources = Counter(s.label_source for s in valid_samples)
        bug_types = Counter(s.bug_type for s in valid_samples)
        verif_statuses = Counter(s.verification_status for s in valid_samples)
        excl_stats = Counter(e.exclusion_reason for e in all_exclusions)
        split_parts = Counter(s.split_partition for s in valid_samples)

        audit = DatasetAuditReport(
            dataset_version=dver,
            generated_at=_utc_now(),
            total_records_collected=len(all_raw_samples) + len([e for e in all_exclusions if e.exclusion_reason not in {"cross_label_hash_conflict", "duplicate_source_hash"}]),
            valid_records=len(valid_samples),
            invalid_records=len(all_exclusions),
            bug_count=bug_count,
            clean_count=clean_count,
            bug_ratio=round(bug_count / len(valid_samples), 4) if valid_samples else 0.0,
            repository_count=len(active_repo_ids),
            repositories_by_origin=dict(repo_origins),
            label_source_distribution=dict(label_sources),
            defect_category_distribution=dict(bug_types),
            verification_status_distribution=dict(verif_statuses),
            duplicate_statistics=dup_stats,
            missing_metadata_counts=missing_counts,
            exclusion_statistics=dict(excl_stats),
            split_partition_distribution=dict(split_parts),
            dataset_sha256=dataset_sha256,
        )
        audit_path.write_text(audit.model_dump_json(indent=2) + "\n", encoding="utf-8")

        # 6. Persist atomically to SQLite
        self.repo.replace_dataset_contents(
            dataset_version=dver,
            description="C# method-level bug detection corpus (InferredBugs + GitHub bug-fix pairs + verified hard negatives)",
            repositories=active_repos,
            samples=[s.model_dump() for s in valid_samples],
            exclusions=[e.model_dump() for e in all_exclusions],
            stats={
                "total_records_collected": audit.total_records_collected,
                "valid_records": audit.valid_records,
                "invalid_records": audit.invalid_records,
                "bug_count": audit.bug_count,
                "clean_count": audit.clean_count,
                "repository_count": audit.repository_count,
            },
            dataset_sha256=dataset_sha256,
            parquet_path=str(parquet_path),
            csv_path=str(csv_path),
            audit_report_path=str(audit_path),
        )

        logger.info(
            "Built dataset %s: valid=%d (BUG=%d, CLEAN=%d), repos=%d, exclusions=%d",
            dver,
            audit.valid_records,
            audit.bug_count,
            audit.clean_count,
            audit.repository_count,
            audit.invalid_records,
        )
        return audit
