#!/usr/bin/env python3
"""Executes quick pilot LoRA training (10 iterations) to verify pipeline end-to-end."""

import sys
from pathlib import Path

# Add 1_Source to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cli.interface import cmd_train
import argparse

if __name__ == "__main__":
    args = argparse.Namespace(
        model=None,
        run_name="pilot_verification_v1",
        pilot=True,
        iters=10,
        batch_size=2,
        lr=1e-4,
    )
    sys.exit(cmd_train(args))
