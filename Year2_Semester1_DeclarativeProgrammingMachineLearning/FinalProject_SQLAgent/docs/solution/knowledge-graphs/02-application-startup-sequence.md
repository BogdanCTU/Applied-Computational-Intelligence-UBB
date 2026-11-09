# Knowledge Graph 02 — Application Startup Sequence

## 1. End-to-End Application Initialization Sequence

```mermaid
sequenceDiagram
    autonumber
    participant User as OS / User
    participant Entry as run_app.py
    participant Main as app/main.py
    participant Cfg as config/settings.py & paths.py
    participant Log as config/logging_setup.py
    participant Qt as PySide6 QApplication
    participant MW as app/main_window.py (MainWindow)
    participant Orch as agent/orchestrator.py
    participant Mem as memory/repository.py
    participant Skill as agent/skill_manager.py
    participant CheckW as app/workers/agent_worker.py (OllamaCheckWorker)
    participant Ollama as Local Ollama (127.0.0.1:11434)

    User->>Entry: Execute python run_app.py (or ReportSQLAgent binary)
    Entry->>Main: main(sys.argv)

    alt Child MCP Server Subprocess ("--mcp-server" in sys.argv)
        Main->>Main: mcp_layer.server.run_stdio_server()
    else Desktop GUI Process
        Note over Main,Log: Stage 1: Configuration, Path Resolution & Rotating Logging
        Main->>Cfg: load_settings() (Defaults -> settings.json -> REPORT_AGENT_*)
        Cfg->>Cfg: AppSettings.validate() (Loopback, Context Window, Page Size)
        Cfg-->>Main: AppSettings instance
        Main->>Log: setup_logging(settings, process_name="app")
        Log-->>Main: logs/report_agent_app.log
        Main->>Main: _install_global_exception_handler(log_file_path)

        Note over Main,Qt: Stages 2 & 3: Qt Application & Dark Theme Stylesheet
        Main->>Qt: QApplication(args)
        Main->>Qt: app.setStyleSheet(APP_STYLESHEET)

        Note over Main,Skill: Stage 4: MainWindow, AgentOrchestrator, Memory Migrations & Skills
        Main->>MW: MainWindow(settings)
        MW->>Orch: AgentOrchestrator(settings)
        Orch->>Mem: SQLiteMemoryRepository()
        Mem->>Mem: Verify db_path != data/ecommerce.db
        Mem->>Mem: PRAGMA journal_mode = WAL & apply_migrations(001, 002, 003)
        Orch->>Skill: SkillManager.discover_skills() (sql, data_analysis, data_validation)
        Orch->>Mem: upsert_skill_metadata() for all valid skills
        Orch->>Orch: CheckpointManager.detect_interrupted_tasks()
        MW->>MW: _init_ui() (Header, QSplitter, ReportPreviewWidget, ChatView)
        MW->>MW: _connect_signals()
        MW->>CheckW: QTimer.singleShot(100ms, _check_ollama_status)

        opt "--smoke-test" in sys.argv
            Main->>MW: window.close()
            Main-->>User: Exit 0
        end

        Note over Main,Ollama: Stage 5: Show Window & Asynchronous Ollama Health Check
        Main->>MW: window.show()
        Main->>Qt: app.exec()
        CheckW->>Ollama: GET /api/version & GET /api/tags
        Ollama-->>CheckW: Version + Installed Model List
        CheckW-->>MW: signals.check_completed.emit(is_online, version, models)
        MW->>MW: _on_ollama_status_checked() -> Update status_pill
    end
```

The sequence diagram above captures every startup interaction from process launch (`run_app.py`) through `AppSettings.validate()`, `SQLiteMemoryRepository` schema migrations, `SkillManager` discovery, and the non-blocking `OllamaCheckWorker` health check.

---

## 2. Startup Invariants and Guarantees

1. **Zero UI Blocking on Startup**: `MainWindow.__init__()` schedules `_check_ollama_status()` via `QTimer.singleShot(100, ...)` on `OllamaCheckWorker` (`QThread`), and defers MCP subprocess spawn (`AgentOrchestrator.initialize()`) until the first `process_message()` call on `AgentWorker`. As a result, the desktop window appears in `< 300 ms` even if Ollama is offline.
2. **Early Crash Persistence**: If an unhandled exception occurs before `setup_logging()` finishes, `run_app.py:_fallback_log_fatal(exc)` writes the traceback to `user_data_root() / "logs" / "startup_crash.log"`.
3. **Database Separation Check at Boot**: `SQLiteMemoryRepository.__init__()` immediately verifies that the writable `agent_memory.db` path does not point to `data/ecommerce.db` before opening any SQLite connection.
