"""Filesystem location helpers for the restructured repository.

All paths are resolved relative to the project root, source root, or user data directory
so that no absolute paths are hardcoded:

* When running from source:
  - Project root: FinalProject_SQLAgent (parents[2] from 1_Source/config/paths.py)
  - Source root: FinalProject_SQLAgent/1_Source
  - Database root: FinalProject_SQLAgent/2_Database
  - Documentation root: FinalProject_SQLAgent/3_Documentation
  - Presentation root: FinalProject_SQLAgent/4_Presentation
  - Reports root: FinalProject_SQLAgent/5_Reports/generated
  - Builds root: FinalProject_SQLAgent/6_Builds
* When running as a PyInstaller executable:
  - Bundled read-only resources (database template, assets, skills, migrations) live in resource_root() (sys._MEIPASS).
  - Mutable user data (custom settings, reports, logs, history, user database) lives in user_data_root()
    (e.g., ~/Library/Application Support/ReportSQLAgent on macOS, %APPDATA%/ReportSQLAgent on Windows).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ENV_APP_ROOT = "REPORT_AGENT_HOME"


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Top-level directory holding the restructured solution (1_Source, 2_Database, etc.)."""
    override = os.environ.get(ENV_APP_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        # macOS .app bundle: <App>.app/Contents/MacOS/<exe> -> parent directory holding .app
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            return exe_dir.parents[2]
        return exe_dir
    # 1_Source/config/paths.py -> project root is two levels up
    return Path(__file__).resolve().parents[2]


def source_root() -> Path:
    """Directory holding Python source code and developer packages (1_Source)."""
    if is_frozen():
        return resource_root()
    return project_root() / "1_Source"


def app_root() -> Path:
    """Backward-compatible alias for source_root()."""
    return source_root()


def resource_root() -> Path:
    """Directory holding read-only bundled resources (e.g. bundled 2_Database/ecommerce.db)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return project_root()
    return project_root()


def user_data_root() -> Path:
    """Directory holding mutable user data (settings.json, reports/, logs/, user databases)."""
    override = os.environ.get(ENV_APP_ROOT)
    if override:
        p = Path(override).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if not is_frozen():
        return project_root()

    if sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "ReportSQLAgent"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        path = (
            Path(appdata) / "ReportSQLAgent"
            if appdata
            else Path.home() / "AppData" / "Roaming" / "ReportSQLAgent"
        )
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        path = (
            Path(xdg) / "ReportSQLAgent"
            if xdg
            else Path.home() / ".local" / "share" / "ReportSQLAgent"
        )

    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_relative_asset_path(raw_path: str | os.PathLike[str]) -> Path:
    """Map legacy paths ('data/ecommerce.db', 'reports', 'logs') to new target directory structure."""
    p = Path(raw_path)
    posix_str = p.as_posix()

    if posix_str.startswith("data/"):
        return Path("2_Database") / Path(*p.parts[1:])
    if posix_str == "data":
        return Path("2_Database")

    if posix_str == "reports" or posix_str == "reports/":
        return Path("5_Reports/generated")
    if posix_str == "reports/report_history.json":
        return Path("5_Reports/report_history.json")
    if posix_str.startswith("reports/"):
        return Path("5_Reports/generated") / Path(*p.parts[1:])

    if posix_str == "logs" or posix_str == "logs/":
        return Path("1_Source/logs")
    if posix_str.startswith("logs/"):
        return Path("1_Source/logs") / Path(*p.parts[1:])

    return p


def ensure_writable_database(
    rel_or_abs_path: str | os.PathLike[str] = "2_Database/ecommerce.db",
) -> Path:
    """Ensure the SQLite database lives in a persistent, readable/writable directory.

    When running from source (development):
      Resolves against project_root() / 2_Database/ecommerce.db.
    When frozen:
      Seeds database into user_data_root() / 2_Database/ecommerce.db from bundled template.
    """
    p = Path(rel_or_abs_path).expanduser()
    if p.is_absolute():
        return p.resolve()

    norm_path = _normalize_relative_asset_path(p)

    if not is_frozen():
        cand = (project_root() / norm_path).resolve()
        if cand.exists():
            return cand
        # Fallback if accessed relative to source root
        cand_src = (source_root() / norm_path).resolve()
        if cand_src.exists():
            return cand_src
        return cand

    user_db_path = (user_data_root() / norm_path).resolve()
    if user_db_path.exists():
        return user_db_path

    # First run in packaged mode: seed user database from bundled template
    user_db_path.parent.mkdir(parents=True, exist_ok=True)
    template_candidates = [
        resource_root() / norm_path,
        resource_root() / p,
        resource_root() / "2_Database" / "ecommerce.db",
        resource_root() / "data" / "ecommerce.db",
        project_root() / norm_path,
    ]
    for candidate in template_candidates:
        if candidate.exists() and candidate.is_file():
            try:
                shutil.copy2(candidate, user_db_path)
                try:
                    os.chmod(user_db_path, 0o666)
                except OSError:
                    pass
                break
            except Exception:
                pass

    return user_db_path


def get_memory_database_path(
    rel_or_abs_path: str | os.PathLike[str] | None = "2_Database/agent_memory.db",
) -> Path:
    """Resolve the location of the persistent agent memory database.

    Guarantees:
    - Stored in persistent, writable user data directory when packaged (macOS App Support, Windows %APPDATA%).
    - Stored in 2_Database/agent_memory.db when running in development.
    - Ensures parent directories exist.
    """
    target = rel_or_abs_path or "2_Database/agent_memory.db"
    p = Path(target).expanduser()
    if p.is_absolute():
        dest = p.resolve()
    else:
        norm_path = _normalize_relative_asset_path(p)
        if is_frozen():
            dest = (user_data_root() / norm_path).resolve()
        else:
            dest = (project_root() / norm_path).resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def resolve_path(value: str | os.PathLike[str], base: Path | None = None) -> Path:
    """Resolve a (possibly relative) path against the appropriate directory."""
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()
    if base is not None:
        return (base / p).resolve()

    norm_path = _normalize_relative_asset_path(p)

    if is_frozen():
        if norm_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            return ensure_writable_database(norm_path)
        return (user_data_root() / norm_path).resolve()

    # In development mode: resolve against project_root
    dest = (project_root() / norm_path).resolve()
    if dest.exists():
        return dest
    # If not found at project_root, try resolving against source_root
    dest_src = (source_root() / norm_path).resolve()
    if dest_src.exists():
        return dest_src
    return dest
