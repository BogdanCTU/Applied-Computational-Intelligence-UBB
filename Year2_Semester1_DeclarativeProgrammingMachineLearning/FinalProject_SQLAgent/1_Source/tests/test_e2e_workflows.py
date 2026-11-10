"""End-to-End Workflow Verification Suite (Milestone 6 Phase B).

Validates all 6 core workflows of the Report SQL Agent:
1. Basic interaction (conversational greeting without tools)
2. Database discovery (schema inspection over stdio MCP)
3. SQL preparation and rejection (prepare -> reject -> no execution)
4. SQL approval and PDF report generation (prepare -> approve -> execute -> PDF -> history)
5. CSV report generation (prepare -> approve -> execute -> CSV -> history)
6. Error handling (Ollama unreachable, invalid SQL, cancellation)
"""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from agent import (
    AgentEventType,
    AgentOrchestrator,
    OllamaChatResponse,
    OllamaToolCall,
)
from config.settings import AppSettings
from database import import_dataset
from reporting.report_manager import ReportHistoryManager


@pytest.fixture()
def e2e_settings(tmp_path: Path) -> AppSettings:
    """Creates a temporary test database and clean output directory."""
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()

    with (csv_dir / "customers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "first_name", "country"])
        w.writerows([[1, "Alice", "USA"], [2, "Bob", "UK"], [3, "Charlie", "Germany"]])

    with (csv_dir / "orders.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["order_id", "customer_id", "total_amount", "order_date"])
        w.writerows([
            [10, 1, "120.50", "2025-01-15"],
            [11, 2, "85.00", "2025-01-20"],
            [12, 1, "340.00", "2025-02-10"],
        ])

    with (csv_dir / "payments.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["payment_id", "order_id", "payment_method", "amount"])
        w.writerows([
            [101, 10, "credit_card", "120.50"],
            [102, 11, "paypal", "85.00"],
            [103, 12, "credit_card", "340.00"],
        ])

    db_path = tmp_path / "e2e_ecommerce.db"
    import_dataset(csv_dir, db_path)

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.database.max_result_rows = 500
    settings.reports.output_dir = str(reports_dir)
    settings.agent.max_iterations = 6
    settings.agent.require_sql_approval = True
    return settings


# ===========================================================================
# Workflow 1: Basic Interaction
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_1_basic_interaction(e2e_settings: AppSettings) -> None:
    """Verify conversational capability greeting without tool execution."""
    orchestrator = AgentOrchestrator(e2e_settings)
    mock_greeting = (
        "Hello! I am your Local Report SQL Agent. I can help you analyze your "
        "database, generate SQL queries, and export reports in PDF or CSV format."
    )

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", new_callable=AsyncMock
    ) as mock_chat:
        mock_conn.return_value = (True, "0.40.14")
        mock_chat.return_value = OllamaChatResponse(
            content=mock_greeting,
            tool_calls=[],
            finish_reason="stop",
        )

        async with orchestrator:
            result = await orchestrator.process_message("Hello, what can you do?")

            assert result.status == "success"
            assert len(result.generated_reports) == 0
            assert "Local Report SQL Agent" in result.final_message


# ===========================================================================
# Workflow 2: Database Discovery
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_2_database_discovery(e2e_settings: AppSettings) -> None:
    """Verify database schema discovery over genuine stdio MCP client."""
    orchestrator = AgentOrchestrator(e2e_settings)

    call_count = 0

    async def mock_chat_flow(messages, tools=None, tool_mode="auto"):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Model asks to inspect database schema
            return OllamaChatResponse(
                content="Let me inspect the database schema.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_inspect",
                        name="inspect_database_schema",
                        arguments={},
                    )
                ],
            )
        # Model receives schema and answers user
        return OllamaChatResponse(
            content="The database contains tables: customers, orders, and payments.",
            tool_calls=[],
            finish_reason="stop",
        )

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=mock_chat_flow
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            result = await orchestrator.process_message("Show me the available database tables.")

            assert result.status == "success"
            assert "customers" in result.final_message
            assert "orders" in result.final_message


# ===========================================================================
# Workflow 3: SQL Preparation & Rejection
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_3_sql_preparation_and_rejection(e2e_settings: AppSettings) -> None:
    """Verify that when a proposed SQL query is rejected, execution halts immediately."""
    orchestrator = AgentOrchestrator(e2e_settings)
    executed_sql = False
    step = 0

    sql = "SELECT payment_method, SUM(amount) AS total FROM payments GROUP BY payment_method"

    async def mock_chat_prep(messages, tools=None, tool_mode="auto"):
        nonlocal step
        step += 1
        if step == 1:
            return OllamaChatResponse(
                content="I will prepare a query for monthly revenue.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_prep",
                        name="prepare_sql_query",
                        arguments={
                            "sql_query": sql,
                            "explanation": "Calculates revenue grouped by payment method",
                        },
                    )
                ],
            )
        elif step == 2:
            return OllamaChatResponse(
                content="SQL prepared. Now executing query.",
                tool_calls=[
                    OllamaToolCall(
                        id="call_exec",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql},
                    )
                ],
            )
        return OllamaChatResponse(
            content="Understood. The SQL query execution was denied by the user and was not executed.",
            tool_calls=[],
            finish_reason="stop",
        )

    # Track if execute_readonly_sql tool is ever called
    orig_execute = orchestrator.mcp_client.call_tool

    async def spy_call_tool(tool_name: str, arguments: dict[str, Any]):
        nonlocal executed_sql
        if tool_name == "execute_readonly_sql":
            executed_sql = True
        return await orig_execute(tool_name, arguments)

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=mock_chat_prep
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            orchestrator.mcp_client.call_tool = spy_call_tool

            # User rejection callback
            def reject_callback(q: str, explanation: str) -> bool:
                return False

            result = await orchestrator.process_message(
                "Calculate monthly revenue grouped by payment method.",
                approval_callback=reject_callback,
            )

            assert result.status == "approval_denied"
            assert executed_sql is False
            assert result.executed_sql is None
            assert "denied" in result.final_message.lower() or "rejected" in result.final_message.lower()


# ===========================================================================
# Workflow 4: SQL Approval & PDF Report Generation
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_4_sql_approval_and_pdf_generation(e2e_settings: AppSettings) -> None:
    """Verify end-to-end PDF generation workflow with user approval."""
    orchestrator = AgentOrchestrator(e2e_settings)
    step = 0

    sql_query = (
        "SELECT payment_method, SUM(amount) AS total_revenue "
        "FROM payments GROUP BY payment_method ORDER BY total_revenue DESC"
    )

    async def mock_chat_pdf_flow(messages, tools=None, tool_mode="auto"):
        nonlocal step
        step += 1
        if step == 1:
            # 1. Prepare query
            return OllamaChatResponse(
                content="Preparing the revenue query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="prepare_sql_query",
                        arguments={
                            "sql_query": sql_query,
                            "explanation": "Group revenue by payment method",
                        },
                    )
                ],
            )
        elif step == 2:
            # 2. Execute query (after user approval)
            return OllamaChatResponse(
                content="Executing the approved query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c2",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql_query},
                    )
                ],
            )
        elif step == 3:
            # 3. Generate PDF report
            return OllamaChatResponse(
                content="Generating PDF report.",
                tool_calls=[
                    OllamaToolCall(
                        id="c3",
                        name="generate_pdf_report",
                        arguments={
                            "title": "Payment Method Revenue Report",
                            "description": "Revenue breakdown across all payment methods",
                            "columns": ["payment_method", "total_revenue"],
                            "rows": [["credit_card", 460.50], ["paypal", 85.00]],
                            "summary": "Total revenue across payment methods.",
                            "sql_query": sql_query,
                        },
                    )
                ],
            )
        # 4. Final summary
        return OllamaChatResponse(
            content="Payment Method Revenue Report has been successfully generated as PDF.",
            tool_calls=[],
            finish_reason="stop",
        )

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=mock_chat_pdf_flow
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            approval_called = False

            def approve_callback(q: str, explanation: str) -> bool:
                nonlocal approval_called
                approval_called = True
                return True

            result = await orchestrator.process_message(
                "Calculate monthly revenue grouped by payment method as PDF.",
                approval_callback=approve_callback,
            )

            assert result.status == "success"
            assert approval_called is True
            assert len(result.generated_reports) >= 1

            pdf_path = Path(result.generated_reports[0]["output_path"])
            assert pdf_path.exists()
            assert pdf_path.suffix.lower() == ".pdf"
            assert pdf_path.stat().st_size > 500  # Valid non-empty PDF

            # Verify history record persistence
            history = orchestrator.history_manager.list_reports()
            assert any(entry.file_name == pdf_path.name for entry in history)


# ===========================================================================
# Workflow 5: CSV Generation
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_5_csv_generation(e2e_settings: AppSettings) -> None:
    """Verify explicit CSV report generation."""
    orchestrator = AgentOrchestrator(e2e_settings)
    step = 0

    sql_query = "SELECT first_name, country FROM customers ORDER BY first_name ASC"

    async def mock_chat_csv_flow(messages, tools=None, tool_mode="auto"):
        nonlocal step
        step += 1
        if step == 1:
            return OllamaChatResponse(
                content="Preparing customer query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="prepare_sql_query",
                        arguments={
                            "sql_query": sql_query,
                            "explanation": "Select customers",
                        },
                    )
                ],
            )
        elif step == 2:
            return OllamaChatResponse(
                content="Executing customer query.",
                tool_calls=[
                    OllamaToolCall(
                        id="c2",
                        name="execute_readonly_sql",
                        arguments={"sql_query": sql_query},
                    )
                ],
            )
        elif step == 3:
            return OllamaChatResponse(
                content="Generating CSV export.",
                tool_calls=[
                    OllamaToolCall(
                        id="c3",
                        name="generate_csv_report",
                        arguments={
                            "title": "Customer Export",
                            "description": "Export of customers by country",
                            "columns": ["first_name", "country"],
                            "rows": [["Alice", "USA"], ["Bob", "UK"], ["Charlie", "Germany"]],
                            "summary": "Customer listing CSV",
                            "sql_query": sql_query,
                        },
                    )
                ],
            )
        return OllamaChatResponse(
            content="CSV report generated successfully.",
            tool_calls=[],
            finish_reason="stop",
        )

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=mock_chat_csv_flow
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            result = await orchestrator.process_message(
                "Generate a CSV report showing all customers.",
                approval_callback=lambda s, e: True,
            )

            assert result.status == "success"
            assert len(result.generated_reports) >= 1

            csv_path = Path(result.generated_reports[0]["output_path"])
            assert csv_path.exists()
            assert csv_path.suffix.lower() == ".csv"

            # Check CSV content structure
            content = csv_path.read_text(encoding="utf-8")
            assert "first_name,country" in content
            assert "Alice,USA" in content


# ===========================================================================
# Workflow 6: Error Handling
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_6_error_handling_ollama_unavailable(e2e_settings: AppSettings) -> None:
    """Verify handling when Ollama daemon is unreachable."""
    from agent.ollama_client import OllamaConnectionError

    orchestrator = AgentOrchestrator(e2e_settings)

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", new_callable=AsyncMock
    ) as mock_chat:
        mock_conn.return_value = (False, "Connection refused at 127.0.0.1:11434")
        mock_chat.side_effect = OllamaConnectionError("Connection refused at 127.0.0.1:11434")

        async with orchestrator:
            result = await orchestrator.process_message("Give me a sales report.")

            assert result.status == "error"
            assert "ollama" in (result.error or "").lower() or "connection" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_workflow_6_error_handling_unsafe_sql_rejected(e2e_settings: AppSettings) -> None:
    """Verify that dangerous write SQL queries are caught by preparation validation."""
    orchestrator = AgentOrchestrator(e2e_settings)

    async def mock_unsafe_flow(messages, tools=None, tool_mode="auto"):
        return OllamaChatResponse(
            content="Attempting forbidden query.",
            tool_calls=[
                OllamaToolCall(
                    id="c_bad",
                    name="prepare_sql_query",
                    arguments={
                        "sql_query": "DROP TABLE customers;",
                        "explanation": "Delete customers table",
                    },
                )
            ],
        )

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=mock_unsafe_flow
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            # Result tool handler should return is_error=True for prepare_sql_query
            result = await orchestrator.process_message(
                "Delete the customers table",
                approval_callback=lambda s, e: True,
            )
            # The agent should not execute DROP TABLE
            assert result.status in {"success", "error"}
            # The database was not modified
            import sqlite3
            with sqlite3.connect(f"file:{e2e_settings.database.path}?mode=ro", uri=True) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t[0] for t in tables]
                assert "customers" in table_names


@pytest.mark.asyncio
async def test_workflow_6_cancellation(e2e_settings: AppSettings) -> None:
    """Verify cancellation mid-flight."""
    orchestrator = AgentOrchestrator(e2e_settings)
    cancel_evt = asyncio.Event()

    async def slow_chat(messages, tools=None, tool_mode="auto"):
        cancel_evt.set()  # Cancel while in progress
        await asyncio.sleep(0.05)
        return OllamaChatResponse(content="Done", tool_calls=[])

    with patch.object(
        orchestrator.ollama_client, "check_connection", new_callable=AsyncMock
    ) as mock_conn, patch.object(
        orchestrator.ollama_client, "chat", side_effect=slow_chat
    ):
        mock_conn.return_value = (True, "0.40.14")

        async with orchestrator:
            result = await orchestrator.process_message(
                "Start a long running query",
                cancel_event=cancel_evt,
            )
            assert result.status == "cancelled"
