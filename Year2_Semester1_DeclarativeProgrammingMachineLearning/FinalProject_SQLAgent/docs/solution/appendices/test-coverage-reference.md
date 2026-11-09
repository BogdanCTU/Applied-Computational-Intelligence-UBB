# Appendix F — Test Coverage Reference

## 1. Automated Test Suite Summary

- **Total Test Modules (`tests/test_*.py`)**: `35`
- **Total Test Functions (`def test_*`)**: `388`
- **Total Collected Pytest Items (with `@pytest.mark.parametrize`)**: `439`
  - **Deterministic Offline Suite (`-k "not live"`)**: `437 passed` (`~22s` execution time)
  - **Live Local Ollama `qwen3.5:4b` Suite (`-k "live"`)**: `2` E2E tests (`test_live_local_ollama_integration_end_to_end` in `test_agent.py` and `test_13_live_ollama_qwen_reporting_workflow` in `test_mcp_tool_discovery_and_capability.py`)

---

## 2. Complete Inventory of Test Modules (`tests/`)

| # | Test File | Test Functions | Primary Subsystems & Invariants Tested |
| :--- | :--- | :--- | :--- |
| 1 | `tests/test_advanced_visualization_engine.py` | `5` (parametrized across 25 chart types) | `ChartRegistry` registration, validation, and ReportLab vector PDF rendering for all 25 chart type keys. |
| 2 | `tests/test_agent.py` | `54` | `OllamaClient` loopback security, `<think>` stripping, native/JSON tool parsing, `ConversationMemory`, `ToolHandler`, `AgentOrchestrator`, and live Ollama E2E. |
| 3 | `tests/test_agent_intelligence_integration.py` | `6` | End-to-end integration of `TaskPlanner`, `TaskManager`, `SkillManager`, `ContextBuilder`, `CheckpointManager`, and `SQLiteMemoryRepository`. |
| 4 | `tests/test_approval_config.py` | `8` | `require_sql_approval=False` (automated read-only execution) vs. `require_sql_approval=True` (modal `SqlApprovalDialog` approval/rejection) and `SettingsView` persistence. |
| 5 | `tests/test_checkpoint_manager.py` | `6` | `CheckpointManager.create_checkpoint()`, `restore_checkpoint()`, and `RecoveryValidator` SHA-256 tamper detection. |
| 6 | `tests/test_checkpoint_models.py` | `6` | `TaskCheckpoint` deterministic SHA-256 checksum calculation, serialization, and schema version validation. |
| 7 | `tests/test_checkpoint_repository.py` | `5` | SQLite persistence of `task_checkpoints`, sequence numbering, and `interrupted_operations` idempotency keys. |
| 8 | `tests/test_context_builder.py` | `13` | `ContextBuilder` budget allocation, `MANDATORY` vs. optional priority ordering, `ContextBudgetExceededError`, and `ContextBuildReport`. |
| 9 | `tests/test_context_models.py` | `8` | `ExecutionStage`, `SectionPriority`, `ContextComponentBreakdown`, and `ContextBuildReport.summary_text()`. |
| 10 | `tests/test_context_relevance.py` | `5` | Stage-specific `STAGE_PRIORITIES` and keyword relevance tie-breaking in `ContextBuilder`. |
| 11 | `tests/test_context_security.py` | `6` | `ContextBuilder.sanitize_text()` stripping ASCII control characters and prompt-injection markers. |
| 12 | `tests/test_context_window.py` | `15` | `32K`/`64K`/`128K`/`256K` context window presets, `resolve_effective_context_window()`, clamping, and GUI `SettingsView` selector. |
| 13 | `tests/test_database.py` | `20` | `data/ecommerce.db` integrity (`499,385` rows, 7 tables, FK checks), `compare_databases()`, `connect_readonly()`, and `import_dataset()`. |
| 14 | `tests/test_database_discovery_reporting.py` | `8` | Dynamic schema reflection (`inspect_schema`) feeding multi-table SQL queries and PDF/CSV report generation. |
| 15 | `tests/test_dynamic_pdf_milestone9.py` | `5` | `ReportSpecification`, `compose_dynamic_pdf()`, multi-section layouts, KPI cards, and landscape orientation (`>6` columns). |
| 16 | `tests/test_e2e_workflows.py` | `8` | Full orchestrator + GUI worker workflows: PDF/CSV generation, SQL self-correction, approval denial, and cooperative cancellation. |
| 17 | `tests/test_gui.py` | `21` | Headless PySide6 (`QT_QPA_PLATFORM=offscreen`) tests for `MainWindow`, `ChatView`, `ReportPreviewWidget`, `CsvTableModel`, `HistoryView`, `SettingsView`, and `SqlApprovalDialog`. |
| 18 | `tests/test_macos_startup.py` | `7` | `run_app.py`, `app.main:main("--smoke-test")`, `--mcp-server` dispatch, and `config/paths.py` frozen vs. user-data path routing. |
| 19 | `tests/test_mcp_reliability.py` | `5` | `MCPClientManager` persistent session reuse, transient `BrokenPipeError` recovery (`_reset_session`), and concurrent lock safety. |
| 20 | `tests/test_mcp_tool_discovery_and_capability.py` | `8` (`13` parametrized items) | Complete 12-stage MCP discovery audit: subprocess handshake, `list_tools()`, `ToolRegistry` 6-tool completeness gate, `/api/chat` `tools` payload, all 6 tool executions, and live `qwen3.5:4b` E2E workflow. |
| 21 | `tests/test_mcp_tools.py` | `4` | Direct MCP server/client contract tests for `inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, and `generate_csv_report`. |
| 22 | `tests/test_memory_migrations.py` | `9` | Idempotent execution of `001_initial_schema.sql`, `002_checkpoint_recovery.sql`, and `003_skill_registry_enhancements.sql`. |
| 23 | `tests/test_memory_repository.py` | `18` | `SQLiteMemoryRepository` CRUD for tasks, plans, steps, decisions, tool calls, artifacts, semantic facts, and `ecommerce.db` separation guard. |
| 24 | `tests/test_reporting.py` | `10` | `generate_pdf_file()`, `generate_csv_file()`, `sanitize_filename_stem()`, path-traversal blocking (`ReportSecurityError`), and `ReportHistoryManager`. |
| 25 | `tests/test_reporting_accuracy.py` | `16` | `CanonicalSQLDataset`, deterministic KPI calculations, `ReportConsistencyValidator`, pie chart Top-7 + `"Other"` 100% normalization, and `calculate_previous_calendar_month()`. |
| 26 | `tests/test_skill_manager.py` | `11` | `SkillManager.discover_skills()`, frontmatter parsing, and `skill_registry` synchronization. |
| 27 | `tests/test_skill_models.py` | `14` | `SkillDefinition`, `SkillSection`, `SkillMetadata`, and section slice extraction. |
| 28 | `tests/test_skill_security.py` | `8` | `SkillManager._scan_security()` blocking `<script>`, `eval()`, destructive SQL, and prompt-injection patterns. |
| 29 | `tests/test_skill_selection.py` | `9` | Stage-aware and tool-aware skill selection in `SkillManager.get_context_for_step()`. |
| 30 | `tests/test_sql_validation.py` | `6` (parametrized across 25+ SQL attack queries) | `validate_readonly_sql()` and `_readonly_authorizer` blocking all DML/DDL/PRAGMA/ATTACH/multi-statement attacks while permitting complex CTEs and window functions. |
| 31 | `tests/test_task_manager.py` | `18` | `TaskManager` lifecycle transitions, `validate_plan_dag()` cycle detection (Kahn's algorithm), and step readiness promotion. |
| 32 | `tests/test_task_manager_sqlite.py` | `4` | `TaskManager` backed by persistent `SQLiteMemoryRepository`. |
| 33 | `tests/test_task_models.py` | `11` | `AgentTask` and `TaskStep` state machine transition rules (`InvalidStateTransitionError`). |
| 34 | `tests/test_task_planner.py` | `18` | `TaskPlanner.generate_plan()` JSON parsing, tool whitelisting, and deterministic 4-step fallback plan synthesis. |
| 35 | `tests/test_task_recovery.py` | `13` | `CheckpointManager.recover_task()` across Scenarios A, B, C, D, E, and F under `AUTOMATIC_SAFE`, `REQUIRE_CONFIRMATION`, and `MANUAL_ONLY` policies. |

