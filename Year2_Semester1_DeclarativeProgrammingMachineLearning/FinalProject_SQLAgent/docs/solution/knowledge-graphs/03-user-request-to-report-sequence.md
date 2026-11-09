# Knowledge Graph 03 — End-to-End User Request to Report Sequence

## 1. Complete Multi-Turn Request-to-Report Execution Trace

```mermaid
sequenceDiagram
    autonumber
    participant User as Business Analyst
    participant UI as ChatView / MainWindow
    participant AW as AgentWorker (QThread)
    participant Orch as AgentOrchestrator
    participant TP as TaskPlanner & TaskManager
    participant CB as ContextBuilder
    participant Ollama as Local Ollama (qwen3.5:4b)
    participant TH as ToolHandler & ToolRegistry
    participant MCP as FastMCP Server Subprocess
    participant DB as SQLite (ecommerce.db)
    participant Rep as Reporting Engine (CanonicalSQLDataset + ReportLab)

    User->>UI: Enter prompt ("Executive sales report for last month by category")
    UI->>AW: Launch AgentWorker(orchestrator, message)
    AW->>Orch: await process_message(user_message)

    opt First Request in Session (not _initialized)
        Orch->>TH: await tool_handler.initialize()
        TH->>MCP: Connect stdio + list_tools() (6 tools)
        MCP-->>TH: 6 MCPToolSpec schemas
        Orch->>TH: Execute inspect_database_schema()
        TH->>MCP: call_tool("inspect_database_schema")
        MCP->>DB: PRAGMA table_info / foreign_key_list / COUNT(*)
        DB-->>Orch: Cached DatabaseSchema (7 tables, 499,385 rows)
    end

    Note over Orch,TP: Phase 1: Task Creation & DAG Planning
    Orch->>TP: create_task(user_message) -> TaskStatus.PENDING
    Orch->>TP: await generate_plan(task_id, user_message, schema_summary)
    TP->>Ollama: POST /api/chat (Planning prompt)
    Ollama-->>TP: Structured JSON steps (or deterministic 4-step fallback)
    TP->>TP: validate_plan_dag() (Kahn's algorithm) & register_plan()
    Orch->>TP: start_task(task_id) -> TaskStatus.RUNNING

    Note over Orch,Rep: Phase 2: Iterative Tool-Calling Loop (Stages -> Context -> Ollama -> MCP)
    loop Up to max_iterations (20)
        Orch->>CB: build_context(stage, user_request, discovered_tools, schema, skills, memory, history)
        CB-->>Orch: AssembledContext + ContextBuildReport (128K window)
        Orch->>Ollama: POST /api/chat (messages + tools=6 MCP tool schemas)
        Ollama-->>Orch: OllamaResponse (thinking + tool_calls)

        alt Tool Call == "prepare_sql_query"
            Orch->>TH: execute_tool("prepare_sql_query")
            TH->>MCP: call_tool("prepare_sql_query", {sql_query})
            MCP->>DB: validate_readonly_sql() + EXPLAIN QUERY PLAN
            DB-->>Orch: status="valid", query_plan=[...]
        else Tool Call == "execute_readonly_sql"
            Orch->>TH: execute_tool("execute_readonly_sql", approval_callback)
            TH->>MCP: call_tool("execute_readonly_sql", {sql_query})
            MCP->>DB: connect_readonly(mode=ro) + Authorizer + SELECT
            DB-->>TH: columns + full_rows (cached in _latest_sql_result) + 50-row preview
            TH-->>Orch: ToolExecutionResult (preview JSON for LLM)
        else Tool Call == "generate_pdf_report"
            Orch->>TH: execute_tool("generate_pdf_report")
            TH->>TH: Inject full cached rows from _latest_sql_result
            TH->>MCP: call_tool("generate_pdf_report", enriched_args)
            MCP->>Rep: CanonicalSQLDataset -> KPIs -> ChartRegistry -> compose_dynamic_pdf()
            Rep-->>MCP: Atomic write reports/<stem>_<ts>_<id>.pdf + report_history.json
            MCP-->>Orch: ReportMetadata (output_path, page_count, charts_rendered)
            Orch-->>UI: Emit REPORT_GENERATED -> ReportPreviewWidget.load_report(pdf_path)
        end
    end

    Note over Orch,UI: Phase 3: Final Executive Summary & Task Completion
    Ollama-->>Orch: Final assistant response (no more tool_calls)
    Orch->>TP: Complete remaining steps -> TaskStatus.COMPLETED
    Orch-->>AW: AgentRunResult(status="success", final_message, generated_reports)
    AW-->>UI: signals.finished.emit(result)
    UI-->>User: Display formatted executive summary + interactive PDF in workspace
```

The sequence diagram above traces the complete lifecycle of a user reporting prompt across all 11 runtime participants.

---

## 2. Data Handoff Checkpoints Along the Pipeline

1. **Schema Handoff**: `inspect_database_schema` caches `self._cached_schema_text` on `AgentOrchestrator` and seeds `semantic_facts` in `data/agent_memory.db` so subsequent turns do not need redundant schema queries.
2. **Full-Row Dataset Handoff**: `execute_readonly_sql` returns both `records` (capped at `llm_preview_rows = 50` for the LLM context window) and `full_rows` (up to `100,000` rows), which `ToolHandler` stores in `self._latest_sql_result` and `self._sql_datasets` and automatically forwards into `generate_pdf_report` / `generate_csv_report`.
3. **Artifact Handoff**: As soon as `generate_pdf_report` or `generate_csv_report` completes, `AgentOrchestrator` emits `AgentEventType.REPORT_GENERATED`, allowing `MainWindow._on_report_generated()` to load the PDF into `ReportPreviewWidget` immediately while the LLM writes its final narrative response.
