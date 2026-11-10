# Build and Packaging Guide: Report SQL Agent

This document provides complete instructions for building, packaging, and distributing **Report SQL Agent** as a standalone, native desktop application on **Windows** and **macOS** using **PyInstaller**.

---

## 1. Overview and Architecture

Report SQL Agent is a native Python desktop application featuring:
- **PySide6 (Qt6)** graphical interface with embedded **QtPdf** previewer.
- **FastMCP Stdio Server** as an isolated background subprocess providing database tools.
- **ReportLab PDF Engine** generating dynamic, multi-page business intelligence reports.
- **Local SQLite Database** (`ecommerce.db`) with read-only transaction guardrails.
- **Local Ollama Integration** (`qwen3.5:4b`) executing private, offline LLM inference.

### Frozen Execution Architecture

When packaged with PyInstaller into a standalone executable, the application operates in **frozen mode** (`getattr(sys, "frozen", False) == True`):

```
+-------------------------------------------------------------------------+
| ReportSQLAgent Executable / App Bundle                                  |
|                                                                         |
|  +--------------------------------+   Stdio JSON-RPC (sys.executable)  |
|  | Main Process: PySide6 GUI      | <---------------------------------> |
|  | - QtPdf Document Viewer        |     --mcp-server flag               |
|  | - Chat Assistant Panel         |                                     |
|  | - Agent Orchestrator           |  +--------------------------------+ |
|  | - Ollama HTTP Client           |  | Child Process: FastMCP Server  | |
|  +--------------------------------+  | - inspect_database_schema      | |
|                 |                    | - execute_read_only_query      | |
|                 v                    | - generate_kpi_metrics         | |
|  +--------------------------------+  | - generate_chart_specifications| |
|  | ReportLab PDF Engine           |  | - generate_table_view          | |
|  +--------------------------------+  +--------------------------------+ |
+-------------------------------------------------------------------------+
       |                                              |
       v                                              v
+-------------------------------+             +---------------------------+
| Local Ollama Daemon           |             | User Data Directory       |
| http://localhost:11434        |             | (Persistent SQLite,       |
| Model: qwen3.5:4b             |             |  reports/, logs/)         |
+-------------------------------+             +---------------------------+
```

1. **Dual-Mode Binary**: PyInstaller bundles the entire application into a single executable. At runtime, `sys.executable` points to `ReportSQLAgent.exe` (Windows) or `ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent` (macOS).
2. **Child MCP Server**: The main process launches its child MCP server by invoking `sys.executable --mcp-server`. In `app/main.py`, the CLI flag `--mcp-server` immediately routes control to `mcp_layer.server:run_stdio_server()` **without initializing Qt or loading any GUI dependencies**, keeping stdout and stderr clean for JSON-RPC stdio communication.
3. **User Data Isolation & Database Safety**:
   - In PyInstaller, the bundle root (`_MEIPASS` or `Contents/Frameworks`) is read-only or ephemeral.
   - The verified database template (`data/ecommerce.db`) bundled inside the application is **never modified directly**.
   - On first launch, `config.paths.ensure_writable_database()` seeds the SQLite database into the OS user data directory:
     - **Windows**: `%APPDATA%\ReportSQLAgent\data\ecommerce.db`
     - **macOS**: `~/Library/Application Support/ReportSQLAgent/data/ecommerce.db`
   - Generated PDF reports (`reports/`) and session logs (`logs/`) are also stored in the user data directory, ensuring all writes succeed and user data persists between runs.
4. **Local Ollama Independence**: Ollama and LLM model weights are **not bundled** into the PyInstaller artifact. Users run Ollama locally as an independent service on `localhost:11434`.

---

## 2. Prerequisites

### Windows 10/11
- **Python**: Version 3.10 to 3.13 (64-bit recommended).
- **PowerShell**: Version 5.1 or PowerShell Core 7+.
- **Virtual Environment**: `.venv` created in the project root with dependencies installed:
  ```powershell
  py -3.13 -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
  ```

### macOS (Apple Silicon & Intel)
- **macOS**: Version 12.0 (Monterey) or later.
- **Python**: Version 3.10 to 3.13.
- **Virtual Environment**: `.venv` created in the project root with dependencies installed:
  ```bash
  python3 -m venv .venv
  ./.venv/bin/pip install -r requirements.txt
  ```

---

## 3. Quick Start: One-Command Build

### Building on macOS

Run the dedicated build script from the repository root:

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

**Build Artifacts Created**:
- **Application Bundle**: `dist/ReportSQLAgent.app`
- **Standalone Directory**: `dist/ReportSQLAgent/`

**Running the Built macOS App**:
```bash
# Launch the macOS App Bundle
open dist/ReportSQLAgent.app

# Or execute directly via terminal to see stdout/stderr:
./dist/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent
```

---

### Building on Windows

Run the dedicated PowerShell build script from the repository root:

```powershell
.\scripts\build_windows.ps1
```

> [!TIP]
> If PowerShell blocks script execution with `PSSecurityException`, allow execution for your current session:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\scripts\build_windows.ps1
> ```

**Build Artifacts Created**:
- **Distribution Directory**: `dist\ReportSQLAgent\`
- **Standalone Executable**: `dist\ReportSQLAgent\ReportSQLAgent.exe`

**Running the Built Windows App**:
```powershell
.\dist\ReportSQLAgent\ReportSQLAgent.exe
```

---

## 4. Build Pipeline Stages

Both `scripts/build_macos.sh` and `scripts/build_windows.ps1` execute the following 5 automated stages:

| Stage | Name | Description |
|:---|:---|:---|
| **[1/5]** | **Environment Verification** | Runs `scripts/verify_environment.py --build` to confirm Python version compatibility, package dependencies (`PySide6`, `reportlab`, `mcp`, `httpx`, `pydantic`), and SQLite database file presence. |
| **[2/5]** | **Automated Test Suite** | Runs `pytest tests/ -k "not test_live_local_ollama_integration_end_to_end" -q` to guarantee 100% of offline unit, integration, and reporting pipeline tests (456 tests) pass before packaging. |
| **[3/5]** | **Clean Artifacts** | Safely deletes stale `build/` and `dist/` folders to ensure a reproducible, clean build. |
| **[4/5]** | **PyInstaller Packaging** | Executes PyInstaller against `ReportSQLAgent.spec` with optimizations and hidden imports. |
| **[5/5]** | **Output Validation** | Validates the output binaries, checks file permissions, and runs a live smoke test against `--mcp-server` to verify stdio JSON-RPC initialization. |

---

## 5. PyInstaller Specification Details (`ReportSQLAgent.spec`)

The project uses a unified specification file (`ReportSQLAgent.spec`) that handles both Windows and macOS packaging.

### Key Configurations

- **Entry Point**: `run_app.py`
- **Explicit Hidden Imports**:
  - `PySide6.QtPdf` & `PySide6.QtPdfWidgets` (Qt PDF rendering widgets).
  - `anyio._backends._asyncio` (required for FastMCP stdio client async loop).
  - `httpx`, `httpcore` (Ollama REST communication).
  - `pydantic`, `pydantic_core` (FastMCP schema parsing and type validation).
  - `reportlab.platypus`, `reportlab.graphics`, `reportlab.pdfgen` (PDF synthesis).
  - Dynamic discovery of `app.*`, `agent.*`, `mcp_layer.*`, `reporting.*`, `database.*`, and `config.*`.
- **Bundled Data**:
  - ReportLab standard fonts and metrics (`reportlab`).
  - MCP schema definitions (`mcp`).
  - SQLite database template (`data/ecommerce.db`).
  - Configuration template (`.env.example`).
- **Excluded Modules**:
  - Unused heavy packages are excluded to keep bundle sizes lean and startup fast: `tkinter`, `matplotlib`, `scipy`, `numpy`, `pandas`, `IPython`, `jupyter`, `pytest`.
- **UPX Compression**:
  - Disabled (`upx=False`) to avoid corrupting Qt6 and macOS Mach-O/ARM64 code signatures and dynamic libraries.

---

## 6. Distribution and Deployment

### Distributing to End Users

To distribute Report SQL Agent to end users who do not have Python installed:

#### Windows Distribution
1. Package the entire `dist\ReportSQLAgent\` folder (e.g., zip as `ReportSQLAgent-Windows.zip`).
2. Instruct the user to extract the zip file and double-click `ReportSQLAgent.exe`.
3. Ensure Ollama is installed and running (`ollama run qwen3.5:4b`).

#### macOS Distribution
1. Distribute `dist/ReportSQLAgent.app` directly or package it in a `.dmg` disk image.
2. Ensure Ollama is installed and running (`ollama run qwen3.5:4b`).

---

## 7. Troubleshooting

### Windows Issues

1. **PowerShell Script Policy Error**:
   - *Error*: `...cannot be loaded because running scripts is disabled on this system.`
   - *Fix*: Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before invoking the script.
2. **Missing MSVCP140.dll or Visual C++ Runtime**:
   - *Fix*: Ensure the end user has installed the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).
3. **Windows Defender / SmartScreen Alert**:
   - *Cause*: The executable is unsigned.
   - *Fix*: Click *More info* -> *Run anyway*. For enterprise production releases, sign the binary using `signtool.exe` with a valid Authenticode certificate.

### macOS Issues

1. **Gatekeeper / App Cannot Be Opened**:
   - *Cause*: The application is built locally and is not notarized by Apple.
   - *Fix*: Right-click `ReportSQLAgent.app` and choose *Open*, then click *Open* in the dialog. Alternatively, remove quarantine flags:
     ```bash
     xattr -cr dist/ReportSQLAgent.app
     ```
2. **Ollama Connection Warning**:
   - *Cause*: Ollama service is not running locally.
   - *Fix*: Start Ollama from the terminal or menu bar app:
     ```bash
     ollama serve
     ollama pull qwen3.5:4b
     ```
3. **Resetting User Database**:
   - To restore the default database state:
     - On Windows, delete `%APPDATA%\ReportSQLAgent\data\ecommerce.db`.
     - On macOS, delete `~/Library/Application Support/ReportSQLAgent/data/ecommerce.db`.
   - On the next launch, Report SQL Agent will re-seed the pristine database from its internal template.

