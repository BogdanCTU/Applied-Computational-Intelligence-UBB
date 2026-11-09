# Appendix A — Glossary of Terms and Concepts

| Term / Symbol | Category | Definition in the Local Report SQL Agent |
| :--- | :--- | :--- |
| **`AgentOrchestrator`** | Agent Layer (`agent/orchestrator.py`) | The central coordinator driving MCP initialization, DAG planning, context building, multi-turn LLM tool calling, SQL self-correction, and report synthesis. |
| **`AgentTask` / `TaskStep`** | Planning (`agent/task_models.py`) | Pydantic v2 models representing a user reporting workflow (`AgentTask`) and its individual dependency-ordered execution units (`TaskStep`). |
| **`AgentWorker`** | GUI Concurrency (`app/workers/agent_worker.py`) | Background `QThread` that creates a dedicated `asyncio` event loop to execute `AgentOrchestrator.process_message()` without blocking the PySide6 UI thread. |
| **`CanonicalSQLDataset`** | Reporting (`reporting/canonical_data.py`) | Single Source of Truth (SSOT) data container wrapping SQLite `columns` and `rows` to compute deterministic KPIs, chart series, and consistency validations in Python. |
| **`ChartRegistry`** | Visualization (`reporting/chart_registry.py`) | Centralized registry of 25 ReportLab vector chart renderers (covering 22 canonical chart types across Comparison, Trend, Distribution, Relationship, Hierarchical, and Matrix categories). |
| **`CheckpointManager`** | Recovery (`agent/checkpoint_manager.py`) | Manages creation, SHA-256 verification, and restoration of `TaskCheckpoint` snapshots across Scenarios A through F. |
| **`ContextBuilder`** | Context Management (`agent/context_builder.py`) | Stage-aware token budgeting engine that prioritizes mandatory and optional context sections within the configured context window (`32K`, `64K`, `128K` default, `256K`). |
| **`DiscoveredTool` / `ToolRegistry`** | MCP Adapter (`agent/tool_handler.py`) | Runtime registry storing the 6 MCP tool schemas discovered via `list_tools()` and converting them into Ollama `/api/chat` `tools` definitions. |
| **Episodic Memory** | Memory (`memory/repository.py`) | Historical records of completed/failed task runs, SHA-256 checkpoints (`task_checkpoints`), and recovery audits (`recovery_attempts`) stored in `data/agent_memory.db`. |
| **`FastMCP`** | MCP Server (`mcp_layer/server.py`) | Official MCP SDK server class hosting the 6 `@mcp.tool()` functions over `stdin`/`stdout` JSON-RPC 2.0. |
| **`is_frozen()`** | Packaging (`config/paths.py`) | Helper returning `True` when running inside a PyInstaller bundle (`getattr(sys, "frozen", False)`), routing mutable files to `user_data_root()`. |
| **Kahn's Algorithm** | DAG Validation (`agent/task_manager.py`) | Topological sorting algorithm used by `validate_plan_dag()` to verify that `TaskPlan` steps contain zero cyclic dependencies. |
| **`llm_preview_rows`** | Database Config (`config/settings.py`) | Maximum number of rows (`50` default) included in the `role="tool"` JSON preview sent to the LLM, while full rows (`up to 100,000`) are cached in `ToolHandler._latest_sql_result` for PDF/CSV generation. |
| **MCP (Model Context Protocol)** | Architecture (`mcp_layer/`) | Open standard protocol used over `stdio` JSON-RPC 2.0 to decouple the agent orchestrator from database and reporting tool implementations. |
| **`_NumberedCanvas`** | PDF Engine (`reporting/pdf_generator.py`) | Two-pass ReportLab `canvas.Canvas` subclass that buffers page states in memory to stamp accurate `"Page X of Y"` footers on every page. |
| **`_progress_watchdog`** | SQL Security (`database/query_executor.py`) | SQLite VM progress callback invoked every 5,000 opcodes to enforce `query_timeout_s` (`120.0s`) and cooperative `cancel_event` cancellation. |
| **`_readonly_authorizer`** | SQL Security (`database/query_executor.py`) | SQLite connection authorizer callback (`con.set_authorizer`) permitting only `SQLITE_SELECT`, `SQLITE_READ`, safe `SQLITE_FUNCTION`, and `SQLITE_RECURSIVE`. |
| **Semantic Memory** | Memory (`memory/repository.py`) | Validated domain facts (`semantic_facts`) and discovered skill metadata (`skill_registry`) persisted in `data/agent_memory.db`. |
| **`SkillManager`** | Skills (`agent/skill_manager.py`) | Discovers, security-scans, and extracts stage-relevant slices from `skills/*/SKILL.md` (`sql`, `data_analysis`, `data_validation`). |
| **Working Memory** | Memory (`memory/repository.py`) | Active task execution state (`task_runs`, `task_plans`, `task_steps`, `task_decisions`, `task_tool_calls`, `task_artifacts`) persisted in `data/agent_memory.db`. |
