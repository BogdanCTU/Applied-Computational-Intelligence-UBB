"""Real stdio MCP server/client integration tests using the official Python MCP SDK.

Spawns ``python -m mcp_layer.server`` as an actual subprocess and communicates
exclusively over JSON-RPC stdio via ``MCPStdioClient``.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from config.settings import AppSettings
from database import import_dataset
from mcp_layer.client import MCPStdioClient
from reporting import ReportHistoryManager

EXPECTED_TOOLS = {
    "inspect_database_schema",
    "get_table_sample",
    "prepare_sql_query",
    "execute_readonly_sql",
    "generate_pdf_report",
    "generate_csv_report",
}


@pytest.fixture()
def mcp_test_settings(tmp_path: Path) -> AppSettings:
    csv_dir = tmp_path / "raw"
    csv_dir.mkdir()

    with (csv_dir / "customers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "first_name", "country", "loyalty_tier"])
        w.writerows(
            [
                [1, "Alice", "USA", "gold"],
                [2, "Bob", "Canada", "silver"],
                [3, "Cara", "USA", "platinum"],
                [4, "Dan", "Germany", "none"],
            ]
        )

    with (csv_dir / "orders.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["order_id", "customer_id", "order_date", "status", "total_amount"])
        w.writerows(
            [
                [101, 1, "2026-01-15", "delivered", "250.00"],
                [102, 1, "2026-02-10", "delivered", "150.50"],
                [103, 2, "2026-02-18", "shipped", "99.95"],
                [104, 3, "2026-03-05", "delivered", "520.00"],
                [105, 4, "2026-03-09", "cancelled", "40.00"],
            ]
        )

    db_path = tmp_path / "mcp_test.db"
    import_dataset(csv_dir, db_path)

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.database.max_result_rows = 50
    settings.database.query_timeout_s = 3.0
    settings.reports.output_dir = str(tmp_path / "generated_reports")
    settings.logging.directory = str(tmp_path / "logs")
    return settings


async def test_mcp_stdio_startup_and_tool_discovery(
    mcp_test_settings: AppSettings,
) -> None:
    async with MCPStdioClient(settings=mcp_test_settings) as client:
        assert client.is_connected is True
        tools = await client.list_tools()
        discovered = {t.name: t for t in tools}

        assert set(discovered.keys()) == EXPECTED_TOOLS
        for name, spec in discovered.items():
            assert spec.description, f"Tool '{name}' missing description"
            assert spec.input_schema.get("type") == "object"


async def test_mcp_schema_inspection_and_sampling(
    mcp_test_settings: AppSettings,
) -> None:
    async with MCPStdioClient(settings=mcp_test_settings) as client:
        # Full schema inspection
        schema_res = await client.call_tool("inspect_database_schema", {})
        assert schema_res.is_error is False
        assert schema_res.data["status"] == "ok"
        assert schema_res.data["table_count"] == 2
        assert schema_res.data["total_rows"] == 9
        assert len(schema_res.data["relationships"]) == 1

        # Single table inspection
        orders_res = await client.call_tool(
            "inspect_database_schema", {"table_name": "orders"}
        )
        assert orders_res.is_error is False
        assert orders_res.data["tables"][0]["name"] == "orders"

        # Unknown table error
        missing_res = await client.call_tool(
            "inspect_database_schema", {"table_name": "does_not_exist"}
        )
        assert missing_res.is_error is True
        assert missing_res.data["error_code"] == "TABLE_NOT_FOUND"

        # Table sample with max cap enforcement (500 -> capped at 50)
        sample_res = await client.call_tool(
            "get_table_sample", {"table_name": "orders", "num_records": 500}
        )
        assert sample_res.is_error is False
        assert sample_res.data["effective_limit"] == 50
        assert sample_res.data["returned_count"] == 5

        # Invalid tool argument type (protocol-level Pydantic validation error)
        bad_arg_res = await client.call_tool(
            "get_table_sample", {"table_name": "orders", "num_records": "not_an_int"}
        )
        assert bad_arg_res.is_error is True


async def test_mcp_sql_validation_execution_and_reporting_end_to_end(
    mcp_test_settings: AppSettings,
) -> None:
    sql = """
    SELECT
        c.country,
        COUNT(o.order_id) AS orders_count,
        ROUND(SUM(o.total_amount), 2) AS revenue
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.status != 'cancelled'
    GROUP BY c.country
    ORDER BY revenue DESC
    """

    async with MCPStdioClient(settings=mcp_test_settings) as client:
        # 1. Reject unsafe SQL via prepare_sql_query
        unsafe = await client.call_tool(
            "prepare_sql_query", {"sql_query": "DROP TABLE orders"}
        )
        assert unsafe.is_error is True
        assert unsafe.data["valid"] is False
        assert unsafe.data["error_code"] == "FORBIDDEN_STATEMENT"

        # 2. Reject unsafe SQL directly in execute_readonly_sql (independent check)
        unsafe_exec = await client.call_tool(
            "execute_readonly_sql",
            {"sql_query": "INSERT INTO customers VALUES (99, 'Hack', 'US', 'none')"},
        )
        assert unsafe_exec.is_error is True
        assert unsafe_exec.data["error_code"] == "FORBIDDEN_STATEMENT"

        # 3. Prepare valid analytical SQL
        prep = await client.call_tool("prepare_sql_query", {"sql_query": sql})
        assert prep.is_error is False
        assert prep.data["valid"] is True
        assert set(prep.data["referenced_tables"]) == {"customers", "orders"}

        # 4. Execute validated SQL
        exec_res = await client.call_tool(
            "execute_readonly_sql", {"sql_query": prep.data["sql_query"]}
        )
        assert exec_res.is_error is False
        assert exec_res.data["record_count"] == 2
        cols = exec_res.data["columns"]
        rows = exec_res.data["rows"]
        assert cols == ["country", "orders_count", "revenue"]
        assert rows[0] == ["USA", 3, 920.5]

        # 5. Generate PDF report over MCP
        pdf_res = await client.call_tool(
            "generate_pdf_report",
            {
                "title": "Revenue by Country",
                "description": "Captured non-cancelled order revenue grouped by customer country.",
                "sql_query": prep.data["sql_query"],
                "columns": cols,
                "rows": rows,
                "summary": "USA leads with $920.50 across 3 orders.",
                "user_request": "Show me revenue by country",
            },
        )
        assert pdf_res.is_error is False
        assert pdf_res.data["output_format"] == "PDF"
        assert pdf_res.data["record_count"] == 2
        pdf_file = Path(pdf_res.data["output_path"])
        assert pdf_file.is_file()
        assert pdf_file.read_bytes().startswith(b"%PDF-")

        # 6. Generate CSV report over MCP
        csv_res = await client.call_tool(
            "generate_csv_report",
            {
                "title": "Revenue by Country",
                "columns": cols,
                "rows": rows,
                "description": "CSV export of revenue by country",
                "sql_query": prep.data["sql_query"],
                "user_request": "Export revenue by country as CSV",
            },
        )
        assert csv_res.is_error is False
        assert csv_res.data["output_format"] == "CSV"
        csv_file = Path(csv_res.data["output_path"])
        assert csv_file.is_file()
        with csv_file.open("r", encoding="utf-8", newline="") as fh:
            csv_rows = list(csv.reader(fh))
        assert csv_rows == [
            ["country", "orders_count", "revenue"],
            ["USA", "3", "920.5"],
            ["Canada", "1", "99.95"],
        ]

    # 7. Verify shared ReportHistoryManager persisted both reports from subprocess
    history = ReportHistoryManager(mcp_test_settings.output_dir).list_reports()
    assert len(history) == 2
    assert {h.output_format for h in history} == {"PDF", "CSV"}


async def test_mcp_limits_timeout_and_security_over_stdio(
    mcp_test_settings: AppSettings,
) -> None:
    mcp_test_settings.database.max_result_rows = 2
    mcp_test_settings.database.query_timeout_s = 0.08

    async with MCPStdioClient(settings=mcp_test_settings) as client:
        # Row limit enforcement over stdio
        limited = await client.call_tool(
            "execute_readonly_sql",
            {"sql_query": "SELECT order_id FROM orders ORDER BY order_id", "row_limit": 99},
        )
        assert limited.is_error is False
        assert limited.data["effective_row_limit"] == 2
        assert limited.data["record_count"] == 2
        assert limited.data["truncated"] is True

        # Timeout enforcement over stdio
        spin = await client.call_tool(
            "execute_readonly_sql",
            {
                "sql_query": (
                    "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r WHERE n < 50000000) "
                    "SELECT COUNT(*) FROM r"
                )
            },
        )
        assert spin.is_error is True
        assert spin.data["error_code"] == "QUERY_TIMEOUT"

        # Path traversal attempt in report title stays confined to output_dir
        safe_pdf = await client.call_tool(
            "generate_pdf_report",
            {
                "title": "../../../../etc/evil_report",
                "description": "Traversal sanitization check",
                "sql_query": "SELECT 1 AS flag",
                "columns": ["flag"],
                "rows": [],
            },
        )
        assert safe_pdf.is_error is False
        out_path = Path(safe_pdf.data["output_path"]).resolve()
        assert out_path.parent == mcp_test_settings.output_dir.resolve()
        assert out_path.is_file()

        # Unknown tool invocation returns error cleanly without crashing server
        unknown = await client.call_tool("nonexistent_mcp_tool", {})
        assert unknown.is_error is True

