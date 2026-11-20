"""Main entrypoint for SQLReportAgentFineTune."""

import sys
from pathlib import Path

# Add 1_Source to sys.path so app package is discoverable
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from app.cli.interface import run_cli

if __name__ == "__main__":
    sys.exit(run_cli())
