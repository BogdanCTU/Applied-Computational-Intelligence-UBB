#!/usr/bin/env bash
# Automated macOS Build Script for Bank Marketing Classifier
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Prefer the project virtual environment
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
else
    echo "❌ Error: Python 3 not found. Please activate your virtual environment."
    exit 1
fi

echo "Using Python: $($PYTHON_EXEC --version) ($PYTHON_EXEC)"
exec "$PYTHON_EXEC" "$PROJECT_ROOT/build_mac.py" "$@"
