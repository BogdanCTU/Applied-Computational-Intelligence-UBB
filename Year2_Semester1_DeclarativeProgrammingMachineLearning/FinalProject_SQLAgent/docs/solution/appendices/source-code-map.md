# Appendix E — Source Code Map

This appendix provides a complete, file-by-file map of every source module in the Local Report SQL Agent repository.

---

## 1. Root & Packaging Files

| File Path | Key Symbols / Functions | Responsibility |
| :--- | :--- | :--- |
| `run_app.py` | `_fallback_log_fatal()`, `__main__` | Top-level application bootstrap with early crash log fallback (`logs/startup_crash.log`). |
| `ReportSQLAgent.spec` | `Analysis`, `PYZ`, `EXE`, `COLLECT`, `BUNDLE` | PyInstaller packaging specification for macOS `.app` and Windows `.exe`. |
| `requirements.txt` | — | Pinned runtime, GUI, MCP, reporting, testing, and packaging dependencies. |
| `.env.example` | `REPORT_AGENT_*` | Template of supported environment variable overrides. |

---

## 2. `config/` — Configuration, Paths, Prompts & Logging

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `config/__init__.py` | Package exports | Re-exports `AppSettings`, `load_settings`, `save_settings`. |
| `config/settings.py` | `AppSettings`, `OllamaSettings`, `DatabaseSettings`, `AgentSettings`, `ReportSettings`, `LoggingSettings`, `load_settings()`, `save_settings()` | 3-layer settings loader, `LOCAL_HOSTS` loopback validator, and context window presets (`32K`–`256K`). |
| `config/paths.py` | `is_frozen()`, `resource_root()`, `user_data_root()`, `resolve_path()`, `get_settings_path()`, `get_memory_database_path()` | Dual-mode path resolution separating read-only bundled assets from writable user data. |
| `config/prompts.py` | `DEFAULT_SYSTEM_PROMPT`, `JSON_TOOL_FALLBACK_INSTRUCTIONS` | Authoritative system prompt template with dynamic temporal anchors and tool rules. |
| `config/logging_setup.py` | `setup_logging()` | Rotating file logger (`2 MB × 3 backups`) shared by the GUI process and MCP server subprocess. |

---

## 3. `database/` — Read-Only SQLite Engine, Schema Discovery & Importer

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `database/connection.py` | `build_readonly_uri()`, `connect_readonly()`, `connect_readwrite()`, `quote_identifier()`, `is_valid_identifier()` | SQLite `mode=ro` URI builder, `PRAGMA query_only=ON`, and SQL identifier quoting. |
| `database/query_executor.py` | `QueryExecutionResult`, `validate_readonly_sql()`, `execute_readonly_query()`, `_readonly_authorizer()`, `_progress_watchdog()` | Lexical SQL validator, 23 forbidden keyword blocker, SQLite VM authorizer, and 5,000-opcode timeout/cancel watchdog. |
| `database/schema_inspector.py` | `DatabaseSchema`, `TableSchema`, `ColumnInfo`, `ForeignKeyInfo`, `IndexInfo`, `RelationshipInfo`, `inspect_schema()`, `get_table_sample()`, `validate_database_integrity()`, `compare_databases()` | Zero-assumption dynamic SQLite schema reflection, sampling, integrity check, and parity comparator. |
| `database/importer.py` | `ImportSummary`, `TableSpec`, `ColumnSpec`, `import_dataset()` | Streaming, transactional dataset builder from CSV directories, `.zip` archives, or reference `.sqlite` files. |

---

## 4. `mcp_layer/` — Model Context Protocol Server & Client

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `mcp_layer/server.py` | `mcp` (`FastMCP`), `run_stdio_server()` | Child MCP server registering the 6 `@mcp.tool()` functions over `stdio`. |
| `mcp_layer/client.py` | `MCPClientManager`, `MCPToolSpec`, `MCPToolCallResult` | Persistent `stdio_client` + `ClientSession` manager with `list_tools()`, `call_tool()`, and auto-reconnect. |
| `mcp_layer/tools/database_tools.py` | `inspect_database_schema()`, `get_table_sample()` | MCP tool implementations for schema discovery and table sampling. |
| `mcp_layer/tools/sql_tools.py` | `prepare_sql_query()`, `execute_readonly_sql()` | MCP tool implementations for `EXPLAIN QUERY PLAN` validation and read-only SQL execution. |
| `mcp_layer/tools/reporting_tools.py` | `generate_pdf_report()`, `generate_csv_report()` | MCP tool implementations for multi-page PDF and UTF-8 CSV report generation. |

---

## 5. `agent/` — Orchestration, Planning, Context, Skills & Recovery

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `agent/orchestrator.py` | `AgentOrchestrator`, `AgentRunResult`, `AgentEvent`, `AgentEventType` | Main autonomous workflow controller, multi-turn tool loop, SQL retry engine, and fallback report synthesizer. |
| `agent/ollama_client.py` | `OllamaClient`, `OllamaResponse`, `ToolCall` | Async HTTP client for local Ollama (`/api/chat`, `/api/show`, `/api/tags`, `/api/version`), `<think>` parser, and tool call extractor. |
| `agent/tool_handler.py` | `ToolHandler`, `ToolRegistry`, `DiscoveredTool`, `ToolExecutionResult`, `EXPECTED_MCP_TOOLS` | MCP tool discovery gate, Ollama function schema converter, full-row SQL cache, and tool dispatcher. |
| `agent/context_builder.py` | `ContextBuilder` | Token-budgeted, stage-aware context assembler and prompt-injection sanitizer. |
| `agent/context_models.py` | `ExecutionStage`, `SectionPriority`, `ContextSection`, `ContextBuildReport`, `AssembledContext` | Pydantic models and priority enums for `ContextBuilder`. |
| `agent/system_prompt.py` | `SystemPromptBuilder`, `build_system_prompt()` | Dynamic system prompt builder injecting current calendar period, discovered MCP tools, and schema summaries. |
| `agent/conversation.py` | `ConversationMemory`, `ConversationMessage` | Rolling multi-turn conversation buffer preserving unbroken `assistant` → `tool` call chains. |
| `agent/task_models.py` | `AgentTask`, `TaskPlan`, `TaskStep`, `TaskStatus`, `StepStatus`, `VALID_TASK_TRANSITIONS`, `VALID_STEP_TRANSITIONS` | Lifecycle state machines and Pydantic models for tasks and DAG steps. |
| `agent/task_manager.py` | `TaskManager`, `validate_plan_dag()`, `InMemoryTaskRepository` | Kahn's algorithm DAG validator, step readiness promoter, and task lifecycle controller. |
| `agent/task_planner.py` | `TaskPlanner` | LLM-assisted and deterministic fallback DAG task planner. |
| `agent/checkpoint_models.py` | `TaskCheckpoint`, `CheckpointType`, `RecoveryPolicy`, `RecoveryStatus`, `OperationStatus`, `RecoveryResult` | Versioned checkpoint models with deterministic SHA-256 payload hashing. |
| `agent/checkpoint_manager.py` | `CheckpointManager`, `RecoveryValidator` | Cryptographic checkpoint validator and Scenarios A–F crash recovery engine. |
| `agent/skill_models.py` | `SkillDefinition`, `SkillSection`, `SkillMetadata`, `SkillValidationStatus`, `SkillDiscoveryReport` | Data models for modular domain skills. |
| `agent/skill_manager.py` | `SkillManager` | YAML/Markdown skill loader, security scanner, and stage-aware slice selector. |
| `agent/events.py` | `ActivityEvent`, `ActivityCategory`, `mask_sensitive_data()` | Structured execution timeline events and recursive credential redaction. |

---

## 6. `memory/` — Persistent SQLite Memory Repository

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `memory/models.py` | `TaskDecision`, `TaskToolCallRecord`, `TaskArtifactRecord`, `SemanticFact`, `TaskHistoryItem` | Pydantic models for Working, Episodic, and Semantic memory records. |
| `memory/repository.py` | `SQLiteMemoryRepository` | Thread-safe WAL-mode SQLite repository managing `data/agent_memory.db`. |
| `memory/migrations/__init__.py` | `apply_migrations()` | Versioned SQL migration runner. |
| `memory/migrations/001..003.sql` | 11 SQLite tables & indexes | Schema definitions for tasks, steps, plans, decisions, tool calls, artifacts, semantic facts, skills, checkpoints, and recovery. |

---

## 7. `reporting/` — Canonical Data, Vector Charts, PDF & CSV Engines

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `reporting/canonical_data.py` | `CanonicalSQLDataset`, `ChartSpecification`, `TransformedChartData`, `ReportConsistencyValidator` | Single Source of Truth dataset container, deterministic KPI calculator, chart transformer, and consistency validator. |
| `reporting/chart_registry.py` | `ChartRegistry`, `extract_chart_data()`, 25 registered renderers | ReportLab vector chart rendering engine across 6 analytical categories. |
| `reporting/chart_builder.py` | `build_chart()` | Facade entry point delegating to `ChartRegistry.render()`. |
| `reporting/pdf_generator.py` | `generate_pdf_file()`, `_make_numbered_canvas()`, `_compute_column_widths()`, `_ensure_fonts_registered()` | Multi-page ReportLab PDF generator, Vera TrueType font loader, and `"Page X of Y"` canvas. |
| `reporting/dynamic_pdf_composer.py` | `compose_dynamic_pdf()`, `_build_table_flowable()` | Executive multi-section PDF composer rendering KPI grids, findings callouts, vector charts, and `LongTable` components. |
| `reporting/csv_generator.py` | `generate_csv_file()` | Single and multi-dataset UTF-8 CSV exporter. |
| `reporting/report_spec.py` | `ReportSpecification`, `ReportSection`, `ReportComponent`, `ChartConfiguration`, `TableConfiguration`, `ChartType` | Dataclass blueprints for dynamic multi-component reports. |
| `reporting/report_manager.py` | `ReportMetadata`, `ReportHistoryManager`, `sanitize_filename_stem()`, `resolve_safe_report_path()`, `normalize_tabular_data()` | Filename sanitizer, path-traversal guard, and atomic `reports/report_history.json` persistence. |
| `reporting/date_utils.py` | `ReportingPeriod`, `calculate_previous_calendar_month()` | Dynamic calendar period calculator for relative date queries. |

---

## 8. `app/` — PySide6 Desktop Graphical User Interface

| File Path | Key Classes & Functions | Responsibility |
| :--- | :--- | :--- |
| `app/main.py` | `main()`, `_show_fatal_error_dialog()`, `_install_global_exception_handler()` | 5-stage GUI startup, `--mcp-server` dispatch, and `--smoke-test` mode. |
| `app/main_window.py` | `MainWindow` | Primary split-pane desktop window, header status pill, and worker signal orchestration. |
| `app/style.py` | `APP_STYLESHEET` | Global dark-mode QSS stylesheet. |
| `app/views/chat_view.py` | `ChatView`, `ChatInputEdit` | Conversational panel, progress banner, and vertical splitter for `AgentActivityInspectorWidget`. |
| `app/views/history_view.py` | `HistoryView` | Modal dialog browsing `report_history.json` with workspace preview and external open actions. |
| `app/views/settings_view.py` | `SettingsView` | Configuration dialog for Ollama endpoint/model/context window, SQL approval toggle, and report settings. |
| `app/dialogs/sql_approval_dialog.py` | `SqlApprovalDialog` | Modal human-in-the-loop SQL review dialog with syntax highlighting and default focus on **Reject Execution**. |
| `app/widgets/report_preview_widget.py` | `ReportPreviewWidget` | Central workspace hosting native `QPdfView` (zoom/page controls) and `QTableView` (`CsvTableModel`). |
| `app/widgets/activity_inspector_widget.py` | `AgentActivityInspectorWidget`, `ActivityEventCard` | Live chronological execution timeline with expandable SQL, sanitized arguments, and context token reports. |
| `app/widgets/message_widget.py` | `MessageWidget` | Chat bubble with collapsible `<think>` reasoning viewer and strict HTML sanitizer. |
| `app/widgets/sql_preview_widget.py` | `SqlPreviewWidget` | Inline syntax-highlighted SQL card with clipboard copy button. |
| `app/widgets/sql_highlighter.py` | `SqlSyntaxHighlighter` | `QSyntaxHighlighter` coloring SQL keywords, functions, numbers, strings, and comments. |
| `app/models/csv_table_model.py` | `CsvTableModel` | `QAbstractTableModel` loading up to `5,000` preview rows from UTF-8/Latin-1 CSV files. |
| `app/workers/agent_worker.py` | `AgentWorker`, `OllamaCheckWorker` | `QThread` workers running dedicated `asyncio` event loops for agent execution and Ollama health checks. |
| `app/workers/worker_signals.py` | `WorkerSignals`, `OllamaCheckSignals` | Qt `Signal` definitions synchronizing background threads with `MainWindow`. |
