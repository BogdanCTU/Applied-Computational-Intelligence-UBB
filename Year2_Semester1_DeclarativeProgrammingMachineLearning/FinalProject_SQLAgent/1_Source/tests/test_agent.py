"""Comprehensive automated Pytest suite for the Ollama Agent and Orchestrator.

All tests use mocks for local Ollama responses and temporary databases.
An optional live integration test executes against the running local Ollama model if available.
"""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agent import (
    ActivityCategory,
    ActivityEvent,
    AgentEventType,
    AgentOrchestrator,
    ConversationManager,
    ConversationMessage,
    OllamaChatResponse,
    OllamaClient,
    OllamaConnectionError,
    OllamaConnectionRefusedError,
    OllamaDisconnectError,
    OllamaEmptyResponseError,
    OllamaHTTPError,
    OllamaInvalidJSONError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaToolCall,
    ToolHandler,
    build_system_prompt,
    detect_requested_report_format,
    mask_sensitive_data,
)
from config.settings import AppSettings, OllamaSettings
from database import import_dataset
from mcp_layer.client import MCPStdioClient, MCPToolCallResult, MCPToolSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_test_settings(tmp_path: Path) -> AppSettings:
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()

    with (csv_dir / "customers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "first_name", "country"])
        w.writerows([[1, "Alice", "USA"], [2, "Bob", "UK"]])

    with (csv_dir / "orders.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["order_id", "customer_id", "total_amount"])
        w.writerows([[10, 1, "100.00"], [11, 2, "50.00"]])

    db_path = tmp_path / "agent_test.db"
    import_dataset(csv_dir, db_path)

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.database.max_result_rows = 50
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.max_iterations = 6
    settings.agent.require_sql_approval = True
    return settings


# ---------------------------------------------------------------------------
# 1. Ollama Client Tests
# ---------------------------------------------------------------------------


def test_ollama_client_rejects_remote_hosts() -> None:
    bad_settings = OllamaSettings(host="http://remote-server.com:11434")
    with pytest.raises(OllamaConnectionError, match="remote host"):
        OllamaClient(bad_settings)


def test_ollama_client_invalid_url() -> None:
    bad_settings = OllamaSettings(host="not_a_url")
    with pytest.raises(OllamaConnectionError, match="Invalid Ollama host"):
        OllamaClient(bad_settings)


@pytest.mark.asyncio
async def test_ollama_client_check_connection_success() -> None:
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"version": "0.40.14"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        ok, ver = await client.check_connection()
        assert ok is True
        assert ver == "0.40.14"


@pytest.mark.asyncio
async def test_ollama_client_connection_failure() -> None:
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        ok, err = await client.check_connection()
        assert ok is False
        assert "Failed to connect" in err


@pytest.mark.asyncio
async def test_ollama_client_chat_success_and_native_tool_call() -> None:
    settings = OllamaSettings(host="http://localhost:11434", model="qwen3.5:4b")
    client = OllamaClient(settings)

    mock_payload = {
        "model": "qwen3.5:4b",
        "message": {
            "role": "assistant",
            "content": "I will inspect the schema.",
            "thinking": "Need schema first",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "inspect_database_schema",
                        "arguments": {"table_name": "orders"},
                    },
                }
            ],
        },
        "done": True,
        "done_reason": "stop",
        "total_duration": 1_500_000_000,
    }

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = mock_payload

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await client.chat(
            messages=[{"role": "user", "content": "hello"}],
            tool_mode="native",
        )

        assert resp.content == "I will inspect the schema."
        assert resp.thinking == "Need schema first"
        assert resp.has_tool_calls is True
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "inspect_database_schema"
        assert resp.tool_calls[0].arguments == {"table_name": "orders"}
        assert resp.total_duration_s == 1.5


@pytest.mark.asyncio
async def test_ollama_client_chat_timeout_and_errors() -> None:
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    # 1. Timeout
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        with pytest.raises(OllamaTimeoutError):
            await client.chat(messages=[])

    # 2. 404 Model Not Found
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=404, text="Model not found")
        with pytest.raises(OllamaModelNotFoundError):
            await client.chat(messages=[])

    # 3. 500 Server Error
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=500, text="Internal Error")
        with pytest.raises(OllamaResponseError):
            await client.chat(messages=[])


@pytest.mark.asyncio
async def test_ollama_client_structured_json_fallback_parsing() -> None:
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    # JSON Tool Call response
    tool_json = '{"type": "tool_call", "tool": "get_table_sample", "arguments": {"table_name": "orders"}}'
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": tool_json}
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await client.chat(messages=[], tool_mode="json")
        assert resp.has_tool_calls is True
        assert resp.tool_calls[0].name == "get_table_sample"
        assert resp.tool_calls[0].arguments == {"table_name": "orders"}

    # JSON Final Response
    final_json = '{"type": "final_response", "message": "Here is the report."}'
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": final_json}
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await client.chat(messages=[], tool_mode="json")
        assert resp.has_tool_calls is False
        assert resp.content == "Here is the report."


# ---------------------------------------------------------------------------
# 2. Conversation Manager Tests
# ---------------------------------------------------------------------------


def test_conversation_manager_limits_and_tool_pairing() -> None:
    mgr = ConversationManager(max_history_messages=4)

    mgr.add_user_message("msg 1")
    mgr.add_assistant_message("msg 2")
    mgr.add_user_message("msg 3")
    mgr.add_assistant_message("msg 4", tool_calls=[{"id": "c1"}])
    mgr.add_tool_message("tool_1", {"ok": True}, tool_call_id="c1")

    # Length before: 5 -> after limit: stays bound without breaking tool pair
    assert len(mgr.messages) <= 4
    roles = [m.role for m in mgr.messages]
    # The assistant tool_calls message and its tool message must remain intact together
    assert "tool" in roles
    tool_idx = roles.index("tool")
    assert roles[tool_idx - 1] == "assistant"

    mgr.clear()
    assert len(mgr.messages) == 0


def test_detect_requested_report_format() -> None:
    assert detect_requested_report_format("Please give me the report in CSV format") == "CSV"
    assert detect_requested_report_format("Export as .csv") == "CSV"
    assert detect_requested_report_format("Show me total revenue per month") == "PDF"
    assert detect_requested_report_format("Create a PDF report") == "PDF"


# ---------------------------------------------------------------------------
# 3. Tool Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_handler_unknown_tool_and_invalid_args() -> None:
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    handler = ToolHandler(mock_mcp)

    # 1. Unknown tool rejected
    res = await handler.execute_tool("arbitrary_command", {})
    assert res.is_error is True
    assert res.data["error_code"] in {"INVALID_TOOL_ARGUMENTS", "UNKNOWN_TOOL"}

    # 2. Prohibited argument keys rejected
    res2 = await handler.execute_tool(
        "inspect_database_schema", {"__proto__": "attack"}
    )
    assert res2.is_error is True

    # 3. Missing required argument rejected
    res3 = await handler.execute_tool("get_table_sample", {})
    assert res3.is_error is True
    assert "table_name is required" in res3.data["error"]


@pytest.mark.asyncio
async def test_tool_handler_timeout() -> None:
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    async def slow_call(*args: Any, **kwargs: Any) -> Any:
        await asyncio.sleep(0.5)

    mock_mcp.call_tool = slow_call
    handler = ToolHandler(mock_mcp, default_tool_timeout_s=0.05)

    res = await handler.execute_tool(
        "get_table_sample", {"table_name": "orders"}, timeout_s=0.05
    )
    assert res.is_error is True
    assert res.data["error_code"] == "TOOL_TIMEOUT"


# ---------------------------------------------------------------------------
# 4. Orchestrator Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_simple_conversation_without_tools(
    agent_test_settings: AppSettings,
) -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Hello! I am your SQL reporting assistant.",
            tool_calls=[],
        )
    )

    orchestrator = AgentOrchestrator(
        agent_test_settings,
        ollama_client=mock_ollama,
    )
    orchestrator._initialized = True  # skip MCP launch for pure conversational test

    events: list[AgentEventType] = []
    res = await orchestrator.process_message(
        "Hello",
        progress_callback=lambda e: events.append(e.event_type),
    )

    assert res.is_success is True
    assert res.final_message == "Hello! I am your SQL reporting assistant."
    assert res.iterations == 1
    assert AgentEventType.FINAL_ANSWER in events


@pytest.mark.asyncio
async def test_orchestrator_sql_approval_denied_stops_execution(
    agent_test_settings: AppSettings,
) -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    # LLM requests execute_readonly_sql
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="I want to run this query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="execute_readonly_sql",
                        arguments={"sql_query": "SELECT * FROM orders"},
                    )
                ],
            ),
            OllamaChatResponse(
                content="Understood. The query was not executed.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(
        agent_test_settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp,
    )
    orchestrator._initialized = True

    # User approval callback returns False (denied)
    denied_callback = MagicMock(return_value=False)
    events: list[AgentEventType] = []

    res = await orchestrator.process_message(
        "Run orders report",
        approval_callback=denied_callback,
        progress_callback=lambda e: events.append(e.event_type),
    )

    assert AgentEventType.SQL_APPROVAL_REQUESTED in events
    assert AgentEventType.SQL_DENIED in events
    assert res.executed_sql is None
    # MCP client must NOT have been called with execute_readonly_sql
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_missing_approval_callback_denies_execution(
    agent_test_settings: AppSettings,
) -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Run query directly",
            tool_calls=[
                OllamaToolCall(
                    id="c1",
                    name="execute_readonly_sql",
                    arguments={"sql_query": "SELECT * FROM orders"},
                )
            ],
        )
    )

    orchestrator = AgentOrchestrator(
        agent_test_settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp,
    )
    orchestrator._initialized = True

    # No approval callback provided
    res = await orchestrator.process_message("Get data")
    assert res.status == "approval_denied"
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_complete_pdf_workflow_with_mcp(
    agent_test_settings: AppSettings,
) -> None:
    """Test full cycle: schema inspection -> SQL prepare -> approved execute -> PDF report."""
    sql = "SELECT c.country, SUM(o.total_amount) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.country"

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    # Simulate realistic multi-turn model thinking and tool calls
    mock_ollama.chat = AsyncMock(
        side_effect=[
            # Iteration 1: Discover schema
            OllamaChatResponse(
                content="Let me inspect the schema first.",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="inspect_database_schema",
                        arguments={},
                    )
                ],
            ),
            # Iteration 2: Prepare SQL
            OllamaChatResponse(
                content="Now I will prepare the revenue query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c2",
                        name="prepare_sql_query",
                        arguments={"sql_query": sql},
                    )
                ],
            ),
            # Iteration 3: Request SQL execution
            OllamaChatResponse(
                content="SQL is valid. Requesting execution.",
                tool_calls=[
                    OllamaToolCall(
                        id="c3",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql},
                    )
                ],
            ),
            # Iteration 4: Generate PDF report
            OllamaChatResponse(
                content="Generating PDF report.",
                tool_calls=[
                    OllamaToolCall(
                        id="c4",
                        name="generate_pdf_report",
                        arguments={
                            "title": "Country Revenue Report",
                            "description": "Total revenue grouped by country",
                            "sql_query": sql,
                            "columns": ["country", "revenue"],
                            "rows": [["USA", 100.0], ["UK", 50.0]],
                        },
                    )
                ],
            ),
            # Iteration 5: Final concluding answer
            OllamaChatResponse(
                content="The report has been generated successfully.",
                tool_calls=[],
            ),
        ]
    )

    async with MCPStdioClient(settings=agent_test_settings) as real_mcp:
        orchestrator = AgentOrchestrator(
            agent_test_settings,
            ollama_client=mock_ollama,
            mcp_client=real_mcp,
        )
        await orchestrator.initialize()

        # Deterministic mock approval granting permission
        approved_cb = MagicMock(return_value=True)
        events: list[AgentEventType] = []

        res = await orchestrator.process_message(
            "Generate revenue report by country",
            approval_callback=approved_cb,
            progress_callback=lambda e: events.append(e.event_type),
        )

        assert res.is_success is True
        assert res.executed_sql == sql
        assert len(res.generated_reports) == 1
        assert res.generated_reports[0]["output_format"] == "PDF"
        pdf_path = Path(res.generated_reports[0]["output_path"])
        assert pdf_path.is_file()
        assert pdf_path.read_bytes().startswith(b"%PDF-")

        assert AgentEventType.SQL_PROPOSED in events
        assert AgentEventType.SQL_APPROVED in events
        assert AgentEventType.REPORT_GENERATED in events


@pytest.mark.asyncio
async def test_orchestrator_explicit_csv_workflow(
    agent_test_settings: AppSettings,
) -> None:
    """Test explicit CSV request steers format to CSV."""
    sql = "SELECT first_name, country FROM customers"

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Preparing query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="prepare_sql_query",
                        arguments={"sql_query": sql},
                    )
                ],
            ),
            OllamaChatResponse(
                content="Executing query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c2",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql},
                    )
                ],
            ),
            OllamaChatResponse(
                content="Generating CSV.",
                tool_calls=[
                    OllamaToolCall(
                        id="c3",
                        name="generate_csv_report",
                        arguments={
                            "title": "Customers Export",
                            "columns": ["first_name", "country"],
                            "rows": [["Alice", "USA"], ["Bob", "UK"]],
                        },
                    )
                ],
            ),
            OllamaChatResponse(
                content="CSV export complete.",
                tool_calls=[],
            ),
        ]
    )

    async with MCPStdioClient(settings=agent_test_settings) as real_mcp:
        orchestrator = AgentOrchestrator(
            agent_test_settings,
            ollama_client=mock_ollama,
            mcp_client=real_mcp,
        )
        await orchestrator.initialize()

        res = await orchestrator.process_message(
            "Export all customers to CSV",
            approval_callback=lambda q, exp: True,
        )

        assert res.is_success is True
        assert len(res.generated_reports) == 1
        assert res.generated_reports[0]["output_format"] == "CSV"
        csv_file = Path(res.generated_reports[0]["output_path"])
        assert csv_file.is_file()


@pytest.mark.asyncio
async def test_orchestrator_max_iteration_limit(
    agent_test_settings: AppSettings,
) -> None:
    agent_test_settings.agent.max_iterations = 2
    mock_ollama = MagicMock(spec=OllamaClient)
    # Loop continuously proposing schema inspection
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Inspecting...",
            tool_calls=[
                OllamaToolCall(
                    id="loop",
                    name="inspect_database_schema",
                    arguments={},
                )
            ],
        )
    )

    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    mock_mcp.call_tool = AsyncMock(
        return_value=MCPToolCallResult(
            tool_name="inspect_database_schema",
            is_error=False,
            data={"status": "ok", "tables": []},
            raw_text="ok",
        )
    )

    orchestrator = AgentOrchestrator(
        agent_test_settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp,
    )
    orchestrator._initialized = True

    res = await orchestrator.process_message("Check schema")
    assert res.status == "error"
    assert "maximum tool iterations" in res.error.lower()
    assert res.iterations == 2


@pytest.mark.asyncio
async def test_orchestrator_cancellation(
    agent_test_settings: AppSettings,
) -> None:
    cancel_evt = asyncio.Event()
    cancel_evt.set()  # Pre-cancelled

    orchestrator = AgentOrchestrator(agent_test_settings)
    orchestrator._initialized = True

    res = await orchestrator.process_message(
        "Do something", cancel_event=cancel_evt
    )
    assert res.status == "cancelled"
    assert "cancelled" in res.final_message.lower()


# ---------------------------------------------------------------------------
# 5. Live Local Ollama Integration Test (skipped if Ollama is offline)
# ---------------------------------------------------------------------------


def _is_local_ollama_available() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:11434/api/version", timeout=1.0) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.mark.skipif(
    not _is_local_ollama_available(),
    reason="Local Ollama daemon is not running on http://localhost:11434",
)
@pytest.mark.asyncio
async def test_live_local_ollama_integration_end_to_end(
    agent_test_settings: AppSettings,
) -> None:
    """Verifies live qwen3.5:4b interaction with genuine MCP tools."""
    orchestrator = AgentOrchestrator(agent_test_settings)
    async with orchestrator:
        # Check model presence first
        has_model = await orchestrator.ollama_client.check_model_availability("qwen3.5:4b")
        if not has_model:
            pytest.skip("qwen3.5:4b model not pulled in local Ollama")

        # Deterministic test approval callback
        approved = False

        def mock_approval(query: str, exp: str) -> bool:
            nonlocal approved
            approved = True
            return True

        res = await orchestrator.process_message(
            "Please check the database schema and tell me what tables exist.",
            approval_callback=mock_approval,
        )

        assert res.status in {"success", "approval_denied"}
        assert len(res.final_message) > 0
        # Verify conversation context was maintained
        assert len(orchestrator.conversation.messages) >= 2


# ---------------------------------------------------------------------------
# 6. Milestone 7 Tool Calling & Timeout Regression Tests
# ---------------------------------------------------------------------------


def test_tool_calling_successful_parsing() -> None:
    """Milestone 7: Test successful parsing of tool calls across format variations."""
    # Standard format
    raw1 = '{"type": "tool_call", "tool": "inspect_database_schema", "arguments": {"table_name": "orders"}}'
    tc1 = OllamaClient._extract_json_tool_call(raw1)
    assert tc1 is not None
    assert tc1.name == "inspect_database_schema"
    assert tc1.arguments == {"table_name": "orders"}

    # OpenAI-style function format with markdown block
    raw2 = "```json\n" '{"function": {"name": "prepare_sql_query", "arguments": {"sql_query": "SELECT 1;"}}}\n' "```"
    tc2 = OllamaClient._extract_json_tool_call(raw2)
    assert tc2 is not None
    assert tc2.name == "prepare_sql_query"
    assert tc2.arguments == {"sql_query": "SELECT 1;"}

    # Action / parameters format with stringified arguments
    raw3 = '{"action": "get_table_sample", "parameters": "{\\"table_name\\": \\"customers\\", \\"num_records\\": 5}"}'
    tc3 = OllamaClient._extract_json_tool_call(raw3)
    assert tc3 is not None
    assert tc3.name == "get_table_sample"
    assert tc3.arguments == {"table_name": "customers", "num_records": 5}


@pytest.mark.asyncio
async def test_tool_calling_xml_error_fallback_to_json() -> None:
    """Milestone 7: Verify HTTP 500 XML syntax error automatically triggers structured JSON fallback."""
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    # First call (native with tools) returns HTTP 500 XML syntax error
    mock_500 = MagicMock(status_code=500)
    mock_500.text = '{"error":"XML syntax error on line 3: element <function> closed by </parameter>"}'

    # Second call (json fallback) returns HTTP 200 with JSON tool call
    mock_200 = MagicMock(status_code=200)
    mock_200.json.return_value = {
        "message": {
            "role": "assistant",
            "content": '{"type": "tool_call", "tool": "inspect_database_schema", "arguments": {}}',
        },
        "done_reason": "stop",
    }

    messages = [
        {"role": "system", "content": "You are a reporting agent."},
        {"role": "user", "content": "Generate a PDF report."},
    ]
    tools = [{"type": "function", "function": {"name": "inspect_database_schema", "parameters": {}}}]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [mock_500, mock_200]
        resp = await client.chat(messages, tools=tools, tool_mode="native")

        assert resp.used_fallback is True
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "inspect_database_schema"
        assert mock_post.call_count == 2
        # Verify the fallback call used format="json" and omitted tools
        fallback_call_kwargs = mock_post.call_args_list[1][1]
        assert fallback_call_kwargs["json"]["format"] == "json"
        assert "tools" not in fallback_call_kwargs["json"]


def test_tool_calling_embedded_json_in_content() -> None:
    """Milestone 7: Verify tool calls embedded in surrounding reasoning/markdown text are parsed."""
    mixed_content = (
        "I need to inspect the orders table first to see available columns.\n\n"
        "```json\n"
        "{\n"
        '  "tool": "get_table_sample",\n'
        '  "arguments": {\n'
        '    "table_name": "orders",\n'
        '    "num_records": 10\n'
        "  }\n"
        "}\n"
        "```\n"
        "Please provide the table sample."
    )
    tc = OllamaClient._extract_json_tool_call(mixed_content)
    assert tc is not None
    assert tc.name == "get_table_sample"
    assert tc.arguments == {"table_name": "orders", "num_records": 10}


def test_tool_calling_invalid_arguments_feedback() -> None:
    """Milestone 7: Verify invalid tool arguments are rejected with descriptive error."""
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    handler = ToolHandler(mock_mcp)

    # get_table_sample with non-integer num_records
    is_valid, err_msg, _ = handler.validate_tool_request(
        "get_table_sample", {"table_name": "orders", "num_records": "invalid"}
    )
    assert is_valid is False
    assert "integer" in err_msg.lower()

    # prepare_sql_query with empty query
    is_valid2, err_msg2, _ = handler.validate_tool_request(
        "prepare_sql_query", {"sql_query": "   "}
    )
    assert is_valid2 is False
    assert "required" in err_msg2.lower()


def test_tool_calling_unknown_tool_rejected() -> None:
    """Milestone 7: Verify unapproved/unknown tools are rejected with permitted tools list."""
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    handler = ToolHandler(mock_mcp)

    is_valid, err_msg, _ = handler.validate_tool_request(
        "unapproved_bash_tool", {"command": "ls"}
    )
    assert is_valid is False
    assert "not recognized" in err_msg
    assert "prepare_sql_query" in err_msg
    assert "execute_readonly_sql" in err_msg


def test_tool_calling_missing_required_arguments() -> None:
    """Milestone 7: Verify missing required arguments are caught before execution."""
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    handler = ToolHandler(mock_mcp)

    # generate_pdf_report missing required fields
    is_valid, err_msg, _ = handler.validate_tool_request(
        "generate_pdf_report", {"title": "Monthly Report"}
    )
    assert is_valid is False
    assert "missing required argument" in err_msg.lower()


@pytest.mark.asyncio
async def test_tool_calling_sql_approval_enforced_in_fallback(
    agent_test_settings: AppSettings,
) -> None:
    """Milestone 7: Ensure SQL approval is strictly enforced even when in JSON fallback mode."""
    orchestrator = AgentOrchestrator(agent_test_settings)
    orchestrator.active_tool_mode = "json"
    orchestrator.initialize = AsyncMock()
    orchestrator.tool_handler.initialize = AsyncMock()

    # Mock LLM proposing execute_readonly_sql via JSON fallback
    call_resp = OllamaChatResponse(
        content='{"type": "tool_call", "tool": "execute_readonly_sql", "arguments": {"sql_query": "SELECT * FROM orders;"}}',
        tool_calls=[
            OllamaToolCall(
                id="call_json_1",
                name="execute_readonly_sql",
                arguments={"sql_query": "SELECT * FROM orders;"},
            )
        ],
    )
    orchestrator.ollama_client.chat = AsyncMock(return_value=call_resp)

    # Case 1: User denies approval
    def deny_approval(query: str, exp: str) -> bool:
        return False

    res = await orchestrator.process_message(
        "Run this query for me",
        approval_callback=deny_approval,
    )
    assert res.status == "approval_denied"
    assert "denied by user" in res.final_message


def test_user_facing_error_messages(agent_test_settings: AppSettings) -> None:
    """Milestone 7: Verify user-friendly error formatting without raw stack traces."""
    orchestrator = AgentOrchestrator(agent_test_settings)

    # 1. Connection error / refused
    conn_err = OllamaConnectionError("ConnectError: connection refused")
    msg1 = orchestrator._format_friendly_error(conn_err)
    assert "Cannot connect to Ollama" in msg1
    assert "ollama serve" in msg1

    refused_err = OllamaConnectionRefusedError("Connection refused")
    msg1b = orchestrator._format_friendly_error(refused_err)
    assert "Cannot connect to Ollama" in msg1b
    assert "ollama serve" in msg1b

    # 2. Ollama timeout
    timeout_err = OllamaTimeoutError("Timed out after 600s")
    msg2 = orchestrator._format_friendly_error(timeout_err)
    assert "timed out after 600 seconds" in msg2

    # 3. Model not found
    model_err = OllamaModelNotFoundError("Model not found")
    msg3 = orchestrator._format_friendly_error(model_err)
    assert "ollama pull qwen3.5:4b" in msg3

    # 4. Disconnect / runner crash
    disc_err = OllamaDisconnectError("Server disconnected without sending a response.")
    msg4 = orchestrator._format_friendly_error(disc_err)
    assert "disconnected abruptly" in msg4
    assert "runner may have crashed" in msg4

    # 5. Empty assistant response
    empty_err = OllamaEmptyResponseError("Empty response")
    msg5 = orchestrator._format_friendly_error(empty_err)
    assert "empty response" in msg5

    # 6. Invalid JSON response
    json_err = OllamaInvalidJSONError("Invalid JSON")
    msg6 = orchestrator._format_friendly_error(json_err)
    assert "invalid or unparseable JSON" in msg6

    # 7. HTTP Error response
    http_err = OllamaHTTPError(status_code=500, message="Internal Server Error")
    msg7 = orchestrator._format_friendly_error(http_err)
    assert "HTTP 500" in msg7
    assert "Internal Server Error" in msg7

    # 8. Query execution timeout
    query_timeout_err = RuntimeError("QUERY_TIMEOUT: query exceeded timeout")
    msg8 = orchestrator._format_friendly_error(query_timeout_err)
    assert "120 seconds" in msg8
    assert "simplifying your query" in msg8


@pytest.mark.asyncio
async def test_ollama_client_remote_protocol_disconnect_with_retry() -> None:
    """Verify httpx.RemoteProtocolError triggers bounded retry and then raises OllamaDisconnectError."""
    import json
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    # Case A: Fails on attempt 0, succeeds on attempt 1 (retry succeeds)
    success_resp = MagicMock(status_code=200)
    success_resp.json.return_value = {
        "message": {"role": "assistant", "content": "Hello!"},
        "done": True,
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [
            httpx.RemoteProtocolError("Server disconnected without sending a response."),
            success_resp,
        ]
        res = await client.chat(messages=[{"role": "user", "content": "hi"}])
        assert res.content == "Hello!"
        assert mock_post.call_count == 2

    # Case B: Fails on all attempts -> raises OllamaDisconnectError
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RemoteProtocolError("Server disconnected without sending a response.")
        with pytest.raises(OllamaDisconnectError) as exc_info:
            await client.chat(messages=[{"role": "user", "content": "hi"}])
        assert "disconnected without sending a response" in str(exc_info.value)
        assert mock_post.call_count == 3  # exactly 3 attempts (1 initial + 2 retries), bounded retry


@pytest.mark.asyncio
async def test_ollama_client_connection_refused_error() -> None:
    """Verify connection refused raises OllamaConnectionRefusedError."""
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("[WinError 10061] No connection could be made because the target machine actively refused it")
        with pytest.raises(OllamaConnectionRefusedError) as exc_info:
            await client.chat(messages=[{"role": "user", "content": "hi"}])
        assert "connection refused" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_ollama_client_invalid_json_error() -> None:
    """Verify invalid JSON payload raises OllamaInvalidJSONError."""
    import json
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    bad_resp = MagicMock(status_code=200, text="not-valid-json")
    bad_resp.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = bad_resp
        with pytest.raises(OllamaInvalidJSONError) as exc_info:
            await client.chat(messages=[{"role": "user", "content": "hi"}])
        assert "invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_client_empty_response_error() -> None:
    """Verify empty assistant response (no text, no tool calls) raises OllamaEmptyResponseError."""
    settings = OllamaSettings(host="http://localhost:11434")
    client = OllamaClient(settings)

    empty_resp = MagicMock(status_code=200)
    empty_resp.json.return_value = {
        "message": {"role": "assistant", "content": ""},
        "done": True,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = empty_resp
        with pytest.raises(OllamaEmptyResponseError) as exc_info:
            await client.chat(messages=[{"role": "user", "content": "hi"}])
        assert "empty response" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_orchestrator_native_mode_disconnect_recovers_via_json_fallback(
    agent_test_settings: AppSettings,
) -> None:
    """Verify that if Ollama disconnects during native tool calling, orchestrator falls back to JSON mode and recovers."""
    mock_ollama = MagicMock(spec=OllamaClient)
    # First call in native mode disconnects
    # Second call in json fallback mode succeeds
    json_call = '{"type": "tool_call", "tool": "inspect_database_schema", "arguments": {}}'
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaDisconnectError("Server disconnected without sending a response."),
            OllamaChatResponse(
                content=json_call,
                tool_calls=[
                    OllamaToolCall(id="c1", name="inspect_database_schema", arguments={})
                ],
            ),
            OllamaChatResponse(
                content="Found tables: customers, orders.",
                tool_calls=[],
            ),
        ]
    )

    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    mock_mcp.call_tool = AsyncMock(
        return_value=MCPToolCallResult(
            tool_name="inspect_database_schema",
            is_error=False,
            data={"status": "ok", "tables": ["customers", "orders"]},
            raw_text="customers, orders",
        )
    )

    orchestrator = AgentOrchestrator(
        agent_test_settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp,
    )
    orchestrator._initialized = True
    orchestrator.active_tool_mode = "native"

    res = await orchestrator.process_message("Show tables")
    assert res.is_success is True
    assert "Found tables" in res.final_message
    assert orchestrator.active_tool_mode == "json"


def test_timeout_configuration_defaults() -> None:
    """Milestone 7: Verify 600s Ollama timeout and 120s SQL execution timeout defaults."""
    settings = AppSettings()
    assert settings.ollama.request_timeout_s == 600.0
    assert settings.database.query_timeout_s == 120.0
    assert settings.validate() == []


# ===========================================================================
# Milestone 8: SQL Approval Workflow & Transparency Regression Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_m8_valid_sql_reaches_approval_dialog(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Valid SQL reaches the approval callback with exact query and explanation."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    mock_mcp.call_tool = AsyncMock(return_value={"columns": ["id"], "rows": [[1]], "record_count": 1})

    query = "SELECT order_id, total_amount FROM orders LIMIT 5"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Executing orders query.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": query})
                ],
            ),
            OllamaChatResponse(content="Here is your result.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    approval_queries_received: list[str] = []

    def mock_approval(sql_text: str, explanation: str) -> bool:
        approval_queries_received.append(sql_text)
        return True

    res = await orchestrator.process_message("Show orders", approval_callback=mock_approval)
    assert res.is_success is True
    assert len(approval_queries_received) == 1
    assert "SELECT order_id, total_amount FROM orders" in approval_queries_received[0]


@pytest.mark.asyncio
async def test_m8_sql_displayed_matches_sql_executed(agent_test_settings: AppSettings) -> None:
    """Milestone 8: The SQL query shown in the dialog is identically equal to the SQL executed."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    executed_queries: list[str] = []

    async def mock_call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "execute_readonly_sql":
            executed_queries.append(args["sql_query"])
        return {"columns": ["cnt"], "rows": [[42]], "record_count": 1}

    mock_mcp.call_tool = AsyncMock(side_effect=mock_call_tool)

    query = "SELECT count(*) AS total_orders FROM orders"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Counting orders.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": query})
                ],
            ),
            OllamaChatResponse(content="Done.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    dialog_queries: list[str] = []

    def capture_approval(sql_text: str, exp: str) -> bool:
        dialog_queries.append(sql_text)
        return True

    await orchestrator.process_message("Count orders", approval_callback=capture_approval)
    assert len(dialog_queries) == 1
    assert len(executed_queries) == 1
    # INVARIANT: SQL shown in dialog MUST identically equal SQL executed
    assert dialog_queries[0] == executed_queries[0]


@pytest.mark.asyncio
async def test_m8_empty_sql_rejected_without_dialog(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Empty SQL query is rejected BEFORE approval dialog is shown."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Running empty query.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": "   "})
                ],
            ),
            OllamaChatResponse(content="Correcting my query.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    dialog_shown = False

    def check_dialog(sql_text: str, exp: str) -> bool:
        nonlocal dialog_shown
        dialog_shown = True
        return True

    await orchestrator.process_message("Get data", approval_callback=check_dialog)
    # Safety Invariant: Dialog MUST NOT have been displayed!
    assert dialog_shown is False
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_m8_missing_sql_argument_rejected_without_dialog(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Missing sql_query argument is rejected without showing approval dialog."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Calling tool with no arguments.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={})
                ],
            ),
            OllamaChatResponse(content="Understood.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    dialog_shown = False

    def check_dialog(sql_text: str, exp: str) -> bool:
        nonlocal dialog_shown
        dialog_shown = True
        return True

    await orchestrator.process_message("Get data", approval_callback=check_dialog)
    assert dialog_shown is False
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_m8_invalid_sql_syntax_rejected_without_dialog(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Malformed SQL syntax is rejected BEFORE approval dialog is shown."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    bad_sql = "SELECT FROM WHERE GROUP BY ORDER"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Trying invalid syntax.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": bad_sql})
                ],
            ),
            OllamaChatResponse(content="Recovered.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    dialog_shown = False

    def check_dialog(sql_text: str, exp: str) -> bool:
        nonlocal dialog_shown
        dialog_shown = True
        return True

    await orchestrator.process_message("Execute invalid", approval_callback=check_dialog)
    assert dialog_shown is False
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_m8_destructive_statement_rejected_without_dialog(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Destructive statements (DROP TABLE) are rejected BEFORE approval dialog."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True

    forbidden_sql = "DROP TABLE orders;"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Attempting drop.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": forbidden_sql})
                ],
            ),
            OllamaChatResponse(content="Forbidden.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    dialog_shown = False

    def check_dialog(sql_text: str, exp: str) -> bool:
        nonlocal dialog_shown
        dialog_shown = True
        return True

    await orchestrator.process_message("Drop orders", approval_callback=check_dialog)
    assert dialog_shown is False
    mock_mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_m8_argument_normalization_preserves_sql_aliases(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Argument normalization handles 'query' and 'sql' aliases without losing the query."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    mock_mcp.call_tool = AsyncMock(return_value={"columns": ["c"], "rows": [[1]], "record_count": 1})

    query = "SELECT order_id FROM orders LIMIT 1"
    # LLM uses "query" instead of "sql_query"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Running query with alias.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"query": query})
                ],
            ),
            OllamaChatResponse(content="Done.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    approved_sql: list[str] = []

    def capture_approval(sql_text: str, exp: str) -> bool:
        approved_sql.append(sql_text)
        return True

    res = await orchestrator.process_message("Run aliased query", approval_callback=capture_approval)
    assert res.is_success is True
    assert len(approved_sql) == 1
    assert "SELECT order_id FROM orders" in approved_sql[0]


@pytest.mark.asyncio
async def test_m8_activity_events_chronological_emission(agent_test_settings: AppSettings) -> None:
    """Milestone 8: Activity events are emitted in proper chronological order with categories."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = True
    mock_mcp.call_tool = AsyncMock(return_value={"columns": ["c"], "rows": [[1]], "record_count": 1})

    query = "SELECT order_id FROM orders LIMIT 1"
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Thinking about orders.",
                thinking="I should select from orders table.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="execute_readonly_sql", arguments={"sql_query": query})
                ],
            ),
            OllamaChatResponse(content="Orders retrieved.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama, mcp_client=mock_mcp)
    orchestrator._initialized = True

    activity_categories: list[str] = []

    def on_progress(event: AgentEvent) -> None:
        act = event.activity_event
        if act:
            activity_categories.append(act.category)

    res = await orchestrator.process_message(
        "Show orders",
        approval_callback=lambda q, e: True,
        progress_callback=on_progress,
    )
    assert res.is_success is True
    # Verify core categories appeared in order
    assert ActivityCategory.USER_REQUEST.value in activity_categories
    assert ActivityCategory.AGENT_STATUS.value in activity_categories
    assert ActivityCategory.REASONING_SUMMARY.value in activity_categories
    assert ActivityCategory.PLANNING.value in activity_categories
    assert ActivityCategory.SQL_VALIDATION.value in activity_categories
    assert ActivityCategory.APPROVAL_REQUIRED.value in activity_categories
    assert ActivityCategory.APPROVAL_RESULT.value in activity_categories
    assert ActivityCategory.SQL_EXECUTION.value in activity_categories
    assert ActivityCategory.SQL_RESULT.value in activity_categories
    assert ActivityCategory.COMPLETION.value in activity_categories


def test_m8_mask_sensitive_data() -> None:
    """Milestone 8: Sensitive credentials, tokens, and keys are masked."""
    raw_payload = {
        "api_key": "sk-proj-1234567890abcdef",
        "password": "supersecretpassword",
        "auth_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "safe_query": "SELECT * FROM orders",
        "nested": {
            "secret_key": "mysecret",
            "db_user": "postgres",
        },
    }
    masked = mask_sensitive_data(raw_payload)
    assert masked["api_key"] == "[REDACTED_CREDENTIAL]"
    assert masked["password"] == "[REDACTED_CREDENTIAL]"
    assert masked["auth_token"] == "[REDACTED_CREDENTIAL]"
    assert masked["safe_query"] == "SELECT * FROM orders"
    assert masked["nested"]["secret_key"] == "[REDACTED_CREDENTIAL]"
    assert masked["nested"]["db_user"] == "postgres"


# ---------------------------------------------------------------------------
# 7. Milestone 12 Orchestration Robustness & Empty Response Regression Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_scenario_1_normal_assistant_text(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 1: Normal assistant text response without tool calls."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Hello! I am ready to analyze your e-commerce data.",
            tool_calls=[],
        )
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    orchestrator._initialized = True

    res = await orchestrator.process_message("Hello assistant")
    assert res.status == "success"
    assert res.final_message == "Hello! I am ready to analyze your e-commerce data."
    assert res.iterations == 1
    assert res.executed_sql is None
    assert bool(res.final_message.strip())


@pytest.mark.asyncio
async def test_regression_scenario_2_one_tool_call_followed_by_final_text(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 2: One MCP tool call followed by final assistant text."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Inspecting database schema...",
                tool_calls=[
                    OllamaToolCall(id="c1", name="inspect_database_schema", arguments={})
                ],
            ),
            OllamaChatResponse(
                content="The database schema has 5 verified tables: customers, orders, order_items, payments, and products.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("What tables exist in the database?")

    assert res.status == "success"
    assert res.iterations == 2
    assert "5 verified tables" in res.final_message
    assert res.component_status["database_discovery"] == "success"
    assert bool(res.final_message.strip())


@pytest.mark.asyncio
async def test_regression_scenario_3_multiple_consecutive_tool_calling_rounds(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 3: Multiple consecutive MCP tool-calling rounds across iterations."""
    sql = "SELECT country, COUNT(*) AS cnt FROM customers GROUP BY country LIMIT 5"
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            # Round 1
            OllamaChatResponse(
                content="Step 1: Check schema",
                tool_calls=[
                    OllamaToolCall(id="c1", name="inspect_database_schema", arguments={})
                ],
            ),
            # Round 2
            OllamaChatResponse(
                content="Step 2: Prepare SQL",
                tool_calls=[
                    OllamaToolCall(id="c2", name="prepare_sql_query", arguments={"sql_query": sql})
                ],
            ),
            # Round 3: Final text
            OllamaChatResponse(
                content="Query was formulated and verified against the customers table.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Show customer countries")

    assert res.status == "success"
    assert res.iterations == 3
    assert res.proposed_sql == sql
    assert res.component_status["database_discovery"] == "success"
    assert res.component_status["sql_preparation"] == "success"
    assert bool(res.final_message.strip())


@pytest.mark.asyncio
async def test_regression_scenario_4_multiple_tool_calls_in_one_response(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 4: Multiple tool calls returned in a single assistant response."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Inspecting schema and fetching sample simultaneously.",
                tool_calls=[
                    OllamaToolCall(id="c1", name="inspect_database_schema", arguments={}),
                    OllamaToolCall(id="c2", name="get_table_sample", arguments={"table_name": "customers", "num_records": 2}),
                ],
            ),
            OllamaChatResponse(
                content="Completed both schema inspection and sample retrieval.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Inspect schema and sample customers")

    assert res.status == "success"
    assert res.iterations == 2
    assert res.final_message == "Completed both schema inspection and sample retrieval."

    # Verify both tool results exist in conversation history with matching tool_call_ids
    tool_msgs = [m for m in orchestrator.conversation.messages if m.role == "tool"]
    assert len(tool_msgs) == 2
    assert tool_msgs[0].tool_call_id == "c1"
    assert tool_msgs[1].tool_call_id == "c2"


@pytest.mark.asyncio
async def test_regression_scenario_5_empty_assistant_response_after_successful_mcp(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 5: Empty assistant response after MCP execution triggers deterministic synthesis."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    # Simulate Windows Ollama behavior: Turn 2 returns empty content with thinking
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(id="c1", name="inspect_database_schema", arguments={})
                ],
            ),
            OllamaChatResponse(
                content="",  # EMPTY content!
                thinking="The database schema has tables: customers, orders, order_items, payments, products.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Please check the database schema and tell me what tables exist.")

    assert res.status == "success"
    assert res.iterations == 2
    assert len(res.final_message) > 0
    assert bool(res.final_message.strip())
    # Verify deterministic synthesis from actual verified MCP schema
    assert "customers" in res.final_message
    assert "orders" in res.final_message
    assert "records" in res.final_message
    assert res.component_status["database_discovery"] == "success"


@pytest.mark.asyncio
async def test_regression_scenario_6_empty_assistant_response_without_tool_calls(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 6: Empty assistant response without tool calls does NOT report success."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    # Both initial and recovery prompt return empty content
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(content="", thinking="", tool_calls=[]),
            OllamaChatResponse(content="", thinking="", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    orchestrator._initialized = True

    res = await orchestrator.process_message("Hello")

    assert res.status == "error"
    assert res.error is not None
    assert len(res.final_message) > 0
    assert bool(res.final_message.strip())


@pytest.mark.asyncio
async def test_regression_scenario_7_malformed_assistant_response(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 7: Malformed assistant response raises OllamaInvalidJSONError and fails gracefully."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=OllamaInvalidJSONError("Ollama returned invalid JSON response: Unterminated string at line 1")
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    orchestrator._initialized = True

    res = await orchestrator.process_message("Generate report")

    assert res.status == "error"
    assert res.error is not None
    assert "invalid or unparseable JSON" in res.final_message or "invalid" in res.final_message.lower()


@pytest.mark.asyncio
async def test_regression_scenario_8_tool_call_parsing_and_validation_failure(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 8: Unauthorized tool call is rejected by security policy and fed back to conversation."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Attempting unauthorized action",
                tool_calls=[
                    OllamaToolCall(id="c_bad", name="drop_table_customers", arguments={})
                ],
            ),
            OllamaChatResponse(
                content="Understood. That tool is not permitted by policy.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Drop customers")

    assert res.status == "success"
    assert res.iterations == 2
    assert "not permitted" in res.final_message

    # Verify tool error was appended to conversation
    tool_msgs = [m for m in orchestrator.conversation.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "not permitted" in str(tool_msgs[0].content)


@pytest.mark.asyncio
async def test_regression_scenario_9_mcp_execution_failure(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 9: MCP tool execution failure returns structured error and updates component status."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Sampling non-existent table",
                tool_calls=[
                    OllamaToolCall(id="c_missing", name="get_table_sample", arguments={"table_name": "non_existent_xyz"})
                ],
            ),
            OllamaChatResponse(
                content="Table non_existent_xyz was not found in the database.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Sample non_existent_xyz")

    assert res.status == "success"
    assert res.iterations == 2
    assert res.component_status["database_discovery"] == "failed"
    assert "not found" in res.final_message.lower()


@pytest.mark.asyncio
async def test_regression_scenario_10_maximum_iteration_limit(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 10: Model repeating tool calls halts strictly at max_iterations limit."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Looping...",
            tool_calls=[
                OllamaToolCall(id="c_loop", name="inspect_database_schema", arguments={})
            ],
        )
    )

    agent_test_settings.agent.max_iterations = 3
    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Infinite loop query")

    assert res.status == "error"
    assert res.iterations == 3
    assert "maximum tool iterations limit" in res.final_message


@pytest.mark.asyncio
async def test_regression_scenario_11_correct_conversation_history(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 11: Conversation history preserves complete sequence and tool pairing."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="Step 1: Check schema",
                tool_calls=[
                    OllamaToolCall(id="call_inspect_1", name="inspect_database_schema", arguments={})
                ],
            ),
            OllamaChatResponse(
                content="Done inspecting schema.",
                tool_calls=[],
            ),
        ]
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    res = await orchestrator.process_message("Check schema please")

    assert res.status == "success"
    messages = orchestrator.conversation.messages
    # Sequence in conversation manager: user, assistant (with tool_calls), tool, assistant (final)
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].tool_calls is not None
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_inspect_1"
    assert messages[3].role == "assistant"
    assert messages[3].content == "Done inspecting schema."

    # When formatted for LLM with system prompt, system prompt is prepended:
    llm_msgs = orchestrator.conversation.get_messages_for_llm(system_prompt="You are an analyst.")
    assert len(llm_msgs) == 5
    assert llm_msgs[0]["role"] == "system"
    assert llm_msgs[1]["role"] == "user"
    assert llm_msgs[2]["role"] == "assistant"
    assert llm_msgs[3]["role"] == "tool"
    assert llm_msgs[4]["role"] == "assistant"


@pytest.mark.asyncio
async def test_regression_scenario_12_agent_run_result_construction_and_invariant(
    agent_test_settings: AppSettings,
) -> None:
    """Scenario 12: AgentRunResult structure and invariant `if status == 'success': assert final_message.strip()`."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(
            content="Analytical workflow concluded.",
            tool_calls=[],
        )
    )

    orchestrator = AgentOrchestrator(agent_test_settings, ollama_client=mock_ollama)
    orchestrator._initialized = True
    res = await orchestrator.process_message("Run analysis")

    # Invariant assertion
    if res.status == "success":
        assert bool(res.final_message.strip())

    # Full structure verification
    assert res.status == "success"
    assert isinstance(res.final_message, str)
    assert res.iterations == 1
    assert isinstance(res.total_duration_s, float)
    assert res.error is None
    assert isinstance(res.component_status, dict)
    assert "database_discovery" in res.component_status
    assert "sql_execution" in res.component_status
    assert "pdf_generation" in res.component_status



