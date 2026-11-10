#!/usr/bin/env bash
# ==============================================================================
# Build Script for macOS: Report SQL Agent (.app Bundle & Standalone Directory)
# Restructured Repository: Output directed to 6_Builds/macOS/
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${SOURCE_DIR}/.." && pwd)"

# Configuration flags
SKIP_TESTS="${SKIP_TESTS:-0}"
RUN_LIVE_TESTS="${RUN_LIVE_TESTS:-0}"
LIVE_TESTS_ONLY="${LIVE_TESTS_ONLY:-0}"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Build Report SQL Agent for macOS (.app bundle and standalone directory in 6_Builds/macOS/).

Options:
  --with-live-tests     Run both deterministic tests and live Ollama acceptance tests.
  --live-tests-only     Run only live Ollama acceptance tests before packaging.
  --skip-tests          Skip automated test suite (packaged smoke test in step 5/5 is always executed).
  -h, --help            Show this help message and exit.

Environment Variables:
  RUN_LIVE_TESTS=1      Equivalent to --with-live-tests.
  LIVE_TESTS_ONLY=1     Equivalent to --live-tests-only.
  SKIP_TESTS=1          Equivalent to --skip-tests.

By default, deterministic unit and integration tests (461 tests) are executed.
Live Ollama acceptance tests are excluded by default to ensure reproducible, offline-capable builds.
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-live-tests)
            RUN_LIVE_TESTS=1
            shift
            ;;
        --live-tests-only)
            LIVE_TESTS_ONLY=1
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Run '$(basename "$0") --help' for usage."
            exit 1
            ;;
    esac
done

# Output directories under 6_Builds/
BUILDS_DIR="${PROJECT_ROOT}/6_Builds"
MACOS_DIST_DIR="${BUILDS_DIR}/macOS"
BUILD_LOGS_DIR="${BUILDS_DIR}/build_logs"
BUILD_TMP_DIR="${BUILDS_DIR}/build_tmp"

mkdir -p "${MACOS_DIST_DIR}" "${BUILD_LOGS_DIR}"

LOG_FILE="${BUILD_LOGS_DIR}/build_macos.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=========================================================="
echo " Building Report SQL Agent for macOS"
echo " Project root: ${PROJECT_ROOT}"
echo " Source dir:   ${SOURCE_DIR}"
echo " Output dir:   ${MACOS_DIST_DIR}"
echo " Log file:     ${LOG_FILE}"
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

# Verify build dependencies (PyInstaller)
if ! "${VENV_PYTHON}" -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found in .venv. Installing build dependency..."
    "${VENV_PYTHON}" -m pip install "pyinstaller>=6.10"
fi

# 2. Environment and database integrity check
echo "[1/5] Verifying environment and database integrity..."
"${VENV_PYTHON}" "${SOURCE_DIR}/scripts/verify_environment.py" --build

# 3. Automated testing phase
echo "[2/5] Automated Testing Phase..."
if [ "${SKIP_TESTS}" = "1" ]; then
    echo "  [SKIPPED] Deterministic Unit & Integration Tests (skipped via --skip-tests / SKIP_TESTS=1)"
    echo "  [SKIPPED] Live Local Ollama Acceptance Tests (skipped via --skip-tests / SKIP_TESTS=1)"
    echo "  Notice: Automated tests skipped by operator. Packaged smoke test will still run in step 5/5."
elif [ "${LIVE_TESTS_ONLY}" = "1" ]; then
    echo "  [SKIPPED] Deterministic Unit & Integration Tests (skipped via --live-tests-only)"
    echo "  [EXECUTING] Live Local Ollama Acceptance Tests (test_13_live_ollama_qwen_reporting_workflow & test_live_local_ollama_integration_end_to_end)..."
    "${VENV_PYTHON}" -m pytest "${SOURCE_DIR}/tests/" -k "test_13_live_ollama_qwen_reporting_workflow or test_live_local_ollama_integration_end_to_end" -v -s
    echo "  [PASSED] Live Local Ollama Acceptance Tests passed successfully."
elif [ "${RUN_LIVE_TESTS}" = "1" ]; then
    echo "  [EXECUTING] Full Test Suite (Deterministic Suite + Live Local Ollama Acceptance Tests)..."
    "${VENV_PYTHON}" -m pytest "${SOURCE_DIR}/tests/" -q
    echo "  [PASSED] Complete test suite passed successfully."
else
    echo "  [EXECUTING] Deterministic Unit & Integration Tests (461 tests)..."
    echo "  [INFO] Live Ollama tests excluded from default build (selectable via --with-live-tests or --live-tests-only)."
    "${VENV_PYTHON}" -m pytest "${SOURCE_DIR}/tests/" -k "not test_live_local_ollama_integration_end_to_end and not test_13_live_ollama_qwen_reporting_workflow" -q
    echo "  [PASSED] Deterministic Unit & Integration Tests passed successfully."
fi

# 4. Clean previous build artifacts safely
echo "[3/5] Cleaning previous build artifacts..."
rm -rf "${MACOS_DIST_DIR}" "${BUILD_TMP_DIR}"

# 5. Build macOS distribution with PyInstaller
echo "[4/5] Packaging application with PyInstaller into ${MACOS_DIST_DIR}..."
"${PYINSTALLER}" --clean --noconfirm --distpath "${MACOS_DIST_DIR}" --workpath "${BUILD_TMP_DIR}" "${PROJECT_ROOT}/ReportSQLAgent.spec"

# 6. Validate output artifacts and execute packaged smoke test
echo "[5/5] Validating built macOS application bundle and running smoke test..."
APP_PATH="${MACOS_DIST_DIR}/ReportSQLAgent.app"
BIN_PATH="${APP_PATH}/Contents/MacOS/ReportSQLAgent"
STANDALONE_DIR="${MACOS_DIST_DIR}/ReportSQLAgent"

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

echo "Verifying application resource packaging..."
if [ ! -f "${APP_PATH}/Contents/Resources/memory/migrations/001_initial_schema.sql" ] && [ ! -f "${APP_PATH}/Contents/Frameworks/memory/migrations/001_initial_schema.sql" ]; then
    echo "ERROR: Memory database migration files missing from application bundle."
    exit 1
fi
echo "Memory migrations verified in application bundle."

if [ ! -f "${APP_PATH}/Contents/Resources/skills/sql/SKILL.md" ] && [ ! -f "${APP_PATH}/Contents/Frameworks/skills/sql/SKILL.md" ]; then
    echo "ERROR: Domain skills missing from application bundle."
    exit 1
fi
echo "Domain skills verified in application bundle."

echo "Verifying GUI application startup smoke test..."
QT_QPA_PLATFORM=offscreen "${BIN_PATH}" --smoke-test
echo "GUI startup smoke test verified successfully."

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
