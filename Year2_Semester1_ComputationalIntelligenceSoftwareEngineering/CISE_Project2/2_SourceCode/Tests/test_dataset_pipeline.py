"""Tests for dataset ingestion, validation, deduplication, provenance, and split integrity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bug_detector.collection.deduplicator import deduplicate_and_validate_records
from bug_detector.collection.github_bugfix_collector import classify_commit_message
from bug_detector.collection.inferredbugs_ingestor import InferredBugsIngestor
from bug_detector.collection.models import DatasetSampleRecord
from bug_detector.config import AppConfig
from bug_detector.ml.splitting import build_repository_splits, verify_zero_leakage
from conftest import make_synthetic_records


def _make_sample(sid: str, repo: str, label: int, source_hash: str, pair_id: str | None = None) -> DatasetSampleRecord:
    return DatasetSampleRecord(
        sample_id=sid,
        repository_id=repo,
        repository_url=f"https://github.com/{repo}",
        commit_sha="abc123",
        parent_commit_sha="def456" if label == 0 else None,
        file_path="src/Service.cs",
        class_name="Service",
        method_name="Handle",
        method_signature="void Handle(string s)",
        source_code="public void Handle(string s) { var n = s.Length; }",
        label=label,  # type: ignore[arg-type]
        label_source="inferredbugs_infersharp" if label == 1 else "inferredbugs_post_fix",
        verification_status="static_analyzer_verified_fix" if label == 1 else "post_fix_verified",
        bug_type="NULL_DEREFERENCE" if label == 1 else "NONE",
        bug_fix_reference="ref:1",
        source_hash=source_hash,
        structural_hash=f"struct_{source_hash}",
        pair_id=pair_id,
        collection_timestamp="2026-11-26T00:00:00Z",
        dataset_version="v5.0.0",
    )


def test_deduplication_rejects_cross_label_conflict_and_same_label_dups() -> None:
    r1 = _make_sample("s1", "org/a", 1, "h_conflict")
    r2 = _make_sample("s2", "org/b", 0, "h_conflict")
    r3 = _make_sample("s3", "org/a", 1, "h_unique")
    r4 = _make_sample("s4", "org/c", 1, "h_unique")
    kept, excl, stats = deduplicate_and_validate_records([r1, r2, r3, r4])
    assert [r.sample_id for r in kept] == ["s3"]
    assert stats["cross_label_hash_conflicts_excluded"] == 2
    assert stats["same_label_duplicates_removed"] == 1
    reasons = {e.exclusion_reason for e in excl}
    assert "cross_label_hash_conflict" in reasons
    assert "duplicate_source_hash" in reasons


def test_commit_message_classifier_rejects_refactoring_docs_and_formatting() -> None:
    assert classify_commit_message("Fix null reference exception in Parser.Read")[0] is True
    assert classify_commit_message("Merge pull request #42 from dev")[0] is False
    assert classify_commit_message("Refactor parser helpers and rename variables")[0] is False
    assert classify_commit_message("Format code with whitespace cleanup")[0] is False
    assert classify_commit_message("Bump Newtonsoft.Json nuget package to 13.0.3")[0] is False
    assert classify_commit_message("Update README docs and comments")[0] is False


def test_inferredbugs_ingestor_validates_and_logs_exclusions(tmp_path: Path, temp_config: AppConfig) -> None:
    ext = tmp_path / "External"
    ib_root = ext / "InferredBugs" / "inferredbugs" / "csharp"
    # Valid bug pair
    b1 = ib_root / "DemoRepo" / "1"
    b1.mkdir(parents=True)
    (b1 / "bug.json").write_text(
        json.dumps(
            {
                "bug_type": "NULL_DEREFERENCE",
                "severity": "ERROR",
                "procedure": "Int32 Demo.GetLen(String)",
                "file": "src/Demo.cs",
                "procedure_start_line": 4,
            }
        ),
        encoding="utf-8",
    )
    (b1 / "commit_info.json").write_text(json.dumps({"hash": "deadbeef1234", "message": "Fix NRE"}), encoding="utf-8")
    before_file = """
    namespace DemoNs {
        public class Demo {
            public int GetLen(string s) {
                var trimmed = s.Trim();
                var upper = trimmed.ToUpper();
                return upper.Length;
            }
        }
    }
    """
    after_file = """
    namespace DemoNs {
        public class Demo {
            public int GetLen(string s) {
                if (s == null) return 0;
                var trimmed = s.Trim();
                var upper = trimmed.ToUpper();
                return upper.Length;
            }
        }
    }
    """
    (b1 / "file_before.txt").write_text(before_file, encoding="utf-8")
    (b1 / "file_after.txt").write_text(after_file, encoding="utf-8")
    (b1 / "method_before.txt").write_text(before_file, encoding="utf-8")
    (b1 / "method_after.txt").write_text(after_file, encoding="utf-8")

    # Invalid record (missing method_after.txt)
    b2 = ib_root / "DemoRepo" / "2"
    b2.mkdir(parents=True)
    (b2 / "bug.json").write_text(json.dumps({"bug_type": "DOTNET_RESOURCE_LEAK"}), encoding="utf-8")

    temp_config.external_dir_relpath = str(ext)
    ingestor = InferredBugsIngestor(temp_config)
    samples, exclusions, _ = ingestor.ingest(max_records=10, dataset_version="v5-test")
    assert len(samples) == 2
    assert {s.label for s in samples} == {0, 1}
    assert samples[0].pair_id == samples[1].pair_id
    assert any(e.exclusion_reason == "missing_required_files" for e in exclusions)


def test_repository_split_zero_leakage() -> None:
    records = make_synthetic_records(n_repos=14, per_repo=6)
    # Assign 2 repos as dedicated hard_negative_test
    for r in records:
        if r["repository_id"] in {"org/repo_12", "org/repo_13"}:
            r["split_partition"] = "hard_negative_test"
    splits = build_repository_splits(records, independent_test_fraction=0.25, random_state=42)
    verify_zero_leakage(splits["dev"], splits["independent_test"], splits["hard_negative_test"])
    assert len(splits["dev"]) > 0
    assert len(splits["independent_test"]) > 0
    assert len(splits["hard_negative_test"]) == 12
