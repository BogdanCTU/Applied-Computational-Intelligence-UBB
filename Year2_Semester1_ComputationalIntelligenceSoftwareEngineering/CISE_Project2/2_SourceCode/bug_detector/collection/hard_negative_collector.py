"""Hard-negative collector for complex, test-backed verified-correct C# methods."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bug_detector.collection.github_bugfix_collector import (
    _parse_github_repo_id,
    classify_commit_message,
)
from bug_detector.collection.inferredbugs_ingestor import _build_feature_payload
from bug_detector.collection.models import DatasetSampleRecord, ExclusionRecord
from bug_detector.config.settings import AppConfig, load_config
from bug_detector.db.repository import sha256_text
from bug_detector.logging_utils import get_logger
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient

logger = get_logger(__name__)

_TEST_FILE_RE = re.compile(r"(?:^|/)(?:test|tests|unittest|unittests|specs?)(?:/|\.|$)|tests?\.cs$", re.IGNORECASE)
_GEN_OR_NONPROD_RE = re.compile(
    r"\.(?:designer|g|generated)\.cs$|(?:/|\\)(?:obj|bin|samples?|examples?|benchmarks?)(?:/|\\)",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class HardNegativeCollector:
    """Collects verified complex-but-correct C# methods backed by unit tests and clean recent history."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

    def _collect_test_corpus_text(self, repo_dir: Path, max_test_files: int = 80) -> str:
        chunks: list[str] = []
        count = 0
        for p in repo_dir.rglob("*.cs"):
            rel = str(p.relative_to(repo_dir))
            if _GEN_OR_NONPROD_RE.search(rel):
                continue
            if _TEST_FILE_RE.search(rel):
                try:
                    chunks.append(p.read_text(encoding="utf-8", errors="replace"))
                    count += 1
                    if count >= max_test_files:
                        break
                except Exception:
                    continue
        return "\n".join(chunks)

    def _recent_bugfix_touched_files(self, repo_dir: Path, max_commits: int = 200) -> set[str]:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "log", f"-n{max_commits}", "--no-merges", "--name-only", "--pretty=format:COMMIT:%s"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        touched: set[str] = set()
        current_is_fix = False
        for line in proc.stdout.splitlines():
            if line.startswith("COMMIT:"):
                subj = line[7:]
                current_is_fix, _ = classify_commit_message(subj)
            elif current_is_fix and line.strip().endswith(".cs"):
                touched.add(line.strip())
        return touched

    def collect(
        self,
        max_repos: int | None = None,
        max_per_repo: int | None = None,
        exclude_repo_ids: set[str] | None = None,
        exclude_short_names: set[str] | None = None,
        dataset_version: str | None = None,
        roslyn_client: RoslynPreprocessorClient | None = None,
    ) -> tuple[list[DatasetSampleRecord], list[ExclusionRecord], list[dict[str, Any]]]:
        """Collect complex, test-referenced, clean-history methods as verified hard negatives."""
        cfg_c = self.config.collection
        repo_limit = max_repos if max_repos is not None else cfg_c.hard_negatives_max_repos
        per_repo_limit = max_per_repo if max_per_repo is not None else cfg_c.hard_negatives_max_per_repo
        min_cc = cfg_c.hard_negative_min_complexity
        min_loc = cfg_c.hard_negative_min_logical_loc
        dver = dataset_version or self.config.dataset_version
        excluded = exclude_repo_ids or set()
        excluded_short = {s.lower() for s in (exclude_short_names or set())}

        root = self.config.repositories_dir
        if not root.exists():
            return [], [], []

        candidate_repos: list[tuple[str, str, Path]] = []
        for owner_dir in sorted(root.iterdir()):
            if not owner_dir.is_dir():
                continue
            for repo_dir in sorted(owner_dir.iterdir()):
                if not (repo_dir / ".git").exists():
                    continue
                remote = subprocess.run(
                    ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()
                repo_id, repo_url = _parse_github_repo_id(remote, repo_dir)
                if repo_id in excluded or repo_id.split("/")[-1].lower() in excluded_short:
                    continue
                candidate_repos.append((repo_id, repo_url, repo_dir))

        samples: list[DatasetSampleRecord] = []
        exclusions: list[ExclusionRecord] = []
        repos_meta: list[dict[str, Any]] = []
        now_ts = _utc_now()
        selected_count = 0

        own_client = roslyn_client is None
        client = roslyn_client or RoslynPreprocessorClient(self.config)
        try:
            for repo_id, repo_url, repo_dir in candidate_repos:
                if selected_count >= repo_limit:
                    break
                test_text = self._collect_test_corpus_text(repo_dir)
                if len(test_text) < 200:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="hard_negative",
                            repository_id=repo_id,
                            exclusion_reason="no_unit_test_evidence",
                        )
                    )
                    continue

                head_sha = subprocess.run(
                    ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip() or "HEAD"
                bugfix_files = self._recent_bugfix_touched_files(repo_dir)

                prod_files = [
                    p
                    for p in sorted(repo_dir.rglob("*.cs"))
                    if not _TEST_FILE_RE.search(str(p.relative_to(repo_dir)))
                    and not _GEN_OR_NONPROD_RE.search(str(p.relative_to(repo_dir)))
                ]

                repo_samples = 0
                for cs_path in prod_files[:120]:
                    if repo_samples >= per_repo_limit:
                        break
                    rel_path = str(cs_path.relative_to(repo_dir))
                    if rel_path in bugfix_files:
                        continue
                    try:
                        src = cs_path.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    if len(src) > 120_000:
                        continue
                    res = client.analyze_source(src, file_path=rel_path, mode="file")
                    if not res.success or res.has_syntax_errors:
                        continue

                    for m in res.methods:
                        if repo_samples >= per_repo_limit:
                            break
                        cc = m.structural_metrics.get("struct_cyclomatic_complexity", 1)
                        lloc = m.structural_metrics.get("struct_logical_loc", 0)
                        if cc < min_cc or lloc < min_loc:
                            continue
                        # Verify test suite references the enclosing class or method name
                        base_class = m.class_name.split(".")[-1]
                        if base_class not in test_text and m.method_name not in test_text:
                            continue

                        sid = f"hn_{repo_id.replace('/', '_')}_{sha256_text(f'{rel_path}:{m.class_name}:{m.method_signature}:{m.start_line}')[:12]}"
                        samples.append(
                            DatasetSampleRecord(
                                sample_id=sid,
                                repository_id=repo_id,
                                repository_url=repo_url,
                                commit_sha=head_sha,
                                parent_commit_sha=None,
                                file_path=rel_path,
                                class_name=m.class_name,
                                method_name=m.method_name,
                                method_signature=m.method_signature,
                                source_code=m.raw_source,
                                label=0,
                                label_source="verified_hard_negative",
                                verification_status="test_backed_verified",
                                bug_type="NONE",
                                bug_fix_reference=f"UnitTestBacked:{repo_url}/blob/{head_sha[:12]}/{rel_path}",
                                source_hash=sha256_text(m.normalized_source or m.raw_source),
                                collection_timestamp=now_ts,
                                dataset_version=dver,
                                normalized_source=m.normalized_source,
                                structural_hash=m.structural_hash,
                                pair_id=None,
                                type_kind=m.type_kind,
                                start_line=m.start_line,
                                end_line=m.end_line,
                                is_constructor=m.is_constructor,
                                is_static=m.is_static,
                                is_async=m.is_async,
                                is_generic=m.is_generic,
                                is_expression_bodied=m.is_expression_bodied,
                                extraction_mode="file",
                                source_origin="hard_negative",
                                local_path=str(repo_dir),
                                features_payload=_build_feature_payload(m),
                            )
                        )
                        repo_samples += 1

                if repo_samples > 0:
                    selected_count += 1
                    repos_meta.append(
                        {
                            "repository_id": repo_id,
                            "full_name": repo_id,
                            "repository_url": repo_url,
                            "source_origin": "hard_negative",
                            "default_branch": "HEAD",
                            "stars": 0,
                            "local_path": str(repo_dir),
                        }
                    )
        finally:
            if own_client:
                client.close()

        logger.info(
            "Hard-negative collection complete: %d complex verified-correct methods across %d repos",
            len(samples),
            selected_count,
        )
        return samples, exclusions, repos_meta
