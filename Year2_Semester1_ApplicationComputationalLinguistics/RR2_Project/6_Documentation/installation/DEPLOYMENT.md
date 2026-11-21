# Deployment and Standalone Packaging Guide

## 1. Overview

The Agent-OM Desktop Workbench is packaged as a standalone `--onedir` desktop application using **PyInstaller (`6.22.3`)** and the specification file located at `packaging/agent_om.spec` (and root `agent_om.spec`).

### Packaging Design Principles
1. **Self-Contained Python & Qt6 Runtime:** Bundles the Python 3.13 interpreter, `PySide6` (`QtCore`, `QtGui`, `QtWidgets`), `matplotlib`, `rdflib`, `breame`, `pandas`, `numpy`, `psycopg2`, `pgvector`, `ollama`, and `langchain-ollama`.
2. **Zero Heavyweight Bloat:** Explicitly excludes `torch`, `tensorflow`, `scipy`, and `QtWebEngine` to keep startup fast and binary footprint minimal.
3. **External Local Services:** Does not bundle PostgreSQL database clusters or multi-gigabyte Ollama model weights inside the binary; connects cleanly to local loopback services (`127.0.0.1:5432` and `127.0.0.1:11434`).
4. **No Embedded Credentials:** Loads `.env` dynamically from the project root at runtime.

---

## 2. Building the Standalone Application

### On macOS (`arm64`):
```bash
rm -rf build dist
.venv/bin/python -m PyInstaller --noconfirm --clean packaging/agent_om.spec
```
This produces the standalone application directory at `dist/AgentOM/AgentOM`.

### On Windows 10/11 (`x86_64`):
```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build_exe.ps1
```
This produces `dist\AgentOM\AgentOM.exe` and the top-level convenience launcher `dist\AgentOM.exe`.

---

## 3. Verifying the Standalone Build (`--self-test`)

Always verify the compiled binary independently of the development IDE using the built-in offscreen self-test mode:

```bash
# macOS:
QT_QPA_PLATFORM=offscreen ./dist/AgentOM/AgentOM --self-test

# Windows:
.\dist\AgentOM\AgentOM.exe --self-test
```

### Expected Self-Test JSON Output
```json
{
  "is_frozen": true,
  "screens_verified": 10,
  "screen_names": [
    "1. Dashboard",
    "2. Environment Diagnostics",
    "3. Dataset Manager",
    "4. Configuration Profiles",
    "5. Replication Wizard (14 Stages)",
    "6. Pipeline Stage Inspector",
    "7. Original vs Local Comparison",
    "8. Evaluation & Charts",
    "9. Live Logs & Run History",
    "10. Report & Artifact Export"
  ],
  "postgresql_reachable": true,
  "ollama_reachable": true,
  "datasets_discovered": 1
}
```
