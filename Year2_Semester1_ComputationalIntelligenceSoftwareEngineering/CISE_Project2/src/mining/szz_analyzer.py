"""SZZ (Śliwerski–Zimmermann–Zeller) algorithm implementation for C# repositories.
Traces modified/deleted lines from bug-fixing commits back to candidate Bug-Inducing Commits (BICs).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import git
from git.exc import GitCommandError

from src.database.repository import RepositoryDB
from src.utils.logger import setup_logger
from src.utils.source_classifier import is_production_csharp_file

logger = setup_logger("szz_analyzer")


class SZZAnalyzer:
    """Enhanced SZZ implementation with whitespace/comment filtering and blame tracking."""

    # Default exclusion patterns for test files, generated files, and build artifacts
    DEFAULT_EXCLUSIONS = [
        re.compile(r"(?:^|/)(?:obj|bin|\.vs|packages)/", re.IGNORECASE),
        re.compile(r"\.(?:Designer|g|i|generated)\.cs$", re.IGNORECASE),
        re.compile(r"(?:Tests?|Specs?)\.cs$", re.IGNORECASE),
        re.compile(r"(?:^|/)(?:tests?|specs?|testing)/", re.IGNORECASE),
    ]

    def __init__(self, db: Optional[RepositoryDB] = None) -> None:
        self.db = db

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

        # Parent-selection strategy: For merge commits, use mainline parent (parents[0])
        # This isolates the changes integrated into the target branch by the fix.
        parent = fix_commit.parents[0]

        try:
            diffs = parent.diff(fix_commit, create_patch=True)
        except GitCommandError as e:
            logger.error(f"Failed to generate diff for {fixing_commit_sha[:8]}: {e}")
            return []

        bic_records: List[Dict[str, Any]] = []

        for diff in diffs:
            file_path = diff.b_path or diff.a_path
            if not file_path or not self.is_target_file(file_path):
                continue

            # Deleted or modified files exist in parent
            parent_file_path = diff.a_path or file_path
            try:
                patch_text = diff.diff.decode("utf-8", errors="replace")
            except Exception:
                patch_text = str(diff.diff)

            deleted_lines = self._extract_deleted_lines(patch_text)
            if not deleted_lines:
                continue

            for line_no, line_content in deleted_lines:
                bic_sha = self._blame_line(repo, parent.hexsha, parent_file_path, line_no)
                if not bic_sha or bic_sha == fix_commit.hexsha:
                    continue  # Self-referencing or unblamable

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
                if self.db:
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
                # SZZ filtering: Ignore whitespace-only, comment-only, and closing braces
                stripped = content.strip()
                is_comment = stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")
                is_cosmetic = len(stripped) <= 1 and stripped in ("{", "}", ";", "")

                if not is_comment and not is_cosmetic:
                    results.append((current_old_line, content))
                current_old_line += 1

            elif line.startswith("+") and not line.startswith("+++"):
                # Added line in fix: does not advance old parent line counter
                continue
            else:
                # Context line (space prefix or unchanged): advances old line counter
                current_old_line += 1

        return results

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
            # First line of porcelain blame is '<40_char_sha> <orig_line> <final_line>'
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
    ) -> Dict[str, Any]:
        """Run SZZ on all confirmed or high-confidence bug-fixing commits in repository."""
        if not self.db:
            raise ValueError("RepositoryDB required.")

        repo = git.Repo(local_path)
        bug_commits = self.db.list_commits(repository_id=repository_id, bug_fix_only=True)

        total_fixes = len(bug_commits)
        logger.info(f"Starting SZZ run for repo #{repository_id}: {total_fixes} bug-fixing commits to process.")

        total_bic_traces = 0
        unique_bics: Set[str] = set()

        for idx, fix in enumerate(bug_commits):
            sha = fix["commit_sha"]
            traces = self.analyze_commit(repo, sha, repository_id)
            total_bic_traces += len(traces)
            for t in traces:
                unique_bics.add(t["inducing_commit_sha"])

            if progress_callback and total_fixes > 0:
                pct = (idx + 1) / total_fixes
                progress_callback(f"SZZ analyzed {idx + 1}/{total_fixes} fixes ({total_bic_traces} traces found)...", pct)

        return {
            "total_fixing_commits": total_fixes,
            "total_bic_traces": total_bic_traces,
            "unique_bug_inducing_commits": len(unique_bics),
        }

