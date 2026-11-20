#!/usr/bin/env python3
"""Standalone script to acquire public benchmarks and build synthetic test suites."""

import sys
from pathlib import Path

# Add 1_Source to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cli.interface import cmd_data
import argparse

if __name__ == "__main__":
    sys.exit(cmd_data(argparse.Namespace()))
