#!/usr/bin/env python3
"""Runs execution accuracy benchmarks on baseline or fine-tuned checkpoints."""

import sys
from pathlib import Path

# Add 1_Source to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cli.interface import cmd_eval
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Execution Benchmark")
    parser.add_argument("--run-name", type=str, default="baseline")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--adapter", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    sys.exit(cmd_eval(args))
