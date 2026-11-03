"""Filesystem location helpers.

All paths are resolved relative to the *application root* so that no absolute
paths are hardcoded:

* When running from source, the application root is the project directory
  (the folder containing ``settings.json`` and ``main.py``).
* When running as a PyInstaller executable, the application root is the folder
  containing the executable. The database, ``reports/`` and ``logs/`` live next
  to the executable, never inside it.
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
    """Directory that holds settings.json, data/, reports/ and logs/."""
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
    """Directory holding read-only bundled resources (icons, default settings)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return app_root()


def resolve_path(value: str | os.PathLike[str], base: Path | None = None) -> Path:
    """Resolve a (possibly relative) path against the application root."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = (base or app_root()) / p
    return p.resolve()

