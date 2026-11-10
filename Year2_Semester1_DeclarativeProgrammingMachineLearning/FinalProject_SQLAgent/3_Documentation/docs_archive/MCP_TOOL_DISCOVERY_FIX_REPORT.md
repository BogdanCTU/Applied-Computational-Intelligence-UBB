# MCP Tool Discovery and LLM Capability Awareness — Fix Report

## 1. Root-Cause Analysis

An end-to-end audit of the 12-stage initialization, MCP discovery, context assembly, and Ollama inference lifecycle revealed a 4-part chain of defects that caused the local `qwen3.5:4b` model to respond with:

```text
CAPABILITY_LIMITATION: I cannot generate PDF files, create graphical visualizations, or export data to files directly.
```

### Root Cause 1: Disconnected System Prompt in `ContextBuilder` (`agent/context_builder.py` & `agent/orchestrator.py`)
- `AgentOrchestrator.process_message()` called `system_prompt = build_system_prompt(self.settings, tool_mode=self.active_tool_mode)` on line 1063, **but never passed that `system_prompt` to the LLM**.
- Instead, `process_message()` called `self.conversation.get_messages_for_llm(system_prompt=assembled_ctx.system_prompt)` using the prompt assembled by `ContextBuilder.build()`.
- `ContextBuilder._build_base_system_instructions()` ignored `agent/system_prompt.py` and `config/prompts.py` (`DEFAULT_SYSTEM_PROMPT` and `JSON_FALLBACK_INSTRUCTIONS`), returning a hardcoded 5-line stub that mentioned neither the 6 MCP tools nor PDF/CSV report and chart generation capabilities.

### Root Cause 2: Ollama `0.40.14` `PARSER qwen3.5` XML Failure on `inspect_database_schema(table_name="")` (`mcp_layer/tools/database_tools.py` & `agent/tool_handler.py`)
- `inspect_database_schema` defined `table_name: str = ""` as optional with `"default": ""` and instructed the model: *"omit 'table_name' or pass empty string '' to list all tables"*.
- When `qwen3.5:4b` invoked `inspect_database_schema` with an empty string `""` in Qwen3.5's native XML tool-call format, Ollama `0.40.14`'s `PARSER qwen3.5` failed deterministically with:
  ```json
  HTTP 500 {"error":"XML syntax error on line 3: element <function> closed by </parameter>"}
  ```
- Similarly, `generate_pdf_report` and `generate_csv_report` required `columns`, `rows`, and `sql_query` in their MCP JSON Schemas even though `AgentOrchestrator._prepare_and_validate_report_args()` automatically binds `sql_query`, `columns`, `rows`, `datasets`, `kpis`, and `charts` from the executed `CanonicalSQLDataset`.

### Root Cause 3: Permanent Fallback to `mode="json"` with `tools=None` (`agent/orchestrator.py`)
- When the Turn 1 HTTP 500 XML parser error triggered `OllamaClient._fallback_chat_json()`, `AgentOrchestrator` permanently mutated `self.active_tool_mode = "json"` and set `ollama_tools = None` (`tools=0`).
- Because `ContextBuilder` also omitted `JSON_FALLBACK_INSTRUCTIONS` from `assembled_ctx.system_prompt`, every subsequent turn and user request was sent to Ollama with `mode=json`, `tools=0` (no native tools), and no tool definitions in the system prompt. Deprived of all tools and capability instructions, `qwen3.5:4b` output the `CAPABILITY_LIMITATION` refusal.

### Root Cause 4: Schema/Skill Mismatches and Missing Runtime Tool Registry Validation
- `ToolHandler.initialize()` did not validate that all 6 expected MCP tools were discovered with valid descriptions and input schemas, nor did it expose a structured `MCPToolRegistry` shared across `AgentOrchestrator`, `ToolHandler`, `ContextBuilder`, `system_prompt.py`, and `OllamaClient`.
- `OllamaClient.probe_tool_capability()` sent a dummy `[probe_tool]` `/api/chat` inference call before the first user request instead of checking `"tools"` in Ollama `/api/show` `capabilities`.
- `skills/sql/SKILL.md`, `skills/data_analysis/SKILL.md`, and `skills/data_validation/SKILL.md` referenced non-existent Olist column names (`order_purchase_timestamp`, `order_items.price`, `payments.payment_value`) instead of the actual `data/ecommerce.db` schema (`orders.order_date`, `orders.subtotal`, `orders.total_amount`, `order_items.line_total`, `payments.payment_id`, `payments.amount`).
- `TaskPlanner.create_fallback_plan()` referenced unregistered skill names (`"sql/schema_analysis"`, etc.) instead of the registered skill IDs (`"sql_generation"`, `"ecommerce_analysis"`, `"data_validation"`, `"report_design"`).
- `ContextBuilder._resolve_schema_text()` dumped raw `inspect_database_schema` dicts as 28 KB of indented JSON instead of a concise tabular summary with date ranges.
- `_synthesize_charts_from_intent()` in `agent/orchestrator.py` matched numeric columns by substring name without checking whether row values were numeric, and `save_artifact()` passed `file_size=` instead of `file_size_bytes=`.

---

## 2. Modified and Newly Created Files

### Modified Files
1. `mcp_layer/tools/database_tools.py` — Updated `inspect_database_schema_impl` and `register_database_tools` so `table_name="ALL"` (or `"*"` / `""`) inspects all tables and the tool description instructs passing `table_name='ALL'`.
2. `mcp_layer/tools/reporting_tools.py` — Made `description`, `sql_query`, `columns`, and `rows` optional defaults in `generate_pdf_report` and `generate_csv_report` so the LLM only needs to supply `title` and `description` while `AgentOrchestrator` binds the canonical dataset, KPIs, and charts.
3. `agent/tool_handler.py` — Added `EXPECTED_MCP_TOOLS`, `ToolDiscoveryError`, `DiscoveredTool`, and `MCPToolRegistry`; enforced 6-tool discovery validation in `ToolHandler.initialize()`; enhanced `_clean_schema_for_ollama()` to normalize schemas and mark `table_name` required on `inspect_database_schema` for Qwen3.5 XML parser compatibility; normalized `table_name="ALL"` to `""` in `validate_tool_request()`.
4. `config/prompts.py` — Updated `DEFAULT_SYSTEM_PROMPT` and `JSON_FALLBACK_INSTRUCTIONS` with explicit capability awareness (database inspection, SQL validation/execution, deterministic KPIs, PDF/CSV generation, and 22 chart types) and the 7 critical behavioral rules forbidding false `CAPABILITY_LIMITATION` refusals.
5. `agent/system_prompt.py` — Updated `build_system_prompt()` to accept `discovered_tools` (`MCPToolRegistry` or tool list) and `reporting_period`, formatting the active runtime tool registry into the system prompt.
6. `agent/context_builder.py` — Connected `ContextBuilder._build_base_system_instructions()` to `build_system_prompt()`; added `discovered_mcp_tools` high-priority context section; updated `STAGE_INSTRUCTIONS` with explicit MCP tool guidance; added `_format_schema_dict()` to format `inspect_database_schema` dictionary results concisely with table row counts, columns, foreign keys, and date ranges.
7. `agent/ollama_client.py` — Added `tool_registry` support; updated `probe_tool_capability()` to check Ollama `/api/show` `capabilities` (`"tools"`) first without firing a dummy LLM chat request; ensured `chat()` and `_fallback_chat_json()` include discovered MCP tools.
8. `agent/task_planner.py` — Updated `create_fallback_plan()` to reference registered skill IDs (`sql_generation`, `ecommerce_analysis`, `data_validation`, `report_design`).
9. `agent/orchestrator.py` — Exposed `orchestrator.tool_registry`; wired `MCPToolRegistry` into `OllamaClient`, `ContextBuilder`, and `build_system_prompt()`; surfaced explicit `MCPClientError` / `ToolHandlerError` initialization errors; preserved native MCP tools across reasoning iterations; added recovery guard against false `CAPABILITY_LIMITATION` responses; improved numeric column detection in `_synthesize_charts_from_intent()`; supplemented partial LLM chart lists with user-intent chart types; fixed `save_artifact(..., file_size_bytes=...)`; added mid-flight cancellation check after `ollama_client.chat()`.
10. `skills/sql/SKILL.md` — Updated SQLite date column examples to `orders.order_date`.
11. `skills/data_analysis/SKILL.md` — Updated metric formulas and join patterns to match `data/ecommerce.db` (`orders.subtotal`, `orders.total_amount`, `order_items.line_total`, `payments.payment_id`, `payments.amount`, `orders.channel`, `orders.status`).
12. `skills/data_validation/SKILL.md` — Updated dimension column names and dataset timeline (`2024-01-01` to `2026-09-29`).
13. `tests/test_approval_config.py` — Updated mocked `list_tools` fixture to include all 6 `EXPECTED_MCP_TOOLS`.

### Newly Created Files
1. `tests/test_mcp_tool_discovery_and_capability.py` — Comprehensive 13-scenario automated test suite covering MCP discovery, schema conversion, first-request tool injection, capability-aware system prompt assembly, `CAPABILITY_LIMITATION` recovery, end-to-end multi-chart PDF generation, discovery failure handling, and live local `qwen3.5:4b` acceptance testing.
2. `docs/MCP_TOOL_DISCOVERY_FIX_REPORT.md` — This engineering report.

---

## 3. MCP Discovery to Ollama Tool-Calling Architecture

1. **Subprocess Startup & Handshake (`MCPStdioClient.connect`)**:
   - Spawns `python -m mcp_layer.server` over stdio and completes the MCP protocol handshake.
2. **Authoritative Discovery & Validation (`ToolHandler.initialize`)**:
   - Calls `await self.mcp_client.list_tools()` and verifies that all 6 expected tools (`inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`) are present with non-empty descriptions and valid object `input_schema`s.
   - Populates `ToolHandler.registry` (`MCPToolRegistry`) with `DiscoveredTool` entries containing both the raw MCP `input_schema` and the normalized `ollama_schema`.
   - Raises `ToolDiscoveryError` immediately if 0 tools or incomplete tools are returned.
3. **Schema Normalization for Ollama (`_clean_schema_for_ollama`)**:
   - Converts each MCP tool's JSON Schema into Ollama's native `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}` format.
   - Flattens nullable `anyOf` unions, strips Pydantic `title`/`additionalProperties` metadata, ensures every parameter has a concrete `"type"`, and marks `table_name` required (`'ALL'` or specific table name) on `inspect_database_schema` so Ollama `0.40.14`'s `PARSER qwen3.5` never encounters an empty XML `<parameter>` tag.
4. **Capability-Aware Prompt & Context Assembly (`build_system_prompt` & `ContextBuilder`)**:
   - `AgentOrchestrator.initialize()` shares `self.tool_handler.registry` with `self.ollama_client.tool_registry` and `self.context_builder.tool_registry`.
   - Every stage context built by `ContextBuilder.build()` includes `DEFAULT_SYSTEM_PROMPT` (via `build_system_prompt()`) plus the `DISCOVERED MCP TOOLS (ACTIVE RUNTIME REGISTRY)` summary and active reporting period boundaries.
5. **Multi-Turn Tool Execution & PDF Generation (`AgentOrchestrator.process_message`)**:
   - On every iteration in `native` mode, all 6 Ollama function-tool definitions are passed in `payload["tools"]`.
   - Tool calls are validated and dispatched through `ToolHandler.execute_tool()` to the MCP subprocess, compacted via `compact_tool_result_for_llm()`, and returned as `role="tool"` messages until `generate_pdf_report` (or `generate_csv_report`) completes and the final summary is produced.

---

## 4. Test Results & Live `qwen3.5:4b` Acceptance Verification

### Automated Test Suite
- **MCP Tool Discovery & Capability Suite (`tests/test_mcp_tool_discovery_and_capability.py`)**:
  - `test_1_mcp_discovery_returns_all_six_tools_with_valid_schemas`: **PASSED**
  - `test_3_mcp_schemas_converted_to_ollama_function_tool_format`: **PASSED**
  - `test_4_first_ollama_request_includes_all_discovered_tools`: **PASSED**
  - `test_5_system_prompt_and_context_builder_include_full_capabilities`: **PASSED**
  - `test_6_orchestrator_recovers_if_model_emits_capability_limitation`: **PASSED**
  - `test_7_to_11_end_to_end_multi_chart_pdf_reporting_lifecycle`: **PASSED**
  - `test_12_mcp_discovery_failure_surfaces_explicit_error`: **PASSED**
  - `test_13_live_ollama_qwen_reporting_workflow` (Live `qwen3.5:4b` + real MCP server): **PASSED**
- **Full Repository Test Suite (`.venv/bin/pytest -k "not live" -q`)**:
  - **437 passed, 0 failed**

### Demonstration of the Example Request Reaching `generate_pdf_report`
Request tested against live `qwen3.5:4b`:
> `"Generate a PDF report for last month's orders, sales, revenue, and transactions. Include historical bar charts, distribution pie charts, matrix graphs, and data tables at the end."`

Observed live execution trace:
1. **MCP Initialization**: Connected to MCP server subprocess and registered all 6 tools (`inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, `execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`); `probe_tool_capability()` verified `"tools"` capability via `/api/show` (`active_tool_mode='native'`).
2. **Iteration 1 (`SCHEMA_DISCOVERY`)**: First `/api/chat` payload sent `tools=6` and the capability-aware system prompt. `qwen3.5:4b` returned HTTP 200 with native tool call `inspect_database_schema({"table_name": "ALL"})`.
3. **Iteration 2 (`SQL_GENERATION`)**: `qwen3.5:4b` inspected the 7 discovered tables (`customers`, `order_items`, `orders`, `payments`, `products`, `returns`, `shipments`) and called `prepare_sql_query` with a read-only `SELECT` query aggregating orders, sales, revenue, and transactions.
4. **Iteration 3 (`SQL_VALIDATION`)**: `qwen3.5:4b` called `execute_readonly_sql`, which auto-approved (`require_sql_approval=False`) and captured the canonical dataset into `session_datasets`.
5. **Iteration 4 (`REPORT_GENERATION`)**: `qwen3.5:4b` invoked `generate_pdf_report` (with deterministic KPIs, bar chart, distribution pie chart, matrix chart, and data summary table bound from `CanonicalSQLDataset`), producing a valid multi-page PDF file on disk (`%PDF-`, `> 10 KB`).
6. **Final Response**: Returned an executive summary with the generated PDF path and zero `CAPABILITY_LIMITATION` text.

---

## 5. Database & Constraint Verification

- `data/ecommerce.db` SHA-256 verified unchanged:
  `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`
- `data/raw/` untouched.
- All execution remained 100% local using `.venv` and local Ollama (`qwen3.5:4b`).

