# Knowledge Graph 10 — Cross-Platform Deployment and Packaging

## 1. Build, Packaging, and Runtime Path Resolution Graph

```mermaid
flowchart TB
    subgraph BuildPipeline["1. Automated Build Pipeline (scripts/build_macos.sh & build_windows.ps1)"]
        S1["Step 1: scripts/verify_environment.py --build<br/>• Check Python 3.13 & required packages<br/>• Verify FastMCP + stdio_client APIs<br/>• Verify data/ecommerce.db SHA-256"]
        S2["Step 2: Run Automated Test Suite<br/>pytest tests/ -k 'not live'"]
        S3["Step 3: Clean build/ and dist/"]
        S4["Step 4: pyinstaller --clean --noconfirm ReportSQLAgent.spec"]
        S5["Step 5: Post-Build Smoke Validation<br/>• Test binary --mcp-server stdio handshake<br/>• Verify bundled migrations & skills<br/>• Run QT_QPA_PLATFORM=offscreen binary --smoke-test"]
        S1 --> S2 --> S3 --> S4 --> S5
    end

    subgraph Artifacts["2. Generated Distribution Artifacts"]
        MacApp["macOS Application Bundle:<br/>dist/ReportSQLAgent.app<br/>(Contents/MacOS/ReportSQLAgent)"]
        WinExe["Windows Standalone Directory:<br/>dist\\ReportSQLAgent\\ReportSQLAgent.exe"]
    end

    subgraph RuntimeRouting["3. Runtime Path Routing in Frozen Mode (config/paths.py)"]
        FrozenCheck{"is_frozen()<br/>(sys.frozen == True)"}
        ReadOnly["resource_root() -> sys._MEIPASS<br/>• memory/migrations/001..003.sql<br/>• skills/sql, data_analysis, data_validation<br/>• data/ecommerce.db (Read-Only URI mode=ro)"]
        Mutable["user_data_root()<br/>macOS: ~/Library/Application Support/ReportSQLAgent/<br/>Windows: %APPDATA%\\ReportSQLAgent\\<br/>• settings.json<br/>• data/agent_memory.db (WAL mode)<br/>• reports/*.pdf, *.csv, report_history.json<br/>• logs/report_agent_app.log & mcp_server.log"]
        DualBin["MCP Subprocess Spawn:<br/>sys.executable --mcp-server<br/>-> app.main:main() -> run_stdio_server()"]
    end

    S4 --> MacApp & WinExe
    MacApp & WinExe --> FrozenCheck
    FrozenCheck --> ReadOnly
    FrozenCheck --> Mutable
    FrozenCheck --> DualBin
```

The deployment graph above connects the 5-step build scripts (`build_macos.sh`, `build_windows.ps1`), the generated platform bundles (`ReportSQLAgent.app`, `ReportSQLAgent.exe`), and the runtime path routing in `config/paths.py`.

---

## 2. macOS `.app` Bundle vs. Windows Standalone Directory Structure

| Component | macOS (`dist/ReportSQLAgent.app`) | Windows (`dist\ReportSQLAgent\`) |
| :--- | :--- | :--- |
| **Primary Executable** | `Contents/MacOS/ReportSQLAgent` | `ReportSQLAgent.exe` |
| **MCP Child Server Command** | `Contents/MacOS/ReportSQLAgent --mcp-server` | `ReportSQLAgent.exe --mcp-server` |
| **Bundled Read-Only Assets (`sys._MEIPASS`)** | `Contents/Resources/` & `Contents/Frameworks/` (`memory/migrations/*.sql`, `skills/*`, `data/ecommerce.db`) | `_internal\` (`memory\migrations\*.sql`, `skills\*`, `data\ecommerce.db`) |
| **Writable User Data Root** | `~/Library/Application Support/ReportSQLAgent/` | `%APPDATA%\ReportSQLAgent\` |

