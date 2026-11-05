# Testing Architecture & Verification Results

This document describes the automated testing framework, test suite breakdown, verification procedures, manual acceptance tests, and current testing metrics for the **Local Report SQL Agent**.

---

## 1. Testing Philosophy & Architecture

The project employs an automated, 100% offline testing strategy:
* **No Cloud Dependencies**: Tests never call external APIs, cloud services, or paid endpoints.
* **Hermetic & Isolated**: Unit and integration tests construct temporary SQLite databases (`tmp_path`) and test CSVs, ensuring tests never mutate or depend on the production dataset.
* **Genuine MCP Subprocesses**: Integration tests connect to real FastMCP server child processes over standard input/output pipes.
* **Headless GUI Testing**: PySide6 GUI tests run in offscreen mode (`QT_QPA_PLATFORM=offscreen`), allowing automated testing without a physical display monitor.

---

## 2. Test Suite Breakdown

The automated test suite contains **106 tests** across 7 test modules:

```
tests/
├── test_database.py          (26 tests) • Relational import, schema discovery, read-only C authorizer
├── test_sql_validation.py    (32 tests) • AST checking, statement whitelisting, injection defense
├── test_mcp_tools.py         (10 tests) • FastMCP stdio protocol, tool registration, error handling
├── test_reporting.py         ( 6 tests) • ReportLab PDF compilation, CSV escaping, path traversal
├── test_agent.py             (13 tests) • Ollama client, conversation manager, orchestrator loop
├── test_gui.py               (11 tests) • Offscreen PySide6 GUI, preview widgets, thread bridges
└── test_e2e_workflows.py     ( 8 tests) • 6 end-to-end analytical workflows over stdio MCP
```

---

## 3. Detailed Test Module Breakdown

### 1. `tests/test_database.py` (26 Tests)
* **Read-Only Mode & C-Authorizer**: Verifies that direct database writes (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `PRAGMA`, `ATTACH`) raise `OperationalError` and are blocked by the low-level SQLite authorizer.
* **Dataset Import**: Tests importing from individual CSV files, directory of CSVs, ZIP archives, and existing SQLite databases.
* **Transactional Rollback**: Confirms that import failures roll back completely without leaving partially corrupted database files.
* **Schema Inspection & Sampling**: Validates table discovery, column data types, foreign key extraction, and sample record limits.
* **Relational Parity**: Compares `data/ecommerce.db` against `data/raw/ecommerce.sqlite`, verifying 100% table and row count match across all 7 tables.

### 2. `tests/test_sql_validation.py` (32 Tests)
* **Statement Whitelisting**: Tests that `SELECT` and `WITH ... SELECT` queries pass validation.
* **Prohibited Statements**: Verifies immediate rejection of `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `BEGIN`, and `EXPLAIN`.
* **Prohibited Functions**: Rejects dangerous SQLite functions such as `load_extension`.
* **Syntax & Schema Verification**: Rejects invalid syntax, unclosed quotes, unknown tables, and non-existent columns via `EXPLAIN QUERY PLAN`.
* **Complexity Limits**: Rejects queries exceeding maximum join counts or statement nesting thresholds.

### 3. `tests/test_mcp_tools.py` (10 Tests)
* **FastMCP Stdio Communication**: Verifies end-to-end JSON-RPC 2.0 communication over stdio pipes using the official Python MCP SDK.
* **Tool Catalog Registration**: Verifies that all 6 tools are registered with valid input schemas.
* **Data Flow & Serialization**: Confirms structured JSON serialization of schema metadata, sample records, and query results.
* **Timeout & Row Limits**: Tests that slow queries or oversized result sets are truncated or aborted according to configuration.

### 4. `tests/test_reporting.py` (6 Tests)
* **ReportLab PDF Generation**: Validates single-page and multi-page PDF generation, auto-layout table wrapping, and header/footer numbering.
* **CSV Generation**: Tests UTF-8 preservation, RFC-4180 escaping, and null value representation.
* **Security & Path Traversal**: Confirms that directory traversal characters (`../`, `/`, `\`) in titles are sanitized and cannot write files outside `reports/`.
* **Report History**: Verifies persistence and retrieval in `reports/report_history.json`.

### 5. `tests/test_agent.py` (13 Tests)
* **Localhost Boundary**: Verifies that `OllamaClient` raises `OllamaConnectionError` if configured with a remote host.
* **Context Window Compaction**: Tests that conversation history stays within token limits without breaking tool-call/result pairings.
* **Approval Gate Policy**: Verifies that when `require_sql_approval` is enabled, missing callbacks or denied callbacks strictly halt execution.
* **Format Steering**: Tests automatic steering to PDF by default, or CSV upon explicit request.
* **Live Ollama Integration**: Runs an end-to-end multi-turn query against the local `qwen3.5:4b` model when available.

### 6. `tests/test_gui.py` (11 Tests)
* **Headless PySide6 Execution**: Runs using `QT_QPA_PLATFORM=offscreen`.
* **Report Workspace Preview**: Tests empty states, native PDF loading (`QPdfDocument`), and tabular CSV loading (`CsvTableModel`).
* **Chat Interactions**: Verifies user message submission, assistant message rendering, and removal of raw `<think>` content.
* **Thread Decoupling**: Tests asynchronous `AgentWorker` startup, progress event signals, error propagation, and shutdown without deadlocks.
* **Cross-Thread Approval Bridge**: Tests synchronous `queue.Queue` bridge between worker thread and main UI thread.

### 7. `tests/test_e2e_workflows.py` (8 Tests)
* **Workflow 1**: Basic conversational interaction without tool invocation.
* **Workflow 2**: Database discovery calling `inspect_database_schema`.
* **Workflow 3**: SQL preparation followed by user rejection (verifies query was not executed).
* **Workflow 4**: SQL approval followed by execution, PDF generation, and history recording.
* **Workflow 5**: Explicit CSV report request generating valid RFC-4180 CSV export.
* **Workflow 6**: Comprehensive error handling:
  - Ollama service unavailable.
  - Prohibited / dangerous SQL statements (`DROP TABLE`).
  - Cooperative workflow cancellation mid-flight.

---

## 4. Current Test Results

Executing the complete automated suite:

```bash
.venv/bin/pytest tests/ -v
```

**Results:**
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.16, pytest-9.2.0, pluggy-1.7.0 -- /Users/.../.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/.../FinalProject_SQLAgent
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 106 items

tests/test_agent.py ...................                                  [ 17%]
tests/test_database.py ..........................                        [ 42%]
tests/test_e2e_workflows.py ........                                     [ 50%]
tests/test_gui.py ...........                                            [ 60%]
tests/test_mcp_tools.py ..........                                       [ 69%]
tests/test_reporting.py ......                                           [ 75%]
tests/test_sql_validation.py ................................            [100%]

============================= 106 passed in 327.15s (0:05:27) ==================
```

* **Passed:** **106**
* **Failed:** **0**
* **Skipped:** **0**
* **Result:** **100% PASS**

---

## 5. Manual Acceptance Test Procedure

This checklist allows human evaluators to verify the live desktop GUI:

| Step | Action | Expected Result | Pass / Fail |
| :---: | :--- | :--- | :---: |
| **1** | Run `scripts/verify_environment.py` | Prints `== RESULT: PASS ==` with all 11 green checks. | [ ] |
| **2** | Launch application (`run_app.py`) | Main window appears with modern dark theme and split layout. | [ ] |
| **3** | Check Header Status Pill | Pill displays `● Ollama Online (qwen3.5:4b)` in green. | [ ] |
| **4** | Send Greeting: `"Hello, what can you do?"` | Agent responds conversationally describing its reporting capabilities. | [ ] |
| **5** | Schema Inspection: `"What tables are available?"` | Agent calls schema tool and lists the 7 tables in the chat. | [ ] |
| **6** | Trigger SQL & Reject Query: `"Show revenue by category"` | Modal SQL Approval Dialog appears with query. Click **Reject Query**. Workflow halts with rejection notice. | [ ] |
| **7** | Trigger SQL & Approve Query: Repeat prompt | Modal SQL Approval Dialog appears. Click **Approve Query**. Query executes. | [ ] |
| **8** | Verify Embedded PDF Preview | Generated PDF automatically loads into the embedded PDF viewer. Page controls and zoom function smoothly. | [ ] |
| **9** | Generate CSV Report: `"Export customers by country as CSV"` | Query is proposed and approved. Generated CSV automatically opens in the tabular CSV viewer. | [ ] |
| **10** | Verify Report History | Click **History** in top header. Both generated reports appear in the table with timestamps and preview buttons. | [ ] |
| **11** | Clean Shutdown | Close main window. Background threads and MCP subprocesses terminate cleanly with exit code 0. | [ ] |

---

## 6. Known Technical Limitations

1. **Host-Bound Windows Executable Testing**:
   Because development and automated verification were conducted on a macOS ARM64 workstation, the Windows PowerShell build script (`scripts/build_windows.ps1`) was authored and structurally validated, but native compilation and execution of `ReportSQLAgent.exe` requires a physical Windows machine.
2. **Offscreen vs Visual Display**:
   Offscreen tests verify widget instantiation, signal delivery, layout calculations, and thread cleanup. Final font rendering and visual aesthetics should be checked on a physical monitor.

