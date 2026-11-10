"""Regression tests for dynamic database discovery, reporting periods, and multi-component synthesis."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from agent.orchestrator import _synthesize_charts_from_intent, _synthesize_kpis
from config.settings import AppSettings
from mcp_layer.tools.database_tools import inspect_database_schema_impl, get_table_sample_impl
from reporting.date_utils import ReportingPeriod, calculate_previous_calendar_month
from reporting.pdf_generator import generate_pdf_file


def test_previous_calendar_month_calculation_standard() -> None:
    """Verify normal month calculation (e.g., November 2026 -> October 2026)."""
    ref_date = datetime(2026, 11, 5, 14, 30, 0)
    period = calculate_previous_calendar_month(ref_date)

    assert period.year == 2026
    assert period.month == 10
    assert period.period_label == "October 2026"
    assert period.start_date_str == "2026-10-01"
    assert period.end_date_str == "2026-11-01"
    assert period.start_date_inclusive == "2026-10-01"
    assert period.end_date_exclusive == "2026-11-01"
    assert ">= '2026-10-01'" in period.sql_filter_clause
    assert "< '2026-11-01'" in period.sql_filter_clause


def test_previous_calendar_month_calculation_year_rollover() -> None:
    """Verify January rollover to previous year's December."""
    ref_date = datetime(2027, 1, 15, 9, 0, 0)
    period = calculate_previous_calendar_month(ref_date)

    assert period.year == 2026
    assert period.month == 12
    assert period.period_label == "December 2026"
    assert period.start_date_str == "2026-12-01"
    assert period.end_date_str == "2027-01-01"


def test_previous_calendar_month_calculation_leap_year() -> None:
    """Verify March in a leap year -> February 1 to March 1."""
    ref_date = datetime(2028, 3, 10)
    period = calculate_previous_calendar_month(ref_date)

    assert period.year == 2028
    assert period.month == 2
    assert period.period_label == "February 2028"
    assert period.start_date_str == "2028-02-01"
    assert period.end_date_str == "2028-03-01"


def test_schema_inspection_date_columns_and_business_entities() -> None:
    """Verify inspect_database_schema_impl extracts date candidates with min/max and business entities."""
    settings = AppSettings()
    res = inspect_database_schema_impl(settings)

    assert res["status"] in {"ok", "success"}
    assert "business_entities" in res
    assert "date_columns" in res

    # Verify orders table has date discovery
    date_cols = res["date_columns"]
    assert any(dc["table"] == "orders" and "order_date" in dc["column"] for dc in date_cols)

    # Check that min_value and max_value are populated from the real database
    order_date_entry = next(dc for dc in date_cols if dc["table"] == "orders" and dc["column"] == "order_date")
    assert order_date_entry["min_value"] is not None
    assert order_date_entry["max_value"] is not None
    assert "2026" in str(order_date_entry["max_value"])

    # Check business entities
    entities = res["business_entities"]
    assert "orders" in entities
    assert "payments" in entities


def test_table_sampling() -> None:
    """Verify get_table_sample_impl returns real sample rows and column types."""
    settings = AppSettings()
    res = get_table_sample_impl(settings, table_name="orders", num_records=3)

    assert res["status"] in {"ok", "success"}
    assert res["table_name"] == "orders"
    assert len(res["records"]) == 3
    col_names = [c["name"] for c in res["columns"]]
    assert "order_id" in col_names
    assert "total_amount" in col_names


def test_kpi_synthesis_no_double_counting() -> None:
    """Verify _synthesize_kpis accurately parses orders, sales, revenue, transactions."""
    columns = ["month", "total_orders", "gross_sales", "net_revenue", "total_transactions"]
    rows = [
        ["2026-08", 100, 15000.0, 14200.0, 100],
        ["2026-09", 150, 22500.0, 21300.0, 150],
    ]
    kpis = _synthesize_kpis(columns, rows)
    labels = {k["label"]: k["value"] for k in kpis}

    assert "Total Orders" in labels
    assert labels["Total Orders"] == "250"
    assert "Sales Volume" in labels
    assert "$37,500.00" in labels["Sales Volume"]
    assert "Total Revenue" in labels
    assert "$35,500.00" in labels["Total Revenue"]
    assert "Transactions" in labels
    assert labels["Transactions"] == "250"


def test_chart_synthesis_historical_bar_pie_and_matrix() -> None:
    """Verify prompt asking for bar, pie, and matrix generates all three distinct chart types."""
    prompt = (
        "I want an output report in PDF file, exporting last month orders, sales, revenue, transactions. "
        "I want graphical historical bar charts, some distribution pies and matrix graphs. "
        "Provide also at the end of the report data in table format."
    )
    columns = ["month", "status", "total_orders", "sales_volume", "total_revenue", "transactions"]
    rows = [
        ["2026-07", "delivered", 120, 18000.0, 17100.0, 120],
        ["2026-08", "shipped", 140, 21000.0, 19950.0, 140],
        ["2026-09", "processing", 160, 24000.0, 22800.0, 160],
    ]
    charts = _synthesize_charts_from_intent(prompt, columns, rows)
    chart_types = [c["chart_type"] for c in charts]

    assert "vertical_bar" in chart_types
    assert "pie" in chart_types
    assert "matrix" in chart_types


def test_pdf_generation_multi_chart_and_table_paginated(tmp_path: Path) -> None:
    """Verify generate_pdf_file produces a valid multi-page PDF with bar, pie, matrix, and tables."""
    out_file = str(tmp_path / "test_full_report.pdf")
    columns = ["month", "status", "total_orders", "sales_volume", "total_revenue", "transactions"]
    rows = [
        ["2026-07", "delivered", 120, 18000.0, 17100.0, 120],
        ["2026-08", "shipped", 140, 21000.0, 19950.0, 140],
        ["2026-09", "processing", 160, 24000.0, 22800.0, 160],
    ]
    charts = [
        {
            "chart_type": "vertical_bar",
            "title": "Historical Order Volume",
            "x_column": "month",
            "y_columns": ["total_orders"],
        },
        {
            "chart_type": "pie",
            "title": "Status Distribution",
            "x_column": "status",
            "y_columns": ["total_orders"],
        },
        {
            "chart_type": "matrix",
            "title": "Channel & Status Matrix",
            "x_column": "status",
            "y_columns": ["total_orders", "sales_volume", "total_revenue", "transactions"],
        },
    ]
    kpis = [
        {"label": "Total Orders", "value": "420", "note": "Verified orders"},
        {"label": "Total Revenue", "value": "$59,850.00", "note": "Net revenue"},
    ]

    res = generate_pdf_file(
        title="Comprehensive Performance Report",
        description="Full multi-metric analysis with historical bar, pie, and matrix charts.",
        columns=columns,
        rows=rows,
        charts=charts,
        kpis=kpis,
        findings=["All metrics verified against SQLite ledger.", "Period: Q3 2026."],
        output_dir=str(tmp_path),
    )

    assert Path(res.output_path).exists()
    assert res.file_size_bytes > 10000
    assert res.page_count >= 2
    assert res.charts_rendered == 3
    assert res.tables_rendered >= 1
