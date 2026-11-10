# macOS App Startup Fix & Bundle Verification Report

**Project**: Local Report SQL Agent  
**Target Platform**: macOS (Apple Silicon / Darwin arm64)  
**Deliverable**: `docs/MACOS_STARTUP_FIX_REPORT.md`  
**Date**: November 8, 2026  
**Status**: Verified & Operational  

---

## 1. Executive Summary

When running `./scripts/build_macos.sh`, the build process completed and generated `dist/ReportSQLAgent.app`. However, attempting to open the packaged application from macOS Finder (`open dist/ReportSQLAgent.app`) or directly executing the binary from Terminal (`./dist/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent`) resulted in an immediate, silent process termination with no graphical window or user-facing error message. In addition, the build logs emitted an extraneous PyInstaller warning:
```text
Error: typer is required. Install with 'pip install mcp[cli]'
```

Through root-cause diagnosis, multiple contributing issues were identified and resolved:
1. **Missing Migration SQL Files in Bundle**: `ReportSQLAgent.spec` omitted `memory/migrations/*.sql` from `datas`. On launch, `MainWindow` initialized `AgentOrchestrator`, which constructed `SQLiteMemoryRepository`, invoking `apply_migrations()`. The migration runner could not locate `001_initial_schema.sql` inside the bundle and raised an unhandled `MigrationError`. Because `console=False` in the PyInstaller specification, this exception crashed the application silently.
2. **Missing Domain Skills in Bundle**: `skills/` was omitted from `datas` in `ReportSQLAgent.spec`. When frozen, `SkillManager` looked in the unpopulated `~/Library/Application Support/ReportSQLAgent/skills` directory, failing to discover built-in domain skills.
3. **Incomplete Submodule Collection**: The `memory` package was not included in `collect_submodules` in `ReportSQLAgent.spec`.
4. **`typer` Warning Root Cause**: `collect_submodules("mcp")` in `ReportSQLAgent.spec` traversed the optional `mcp.cli.cli` module that requires `typer`. Because the desktop app uses MCP exclusively as an embedded library and child stdio subprocess (not via CLI), `mcp.cli` was excluded from submodule collection and analysis.
5. **Lack of Diagnostics & Error Visibility**: The application startup sequence lacked structured stage-by-stage logging, top-level uncaught exception handling (`sys.excepthook`), and a fallback graphical error dialog (`QMessageBox.critical`).

All issues were corrected with minimal, surgical changes, maintaining strict constraints (zero git commands, identical database SHA-256, no unnecessary dependencies, local Ollama only). Both Terminal direct execution and Finder launching were verified to display the PySide6 main window and start the background MCP subprocess. All 431 automated tests pass.

---

## 2. Confirmed Root Causes

### Root Cause 1: Missing Memory Migration SQL Files (`MigrationError`)
* **Mechanism**: During startup, `app/main.py` instantiates `MainWindow(settings)`, which creates `AgentOrchestrator(settings)`. The orchestrator initializes `SQLiteMemoryRepository(db_path=...)`, calling `initialize_schema()`, which invokes `apply_migrations(conn)`.
* **Failure**: `apply_migrations()` searched for migration files in `Path(__file__).resolve().parent`. In the frozen bundle (`.../ReportSQLAgent.app/Contents/Frameworks/memory/migrations`), no `.sql` files were present because PyInstaller only bundles Python bytecode (`.pyc`) unless non-code assets are explicitly added to `datas`.
* **Symptom**: `MigrationError: Migration file for version 1 not found in .../memory/migrations`. Because `console=False` was set in the spec file, stderr was redirected to `/dev/null`, causing a silent crash with exit code `1`.

### Root Cause 2: Missing Domain Skills Directory in Bundle
* **Mechanism**: `AgentOrchestrator` initializes `SkillManager(repository=...)`. By default, `SkillManager` resolved its directory via `resolve_path("skills")`, which mapped to `~/Library/Application Support/ReportSQLAgent/skills` when frozen.
* **Failure**: The app bundle did not include the `skills/` directory tree (`sql/`, `reporting/`, `database/`, etc.), and the user data directory had not been populated.
* **Symptom**: `SkillManager` logged a warning that domain skills were missing, degrading agent intelligence capabilities.

### Root Cause 3: Incomplete Submodule Collection for `memory`
* `ReportSQLAgent.spec` iterated over `["app", "agent", "mcp_layer", "reporting", "database", "config", ...]` when calling `collect_submodules()`, but omitted `"memory"`.

### Root Cause 4: PyInstaller `typer` Warning from `mcp.cli`
* **Mechanism**: The build script executed `pyinstaller ReportSQLAgent.spec`. The spec called `collect_submodules("mcp")`.
* **Failure**: The official `mcp` Python package includes an optional CLI entry point (`mcp.cli.cli`) that imports `typer`.
* **Resolution**: Neither the desktop GUI nor the child MCP stdio server uses `mcp.cli`. Filtering out `mcp.cli` during collection and adding `mcp.cli` to `Analysis.excludes` completely eliminated the warning without introducing unwanted dependencies.

### Root Cause 5: Silent Crash Without Graphical Diagnostics
* If an exception occurred during early initialization (before or during `app.exec()`), `app/main.py` let the exception bubble up to the Python runtime. In a windowed macOS bundle (`console=False`), standard error is not displayed in the GUI, giving the user the impression that the app simply failed to open.

---

## 3. Architecture Fix & Modified Files

### 1. `ReportSQLAgent.spec`
* Added `"memory"` to the list of packages passed to `collect_submodules`.
* Filtered `collect_submodules("mcp", filter=lambda name: not name.startswith("mcp.cli"))`.
* Added `"mcp.cli"` to `Analysis.excludes`.
* Explicitly enumerated and bundled all SQL migration files:
  ```python
  migrations_dir = SPEC_ROOT / "memory" / "migrations"
  if migrations_dir.exists():
      for sql_file in sorted(migrations_dir.glob("*.sql")):
          datas.append((str(sql_file), "memory/migrations"))
  ```
* Explicitly enumerated and bundled all domain skill markdown and YAML metadata files:
  ```python
  skills_dir = SPEC_ROOT / "skills"
  if skills_dir.exists():
      for skill_file in sorted(skills_dir.rglob("*")):
          if skill_file.is_file() and not skill_file.name.startswith("."):
              rel_dir = skill_file.parent.relative_to(SPEC_ROOT)
              datas.append((str(skill_file), str(rel_dir)))
  ```

### 2. `memory/migrations/__init__.py`
* Introduced `get_default_migrations_dir() -> Path` which respects frozen execution mode by inspecting `resource_root() / "memory" / "migrations"`, `resource_root() / "migrations"`, and `app_root() / "memory" / "migrations"` before falling back to `__file__.parent`.
* Updated `apply_migrations()` to use `get_default_migrations_dir()` as default.

### 3. `agent/skill_manager.py`
* Updated default path resolution in `SkillManager.__init__()`: when `is_frozen()` is true, it checks `resource_root() / "skills"` and `app_root() / "skills"` to load bundled domain skills rather than looking only in an empty user data folder.

### 4. `app/main.py`
* Added structured 5-stage startup logging:
  - `Stage 1/5`: Application configuration and logging initialization (`log.info`).
  - `Stage 2/5`: PySide6 `QApplication` instantiation.
  - `Stage 3/5`: Global dark theme stylesheet application.
  - `Stage 4/5`: `MainWindow` and `AgentOrchestrator` construction.
  - `Stage 5/5`: Window display and entry into Qt event loop.
* Implemented `_show_fatal_error_dialog(exc, log_file_path)`: displays a native modal `QMessageBox.critical` with error details, log file location, and expandable stack trace. Safely avoids blocking modal dialogs when running in headless/offscreen test environments (`QT_QPA_PLATFORM=offscreen`).
* Implemented `_install_global_exception_handler(log_file_path)`: hooks `sys.excepthook` to capture any uncaught thread exception, log with full stack trace, and show the fatal error dialog.
* Added non-interactive smoke test support (`--smoke-test`): constructs the complete GUI window and orchestrator, logs clean initialization, closes the window, and exits with code `0`.

### 5. `run_app.py`
* Added top-level safety handler `_fallback_log_fatal(exc)`: writes uncaught import or early launcher errors to `~/Library/Application Support/ReportSQLAgent/logs/startup_crash.log`.

### 6. `scripts/build_macos.sh`
* Added post-build bundle integrity checks:
  - Verifies presence of `memory/migrations/001_initial_schema.sql` inside the bundle.
  - Verifies presence of `skills/sql/SKILL.md` inside the bundle.
* Added child MCP server stdio handshake verification (`"${BIN_PATH}" --mcp-server`).
* Added automated GUI smoke test execution: `QT_QPA_PLATFORM=offscreen "${BIN_PATH}" --smoke-test`.

### 7. `tests/test_macos_startup.py`
* Added 7 automated regression tests:
  - `test_main_smoke_test_mode`: tests `--smoke-test` clean execution and return code `0`.
  - `test_migrations_dir_resolution_source`: validates migration directory resolution in development mode.
  - `test_migrations_dir_resolution_frozen_fallback`: validates frozen fallback resolution via mocked `resource_root`.
  - `test_skill_manager_frozen_resolution`: validates frozen domain skill path resolution.
  - `test_spec_file_packaging_configuration`: verifies `ReportSQLAgent.spec` data inclusion and `mcp.cli` exclusion.
  - `test_fatal_error_dialog_handling`: validates `_show_fatal_error_dialog` dialog creation and text formatting.
  - `test_launcher_fallback_crash_logger`: tests launcher crash file writing on unhandled fatal error.

---

## 4. Build Pipeline Verification

Execution of `./scripts/build_macos.sh`:

```text
==========================================================
 Building Report SQL Agent for macOS
 Project root: /.../FinalProject_SQLAgent
==========================================================
[1/5] Verifying environment and database integrity...
== Local Report SQL Agent: environment verification ==
[ OK ] Python 3.13.16
[ OK ] PySide6 6.10.3
[ OK ] mcp 1.30.0
[ OK ] httpx 0.28.1
[ OK ] reportlab 5.1.0
[ OK ] pytest 9.2.0
[ OK ] MCP SDK exposes FastMCP server + stdio client APIs
[ OK ] Ollama reachable at http://localhost:11434 (version 0.40.14)
[ OK ] Model 'qwen3.5:4b' is installed
[ OK ] Database ecommerce.db: 7 tables, 499,385 total records
[ OK ] SHA-256 integrity verified: c5a5965e000becdb...
== RESULT: PASS ==

[2/5] Running automated tests (excluding live Ollama test)...
430 passed, 1 deselected in 15.58s

[3/5] Cleaning previous build artifacts...
[4/5] Packaging application with PyInstaller...
(Build complete with ZERO typer warnings)

[5/5] Validating built macOS application bundle...
Verifying child MCP server execution mode...
Child MCP server stdio response verified successfully.
Verifying application resource packaging...
Memory migrations verified in application bundle.
Domain skills verified in application bundle.
Verifying GUI application startup smoke test...
Stage 1/5: Application configuration and logging initialized.
Stage 2/5: Initializing PySide6 QApplication...
Stage 3/5: Applying global application stylesheet...
Stage 4/5: Constructing main window and initializing agent orchestrator...
Discovered 4 domain skills from .../ReportSQLAgent.app/Contents/Frameworks/skills
Smoke test requested: MainWindow constructed cleanly. Closing window and exiting.
GUI startup smoke test verified successfully.

==========================================================
 BUILD SUCCESSFUL!
 macOS Application Bundle: .../dist/ReportSQLAgent.app
 Standalone Directory:    .../dist/ReportSQLAgent
==========================================================
```

---

## 5. Automated Test Suite Results

Full test suite execution with pytest:
```bash
source .venv/bin/activate && pytest
```

Output:
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.16, pytest-9.2.0, pluggy-1.7.0
rootdir: /.../FinalProject_SQLAgent
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 431 items

tests/test_advanced_visualization_engine.py .....                        [  1%]
tests/test_agent.py .................................................... [ 13%]
..                                                                       [ 13%]
tests/test_agent_intelligence_integration.py .....                       [ 14%]
tests/test_approval_config.py ........                                   [ 16%]
tests/test_checkpoint_manager.py ......                                  [ 18%]
tests/test_checkpoint_models.py ......                                   [ 19%]
tests/test_checkpoint_repository.py .....                                [ 20%]
tests/test_context_builder.py .............                              [ 23%]
tests/test_context_models.py ........                                    [ 25%]
tests/test_context_relevance.py .....                                    [ 26%]
tests/test_context_security.py ......                                    [ 28%]
tests/test_context_window.py ....................................        [ 36%]
tests/test_database.py ..........................                        [ 42%]
tests/test_database_discovery_reporting.py ........                      [ 44%]
tests/test_dynamic_pdf_milestone9.py .....                               [ 45%]
tests/test_e2e_workflows.py ........                                     [ 47%]
tests/test_gui.py .....................                                  [ 52%]
tests/test_macos_startup.py .......                                      [ 53%]
tests/test_mcp_reliability.py .....                                      [ 54%]
tests/test_mcp_tools.py ....                                             [ 55%]
tests/test_memory_migrations.py .........                                [ 58%]
tests/test_memory_repository.py ..................                       [ 62%]
tests/test_reporting.py ..........                                       [ 64%]
tests/test_reporting_accuracy.py ...............                         [ 67%]
tests/test_skill_manager.py ...........                                  [ 70%]
tests/test_skill_models.py ..............                                [ 73%]
tests/test_skill_security.py ........                                    [ 75%]
tests/test_skill_selection.py .........                                  [ 77%]
tests/test_sql_validation.py ................................            [ 85%]
tests/test_task_manager.py ..................                            [ 89%]
tests/test_task_manager_sqlite.py ....                                   [ 90%]
tests/test_task_models.py ...........                                    [ 92%]
tests/test_task_planner.py ..................                            [ 96%]
tests/test_task_recovery.py .............                                [100%]

============================= 431 passed in 49.74s =============================
```

All 431 tests passed with zero failures.

---

## 6. Live GUI Launch Verification

### Verification 1: Terminal Direct Execution
Command:
```bash
./dist/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent
```
* **Process Status**: Spawned process PID 22065.
* **Console / Log Output**:
  ```text
  2026-11-08 22:02:54,261 | INFO | 22065 | config.logging_setup | Logging initialised (app) -> ~/Library/Application Support/ReportSQLAgent/logs/report_agent_app.log
  2026-11-08 22:02:54,261 | INFO | 22065 | app.main | Stage 1/5: Application configuration and logging initialized.
  2026-11-08 22:02:54,261 | INFO | 22065 | app.main | Executable: .../ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent (frozen=True)
  2026-11-08 22:02:54,261 | INFO | 22065 | app.main | Stage 2/5: Initializing PySide6 QApplication...
  2026-11-08 22:02:54,465 | INFO | 22065 | app.main | Stage 3/5: Applying global application stylesheet...
  2026-11-08 22:02:54,466 | INFO | 22065 | app.main | Stage 4/5: Constructing main window and initializing agent orchestrator...
  2026-11-08 22:02:54,474 | INFO | 22065 | agent.skill_manager | Discovered 4 domain skills from .../Contents/Frameworks/skills
  2026-11-08 22:02:54,708 | INFO | 22065 | app.main | Stage 5/5: Displaying main GUI window and entering Qt event loop.
  ```
* **Result**: Reached Stage 5/5, rendered the window, and remained active in the event loop.

### Verification 2: Finder Launch
Command:
```bash
open ./dist/ReportSQLAgent.app
```
* **Process Status**:
  ```text
  stefanapopa  22105  ... /.../dist/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent
  stefanapopa  22127  ... /.../dist/ReportSQLAgent.app/Contents/MacOS/ReportSQLAgent --mcp-server
  ```
* **Runtime Verification**:
  1. Main GUI process (PID 22105) started and completed all 5 stages.
  2. Spawned child stdio MCP server subprocess (PID 22127).
  3. `mcp_layer.client` established connection over stdio.
  4. Tool handler initialized 6 permitted MCP tools: `inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`.
  5. Discovered 4 domain skills from the bundle.
  6. Connected to Ollama at `http://localhost:11434`, validated `qwen3.5:4b` capabilities, and verified context window limit `effective_ctx=131072`.
  7. Checkpoint manager created initial checkpoints.
* **Result**: Application successfully displayed GUI, maintained child MCP server, and was fully interactive.

---

## 7. Strict Constraint & Security Invariants

* **Git Commands**: Zero git commands executed (no `git status`, `git commit`, `git diff`, etc.).
* **Database Integrity**:
  - Expected SHA-256: `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`
  - Current SHA-256:
    ```bash
    shasum -a 256 data/ecommerce.db
    # Output: c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934  data/ecommerce.db
    ```
    *Status*: Unchanged, bit-for-bit identical.
* **Raw Data**: `data/raw/` remains untouched.
* **Virtual Environment**: `.venv` preserved, no global package installations.
* **AI Security**: Local Ollama only; no cloud AI services utilized.
* **Database Security**: SQLite read-only enforcement maintained; MCP security boundaries intact.

---

## 8. Summary of Completed Deliverables

| Requirement | Status | Evidence |
|---|---|---|
| Diagnose startup failure | Confirmed | Missing migration SQL files + missing domain skills in PyInstaller bundle |
| Eliminate `typer` warning | Resolved | Excluded `mcp.cli` from PyInstaller collection; clean build |
| Add diagnostic startup logging | Implemented | 5-stage logging in `app/main.py` |
| Add graphical error handling | Implemented | `_show_fatal_error_dialog` and `sys.excepthook` installed |
| Bundle all required assets | Implemented | `ReportSQLAgent.spec` bundles `memory/migrations/*.sql` & `skills/` |
| Full build passing | Verified | `./scripts/build_macos.sh` completes with code 0 |
| Automated tests passing | Verified | 431/431 pytest tests pass |
| Terminal launch verified | Verified | Executes to Stage 5/5 and enters Qt event loop |
| Finder launch verified | Verified | `open dist/ReportSQLAgent.app` launches GUI and child MCP server |
| Integrity preserved | Verified | `data/ecommerce.db` SHA-256 verified unchanged |

