"""Comprehensive tests for Report Data Accuracy (Problem 2) and Agent Execution Reliability (Problem 1).

Covers:
- Test 1: SQL result consistency across tables, charts, and KPIs
- Test 2: KPI calculation accuracy and no double-counting
- Test 3: Pie chart percentage calculations totaling ~100% and non-negative filtering
- Test 4: Bar chart data accuracy and category aggregation
- Test 5: Line chart ordering (chronological) and series values
- Test 6: Invalid chart specifications (missing columns, non-numeric Y-axis)
- Test 7: Handling of missing and NULL values in numeric columns
- Test 8: Empty SQL results producing clean "No Data" report without crashing
- Test 9: Multiple chart configurations using the same SQL result
- Test 10: Report validation failures and warnings generation
- Test 11: Ollama tool-calling responses with multiple tool calls
- Test 12: Tool message correlation with tool_call_id
- Test 13: Non-empty response invariant enforcement in AgentOrchestrator
- Test 14: Windows subprocess environment variable preservation in MCP client
"""

from __future__ import annotations

import csv
import os
import platform
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.conversation import ConversationManager, ConversationMessage
from agent.ollama_client import OllamaChatResponse, OllamaClient, OllamaToolCall
from agent.orchestrator import AgentOrchestrator, AgentRunResult, _synthesize_kpis
from config.settings import AppSettings, OllamaSettings
from database.importer import import_dataset
from mcp_layer.client import MCPStdioClient, _build_subprocess_env
from reporting.canonical_data import (
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    TransformedChartData,
    extract_and_transform_chart,
    safe_float,
)
from reporting.pdf_generator import generate_pdf_file


@pytest.fixture()
def test_app_settings(tmp_path: Path) -> AppSettings:
    """Fixture providing an isolated SQLite database and AppSettings."""
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

    db_path = tmp_path / "accuracy_test.db"
    import_dataset(csv_dir, db_path)

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.database.max_result_rows = 50
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.agent.max_iterations = 6
    settings.agent.require_sql_approval = False
    return settings


# ===========================================================================
# Test 1: SQL result consistency across tables, charts, and KPIs
# ===========================================================================

def test_sql_result_consistency_across_tables_charts_and_kpis() -> None:
    """Verify that table rows, chart aggregates, and KPI totals all derive from CanonicalSQLDataset."""
    columns = ["category", "total_orders", "net_revenue"]
    rows = [
        ["Electronics", 50, 15000.0],
        ["Clothing", 30, 9000.0],
        ["Home & Garden", 20, 6000.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows, name="sales_by_cat")

    # 1. Table rows check
    assert dataset.row_count == 3
    assert len(dataset.table_rows) == 3

    # 2. KPI check
    kpis = dataset.compute_deterministic_kpis()
    kpi_map = {k["label"]: k["value"] for k in kpis}
    assert kpi_map["Total Orders"] == "100"
    assert kpi_map["Total Revenue"] == "$30,000.00"

    # 3. Chart extraction check
    spec = ChartSpecification(
        chart_type="bar",
        title="Revenue by Category",
        x_axis="category",
        y_axis="net_revenue",
        aggregation_method="sum",
    )
    transformed = extract_and_transform_chart(dataset, spec)
    assert transformed.is_valid is True
    assert transformed.categories == ["Electronics", "Clothing", "Home & Garden"]
    assert transformed.data_series == [[15000.0, 9000.0, 6000.0]]

    # Sum of chart series exactly matches KPI revenue
    chart_total = sum(transformed.data_series[0])
    assert chart_total == 30000.0

    # 4. Consistency validator
    val_res = ReportConsistencyValidator.validate_report_components(
        dataset,
        charts=[transformed],
        kpis=kpis,
    )
    assert val_res["is_consistent"] is True
    assert len(val_res["issues"]) == 0


# ===========================================================================
# Test 2: KPI calculation accuracy and no double-counting
# ===========================================================================

def test_kpi_calculation_accuracy_and_no_double_counting() -> None:
    """Verify distinct column parsing prevents double counting and computes correct AOV."""
    columns = ["month", "total_orders", "gross_sales", "net_revenue", "total_transactions"]
    rows = [
        ["2026-08", 120, 18000.0, 17100.0, 120],
        ["2026-09", 180, 27000.0, 25650.0, 180],
    ]
    dataset = CanonicalSQLDataset(columns, rows)
    kpis = dataset.compute_deterministic_kpis()
    kpi_dict = {k["label"]: k["value"] for k in kpis}

    assert kpi_dict["Total Orders"] == "300"
    assert kpi_dict["Sales Volume"] == "$45,000.00"
    assert kpi_dict["Total Revenue"] == "$42,750.00"
    assert kpi_dict["Transactions"] == "300"
    # AOV = Net Revenue / Orders = 42750 / 300 = 142.50
    assert kpi_dict["Average Order Value"] == "$142.50"


def test_kpi_distinct_id_counting_fallback() -> None:
    """Verify distinct count works when raw unaggregated transaction rows are provided."""
    columns = ["order_id", "payment_id", "total_amount"]
    rows = [
        [101, "pay_1", 50.0],
        [101, "pay_2", 25.0],  # Same order, split payment
        [102, "pay_3", 100.0],
        [103, "pay_4", 200.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)
    kpis = dataset.compute_deterministic_kpis()
    kpi_dict = {k["label"]: k["value"] for k in kpis}

    assert kpi_dict["Total Orders"] == "3"  # distinct orders (101, 102, 103)
    assert kpi_dict["Transactions"] == "4"  # distinct payments
    assert kpi_dict["Total Revenue"] == "$375.00"


# ===========================================================================
# Test 3: Pie chart percentage calculations totaling ~100% and non-negative filtering
# ===========================================================================

def test_pie_chart_percentage_and_non_negative_filtering() -> None:
    """Verify negative and zero slices are handled, percentages sum to 100%, and tail is grouped into 'Other'."""
    columns = ["product", "revenue"]
    rows = [
        ["Prod A", 500.0],
        ["Prod B", 300.0],
        ["Prod C", 200.0],
        ["Prod D (Return)", -50.0],  # Negative refund
        ["Prod E (Zero)", 0.0],      # Zero revenue
        ["Prod F", 150.0],
        ["Prod G", 100.0],
        ["Prod H", 80.0],
        ["Prod I", 50.0],
        ["Prod J", 20.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)
    spec = ChartSpecification(
        chart_type="pie",
        title="Revenue Share",
        x_axis="product",
        y_axis="revenue",
    )
    transformed = extract_and_transform_chart(dataset, spec)

    assert transformed.is_valid is True
    # Non-negative filtering: negative slice was filtered out with warning
    assert any("negative" in w.lower() for w in transformed.warnings)
    assert "Prod D (Return)" not in transformed.categories

    # Top slices preserved with 'Other' grouping because > 7 categories
    assert "Other" in transformed.categories
    assert len(transformed.categories) <= 8

    # Check percentages exist and sum to 100.0% (+- 0.2% rounding tolerance)
    assert transformed.percentages is not None
    assert len(transformed.percentages) == len(transformed.categories)
    assert sum(transformed.percentages) == pytest.approx(100.0, abs=0.2)


# ===========================================================================
# Test 4: Bar chart data accuracy and category aggregation
# ===========================================================================

def test_bar_chart_category_aggregation_methods() -> None:
    """Verify sum, avg, count, min, and max aggregations when grouping repeated categories."""
    columns = ["department", "sales"]
    rows = [
        ["Support", 100.0],
        ["Sales", 300.0],
        ["Support", 200.0],
        ["Sales", 500.0],
        ["Engineering", 400.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)

    # 1. SUM aggregation
    spec_sum = ChartSpecification(
        chart_type="bar",
        title="Sales by Dept (Sum)",
        x_axis="department",
        y_axis="sales",
        aggregation_method="sum",
        sorting="none",
    )
    res_sum = extract_and_transform_chart(dataset, spec_sum)
    sum_map = dict(zip(res_sum.categories, res_sum.data_series[0]))
    assert sum_map["Support"] == 300.0
    assert sum_map["Sales"] == 800.0
    assert sum_map["Engineering"] == 400.0

    # 2. AVG aggregation
    spec_avg = ChartSpecification(
        chart_type="bar",
        title="Sales by Dept (Avg)",
        x_axis="department",
        y_axis="sales",
        aggregation_method="avg",
        sorting="none",
    )
    res_avg = extract_and_transform_chart(dataset, spec_avg)
    avg_map = dict(zip(res_avg.categories, res_avg.data_series[0]))
    assert avg_map["Support"] == 150.0
    assert avg_map["Sales"] == 400.0
    assert avg_map["Engineering"] == 400.0

    # 3. COUNT aggregation
    spec_cnt = ChartSpecification(
        chart_type="bar",
        title="Sales by Dept (Count)",
        x_axis="department",
        y_axis="sales",
        aggregation_method="count",
        sorting="none",
    )
    res_cnt = extract_and_transform_chart(dataset, spec_cnt)
    cnt_map = dict(zip(res_cnt.categories, res_cnt.data_series[0]))
    assert cnt_map["Support"] == 2.0
    assert cnt_map["Sales"] == 2.0
    assert cnt_map["Engineering"] == 1.0


# ===========================================================================
# Test 5: Line chart ordering (chronological) and series values
# ===========================================================================

def test_line_chart_chronological_ordering() -> None:
    """Verify unordered date strings are sorted chronologically for line charts."""
    columns = ["order_date", "daily_revenue"]
    rows = [
        ["2026-03-15", 350.0],
        ["2026-01-10", 120.0],
        ["2026-02-20", 240.0],
        ["2026-01-05", 100.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)
    spec = ChartSpecification(
        chart_type="line",
        title="Revenue Trend",
        x_axis="order_date",
        y_axis="daily_revenue",
        sorting="asc",
    )
    res = extract_and_transform_chart(dataset, spec)
    assert res.is_valid is True
    assert res.categories == ["2026-01-05", "2026-01-10", "2026-02-20", "2026-03-15"]
    assert res.data_series == [[100.0, 120.0, 240.0, 350.0]]


# ===========================================================================
# Test 6: Invalid chart specifications (missing columns, non-numeric Y-axis)
# ===========================================================================

def test_invalid_chart_specification_error_handling() -> None:
    """Verify missing columns and non-numeric metrics report validation errors gracefully."""
    columns = ["customer_name", "status"]
    rows = [
        ["Alice", "active"],
        ["Bob", "pending"],
    ]
    dataset = CanonicalSQLDataset(columns, rows)

    # 1. Non-existent column
    spec_missing = ChartSpecification(
        chart_type="bar",
        title="Missing Column Chart",
        x_axis="missing_col",
        y_axis="status",
    )
    res_missing = extract_and_transform_chart(dataset, spec_missing)
    assert res_missing.is_valid is False
    assert "not found" in str(res_missing.error_message).lower()

    # 2. Non-numeric Y-axis
    spec_non_numeric = ChartSpecification(
        chart_type="bar",
        title="Non-numeric Y",
        x_axis="customer_name",
        y_axis="status",
    )
    res_non_numeric = extract_and_transform_chart(dataset, spec_non_numeric)
    # The system safely converts non-numeric strings to 0.0 with warning
    assert res_non_numeric.is_valid is True
    assert any("non-numeric" in w.lower() for w in res_non_numeric.warnings)
    assert res_non_numeric.data_series == [[0.0, 0.0]]


# ===========================================================================
# Test 7: Handling of missing and NULL values in numeric columns
# ===========================================================================

def test_missing_and_null_value_handling() -> None:
    """Verify safe_float cleans formatted strings and handles None/NaN without crashing."""
    assert safe_float(None) == 0.0
    assert safe_float("N/A") == 0.0
    assert safe_float("") == 0.0
    assert safe_float("$1,234.56") == 1234.56
    assert safe_float(" -$45.50 ") == -45.50
    assert safe_float(42) == 42.0

    columns = ["quarter", "revenue"]
    rows = [
        ["Q1", "$1,000.00"],
        ["Q2", None],
        ["Q3", "N/A"],
        ["Q4", "$2,500.50"],
    ]
    dataset = CanonicalSQLDataset(columns, rows)
    spec = ChartSpecification(chart_type="bar", title="Q Revenue", x_axis="quarter", y_axis="revenue")
    res = extract_and_transform_chart(dataset, spec)

    assert res.is_valid is True
    assert res.data_series == [[1000.0, 0.0, 0.0, 2500.5]]


# ===========================================================================
# Test 8: Empty SQL results producing clean "No Data" report without crashing
# ===========================================================================

def test_empty_sql_results_pdf_generation(tmp_path: Path) -> None:
    """Verify empty query dataset produces clean PDF without uncaught exceptions."""
    empty_dataset = CanonicalSQLDataset(columns=["month", "revenue"], rows=[])
    assert empty_dataset.is_empty is True
    assert empty_dataset.compute_deterministic_kpis() == []

    meta = generate_pdf_file(
        title="Empty Sales Report",
        description="No data found for the requested period.",
        kpis=[],
        charts=[],
        columns=["month", "revenue"],
        rows=[],
        output_dir=tmp_path,
    )

    pdf_file = tmp_path / meta.file_name
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0


# ===========================================================================
# Test 9: Multiple chart configurations using the same SQL result
# ===========================================================================

def test_multiple_charts_from_single_canonical_dataset() -> None:
    """Verify multiple charts (bar, pie, line) can be derived from one canonical dataset."""
    columns = ["month", "channel", "revenue"]
    rows = [
        ["2026-01", "Online", 1000.0],
        ["2026-01", "Retail", 500.0],
        ["2026-02", "Online", 1500.0],
        ["2026-02", "Retail", 700.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)

    # Chart 1: Bar chart by month
    spec_bar = ChartSpecification(chart_type="bar", title="Monthly Revenue", x_axis="month", y_axis="revenue")
    res_bar = extract_and_transform_chart(dataset, spec_bar)
    assert res_bar.categories == ["2026-01", "2026-02"]
    assert res_bar.data_series == [[1500.0, 2200.0]]

    # Chart 2: Pie chart by channel
    spec_pie = ChartSpecification(chart_type="pie", title="Channel Share", x_axis="channel", y_axis="revenue")
    res_pie = extract_and_transform_chart(dataset, spec_pie)
    assert set(res_pie.categories) == {"Online", "Retail"}
    assert sum(res_pie.percentages or []) == pytest.approx(100.0, abs=0.1)

    # Chart 3: Line trend
    spec_line = ChartSpecification(chart_type="line", title="Trend", x_axis="month", y_axis="revenue")
    res_line = extract_and_transform_chart(dataset, spec_line)
    assert res_line.is_valid is True


# ===========================================================================
# Test 10: Report validation failures and warnings generation
# ===========================================================================

def test_report_consistency_validator_detects_mismatches() -> None:
    """Verify validator flags inconsistencies between chart totals and table totals."""
    columns = ["region", "revenue"]
    rows = [
        ["North", 1000.0],
        ["South", 2000.0],
    ]
    dataset = CanonicalSQLDataset(columns, rows)

    # Corrupted chart with wrong series values
    corrupted_chart = TransformedChartData(
        title="Corrupted Chart",
        chart_type="bar",
        x_axis="region",
        y_axes=["revenue"],
        categories=["North", "South"],
        data_series=[[5000.0, 5000.0]],  # Sum = 10000 != 3000
        series_names=["revenue"],
    )

    validation = ReportConsistencyValidator.validate_report_components(
        dataset,
        charts=[corrupted_chart],
        kpis=[{"label": "Total Revenue", "value": "$3,000.00"}],
    )

    assert validation["is_consistent"] is False
    assert any("does not match table total" in issue for issue in validation["issues"])


# ===========================================================================
# Test 11: Ollama tool-calling responses with multiple tool calls
# ===========================================================================

def test_extract_all_tool_calls_multiple_formats() -> None:
    """Verify _extract_all_tool_calls extracts multiple calls from JSON, XML, and markdown."""
    # 1. Multiple XML tags in content
    xml_text = (
        "Here are the tools:\n"
        '<tool_call>{"name": "inspect_database_schema", "arguments": {}}</tool_call>\n'
        '<tool_call>{"name": "execute_read_only_query", "arguments": {"query": "SELECT 2"}}</tool_call>'
    )
    xml_calls = OllamaClient._extract_all_tool_calls(xml_text)
    assert len(xml_calls) == 2
    assert xml_calls[0].name == "inspect_database_schema"
    assert xml_calls[1].name == "execute_read_only_query"
    assert xml_calls[1].arguments == {"query": "SELECT 2"}

    # 2. Markdown code block containing tool call list
    md_text = (
        "```json\n"
        '[\n'
        '  {"name": "inspect_database_schema", "arguments": {}},\n'
        '  {"name": "get_table_sample", "arguments": {"table_name": "orders"}}\n'
        ']\n'
        "```"
    )
    md_calls = OllamaClient._extract_all_tool_calls(md_text)
    assert len(md_calls) == 2
    assert md_calls[1].name == "get_table_sample"

    # 3. Single tool call dict extraction
    single_call = OllamaClient._extract_single_tool_call_from_dict({
        "function": {"name": "execute_read_only_query", "arguments": {"query": "SELECT 1"}}
    })
    assert single_call is not None
    assert single_call.name == "execute_read_only_query"
    assert single_call.arguments == {"query": "SELECT 1"}


# ===========================================================================
# Test 12: Tool message correlation with tool_call_id
# ===========================================================================

def test_conversation_message_preserves_tool_call_id() -> None:
    """Verify to_ollama_dict() preserves tool_call_id for role='tool' and 'assistant'."""
    tool_msg = ConversationMessage(
        role="tool",
        content='{"status": "ok"}',
        tool_call_id="call_998877",
    )
    d = tool_msg.to_ollama_dict()
    assert d["role"] == "tool"
    assert d["content"] == '{"status": "ok"}'
    assert d["tool_call_id"] == "call_998877"

    # Assistant message with tool calls
    asst_msg = ConversationMessage(
        role="assistant",
        content="",
        tool_calls=[{"id": "call_998877", "name": "test_tool", "arguments": {}}],
    )
    d_asst = asst_msg.to_ollama_dict()
    assert d_asst["role"] == "assistant"
    assert len(d_asst["tool_calls"]) == 1
    assert d_asst["tool_calls"][0]["id"] == "call_998877"


# ===========================================================================
# Test 13: Non-empty response invariant enforcement in AgentOrchestrator
# ===========================================================================

@pytest.mark.asyncio
async def test_non_empty_response_invariant_with_executed_sql(
    test_app_settings: AppSettings,
) -> None:
    """Verify orchestrator never returns empty final_message when SQL was executed."""
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")

    # Turn 1: execute readonly sql
    # Turn 2: returns empty content, which orchestrator recovers from
    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(
                content="",
                tool_calls=[
                    OllamaToolCall(
                        id="c1",
                        name="execute_readonly_sql",
                        arguments={"query": "SELECT customer_id, first_name FROM customers LIMIT 2"},
                    )
                ],
            ),
            OllamaChatResponse(
                content="",  # Empty final content from model!
                tool_calls=[],
            ),
            OllamaChatResponse(
                content="Successfully retrieved 2 customers from the database.",
                tool_calls=[],
            ),
        ]
    )

    mock_mcp = MagicMock(spec=MCPStdioClient)
    mock_mcp.is_connected = MagicMock(return_value=True)
    mock_mcp.call_tool = AsyncMock(
        return_value={
            "columns": ["customer_id", "first_name"],
            "rows": [[1, "Alice"], [2, "Bob"]],
            "record_count": 2,
            "status": "ok",
        }
    )

    orchestrator = AgentOrchestrator(
        test_app_settings,
        ollama_client=mock_ollama,
        mcp_client=mock_mcp,
    )
    orchestrator._initialized = True

    result = await orchestrator.process_message("List customers")
    assert result.status == "success"
    assert result.final_message is not None
    assert len(result.final_message.strip()) > 0
    assert result.executed_sql is not None


# ===========================================================================
# Test 14: Windows subprocess environment variable preservation in MCP client
# ===========================================================================

def test_windows_subprocess_env_preserves_critical_variables() -> None:
    """Verify MCP client _build_subprocess_env preserves Windows networking and system variables."""
    fake_env = {
        "SYSTEMROOT": r"C:\Windows",
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "COMSPEC": r"C:\Windows\System32\cmd.exe",
        "PATH": r"C:\Windows\System32;C:\Python",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": r"C:\Users\User\AppData\Local\Temp",
        "TMP": r"C:\Users\User\AppData\Local\Temp",
        "LOCALAPPDATA": r"C:\Users\User\AppData\Local",
        "APPDATA": r"C:\Users\User\AppData\Roaming",
    }

    with patch.dict(os.environ, fake_env, clear=True):
        env = _build_subprocess_env()

        # Critical Windows system variables must be present
        assert env.get("SYSTEMROOT") == r"C:\Windows"
        assert env.get("SystemRoot") == r"C:\Windows"
        assert env.get("WINDIR") == r"C:\Windows"
        assert env.get("COMSPEC") == r"C:\Windows\System32\cmd.exe"
        assert env.get("PATHEXT") == ".COM;.EXE;.BAT;.CMD"
        assert env.get("TEMP") == r"C:\Users\User\AppData\Local\Temp"
        assert env.get("LOCALAPPDATA") == r"C:\Users\User\AppData\Local"

        # UTF-8 stdio flags must be active
        assert env.get("PYTHONIOENCODING") == "utf-8"
        assert env.get("PYTHONUTF8") == "1"
