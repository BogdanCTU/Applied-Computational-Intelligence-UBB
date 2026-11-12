"""Commit Collector for extracting commit history and file diffs from local repositories."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import git
from git.exc import GitCommandError, InvalidGitRepositoryError

from src.database.repository import RepositoryDB
from src.utils.logger import setup_logger

logger = setup_logger("commit_collector")


class CommitCollectorError(Exception):
    """Base exception for commit extraction failures."""
    pass


class CommitCollector:
    """Extracts commit metadata and file changes from a local Git repository."""

    def __init__(self, db: RepositoryDB) -> None:
        self.db = db

    def extract_and_persist(
        self,
        repository_id: int,
        local_path: Path | str,
        max_commits: Optional[int] = None,
        batch_size: int = 100,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Extract commits incrementally and persist to SQLite in batches."""
        path = Path(local_path)
        if not path.exists():
            raise CommitCollectorError(f"Local repository path does not exist: {path}")

        try:
            repo = git.Repo(path)
        except (InvalidGitRepositoryError, Exception) as e:
            raise CommitCollectorError(f"Invalid Git repository at {path}: {e}") from e

        # Incremental check: fetch already recorded SHAs
        existing_shas = self.db.get_commit_shas_for_repository(repository_id)
        logger.info(f"Repository #{repository_id} has {len(existing_shas)} existing commits in database.")

        # Traverse commits in topological/reverse-chronological order
        try:
            # Iterating all commits reachable from HEAD
            all_commits = list(repo.iter_commits())
        except GitCommandError as e:
            raise CommitCollectorError(f"Failed to read commit log: {e}") from e

        total_repo_commits = len(all_commits)
        commits_to_process = [c for c in all_commits if c.hexsha not in existing_shas]
        if max_commits:
            commits_to_process = commits_to_process[:max_commits]

        total_to_process = len(commits_to_process)
        logger.info(f"Processing {total_to_process} new commits out of {total_repo_commits} total.")

        if total_to_process == 0:
            if progress_callback:
                progress_callback("All commits are already synchronized.", 1.0)
            now_iso = datetime.now(timezone.utc).isoformat()
            self.db.update_repository_status(repository_id, status="synced", last_sync_at=now_iso)
            return {
                "total_in_repo": total_repo_commits,
                "already_present": len(existing_shas),
                "new_extracted": 0,
            }

        extracted_count = 0
        batch_commits: List[Dict[str, Any]] = []
        batch_files: List[tuple[int, List[Dict[str, Any]]]] = []

        for idx, commit in enumerate(commits_to_process):
            commit_data, file_changes = self._parse_commit(repository_id, commit)
            batch_commits.append(commit_data)
            batch_files.append((0, file_changes)) # placeholder for commit_id

            if len(batch_commits) >= batch_size or idx == total_to_process - 1:
                # Persist batch
                for i, c_data in enumerate(batch_commits):
                    cid = self.db.upsert_commit(c_data)
                    files = batch_files[i][1]
                    if files:
                        self.db.insert_commit_files(cid, files)
                    extracted_count += 1

                batch_commits.clear()
                batch_files.clear()

                progress = (idx + 1) / total_to_process
                msg = f"Extracted {idx + 1}/{total_to_process} commits ({progress * 100:.1f}%)"
                logger.debug(msg)
                if progress_callback:
                    progress_callback(msg, progress)

        # Update repository sync time
        now_iso = datetime.now(timezone.utc).isoformat()
        self.db.update_repository_status(repository_id, status="synced", is_cloned=True, last_sync_at=now_iso)

        logger.info(f"Successfully extracted and persisted {extracted_count} commits for repo #{repository_id}.")
        return {
            "total_in_repo": total_repo_commits,
            "already_present": len(existing_shas),
            "new_extracted": extracted_count,
        }

    def _parse_commit(self, repository_id: int, commit: git.Commit) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extract metadata and file modifications from a single Git commit."""
        parent_shas = [p.hexsha for p in commit.parents]
        primary_parent = parent_shas[0] if parent_shas else None

        # Author & committer timestamps (handle timezone safely)
        try:
            author_date = commit.authored_datetime.isoformat()
        except Exception:
            author_date = str(commit.authored_date)

        try:
            committer_date = commit.committed_datetime.isoformat()
        except Exception:
            committer_date = str(commit.committed_date)

        # Extract file stats
        files_data: List[Dict[str, Any]] = []
        modifies_csharp = False
        total_insertions = 0
        total_deletions = 0

        try:
            stats = commit.stats
            total_insertions = stats.total.get("insertions", 0)
            total_deletions = stats.total.get("deletions", 0)
            file_stats = stats.files

            # Map change types via git diff
            change_types: Dict[str, str] = {}
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                for d in diffs:
                    path = d.b_path or d.a_path
                    if path:
                        change_types[path] = d.change_type or "M"
            else:
                # Root commit: all files added
                for fpath in file_stats.keys():
                    change_types[fpath] = "A"

            for file_path, stat in file_stats.items():
                is_cs = file_path.lower().endswith(".cs")
                if is_cs:
                    modifies_csharp = True
                files_data.append({
                    "file_path": file_path,
                    "change_type": change_types.get(file_path, "M"),
                    "insertions": stat.get("insertions", 0),
                    "deletions": stat.get("deletions", 0),
                    "is_csharp": is_cs,
                })
        except Exception as e:
            logger.debug(f"Could not compute fine-grained diff for commit {commit.hexsha[:8]}: {e}")

        commit_record = {
            "repository_id": repository_id,
            "commit_sha": commit.hexsha,
            "parent_sha": primary_parent,
            "parent_shas": ",".join(parent_shas),
            "author_name": commit.author.name or "Unknown",
            "author_email": commit.author.email or "unknown@example.com",
            "committed_date": author_date,
            "committer_date": committer_date,
            "message": commit.message.strip(),
            "files_changed_count": len(files_data),
            "insertions": total_insertions,
            "deletions": total_deletions,
            "modifies_csharp": 1 if modifies_csharp else 0,
            "is_bug_fix": 0,
            "bug_fix_confidence": 0.0,
            "bug_fix_evidence": None,
        }

        return commit_record, files_data

