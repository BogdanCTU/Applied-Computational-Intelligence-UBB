"""Microsoft InferredBugs (C# / InferSharp) dataset acquirer and validated ingestor."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bug_detector.collection.models import DatasetSampleRecord, ExclusionRecord
from bug_detector.config.settings import AppConfig, load_config
from bug_detector.db.repository import sha256_text
from bug_detector.logging_utils import get_logger
from bug_detector.preprocessing.models import MethodAnalysis
from bug_detector.preprocessing.normalizer import python_fallback_tokenize, token_jaccard_similarity
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient

logger = get_logger(__name__)

_TEST_PATH_RE = re.compile(r"(?:^|/)(?:test|tests|unittest|unittests|specs?)(?:/|\.|$)|test\.cs$", re.IGNORECASE)
_GENERATED_PATH_RE = re.compile(r"\.(?:designer|g|generated)\.cs$|(?:/|\\)(?:obj|bin)(?:/|\\)", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_proc_name(procedure: str) -> tuple[str | None, str | None]:
    """Parse InferSharp procedure like 'Void Documenter.CreateSimpleSettingsDataSets(Int32)'."""
    if not procedure:
        return None, None
    before_paren = procedure.split("(", 1)[0].strip()
    parts = before_paren.split()
    qual = parts[-1] if parts else before_paren
    if "." in qual:
        cls, meth = qual.rsplit(".", 1)
        cls_short = cls.split(".")[-1]
        if meth == ".ctor":
            meth = cls_short
        return cls_short, meth
    return None, qual


def _pick_matching_method(
    methods: list[MethodAnalysis],
    target_class: str | None,
    target_method: str | None,
    target_line: int | None,
) -> MethodAnalysis | None:
    if not methods:
        return None
    if len(methods) == 1:
        return methods[0]

    # Prefer exact line + name match
    if target_method:
        name_matches = [
            m
            for m in methods
            if m.method_name == target_method
            and (not target_class or target_class in m.class_name.split("."))
        ]
        if not name_matches:
            name_matches = [m for m in methods if m.method_name == target_method]
        if len(name_matches) == 1:
            return name_matches[0]
        if name_matches and target_line is not None:
            return min(
                name_matches,
                key=lambda m: (
                    0 if m.start_line <= target_line <= m.end_line else 1,
                    abs(m.start_line - target_line),
                ),
            )
    if target_line is not None:
        return min(
            methods,
            key=lambda m: (
                0 if m.start_line <= target_line <= m.end_line else 1,
                abs(m.start_line - target_line),
            ),
        )
    return None


def _build_feature_payload(m: MethodAnalysis) -> dict[str, Any]:
    return {
        "extractor_version": "1.0.0",
        "semantic_model_available": bool(m.dfg_metrics.get("semantic_model_available", 0.0) > 0.5),
        "cfg_available": bool(m.cfg_metrics.get("cfg_available", 0.0) > 0.5),
        "dfg_available": bool(m.dfg_metrics.get("dfg_available", 0.0) > 0.5),
        "extraction_failed": bool(m.has_syntax_errors),
        "tokens_normalized": m.tokens_normalized,
        "api_calls": m.api_calls,
        "lexical_metrics": m.lexical_metrics,
        "ast_metrics": m.ast_metrics,
        "cfg_metrics": m.cfg_metrics,
        "dfg_metrics": m.dfg_metrics,
        "structural_metrics": m.structural_metrics,
        "extraction_warnings": m.extraction_warnings,
    }


class InferredBugsIngestor:
    """Validates and ingests C# buggy/fixed pairs from microsoft/InferredBugs."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.inferred_dir = self.config.external_dir / "InferredBugs"
        self.csharp_root = self.inferred_dir / "inferredbugs" / "csharp"

    def ensure_cloned(self) -> Path:
        """Sparse-clone microsoft/InferredBugs (C# subset only) if not already present."""
        if self.csharp_root.exists():
            return self.csharp_root
        self.inferred_dir.parent.mkdir(parents=True, exist_ok=True)
        url = self.config.collection.inferredbugs_repo_url
        logger.info("Sparse-cloning InferredBugs C# dataset from %s...", url)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", url, str(self.inferred_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.inferred_dir),
                "sparse-checkout",
                "set",
                "--no-cone",
                "/inferredbugs/csharp",
                "/README.md",
                "/LICENSE",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return self.csharp_root

    def _discover_bug_dirs(self, max_records: int | None = None) -> list[tuple[str, str, Path]]:
        if not self.csharp_root.exists():
            raise FileNotFoundError(f"InferredBugs C# directory not found: {self.csharp_root}")
        entries: list[tuple[str, str, Path]] = []
        for repo_dir in sorted(self.csharp_root.iterdir()):
            if not repo_dir.is_dir():
                continue
            for bug_dir in sorted(repo_dir.iterdir(), key=lambda p: (len(p.name), p.name)):
                if bug_dir.is_dir():
                    entries.append((repo_dir.name, bug_dir.name, bug_dir))
                    if max_records is not None and len(entries) >= max_records:
                        return entries
        return entries

    def ingest(
        self,
        max_records: int | None = None,
        dataset_version: str | None = None,
        roslyn_client: RoslynPreprocessorClient | None = None,
    ) -> tuple[list[DatasetSampleRecord], list[ExclusionRecord], list[dict[str, Any]]]:
        """Ingest validated BUG/CLEAN pairs from InferredBugs C# records."""
        if not self.csharp_root.exists():
            self.ensure_cloned()

        limit = max_records if max_records is not None else self.config.collection.inferredbugs_max_records
        dver = dataset_version or self.config.dataset_version
        bug_dirs = self._discover_bug_dirs(max_records=limit)
        logger.info("Found %d InferredBugs C# bug directories to validate (limit=%d)", len(bug_dirs), limit)

        samples: list[DatasetSampleRecord] = []
        exclusions: list[ExclusionRecord] = []
        repo_meta: dict[str, dict[str, Any]] = {}
        now_ts = _utc_now()

        own_client = roslyn_client is None
        client = roslyn_client or RoslynPreprocessorClient(self.config)
        try:
            for repo_name, bug_id, bug_dir in bug_dirs:
                repo_id = f"inferredbugs/{repo_name}"
                ext_ref = f"{repo_name}/{bug_id}"
                repo_meta.setdefault(
                    repo_id,
                    {
                        "repository_id": repo_id,
                        "full_name": repo_name,
                        "repository_url": f"https://github.com/microsoft/InferredBugs/tree/main/inferredbugs/csharp/{repo_name}",
                        "source_origin": "inferredbugs",
                        "default_branch": "main",
                        "stars": 0,
                        "local_path": str(bug_dir.parent),
                    },
                )

                bug_json_path = bug_dir / "bug.json"
                commit_json_path = bug_dir / "commit_info.json"
                meth_before_path = bug_dir / "method_before.txt"
                meth_after_path = bug_dir / "method_after.txt"
                file_before_path = bug_dir / "file_before.txt"
                file_after_path = bug_dir / "file_after.txt"

                if not bug_json_path.exists() or not meth_before_path.exists() or not meth_after_path.exists():
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            exclusion_reason="missing_required_files",
                            details="Missing bug.json, method_before.txt, or method_after.txt",
                        )
                    )
                    continue

                try:
                    bug_info = json.loads(bug_json_path.read_text(encoding="utf-8", errors="replace"))
                    commit_info = (
                        json.loads(commit_json_path.read_text(encoding="utf-8", errors="replace"))
                        if commit_json_path.exists()
                        else {}
                    )
                except Exception as exc:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            exclusion_reason="malformed_metadata_json",
                            details=str(exc),
                        )
                    )
                    continue

                file_rel = str(bug_info.get("file") or f"{repo_name}.cs")
                if _TEST_PATH_RE.search(file_rel) or _GENERATED_PATH_RE.search(file_rel):
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            exclusion_reason="test_or_generated_file",
                        )
                    )
                    continue

                bug_type = str(bug_info.get("bug_type") or "UNKNOWN_INFERSHARP_BUG")
                severity = str(bug_info.get("severity") or "ERROR")
                procedure = str(bug_info.get("procedure") or "")
                target_line = bug_info.get("procedure_start_line") or bug_info.get("line")
                target_cls, target_meth = _extract_proc_name(procedure)

                mb_raw = meth_before_path.read_text(encoding="utf-8", errors="replace").strip()
                ma_raw = meth_after_path.read_text(encoding="utf-8", errors="replace").strip()
                if not mb_raw or not ma_raw:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=target_meth,
                            exclusion_reason="empty_source",
                        )
                    )
                    continue

                if mb_raw == ma_raw:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=target_meth,
                            exclusion_reason="identical_before_after",
                        )
                    )
                    continue

                # Prefer extracting from full file_before/file_after for realistic semantic/class context
                before_method: MethodAnalysis | None = None
                after_method: MethodAnalysis | None = None
                extraction_mode = "file"

                if file_before_path.exists() and file_after_path.exists():
                    fb_raw = file_before_path.read_text(encoding="utf-8", errors="replace")
                    fa_raw = file_after_path.read_text(encoding="utf-8", errors="replace")
                    if fb_raw.strip() and fa_raw.strip():
                        fb_res = client.analyze_source(fb_raw, file_path=file_rel, mode="file")
                        fa_res = client.analyze_source(fa_raw, file_path=file_rel, mode="file")
                        if fb_res.success and fa_res.success:
                            cand_b = _pick_matching_method(
                                fb_res.methods, target_cls, target_meth, int(target_line) if target_line else None
                            )
                            cand_a = _pick_matching_method(
                                fa_res.methods, target_cls, target_meth, int(target_line) if target_line else None
                            )
                            if cand_b is not None and cand_a is not None and cand_b.method_name == cand_a.method_name:
                                before_method = cand_b
                                after_method = cand_a

                if before_method is None or after_method is None:
                    extraction_mode = "method_snippet"
                    mb_res = client.analyze_source(mb_raw, file_path=file_rel, mode="method_snippet")
                    ma_res = client.analyze_source(ma_raw, file_path=file_rel, mode="method_snippet")
                    if not mb_res.success or not ma_res.success or mb_res.has_syntax_errors or ma_res.has_syntax_errors:
                        exclusions.append(
                            ExclusionRecord(
                                source_origin="inferredbugs",
                                repository_id=repo_id,
                                external_ref=ext_ref,
                                file_path=file_rel,
                                method_name=target_meth,
                                exclusion_reason="syntax_error_in_source",
                                details=mb_res.error_message or ma_res.error_message,
                            )
                        )
                        continue
                    if not mb_res.methods or not ma_res.methods:
                        exclusions.append(
                            ExclusionRecord(
                                source_origin="inferredbugs",
                                repository_id=repo_id,
                                external_ref=ext_ref,
                                file_path=file_rel,
                                method_name=target_meth,
                                exclusion_reason="no_method_extracted",
                            )
                        )
                        continue
                    before_method = mb_res.methods[0]
                    after_method = ma_res.methods[0]
                    if target_cls and before_method.class_name == "SnippetContainer":
                        before_method.class_name = target_cls
                        after_method.class_name = target_cls

                if before_method.normalized_source == after_method.normalized_source:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=before_method.method_name,
                            exclusion_reason="identical_after_normalization",
                        )
                    )
                    continue

                b_loc = before_method.structural_metrics.get("struct_logical_loc", 0)
                a_loc = after_method.structural_metrics.get("struct_logical_loc", 0)
                b_stmts = before_method.structural_metrics.get("struct_statement_count", 0)
                a_stmts = after_method.structural_metrics.get("struct_statement_count", 0)
                if b_loc < 3 or b_stmts < 1:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=before_method.method_name,
                            exclusion_reason="trivial_or_empty_method",
                        )
                    )
                    continue

                # Reject cases where after-method was refactored into a tiny 1-2 statement delegation stub
                if b_stmts >= 5 and a_stmts <= 2 and len(after_method.tokens_normalized) < 0.35 * len(before_method.tokens_normalized):
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=before_method.method_name,
                            exclusion_reason="delegation_stub_refactor",
                            details=f"before_stmts={b_stmts}, after_stmts={a_stmts}",
                        )
                    )
                    continue

                jaccard = token_jaccard_similarity(
                    before_method.tokens_normalized or python_fallback_tokenize(before_method.raw_source),
                    after_method.tokens_normalized or python_fallback_tokenize(after_method.raw_source),
                )
                if jaccard < 0.15:
                    exclusions.append(
                        ExclusionRecord(
                            source_origin="inferredbugs",
                            repository_id=repo_id,
                            external_ref=ext_ref,
                            file_path=file_rel,
                            method_name=before_method.method_name,
                            exclusion_reason="unrelated_full_rewrite",
                            details=f"jaccard={jaccard:.3f}",
                        )
                    )
                    continue

                fix_sha = str(commit_info.get("hash") or f"inferredbugs_{repo_name}_{bug_id}")
                commit_msg = str(commit_info.get("message") or "")
                pair_id = f"ib_{repo_name}_{bug_id}"
                bug_ref = f"InferredBugs:{repo_name}/{bug_id}:{fix_sha[:12]}"

                samples.append(
                    DatasetSampleRecord(
                        sample_id=f"{pair_id}_bug",
                        repository_id=repo_id,
                        repository_url=repo_meta[repo_id]["repository_url"],
                        commit_sha=f"{fix_sha}^",
                        parent_commit_sha=None,
                        file_path=file_rel,
                        class_name=before_method.class_name,
                        method_name=before_method.method_name,
                        method_signature=before_method.method_signature,
                        source_code=before_method.raw_source,
                        label=1,
                        label_source="inferredbugs_infersharp",
                        verification_status="static_analyzer_verified_fix",
                        bug_type=bug_type,
                        bug_fix_reference=bug_ref,
                        source_hash=sha256_text(before_method.normalized_source or before_method.raw_source),
                        collection_timestamp=now_ts,
                        dataset_version=dver,
                        normalized_source=before_method.normalized_source,
                        structural_hash=before_method.structural_hash,
                        pair_id=pair_id,
                        commit_message=commit_msg,
                        severity=severity,
                        type_kind=before_method.type_kind,
                        start_line=before_method.start_line,
                        end_line=before_method.end_line,
                        is_constructor=before_method.is_constructor,
                        is_static=before_method.is_static,
                        is_async=before_method.is_async,
                        is_generic=before_method.is_generic,
                        is_expression_bodied=before_method.is_expression_bodied,
                        extraction_mode=extraction_mode,
                        source_origin="inferredbugs",
                        local_path=str(bug_dir),
                        features_payload=_build_feature_payload(before_method),
                    )
                )

                samples.append(
                    DatasetSampleRecord(
                        sample_id=f"{pair_id}_fix",
                        repository_id=repo_id,
                        repository_url=repo_meta[repo_id]["repository_url"],
                        commit_sha=fix_sha,
                        parent_commit_sha=f"{fix_sha}^",
                        file_path=file_rel,
                        class_name=after_method.class_name,
                        method_name=after_method.method_name,
                        method_signature=after_method.method_signature,
                        source_code=after_method.raw_source,
                        label=0,
                        label_source="inferredbugs_post_fix",
                        verification_status="post_fix_verified",
                        bug_type="NONE",
                        bug_fix_reference=bug_ref,
                        source_hash=sha256_text(after_method.normalized_source or after_method.raw_source),
                        collection_timestamp=now_ts,
                        dataset_version=dver,
                        normalized_source=after_method.normalized_source,
                        structural_hash=after_method.structural_hash,
                        pair_id=pair_id,
                        commit_message=commit_msg,
                        severity=severity,
                        type_kind=after_method.type_kind,
                        start_line=after_method.start_line,
                        end_line=after_method.end_line,
                        is_constructor=after_method.is_constructor,
                        is_static=after_method.is_static,
                        is_async=after_method.is_async,
                        is_generic=after_method.is_generic,
                        is_expression_bodied=after_method.is_expression_bodied,
                        extraction_mode=extraction_mode,
                        source_origin="inferredbugs",
                        local_path=str(bug_dir),
                        features_payload=_build_feature_payload(after_method),
                    )
                )
        finally:
            if own_client:
                client.close()

        logger.info(
            "InferredBugs ingestion complete: %d valid samples (%d pairs), %d exclusions across %d repos",
            len(samples),
            len(samples) // 2,
            len(exclusions),
            len({s.repository_id for s in samples}),
        )
        return samples, exclusions, list(repo_meta.values())
