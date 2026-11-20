#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"
source .venv/bin/activate

echo "============================================================"
echo "  Preparing Datasets and SQLite Evaluation Databases"
echo "============================================================"

python 1_Source/main.py data
