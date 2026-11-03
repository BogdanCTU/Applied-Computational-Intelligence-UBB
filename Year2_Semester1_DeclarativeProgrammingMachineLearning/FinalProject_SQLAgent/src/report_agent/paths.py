"""Filesystem location helpers.

All paths are resolved relative to the *application root* so that no absolute
paths are hardcoded:

* When running from source, the application root is the project directory
  (the folder containing ``settings.json`` and ``src/``).
* When running as a PyInstaller executable, the application root is the folder
  containing the executable. The database, ``output/`` and ``logs/`` live next
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
    """Directory that holds settings.json, data/, output/ and logs/."""
    override = os.environ.get(ENV_APP_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # src/report_agent/paths.py -> project root is three levels up
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    """Directory holding read-only bundled resources (icons, default settings)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return Path(__file__).resolve().parent / "resources"


def resolve_path(value: str | os.PathLike[str], base: Path | None = None) -> Path:
    """Resolve a (possibly relative) path against the application root."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = (base or app_root()) / p
    return p.resolve()
