#!/usr/bin/env bash
set -euo pipefail

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "============================================================"
echo "  Setting up SQLReportAgentFineTune Laboratory"
echo "============================================================"

cd "${ROOT_DIR}"

# Ensure Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with Python 3.13..."
    python3.13 -m venv .venv || python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

echo "Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Verifying environment..."
python 1_Source/scripts/verify_env.py

echo "Environment successfully configured."
