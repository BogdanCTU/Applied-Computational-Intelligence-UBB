"""Filesystem location helpers.

All paths are resolved relative to the application root or user data directory
so that no absolute paths are hardcoded:

* When running from source, the application root is the project directory
  (the folder containing ``settings.json`` and ``run_app.py``).
* When running as a PyInstaller executable:
  - Bundled read-only resources (database template, assets) live in ``resource_root()`` (sys._MEIPASS).
  - Mutable user data (custom settings, reports, logs, history) lives in ``user_data_root()``
    (e.g., ~/Library/Application Support/ReportSQLAgent on macOS, %APPDATA%/ReportSQLAgent on Windows).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_APP_ROOT = "REPORT_AGENT_HOME"


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Directory that holds source code and dev assets."""
    override = os.environ.get(ENV_APP_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        # macOS .app bundle: <App>.app/Contents/MacOS/<exe> -> use folder holding the .app
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            return exe_dir.parents[2]
        return exe_dir
    # config/paths.py -> project root is one level up
    return Path(__file__).resolve().parents[1]


def resource_root() -> Path:
    """Directory holding read-only bundled resources (e.g. bundled data/ecommerce.db)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return app_root()
    return app_root()


def user_data_root() -> Path:
    """Directory holding mutable user data (settings.json, reports/, logs/)."""
    override = os.environ.get(ENV_APP_ROOT)
    if override:
        p = Path(override).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if not is_frozen():
        return app_root()

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


def ensure_writable_database(
    rel_or_abs_path: str | os.PathLike[str] = "data/ecommerce.db",
) -> Path:
    """Ensure the SQLite database lives in a persistent, writable user data directory when frozen.

    When frozen:
      1. Absolute paths are respected as-is.
      2. If relative, destination is user_data_root() / rel_or_abs_path
         (e.g., ~/Library/Application Support/ReportSQLAgent/data/ecommerce.db on macOS,
          %APPDATA%/ReportSQLAgent/data/ecommerce.db on Windows).
      3. If the destination already exists, return it immediately (never overwrite user data).
      4. If destination does not exist, look for a bundled template in resource_root()
         or app_root(). If found, copy it to the user data directory.
      5. Ensure destination directory exists and return destination.

    When running from source (not frozen):
      Resolves against app_root() (or custom override).
    """
    p = Path(rel_or_abs_path).expanduser()
    if p.is_absolute():
        return p.resolve()

    if not is_frozen():
        return (app_root() / p).resolve()

    user_db_path = (user_data_root() / p).resolve()
    if user_db_path.exists():
        return user_db_path

    # First run in packaged mode: seed user database from bundled template if available
    user_db_path.parent.mkdir(parents=True, exist_ok=True)
    template_candidates = [
        resource_root() / p,
        app_root() / p,
    ]
    for candidate in template_candidates:
        if candidate.exists() and candidate.is_file():
            try:
                import shutil
                shutil.copy2(candidate, user_db_path)
                try:
                    os.chmod(user_db_path, 0o666)
                except OSError:
                    pass
                break
            except Exception:
                pass

    return user_db_path


def resolve_path(value: str | os.PathLike[str], base: Path | None = None) -> Path:
    """Resolve a (possibly relative) path against appropriate directory.

    When running from source:
      - Resolves against base or app_root().
    When running as a PyInstaller executable:
      - If an explicit base is provided, resolves against base.
      - If value is a database, delegates to ensure_writable_database.
      - Otherwise, resolves against user_data_root() for writable outputs (reports, logs).
    """
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()
    if base is not None:
        return (base / p).resolve()
    if is_frozen():
        if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            return ensure_writable_database(p)
        return (user_data_root() / p).resolve()
    return (app_root() / p).resolve()


def get_memory_database_path(
    rel_or_abs_path: str | os.PathLike[str] = "data/agent_memory.db",
) -> Path:
    """Resolve the location of the persistent agent memory database.

    Guarantees:
    - Stored in persistent, writable user data directory when packaged (macOS App Support, Windows %APPDATA%).
    - Stored in app root directory when running in development.
    - Ensures parent directories exist.
    """
    p = Path(rel_or_abs_path).expanduser()
    if p.is_absolute():
        dest = p.resolve()
    elif is_frozen():
        dest = (user_data_root() / p).resolve()
    else:
        dest = (app_root() / p).resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest
