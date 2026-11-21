"""Commit Collector for extracting commit history and file diffs from local repositories."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple
import git
from git.exc import GitCommandError, InvalidGitRepositoryError

from database.repository import RepositoryDB
from utils.logger import setup_logger

logger = setup_logger("commit_collector")


class CommitCollectorError(Exception):
    """Base exception for commit extraction failures."""
    pass


class CommitCollector:
    """Extracts commit metadata and file changes from a local Git repository."""

    COMMIT_HEADER_PREFIX = "__CISE_COMMIT__|"

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

        existing_shas = self.db.get_commit_shas_for_repository(repository_id)
        logger.info(f"Repository #{repository_id} has {len(existing_shas)} existing commits in database.")

        try:
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
        batch_items: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []

        for idx, commit in enumerate(commits_to_process):
            commit_data, file_changes = self._parse_commit(repository_id, commit)
            batch_items.append((commit_data, file_changes))

            if len(batch_items) >= batch_size or idx == total_to_process - 1:
                extracted_count += self.db.batch_insert_commits_with_files(batch_items)
                batch_items.clear()

                progress = (idx + 1) / total_to_process
                msg = f"Extracted {idx + 1}/{total_to_process} commits ({progress * 100:.1f}%)"
                logger.debug(msg)
                if progress_callback:
                    progress_callback(msg, progress)

        now_iso = datetime.now(timezone.utc).isoformat()
        self.db.update_repository_status(repository_id, status="synced", is_cloned=True, last_sync_at=now_iso)

        logger.info(f"Successfully extracted and persisted {extracted_count} commits for repo #{repository_id}.")
        return {
            "total_in_repo": total_repo_commits,
            "already_present": len(existing_shas),
            "new_extracted": extracted_count,
        }

    def extract_and_persist_fast(
        self,
        repository_id: int,
        local_path: Path | str,
        max_commits: int = 250,
    ) -> Dict[str, Any]:
        """High-throughput commit mining using a single `git log --numstat` subprocess and batch SQLite commit."""
        path = Path(local_path)
        if not path.exists():
            raise CommitCollectorError(f"Local repository path does not exist: {path}")

        existing_shas = self.db.get_commit_shas_for_repository(repository_id)

        fmt = f"{self.COMMIT_HEADER_PREFIX}%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%B%x1e"
        cmd = ["git", "-C", str(path), "log", f"-n{max_commits}", "--numstat", f"--format={fmt}"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
            if proc.returncode != 0:
                raise CommitCollectorError(f"git log failed: {proc.stderr}")
        except subprocess.TimeoutExpired as e:
            raise CommitCollectorError(f"git log timed out: {e}") from e

        parsed_items: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
        blocks = proc.stdout.split(self.COMMIT_HEADER_PREFIX)
        total_seen = 0

        for block in blocks:
            if not block.strip() or "\x1e" not in block:
                continue
            header_part, stats_part = block.split("\x1e", 1)
            fields = header_part.split("\x1f")
            if len(fields) < 7:
                continue

            total_seen += 1
            sha, parents_raw, author_name, author_email, a_date, c_date, msg = fields[:7]
            sha = sha.strip()
            if not sha or sha in existing_shas:
                continue

            parent_list = [p for p in parents_raw.strip().split() if p]
            primary_parent = parent_list[0] if parent_list else None

            files_data: List[Dict[str, Any]] = []
            total_ins = 0
            total_del = 0
            modifies_csharp = False

            for stat_line in stats_part.splitlines():
                stat_line = stat_line.strip()
                if not stat_line:
                    continue
                parts = stat_line.split("\t")
                if len(parts) < 3:
                    continue
                ins_str, del_str, fpath = parts[0], parts[1], parts[-1]
                # Handle rename notation like 'src/{Old.cs => New.cs}'
                if "=>" in fpath and "{" in fpath and "}" in fpath:
                    prefix, rest = fpath.split("{", 1)
                    inside, suffix = rest.split("}", 1)
                    new_part = inside.split("=>", 1)[-1].strip()
                    fpath = f"{prefix}{new_part}{suffix}".replace("//", "/")
                elif " => " in fpath:
                    fpath = fpath.split(" => ", 1)[-1].strip()

                ins = int(ins_str) if ins_str.isdigit() else 0
                dels = int(del_str) if del_str.isdigit() else 0
                total_ins += ins
                total_del += dels
                is_cs = fpath.lower().endswith(".cs")
                if is_cs:
                    modifies_csharp = True
                files_data.append({
                    "file_path": fpath,
                    "change_type": "M",
                    "insertions": ins,
                    "deletions": dels,
                    "is_csharp": is_cs,
                })

            commit_record = {
                "repository_id": repository_id,
                "commit_sha": sha,
                "parent_sha": primary_parent,
                "parent_shas": ",".join(parent_list),
                "author_name": author_name.strip() or "Unknown",
                "author_email": author_email.strip() or "unknown@example.com",
                "committed_date": a_date.strip(),
                "committer_date": c_date.strip(),
                "message": msg.strip(),
                "files_changed_count": len(files_data),
                "insertions": total_ins,
                "deletions": total_del,
                "modifies_csharp": 1 if modifies_csharp else 0,
                "is_bug_fix": 0,
                "bug_fix_confidence": 0.0,
                "bug_fix_evidence": None,
            }
            parsed_items.append((commit_record, files_data))

        new_extracted = self.db.batch_insert_commits_with_files(parsed_items)
        now_iso = datetime.now(timezone.utc).isoformat()
        self.db.update_repository_status(repository_id, status="synced", is_cloned=True, last_sync_at=now_iso)
        self.db.update_repository_metrics(repository_id, {"commits_mined_count": len(existing_shas) + new_extracted})

        return {
            "total_in_repo": total_seen,
            "already_present": len(existing_shas),
            "new_extracted": new_extracted,
        }

    def _parse_commit(self, repository_id: int, commit: git.Commit) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extract metadata and file modifications from a single Git commit."""
        parent_shas = [p.hexsha for p in commit.parents]
        primary_parent = parent_shas[0] if parent_shas else None

        try:
            author_date = commit.authored_datetime.isoformat()
        except Exception:
            author_date = str(commit.authored_date)

        try:
            committer_date = commit.committed_datetime.isoformat()
        except Exception:
            committer_date = str(commit.committed_date)

        files_data: List[Dict[str, Any]] = []
        modifies_csharp = False
        total_insertions = 0
        total_deletions = 0

        try:
            stats = commit.stats
            total_insertions = stats.total.get("insertions", 0)
            total_deletions = stats.total.get("deletions", 0)
            file_stats = stats.files

            change_types: Dict[str, str] = {}
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                for d in diffs:
                    path = d.b_path or d.a_path
                    if path:
                        change_types[path] = d.change_type or "M"
            else:
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
