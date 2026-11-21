"""Repository Manager for cloning, updating, and maintaining local Git repositories."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import git
from git.exc import GitCommandError, InvalidGitRepositoryError

from database.repository import RepositoryDB
from utils.logger import setup_logger

logger = setup_logger("repository_manager")


class RepositoryManagerError(Exception):
    """Base exception for repository management operations."""
    pass


class RepositoryManager:
    """Manages cloning, updating, and filesystem tracking for local Git repositories."""

    SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

    def __init__(self, base_storage_dir: Path, db: Optional[RepositoryDB] = None) -> None:
        self.base_storage_dir = Path(base_storage_dir)
        self.base_storage_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def sanitize_path_component(self, component: str) -> str:
        """Prevent path traversal and illegal filesystem characters."""
        cleaned = component.strip()
        if not cleaned or not self.SAFE_NAME_RE.match(cleaned) or ".." in cleaned:
            raise RepositoryManagerError(f"Unsafe repository name component: '{component}'")
        return cleaned

    def get_local_path(self, owner: str, name: str) -> Path:
        """Resolve safe local path: base_storage_dir / owner / name."""
        safe_owner = self.sanitize_path_component(owner)
        safe_name = self.sanitize_path_component(name)
        return self.base_storage_dir / safe_owner / safe_name

    def is_valid_cloned_repo(self, path: Path) -> bool:
        """Check whether directory exists and contains a valid Git repository."""
        if not path.exists() or not (path / ".git").exists():
            return False
        try:
            repo = git.Repo(path)
            _ = repo.head.commit
            return True
        except (InvalidGitRepositoryError, ValueError):
            return False

    @staticmethod
    def _cleanup_incomplete_dir(target_dir: Path) -> None:
        if not target_dir.exists():
            return
        try:
            shutil.rmtree(target_dir, ignore_errors=False)
        except Exception:
            def _handle_remove_readonly(func, path, exc):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(target_dir, onerror=_handle_remove_readonly)

    def clone_or_update(
        self,
        url: str,
        owner: str,
        name: str,
        default_branch: str = "main",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        skip_update_if_valid: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Clone repository with complete history or update if already present. Idempotent."""
        target_dir = self.get_local_path(owner, name)
        full_name = f"{owner}/{name}"

        if target_dir.exists() and not self.is_valid_cloned_repo(target_dir):
            logger.warning(f"Found incomplete clone at {target_dir}. Cleaning up...")
            self._cleanup_incomplete_dir(target_dir)

        if self.is_valid_cloned_repo(target_dir):
            if skip_update_if_valid:
                repo = git.Repo(target_dir)
                head_commit = repo.head.commit.hexsha
                if self.db:
                    repo_record = self.db.get_repository_by_full_name(full_name)
                    if repo_record:
                        self.db.update_repository_status(
                            repo_id=repo_record["id"],
                            status="cloned",
                            is_cloned=True,
                            local_path=str(target_dir),
                        )
                return {
                    "status": "cached",
                    "local_path": str(target_dir),
                    "head_commit": head_commit,
                    "is_cloned": True,
                }

            logger.info(f"Repository {full_name} already exists locally. Updating...")
            if progress_callback:
                progress_callback("Updating existing repository...", 0.3)
            res = self.update_repository(target_dir, default_branch=default_branch, progress_callback=progress_callback)
            if self.db:
                repo_record = self.db.get_repository_by_full_name(full_name)
                if repo_record:
                    self.db.update_repository_status(
                        repo_id=repo_record["id"],
                        status="updated",
                        is_cloned=True,
                        local_path=str(target_dir),
                    )
            return res

        logger.info(f"Cloning {full_name} from {url} into {target_dir} with FULL history...")
        if progress_callback:
            progress_callback(f"Cloning {full_name} (full history)...", 0.1)

        target_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            if timeout_seconds is not None and str(url).startswith(("http://", "https://", "git://")):
                env = dict(os.environ)
                env["GIT_TERMINAL_PROMPT"] = "0"
                proc = subprocess.run(
                    ["git", "clone", "--no-tags", url, str(target_dir)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    env=env,
                )
                if proc.returncode != 0:
                    raise GitCommandError(["git", "clone", url], proc.returncode, proc.stderr)
                repo = git.Repo(target_dir)
            else:
                # Full clone: never pass depth (depth=None default in GitPython)
                repo = git.Repo.clone_from(
                    url=url,
                    to_path=target_dir,
                    env={"GIT_TERMINAL_PROMPT": "0"},
                )

            head_commit = repo.head.commit.hexsha
            logger.info(f"Successfully cloned {full_name} (HEAD: {head_commit[:8]})")

            if progress_callback:
                progress_callback(f"Clone complete (HEAD: {head_commit[:8]})", 1.0)

            result = {
                "status": "cloned",
                "local_path": str(target_dir),
                "head_commit": head_commit,
                "is_cloned": True,
            }

            if self.db:
                repo_record = self.db.get_repository_by_full_name(full_name)
                if repo_record:
                    self.db.update_repository_status(
                        repo_id=repo_record["id"],
                        status="cloned",
                        is_cloned=True,
                        local_path=str(target_dir),
                    )

            return result

        except (GitCommandError, subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Git clone error for {full_name}: {e}")
            self._cleanup_incomplete_dir(target_dir)
            if self.db:
                repo_record = self.db.get_repository_by_full_name(full_name)
                if repo_record:
                    self.db.update_repository_status(
                        repo_record["id"],
                        status="failed",
                        processing_error=str(e)[:500],
                    )
            raise RepositoryManagerError(f"Git clone failed: {e}") from e

    def update_repository(
        self,
        local_path: Path,
        default_branch: str = "main",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Fetch latest changes from origin and fast-forward cleanly."""
        try:
            repo = git.Repo(local_path)
            if repo.is_dirty():
                raise RepositoryManagerError(
                    f"Repository at {local_path} contains uncommitted local changes. Update aborted to prevent data loss."
                )

            origin = repo.remotes.origin
            logger.info(f"Fetching from origin for {local_path}...")
            origin.fetch()

            current_branch = repo.active_branch.name if not repo.head.is_detached else None
            target_branch = default_branch if default_branch in repo.heads else (current_branch or "main")

            if target_branch in repo.heads:
                repo.heads[target_branch].checkout()
                origin.pull(target_branch)

            head_commit = repo.head.commit.hexsha
            logger.info(f"Successfully updated repository at {local_path} (HEAD: {head_commit[:8]})")

            if progress_callback:
                progress_callback(f"Update complete (HEAD: {head_commit[:8]})", 1.0)

            return {
                "status": "updated",
                "local_path": str(local_path),
                "head_commit": head_commit,
                "is_cloned": True,
            }

        except GitCommandError as e:
            logger.error(f"Git update failed for {local_path}: {e}")
            raise RepositoryManagerError(f"Git update failed: {e}") from e
