#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"
source .venv/bin/activate

MODEL_ID="${1:-mlx-community/Qwen2.5-Coder-3B-Instruct-4bit}"

echo "============================================================"
echo "  Downloading Pretrained Model: ${MODEL_ID}"
echo "============================================================"

python 1_Source/main.py download --model "${MODEL_ID}"
