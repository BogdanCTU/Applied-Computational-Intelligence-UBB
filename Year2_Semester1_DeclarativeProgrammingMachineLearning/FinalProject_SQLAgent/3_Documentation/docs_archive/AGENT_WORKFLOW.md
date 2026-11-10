# Agent Workflow & Reasoning Pipeline

This document describes the natural language processing pipeline, local Ollama integration, tool discovery, human-in-the-loop SQL approval gate, and automated report generation lifecycle implemented in the **Local Report SQL Agent**.

---

## 1. End-to-End Workflow Overview

```
User Prompt: "Show me total revenue by country as a PDF report"
                      │
                      ▼
Step 1: Format Steering & Intent Analysis (agent/orchestrator.py)
• Detects format intent: Default is PDF; CSV if explicitly requested
• Registers turn in ConversationManager with format metadata
                      │
                      ▼
Step 2: Prompt Compilation & Context Management
• Builds system prompt with schema rules, permitted tools, and format guidance
• Context manager bounds conversation turns to stay within 8,192 tokens
• Guarantees assistant tool calls and results are never split across boundaries
                      │
                      ▼
Step 3: Local LLM Inference (Ollama qwen3.5:4b)
• Queries http://localhost:11434/api/chat via Async HTTP
• Model outputs tool call or concluding text
• Strips raw <think> tags so internal reasoning does not pollute message body
                      │
                      ▼
Step 4: Tool Calling & Schema Discovery
• Ollama requests inspect_database_schema or get_table_sample
• ToolHandler normalizes parameters and executes over MCP stdio
• Compacts tool result for context bounds and feeds back to LLM
                      │
                      ▼
Step 5: SQL Preparation & Validation
• LLM calls prepare_sql_query(sql_query, explanation)
• Validator runs AST checks and EXPLAIN QUERY PLAN (no execution)
                      │
                      ▼
Step 6: Mandatory Human Approval Gate
• LLM requests execute_readonly_sql(sql_query)
• Orchestrator halts execution and displays modal SqlApprovalDialog
• User reviews exact query text, explanation, and target database
     ├─ User Rejects ──► Execution aborted; agent notified; workflow halts safely
     └─ User Approves ─► Query executed over mode=ro SQLite connection
                      │
                      ▼
Step 7: Report Generation (PDF / CSV)
• Full query results injected into generate_pdf_report or generate_csv_report
• Report compiled in reports/ and cataloged in reports/report_history.json
                      │
                      ▼
Step 8: Workspace Auto-Preview & Concluding Answer
• Generated file automatically loaded into Qt PDF / CSV viewer
• Concluding assistant summary displayed in lateral chat
```

---

## 2. Intent Analysis & Format Steering

To satisfy business and academic reporting needs, the agent enforces format steering rules:
* **Default Output (PDF)**: Any analytical or reporting request defaults to a paginated, publication-grade PDF report (e.g., *"Compare product sales"* or *"Show monthly revenue"*).
* **Explicit CSV Requests**: Regex matching (`_CSV_INTENT_RE = r"\b(?:csv|to\s+csv|as\s+csv|in\s+csv|\.csv)\b"`) steers the workflow to UTF-8 CSV generation when the user explicitly requests raw data exports (e.g., *"Export customer list as CSV"*).
* **Conversational Questions**: General inquiries (e.g., *"What can you do?"* or *"Explain what tables exist"*) are answered conversationally without triggering report generation.

---

## 3. Ollama LLM Integration (`agent/ollama_client.py`)

Inference is performed strictly on the local machine using **Ollama** and the **`qwen3.5:4b`** model:
* **Local Endpoint**: `http://localhost:11434/api/chat`. Remote hosts are strictly forbidden.
* **Dual Tool Protocol Support**:
  1. **Native Function Calling (`tool_mode: "native"`)**: Sends tools array in Ollama's native tool-calling JSON schema.
  2. **Structured JSON Fallback (`tool_mode: "json"`)**: Injects tool specifications into the system prompt and requests JSON output (`format: "json"`) for models that lack robust native tool support.
  3. **Auto-Detection (`tool_mode: "auto"`)**: Probes Ollama upon startup with a synthetic test tool call (`probe_tool_capability`). Automatically selects native mode if supported, otherwise seamlessly falls back to structured JSON.
* **Schema Flattening for Ollama (`_clean_schema_for_ollama`)**:
  FastMCP generates JSON Schema union types (e.g. `anyOf: [string, null]`) for optional arguments. Ollama's Go XML parser can misinterpret these unions, causing mismatched tag syntax errors. The tool handler flattens these unions to plain types (`type: "string"` with default `""`), guaranteeing 100% reliable tool calling.
* **Chain-of-Thought (CoT) Reasoning Filter**:
  The `qwen3.5:4b` model often outputs internal reasoning in `<think>...</think>` tags. The client and GUI parse and separate these tags:
  - Internal reasoning is captured in `response.thinking` for logging and status indicators.
  - Raw `<think>` tokens are stripped from the displayed message body, preventing raw internal chain-of-thought from cluttering the user interface.

---

## 4. MCP Tool Catalog & Discovery (`mcp_layer/`)

The FastMCP server exposes six tools that map to specific phases of the analytical pipeline:

| Phase | Tool Name | Input Arguments | Output Payload |
| :--- | :--- | :--- | :--- |
| **Discovery** | `inspect_database_schema` | `table_name: str = ""` | Table schemas, columns, affinities, PKs, FKs, row counts |
| **Sampling** | `get_table_sample` | `table_name: str`, `num_records: int = 5` | Sample records (capped at 50) and column names |
| **Preparation** | `prepare_sql_query` | `sql_query: str`, `explanation: str = ""` | Syntax validity, statement type, query plan, validation status |
| **Execution** | `execute_readonly_sql` | `sql_query: str`, `max_rows: int = 1000` | Column names, result rows, execution time, truncation status |
| **Reporting (PDF)** | `generate_pdf_report` | `title`, `description`, `sql_query`, `columns`, `rows`, `summary` | Report metadata, output filepath, file size, status |
| **Reporting (CSV)** | `generate_csv_report` | `title`, `description`, `sql_query`, `columns`, `rows`, `summary` | CSV filepath, row count, file size, status |

---

## 5. Mandatory Human-in-the-Loop Approval Gate

The application enforces a strict security policy: **No database query can execute without explicit user approval.**

```
LLM decides to call execute_readonly_sql
                │
                ▼
AgentOrchestrator: Is sql_query in approved_queries?
        ├─ YES ──► Proceed to MCP execution
        └─ NO  ──► Halt and trigger approval_callback
                         │
                         ▼
AgentWorker (QThread): Emits Qt signal to UI thread
Worker pauses synchronously on queue.get()
                         │
                         ▼
MainWindow: Constructs and displays modal SqlApprovalDialog
Displays: Query Text • Formatted Syntax • Explanation • Target Database
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   User clicks "Reject"             User clicks "Approve"
   (or presses Esc / closes dialog)  (Explicit confirmation)
        │                                 │
        ▼                                 ▼
   queue.put(False)                  queue.put(True)
   Worker unblocks                   Worker unblocks
   overall_status = "approval_denied" approved_queries.add(query)
   Query NOT executed                MCP executes query over mode=ro
   Agent explains rejection safely   Results returned to LLM
```

### Safety Guarantees
1. **Default Action is Reject**: The modal dialog focuses on the "Reject Query" button by default.
2. **Esc and Close Safeguard**: Hitting `Esc` or clicking the window close button (`X`) immediately returns `False`.
3. **No Callback = No Execution**: If `approval_callback` is `None`, the orchestrator automatically refuses execution by policy.
4. **Exact Query Match**: Approval applies strictly to the exact character sequence of the query. If the LLM alters a single keyword or filter clause, it must be presented for approval again.

---

## 6. Report Generation & Automatic Preview

### A. PDF Generation Engine (`reporting/pdf_generator.py`)
PDF reports are compiled using **ReportLab** with a clean, executive visual layout:
* **Running Headers & Footers**: Displays document title, generation timestamp, and dynamic page numbering (`Page X of Y`) using a two-pass `NumberedCanvas`.
* **KPI Header Cards**: Highlights total record counts, execution time, and currency totals.
* **Auto-Wrapping Tables**: Calculates available printable width and applies `Paragraph` wrappers to prevent column clipping.
* **Landscape Orientation**: Queries with 6 or more columns automatically switch from Portrait to Landscape layout.
* **SQL Query Block**: Formatted code block showing the exact executed query for transparency.

### B. CSV Generation Engine (`reporting/csv_generator.py`)
CSV reports are compiled using Python's standard `csv` library:
* **RFC-4180 Compliance**: Quotes strings containing delimiters, quotes, or newlines.
* **UTF-8 Encoding**: Fully preserves international characters (names, cities, descriptions).
* **Null Safety**: `None` values are rendered cleanly as empty strings (`""`).

### C. Workspace Auto-Preview
Upon successful tool execution:
1. `AgentWorker` emits `signals.report_generated(data)`.
2. `MainWindow._on_report_generated` receives the file path and format.
3. `ReportPreviewWidget.load_report(path, format)` immediately displays the newly created PDF or CSV inside the workspace without requiring manual file selection.
4. The file metadata is recorded in `reports/report_history.json`.

