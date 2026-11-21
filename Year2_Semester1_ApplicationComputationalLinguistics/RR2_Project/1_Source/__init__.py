"""Agent-OM Local Replication Package — bridges to 1_Source/."""
from __future__ import annotations
from pathlib import Path

_SOURCE_DIR = Path(__file__).resolve().parent.parent / "1_Source"
if _SOURCE_DIR.is_dir() and str(_SOURCE_DIR) not in __path__:
    __path__.insert(0, str(_SOURCE_DIR))
