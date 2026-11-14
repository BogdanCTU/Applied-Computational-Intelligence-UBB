"""Streamlit Main Application Entrypoint (Root Launcher).
Provides the root entrypoint and delegates to 2_SourceCode/Python/app.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add 2_SourceCode/Python to sys.path so modules resolve seamlessly
_root = Path(__file__).resolve().parent
_source_python = _root / "2_SourceCode" / "Python"

if str(_source_python) not in sys.path:
    sys.path.insert(0, str(_source_python))

# Execute the application
import app as _app_module

if __name__ == "__main__":
    _app_module.main()
