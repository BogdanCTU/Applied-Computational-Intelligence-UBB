"""Verified GitHub bug-fix pair collector (API client + local mirror git history miner)."""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from bug_detector.collection.inferredbugs_ingestor import _build_feature_payload
from bug_detector.collection.models import DatasetSampleRecord, ExclusionRecord
from bug_detector.config.settings import AppConfig, load_config
from bug_detector.db.repository import sha256_text
from bug_detector.logging_utils import get_logger
from bug_detector.preprocessing.models import MethodAnalysis
from bug_detector.preprocessing.normalizer import python_fallback_tokenize, token_jaccard_similarity
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient

logger = get_logger(__name__)

_BUG_POSITIVE_RE = re.compile(
    r"\b(fix(?:es|ed|ing)?|bug|defect|null(?:\s*reference|\s*pointer|\s*check)?|nre|"
    r"crash|exception|race(?:\s*condition)?|deadlock|leak|dispose|overflow|underflow|"
    r"off[-\s]?by[-\s]?one|regression|fault|broken|incorrect|wrong)\b",
    re.IGNORECASE,
)

_NON_BUG_EXCLUSION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("merge_or_revert_commit", re.compile(r"^(?:merge\b|revert\b)", re.IGNORECASE)),
    ("formatting_only", re.compile(r"\b(?:format(?:ting)?|whitespace|indent(?:ation)?|stylecop|clang-format|lint)\b", re.IGNORECASE)),
    ("pure_refactoring", re.compile(r"\b(?:refactor(?:ing)?|cleanup|clean\s+up|rename|reorganize|simplify|extract\s+method)\b", re.IGNORECASE)),
    ("documentation_only", re.compile(r"\b(?:docs?|readme|changelog|comment|typo|javadoc|xmldoc)\b", re.IGNORECASE)),
    ("dependency_update", re.compile(r"\b(?:bump|dependabot|nuget|package|upgrade\s+dependency|version\s+bump)\b", re.IGNORECASE)),
    ("performance_without_defect", re.compile(r"\b(?:perf(?:ormance)?|optimize|optimization|benchmark|alloc(?:ation)?\s+reduction)\b", re.IGNORECASE)),
    ("ci_or_build_change", re.compile(r"\b(?:ci|workflow|github\s+actions|pipeline|csproj|sln)\b", re.IGNORECASE)),
]

_ISSUE_PR_RE = re.compile(r"(?:#|GH-)(\d+)\b", re.IGNORECASE)
_TEST_OR_GEN_PATH_RE = re.compile(
    r"(?:^|/)(?:test|tests|unittest|unittests|spec|specs|sample|samples|example|examples|benchmark|benchmarks)(?:/|\.|$)"
    r"|\.(?:designer|g|generated)\.cs$|(?:/|\\)(?:obj|bin)(?:/|\\)|test\.cs$",
    re.IGNORECASE,
)

_BUG_TYPE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("NULL_DEREFERENCE", re.compile(r"\b(?:null|nre|nullreference|nullable|null\s*check)\b", re.IGNORECASE)),
    ("RESOURCE_LEAK", re.compile(r"\b(?:leak|dispose|disposable|close|stream|handle|memory\s*leak)\b", re.IGNORECASE)),
    ("CONCURRENCY_DEFECT", re.compile(r"\b(?:race|deadlock|thread|lock|async|concurrent|cancellation)\b", re.IGNORECASE)),
    ("EXCEPTION_HANDLING", re.compile(r"\b(?:exception|catch|throw|crash|unhandled)\b", re.IGNORECASE)),
    ("BOUNDARY_OR_INDEX_ERROR", re.compile(r"\b(?:index|bounds|range|off[-\s]?by[-\s]?one|overflow|underflow)\b", re.IGNORECASE)),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_commit_message(message: str) -> tuple[bool, str]:
    """Classify whether a commit message indicates a genuine correctness defect fix."""
    first_line = (message or "").strip().splitlines()[0] if message else ""
    if not first_line:
        return False, "empty_commit_message"

    for reason, pat in _NON_BUG_EXCLUSION_PATTERNS:
        if pat.search(first_line):
            # Allow if explicit issue fix AND bug/null/crash/regression is mentioned, unless merge/revert/dependency
            if reason in {"merge_or_revert_commit", "dependency_update", "documentation_only", "formatting_only"}:
                return False, reason
            if not re.search(r"\b(?:bug|null|crash|regression|exception|race|deadlock|leak)\b", first_line, re.IGNORECASE):
                return False, reason

    if _BUG_POSITIVE_RE.search(first_line):
        return True, "bugfix_signal"
    return False, "no_bugfix_signal"


def infer_bug_type_from_message(message: str) -> str:
    for btype, pat in _BUG_TYPE_RULES:
        if pat.search(message or ""):
            return btype
    return "LOGIC_OR_CORRECTNESS_DEFECT"


def _parse_github_repo_id(remote_url: str, fallback_dir: Path) -> tuple[str, str]:
    url = (remote_url or "").strip()
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", url, re.IGNORECASE)
    if m:
        owner, name = m.group(1), m.group(2)
        return f"{owner}/{name}", f"https://github.com/{owner}/{name}"
    return f"{fallback_dir.parent.name}/{fallback_dir.name}", url or str(fallback_dir)


class GitHubRestClient:
    """Rate-limit-aware GitHub REST API v3 client with exponential-backoff retries."""

    def __init__(self, token: str | None = None, timeout_seconds: int = 20, max_retries: int = 4) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "CISE-BugDetector-v5",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(self.max_retries):
            resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if resp.status_code == 403 and remaining == "0":
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0") or 0)
                wait_s = max(1, min(60, reset_ts - int(time.time()) + 1))
                logger.warning("GitHub API rate limit hit; sleeping %ds (attempt %d)", wait_s, attempt + 1)
                time.sleep(wait_s)
                continue
            if resp.status_code >= 500 or resp.status_code == 429:
                time.sleep(min(30, 2**attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"GitHub API request failed after {self.max_retries} retries: {url}")


class GitHubBugFixCollector:
    """Collects verified before/after bug-fix method pairs from GitHub repositories."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.checkpoint_path = self.config.datasets_dir / "checkpoints" / "github_bugfix_checkpoint.json"

    def _load_checkpoint(self) -> dict[str, Any]:
        if self.checkpoint_path.exists():
            try:
                return json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            except Exception:
                return {"completed_repos": []}
        return {"completed_repos": []}

    def _save_checkpoint(self, state: dict[str, Any]) -> None:
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _discover_local_git_repos(
        self,
        exclude_repo_ids: set[str] | None = None,
        exclude_short_names: set[str] | None = None,
    ) -> list[tuple[str, str, Path]]:
        root = self.config.repositories_dir
        if not root.exists():
            return []
        excluded = exclude_repo_ids or set()
        excluded_short = {s.lower() for s in (exclude_short_names or set())}
        repos: list[tuple[str, str, Path]] = []
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
                short_name = repo_id.split("/")[-1].lower()
                if repo_id in excluded or short_name in excluded_short:
                    continue
                repos.append((repo_id, repo_url, repo_dir))
        return repos

    def _git_show(self, repo_dir: Path, rev: str, rel_path: str) -> str | None:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "show", f"{rev}:{rel_path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return proc.stdout if proc.returncode == 0 else None

    def collect_from_local_mirrors(
        self,
        max_repos: int | None = None,
        max_commits_per_repo: int | None = None,
        max_pairs_per_repo: int | None = None,
        exclude_repo_ids: set[str] | None = None,
        exclude_short_names: set[str] | None = None,
        resume: bool = False,
        dataset_version: str | None = None,
        roslyn_client: RoslynPreprocessorClient | None = None,
    ) -> tuple[list[DatasetSampleRecord], list[ExclusionRecord], list[dict[str, Any]]]:
        """Mine verified bug-fix method pairs from local full-history GitHub clones."""
        cfg_c = self.config.collection
        repo_limit = max_repos if max_repos is not None else cfg_c.github_max_repos
        commit_limit = max_commits_per_repo if max_commits_per_repo is not None else cfg_c.github_max_commits_per_repo
        pair_limit = max_pairs_per_repo if max_pairs_per_repo is not None else cfg_c.github_max_pairs_per_repo
        dver = dataset_version or self.config.dataset_version

        ckpt = self._load_checkpoint() if resume else {"completed_repos": []}
        completed = set(ckpt.get("completed_repos", []))

        candidates = self._discover_local_git_repos(
            exclude_repo_ids=exclude_repo_ids,
            exclude_short_names=exclude_short_names,
        )
        selected = [c for c in candidates if c[0] not in completed][:repo_limit]
        logger.info("Mining GitHub bug-fix pairs from %d local repository mirrors", len(selected))

        samples: list[DatasetSampleRecord] = []
        exclusions: list[ExclusionRecord] = []
        repos_meta: list[dict[str, Any]] = []
        now_ts = _utc_now()

        own_client = roslyn_client is None
        client = roslyn_client or RoslynPreprocessorClient(self.config)
        try:
            for repo_id, repo_url, repo_dir in selected:
                repos_meta.append(
                    {
                        "repository_id": repo_id,
                        "full_name": repo_id,
                        "repository_url": repo_url,
                        "source_origin": "github_bugfix",
                        "default_branch": "HEAD",
                        "stars": 0,
                        "local_path": str(repo_dir),
                    }
                )
                log_proc = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_dir),
                        "log",
                        f"-n{commit_limit}",
                        "--no-merges",
                        "--pretty=format:%H%x1f%P%x1f%aI%x1f%s",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                if log_proc.returncode != 0:
                    continue

                repo_pairs = 0
                for line in log_proc.stdout.splitlines():
                    if repo_pairs >= pair_limit:
                        break
                    parts = line.split("\x1f")
                    if len(parts) < 4:
                        continue
                    sha, parents_str, author_date, subject = parts[0], parts[1], parts[2], parts[3]
                    parents = [p for p in parents_str.split() if p]
                    if len(parents) != 1:
                        continue
                    parent_sha = parents[0]

                    is_fix, reason = classify_commit_message(subject)
                    if not is_fix:
                        if reason != "no_bugfix_signal":
                            exclusions.append(
                                ExclusionRecord(
                                    source_origin="github_bugfix",
                                    repository_id=repo_id,
                                    external_ref=sha[:12],
                                    exclusion_reason=reason,
                                    details=subject[:180],
                                )
                            )
                        continue

                    # Inspect changed files in commit
                    files_proc = subprocess.run(
                        ["git", "-C", str(repo_dir), "diff-tree", "--no-commit-id", "--name-status", "-r", sha],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                    )
                    changed_cs: list[str] = []
                    all_changed_count = 0
                    for fline in files_proc.stdout.splitlines():
                        fparts = fline.split("\t")
                        if len(fparts) < 2:
                            continue
                        status, fpath = fparts[0], fparts[-1]
                        all_changed_count += 1
                        if status == "M" and fpath.endswith(".cs") and not _TEST_OR_GEN_PATH_RE.search(fpath):
                            changed_cs.append(fpath)

                    if not changed_cs or len(changed_cs) > cfg_c.github_max_changed_files or all_changed_count > 6:
                        exclusions.append(
                            ExclusionRecord(
                                source_origin="github_bugfix",
                                repository_id=repo_id,
                                external_ref=sha[:12],
                                exclusion_reason="unfocused_or_non_csharp_commit",
                                details=f"cs={len(changed_cs)}, total={all_changed_count}",
                            )
                        )
                        continue

                    issue_match = _ISSUE_PR_RE.search(subject)
                    bug_fix_ref = f"{repo_url}/commit/{sha}" + (f" (#{issue_match.group(1)})" if issue_match else "")
                    bug_type = infer_bug_type_from_message(subject)

                    for rel_path in changed_cs:
                        if repo_pairs >= pair_limit:
                            break
                        before_src = self._git_show(repo_dir, parent_sha, rel_path)
                        after_src = self._git_show(repo_dir, sha, rel_path)
                        if not before_src or not after_src:
                            continue

                        res_b = client.analyze_source(before_src, file_path=rel_path, mode="file")
                        res_a = client.analyze_source(after_src, file_path=rel_path, mode="file")
                        if not res_b.success or not res_a.success or res_b.has_syntax_errors or res_a.has_syntax_errors:
                            exclusions.append(
                                ExclusionRecord(
                                    source_origin="github_bugfix",
                                    repository_id=repo_id,
                                    external_ref=sha[:12],
                                    file_path=rel_path,
                                    exclusion_reason="syntax_error_in_commit_file",
                                )
                            )
                            continue

                        map_b: dict[tuple[str, str], MethodAnalysis] = {
                            (m.class_name, m.method_signature): m for m in res_b.methods
                        }
                        map_a: dict[tuple[str, str], MethodAnalysis] = {
                            (m.class_name, m.method_signature): m for m in res_a.methods
                        }
                        common_keys = sorted(set(map_b.keys()) & set(map_a.keys()))
                        changed_pairs: list[tuple[MethodAnalysis, MethodAnalysis]] = []
                        for k in common_keys:
                            mb, ma = map_b[k], map_a[k]
                            if mb.raw_source != ma.raw_source:
                                changed_pairs.append((mb, ma))

                        # Require focused fix: 1 or 2 changed methods per file
                        if not changed_pairs or len(changed_pairs) > 2:
                            exclusions.append(
                                ExclusionRecord(
                                    source_origin="github_bugfix",
                                    repository_id=repo_id,
                                    external_ref=sha[:12],
                                    file_path=rel_path,
                                    exclusion_reason="ambiguous_changed_methods",
                                    details=f"changed_method_count={len(changed_pairs)}",
                                )
                            )
                            continue

                        for idx_m, (mb, ma) in enumerate(changed_pairs):
                            if mb.normalized_source == ma.normalized_source:
                                exclusions.append(
                                    ExclusionRecord(
                                        source_origin="github_bugfix",
                                        repository_id=repo_id,
                                        external_ref=sha[:12],
                                        file_path=rel_path,
                                        method_name=mb.method_name,
                                        exclusion_reason="formatting_only_diff",
                                    )
                                )
                                continue

                            b_loc = mb.structural_metrics.get("struct_logical_loc", 0)
                            b_stmts = mb.structural_metrics.get("struct_statement_count", 0)
                            if b_loc < 4 or b_stmts < 2:
                                exclusions.append(
                                    ExclusionRecord(
                                        source_origin="github_bugfix",
                                        repository_id=repo_id,
                                        external_ref=sha[:12],
                                        file_path=rel_path,
                                        method_name=mb.method_name,
                                        exclusion_reason="trivial_or_empty_method",
                                    )
                                )
                                continue

                            line_delta = abs((mb.end_line - mb.start_line) - (ma.end_line - ma.start_line))
                            jaccard = token_jaccard_similarity(
                                mb.tokens_normalized or python_fallback_tokenize(mb.raw_source),
                                ma.tokens_normalized or python_fallback_tokenize(ma.raw_source),
                            )
                            if line_delta > cfg_c.github_max_changed_lines_per_method or jaccard < 0.25:
                                exclusions.append(
                                    ExclusionRecord(
                                        source_origin="github_bugfix",
                                        repository_id=repo_id,
                                        external_ref=sha[:12],
                                        file_path=rel_path,
                                        method_name=mb.method_name,
                                        exclusion_reason="excessive_method_rewrite",
                                        details=f"line_delta={line_delta}, jaccard={jaccard:.3f}",
                                    )
                                )
                                continue

                            file_tag = sha256_text(rel_path)[:6]
                            pair_id = f"gh_{repo_id.replace('/', '_')}_{sha[:10]}_{file_tag}_{idx_m}"
                            samples.append(
                                DatasetSampleRecord(
                                    sample_id=f"{pair_id}_bug",
                                    repository_id=repo_id,
                                    repository_url=repo_url,
                                    commit_sha=parent_sha,
                                    parent_commit_sha=None,
                                    file_path=rel_path,
                                    class_name=mb.class_name,
                                    method_name=mb.method_name,
                                    method_signature=mb.method_signature,
                                    source_code=mb.raw_source,
                                    label=1,
                                    label_source="github_bugfix_commit",
                                    verification_status="commit_verified_bugfix",
                                    bug_type=bug_type,
                                    bug_fix_reference=bug_fix_ref,
                                    source_hash=sha256_text(mb.normalized_source or mb.raw_source),
                                    collection_timestamp=now_ts,
                                    dataset_version=dver,
                                    normalized_source=mb.normalized_source,
                                    structural_hash=mb.structural_hash,
                                    pair_id=pair_id,
                                    commit_timestamp=author_date,
                                    commit_message=subject,
                                    type_kind=mb.type_kind,
                                    start_line=mb.start_line,
                                    end_line=mb.end_line,
                                    is_constructor=mb.is_constructor,
                                    is_static=mb.is_static,
                                    is_async=mb.is_async,
                                    is_generic=mb.is_generic,
                                    is_expression_bodied=mb.is_expression_bodied,
                                    extraction_mode="file",
                                    source_origin="github_bugfix",
                                    local_path=str(repo_dir),
                                    features_payload=_build_feature_payload(mb),
                                )
                            )
                            samples.append(
                                DatasetSampleRecord(
                                    sample_id=f"{pair_id}_fix",
                                    repository_id=repo_id,
                                    repository_url=repo_url,
                                    commit_sha=sha,
                                    parent_commit_sha=parent_sha,
                                    file_path=rel_path,
                                    class_name=ma.class_name,
                                    method_name=ma.method_name,
                                    method_signature=ma.method_signature,
                                    source_code=ma.raw_source,
                                    label=0,
                                    label_source="github_post_fix",
                                    verification_status="post_fix_verified",
                                    bug_type="NONE",
                                    bug_fix_reference=bug_fix_ref,
                                    source_hash=sha256_text(ma.normalized_source or ma.raw_source),
                                    collection_timestamp=now_ts,
                                    dataset_version=dver,
                                    normalized_source=ma.normalized_source,
                                    structural_hash=ma.structural_hash,
                                    pair_id=pair_id,
                                    commit_timestamp=author_date,
                                    commit_message=subject,
                                    type_kind=ma.type_kind,
                                    start_line=ma.start_line,
                                    end_line=ma.end_line,
                                    is_constructor=ma.is_constructor,
                                    is_static=ma.is_static,
                                    is_async=ma.is_async,
                                    is_generic=ma.is_generic,
                                    is_expression_bodied=ma.is_expression_bodied,
                                    extraction_mode="file",
                                    source_origin="github_bugfix",
                                    local_path=str(repo_dir),
                                    features_payload=_build_feature_payload(ma),
                                )
                            )
                            repo_pairs += 1

                completed.add(repo_id)
                self._save_checkpoint({"completed_repos": sorted(completed), "updated_at": _utc_now()})
        finally:
            if own_client:
                client.close()

        logger.info(
            "GitHub bug-fix collection complete: %d samples (%d pairs), %d exclusions across %d repos",
            len(samples),
            len(samples) // 2,
            len(exclusions),
            len({s.repository_id for s in samples}),
        )
        return samples, exclusions, repos_meta

    def collect_from_github_api(
        self,
        repo_full_names: list[str],
        max_commits_per_repo: int = 30,
        max_pairs_per_repo: int = 10,
        dataset_version: str | None = None,
        roslyn_client: RoslynPreprocessorClient | None = None,
    ) -> tuple[list[DatasetSampleRecord], list[ExclusionRecord], list[dict[str, Any]]]:
        """Collect verified bug-fix pairs directly via GitHub REST API v3 (rate-limit & retry aware)."""
        dver = dataset_version or self.config.dataset_version
        api = GitHubRestClient(
            token=self.config.github_token,
            timeout_seconds=self.config.collection.github_api_timeout_seconds,
            max_retries=self.config.collection.github_api_max_retries,
        )
        samples: list[DatasetSampleRecord] = []
        exclusions: list[ExclusionRecord] = []
        repos_meta: list[dict[str, Any]] = []
        now_ts = _utc_now()
        own_client = roslyn_client is None
        client = roslyn_client or RoslynPreprocessorClient(self.config)
        try:
            for full_name in repo_full_names:
                repo_info = api.get_json(f"https://api.github.com/repos/{full_name}")
                repo_url = str(repo_info.get("html_url") or f"https://github.com/{full_name}")
                repos_meta.append(
                    {
                        "repository_id": full_name,
                        "full_name": full_name,
                        "repository_url": repo_url,
                        "source_origin": "github_api_bugfix",
                        "default_branch": repo_info.get("default_branch", "main"),
                        "stars": int(repo_info.get("stargazers_count", 0)),
                        "local_path": None,
                    }
                )
                commits = api.get_json(
                    f"https://api.github.com/repos/{full_name}/commits",
                    params={"per_page": min(max_commits_per_repo, 100)},
                )
                repo_pairs = 0
                for c_item in commits:
                    if repo_pairs >= max_pairs_per_repo:
                        break
                    sha = c_item["sha"]
                    parents = c_item.get("parents") or []
                    if len(parents) != 1:
                        continue
                    parent_sha = parents[0]["sha"]
                    msg = (c_item.get("commit") or {}).get("message", "")
                    author_date = ((c_item.get("commit") or {}).get("author") or {}).get("date")
                    is_fix, reason = classify_commit_message(msg)
                    if not is_fix:
                        if reason != "no_bugfix_signal":
                            exclusions.append(
                                ExclusionRecord(
                                    source_origin="github_api_bugfix",
                                    repository_id=full_name,
                                    external_ref=sha[:12],
                                    exclusion_reason=reason,
                                    details=msg.splitlines()[0][:180] if msg else "",
                                )
                            )
                        continue
                    detail = api.get_json(f"https://api.github.com/repos/{full_name}/commits/{sha}")
                    files = [
                        f
                        for f in detail.get("files", [])
                        if f.get("status") == "modified"
                        and str(f.get("filename", "")).endswith(".cs")
                        and not _TEST_OR_GEN_PATH_RE.search(str(f.get("filename", "")))
                    ]
                    if not files or len(files) > self.config.collection.github_max_changed_files:
                        continue
                    bug_type = infer_bug_type_from_message(msg)
                    issue_m = _ISSUE_PR_RE.search(msg)
                    bug_ref = f"{repo_url}/commit/{sha}" + (f" (#{issue_m.group(1)})" if issue_m else "")
                    for f in files:
                        if repo_pairs >= max_pairs_per_repo:
                            break
                        fpath = f["filename"]
                        raw_b_resp = api.session.get(
                            f"https://raw.githubusercontent.com/{full_name}/{parent_sha}/{fpath}",
                            timeout=self.config.collection.github_api_timeout_seconds,
                        )
                        raw_a_resp = api.session.get(
                            f"https://raw.githubusercontent.com/{full_name}/{sha}/{fpath}",
                            timeout=self.config.collection.github_api_timeout_seconds,
                        )
                        if raw_b_resp.status_code != 200 or raw_a_resp.status_code != 200:
                            continue
                        res_b = client.analyze_source(raw_b_resp.text, file_path=fpath, mode="file")
                        res_a = client.analyze_source(raw_a_resp.text, file_path=fpath, mode="file")
                        if not res_b.success or not res_a.success or res_b.has_syntax_errors or res_a.has_syntax_errors:
                            continue
                        map_b = {(m.class_name, m.method_signature): m for m in res_b.methods}
                        map_a = {(m.class_name, m.method_signature): m for m in res_a.methods}
                        changed = [
                            (map_b[k], map_a[k])
                            for k in sorted(set(map_b) & set(map_a))
                            if map_b[k].raw_source != map_a[k].raw_source
                        ]
                        if not changed or len(changed) > 2:
                            continue
                        for idx_m, (mb, ma) in enumerate(changed):
                            if mb.normalized_source == ma.normalized_source:
                                continue
                            file_tag = sha256_text(fpath)[:6]
                            pair_id = f"ghapi_{full_name.replace('/', '_')}_{sha[:10]}_{file_tag}_{idx_m}"
                            for lbl, lsrc, vstat, btype, csha, psha, m_obj in [
                                (1, "github_bugfix_commit", "commit_verified_bugfix", bug_type, parent_sha, None, mb),
                                (0, "github_post_fix", "post_fix_verified", "NONE", sha, parent_sha, ma),
                            ]:
                                samples.append(
                                    DatasetSampleRecord(
                                        sample_id=f"{pair_id}_{'bug' if lbl == 1 else 'fix'}",
                                        repository_id=full_name,
                                        repository_url=repo_url,
                                        commit_sha=csha,
                                        parent_commit_sha=psha,
                                        file_path=fpath,
                                        class_name=m_obj.class_name,
                                        method_name=m_obj.method_name,
                                        method_signature=m_obj.method_signature,
                                        source_code=m_obj.raw_source,
                                        label=lbl,  # type: ignore[arg-type]
                                        label_source=lsrc,
                                        verification_status=vstat,
                                        bug_type=btype,
                                        bug_fix_reference=bug_ref,
                                        source_hash=sha256_text(m_obj.normalized_source or m_obj.raw_source),
                                        collection_timestamp=now_ts,
                                        dataset_version=dver,
                                        normalized_source=m_obj.normalized_source,
                                        structural_hash=m_obj.structural_hash,
                                        pair_id=pair_id,
                                        commit_timestamp=author_date,
                                        commit_message=msg.splitlines()[0] if msg else "",
                                        type_kind=m_obj.type_kind,
                                        start_line=m_obj.start_line,
                                        end_line=m_obj.end_line,
                                        is_constructor=m_obj.is_constructor,
                                        is_static=m_obj.is_static,
                                        is_async=m_obj.is_async,
                                        is_generic=m_obj.is_generic,
                                        is_expression_bodied=m_obj.is_expression_bodied,
                                        extraction_mode="file",
                                        source_origin="github_api_bugfix",
                                        stars=int(repo_info.get("stargazers_count", 0)),
                                        features_payload=_build_feature_payload(m_obj),
                                    )
                                )
                            repo_pairs += 1
        finally:
            if own_client:
                client.close()
        return samples, exclusions, repos_meta
