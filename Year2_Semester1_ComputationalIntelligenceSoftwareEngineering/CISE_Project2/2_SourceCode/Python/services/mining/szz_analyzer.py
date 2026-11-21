"""SZZ (Śliwerski–Zimmermann–Zeller) algorithm implementation for C# repositories.
Traces modified/deleted lines from bug-fixing commits back to candidate Bug-Inducing Commits (BICs).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import git
from git.exc import GitCommandError

from database.repository import RepositoryDB
from utils.logger import setup_logger
from utils.source_classifier import is_production_csharp_file

logger = setup_logger("szz_analyzer")


class SZZAnalyzer:
    """Enhanced SZZ implementation with whitespace/comment filtering and cached line blame tracking."""

    DEFAULT_EXCLUSIONS = [
        re.compile(r"(?:^|/)(?:obj|bin|\.vs|packages)/", re.IGNORECASE),
        re.compile(r"\.(?:Designer|g|i|generated)\.cs$", re.IGNORECASE),
        re.compile(r"(?:Tests?|Specs?)\.cs$", re.IGNORECASE),
        re.compile(r"(?:^|/)(?:tests?|specs?|testing)/", re.IGNORECASE),
    ]

    SHA_LINE_RE = re.compile(r"^([0-9a-fA-F]{40})\s+\d+\s+(\d+)")

    def __init__(self, db: Optional[RepositoryDB] = None) -> None:
        self.db = db
        self._file_blame_cache: Dict[Tuple[str, str, str], Dict[int, str]] = {}

    def is_target_file(self, file_path: str, custom_exclusions: Optional[List[re.Pattern]] = None) -> bool:
        """Check if file is a non-test production C# source file."""
        if custom_exclusions:
            if not file_path.lower().endswith(".cs"):
                return False
            normalized = file_path.replace("\\", "/")
            return not any(pat.search(normalized) for pat in custom_exclusions)
        return is_production_csharp_file(file_path)

    def analyze_commit(
        self,
        repo: git.Repo,
        fixing_commit_sha: str,
        repository_id: int,
        max_files: Optional[int] = None,
        max_deleted_lines_per_file: Optional[int] = None,
        persist: bool = True,
        use_file_blame_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run SZZ on a specific fixing commit. Returns list of candidate BIC records."""
        try:
            fix_commit = repo.commit(fixing_commit_sha)
        except Exception as e:
            logger.error(f"Cannot resolve fixing commit {fixing_commit_sha}: {e}")
            return []

        if not fix_commit.parents:
            logger.debug(f"Commit {fixing_commit_sha[:8]} has no parents (root commit); skipping SZZ.")
            return []

        parent = fix_commit.parents[0]

        try:
            diffs = parent.diff(fix_commit, create_patch=True)
        except GitCommandError as e:
            logger.error(f"Failed to generate diff for {fixing_commit_sha[:8]}: {e}")
            return []

        bic_records: List[Dict[str, Any]] = []
        prod_diffs = []
        for diff in diffs:
            file_path = diff.b_path or diff.a_path
            if file_path and self.is_target_file(file_path):
                prod_diffs.append(diff)

        if max_files is not None:
            prod_diffs = prod_diffs[:max_files]

        for diff in prod_diffs:
            file_path = diff.b_path or diff.a_path
            parent_file_path = diff.a_path or file_path
            if not parent_file_path:
                continue

            try:
                patch_text = diff.diff.decode("utf-8", errors="replace")
            except Exception:
                patch_text = str(diff.diff)

            deleted_lines = self._extract_deleted_lines(patch_text)
            if not deleted_lines:
                continue
            if max_deleted_lines_per_file is not None:
                deleted_lines = deleted_lines[:max_deleted_lines_per_file]

            file_blame_map: Optional[Dict[int, str]] = None
            if use_file_blame_cache or len(deleted_lines) > 2:
                file_blame_map = self._blame_whole_file(repo, parent.hexsha, parent_file_path)

            for line_no, line_content in deleted_lines:
                if file_blame_map is not None:
                    bic_sha = file_blame_map.get(line_no)
                else:
                    bic_sha = self._blame_line(repo, parent.hexsha, parent_file_path, line_no)

                if not bic_sha or bic_sha == fix_commit.hexsha:
                    continue

                record = {
                    "repository_id": repository_id,
                    "fixing_commit_sha": fix_commit.hexsha,
                    "inducing_commit_sha": bic_sha,
                    "file_path": parent_file_path,
                    "deleted_line_number": line_no,
                    "deleted_line_content": line_content[:200],
                    "inducing_line_number": None,
                    "confidence": 0.85,
                    "evidence": f"Deleted in fix {fix_commit.hexsha[:8]}, blamed to {bic_sha[:8]}",
                }
                bic_records.append(record)
                if persist and self.db:
                    self.db.insert_szz_result(record)

        logger.info(f"SZZ analyzed fix {fixing_commit_sha[:8]}: discovered {len(bic_records)} BIC line traces.")
        return bic_records

    def _extract_deleted_lines(self, patch: str) -> List[Tuple[int, str]]:
        """Parse unified diff patch and extract 1-based line numbers of deleted non-trivial lines."""
        results: List[Tuple[int, str]] = []
        hunk_header_re = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

        current_old_line = 0
        in_hunk = False

        for line in patch.splitlines():
            hunk_match = hunk_header_re.match(line)
            if hunk_match:
                current_old_line = int(hunk_match.group(1))
                in_hunk = True
                continue

            if not in_hunk:
                continue

            if line.startswith("-") and not line.startswith("---"):
                content = line[1:]
                stripped = content.strip()
                is_comment = (
                    stripped.startswith("//")
                    or stripped.startswith("/*")
                    or stripped.startswith("*")
                    or stripped.startswith("///")
                )
                is_cosmetic = len(stripped) <= 1 and stripped in ("{", "}", ";", "")
                is_using = stripped.startswith("using ") and stripped.endswith(";")

                if not is_comment and not is_cosmetic and not is_using:
                    results.append((current_old_line, content))
                current_old_line += 1

            elif line.startswith("+") and not line.startswith("+++"):
                continue
            else:
                current_old_line += 1

        return results

    def _blame_whole_file(self, repo: git.Repo, commit_sha: str, file_path: str) -> Dict[int, str]:
        """Run git blame -w -M -C --line-porcelain once for an entire file and map line -> SHA."""
        repo_key = str(repo.working_tree_dir or "")
        cache_key = (repo_key, commit_sha, file_path)
        if cache_key in self._file_blame_cache:
            return self._file_blame_cache[cache_key]

        line_map: Dict[int, str] = {}
        try:
            proc = subprocess.run(
                [
                    "git", "-C", repo_key,
                    "blame", "-w", "-M", "-C", "--porcelain",
                    commit_sha, "--", file_path,
                ],
                capture_output=True,
                text=True,
                timeout=20,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0:
                for raw_line in proc.stdout.splitlines():
                    m = self.SHA_LINE_RE.match(raw_line)
                    if m:
                        sha, final_line = m.group(1), int(m.group(2))
                        line_map[final_line] = sha
        except Exception as e:
            logger.debug(f"Whole-file blame failed on {file_path} at {commit_sha[:8]}: {e}")

        if len(self._file_blame_cache) > 512:
            self._file_blame_cache.clear()
        self._file_blame_cache[cache_key] = line_map
        return line_map

    def _blame_line(self, repo: git.Repo, commit_sha: str, file_path: str, line_number: int) -> Optional[str]:
        """Execute git blame with -w -M -C and porcelain output for a single line."""
        try:
            blame_output = repo.git.blame(
                "-w", "-M", "-C",
                "--porcelain",
                "-L", f"{line_number},{line_number}",
                commit_sha,
                "--", file_path,
            )
            first_line = blame_output.splitlines()[0].strip()
            sha = first_line.split()[0]
            if len(sha) == 40 and re.match(r"^[0-9a-fA-F]{40}$", sha):
                return sha
        except GitCommandError as e:
            logger.debug(f"Blame failed on {file_path}:{line_number} at {commit_sha[:8]}: {e}")
        return None

    def run_repository_szz(
        self,
        repository_id: int,
        local_path: Path | str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        max_fixes: Optional[int] = None,
        max_files_per_fix: Optional[int] = None,
        max_deleted_lines_per_file: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run SZZ on bug-fixing commits in repository."""
        if not self.db:
            raise ValueError("RepositoryDB required.")

        repo = git.Repo(local_path)
        bug_commits = self.db.list_commits(repository_id=repository_id, bug_fix_only=True, limit=2000)
        bug_commits = [c for c in bug_commits if c.get("modifies_csharp", 1) == 1]
        bug_commits.sort(key=lambda c: float(c.get("bug_fix_confidence", 0.0)), reverse=True)
        if max_fixes is not None:
            bug_commits = bug_commits[:max_fixes]

        total_fixes = len(bug_commits)
        logger.info(f"Starting SZZ run for repo #{repository_id}: {total_fixes} bug-fixing commits to process.")

        all_traces: List[Dict[str, Any]] = []
        unique_bics: Set[str] = set()

        for idx, fix in enumerate(bug_commits):
            sha = fix["commit_sha"]
            traces = self.analyze_commit(
                repo,
                sha,
                repository_id,
                max_files=max_files_per_fix,
                max_deleted_lines_per_file=max_deleted_lines_per_file,
                persist=False,
                use_file_blame_cache=True,
            )
            all_traces.extend(traces)
            for t in traces:
                unique_bics.add(t["inducing_commit_sha"])

            if progress_callback and total_fixes > 0:
                pct = (idx + 1) / total_fixes
                progress_callback(f"SZZ analyzed {idx + 1}/{total_fixes} fixes ({len(all_traces)} traces found)...", pct)

        if all_traces:
            self.db.batch_insert_szz_results(all_traces)
        self.db.update_repository_metrics(repository_id, {"szz_traces_count": len(all_traces)})

        return {
            "total_fixing_commits": total_fixes,
            "total_bic_traces": len(all_traces),
            "unique_bug_inducing_commits": len(unique_bics),
        }
