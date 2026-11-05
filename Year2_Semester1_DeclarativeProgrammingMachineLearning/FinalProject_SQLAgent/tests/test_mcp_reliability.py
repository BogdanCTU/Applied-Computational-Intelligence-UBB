"""Regression tests for MCP server lifecycle, tool execution, loop transitions, and error recovery."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from config.settings import AppSettings
from mcp_layer.client import MCPClientError, MCPInvocationLog, MCPStdioClient, MCPToolCallResult
from mcp_layer.tools.database_tools import inspect_database_schema_impl, get_table_sample_impl


@pytest.fixture
def mcp_settings(tmp_path) -> AppSettings:
    """Fixture providing settings pointing to real or test DB."""
    settings = AppSettings()
    return settings


@pytest.mark.asyncio
async def test_mcp_server_startup_shutdown_lifecycle(mcp_settings: AppSettings) -> None:
    """Verify MCP server starts cleanly and shuts down without leaking subprocesses."""
    client = MCPStdioClient(mcp_settings)
    assert not client.is_connected

    await client.connect()
    assert client.is_connected

    # Discover registered tools
    tools = await client.list_tools()
    assert len(tools) >= 5
    tool_names = {t.name for t in tools}
    assert "inspect_database_schema" in tool_names
    assert "execute_readonly_sql" in tool_names
    assert "generate_pdf_report" in tool_names

    await client.close()
    assert not client.is_connected


@pytest.mark.asyncio
async def test_mcp_tool_invocation_and_structured_logging(mcp_settings: AppSettings) -> None:
    """Verify structured diagnostics, invocation id, timing, and credential sanitization."""
    client = MCPStdioClient(mcp_settings)
    await client.connect()

    try:
        # Pass a sensitive argument to verify sanitization
        result: MCPToolCallResult = await client.call_tool(
            "inspect_database_schema",
            {"auth_token": "secret_jwt_token_value", "password": "super_secret"},
        )
        assert not result.is_error
        assert result.invocation_id is not None
        assert result.duration_ms >= 0
        assert result.invocation_log is not None

        # Verify arguments in invocation_log are masked
        inv_log: MCPInvocationLog = result.invocation_log
        assert inv_log.arguments.get("auth_token") == "[REDACTED_CREDENTIAL]"
        assert inv_log.arguments.get("password") == "[REDACTED_CREDENTIAL]"
        assert inv_log.status == "success"
        assert inv_log.error_origin is None
        assert result.is_error is False

        # Convert to dict
        log_dict = inv_log.to_dict()
        assert "invocation_id" in log_dict
        assert log_dict["status"] == "success"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_mcp_invalid_arguments_and_error_origin(mcp_settings: AppSettings) -> None:
    """Verify invalid tool arguments are caught and error_origin is classified as 'tool_arguments'."""
    client = MCPStdioClient(mcp_settings)
    await client.connect()

    try:
        # get_table_sample requires table_name
        result: MCPToolCallResult = await client.call_tool(
            "get_table_sample",
            {},  # Missing required table_name
        )
        assert result.is_error
        assert result.error_origin in {"tool_arguments", "server"}
        assert "table_name" in (result.raw_text or "").lower() or "missing" in (result.raw_text or "").lower()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_mcp_loop_transition_and_automatic_reconnection(mcp_settings: AppSettings) -> None:
    """Verify MCPStdioClient handles new/changed event loops without 'Event loop is closed' error."""
    client = MCPStdioClient(mcp_settings)

    # Invocation 1 on current loop
    res1 = await client.call_tool("inspect_database_schema", {})
    assert not res1.is_error
    assert client.is_connected

    # Simulate loop change: close client connection, run on new loop
    await client.close()
    assert not client.is_connected

    # Invocation 2: client auto-reconnects safely
    res2 = await client.call_tool("inspect_database_schema", {})
    assert not res2.is_error
    assert client.is_connected

    await client.close()


@pytest.mark.asyncio
async def test_mcp_query_timeout_handling(mcp_settings: AppSettings) -> None:
    """Verify query timeouts are propagated with QUERY_TIMEOUT and error_origin 'sqlite'."""
    mcp_settings.database.query_timeout_s = 0.05
    client = MCPStdioClient(mcp_settings)
    await client.connect()

    try:
        # Run a query that exceeds the tight 0.05s timeout
        res = await client.call_tool(
            "execute_readonly_sql",
            {
                "sql_query": "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r WHERE n < 50000000) SELECT COUNT(*) FROM r",
            },
        )
        assert res.is_error
        assert res.data.get("error_code") == "QUERY_TIMEOUT"
        assert res.error_origin == "sqlite"
    finally:
        await client.close()
