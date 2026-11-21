"""Root runner for Seminar 4 Information Retrieval System (Part 1).

Usage:
    python run.py
"""

import sys
from pathlib import Path

# Add solution directories to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir / "1_Solution"))
sys.path.insert(0, str(root_dir / "1_Solution" / "src"))

from src.main import run_pipeline

if __name__ == "__main__":
    run_pipeline()
