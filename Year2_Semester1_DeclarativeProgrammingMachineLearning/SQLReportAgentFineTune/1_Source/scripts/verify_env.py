#!/usr/bin/env python3
"""Standalone script to verify execution environment for Apple Silicon MLX."""

import sys
from pathlib import Path

# Add 1_Source to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cli.interface import cmd_verify
import argparse

if __name__ == "__main__":
    sys.exit(cmd_verify(argparse.Namespace()))
