"""Comprehensive test suite for MCP Tool Discovery and LLM Capability Awareness.

Verifies:
1. MCP server initialization succeeds and returns all six expected tools.
2. Each discovered tool contains a valid name, non-empty description, and input schema.
3. Discovered MCP tool schemas convert cleanly into Ollama function-tool schema format.
4. The first Ollama request includes all 6 discovered tool definitions.
5. The system prompt (both via build_system_prompt and ContextBuilder) includes reporting,
   SQL, schema inspection, chart generation, PDF, and CSV capabilities.
6. The agent does not respond with CAPABILITY_LIMITATION when reporting tools are available
   (and recovers automatically if a model ever attempts a false capability refusal).
7. A reporting request invokes inspect_database_schema before generating SQL.
8. SQL is validated through prepare_sql_query before execution.
9. Approved/auto-approved SQL executes through execute_readonly_sql.
10. Query results are passed into generate_pdf_report.
11. A valid non-empty PDF file is created for the multi-chart reporting request:
    "Generate a PDF report for last month's orders, sales, revenue, and transactions.
     Include historical bar charts, distribution pie charts, matrix graphs, and data tables at the end."
12. If MCP tool discovery fails or returns zero/incomplete tools, the agent surfaces an
    explicit initialization/tool-discovery error rather than claiming PDF/chart generation is unsupported.
13. Live local Ollama (qwen3.5:4b) acceptance test verifying native MCP tool invocation and
    end-to-end PDF report generation without CAPABILITY_LIMITATION.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.context_builder import ContextBuilder
from agent.context_models import ExecutionStage
from agent.ollama_client import OllamaChatResponse, OllamaClient, OllamaToolCall
from agent.orchestrator import AgentEventType, AgentOrchestrator
from agent.system_prompt import build_system_prompt
from agent.tool_handler import (
    EXPECTED_MCP_TOOLS,
    MCPToolRegistry,
    PERMITTED_TOOLS,
    ToolDiscoveryError,
    ToolHandler,
)
from config.settings import AppSettings, load_settings
from mcp_layer.client import MCPClientError, MCPStdioClient, MCPToolSpec


EXAMPLE_USER_REQUEST = (
    "Generate a PDF report for last month's orders, sales, revenue, and transactions. "
    "Include historical bar charts, distribution pie charts, matrix graphs, and data tables at the end."
)


# ---------------------------------------------------------------------------
# 1 & 2. MCP Server Initialization & Six-Tool Discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_1_mcp_discovery_returns_all_six_tools_with_valid_schemas() -> None:
    """Tests 1 & 2: MCP server subprocess starts, handshakes, and returns all 6 expected tools."""
    settings = load_settings()
    async with MCPStdioClient(settings=settings) as client:
        handler = ToolHandler(client)
        specs = await handler.initialize()

        assert len(specs) == 6
        discovered_names = [s.name for s in specs]
        assert discovered_names == list(EXPECTED_MCP_TOOLS)
        assert set(discovered_names) == PERMITTED_TOOLS

        registry = handler.registry
        assert isinstance(registry, MCPToolRegistry)
        assert registry.is_complete is True
        assert registry.missing_tools == []

        for name in EXPECTED_MCP_TOOLS:
            tool = registry.get_tool(name)
            assert tool is not None
            assert tool.name == name
            assert isinstance(tool.description, str) and len(tool.description.strip()) > 15
            assert isinstance(tool.input_schema, dict)
            assert tool.input_schema.get("type") == "object"
            assert "properties" in tool.input_schema


# ---------------------------------------------------------------------------
# 3. Ollama Function-Tool Schema Conversion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_3_mcp_schemas_converted_to_ollama_function_tool_format() -> None:
    """Test 3: Discovered MCP tool schemas convert into valid Ollama function-tool schemas."""
    settings = load_settings()
    async with MCPStdioClient(settings=settings) as client:
        handler = ToolHandler(client)
        await handler.initialize()
        ollama_tools = handler.get_ollama_tools_schema()

        assert len(ollama_tools) == 6
        for idx, expected_name in enumerate(EXPECTED_MCP_TOOLS):
            t_def = ollama_tools[idx]
            assert t_def["type"] == "function"
            fn = t_def["function"]
            assert fn["name"] == expected_name
            assert isinstance(fn["description"], str) and fn["description"].strip()
            params = fn["parameters"]
            assert params["type"] == "object"
            assert isinstance(params["properties"], dict)
            # Every property must have an explicit 'type' for Ollama Go template / XML parser safety
            for prop_name, prop_schema in params["properties"].items():
                assert "type" in prop_schema, f"{expected_name}.{prop_name} missing 'type'"
                assert "title" not in prop_schema

        # Verify inspect_database_schema requires table_name ('ALL' or specific table) for Qwen3.5 XML parser
        inspect_fn = ollama_tools[0]["function"]
        assert inspect_fn["name"] == "inspect_database_schema"
        assert inspect_fn["parameters"]["required"] == ["table_name"]
        assert "ALL" in inspect_fn["parameters"]["properties"]["table_name"]["description"]


# ---------------------------------------------------------------------------
# 4. First Ollama Request Receives All 6 Discovered Tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_4_first_ollama_request_includes_all_discovered_tools(tmp_path: Path) -> None:
    """Test 4: The very first Ollama /api/chat request receives all 6 discovered MCP tool definitions."""
    settings = load_settings()
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.require_sql_approval = False

    captured_calls: list[dict[str, Any]] = []

    async def capture_chat(**kwargs: Any) -> OllamaChatResponse:
        captured_calls.append(dict(kwargs))
        return OllamaChatResponse(
            content="Schema inspected.",
            tool_calls=[],
        )

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(side_effect=capture_chat)

    async with MCPStdioClient(settings=settings) as mcp_client:
        orchestrator = AgentOrchestrator(
            settings,
            ollama_client=mock_ollama,
            mcp_client=mcp_client,
        )
        await orchestrator.initialize()

        assert orchestrator.tool_registry.is_complete is True
        assert orchestrator.ollama_client.tool_registry is orchestrator.tool_registry
        assert orchestrator.context_builder.tool_registry is orchestrator.tool_registry

        await orchestrator.process_message("List the tables in the database.")

        assert len(captured_calls) >= 1
        first_call = captured_calls[0]
        tools_sent = first_call.get("tools")
        assert isinstance(tools_sent, list)
        assert len(tools_sent) == 6
        sent_names = [t["function"]["name"] for t in tools_sent]
        assert sent_names == list(EXPECTED_MCP_TOOLS)


# ---------------------------------------------------------------------------
# 5. System Prompt & ContextBuilder Capability Awareness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_5_system_prompt_and_context_builder_include_full_capabilities() -> None:
    """Test 5: System prompt and ContextBuilder include all reporting, SQL, chart, PDF, and CSV capabilities."""
    settings = load_settings()
    async with MCPStdioClient(settings=settings) as client:
        handler = ToolHandler(client)
        await handler.initialize()

        sys_prompt = build_system_prompt(
            settings,
            tool_mode="native",
            discovered_tools=handler.registry,
        )
        builder = ContextBuilder(settings=settings, tool_registry=handler.registry)
        ctx = builder.build(
            ExecutionStage.SCHEMA_DISCOVERY,
            user_request=EXAMPLE_USER_REQUEST,
        )

        for prompt_text in (sys_prompt, ctx.system_prompt):
            assert "You are the Local Report SQL Agent assistant." in prompt_text
            assert "autonomous local reporting assistant" in prompt_text
            assert "inspect_database_schema" in prompt_text
            assert "get_table_sample" in prompt_text
            assert "prepare_sql_query" in prompt_text
            assert "execute_readonly_sql" in prompt_text
            assert "generate_pdf_report" in prompt_text
            assert "generate_csv_report" in prompt_text
            assert "bar charts" in prompt_text
            assert "pie/donut" in prompt_text
            assert "matrix/heatmap" in prompt_text
            assert "CAPABILITY_LIMITATION" in prompt_text
            assert "DISCOVERED MCP TOOLS (ACTIVE RUNTIME REGISTRY):" in prompt_text


# ---------------------------------------------------------------------------
# 6. Guard Against False CAPABILITY_LIMITATION Refusal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_6_orchestrator_recovers_if_model_emits_capability_limitation(tmp_path: Path) -> None:
    """Test 6: Orchestrator intercepts a false CAPABILITY_LIMITATION response and drives tool execution."""
    settings = load_settings()
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.require_sql_approval = False

    sql = (
        "SELECT strftime('%Y-%m', o.order_date) AS month, o.channel, o.status, "
        "COUNT(DISTINCT o.order_id) AS orders_count, ROUND(SUM(o.subtotal), 2) AS sales_amount, "
        "ROUND(SUM(o.total_amount), 2) AS total_revenue, COUNT(DISTINCT p.payment_id) AS transactions_count "
        "FROM orders o LEFT JOIN payments p ON o.order_id = p.order_id "
        "GROUP BY month, o.channel, o.status ORDER BY month"
    )

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            # Turn 1: Model mistakenly attempts to output CAPABILITY_LIMITATION without calling tools
            OllamaChatResponse(
                content=(
                    "CAPABILITY_LIMITATION: I cannot generate PDF files, create graphical visualizations, "
                    "or export data to files directly."
                ),
                tool_calls=[],
            ),
            # Turn 2: After orchestrator correction, model calls inspect_database_schema
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="inspect_database_schema",
                        arguments={"table_name": "ALL"},
                    )
                ],
            ),
            # Turn 3: Model validates SQL with prepare_sql_query
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(
                        id="c2",
                        name="prepare_sql_query",
                        arguments={"sql_query": sql, "explanation": "Aggregate metrics"},
                    )
                ],
            ),
            # Turn 4: Model executes SQL with execute_readonly_sql
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(
                        id="c3",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql},
                    )
                ],
            ),
            # Turn 5: Model calls generate_pdf_report
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(
                        id="c4",
                        name="generate_pdf_report",
                        arguments={
                            "title": "Monthly Orders, Sales, Revenue & Transactions Report",
                            "description": "Executive report with bar, pie, matrix charts, and tables.",
                        },
                    )
                ],
            ),
            # Turn 6: Final executive summary
            OllamaChatResponse(
                content="The PDF report has been generated with all requested charts and data tables.",
                tool_calls=[],
            ),
        ]
    )

    async with MCPStdioClient(settings=settings) as mcp_client:
        orchestrator = AgentOrchestrator(
            settings,
            ollama_client=mock_ollama,
            mcp_client=mcp_client,
        )
        res = await orchestrator.process_message(EXAMPLE_USER_REQUEST)

        assert res.is_success is True
        assert "CAPABILITY_LIMITATION" not in res.final_message
        assert len(res.generated_reports) == 1
        pdf_path = Path(res.generated_reports[0]["output_path"])
        assert pdf_path.is_file() and pdf_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# 7, 8, 9, 10, 11. Full End-to-End Multi-Chart Reporting Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_7_to_11_end_to_end_multi_chart_pdf_reporting_lifecycle(tmp_path: Path) -> None:
    """Tests 7-11: Verifies inspect_database_schema -> prepare_sql_query -> execute_readonly_sql -> generate_pdf_report."""
    settings = load_settings()
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.require_sql_approval = False

    sql = (
        "SELECT strftime('%Y-%m', o.order_date) AS month, "
        "o.channel AS sales_channel, "
        "o.status AS order_status, "
        "COUNT(DISTINCT o.order_id) AS orders_count, "
        "ROUND(SUM(o.subtotal), 2) AS sales_amount, "
        "ROUND(SUM(o.total_amount), 2) AS total_revenue, "
        "COUNT(DISTINCT p.payment_id) AS transactions_count "
        "FROM orders o "
        "LEFT JOIN payments p ON o.order_id = p.order_id "
        "GROUP BY month, o.channel, o.status "
        "ORDER BY month ASC, total_revenue DESC"
    )

    tool_invocation_order: list[str] = []

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Inspecting database schema.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_schema",
                        name="inspect_database_schema",
                        arguments={"table_name": "ALL"},
                    )
                ],
            ),
            OllamaChatResponse(
                content="Validating SQL query.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_prepare",
                        name="prepare_sql_query",
                        arguments={
                            "sql_query": sql,
                            "explanation": "Monthly and channel/status breakdown of orders, sales, revenue, and transactions.",
                        },
                    )
                ],
            ),
            OllamaChatResponse(
                content="Executing validated read-only SQL.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_exec",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql, "row_limit": 1000},
                    )
                ],
            ),
            OllamaChatResponse(
                content="Generating PDF report with charts and tables.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_pdf",
                        name="generate_pdf_report",
                        arguments={
                            "title": "Monthly Orders, Sales, Revenue & Transactions Report",
                            "description": "Comprehensive report with historical bar charts, distribution pie charts, matrix graphs, and data tables.",
                        },
                    )
                ],
            ),
            OllamaChatResponse(
                content="The PDF report has been generated with historical bar charts, distribution pie charts, matrix graphs, and data tables.",
                tool_calls=[],
            ),
        ]
    )

    async with MCPStdioClient(settings=settings) as mcp_client:
        orig_call_tool = mcp_client.call_tool

        async def traced_call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
            tool_invocation_order.append(name)
            return await orig_call_tool(name, arguments)

        mcp_client.call_tool = traced_call_tool  # type: ignore[method-assign]

        orchestrator = AgentOrchestrator(
            settings,
            ollama_client=mock_ollama,
            mcp_client=mcp_client,
        )
        res = await orchestrator.process_message(EXAMPLE_USER_REQUEST)

        # Verify exact tool invocation sequence (Tests 7, 8, 9, 10)
        assert tool_invocation_order == [
            "inspect_database_schema",
            "prepare_sql_query",
            "execute_readonly_sql",
            "generate_pdf_report",
        ]

        # Verify final result and PDF artifact (Test 11)
        assert res.is_success is True
        assert "CAPABILITY_LIMITATION" not in res.final_message
        assert res.executed_sql == sql
        assert len(res.generated_reports) == 1

        report_meta = res.generated_reports[0]
        assert report_meta["output_format"] == "PDF"
        assert report_meta["charts_rendered"] >= 3
        assert report_meta["tables_rendered"] >= 1
        pdf_path = Path(report_meta["output_path"])
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 10_000
        assert pdf_path.read_bytes().startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# 12. Explicit Error When MCP Discovery Fails or Returns Incomplete Tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_12_mcp_discovery_failure_surfaces_explicit_error() -> None:
    """Test 12: If MCP discovery returns 0 tools, incomplete tools, or fails, surface an explicit error."""
    settings = load_settings()

    # Case A: 0 tools returned
    mock_mcp_empty = MagicMock(spec=MCPStdioClient)
    mock_mcp_empty.is_connected = True
    mock_mcp_empty.list_tools = AsyncMock(return_value=[])

    handler_empty = ToolHandler(mock_mcp_empty)
    with pytest.raises(ToolDiscoveryError, match="returned 0 tools"):
        await handler_empty.initialize()

    # Case B: Missing reporting tools
    mock_mcp_partial = MagicMock(spec=MCPStdioClient)
    mock_mcp_partial.is_connected = True
    mock_mcp_partial.list_tools = AsyncMock(
        return_value=[
            MCPToolSpec("inspect_database_schema", "Inspect schema", {"type": "object", "properties": {}}),
        ]
    )
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.chat = AsyncMock()

    orchestrator = AgentOrchestrator(
        settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp_partial,
    )
    events: list[AgentEventType] = []
    res = await orchestrator.process_message(
        EXAMPLE_USER_REQUEST,
        progress_callback=lambda e: events.append(e.event_type),
    )

    assert res.status == "error"
    assert "MCP tool discovery failed" in (res.error or "")
    assert "generate_pdf_report" in (res.error or "")
    assert "CAPABILITY_LIMITATION" not in res.final_message
    assert AgentEventType.ERROR in events
    # LLM must never be called when MCP discovery fails
    mock_ollama.chat.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Live Local Ollama (qwen3.5:4b) Acceptance Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_13_live_ollama_qwen_reporting_workflow(tmp_path: Path) -> None:
    """Test 13: Live acceptance test with local Ollama (qwen3.5:4b) and real MCP server."""
    settings = load_settings()
    settings.reports.output_dir = str(tmp_path / "live_reports")
    settings.agent.require_sql_approval = False

    ollama_client = OllamaClient(settings.ollama)
    ok, _ = await ollama_client.check_connection()
    if not ok or not await ollama_client.check_model_availability():
        pytest.skip("Local Ollama daemon or configured model is not available for live test.")

    tool_calls_observed: list[str] = []

    async with MCPStdioClient(settings=settings) as mcp_client:
        orig_call_tool = mcp_client.call_tool

        async def trace_mcp(name: str, arguments: dict[str, Any] | None = None) -> Any:
            tool_calls_observed.append(name)
            return await orig_call_tool(name, arguments)

        mcp_client.call_tool = trace_mcp  # type: ignore[method-assign]

        orchestrator = AgentOrchestrator(
            settings,
            ollama_client=ollama_client,
            mcp_client=mcp_client,
        )
        await orchestrator.initialize()
        assert orchestrator.active_tool_mode == "native"
        assert orchestrator.tool_registry.is_complete is True

        res = await orchestrator.process_message(EXAMPLE_USER_REQUEST)

        assert res.is_success is True, f"Live run failed: {res.error} | {res.final_message}"
        assert "CAPABILITY_LIMITATION" not in res.final_message
        assert "cannot generate PDF" not in res.final_message.lower()
        assert "inspect_database_schema" in tool_calls_observed
        assert "execute_readonly_sql" in tool_calls_observed
        assert len(res.generated_reports) >= 1

        pdf_meta = res.generated_reports[-1]
        pdf_path = Path(pdf_meta["output_path"])
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 10_000
        assert pdf_path.read_bytes().startswith(b"%PDF-")
