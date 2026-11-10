# Deployment and Operations Guide: Local Report SQL Agent

This guide provides end-to-end instructions for deploying, packaging, verifying, and operating the **Local Report SQL Agent** on macOS and Windows.

---

## 1. Common Prerequisites

The Local Report SQL Agent runs **100% locally and offline**. It requires no external cloud APIs, API keys, or remote subscriptions.

### 1.1 Python Environment
- **Supported Python Versions**: Python 3.10 to 3.13 (Python 3.13.16 is the certified reference version).
- **Virtual Environment**: A dedicated `.venv` in the repository root. Global package installation is strictly discouraged.

### 1.2 Local Ollama LLM Service
- **Installation**: Download and install Ollama from [ollama.com](https://ollama.com).
- **Service Endpoint**: `http://localhost:11434` (standard Ollama REST API).
- **Certified Model**: `qwen3.5:4b` (Qwen 2.5 / 3.5 4-Billion Parameter Model).
  ```bash
  # Pull the certified model
  ollama pull qwen3.5:4b
  ```
- **Model Verification**:
  ```bash
  ollama list
  # Output must show qwen3.5:4b
  ```

### 1.3 Python Dependencies
Defined in `1_Source/requirements.txt`:
| Package | Version Requirement | Purpose |
|:---|:---|:---|
| `PySide6` | `>=6.7,<6.10` | Qt6 GUI framework, widgets, threading, QtPdf document previewer |
| `mcp` | `>=1.9,<2` | Official Model Context Protocol SDK (FastMCP server & stdio client) |
| `httpx` | `>=0.27` | Asynchronous and synchronous HTTP client for local Ollama communication |
| `reportlab` | `>=4.2` | Enterprise PDF synthesis, Platypus flowables, LongTable, 22 vector charts |
| `pytest` | `>=8.0` | Test framework for unit, integration, and security test suites |
| `pytest-asyncio` | `>=0.23` | Asynchronous test execution for MCP tools and Ollama client |
| `pyinstaller` | `>=6.10` | Standalone binary bundling for desktop deployment |

### 1.4 Database and Resource Requirements
- **Primary Database**: `2_Database/ecommerce.db` (SQLite relational database with 7 tables and 499,385 records).
  - **Integrity Checksum (SHA-256)**:
    ```text
    c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934
    ```
  - **Security Rule**: The primary database is **strictly read-only and immutable**. It is opened using URI parameter `mode=ro` and guarded by a SQLite authorizer.
- **Agent Working Memory**: `2_Database/agent_memory.db` (managed by `SQLiteMemoryRepository` in WAL mode for task history, checkpoints, and execution logs).
- **Domain Skills**: Embedded in `1_Source/skills/` (`sql/`, `ecommerce/`, `analytics/`, `reporting/`).
- **Memory Migrations**: Located in `1_Source/memory/migrations/` (`001_initial_schema.sql`, `002_checkpoint_recovery.sql`, `003_skill_registry_enhancements.sql`).

---

## 2. macOS Deployment

### 2.1 System Requirements
- **Operating System**: macOS 12.0 (Monterey) or later (Apple Silicon M1/M2/M3/M4 or Intel x86_64).
- **Xcode Command Line Tools**: `xcode-select --install` (for Python compilation hooks if building from source).

### 2.2 Environment Setup & Verification
```bash
# 1. Clone or navigate to the repository root
cd /path/to/FinalProject_SQLAgent

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Verify packages and dependencies
pip install -r 1_Source/requirements.txt

# 4. Verify runtime environment and database integrity
python 1_Source/scripts/verify_environment.py
```
Expected output:
```text
== Local Report SQL Agent: environment verification ==
[ OK ] Python 3.13.16 (.../.venv/bin/python)
[ OK ] PySide6 6.10.3
[ OK ] mcp 1.30.0
[ OK ] httpx 0.28.1
[ OK ] reportlab 5.1.0
[ OK ] pytest 9.2.0
[ OK ] MCP SDK exposes FastMCP server + stdio client APIs
[ OK ] Ollama reachable at http://localhost:11434 (version 0.40.15)
[ OK ] Model 'qwen3.5:4b' is installed
[ OK ] Database ecommerce.db: 7 tables, 499,385 total records
[ OK ] SHA-256 integrity verified: c5a5965e000becdb...
== RESULT: PASS ==
```

### 2.3 Packaging with `1_Source/scripts/build_macos.sh`
The build script automates environment verification, testing, clean-up, PyInstaller bundling, and post-packaging smoke tests:

```bash
chmod +x 1_Source/scripts/build_macos.sh
./1_Source/scripts/build_macos.sh
```

#### Supported Build Options
| Option | Environment Variable | Behavior |
|:---|:---|:---|
| *(default)* | *none* | Executes environment check, 461 deterministic unit/integration tests, clean build, PyInstaller bundling, and Stage 5 smoke tests. |
| `--with-live-tests` | `RUN_LIVE_TESTS=1` | Runs the full test suite (463 tests), including the live Ollama workflow (`test_13_live_ollama_qwen_reporting_workflow`). |
| `--live-tests-only` | `LIVE_TESTS_ONLY=1` | Skips deterministic tests and executes only the live Ollama acceptance tests before packaging. |
| `--skip-tests` | `SKIP_TESTS=1` | Skips automated tests for rapid packaging iteration; **Stage 5 smoke tests are always executed**. |
| `-h`, `--help` | *none* | Displays usage information and options. |

### 2.4 Build Output Locations
Packaging produces outputs in `6_Builds/macOS/`:
1. **macOS Application Bundle**: `6_Builds/macOS/ReportSQLAgent.app` (native macOS double-clickable application).
2. **Standalone Directory**: `6_Builds/macOS/ReportSQLAgent/` (Mach-O executable and shared dynamic libraries).
3. **Build Logs**: `6_Builds/build_logs/build_macos.log`.

### 2.5 Launching the Application
```bash
# Method A: Launch via macOS GUI Finder / open command
open 6_Builds/macOS/ReportSQLAgent.app

# Method B: Launch directly via Terminal to observe stdout/stderr
./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent

# Method C: Launch directly from Python source (development mode)
python 1_Source/run_app.py
```

### 2.6 Packaged Smoke Test Verification
Stage 5 of `build_macos.sh` automatically executes these verifications:
1. **Child MCP Stdio Mode**: Verifies that invoking `ReportSQLAgent --mcp-server` returns JSON-RPC protocol initialization without initializing Qt.
   ```bash
   echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | ./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --mcp-server
   ```
2. **Resource Bundling**: Confirms `memory/migrations/001_initial_schema.sql` and `skills/sql/SKILL.md` exist inside `Contents/Resources` or `Contents/Frameworks`.
3. **Headless GUI Startup**:
   ```bash
   QT_QPA_PLATFORM=offscreen ./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --smoke-test
   ```

### 2.7 Common macOS Troubleshooting
- **Gatekeeper "App is damaged or cannot be opened"**:
  Local builds are self-signed. Strip quarantine attributes if needed:
  ```bash
  xattr -cr 6_Builds/macOS/ReportSQLAgent.app
  ```
- **Offscreen / Headless Display**:
  When running smoke tests in CI or headless environments without a display server, prefix with `QT_QPA_PLATFORM=offscreen`.
- **Font Substitution Warnings (`qt.qpa.fonts`)**:
  PySide6 may log informational warnings about font substitutions (e.g. `Populating font family aliases`). These are benign and do not affect rendering.

---

## 3. Windows Deployment

### 3.1 System Requirements
- **Operating System**: Windows 10 (64-bit) or Windows 11 (64-bit).
- **PowerShell**: PowerShell 5.1 (built into Windows) or PowerShell Core 7+.
- **C++ Runtime**: [Microsoft Visual C++ 2015-2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe).

### 3.2 Environment Setup & Verification
```powershell
# 1. Open PowerShell in the project directory
cd C:\path\to\FinalProject_SQLAgent

# 2. Allow script execution in current PowerShell session if restricted
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Create and activate virtual environment
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r 1_Source\requirements.txt

# 5. Verify environment and database
python 1_Source\scripts\verify_environment.py
```

### 3.3 Windows Packaging Procedure
Run the dedicated PowerShell build script:
```powershell
.\1_Source\scripts\build_windows.ps1
```
The script executes 5 automated stages:
1. Environment and database integrity verification (`1_Source\scripts\verify_environment.py --build`).
2. Automated test suite execution (461 deterministic tests).
3. Artifact clean-up (`6_Builds\build_tmp\` and `6_Builds\Windows\`).
4. PyInstaller bundling using `ReportSQLAgent.spec`.
5. Binary validation of `6_Builds\Windows\ReportSQLAgent\ReportSQLAgent.exe`.

### 3.4 Build Output Locations
- **Standalone Folder**: `6_Builds\Windows\ReportSQLAgent\`
- **Windows Executable**: `6_Builds\Windows\ReportSQLAgent\ReportSQLAgent.exe`
- **Build Logs**: `6_Builds\build_logs\build_windows.log`

### 3.5 Launching on Windows
```powershell
# Launch the standalone executable
.\6_Builds\Windows\ReportSQLAgent\ReportSQLAgent.exe

# Or run directly from Python source (development mode)
python 1_Source\run_app.py
```

### 3.6 Platform Verification Status
> [!NOTE]
> - **macOS Deployment**: Fully verified, bundled, and tested locally on macOS Darwin arm64 (`6_Builds/macOS/ReportSQLAgent.app`).
> - **Windows Deployment**: The build script `1_Source/scripts/build_windows.ps1` and the unified specification `ReportSQLAgent.spec` are designed and cross-platform aligned. However, runtime execution has not been validated on a physical Windows host in this macOS development environment.

### 3.7 Windows-Specific Troubleshooting
- **Missing `MSVCP140.dll` or `VCRUNTIME140.dll`**:
  Install the Microsoft Visual C++ Redistributable linked above.
- **Execution Policy Error (`PSSecurityException`)**:
  Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before invoking `.ps1` scripts.
- **Windows Defender / SmartScreen Alert**:
  Unsigned binaries trigger Windows SmartScreen. Click **More Info** -> **Run anyway**.

---

## 4. Troubleshooting and Diagnostics

### 4.1 Local Ollama Connection Failures
- **Symptom**: `Failed to connect to Ollama at http://localhost:11434`.
- **Cause**: The Ollama background service is not running.
- **Resolution**:
  ```bash
  # Check if Ollama is running
  curl http://localhost:11434/api/version
  # If not running, start the daemon
  ollama serve
  ```

### 4.2 Missing Model Error
- **Symptom**: `Model 'qwen3.5:4b' is NOT installed`.
- **Resolution**:
  ```bash
  ollama pull qwen3.5:4b
  ```

### 4.3 Child MCP Server Subprocess Failure
- **Symptom**: `Failed to initialize MCP client: connection timeout or exit`.
- **Diagnostic**: Test the child server directly:
  ```bash
  # In development mode:
  PYTHONPATH=1_Source python -m mcp_layer.server
  # In frozen mode:
  ./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --mcp-server
  ```
  The process should run silently, awaiting standard input JSON-RPC messages. Any crash trace indicates a missing dependency or corrupt environment.

### 4.4 Database Integrity Mismatch
- **Symptom**: `SHA-256 integrity check failed for ecommerce.db`.
- **Cause**: `2_Database/ecommerce.db` was accidentally modified or replaced.
- **Resolution**: Check the hash with `shasum -a 256 2_Database/ecommerce.db`. If corrupted, restore the pristine database file. Never run `UPDATE`, `INSERT`, or schema modifications on `2_Database/ecommerce.db`.

### 4.5 User Data Directory and Persistence
In frozen execution mode, PyInstaller runs from a read-only application directory. The application automatically redirects writable storage to the standard OS user data root:
- **macOS**: `~/Library/Application Support/ReportSQLAgent/`
- **Windows**: `%APPDATA%\ReportSQLAgent\`

Inside the user data directory:
- `2_Database/ecommerce.db`: Local writable template copy seeded on first launch.
- `2_Database/agent_memory.db`: Working memory SQLite database.
- `5_Reports/`: Default destination for generated PDF and CSV reports.
- `1_Source/logs/`: Application execution logs (`report_agent_app.log`, `report_agent_mcp_server.log`).

---

## 5. Summary of Verification Commands

| Action | Command | Expected Result |
|:---|:---|:---|
| Environment Check | `python 1_Source/scripts/verify_environment.py` | `== RESULT: PASS ==` (Exit code 0) |
| Deterministic Tests | `pytest 1_Source/tests/ -k "not test_live_local_ollama_integration_end_to_end and not test_13_live_ollama_qwen_reporting_workflow" -q` | `461 passed` in ~25s (Exit code 0) |
| Live Ollama Test | `pytest 1_Source/tests/test_mcp_tool_discovery_and_capability.py::test_13_live_ollama_qwen_reporting_workflow -v` | `1 passed` (Exit code 0) |
| macOS Build Pipeline | `./1_Source/scripts/build_macos.sh` | Stages 1–5 PASS, `6_Builds/macOS/ReportSQLAgent.app` built |
| Headless Smoke Test | `QT_QPA_PLATFORM=offscreen ./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --smoke-test` | Clean startup & exit code 0 |
| MCP Stdio Smoke Test | `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \| ./6_Builds/macOS/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --mcp-server` | JSON-RPC handshake returned |

