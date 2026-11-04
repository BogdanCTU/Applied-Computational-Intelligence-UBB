# Local Report SQL Agent

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%206.10-green.svg)](https://doc.qt.io/qtforpython/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20qwen3.5%3A4b-orange.svg)](https://ollama.com/)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(FastMCP)-purple.svg)](https://modelcontextprotocol.io/)
[![ReportLab](https://img.shields.io/badge/Reporting-ReportLab%205.1-red.svg)](https://www.reportlab.com/)
[![Tests](https://img.shields.io/badge/Tests-156%20Passed-brightgreen.svg)]()
[![Documentation](https://img.shields.io/badge/Specification-SOLUTION.md-blueviolet.svg)](SOLUTION.md)

> [!IMPORTANT]
> **COMPREHENSIVE SOLUTION DOCUMENTATION AVAILABLE**:  
> For the complete university final project documentation, including in-depth architectural specifications, sequence diagrams, the 25-chart visualization engine catalog, SQLite relational schema details, and 156-test verification evidence, please consult [**`SOLUTION.md`**](SOLUTION.md).

A production-grade, 100% offline desktop application that empowers users to query relational databases and generate publication-quality reports using natural language. 

Powered by a locally hosted Large Language Model (**Ollama `qwen3.5:4b`**), the official Python **Model Context Protocol (MCP)** stdio SDK, a strictly read-only **SQLite** data engine, an advanced **25-chart vector visualization engine**, and an asynchronous **PySide6** GUI with integrated native PDF and tabular CSV viewers.

---

## Key Highlights & Privacy Guarantees

* **Zero Cloud Dependency & Absolute Data Privacy**: Operates entirely on the local loopback interface (`127.0.0.1`). Prompts, schema definitions, query results, and generated reports **never leave your local machine**.
* **Model Context Protocol (FastMCP)**: Genuine MCP architecture implementing separate tool modules for database discovery, SQL preparation, safe execution, and ReportLab PDF/CSV generation.
* **Defense-in-Depth SQL Security**: Lexical scanner, AST structure verification, `EXPLAIN QUERY PLAN` validation, SQLite `mode=ro` URI parameter, `PRAGMA query_only = ON`, and a low-level SQLite C-authorizer blocking all mutation/DDL/PRAGMA/ATTACH operations.
* **Configurable Human-in-the-Loop SQL Approval**: SQL execution can be configured for interactive modal confirmation or automated execution with audit logging in the Agent Activity Inspector.
* **Advanced 25-Chart Visualization Engine**: Supports 25 native vector chart types across Comparison, Trend, Distribution, Relationship, Hierarchical, and Matrix categories rendered directly in ReportLab.
* **Embedded Workspace**: Dual-engine workspace featuring an embedded Qt native PDF viewer (`QPdfView` / `QPdfDocument`) and a virtualized tabular CSV viewer (`QTableView` / `CsvTableModel`).

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PySide6 Desktop GUI                             │
│       (Asymmetric Splitter: Native PDF / CSV Workspace + Chat)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Worker Thread (QThread + asyncio)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Agent Orchestrator Loop                           │
│   Intent Steering • Conversation Manager • Context Compaction Guard   │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
    Async HTTP (JSON/Tools)                          │ Python stdio
                    ▼                                ▼
┌───────────────────────────────┐  ┌─────────────────────────────────────┐
│    Local Ollama Server        │  │     Local MCP Stdio Server          │
│   (http://localhost:11434)    │  │    (mcp_layer.server Subprocess)    │
│      Model: qwen3.5:4b        │  ├─────────────────────────────────────┤
│  • Tool Calling & JSON Modes  │  │  1. inspect_database_schema         │
│  • CoT Reasoning Filter       │  │  2. get_table_sample                │
└───────────────────────────────┘  │  3. prepare_sql_query               │
                                   │  4. execute_readonly_sql            │
                                   │  5. generate_pdf_report             │
                                   │  6. generate_csv_report             │
                                   └───────────────┬─────────────────────┘
                                                   │
                           ┌───────────────────────┴─────────────────────┐
                           │                                             │
                           ▼                                             ▼
             ┌───────────────────────────┐                 ┌───────────────────────────┐
             │   SQLite Database (ro)    │                 │   ReportLab / CSV Engine  │
             │   (data/ecommerce.db)     │                 │   • Styled Paginated PDF  │
             │   499,385 Relational Rows │                 │   • RFC-4180 UTF-8 CSV    │
             │   7 Tables + Foreign Keys │                 │   • reports/history.json  │
             └───────────────────────────┘                 └───────────────────────────┘
```

### Technical Documentation Index (`docs/`)

Comprehensive technical and academic documentation is available in the [`docs/`](docs/) directory:

* [**`SOLUTION.md`**](SOLUTION.md): Comprehensive architectural specification, 25-chart visualization engine catalog, sequence diagrams, and end-to-end verification report.
* [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md): High-level system architecture, component responsibilities, concurrency model, and 4 detailed Mermaid flow/sequence diagrams.
* [**`docs/DATABASE.md`**](docs/DATABASE.md): Relational data model, Entity-Relationship diagram, 7-table specifications (499,385 records), and multi-layer read-only SQLite security.
* [**`docs/AGENT_WORKFLOW.md`**](docs/AGENT_WORKFLOW.md): Natural language request lifecycle, format steering (PDF default vs explicit CSV), Ollama integration, and configurable human approval gate.
* [**`docs/SECURITY.md`**](docs/SECURITY.md): Local-only boundary, defense-in-depth SQL protections (lexical, AST, query-only pragma, C-authorizer), path traversal defenses, and privacy guarantees.
* [**`docs/TESTING.md`**](docs/TESTING.md): Testing architecture, full 156-test breakdown across 10 test suites, manual acceptance test checklist, and known limitations.
* [**`docs/DEMO_GUIDE.md`**](docs/DEMO_GUIDE.md): Step-by-step 5–10 minute demonstration script with exact prompts, expected dialogs, and presenter talking points.
* [**`docs/PROJECT_SUMMARY.md`**](docs/PROJECT_SUMMARY.md): Academic project summary, functional/non-functional requirements compliance matrix, technology stack, and conclusions.

### Module Responsibilities

| Directory | Core Role & Responsibilities |
| :--- | :--- |
| [`app/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app) | PySide6 desktop interface: `MainWindow` layout, `ReportPreviewWidget` (PDF/CSV viewers), `ChatView`, modal `SqlApprovalDialog`, `HistoryView`, `SettingsView`, and asynchronous `AgentWorker` threading. |
| [`agent/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent) | Autonomous orchestration: `OllamaClient` (HTTP API), `ToolHandler` (FastMCP parameter normalization), `ConversationManager` (turn/token bounding), and `AgentOrchestrator`. |
| [`mcp_layer/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer) | MCP implementation: `FastMCP` stdio server (`server.py`), `MCPStdioClient` (`client.py`), and modular tool packages for database inspection, SQL tools, and report generators. |
| [`database/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/database) | Relational engine: batch CSV/ZIP dataset importer (`importer.py`), schema introspection (`inspector.py`), and multi-layer read-only query executor with C-authorizer (`executor.py`). |
| [`reporting/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting) | Output generation: Centralized `ChartRegistry` (25 chart types), dynamic PDF composer (`dynamic_pdf_composer.py`), CSV exporter, and persistent catalog manager (`report_manager.py`). |
| [`config/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/config) | System configuration: layered settings (`settings.py`), cross-platform path resolution (`paths.py`), system prompts (`prompts.py`), and logging (`logging_setup.py`). |
| [`scripts/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/scripts) | Automation scripts: environment and database hash verifier (`verify_environment.py`), acceptance test suite (`verify_milestone10_acceptance.py`), and packaging scripts. |
| [`tests/`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/tests) | Automated pytest suite: 156 automated tests covering database, SQL validator, MCP tools, report generators, agent orchestrator, headless GUI, and E2E workflows. |

---

## MCP Server & Tool Catalog

All operations between the LLM and the local environment pass through standard MCP tools over `stdio` pipes:

| Tool Name | Parameters | Description | Security & Execution Rules |
| :--- | :--- | :--- | :--- |
| `inspect_database_schema` | `table_name` *(optional)* | Returns table definitions, columns, SQLite affinities, primary/foreign keys, and row counts. | Strictly read-only; queries `sqlite_master` and `PRAGMA table_info`. |
| `get_table_sample` | `table_name`, `num_records` *(default: 5)* | Retrieves sample rows to help the LLM understand value distributions. | Capped at 50 records maximum; table name validated against schema whitelist. |
| `prepare_sql_query` | `sql_query`, `explanation` | Validates syntax, structure, and schema compliance **without executing the query**. | Scans for forbidden keywords (`INSERT`, `UPDATE`, `DROP`, `PRAGMA`, etc.) and runs `EXPLAIN QUERY PLAN`. |
| `execute_readonly_sql` | `sql_query`, `max_rows` *(optional)* | Re-validates and executes the query against SQLite over a read-only connection. | **Mandatory user approval required**. Enforces row limit (default: 1,000) and execution timeout (default: 120.0s). |
| `generate_pdf_report` | `title`, `description`, `sql_query`, `columns`, `rows`, `summary` | Compiles a formatted, paginated ReportLab PDF report saved in `reports/pdf/`. | **Default format**. Includes metadata header, KPI cards, query snippet, and `Page X of Y` footers. Never executes SQL. |
| `generate_csv_report` | `title`, `description`, `sql_query`, `columns`, `rows`, `summary` | Compiles an RFC-4180 compliant UTF-8 CSV report saved in `reports/csv/`. | Used when user explicitly requests CSV. Sanitizes filenames against path traversal. Never executes SQL. |

---

## Prerequisites & Installation

### 1. System Requirements

* **Operating System**: macOS (ARM64 or x86_64), Windows 10/11, or Modern Linux.
* **Python**: Python **3.13** (mandatory).
* **Ollama**: Local Ollama daemon running with `qwen3.5:4b`:
  ```bash
  ollama serve
  ollama pull qwen3.5:4b
  ```

### 2. Environment Setup

Clone or place the repository in your workspace, then create a local virtual environment:

**macOS / Linux**:
```bash
# Create local .venv using Python 3.13
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell)**:
```powershell
# Create local .venv using Python 3.13
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Database Import & Integrity Verification

Build the SQLite database from the raw Kaggle e-commerce dataset:

```bash
# Import the 7 relational tables into data/ecommerce.db
python scripts/import_dataset.py --run-validation-queries

# Verify environment, packages, Ollama connectivity, and database SHA-256 hash
python scripts/verify_environment.py
```

Expected verification output:
```text
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
```

---

## User Guide & Workflows

### Launching the Application

Start the graphical interface:

```bash
# macOS / Linux
.venv/bin/python run_app.py

# Windows
.\.venv\Scripts\python.exe run_app.py
```

### Supported Reporting Queries

The agent accepts complex natural language queries and automatically resolves schema joins across customers, orders, order items, products, payments, reviews, and returns:

* **Executive Sales Summary (PDF)**:
  > *"Generate a report showing total revenue grouped by product category for 2023."*
* **Customer Insights (PDF)**:
  > *"Who are the top 10 customers by total spend, including their country and total orders?"*
* **Payment Methods Breakdown (PDF)**:
  > *"Show me monthly revenue breakdown grouped by payment method."*
* **Explicit CSV Data Export (CSV)**:
  > *"Generate a CSV report of all returned orders with customer names and refund amounts."*
* **Schema Discovery**:
  > *"What tables and columns are available in the database?"*

### Mandatory SQL Review & Approval

Before executing any database query, the application displays a dedicated modal **SQL Approval Dialog**:
* Displays the complete proposed SQL query with syntax highlighting.
* Displays the agent's natural-language justification.
* Prominently highlights the target database name.
* **Safety First**: The default button is **Reject**. Pressing `Esc`, clicking the window close button (`X`), or selecting **Reject Query** halts the execution pipeline safely and returns control to the user.

---

## Security Architecture & Local Protection

1. **Local Network Boundary**:
   The application strictly restricts communication to `localhost` and `127.0.0.1`. Remote Ollama endpoints or external API URLs are rejected during validation.
2. **SQLite Read-Only Enforcement**:
   - Connections are opened with URI parameter `mode=ro`.
   - `PRAGMA query_only = ON` is executed on connection initialization.
   - Low-level C SQLite authorizer hook (`sqlite3_set_authorizer`) systematically rejects action codes for `SQLITE_INSERT`, `SQLITE_UPDATE`, `SQLITE_DELETE`, `SQLITE_DROP_TABLE`, `SQLITE_ALTER_TABLE`, `SQLITE_ATTACH`, `SQLITE_PRAGMA`, etc.
3. **Execution Limits**:
   - Hard row limits (default 1,000, max configurable 100,000) prevent memory exhaustion.
   - Timeout protection (default 15.0s) cancels run-away queries.
4. **Path Traversal Protection**:
   All report file generation routines sanitize title strings and enforce destination containment within the designated `reports/` folder.

---

## Packaging & Distribution

### macOS (.app Bundle)

Build a self-contained macOS application using PyInstaller:

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

* Output: `dist/ReportSQLAgent.app`
* Architecture: Native ARM64 / Universal
* Launch: `open dist/ReportSQLAgent.app`

### Windows (.exe Standalone)

Build a self-contained Windows executable:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

* Output: `dist\ReportSQLAgent\ReportSQLAgent.exe`
* Launch: `.\dist\ReportSQLAgent\ReportSQLAgent.exe`

### Cross-Platform Path Handling

The application automatically adapts to its runtime environment (`config/paths.py`):
* **Development Mode**: Reads and writes relative to the project directory.
* **Packaged Mode (`sys.frozen`)**:
  - Bundled read-only assets (database, fonts) are read from `sys._MEIPASS` (`resource_root()`).
  - Mutable user files (`settings.json`, generated reports, log files) are written to the standard OS user data directory:
    - macOS: `~/Library/Application Support/ReportSQLAgent`
    - Windows: `%APPDATA%\ReportSQLAgent`
    - Linux: `~/.local/share/ReportSQLAgent`
  - Child MCP server processes are launched directly via `[sys.executable, "--mcp-server"]`, removing any dependency on system Python interpreters.

---

## Testing & Quality Assurance

The test suite runs 100% offline using temporary databases and mocks:

```bash
# Run complete test suite (156 tests)
.venv/bin/pytest tests/ -v
```

### Test Coverage Breakdown

| Test File | Tests | Coverage Scope |
| :--- | :---: | :--- |
| `tests/test_advanced_visualization_engine.py` | 5 | All 25 chart types, ChartRegistry registration, validation, edge cases, multi-chart PDF composition. |
| `tests/test_approval_config.py` | 8 | Configurable SQL approval toggle, settings persistence, auto-approval logging, modal enforcement. |
| `tests/test_dynamic_pdf_milestone9.py` | 5 | Multi-component PDF composer, Page X of Y canvas, LongTable pagination, diagnostic counters. |
| `tests/test_database.py` | 26 | CSV/ZIP importer, schema discovery, read-only guarantees, C-authorizer, table sampling, and parity verification. |
| `tests/test_sql_validation.py` | 32 | Lexical validation, AST inspection, statement whitelisting, injection prevention, and timeout enforcement. |
| `tests/test_mcp_tools.py` | 10 | Official FastMCP stdio server and client, tool registration, schema parity, and error propagation. |
| `tests/test_reporting.py` | 10 | ReportLab PDF layout, typography, multi-page tables, CSV escaping, path traversal defense, and report history. |
| `tests/test_agent.py` | 37 | Ollama client, context manager, tool handler, iterative orchestration, approval gates, and live Ollama integration. |
| `tests/test_gui.py` | 21 | Headless offscreen PySide6 GUI tests: `MainWindow`, `ChatView`, `ReportPreviewWidget`, `SqlApprovalDialog`, `HistoryView`, and worker threads. |
| `tests/test_e2e_workflows.py` | 8 | End-to-end integration workflows: basic interaction, schema discovery, rejection, approval, PDF/CSV generation, and error recovery. |
| **Total** | **156** | **All 156 tests passing.** |

---

## Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Cannot connect to Ollama"** | Local Ollama service is stopped | Start the service in terminal: `ollama serve` |
| **"Model 'qwen3.5:4b' not found"** | Model has not been pulled locally | Run: `ollama pull qwen3.5:4b` |
| **"Database not found at data/ecommerce.db"** | Database import was not executed | Run: `python scripts/import_dataset.py --run-validation-queries` |
| **"SHA-256 checksum mismatch"** | Database was altered or corrupted | Rebuild database: `python scripts/import_dataset.py --overwrite` |
| **GUI does not appear on Linux** | Missing Qt Wayland / X11 platform plugin | Set `export QT_QPA_PLATFORM=xcb` or install `libxcb-cursor0` |
| **SQL query rejected** | Query contains prohibited write or DDL operations | The agent strictly allows `SELECT` and `WITH ... SELECT` queries. |

---

## University Project Metadata

* **Institution**: Babeș-Bolyai University (UBB)
* **Program**: Master in Applied Computational Intelligence
* **Course**: Declarative Programming & Machine Learning
* **Project**: Local Report SQL Agent
* **Deliverable**: Final Course Project (Milestones 1–6 Complete)
