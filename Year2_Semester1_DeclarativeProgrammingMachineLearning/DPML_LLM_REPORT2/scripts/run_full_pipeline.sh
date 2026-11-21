#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"$PYTHON_BIN" -m source.cli check-environment
"$PYTHON_BIN" -m source.cli generate-tests
"$PYTHON_BIN" -m source.cli run-baseline
"$PYTHON_BIN" -m source.cli analyze-baseline
"$PYTHON_BIN" -m source.cli generate-mitigation-data
"$PYTHON_BIN" -m source.cli train
"$PYTHON_BIN" -m source.cli run-mitigated
"$PYTHON_BIN" -m source.cli compare
"$PYTHON_BIN" -m source.cli report
"$PYTHON_BIN" -m pytest 6_Tests/ --cov=4_Source --cov-report=term-missing
