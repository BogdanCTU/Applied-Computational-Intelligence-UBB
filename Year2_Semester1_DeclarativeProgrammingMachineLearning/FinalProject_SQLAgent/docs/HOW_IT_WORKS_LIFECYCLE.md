# End-to-End System Execution Lifecycle

**Project**: Local Report SQL Agent  
**Language**: Python 3.11+ / PySide6 / SQLite / FastMCP  
**Parent Document**: [COMPLETE_SYSTEM_REFERENCE.md](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/docs/COMPLETE_SYSTEM_REFERENCE.md)

---

## 1. Overview of the Execution Flow

When a user submits a natural language request in the desktop interface, the Local Report SQL Agent executes a deterministic 13-stage lifecycle. Concurrency guarantees ensure that the PySide6 Qt GUI never freezes, security gates verify every SQL statement, and reporting engines guarantee mathematical accuracy.

```
[1. User Input in GUI] ──► [2. Worker Thread Dispatch] ──► [3. Intent Analysis & Planning]
                                                                     │
[6. Ollama Local Inference] ◄── [5. Context Allocation (128K)] ◄── [4. Skill & Memory Retrieval]
         │
         ▼
[7. FastMCP Query Validation] ──► [8. Human-in-the-Loop Review Gate]
                                              │ (Approved)
                                              ▼
[11. PDF/CSV Report Generation] ◄── [10. Canonical Dataset] ◄── [9. Read-Only SQL Execution]
         │                                                            (With Self-Healing)
         ▼
[12. Checkpoint Persistence] ──► [13. Native PDF GUI Rendering]
```

---

## 2. Step-by-Step Lifecycle Walkthrough

### Phase 1: Input Submission & Worker Thread Dispatch
1. The user types a query in the [`ChatView`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/views/chat_view.py) input bar (e.g., `"Generate a monthly revenue report for 2024 with a trend line chart and top products table"`).
2. `ChatView` emits `prompt_submitted(str)`.
3. [`MainWindow`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/main_window.py) receives the signal:
   - Validates that no agent task is currently running.
   - Appends a user message bubble to the chat feed.
   - Instantiates [`AgentWorker`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/workers/agent_worker.py) (subclassing `QThread`) to run the asynchronous task off the GUI thread.
   - Updates the status pill to `"Thinking..."`.

### Phase 2: Intent Analysis & Task Planning
1. `AgentWorker` invokes `AgentOrchestrator.run(user_prompt, approval_cb, progress_cb)`.
2. [`AgentOrchestrator`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/orchestrator.py) analyzes the intent:
   - Evaluates desired output format (PDF document vs CSV tabular export).
   - Detects chart preferences (line charts, bar charts, heatmaps, treemaps) and reporting timeframes.
3. [`TaskPlanner`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/task_planner.py) decomposes the request into ordered, machine-decidable execution steps:
   - Step 1: `INSPECT_SCHEMA` (discover table columns and relationships).
   - Step 2: `GENERATE_SQL` (formulate read-only SQL query).
   - Step 3: `EXECUTE_SQL` (execute query and collect tabular dataset).
   - Step 4: `GENERATE_REPORT` (compile dynamic PDF report with charts and KPIs).
4. [`TaskManager`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/task_manager.py) registers the new task in `PENDING` state and writes it to `data/agent_memory.db`.

### Phase 3: Checkpointing & State Snapshotting
1. [`CheckpointManager`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/checkpoint_manager.py) records snapshot `TASK_CREATED`.
2. Upon plan validation, records snapshot `PLAN_READY` capturing the initial plan steps.
3. This guarantees that if a system crash or restart occurs, the state can be recovered without re-running previous steps or losing context.

### Phase 4: Stage Domain Skill & Memory Retrieval
1. [`SkillManager`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/skill_manager.py) loads domain skills specific to the current stage:
   - Planning Stage: loads `skills/sql/SKILL.md` (SQLite join patterns, date functions, indexing rules).
   - Reporting Stage: loads `skills/reporting/SKILL.md` (visual layout rules, chart types, KPI structure).
2. [`SQLiteMemoryRepository`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/memory/repository.py) queries persistent memory for semantic domain facts (e.g., active fiscal year definitions, status codes) and relevant past query executions.

### Phase 5: Dynamic Context Window Assembly (128K Budget)
1. [`ContextBuilder`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/context_builder.py) queries the active configuration:
   - Effective context window: `131,072` tokens (128K).
   - Reserved model output: `1,024` tokens.
   - Safety buffer margin: `256` tokens.
   - Available input budget: $131,072 - 1,024 - 256 = 129,792$ tokens.
2. ContextBuilder packages content into discrete priority buckets:
   - **`MANDATORY` (100)**: System instructions, stage guidelines, sanitized user prompt.
   - **`HIGH` (75)**: Stage domain skills, target table schemas.
   - **`MEDIUM` (50)**: Structured task state, recent tool results, active chat dialogue.
   - **`LOW` (25)**: Semantic facts, historical execution logs.
3. Optional sections that do not fit in remaining capacity are completely excluded and recorded in [`ContextBuildReport`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/context_models.py). No silent truncation is permitted.

### Phase 6: Ollama Local Inference & Tool Dispatch
1. [`OllamaClient`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/ollama_client.py) formats an HTTP `POST` payload to `http://localhost:11434/api/chat`:
   - Passes assembled messages.
   - Supplies the authorized MCP tool schemas.
   - Sets option `options: {"num_ctx": 131072}` to enforce the 128K window at the Ollama runtime level.
2. Ollama evaluates the prompt using `qwen3.5:4b` and emits a structured tool call:
   ```json
   {
     "name": "prepare_sql_query",
     "arguments": {
       "query": "SELECT strftime('%Y-%m', order_date) AS month, SUM(total_amount) AS revenue FROM orders WHERE order_status = 'delivered' GROUP BY month ORDER BY month ASC;"
     }
   }
   ```
3. [`ToolHandler`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/tool_handler.py) validates argument types and prepares the call.

### Phase 7: FastMCP Subprocess Tool Invocation
1. [`MCPStdioClient`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/client.py) sends a JSON-RPC 2.0 `tools/call` message across stdio to the child FastMCP server.
2. The FastMCP server dispatches to `prepare_sql_query()` in [`sql_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/sql_tools.py):
   - AST validation scans for forbidden keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`).
   - Runs `EXPLAIN QUERY PLAN` against `data/ecommerce.db` to verify syntax and index utilization.
   - Formats SQL with consistent indentation.
3. FastMCP server returns validation output to `ToolHandler`.

### Phase 8: Human-in-the-Loop SQL Review Gate
1. `AgentOrchestrator` determines that an executable query is prepared.
2. Invokes the injected `approval_cb(sql, rationale)`.
3. `AgentWorker` forwards the request across threads to the main Qt GUI thread using thread-safe signals.
4. [`SqlApprovalDialog`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/dialogs/sql_approval_dialog.py) opens as a modal window:
   - Displays the formatted SQL query with syntax highlighting ([`SqlHighlighter`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/widgets/sql_highlighter.py)).
   - Details affected tables (`orders`) and estimated row scan.
   - Prompts user to click **Approve Query** or **Deny Query**.
5. The user inspects the query and clicks **Approve Query**.
6. The modal dialog closes, and `approval_cb` returns `True` to the waiting worker thread.

### Phase 9: Bounded Read-Only Query Execution
1. Orchestrator dispatches `execute_readonly_sql(query, max_rows=5000)` via MCP.
2. Inside [`QueryExecutor`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/database/query_executor.py):
   - Opens connection using `file:ecommerce.db?mode=ro` URI.
   - Sets `PRAGMA query_only = ON`.
   - C-authorizer verifies only `SQLITE_SELECT` and `SQLITE_READ` actions.
   - VM Opcode watchdog (`sqlite3_progress_handler`) enforces 30-second timeout.
   - Fetches rows with `cursor.fetchmany(max_rows + 1)`.
3. Returns column names, data rows, record count, and duration (e.g., `12` rows in `18.4 ms`).

### Phase 10: Self-Healing SQL Recovery Loop (Conditional)
* If query validation or execution fails (e.g., column does not exist or invalid SQLite function):
  1. The exact SQLite error code and message are captured.
  2. Orchestrator records snapshot `ERROR_RECOVERY`.
  3. `TaskPlanner.replan_failed_step()` generates a corrective plan: re-inspects table schema for true column names and reformulates the SQL query.
  4. The query enters Phase 7 and Phase 8 again (up to 3 automated self-healing iterations).

### Phase 11: Canonical Dataset & Dynamic Report Generation
1. [`CanonicalSQLDataset`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/canonical_data.py) ingests the SQL results as the authoritative Single Source of Truth:
   - Converts numeric strings to validated floats.
   - Computes deterministic KPIs (Total Revenue, Average Monthly Revenue, Peak Month, Transaction Count).
2. Orchestrator synthesizes chart specifications based on prompt intent (e.g., historical line chart of monthly revenue).
3. Dispatches `generate_pdf_report()` to FastMCP:
   - [`DynamicPdfComposer`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/dynamic_pdf_composer.py) constructs ReportLab Platypus elements.
   - Builds corporate header, KPI summary grid, vector charts ([`ChartBuilder`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/chart_builder.py)), formatted tables with alternating row colors, analytical takeaways, and SQL appendix.
   - Emits a publication-grade PDF file to `reports/monthly_revenue_report_20261108_220324.pdf`.

### Phase 12: Memory Persistence & Final Checkpoints
1. `TaskManager.complete_step()` marks all steps as `COMPLETED`.
2. `CheckpointManager.create_checkpoint(TASK_COMPLETED)` commits final task snapshot.
3. Metadata is written to `reports/report_history.json` and `data/agent_memory.db`.
4. `AgentOrchestrator.run()` returns [`AgentRunResult`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/orchestrator.py) (`status="success"`).

### Phase 13: GUI Workspace Rendering & Observability Update
1. `AgentWorker` emits `run_completed(AgentRunResult)` to the main Qt GUI thread.
2. `MainWindow` handles the completion signal:
   - Appends assistant response bubble with report summary and action buttons (Open PDF, Open Containing Folder).
   - Loads the PDF file in [`ReportPreviewWidget`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/widgets/report_preview_widget.py), rendering the multi-page document inside native `QPdfView`.
   - Populates the SQL Preview tab with formatted query code and copy button.
   - Updates [`ActivityInspectorWidget`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/widgets/activity_inspector_widget.py) with final token utilization, category breakdown, and execution event logs.
   - Status pill resets to `"Ready"`.

