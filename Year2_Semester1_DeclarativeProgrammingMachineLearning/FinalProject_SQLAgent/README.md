# Local Report SQL Agent

A desktop application that turns natural-language report requests into
validated, **read-only** SQL against a local SQLite database, and produces
PDF or CSV reports. Everything runs on your machine:

* **LLM**: Ollama (`qwen3.5:4b`) via the native HTTP API on `localhost`
* **Tools**: a Python MCP server (official `mcp` SDK, stdio transport)
* **Database**: SQLite (`data/ecommerce.db`), opened read-only by the agent
* **GUI**: PySide6

No cloud services, paid APIs or telemetry are used.

> Status: under incremental development (see *Milestones* below).

## Architecture

```
PySide6 GUI ──► Agent orchestrator ──► Ollama (localhost, qwen3.5:4b)
                     │
                     ▼
                 MCP client ──stdio──► MCP server (subprocess)
                                         ├─ inspect_database_schema
                                         ├─ get_table_sample
                                         ├─ prepare_sql_query
                                         ├─ execute_readonly_sql
                                         ├─ generate_pdf_report
                                         └─ generate_csv_report
```

| Package       | Responsibility                                          |
|---------------|---------------------------------------------------------|
| `config/`     | Settings (JSON + env overrides), paths, logging, prompts |
| `app/`        | PySide6 GUI: main window, views, background workers     |
| `agent/`      | Ollama client, conversation state, tool-calling loop    |
| `mcp_layer/`  | MCP server, MCP client, tool implementations            |
| `database/`   | Connections, importer, schema inspector, query executor |
| `reporting/`  | PDF (ReportLab) and CSV generators, report history      |
| `scripts/`    | Environment verification, dataset import, build scripts |
| `tests/`      | Pytest suite (uses temporary databases only)            |

> The MCP package is named `mcp_layer/` rather than `mcp/` because a local
> `mcp` package would shadow the official `mcp` SDK on import.

## MCP Server & Tool Reference

The MCP server (`python -m mcp_layer.server`) uses the official Python `mcp` SDK (`FastMCP`) over **JSON-RPC stdio** transport. The agent and integration tests connect via `MCPStdioClient` (`mcp_layer/client.py`), spawning the server as an isolated local subprocess so no database or reporting operation bypasses MCP.

| Tool | Module | Responsibility |
|---|---|---|
| `inspect_database_schema` | `mcp_layer/tools/database_tools.py` | Discovers all tables (or one `table_name`), columns, SQLite type affinities, primary keys, foreign keys, indexes, row counts, and relationships. |
| `get_table_sample` | `mcp_layer/tools/database_tools.py` | Returns up to `num_records` (capped at 50) sample rows plus column metadata for a validated table. |
| `prepare_sql_query` | `mcp_layer/tools/sql_tools.py` | Validates read-only `SELECT`/`WITH` SQL via a lexical/structural scanner and `EXPLAIN QUERY PLAN` **without executing the query**. Rejects DDL/DML, `PRAGMA`, `ATTACH`, multi-statement SQL, and invalid table/column names. |
| `execute_readonly_sql` | `mcp_layer/tools/sql_tools.py` | Independently re-validates SQL and executes it over a `mode=ro` + `PRAGMA query_only=ON` + SQLite C-authorizer connection with configurable timeout and row caps. |
| `generate_pdf_report` | `mcp_layer/tools/reporting_tools.py` | Generates a paginated ReportLab PDF report (default format) with header KPIs, executive summary, SQL block, auto portrait/landscape layout, and `Page X of Y` footers. Never executes SQL. |
| `generate_csv_report` | `mcp_layer/tools/reporting_tools.py` | Generates a UTF-8 CSV report with null handling and RFC-compliant escaping when explicitly requested. Never executes SQL. |

Every generated report is sanitized against filename/path traversal, written atomically inside `reports/`, and recorded in `reports/report_history.json` via `ReportHistoryManager`.

## Requirements

* Python **3.13**
* [Ollama](https://ollama.com) running locally, with the model pulled:
  ```
  ollama pull qwen3.5:4b
  ```
* The Kaggle dataset *Synthetic E-commerce Database (7 Tables)*, downloaded
  manually (ZIP or extracted CSVs). Place it in `data/raw/`.

## Setup

macOS / Linux:
```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/import_dataset.py --run-validation-queries
.venv/bin/python scripts/verify_environment.py
```

Windows (PowerShell):
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\import_dataset.py --run-validation-queries
.\.venv\Scripts\python.exe scripts\verify_environment.py
```

## Configuration

Defaults live in `config/settings.py`; the GUI Settings page writes
`settings.json`. Environment overrides are listed in `.env.example`.
The Ollama host must be local (`localhost`/`127.0.0.1`); remote hosts are rejected.

## Agent Architecture & Tool Orchestration

The agent package (`agent/`) implements an autonomous reasoning and report generation pipeline running strictly against the local Ollama instance (`qwen3.5:4b`):

* **`OllamaClient` (`agent/ollama_client.py`)**: Asynchronous HTTP client communicating exclusively with `http://localhost:11434`. Enforces local-only host validation, extracts native tool calls and reasoning chains (`thinking`), supports automatic tool capability detection, and provides controlled structured-JSON fallback (`format: "json"`).
* **`ToolHandler` (`agent/tool_handler.py`)**: Strict whitelist dispatcher for permitted MCP tools (`inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`). Normalizes parameter schemas for Ollama compatibility, sanitizes arguments, blocks dangerous injections, and enforces execution timeouts.
* **`ConversationManager` (`agent/conversation.py`)**: Manages conversation history within context limits while guaranteeing that tool call invocations and their corresponding tool execution results are never split across context compaction boundaries.
* **`AgentOrchestrator` (`agent/orchestrator.py`)**: Coordinates the multi-turn analytical loop:
  1. Natural-language intent analysis and format steering (PDF by default, CSV when explicitly requested).
  2. Schema inspection and table sampling when needed.
  3. Pre-execution query validation via `prepare_sql_query`.
  4. **Mandatory User Approval Gate**: Execution of `execute_readonly_sql` is strictly gated by an explicit approval callback. If approval is denied or no callback is provided, execution is refused.
  5. Report generation via MCP tools (`generate_pdf_report` or `generate_csv_report`) with full structured result injection.
  6. Real-time event streaming (`AgentEvent`: thinking, tool calls, SQL proposals, approvals, progress, errors).

## Running the Application

To launch the desktop GUI application:

macOS / Linux:
```bash
.venv/bin/python run_app.py
```

Windows (PowerShell):
```powershell
.\.venv\Scripts\python.exe run_app.py
```

## GUI Architecture & Layout

The desktop interface (`app/`) is built using **PySide6** and styled with a centralized, modern dark dashboard theme (`app/style.py`):

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Report SQL Agent              ● Ollama Online (qwen3.5:4b)  History  ⚙ │
├────────────────────────────────────────┬───────────────────────────────┤
│                                        │                               │
│          REPORT WORKSPACE              │     AI Report Assistant       │
│                                        │                               │
│  [Format: PDF] report.pdf              │  👤 You                       │
│  ◀ Page 1 of 4 ▶  [-] [+] Fit Width    │  Show revenue by country      │
│  ────────────────────────────────────  │                               │
│                                        │  📄 Proposed SQL Query        │
│          Embedded Native PDF           │  [Copy] SELECT ...            │
│         (QPdfView / QtPdf)             │                               │
│                                        │  🤖 Report Agent              │
│                  OR                    │  💡 Thinking process          │
│                                        │  Here is the summary table... │
│         Embedded Tabular CSV           │                               │
│        (QTableView / CsvModel)         │  ───────────────────────────  │
│                                        │  Ask a question...            │
│                                        │  [Cancel]              [Send] │
└────────────────────────────────────────┴───────────────────────────────┘
```

* **Main Window (`app/main_window.py`)**: Asymmetric split layout (`QSplitter`: ~65% Report Workspace, ~35% Lateral Chat). Live Ollama health status pill in header ("● Ollama Online" / "● Ollama Offline") checked asynchronously without freezing the UI.
* **Report Workspace (`app/widgets/report_preview_widget.py`)**:
  - Native **PDF Viewer** utilizing Qt 6's official `QPdfView` and `QPdfDocument`. Features single-page mode, page jump navigation (`◀` / `▶`), page counter (`Page X of Y`), zoom controls (`+` / `-`), fit-to-width, fit-to-page, and external launch in default viewer.
  - Tabular **CSV Viewer** utilizing `QTableView` and custom `CsvTableModel` (`app/models/csv_table_model.py`) with column headers, formatted numbers, null representation (`—`), and memory-safe preview caps.
  - Informative placeholder and error states.
* **Conversational Chat (`app/views/chat_view.py`)**:
  - Visual message bubbles (`app/widgets/message_widget.py`) differentiating user requests, assistant technical responses, and collapsible thinking reasoning accordions (`<think>` CoT).
  - Inline SQL cards (`app/widgets/sql_preview_widget.py`) with copy button and status badges.
  - Multiline editor (`ChatInputEdit`) where Enter sends and Shift+Enter inserts a newline.
  - Real-time progress bar and status indicator with cooperative cancellation button.
* **Dedicated SQL Approval Dialog (`app/dialogs/sql_approval_dialog.py`)**:
  - Modal review dialog triggered before any SQL execution. Displays full proposed SQL, explanation, database name, and safety notices.
  - Default action is **Reject**. Esc, closing ('X'), and cancel all strictly guarantee query rejection.
* **Report History View (`app/views/history_view.py`)**: Displays all generated reports recorded in `report_history.json`. Allows instant preview loading into workspace, opening in system apps, or opening containing folders.
* **Settings View (`app/views/settings_view.py`)**: Inspects and persists local Ollama settings, database timeouts, max rows, approval requirements, and report directories. Features an interactive "Test Connection" tool that queries live local Ollama models.
* **Worker & Threading Decoupling (`app/workers/agent_worker.py`)**:
  - `AgentWorker` runs on a dedicated `QThread` with its own `asyncio` event loop.
  - Qt GUI thread never blocks during Ollama inference or MCP tool runs.
  - Synchronous cross-thread approval bridge via `queue.Queue` delivers modal approval without deadlocks.

## Milestones

1. Environment and project initialisation ✅
2. Dataset import and SQLite ✅
3. MCP server and report generation ✅
4. Local Ollama agent and orchestration ✅
5. PySide6 Desktop GUI ✅
6. Integration and end-to-end verification
7. QA and packaging

