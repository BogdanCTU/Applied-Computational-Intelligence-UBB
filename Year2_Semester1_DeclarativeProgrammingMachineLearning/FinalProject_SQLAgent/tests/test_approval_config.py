"""Tests for Phase 1: Configurable SQL Approval in Agent and Orchestrator."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import (
    ActivityCategory,
    ActivityEvent,
    AgentOrchestrator,
    OllamaChatResponse,
    OllamaToolCall,
)
from config.settings import AppSettings, load_settings, save_settings
from database import import_dataset
from mcp_layer.client import MCPToolCallResult, MCPToolSpec


@pytest.fixture()
def approval_test_settings(tmp_path: Path) -> AppSettings:
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

    db_path = tmp_path / "approval_test.db"
    import_dataset(csv_dir, db_path)

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.max_iterations = 6
    # Default is False per Milestone 9 requirements
    return settings


def _create_mock_orchestrator(
    settings: AppSettings,
    tool_sequence: list[tuple[str, dict[str, Any]]],
    tool_results: list[dict[str, Any]],
) -> AgentOrchestrator:
    """Helper to construct an orchestrator with deterministic mocked Ollama & MCP tools."""
    mock_ollama = MagicMock()
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.list_local_models = AsyncMock(return_value=["qwen3.5:4b"])
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")
    responses: list[OllamaChatResponse] = []
    for idx, (t_name, t_args) in enumerate(tool_sequence):
        responses.append(
            OllamaChatResponse(
                content=f"Calling {t_name}",
                tool_calls=[
                    OllamaToolCall(
                        id=f"call_{idx}",
                        name=t_name,
                        arguments=t_args,
                    )
                ],
            )
        )
    responses.append(
        OllamaChatResponse(
            content="Operation completed successfully.",
            tool_calls=[],
        )
    )
    mock_ollama.chat = AsyncMock(side_effect=responses)

    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.connect = AsyncMock()
    mock_client.list_tools = AsyncMock(
        return_value=[
            MCPToolSpec("inspect_database_schema", "Inspect database schema", {}),
            MCPToolSpec("get_table_sample", "Sample table rows", {}),
            MCPToolSpec("prepare_sql_query", "Prepare and validate SQL query", {}),
            MCPToolSpec("execute_readonly_sql", "Execute read-only SQL", {}),
            MCPToolSpec("generate_pdf_report", "Generate PDF", {}),
            MCPToolSpec("generate_csv_report", "Generate CSV", {}),
        ]
    )

    call_results: list[MCPToolCallResult] = []
    for tr in tool_results:
        is_err = tr.get("status") == "error"
        call_results.append(
            MCPToolCallResult(
                tool_name="execute_readonly_sql",
                is_error=is_err,
                data=tr,
                raw_text=json.dumps(tr),
            )
        )
    mock_client.call_tool = AsyncMock(side_effect=call_results)

    return AgentOrchestrator(
        settings,
        ollama_client=mock_ollama,
        mcp_client=mock_client,
    )


# ---------------------------------------------------------------------------
# Phase 1: 8 Mandatory Tests
# ---------------------------------------------------------------------------


def test_1_default_configuration_has_approval_disabled() -> None:
    """Requirement 1: Default configuration has manual approval disabled."""
    settings = AppSettings()
    assert settings.agent.require_sql_approval is False


@pytest.mark.asyncio
async def test_2_disabled_approval_automatically_approves_valid_sql(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 2: Disabled approval automatically approves valid SQL without prompting user."""
    approval_test_settings.agent.require_sql_approval = False
    valid_query = "SELECT order_id, total_amount FROM orders"

    orchestrator = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": valid_query})],
        tool_results=[{"columns": ["order_id", "total_amount"], "rows": [[10, "100.00"]]}],
    )

    approval_called = False

    def mock_approval(query: str, explanation: str) -> bool:
        nonlocal approval_called
        approval_called = True
        return True

    res = await orchestrator.process_message("List orders", approval_callback=mock_approval)
    assert res.status == "success"
    # Approval callback was NOT invoked because manual approval is disabled
    assert approval_called is False
    # MCP tool was called and executed
    assert orchestrator.tool_handler.mcp_client.call_tool.await_count == 1


@pytest.mark.asyncio
async def test_3_enabled_approval_invokes_approval_callback(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 3: Enabled approval invokes the approval callback with query and explanation."""
    approval_test_settings.agent.require_sql_approval = True
    valid_query = "SELECT order_id, total_amount FROM orders"

    orchestrator = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": valid_query})],
        tool_results=[{"columns": ["order_id", "total_amount"], "rows": [[10, "100.00"]]}],
    )

    captured_queries: list[str] = []
    captured_explanations: list[str] = []

    def mock_approval(query: str, explanation: str) -> bool:
        captured_queries.append(query)
        captured_explanations.append(explanation)
        return True

    res = await orchestrator.process_message("List orders", approval_callback=mock_approval)
    assert res.status == "success"
    assert len(captured_queries) == 1
    assert "SELECT order_id, total_amount FROM orders" in captured_queries[0]
    assert len(captured_explanations) == 1


@pytest.mark.asyncio
async def test_4_rejected_queries_never_execute(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 4: Rejected queries never execute when user denies approval."""
    approval_test_settings.agent.require_sql_approval = True
    valid_query = "SELECT order_id, total_amount FROM orders"

    orchestrator = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": valid_query})],
        tool_results=[{"columns": ["order_id", "total_amount"], "rows": [[10, "100.00"]]}],
    )

    def deny_approval(query: str, explanation: str) -> bool:
        return False

    res = await orchestrator.process_message("List orders", approval_callback=deny_approval)
    assert res.status == "approval_denied"
    # The MCP tool was never dispatched to the database
    assert orchestrator.tool_handler.mcp_client.call_tool.await_count == 0


@pytest.mark.asyncio
async def test_5_invalid_sql_never_executes_even_when_auto_approval_enabled(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 5: Invalid SQL never executes even when automatic approval is enabled."""
    approval_test_settings.agent.require_sql_approval = False
    invalid_query = "SELECT FROM WHERE broken syntax"

    orchestrator = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": invalid_query})],
        tool_results=[],
    )

    res = await orchestrator.process_message("Execute broken SQL")
    # MCP tool was NOT called because AST validation caught the invalid syntax
    assert orchestrator.tool_handler.mcp_client.call_tool.await_count == 0


@pytest.mark.asyncio
async def test_6_non_readonly_sql_never_executes_even_when_auto_approval_enabled(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 6: Non-read-only SQL never executes even when automatic approval is enabled."""
    approval_test_settings.agent.require_sql_approval = False

    for dangerous_sql in [
        "DROP TABLE orders",
        "DELETE FROM customers",
        "INSERT INTO customers (customer_id) VALUES (99)",
        "UPDATE orders SET total_amount = 0",
        "ATTACH DATABASE 'hack.db' AS hacked",
    ]:
        orchestrator = _create_mock_orchestrator(
            approval_test_settings,
            tool_sequence=[("execute_readonly_sql", {"sql_query": dangerous_sql})],
            tool_results=[],
        )

        res = await orchestrator.process_message("Run dangerous SQL")
        # Tool was blocked before execution
        assert orchestrator.tool_handler.mcp_client.call_tool.await_count == 0


@pytest.mark.asyncio
async def test_7_activity_inspector_distinguishes_auto_and_manual_approval(
    approval_test_settings: AppSettings,
) -> None:
    """Requirement 7: Activity inspector distinguishes automatic and manual approval events."""
    valid_query = "SELECT order_id FROM orders"

    # 1. Test auto approval event
    approval_test_settings.agent.require_sql_approval = False
    orchestrator_auto = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": valid_query})],
        tool_results=[{"columns": ["order_id"], "rows": [[10]]}],
    )

    events_auto: list[ActivityEvent] = []

    def record_auto(event: Any) -> None:
        if getattr(event, "activity_event", None):
            events_auto.append(event.activity_event)

    await orchestrator_auto.process_message("List orders", progress_callback=record_auto)

    approval_events_auto = [e for e in events_auto if e.category == ActivityCategory.APPROVAL_RESULT.value]
    assert len(approval_events_auto) == 1
    assert approval_events_auto[0].status == "auto_approved"
    assert "SQL automatically approved — manual approval is disabled in settings." in approval_events_auto[0].description

    # 2. Test manual approval event
    approval_test_settings.agent.require_sql_approval = True
    orchestrator_manual = _create_mock_orchestrator(
        approval_test_settings,
        tool_sequence=[("execute_readonly_sql", {"sql_query": valid_query})],
        tool_results=[{"columns": ["order_id"], "rows": [[10]]}],
    )

    events_manual: list[ActivityEvent] = []

    def record_manual(event: Any) -> None:
        if getattr(event, "activity_event", None):
            events_manual.append(event.activity_event)

    await orchestrator_manual.process_message(
        "List orders",
        approval_callback=lambda q, e: True,
        progress_callback=record_manual,
    )

    approval_events_manual = [e for e in events_manual if e.category == ActivityCategory.APPROVAL_RESULT.value]
    assert len(approval_events_manual) == 1
    assert approval_events_manual[0].status == "success"
    assert "User explicitly approved" in approval_events_manual[0].description


def test_8_setting_persists_after_application_restart(tmp_path: Path) -> None:
    """Requirement 8: Setting persists after application restart."""
    config_file = tmp_path / "test_settings.json"

    # Start with default (False)
    settings = load_settings(path=config_file, apply_env=False)
    assert settings.agent.require_sql_approval is False

    # Modify to True and save
    settings.agent.require_sql_approval = True
    save_settings(settings, path=config_file)

    # Reload from disk
    reloaded = load_settings(path=config_file, apply_env=False)
    assert reloaded.agent.require_sql_approval is True

    # Modify to False and save
    reloaded.agent.require_sql_approval = False
    save_settings(reloaded, path=config_file)

    # Reload again
    reloaded2 = load_settings(path=config_file, apply_env=False)
    assert reloaded2.agent.require_sql_approval is False

