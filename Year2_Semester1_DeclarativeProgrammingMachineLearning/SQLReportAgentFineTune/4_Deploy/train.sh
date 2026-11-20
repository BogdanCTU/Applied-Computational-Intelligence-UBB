#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"
source .venv/bin/activate

RUN_NAME="${1:-full_lora_run}"
ITERS="${2:-600}"

echo "============================================================"
echo "  Executing LoRA Fine-Tuning: ${RUN_NAME} (${ITERS} iters)"
echo "============================================================"

python 1_Source/main.py train --run-name "${RUN_NAME}" --iters "${ITERS}"
