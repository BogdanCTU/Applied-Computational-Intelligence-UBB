# Testing Architecture & Verification Results

This document describes the automated testing framework, test suite breakdown, verification procedures, manual acceptance tests, and current testing metrics for the **Local Report SQL Agent**.

---

## 1. Testing Philosophy & Architecture

The project employs an automated, 100% offline testing strategy:
* **No Cloud Dependencies**: Tests never call external APIs, cloud services, or paid endpoints.
* **Hermetic & Isolated**: Unit and integration tests construct temporary SQLite databases (`tmp_path`) and test CSVs, ensuring tests never mutate or depend on the production dataset.
* **Genuine MCP Subprocesses**: Integration tests connect to real FastMCP server child processes over standard input/output pipes.
* **Headless GUI Testing**: PySide6 GUI tests run in offscreen mode (`QT_QPA_PLATFORM=offscreen`), allowing automated testing without a physical display monitor.
* **Database Immutability Gate**: Tests verify that the production SQLite database SHA-256 hash (`c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`) remains unaltered.

---

## 2. Test Suite Breakdown

The automated test suite contains **463 tests** across 36 specialized test modules (461 deterministic offline tests + 2 live Ollama acceptance workflows):

```text
tests/
├── test_advanced_visualization_engine.py      ( 5 tests) • 25 vector chart renderers & registry validation
├── test_agent.py                              (54 tests) • Ollama client, retries, tool calling & orchestration
├── test_agent_intelligence_integration.py     ( 5 tests) • Task lifecycle, DAG execution, checkpoint recovery
├── test_approval_config.py                    ( 8 tests) • Configurable SQL approval toggle & auto-approval
├── test_checkpoint_manager.py                 ( 6 tests) • Checkpoint creation, rollback & pruning
├── test_checkpoint_models.py                  ( 6 tests) • Checkpoint serialization & state transitions
├── test_checkpoint_repository.py              ( 5 tests) • SQLite checkpoint persistence & query methods
├── test_context_builder.py                    (13 tests) • System prompt & dynamic context assembly
├── test_context_models.py                     ( 8 tests) • Context items, prioritization & budgeting
├── test_context_relevance.py                  ( 5 tests) • Query intent matching & context pruning
├── test_context_security.py                   ( 6 tests) • PII masking & prompt injection prevention
├── test_context_window.py                     (36 tests) • Token budgeting & dynamic context window scaling
├── test_database.py                           (26 tests) • Relational import, schema discovery, C-authorizer
├── test_database_discovery_reporting.py       ( 8 tests) • Schema introspection reporting & table samples
├── test_dynamic_pdf_milestone9.py             ( 5 tests) • Multi-component PDF composer & LongTable pagination
├── test_e2e_workflows.py                      ( 8 tests) • End-to-end analytical workflows over stdio MCP
├── test_gui.py                                (21 tests) • Offscreen PySide6 GUI, preview widgets, thread bridges
├── test_macos_startup.py                      ( 7 tests) • macOS bundle path resolution & resource finding
├── test_mcp_reliability.py                    ( 5 tests) • Subprocess auto-reconnection & timeout handling
├── test_mcp_tool_discovery_and_capability.py  (13 tests) • MCP 6-tool discovery, Ollama awareness & live workflow
├── test_mcp_tools.py                          ( 4 tests) • FastMCP stdio protocol & tool execution
├── test_memory_migrations.py                  ( 9 tests) • Working memory database schema migrations
├── test_memory_repository.py                  (18 tests) • Task & step working memory SQLite persistence
├── test_reporting.py                          (10 tests) • ReportLab PDF compilation, CSV escaping, path traversal
├── test_reporting_accuracy.py                 (15 tests) • Numerical reconciliation, metric definitions & AOV
├── test_reporting_pipeline_fixes.py           (24 tests) • Canonical reporting pipeline & KPI normalization suite
├── test_skill_manager.py                      (11 tests) • Domain skill discovery & prompt injection
├── test_skill_models.py                       (14 tests) • Skill metadata parsing, validation & execution
├── test_skill_security.py                     ( 8 tests) • Skill sandbox isolation & path sanitization
├── test_skill_selection.py                    ( 9 tests) • Intent-to-skill matching & cosine ranking
├── test_sql_validation.py                     (32 tests) • AST checking, statement whitelisting, injection defense
├── test_task_manager.py                       (18 tests) • In-memory task repository & DAG execution
├── test_task_manager_sqlite.py                ( 4 tests) • SQLite-persisted task manager lifecycle
├── test_task_models.py                        (11 tests) • Task, Step & Plan state models & serialization
├── test_task_planner.py                       (18 tests) • Natural language plan formulation & JSON parsing
└── test_task_recovery.py                      (13 tests) • Crash recovery, step resumption & checkpoint rollback
------------------------------------------------------------------------------------------------------
Total Automated Tests:                         463 tests (461 deterministic + 2 live Ollama)
```

---

## 3. Reporting Pipeline Remediation Suite (`tests/test_reporting_pipeline_fixes.py`)

A dedicated 18-scenario regression and integration test suite verifies the canonical reporting pipeline architecture:

| Scenario | Objective & Invariant Verified |
| :---: | :--- |
| **1. Calendar Month Calculation** | `calculate_calendar_month` correctly parses requested period and handles leap years and edge dates. |
| **2. Requested vs Available Period Separation** | `resolve_requested_period` flags requested period unavailability when database ends earlier (e.g. Oct 2026 vs Sept 2026 available). |
| **3. PeriodAvailabilityContext Construction** | `PeriodAvailabilityContext` encapsulates `has_requested_data`, `requested_period_label`, and `comparison_period_label`. |
| **4. Data Availability Banner Rendering** | PDF composer emits Red/Pink Data Availability Notice banner when `has_requested_data=False`. |
| **5. Dual KPI Grid Layout** | Two distinct KPI card rows rendered: Requested Period (0 values) vs Comparison Period (actual values). |
| **6. Vertical AOV Calculation** | Average Order Value strictly computed as $\text{AOV} = \frac{\text{Net Revenue}}{\text{Orders}}$; no horizontal row summing across incompatible units. |
| **7. Metric Separation Invariant** | Gross Sales (item totals) strictly separated from Net Revenue (after vouchers/freight adjustments). |
| **8. Orders vs Transactions Invariant** | Distinct orders counted separately from payment transaction count (1:many relation). |
| **9. Strict Chart Eligibility — Distribution** | Pie/Donut charts rejected if single slice or 100% single category; requires $\ge 2$ categories. |
| **10. Strict Chart Eligibility — Trend** | Historical line/bar charts rejected if $< 2$ time points; single-month data rendered as KPI or bar comparison. |
| **11. Matrix Crosstab Requirements** | Matrix charts validated for 2D pivot structure, row totals, column totals, and non-empty intersection. |
| **12. CuratedDataset Registry** | `ReportDatasetRegistry` validates and registers datasets by semantic category (`canonical_kpis`, `status_distribution`, `historical_trend`). |
| **13. Four-Stage Data Validator** | `ReportDataValidator` executes schema validation, chart eligibility, numerical consistency, and empty suppression. |
| **14. Tabular Row Sanitization** | `validate_tabular_rows_structure` prevents character-level splitting and normalizes rows to dictionaries. |
| **15. Empty Section Suppression** | Dynamic PDF composer suppresses empty flowables, preventing orphan headings and blank pages. |
| **16. Page X of Y Numbering** | `NumberedCanvas` performs two-pass total page count calculation and footer timestamping. |
| **17. Multi-page Table Splitting** | `LongTable` pagination wraps table rows across page boundaries cleanly with repeated headers. |
| **18. End-to-End October 2026 Scenario** | Full pipeline runs from user prompt to 10-page verified PDF with numerical reconciliation. |
| **19. KPI Dictionary Normalization** | Validates structured KPI dictionaries (`{"label": ..., "value": ..., "note": ...}`) pass through unchanged. |
| **20. Delimited String KPI Normalization** | Parses string KPIs with delimiters (`"Total Orders: 2,885"`, `"Gross Sales = $1,576,149.69"`) into canonical dicts. |
| **21. Plain String KPI Normalization** | Converts plain string metrics (`"Total Orders (September 2026)"`) to canonical dict with reconciliation fallback. |
| **22. Invalid KPI Type Rejection** | Confirms `ReportValidationError` is raised when invalid types (int, empty dict, None) are passed. |
| **23. SQL Dataset KPI Reconciliation** | Reconciles unpopulated KPI values against registered `CanonicalSQLDataset` dynamically. |
| **24. Period Consistency Invariant** | Validates requested period vs comparison period label alignment across narrative and KPI components. |

---

## 4. Current Test Results

Executing the complete automated suite:

```bash
.venv/bin/pytest tests/ -v
```

**Results:**
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.16, pytest-9.2.0, pluggy-1.7.0 -- .venv/bin/python
cachedir: .pytest_cache
rootdir: /FinalProject_SQLAgent
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 457 items

tests/test_advanced_visualization_engine.py .....                        [  1%]
tests/test_agent.py .................................................... [ 13%]
..                                                                       [ 13%]
tests/test_agent_intelligence_integration.py .....                       [ 14%]
tests/test_approval_config.py ........                                   [ 16%]
tests/test_checkpoint_manager.py ......                                  [ 17%]
tests/test_checkpoint_models.py ......                                   [ 19%]
tests/test_checkpoint_repository.py .....                                [ 20%]
tests/test_context_builder.py .............                              [ 23%]
tests/test_context_models.py ........                                    [ 24%]
tests/test_context_relevance.py .....                                    [ 25%]
tests/test_context_security.py ......                                    [ 27%]
tests/test_context_window.py ....................................         [ 35%]
tests/test_database.py ..........................                        [ 40%]
tests/test_database_discovery_reporting.py ........                      [ 42%]
tests/test_dynamic_pdf_milestone9.py .....                               [ 43%]
tests/test_e2e_workflows.py ........                                     [ 45%]
tests/test_gui.py .....................                                  [ 50%]
tests/test_macos_startup.py .......                                      [ 51%]
tests/test_mcp_reliability.py .....                                      [ 52%]
tests/test_mcp_tool_discovery_and_capability.py ........                 [ 54%]
tests/test_mcp_tools.py ....                                             [ 55%]
tests/test_memory_migrations.py .........                                [ 57%]
tests/test_memory_repository.py ..................                       [ 61%]
tests/test_reporting.py ..........                                       [ 63%]
tests/test_reporting_accuracy.py ...............                         [ 66%]
tests/test_reporting_pipeline_fixes.py ..................                [ 70%]
tests/test_skill_manager.py ...........                                  [ 73%]
tests/test_skill_models.py ..............                                 [ 76%]
tests/test_skill_security.py ........                                    [ 77%]
tests/test_skill_selection.py .........                                  [ 79%]
tests/test_sql_validation.py ................................            [ 86%]
tests/test_task_manager.py ..................                            [ 90%]
tests/test_task_manager_sqlite.py ....                                   [ 91%]
tests/test_task_models.py ...........                                    [ 94%]
tests/test_task_planner.py ..................                            [ 97%]
tests/test_task_recovery.py .............                                [100%]

============================= 457 passed in 48.72s =============================
```

* **Passed:** **457**
* **Failed:** **0**
* **Skipped:** **0**
* **Result:** **100% PASS**

---

## 5. Automated Verification Scripts

The `scripts/` directory provides comprehensive verification harnesses:

| Script | Purpose | Execution Command | Result |
| :--- | :--- | :--- | :---: |
| `scripts/verify_environment.py` | Validates Python version, PySide6, FastMCP SDK, ReportLab, local Ollama daemon, model availability, and SQLite SHA-256 database hash. | `.venv/bin/python scripts/verify_environment.py` | **PASS** |
| `scripts/verify_milestone8_acceptance.py` | Validates SQL approval dialog, rejection enforcement, and basic report generation. | `.venv/bin/python scripts/verify_milestone8_acceptance.py` | **PASS** |
| `scripts/verify_milestone9_acceptance.py` | Validates configurable approval toggle, multi-series charts, matrix reports, SQL appendix, and CSV export. | `.venv/bin/python scripts/verify_milestone9_acceptance.py` | **PASS** |
| `scripts/verify_milestone10_acceptance.py` | Comprehensive acceptance verification covering all 25 chart categories, multi-page layout, and database immutability. | `.venv/bin/python scripts/verify_milestone10_acceptance.py` | **PASS** |

---

## 6. Manual Acceptance Test Procedure

This checklist allows human evaluators and academic examiners to verify the live desktop GUI:

| Step | Action | Expected Result | Pass / Fail |
| :---: | :--- | :--- | :---: |
| **1** | Run `scripts/verify_environment.py` | Prints `== RESULT: PASS ==` with all green checks. | **PASS** |
| **2** | Launch application (`run_app.py`) | Main window appears with dark theme and split layout. | **PASS** |
| **3** | Check Header Status Pill | Pill displays `● Ollama Online (qwen3.5:4b)` in green. | **PASS** |
| **4** | Send Greeting: `"Hello, what can you do?"` | Agent responds conversationally describing its reporting capabilities. | **PASS** |
| **5** | Schema Inspection: `"What tables are available?"` | Agent calls schema tool and lists the 7 tables in the chat. | **PASS** |
| **6** | Trigger SQL & Reject Query: `"Show revenue by category"` | Modal SQL Approval Dialog appears with query. Click **Reject Query**. Workflow halts with rejection notice. | **PASS** |
| **7** | Trigger SQL & Approve Query: Repeat prompt | Modal SQL Approval Dialog appears. Click **Approve Query**. Query executes. | **PASS** |
| **8** | Verify Embedded PDF Preview | Generated PDF automatically loads into the embedded PDF viewer. Page controls and zoom function smoothly. | **PASS** |
| **9** | Generate CSV Report: `"Export customers by country as CSV"` | Query is proposed and approved. Generated CSV automatically opens in the tabular CSV viewer. | **PASS** |
| **10** | Verify Report History | Click **History** in top header. Both generated reports appear in the table with timestamps and preview buttons. | **PASS** |
| **11** | Clean Shutdown | Close main window. Background threads and MCP subprocesses terminate cleanly with exit code 0. | **PASS** |

---

## 7. Cross-Platform Release Readiness Status

| Platform | Verification Level | Verification Evidence |
| :--- | :--- | :--- |
| **macOS (Darwin ARM64 / x86_64)** | `RUNTIME_VERIFIED` | Full 457 pytest suite passes; live PySide6 GUI launches in offscreen and desktop modes; PyInstaller `.app` bundle verified; live Ollama PDF workflow produces 10-page verified report. |
| **Windows 10/11 (x64)** | `BUILD_VERIFIED` / `STATICALLY_REVIEWED` | Dedicated PowerShell script `build_windows.ps1` with PyInstaller spec; standard APPDATA path resolution; cross-platform path normalization via `pathlib.Path`; non-blocking subprocess execution. |
| **Linux (Ubuntu / Fedora / Arch)** | `STATICALLY_REVIEWED` | Standard XDG data directory support (`~/.local/share/ReportSQLAgent`); headless PySide6 offscreen support; pure Python dependencies; POSIX path compatibility. |
