"""Root Streamlit entrypoint for CISE Project v5.0.0."""

from __future__ import annotations

import sys
from pathlib import Path

_source_dir = Path(__file__).resolve().parent / "2_SourceCode"
if str(_source_dir) not in sys.path:
    sys.path.insert(0, str(_source_dir))

from gui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
