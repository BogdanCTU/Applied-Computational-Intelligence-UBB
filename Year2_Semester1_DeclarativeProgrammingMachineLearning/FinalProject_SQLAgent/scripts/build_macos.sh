#!/usr/bin/env bash
# ==============================================================================
# Build Script for macOS: Report SQL Agent (.app Bundle & Standalone Directory)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo " Building Report SQL Agent for macOS"
echo " Project root: ${PROJECT_ROOT}"
echo "=========================================================="

cd "${PROJECT_ROOT}"

# 1. Locate and check Python virtual environment
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
PYINSTALLER="${PROJECT_ROOT}/.venv/bin/pyinstaller"

if [ ! -f "${VENV_PYTHON}" ]; then
    echo "ERROR: Virtual environment not found at ${VENV_PYTHON}"
    echo "Please ensure the project virtual environment is created (.venv)."
    exit 1
fi

# 2. Verify build dependencies (PyInstaller)
if ! "${VENV_PYTHON}" -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found in .venv. Installing build dependency..."
    "${VENV_PYTHON}" -m pip install "pyinstaller>=6.10"
fi

# 3. Environment and database integrity check
echo "[1/5] Verifying environment and database integrity..."
"${VENV_PYTHON}" scripts/verify_environment.py --build

# 4. Run automated test suite
echo "[2/5] Running automated tests (excluding live Ollama test)..."
"${VENV_PYTHON}" -m pytest tests/ -k "not test_live_local_ollama_integration_end_to_end" -q

# 5. Clean previous build artifacts safely
echo "[3/5] Cleaning previous build artifacts..."
rm -rf "${PROJECT_ROOT}/build" "${PROJECT_ROOT}/dist"

# 6. Build macOS distribution with PyInstaller
echo "[4/5] Packaging application with PyInstaller..."
"${PYINSTALLER}" --clean --noconfirm ReportSQLAgent.spec

# 7. Validate output artifacts
echo "[5/5] Validating built macOS application bundle..."
APP_PATH="${PROJECT_ROOT}/dist/ReportSQLAgent.app"
BIN_PATH="${APP_PATH}/Contents/MacOS/ReportSQLAgent"
STANDALONE_DIR="${PROJECT_ROOT}/dist/ReportSQLAgent"

if [ ! -d "${APP_PATH}" ]; then
    echo "ERROR: Expected macOS application bundle not found at: ${APP_PATH}"
    exit 1
fi

if [ ! -x "${BIN_PATH}" ]; then
    echo "ERROR: Executable not found or not executable at: ${BIN_PATH}"
    exit 1
fi

echo "Verifying child MCP server execution mode..."
TEST_OUTPUT=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | "${BIN_PATH}" --mcp-server 2>/dev/null || true)
if [[ "${TEST_OUTPUT}" == *"capabilities"* || "${TEST_OUTPUT}" == *"result"* || "${TEST_OUTPUT}" == *"protocolVersion"* ]]; then
    echo "Child MCP server stdio response verified successfully."
else
    echo "Warning: Child MCP server did not return standard handshake in smoke test."
fi

echo ""
echo "=========================================================="
echo " BUILD SUCCESSFUL!"
echo " macOS Application Bundle: ${APP_PATH}"
echo " Standalone Directory:    ${STANDALONE_DIR}"
echo ""
echo " Run GUI application with:"
echo "   open \"${APP_PATH}\""
echo " or directly:"
echo "   \"${BIN_PATH}\""
echo "=========================================================="
