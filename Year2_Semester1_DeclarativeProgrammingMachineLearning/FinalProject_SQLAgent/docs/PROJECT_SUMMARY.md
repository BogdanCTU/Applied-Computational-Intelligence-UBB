# Project Summary & Evaluation

**Academic Program:** Master in Applied Computational Intelligence  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University (UBB)  
**Course:** Declarative Programming & Machine Learning  
**Project Title:** Local Report SQL Agent  
**Author / Candidate:** Student  
**Academic Year:** 2025–2026  

---

## 1. Problem Statement

Modern organizations store vast amounts of business data in relational databases. However, accessing actionable reports typically requires either specialized technical knowledge (SQL proficiency) or centralized Business Intelligence (BI) engineering support, creating analytical bottlenecks for business stakeholders.

While cloud-based Generative AI solutions (e.g., OpenAI, Anthropic, Google Cloud) offer text-to-SQL capabilities, enterprise adoption faces critical regulatory and confidentiality barriers:
1. **Data Privacy & Compliance**: Regulatory frameworks (e.g., GDPR, HIPAA) often forbid transmitting internal customer data, financial transactions, or database schemas to third-party cloud APIs.
2. **Security & Injection Risks**: Direct LLM execution against databases risks hallucinated mutations (`DROP`, `DELETE`, `UPDATE`) or prompt injection attacks.
3. **Vendor Lock-in & Cost**: Cloud LLM API billing and internet connectivity requirements introduce operational dependencies and ongoing expenses.

There is a compelling need for a **100% offline, privacy-preserving desktop application** that allows non-technical users to query relational databases in natural language, enforces strict read-only execution, incorporates mandatory human approval, and generates publication-grade business reports.

---

## 2. Project Objectives

The project set out to design and engineer a complete, production-quality local reporting agent meeting five core goals:
1. **Zero Cloud Dependencies**: Run entirely on the local loopback interface (`127.0.0.1`), using locally hosted LLMs (**Ollama `qwen3.5:4b`**) and local databases (**SQLite**).
2. **Genuine Model Context Protocol (FastMCP)**: Decouple database and reporting tools using the official Python MCP SDK over stdio transport.
3. **Multi-Layer Read-Only Security**: Guarantee that the database cannot be modified through lexical AST scanning, SQLite URI read-only modes, internal query-only pragmas, and low-level C-authorizer callbacks.
4. **Human-in-the-Loop SQL Review**: Mandate explicit user confirmation in a modal review dialog before executing any database query.
5. **Integrated Desktop Experience**: Provide a modern desktop GUI (PySide6) with embedded native PDF (`QPdfView`) and tabular CSV (`QTableView`) workspace viewers, lateral chat, and persistent history.

---

## 3. Requirements Compliance Matrix

### Functional Requirements

| ID | Requirement | Status | Verification Evidence |
| :---: | :--- | :---: | :--- |
| **FR-01** | Interpret natural language requests into valid SQL | **Implemented** | Verified in `tests/test_agent.py` and `tests/test_e2e_workflows.py`. |
| **FR-02** | Support complex multi-table joins, CTEs, and aggregations | **Implemented** | Successfully queries joins across all 7 relational tables in `ecommerce.db`. |
| **FR-03** | Dynamic database schema inspection via MCP | **Implemented** | FastMCP tool `inspect_database_schema` extracts tables, columns, and foreign keys. |
| **FR-04** | Table sampling with row bounding | **Implemented** | FastMCP tool `get_table_sample` caps records at 50 max. |
| **FR-05** | SQL preparation and query plan validation | **Implemented** | FastMCP tool `prepare_sql_query` executes `EXPLAIN QUERY PLAN` without running SQL. |
| **FR-06** | Mandatory modal SQL approval gate | **Implemented** | `SqlApprovalDialog` pauses worker thread; default button is strictly Reject. |
| **FR-07** | Bounded read-only query execution | **Implemented** | `execute_readonly_sql` enforces row caps (1,000) and query timeouts (120.0s). |
| **FR-08** | Automatic PDF report generation (default format) | **Implemented** | FastMCP tool `generate_pdf_report` builds styled ReportLab PDFs with KPI cards. |
| **FR-09** | Explicit CSV export generation | **Implemented** | Intent steering routes requests containing `"csv"` to `generate_csv_report`. |
| **FR-10** | Embedded native PDF viewer in GUI workspace | **Implemented** | `QPdfView` / `QPdfDocument` embedded with zoom, fit-to-width, and page jump. |
| **FR-11** | Embedded tabular CSV viewer in GUI workspace | **Implemented** | `QTableView` backed by virtualized `CsvTableModel` with formatted cells. |
| **FR-12** | Persistent historical report catalog | **Implemented** | `ReportHistoryManager` stores entries in `reports/report_history.json`. |
| **FR-13** | Configurable application settings dialog | **Implemented** | `SettingsView` persists configurations to `settings.json` with live Ollama tester. |

### Non-Functional Requirements

| ID | Requirement | Status | Verification Evidence |
| :---: | :--- | :---: | :--- |
| **NFR-01** | Absolute local execution (no cloud APIs) | **Met** | `LOCAL_HOSTS` whitelist strictly denies remote addresses in `OllamaClient`. |
| **NFR-02** | Source dataset preservation | **Met** | `data/raw/` remains untouched; `data/ecommerce.db` built independently. |
| **NFR-03** | Database integrity verification | **Met** | SHA-256 hash verified: `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`. |
| **NFR-04** | Concurrency & UI responsiveness | **Met** | `AgentWorker` runs on private `QThread` with dedicated `asyncio` event loop. |
| **NFR-05** | Clean application termination | **Met** | `closeEvent` hook terminates background workers and MCP subprocesses cleanly. |
| **NFR-06** | Cross-platform standalone packaging | **Met** | Native macOS ARM64 `.app` bundle built (193 MB) via PyInstaller. |
| **NFR-07** | Automated test coverage | **Met** | **106 automated tests** passing with 0 failures and 0 skips. |

---

## 4. Technology Stack

* **Programming Language:** Python 3.13.16
* **Desktop Graphical Interface:** PySide6 6.10.3 (Qt for Python 6.10, QtPdf, QtPdfWidgets)
* **Local LLM Engine:** Ollama (version 0.40.14) running `qwen3.5:4b`
* **Agent-Tool Protocol:** Official Python Model Context Protocol (`mcp` 1.30.0, FastMCP)
* **Relational Database Engine:** SQLite 3.49+ (enforcing URI `mode=ro`, C authorizers, foreign keys)
* **Report Compilation:** ReportLab 5.1.0 (PDF typography, table layouts, KPI cards, NumberedCanvas)
* **HTTP Client:** HTTPX 0.28.1 (asynchronous HTTP communication with Ollama)
* **Packaging & Distribution:** PyInstaller 6.22.3 (native macOS ARM64 bundle and Windows spec)
* **Automated Testing:** Pytest 9.2.0, pytest-asyncio 1.4.1, AnyIO 4.16.0

---

## 5. Completed Implementation Milestones

* **Milestone 1 — Environment & Project Scaffold**: Python 3.13 `.venv`, project directory layout, layered configuration (`config/settings.py`), paths resolution (`config/paths.py`), rotating file logging (`config/logging_setup.py`), and environment verifier (`scripts/verify_environment.py`).
* **Milestone 2 — Dataset & SQLite Engine**: Batch streaming importer (`database/importer.py`), 7 tables imported (499,385 rows), exact parity with reference `ecommerce.sqlite`, read-only connection manager (`database/connection.py`), and low-level SQLite C-authorizer.
* **Milestone 3 — FastMCP Server & Report Generation**: Official Python FastMCP stdio server (`mcp_layer/server.py`), six MCP tools (`inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`), ReportLab PDF builder, CSV exporter, and persistent history manager.
* **Milestone 4 — Local Ollama Agent & Orchestration**: `OllamaClient`, schema parameter flattening (`_clean_schema_for_ollama`), context manager with tool-call pairing guarantees, `AgentOrchestrator` multi-turn loop, format steering, and mandatory user approval gate.
* **Milestone 5 — PySide6 Desktop GUI**: Modern dark dashboard interface (`app/style.py`), asymmetric split layout (`MainWindow`), native PDF viewer (`QPdfView`), tabular CSV viewer (`QTableView`), conversational chat view (`ChatView`), modal approval dialog (`SqlApprovalDialog`), history view (`HistoryView`), settings dialog (`SettingsView`), and background thread decoupling (`AgentWorker`).
* **Milestone 6 — Final Integration, Verification & Packaging**: Elimination of circular imports, chain-of-thought `<think>` display filtering, cross-platform path handling for packaged mode (`user_data_root()`), PyInstaller build (`ReportSQLAgent.spec`), automated macOS ARM64 bundle (`dist/ReportSQLAgent.app`), Windows build script (`scripts/build_windows.ps1`), 8 end-to-end integration tests, and comprehensive technical documentation.

---

## 6. Architecture & Data Flow Overview

```
User Prompt (Natural Language)
             │
             ▼
PySide6 GUI (app/main_window.py)
             │
             ▼  [Cross-thread Signal via WorkerSignals]
AgentWorker QThread (Private Asyncio Loop)
             │
             ▼
AgentOrchestrator (agent/orchestrator.py)
      │                               │
      ├───────────────────────┐       │
      ▼                       ▼       ▼
OllamaClient (Async HTTP)  ConversationManager  ToolHandler (agent/tool_handler.py)
(http://localhost:11434)   (Context Guard)            │
qwen3.5:4b                                            ▼  [JSON-RPC 2.0 Stdio]
                                                MCPStdioClient (mcp_layer/client.py)
                                                      │
                                                      ▼  [Subprocess IPC Pipes]
                                                FastMCP Server (mcp_layer/server.py)
                                                      │
                                   ┌──────────────────┴──────────────────┐
                                   ▼                                     ▼
                      SQLite Database (data/ecommerce.db)    Reporting Engines (reporting/)
                      • URI mode=ro                          • ReportLab PDF Builder
                      • PRAGMA query_only=ON                 • RFC-4180 CSV Exporter
                      • SQLite C-Authorizer Hook             • reports/report_history.json
```

---

## 7. Security & Privacy Assessment

1. **Local Network Boundary**: Zero data transmission to external servers. Configured hostnames must belong to `LOCAL_HOSTS` (`localhost` / `127.0.0.1`).
2. **Defense-in-Depth SQL Security**: Lexical token filtering, AST structure verification (`SELECT`/`WITH` only), `EXPLAIN QUERY PLAN` verification, read-only SQLite URI parameters, query-only pragma, and low-level C-authorizer denying write/DDL/PRAGMA/ATTACH codes.
3. **Mandatory Human Confirmation**: Query execution is halted until the user explicitly clicks "Approve Query" in a modal dialog. Default action is Reject.
4. **Path Traversal Defense**: All report titles are sanitized against directory traversal characters (`../`, `/`, `\`); target directories are validated to stay within `reports/`.
5. **Database Immutability**: The application database SHA-256 hash matches the expected checksum (`c5a5965e000becdb...`); raw source data in `data/raw/` remains completely untouched.

---

## 8. Testing Summary

* **Automated Test Suite:** **106 automated tests** across 7 test suites.
* **Execution Result:** **106 passed**, 0 failed, 0 skipped in 327 seconds.
* **End-to-End Workflows:** All 6 core workflows (conversational greeting, schema discovery, rejection safety, approval & PDF generation, explicit CSV export, and error handling) verified against genuine FastMCP subprocesses.
* **Environment Verification:** Verified 11/11 system checks (Python 3.13, PySide6, MCP SDK, ReportLab, Ollama connectivity, model presence, database records, and SHA-256 integrity).

---

## 9. Limitations & Future Work

### Current Limitations
1. **Host-Bound Windows Executable Compilation**: Development and validation were conducted on macOS ARM64. While the PowerShell script (`scripts/build_windows.ps1`) is fully prepared and structurally verified, compiling and launching `ReportSQLAgent.exe` requires a physical Windows host.
2. **Offscreen vs Physical Monitor GUI Testing**: Automated GUI tests ran in offscreen mode (`QT_QPA_PLATFORM=offscreen`). Final visual aesthetics and window manager behavior were verified manually on a physical display.
3. **Model Context Constraints**: While context compaction protects against exceeding 8,192 tokens, extremely complex queries involving multi-table subqueries may occasionally require iteration fine-tuning.

### Future Improvements
1. **Direct Data Visualization**: Incorporate interactive charting (e.g. Qt Charts or embedded Plotly HTML) directly within the report workspace alongside PDF and CSV views.
2. **Database Support Expansion**: Extend the read-only MCP database tools to support local PostgreSQL and DuckDB instances.
3. **Fine-Tuned Local Models**: Fine-tune smaller local models (e.g. `qwen2.5-coder:3b` or `sqlcoder:7b`) specifically on e-commerce schema queries to further reduce inference latency.

---

## 10. Conclusion

The **Local Report SQL Agent** successfully demonstrates that modern autonomous AI agents can operate with complete data privacy, high relational accuracy, and production-grade software engineering standards. By coupling the official **Model Context Protocol (FastMCP)** with a locally hosted LLM (**Ollama `qwen3.5:4b`**), a multi-layer read-only SQLite security model, and a responsive **PySide6** desktop interface, the project provides a safe, practical, and dependable bridge between human language and relational databases.

All academic objectives, architectural constraints, security safeguards, and functional milestones have been fully accomplished and verified.

