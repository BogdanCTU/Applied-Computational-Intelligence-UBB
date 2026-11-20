"""Agent-OM Local Replication Package — bridges to 1_Source/."""
from __future__ import annotations
import sys
from pathlib import Path

_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "1_Source",
]
if getattr(sys, "_MEIPASS", None):
    _CANDIDATES.insert(0, Path(sys._MEIPASS) / "1_Source")

for _source_dir in _CANDIDATES:
    if _source_dir.is_dir() and str(_source_dir) not in __path__:
        __path__.insert(0, str(_source_dir))
