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


def resolve_path(value: str | os.PathLike[str], base: Path | None = None) -> Path:
    """Resolve a (possibly relative) path against appropriate directory.

    When frozen:
    1. If `value` exists in resource_root() (such as data/ecommerce.db), return that.
    2. Otherwise, resolve against user_data_root() (for reports, logs, settings).
    When running from source, resolves against app_root().
    """
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()
    if base is not None:
        return (base / p).resolve()
    if is_frozen():
        bundled = resource_root() / p
        if bundled.exists():
            return bundled.resolve()
        next_to_app = app_root() / p
        if next_to_app.exists():
            return next_to_app.resolve()
        return (user_data_root() / p).resolve()
    return (app_root() / p).resolve()
