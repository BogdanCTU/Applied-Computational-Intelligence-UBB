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
    AgentEventType,
    AgentOrchestrator,
    ConversationManager,
    ConversationMessage,
    OllamaChatResponse,
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaToolCall,
    ToolHandler,
    build_system_prompt,
    detect_requested_report_format,
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
    assert res.data["error_code"] == "INVALID_TOOL_ARGUMENTS"

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

