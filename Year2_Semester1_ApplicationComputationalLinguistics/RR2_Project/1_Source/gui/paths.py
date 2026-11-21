"""Workspace and packaged-executable path resolution helpers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Canonical paths resolved identically in Python source and PyInstaller frozen modes."""

    is_frozen: bool
    project_root: Path
    workspace_root: Path
    original_repo_dir: Path
    output_dir: Path
    replication_runs_dir: Path
    exports_dir: Path
    docs_dir: Path
    venv_upstream_python: Path


def resolve_project_paths() -> ProjectPaths:
    """Locate `agent_om_local/` and `original_repo/` whether running from source or `dist/` `.exe`."""
    is_frozen = bool(getattr(sys, "frozen", False))
    env_override = os.environ.get("AGENT_OM_PROJECT_ROOT")

    candidates: list[Path] = []
    if env_override:
        candidates.append(Path(env_override).resolve())

    if is_frozen:
        exe_dir = Path(sys.executable).resolve().parent
        # Supports dist/AgentOM/AgentOM.exe (parent.parent) and dist/AgentOM.exe (parent)
        candidates.extend([exe_dir.parent.parent, exe_dir.parent, exe_dir])
    else:
        # 1_Source/gui/paths.py or src/gui/paths.py -> parents[2] is project_root
        candidates.append(Path(__file__).resolve().parents[2])

    cwd = Path.cwd().resolve()
    candidates.extend([cwd, cwd / "agent_om_local"])

    project_root: Path | None = None
    for cand in candidates:
        if (
            (cand / "1_Source").is_dir()
            or (cand / "src").is_dir()
            or (cand / "output").is_dir()
            or cand.name == "agent_om_local"
        ):
            project_root = cand
            break

    if project_root is None:
        project_root = candidates[0]

    workspace_root = project_root.parent
    original_repo_dir = workspace_root / "original_repo"
    if not original_repo_dir.is_dir() and (project_root / "original_repo").is_dir():
        original_repo_dir = project_root / "original_repo"
    output_dir = project_root / "output"
    replication_runs_dir = output_dir / "replication_runs"
    exports_dir = replication_runs_dir / "exports"
    docs_dir = project_root / "6_Documentation"
    if not docs_dir.is_dir():
        docs_dir = project_root / "docs"
    if not docs_dir.is_dir() and (project_root / "1_Documents" / "2_Project").is_dir():
        docs_dir = project_root / "1_Documents" / "2_Project"
    venv_upstream_python = project_root / ".venv_upstream" / "Scripts" / "python.exe"
    if not venv_upstream_python.is_file() and (project_root / ".venv_upstream" / "bin" / "python").is_file():
        venv_upstream_python = project_root / ".venv_upstream" / "bin" / "python"

    return ProjectPaths(
        is_frozen=is_frozen,
        project_root=project_root,
        workspace_root=workspace_root,
        original_repo_dir=original_repo_dir,
        output_dir=output_dir,
        replication_runs_dir=replication_runs_dir,
        exports_dir=exports_dir,
        docs_dir=docs_dir,
        venv_upstream_python=venv_upstream_python,
    )

