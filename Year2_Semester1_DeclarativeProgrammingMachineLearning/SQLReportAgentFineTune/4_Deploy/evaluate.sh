#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"
source .venv/bin/activate

RUN_NAME="${1:-baseline}"
ADAPTER="${2:-}"

echo "============================================================"
echo "  Evaluating Model Performance: ${RUN_NAME}"
echo "============================================================"

if [ -n "${ADAPTER}" ]; then
    python 1_Source/main.py eval --run-name "${RUN_NAME}" --adapter "${ADAPTER}"
else
    python 1_Source/main.py eval --run-name "${RUN_NAME}"
fi
