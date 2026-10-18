"""Make `src` importable and put the numbered part-folders on sys.path for all tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import src.config  # noqa: E402,F401  (its import adds the numbered folders to sys.path)
