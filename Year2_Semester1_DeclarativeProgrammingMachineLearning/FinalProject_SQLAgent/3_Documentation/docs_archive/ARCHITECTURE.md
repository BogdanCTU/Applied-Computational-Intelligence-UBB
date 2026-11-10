# System Architecture

This document describes the software architecture, component relationships, concurrency model, and data communication protocols of the **Local Report SQL Agent**.

---

## 1. High-Level Architecture Overview

The application is structured into five decoupled architectural layers operating strictly on the local machine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        1. Presentation Layer (PySide6)                 │
│    MainWindow • ReportPreviewWidget (PDF/CSV) • ChatView • Dialogs     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Cross-thread Signals & Queues
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        2. Orchestration Layer (agent/)                 │
│      AgentOrchestrator • ConversationManager • ToolHandler • Client    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
      HTTP / JSON   │                                │ JSON-RPC Stdio
                    ▼                                ▼
┌───────────────────────────────┐  ┌─────────────────────────────────────┐
│    Local LLM Service (Ollama) │  │    3. Protocol Layer (mcp_layer/)   │
│   Host: http://localhost:11434│  │      FastMCP Server (Subprocess)    │
│       Model: qwen3.5:4b       │  │  inspect • sample • prepare • exec  │
└───────────────────────────────┘  └───────────────┬─────────────────────┘
                                                   │
                           ┌───────────────────────┴─────────────────────┐
                           │                                             │
                           ▼                                             ▼
             ┌───────────────────────────┐                 ┌───────────────────────────┐
             │   4. Relational Storage   │                 │   5. Reporting Engines    │
             │     (database/)           │                 │      (reporting/)         │
             │ SQLite (data/ecommerce.db)│                 │  ReportLab PDF Generator  │
             │ Read-Only + C Authorizer  │                 │  RFC-4180 CSV Exporter    │
             └───────────────────────────┘                 └───────────────────────────┘
```

---

## 2. Architecture Diagrams

### A. Overall System Architecture

```mermaid
graph TB
    subgraph Presentation["Presentation Layer (PySide6 GUI)"]
        MW["MainWindow"]
        RPW["ReportPreviewWidget<br/>(QPdfView / QTableView)"]
        CV["ChatView<br/>(Messages / Status / Input)"]
        SAD["SqlApprovalDialog<br/>(Modal Security Gate)"]
        HV["HistoryView<br/>(Saved Reports)"]
        SV["SettingsView<br/>(Local Config)"]
    end

    subgraph Concurrency["Concurrency & Threading"]
        QTH["AgentWorker (QThread)"]
        LOOP["Asyncio Event Loop"]
        SYNC["Approval Queue (queue.Queue)"]
    end

    subgraph Agent["Agent Orchestration (agent/)"]
        AO["AgentOrchestrator"]
        CM["ConversationManager"]
        TH["ToolHandler"]
        OC["OllamaClient (Async HTTP)"]
    end

    subgraph LLM["Local Inference (Ollama)"]
        OL["Ollama Daemon<br/>http://localhost:11434<br/>Model: qwen3.5:4b"]
    end

    subgraph MCP["MCP Subprocess (mcp_layer/)"]
        MC["MCPStdioClient"]
        MS["FastMCP Server<br/>(Process: sys.executable)"]
        T1["inspect_database_schema"]
        T2["get_table_sample"]
        T3["prepare_sql_query"]
        T4["execute_readonly_sql"]
        T5["generate_pdf_report"]
        T6["generate_csv_report"]
    end

    subgraph Backend["Data & Reporting Backends"]
        DB[("SQLite Database<br/>data/ecommerce.db<br/>(mode=ro + C Authorizer)")]
        RL["ReportLab Engine<br/>(PDF Generation)"]
        CSV["CSV Exporter<br/>(UTF-8 RFC-4180)"]
        HIST[("Report Catalog<br/>reports/report_history.json")]
    end

    %% Connections
    MW --> CV
    MW --> RPW
    MW --> SAD
    MW --> HV
    MW --> SV

    CV -.->|User prompt| QTH
    QTH --> LOOP
    LOOP --> AO
    AO --> CM
    AO --> OC
    AO --> TH
    OC <==>|Async HTTP| OL

    TH --> MC
    MC <==>|JSON-RPC Stdio| MS

    MS --> T1 & T2 & T3 & T4 & T5 & T6
    T1 & T2 & T4 --> DB
    T3 -.->|EXPLAIN QUERY PLAN| DB
    T5 --> RL
    T6 --> CSV
    T5 & T6 --> HIST

    AO -.->|Approval request| SYNC
    SYNC -.->|Wait for user| SAD
    SAD -.->|Approve/Reject| SYNC
    AO -.->|AgentEvent stream| QTH
    QTH -.->|Qt Signals| MW
    MW -.->|Load newly generated file| RPW
```

---

### B. Agent Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant GUI as ChatView / MainWindow
    participant Worker as AgentWorker (QThread)
    participant Agent as AgentOrchestrator
    participant Ollama as OllamaClient (qwen3.5:4b)
    participant MCP as FastMCP Server (stdio)

    User->>GUI: Submit natural language prompt
    GUI->>Worker: Start worker thread with prompt
    Worker->>Agent: process_message(prompt)
    
    Agent->>Agent: Format detection (PDF vs CSV intent)
    Agent->>Agent: Append user message to ConversationManager
    
    loop Analytical Loop (up to max_iterations)
        Agent->>Ollama: chat(messages, tools)
        Ollama-->>Agent: OllamaChatResponse (tool_calls / content)
        
        alt Tool Call Requested
            Agent->>Worker: Emit AgentEvent (Tool Call Proposed)
            Agent->>MCP: call_tool(tool_name, arguments)
            MCP-->>Agent: Tool execution result
            Agent->>Agent: Compact tool result for context limits
            Agent->>Agent: Append tool response to Conversation
        else Final Concluding Answer
            Agent->>Worker: Emit AgentEvent (Final Answer)
        end
    end

    Agent-->>Worker: AgentRunResult (status, reports, sql)
    Worker-->>GUI: Emit signals.finished(result)
    GUI->>GUI: Render assistant message
    opt Report was generated
        GUI->>GUI: Automatically load file into ReportPreviewWidget
    end
```

---

### C. SQL Approval and Execution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as AgentOrchestrator
    participant Worker as AgentWorker (Worker Thread)
    participant GUI as MainWindow (UI Thread)
    participant Dialog as SqlApprovalDialog
    participant MCP as MCP Server
    participant DB as SQLite Engine

    Note over Agent: LLM decides to run execute_readonly_sql
    Agent->>Agent: Check if query in approved_queries
    
    alt Query NOT yet approved
        Agent->>Worker: approval_callback(sql_query, explanation)
        Worker->>GUI: Emit approval_requested(sql, explanation, queue)
        Note over Worker: Worker blocks on queue.get()
        
        GUI->>Dialog: SqlApprovalDialog.ask_approval(sql, explanation)
        Dialog-->>User: Display modal SQL review card
        
        alt User clicks "Approve Query"
            User->>Dialog: Click Approve
            Dialog-->>GUI: Returns True
            GUI->>Worker: queue.put(True)
            Worker-->>Agent: Callback returns True
            Agent->>Agent: Add query to approved_queries cache
            Agent->>MCP: execute_readonly_sql(sql_query)
            MCP->>DB: Execute with mode=ro & C Authorizer
            DB-->>MCP: Columns + Row tuples
            MCP-->>Agent: Result JSON
        else User clicks "Reject Query" or Esc
            User->>Dialog: Click Reject / Esc / Close
            Dialog-->>GUI: Returns False
            GUI->>Worker: queue.put(False)
            Worker-->>Agent: Callback returns False
            Agent->>Agent: overall_status = "approval_denied"
            Agent->>MCP: (SKIPPED - Query NOT executed)
            Agent->>Agent: Add tool error "APPROVAL_DENIED" to conversation
        end
    else Query already approved
        Agent->>MCP: execute_readonly_sql(sql_query)
        MCP->>DB: Execute query
        DB-->>MCP: Results
        MCP-->>Agent: Result JSON
    end
```

---

### D. MCP Tool Communication Architecture

```mermaid
flowchart LR
    subgraph ClientProcess["Host GUI Process"]
        Orch["AgentOrchestrator"]
        TH["ToolHandler<br/>• Schema Normalization<br/>• Argument Sanitization<br/>• Security Whitelist"]
        Cli["MCPStdioClient<br/>(Official MCP Python SDK)"]
    end

    subgraph Pipes["Standard IO Communication"]
        P1["stdin (JSON-RPC requests)"]
        P2["stdout (JSON-RPC responses)"]
        P3["stderr (Server internal logs)"]
    end

    subgraph ServerProcess["Subprocess: sys.executable --mcp-server"]
        FastMCP["FastMCP Instance<br/>(local-report-sql-agent-mcp)"]
        subgraph Tools["Registered Tool Modules"]
            DBT["Database Tools<br/>• inspect_database_schema<br/>• get_table_sample"]
            SQLT["SQL Tools<br/>• prepare_sql_query<br/>• execute_readonly_sql"]
            REPT["Reporting Tools<br/>• generate_pdf_report<br/>• generate_csv_report"]
        end
    end

    Orch --> TH --> Cli
    Cli -->|write| P1 -->|read| FastMCP
    FastMCP -->|write| P2 -->|read| Cli
    FastMCP -.->|write| P3

    FastMCP --> DBT & SQLT & REPT
```

---

## 3. Component Responsibilities

### 1. Presentation Layer (`app/`)
* **`app/main_window.py` (`MainWindow`)**: Central window orchestrating layout, split pane resizing, menu actions, report opening, and background thread lifecycle management. Implements a safe `closeEvent` hook to cancel active workers and cleanly shut down subprocesses without crashing Qt.
* **`app/widgets/report_preview_widget.py` (`ReportPreviewWidget`)**: Workspace displaying rendered reports using `QStackedWidget`:
  - **PDF View**: Uses official Qt 6 `QPdfView` and `QPdfDocument`. Implements page navigation, zoom factor controls, fit-to-width, fit-to-page, and system file launcher.
  - **CSV View**: Uses `QTableView` backed by custom `CsvTableModel` (`app/models/csv_table_model.py`) with memory-bounded row previewing.
* **`app/views/chat_view.py` (`ChatView`)**: Lateral conversational feed. Renders `MessageWidget` cards, inline SQL code previews (`SqlPreviewWidget`), progress activity bars, and multi-line user text input.
* **`app/dialogs/sql_approval_dialog.py` (`SqlApprovalDialog`)**: Modal security dialog presenting SQL statements, explanations, database target, and warnings. The default action is strictly **Reject** to prevent accidental confirmation.
* **`app/views/history_view.py` (`HistoryView`)**: Dialog displaying historical report records from `report_history.json`. Supports instant loading into the workspace preview or opening in native system applications.
* **`app/views/settings_view.py` (`SettingsView`)**: Dialog for configuring Ollama connection parameters, model selection, execution timeouts, and row caps. Includes an interactive live connectivity test.

### 2. Concurrency & Threading Layer (`app/workers/`)
* **`app/workers/agent_worker.py` (`AgentWorker`)**: Subclasses `QThread`. Runs a private `asyncio` event loop so that asynchronous HTTP requests to Ollama and stdio IPC calls to the FastMCP server never block the GUI thread.
* **`queue.Queue` Cross-Thread Approval Bridge**: When the agent requires SQL execution confirmation, `AgentWorker` emits a Qt signal to the main thread with a thread-safe `queue.Queue[bool]`. The worker thread pauses on `queue.get()`, the UI thread displays `SqlApprovalDialog`, and the user's choice is returned via `queue.put()`.

### 3. Agent Orchestration Layer (`agent/`)
* **`agent/orchestrator.py` (`AgentOrchestrator`)**: Drives the multi-turn conversational loop, intent steering (PDF default vs explicit CSV), event broadcasting, and SQL approval verification.
* **`agent/ollama_client.py` (`OllamaClient`)**: High-performance HTTP client using `httpx.AsyncClient`. Connects exclusively to local hosts, validates endpoints, parses native function calling schemas, extracts CoT `<think>` tags, and supports structured JSON fallback.
* **`agent/tool_handler.py` (`ToolHandler`)**: Security whitelist gateway for MCP tools. Validates tool arguments against strict schemas, sanitizes parameters, enforces tool timeouts, and prevents schema corruption from nullable types.
* **`agent/conversation.py` (`ConversationManager`)**: Manages conversation history within context window bounds (`num_ctx = 8192`). Guarantees that assistant tool calls and their corresponding tool execution results are never split across context compaction boundaries.

### 4. Protocol Layer (`mcp_layer/`)
* **`mcp_layer/server.py`**: FastMCP stdio server registering the 6 tools and configuring process isolation and file-only logging (suppressing console output to prevent JSON-RPC pipe pollution).
* **`mcp_layer/client.py` (`MCPStdioClient`)**: Manages the child subprocess lifecycle and executes JSON-RPC 2.0 tool calls over stdio. Automatically detects development mode (`python -m mcp_layer.server`) versus packaged executable mode (`sys.executable --mcp-server`).
* **Tool Modules (`mcp_layer/tools/`)**: Modular packages for `database_tools.py`, `sql_tools.py` (housing `validate_and_prepare_sql`, the custom Python lexical tokenizer `_tokenize_sql`, and SQLite `EXPLAIN QUERY PLAN` validation using a read-only authorizer connection), and `reporting_tools.py`.

### 5. Storage & Database Layer (`database/`)
* **`database/importer.py`**: Batch-streaming importer converting raw CSV/ZIP datasets into `data/ecommerce.db` with foreign key constraints, indexes, and transactional rollbacks.
* **`database/schema_inspector.py`**: Reusable introspection utility extracting table names, SQLite column affinities, primary keys, foreign keys, and row counts without hardcoded assumptions.
* **`database/query_executor.py`**: Read-only query execution engine enforcing `mode=ro`, `PRAGMA query_only = ON`, hard row limits, query timeouts, and a low-level SQLite C-authorizer.
* **`database/connection.py`**: SQLite connection helpers providing URI percent-encoding, `mode=ro`, and read-write connection factories.

### 6. Reporting Layer (`reporting/`)
* **`reporting/pdf_generator.py`**: ReportLab engine generating paginated, publication-quality PDF documents with executive summary cards, KPI blocks, formatted tabular grids, auto-wrapping, and running headers/footers (`Page X of Y`).
* **`reporting/csv_generator.py`**: RFC-4180 compliant CSV generator handling UTF-8 encoding, null value representations (`""`), and quoting.
* **`reporting/report_manager.py`**: Manages report file naming, atomic filesystem writes, directory traversal prevention, and catalog updates in `reports/report_history.json`.

---

## 4. Concurrency & Communication Model

1. **GUI Main Thread**: Runs the Qt 6 event loop (`QApplication.exec()`). Manages visual component rendering, animations, user input events, and modal dialog presentation.
2. **Agent Worker Thread (`QThread`)**: Executes background inference and MCP communication. Runs a dedicated `asyncio` event loop.
3. **MCP Subprocess**: Spawns an isolated Python child process communicating strictly over anonymous standard input/output pipes (`sys.stdin` / `sys.stdout`).
4. **Ollama Daemon**: External local service running at `http://localhost:11434`. Handled asynchronously via non-blocking HTTP requests.

---

## 5. Execution Modes

* **Development Mode (from source)**:
  - Invoked with `.venv/bin/python run_app.py`.
  - Child MCP server is spawned via `[sys.executable, "-m", "mcp_layer.server"]`.
  - Storage paths resolve relative to the repository root.
* **Packaged Mode (`sys.frozen`)**:
  - Invoked via standalone executable or macOS bundle (`ReportSQLAgent.app`).
  - Read-only bundled assets (reference database, fonts) resolve from `sys._MEIPASS` (`resource_root()`).
  - Mutable application state (custom settings, generated PDF/CSV reports, log files, report history) resolves from standard operating system user application directories (`user_data_root()`):
    - macOS: `~/Library/Application Support/ReportSQLAgent`
    - Windows: `%APPDATA%\ReportSQLAgent`
    - Linux: `~/.local/share/ReportSQLAgent`
  - Child MCP server is spawned directly via `[sys.executable, "--mcp-server"]`, removing any dependency on external or system Python installations.

