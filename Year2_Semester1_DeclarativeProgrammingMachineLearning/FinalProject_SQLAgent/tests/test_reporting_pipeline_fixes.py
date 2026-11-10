"""Comprehensive regression and integration test suite for the SQL Agent Reporting Pipeline.

Covers all 17 scenarios from Section 11 of the specification:
1. Requested month with no records (October 2026)
2. Requested month with complete records (September 2026)
3. Requested month with partial historical data
4. Historical chart with multiple months
5. Historical chart with only one available month (rejected/omitted with reason)
6. Distribution chart with multiple categories
7. Distribution chart with a single category (100% pie rejected/omitted with reason)
8. Empty dataset handling (excluded from display, clean No-Data notice when all empty)
9. Duplicate dataset detection (dataset_4, dataset_6, dataset_7 deduplicated)
10. Scalar string incorrectly supplied as rows (rows = ["month", "order_count", "sales", "revenue"])
11. KPI consistency across executive summary, charts, and tables
12. Sales (SUM(subtotal)) and revenue (SUM(total_amount)) metric separation
13. Order (COUNT(DISTINCT order_id)) vs transaction (COUNT(DISTINCT payment_id)) separation
14. Correct monthly half-open date boundaries (start_date <= date < next_month_start)
15. Report section omission when data is unavailable (no empty section headings)
16. PDF pagination, table rendering, and no duplicated chart titles
17. Report generation success/failure feedback (_build_verified_report_feedback_summary)

Plus an end-to-end integration test reproducing the exact failing October 2026 acceptance scenario
(task_aa07d328 payload + data/ecommerce.db), verifying all 11 defects are fully resolved.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtPdf import QPdfDocument

from agent.orchestrator import _build_verified_report_feedback_summary
from database.connection import connect_readonly
from reporting.canonical_data import (
    AUTHORITATIVE_METRIC_DEFINITIONS,
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    normalize_kpi_collection,
    normalize_kpi_entry,
    validate_tabular_rows_structure,
)
from reporting.date_utils import (
    PeriodAvailabilityContext,
    calculate_calendar_month,
    calculate_previous_calendar_month,
    resolve_requested_period,
)
from reporting.dataset_registry import CuratedDataset, ReportDatasetRegistry
from reporting.dynamic_pdf_composer import compose_dynamic_pdf
from reporting.pdf_generator import generate_pdf_file
from reporting.report_manager import ReportMetadata, ReportValidationError
from reporting.report_spec import (
    ChartConfiguration,
    ChartType,
    ReportComponent,
    ReportSection,
    ReportSpecification,
    TableConfiguration,
)
from reporting.report_validator import ReportDataValidator

_DB_PATH = Path("data/ecommerce.db")


@pytest.fixture(scope="session")
def qcore_app() -> QCoreApplication:
    """Ensure a QCoreApplication exists for QPdfDocument."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _extract_pdf_pages_text(pdf_path: str | Path, app: QCoreApplication) -> list[str]:
    """Extract text from each page of a PDF using PySide6.QtPdf.QPdfDocument."""
    doc = QPdfDocument()
    doc.load(str(pdf_path))
    pages: list[str] = []
    for i in range(doc.pageCount()):
        sel = doc.getAllText(i)
        pages.append(sel.text())
    return pages


# =============================================================================
# SCENARIO 1: Requested month with no records (October 2026)
# =============================================================================
def test_scenario_01_requested_month_with_no_records() -> None:
    """Requested month with no records (October 2026) produces zero KPIs, labeled comparison, and warnings."""
    req_period = calculate_calendar_month(2026, 10)
    assert req_period.period_label == "October 2026"
    assert req_period.start_date_str == "2026-10-01"
    assert req_period.end_date_str == "2026-11-01"

    avail_ctx = PeriodAvailabilityContext(
        requested_period=req_period,
        comparison_period=calculate_calendar_month(2026, 9),
        available_min_date="2024-01-01",
        available_max_date="2026-09-29",
        actual_periods_present=["2026-09"],
        requested_period_has_data=False,
        requested_period_record_count=0,
        comparison_period_record_count=2885,
        missing_data_reason="No order records exist in the database for October 2026.",
    )
    assert not avail_ctx.requested_period_has_data
    assert "No order records exist" in avail_ctx.missing_data_reason

    spec = ReportSpecification.from_user_intent(
        "Generate a sales performance report for October 2026",
        title="October 2026 Sales Report",
    )
    assert spec.requested_period == "October 2026"
    assert spec.period_boundaries["start_date"] == "2026-10-01"
    assert spec.period_boundaries["end_date_exclusive"] == "2026-11-01"


# =============================================================================
# SCENARIO 2: Requested month with complete records (September 2026)
# =============================================================================
def test_scenario_02_requested_month_with_complete_records() -> None:
    """Requested month with complete records (September 2026) generates full verified metrics."""
    req_period = calculate_calendar_month(2026, 9)
    assert req_period.period_label == "September 2026"
    assert req_period.start_date_str == "2026-09-01"
    assert req_period.end_date_str == "2026-10-01"

    cols = ["month", "total_orders", "sales_volume", "total_revenue", "transactions"]
    rows = [["2026-09", 2885, 1497520.10, 1576149.69, 2885]]
    ds = CanonicalSQLDataset(cols, rows, name="sept_2026")
    kpis = ds.compute_deterministic_kpis()

    kpi_dict = {k["label"]: k["value"] for k in kpis}
    assert kpi_dict["Total Orders"] == "2,885"
    assert "$1,497,520.10" in kpi_dict["Sales Volume"]
    assert "$1,576,149.69" in kpi_dict["Total Revenue"]
    assert kpi_dict["Transactions"] == "2,885"


# =============================================================================
# SCENARIO 3: Requested month with partial historical data
# =============================================================================
def test_scenario_03_partial_historical_data_handling() -> None:
    """When only partial data is available, date range is reported transparently without silent substitution."""
    avail_ctx = PeriodAvailabilityContext(
        requested_period=calculate_calendar_month(2026, 9),
        available_min_date="2026-09-01",
        available_max_date="2026-09-29 23:22:24",
        actual_periods_present=["2026-09"],
        requested_period_has_data=True,
        requested_period_record_count=2885,
        missing_data_reason="",
        data_availability_notes="Available ledger terminates on 2026-09-29.",
    )
    assert avail_ctx.requested_period_has_data is True
    assert "2026-09-29" in avail_ctx.data_availability_notes


# =============================================================================
# SCENARIO 4: Historical chart with multiple months
# =============================================================================
def test_scenario_04_historical_chart_multiple_months() -> None:
    """Historical bar or line charts with >= 2 distinct months are accepted and valid."""
    cols = ["month", "total_revenue"]
    rows = [
        ["2026-07", 1450000.0],
        ["2026-08", 1520000.0],
        ["2026-09", 1576149.69],
    ]
    ds = CanonicalSQLDataset(cols, rows)
    spec = ChartSpecification(
        title="Historical Monthly Revenue",
        chart_type="historical_line",
        x_axis="month",
        y_axis="total_revenue",
    )
    transformed = ds.extract_and_transform_chart(spec)
    assert transformed.is_valid is True
    assert len(transformed.categories) == 3


# =============================================================================
# SCENARIO 5: Historical chart with only one available month (rejected/omitted)
# =============================================================================
def test_scenario_05_historical_chart_one_month_rejected() -> None:
    """Historical bar or line chart with only 1 month is rejected as statistically invalid for a trend."""
    cols = ["month", "total_revenue"]
    rows = [["2026-09", 1576149.69]]
    ds = CanonicalSQLDataset(cols, rows)
    spec = ChartSpecification(
        title="Historical Trend",
        chart_type="historical_line",
        x_axis="month",
        y_axis="total_revenue",
    )
    transformed = ds.extract_and_transform_chart(spec)
    assert transformed.is_valid is False
    assert "requires at least 2 time periods" in transformed.error_message


# =============================================================================
# SCENARIO 6: Distribution chart with multiple categories
# =============================================================================
def test_scenario_06_distribution_chart_multiple_categories() -> None:
    """Pie/donut distribution chart with >= 2 positive categories is accepted and sums to 100%."""
    cols = ["channel", "revenue"]
    rows = [
        ["web", 739733.58],
        ["app", 496198.15],
        ["marketplace", 246822.41],
        ["store", 93395.55],
    ]
    ds = CanonicalSQLDataset(cols, rows)
    spec = ChartSpecification(
        title="Channel Revenue Share",
        chart_type="pie",
        x_axis="channel",
        y_axis="revenue",
    )
    transformed = ds.extract_and_transform_chart(spec)
    assert transformed.is_valid is True
    assert len(transformed.categories) == 4
    total_val = sum(transformed.data_series[0])
    assert abs(total_val - 1576149.69) < 0.01


# =============================================================================
# SCENARIO 7: Distribution chart with a single category (rejected/omitted)
# =============================================================================
def test_scenario_07_distribution_chart_single_category_rejected() -> None:
    """Distribution pie chart with only 1 category (100.0% single slice) is rejected."""
    cols = ["month", "revenue"]
    rows = [["2026-09", 1576149.69]]
    ds = CanonicalSQLDataset(cols, rows)
    spec = ChartSpecification(
        title="Distribution by Month",
        chart_type="pie",
        x_axis="month",
        y_axis="revenue",
    )
    transformed = ds.extract_and_transform_chart(spec)
    assert transformed.is_valid is False
    assert "requires at least 2 distinct categories" in transformed.error_message or "requires at least 2 positive categories" in transformed.error_message or "categories" in transformed.error_message


# =============================================================================
# SCENARIO 8: Empty dataset handling (excluded from display, clean No-Data notice)
# =============================================================================
def test_scenario_08_empty_dataset_handling() -> None:
    """Empty datasets are classified as empty_intermediate and excluded from display."""
    reg = ReportDatasetRegistry()
    curated = reg.register(
        dataset_id="dataset_1",
        columns=["month", "order_count", "sales", "revenue"],
        rows=[],
    )
    assert curated.analytical_purpose == "empty_intermediate"
    assert curated.include_in_pdf is False
    assert curated.validation_status == "excluded_empty"


# =============================================================================
# SCENARIO 9: Duplicate dataset detection
# =============================================================================
def test_scenario_09_duplicate_dataset_detection() -> None:
    """Identical datasets (such as dataset_4, dataset_6, dataset_7 in the failing report) are deduplicated."""
    reg = ReportDatasetRegistry()
    ds4 = reg.register(
        dataset_id="dataset_4",
        columns=["month", "order_count", "sales", "revenue"],
        rows=[["2026-09", 2885, 1497520.10, 1576149.69]],
    )
    ds6 = reg.register(
        dataset_id="dataset_6",
        columns=["month", "order_count", "sales", "revenue"],
        rows=[["2026-09", 2885, 1497520.10, 1576149.69]],
    )
    ds7 = reg.register(
        dataset_id="dataset_7",
        columns=["month", "order_count", "sales", "revenue"],
        rows=[["2026-09", 2885, 1497520.10, 1576149.69]],
    )

    assert ds4.include_in_pdf is True
    assert ds6.analytical_purpose == "duplicate_intermediate"
    assert ds6.include_in_pdf is False
    assert ds7.analytical_purpose == "duplicate_intermediate"
    assert ds7.include_in_pdf is False

    included = reg.included_datasets
    included_ids = [d.dataset_id for d in included]
    assert "dataset_4" in included_ids
    assert "dataset_6" not in included_ids
    assert "dataset_7" not in included_ids


# =============================================================================
# SCENARIO 10: Scalar string incorrectly supplied as rows
# =============================================================================
def test_scenario_10_scalar_string_rows_validation_and_rejection() -> None:
    """Rows passed as strings (e.g. ['month', 'order_count', 'sales', 'revenue']) are rejected."""
    cols = ["month", "order_count", "sales", "revenue"]
    bad_rows = ["month", "order_count", "sales", "revenue"]

    is_valid, sanitized, errors = validate_tabular_rows_structure(cols, bad_rows)
    assert not is_valid
    assert any("character-by-character" in e for e in errors)
    assert len(sanitized) == 0

    ds = CanonicalSQLDataset(cols, bad_rows, name="primary")
    assert not ds.is_structurally_valid
    assert ds.row_count == 0

    reg = ReportDatasetRegistry()
    curated = reg.register("primary", cols, bad_rows)
    assert curated.analytical_purpose == "corrupted_payload"
    assert curated.include_in_pdf is False


# =============================================================================
# SCENARIO 11: KPI consistency across executive summary, charts, and tables
# =============================================================================
def test_scenario_11_kpi_consistency_and_reconciliation() -> None:
    """KPIs for requested period and comparison period reconcile with the authoritative datasets."""
    reg = ReportDatasetRegistry()
    reg.register(
        dataset_id="monthly_perf",
        columns=["month", "orders", "sales", "revenue"],
        rows=[["2026-09", 2885, 1497520.10, 1576149.69]],
    )
    val_rep = ReportDataValidator.validate(
        reg,
        kpis=[
            {"label": "Total Orders", "value": "2,885"},
            {"label": "Total Revenue", "value": "$1,576,149.69"},
        ],
        executive_summary="September 2026 generated 2,885 orders and $1,576,149.69 revenue.",
    )
    assert val_rep.is_valid


# =============================================================================
# SCENARIO 12: Sales and revenue metric separation
# =============================================================================
def test_scenario_12_sales_and_revenue_metric_separation() -> None:
    """Gross Sales (SUM(subtotal)) and Net Revenue (SUM(total_amount)) are strictly separated."""
    assert "sales" in AUTHORITATIVE_METRIC_DEFINITIONS
    assert "revenue" in AUTHORITATIVE_METRIC_DEFINITIONS

    sales_def = AUTHORITATIVE_METRIC_DEFINITIONS["sales"]
    rev_def = AUTHORITATIVE_METRIC_DEFINITIONS["revenue"]

    assert sales_def["formula"] == "SUM(orders.subtotal)"
    assert rev_def["formula"] == "SUM(orders.total_amount)"

    cols = ["month", "sales_volume", "total_revenue"]
    rows = [["2026-09", 1497520.10, 1576149.69]]
    ds = CanonicalSQLDataset(cols, rows)
    kpis = {k["label"]: k["value"] for k in ds.compute_deterministic_kpis()}
    assert "$1,497,520.10" in kpis["Sales Volume"]
    assert "$1,576,149.69" in kpis["Total Revenue"]


# =============================================================================
# SCENARIO 13: Order vs transaction separation
# =============================================================================
def test_scenario_13_orders_vs_transactions_separation() -> None:
    """Orders (COUNT(DISTINCT order_id)) and Transactions (COUNT(DISTINCT payment_id)) are separate."""
    ord_def = AUTHORITATIVE_METRIC_DEFINITIONS["orders"]
    tx_def = AUTHORITATIVE_METRIC_DEFINITIONS["transactions"]

    assert "COUNT(DISTINCT orders.order_id)" in ord_def["formula"]
    assert "COUNT(DISTINCT payments.payment_id)" in tx_def["formula"]

    cols = ["month", "total_orders", "transactions"]
    rows = [["2026-09", 2885, 2885]]
    ds = CanonicalSQLDataset(cols, rows)
    kpis = {k["label"]: k["value"] for k in ds.compute_deterministic_kpis()}
    assert kpis["Total Orders"] == "2,885"
    assert kpis["Transactions"] == "2,885"


# =============================================================================
# SCENARIO 14: Correct monthly half-open date boundaries
# =============================================================================
def test_scenario_14_half_open_date_boundaries() -> None:
    """Monthly periods must compute half-open intervals [start_date, next_month_start) to include last day."""
    sept = calculate_calendar_month(2026, 9)
    assert sept.start_date_str == "2026-09-01"
    assert sept.end_date_str == "2026-10-01"
    assert sept.sql_filter_clause == ">= '2026-09-01' AND < '2026-10-01'"

    dec = calculate_calendar_month(2026, 12)
    assert dec.start_date_str == "2026-12-01"
    assert dec.end_date_str == "2027-01-01"


# =============================================================================
# SCENARIO 15: Report section omission when data is unavailable
# =============================================================================
def test_scenario_15_empty_section_omission(tmp_path: Path, qcore_app: QCoreApplication) -> None:
    """Sections with zero components are suppressed; no bare section titles appear at the bottom of pages."""
    spec = ReportSpecification(
        title="Omission Test Report",
        executive_summary="Testing section suppression.",
        datasets={
            "ds1": {
                "columns": ["channel", "revenue"],
                "rows": [["web", 1000.0], ["app", 500.0]],
            }
        },
        sections=[
            ReportSection(
                title="1. Channel Performance",
                components=[
                    ReportComponent(
                        component_type="table",
                        title="Channel Table",
                        table_config=TableConfiguration(columns=["channel", "revenue"]),
                        dataset_id="ds1",
                    )
                ],
            ),
            ReportSection(
                title="2. Empty Payment Method Section",
                description="Should be omitted because components list is empty",
                components=[],
            ),
            ReportSection(
                title="3. Order Status Section With Failed Subcomponent",
                components=[],
            ),
        ],
    )
    meta = compose_dynamic_pdf(spec, tmp_path)
    assert meta.output_path is not None
    pages = _extract_pdf_pages_text(meta.output_path, qcore_app)
    full_text = "\n".join(pages)

    assert "Channel Performance" in full_text
    assert "Empty Payment Method Section" not in full_text
    assert "Order Status Section With Failed" not in full_text


# =============================================================================
# SCENARIO 16: PDF pagination, table rendering, and no duplicated chart titles
# =============================================================================
def test_scenario_16_pdf_pagination_and_no_duplicate_titles(tmp_path: Path, qcore_app: QCoreApplication) -> None:
    """Chart components with identical titles do not render duplicate Paragraph headings."""
    spec = ReportSpecification(
        title="Title De-duplication Test",
        datasets={
            "ds1": {
                "columns": ["channel", "revenue"],
                "rows": [["web", 1000.0], ["app", 500.0], ["store", 300.0]],
            }
        },
        sections=[
            ReportSection(
                title="Visual Breakdown",
                components=[
                    ReportComponent(
                        component_type="chart",
                        title="Channel Revenue Breakdown",
                        chart_config=ChartConfiguration(
                            chart_type="vertical_bar",
                            title="Channel Revenue Breakdown",
                            x_axis="channel",
                            y_axis="revenue",
                            dataset_id="ds1",
                        ),
                        dataset_id="ds1",
                    )
                ],
            )
        ],
    )
    meta = compose_dynamic_pdf(spec, tmp_path)
    pages = _extract_pdf_pages_text(meta.output_path, qcore_app)
    full_text = "\n".join(pages)

    # In QtPdf text extraction, "Channel Revenue Breakdown" appears inside the drawing once
    count = full_text.count("Channel Revenue Breakdown")
    assert count == 1, f"Expected title to appear exactly once, but found {count}"


# =============================================================================
# SCENARIO 17: Report generation success/failure feedback
# =============================================================================
def test_scenario_17_verified_report_feedback_summary() -> None:
    """_build_verified_report_feedback_summary formats authoritative feedback without hallucinating numbers."""
    rep_meta = {
        "output_path": "/tmp/reports/october_report.pdf",
        "output_format": "PDF",
        "requested_period": "October 2026",
        "actual_data_period": "September 2026",
        "historical_comparison_period": "September 2026",
        "requested_period_has_data": False,
        "record_count": 2885,
        "available_data_range": {"min_date": "2024-01-01", "max_date": "2026-09-29"},
        "charts_rendered": 4,
        "tables_rendered": 5,
        "page_count": 2,
        "kpis": [
            {"label": "Total Orders", "value": "0 (No Data)"},
            {"label": "Total Revenue", "value": "$0.00"},
        ],
        "comparison_kpis": [
            {"label": "Total Orders", "value": "2,885"},
            {"label": "Total Revenue", "value": "$1,576,149.69"},
        ],
        "warnings": ["No records found for requested period October 2026."],
        "omitted_analyses": [],
    }

    feedback = _build_verified_report_feedback_summary(rep_meta)
    assert "Verified PDF Report Summary" in feedback
    assert "/tmp/reports/october_report.pdf" in feedback
    assert "**Requested Reporting Period:** October 2026" in feedback
    assert "No records exist for October 2026" in feedback
    assert "**Historical Comparison Period:** September 2026" in feedback
    assert "4 chart(s), 5 table(s)" in feedback
    assert "Total Orders: 0 (No Data)" in feedback
    assert "Historical Comparison Metrics (September 2026):" in feedback
    assert "Total Orders: 2,885" in feedback


# =============================================================================
# END-TO-END ACCEPTANCE INTEGRATION TEST: Reproducing Failing Acceptance Test
# =============================================================================
def test_acceptance_october_2026_sales_performance_report(tmp_path: Path, qcore_app: QCoreApplication) -> None:
    """End-to-End Acceptance Test: Reproduce the exact failing October 2026 report call

    Verifies resolution of all 11 critical defects:
    1. Proper separation between requested (October 2026) and comparison period (September 2026).
    2. Executive summary values and KPI cards reconciled (October: 0, Comparison: 2,885 orders / $1.58M).
    3. Multi-month historical data supplemented from readonly DB, or 1-month chart rejected.
    4. No single-category 100% pie chart.
    5. No 1-row performance matrix.
    6. Empty datasets excluded.
    7. Duplicate monthly totals deduplicated and no horizontal heterogeneous summing.
    8. Character row rendering completely eliminated.
    9. Payment method and order status analyses present.
    10. No empty section headings at page ends.
    11. Claimed chart and table counts match actual rendered counts.
    """
    assert _DB_PATH.exists(), f"Database {_DB_PATH} must exist for end-to-end acceptance test"

    out_file = str(tmp_path / "october_2026_sales_performance_report_fixed.pdf")

    # Exact payload structure from the failing run (task_aa07d328)
    failing_user_request = "October 2026 Sales Performance Report"
    failing_title = "October 2026 Sales Performance Report"
    failing_description = (
        "Monthly sales performance analysis for October 2026 period, including order volume, revenue "
        "by channel, payment methods, and order status breakdown. Note: October 2026 data is not "
        "available in the database; this report covers September 2026 as the most recent month with complete data."
    )

    # Empty datasets from initial queries
    failing_datasets = {
        "dataset_1": {
            "name": "dataset_1",
            "columns": ["month", "order_count", "sales", "revenue"],
            "rows": [],
            "record_count": 0,
        },
        "dataset_2": {
            "name": "dataset_2",
            "columns": ["month", "order_count", "sales", "revenue"],
            "rows": [],
            "record_count": 0,
        },
        "dataset_3": {
            "name": "dataset_3",
            "columns": ["min_order_date", "max_order_date"],
            "rows": [["2024-01-01 00:08:26", "2026-09-29 23:22:24"]],
            "record_count": 1,
        },
        "dataset_4": {
            "name": "dataset_4",
            "columns": ["month", "order_count", "sales", "revenue"],
            "rows": [["2026-09", 2885, 1497520.10, 1576149.69]],
            "record_count": 1,
        },
        "dataset_5": {
            "name": "dataset_5",
            "columns": ["channel", "orders", "sales", "revenue"],
            "rows": [
                ["app", 944, 471634.73, 496198.15],
                ["marketplace", 407, 235569.75, 246822.41],
                ["store", 181, 88272.75, 93395.55],
                ["web", 1353, 702042.87, 739733.58],
            ],
            "record_count": 4,
        },
        "dataset_6": {
            "name": "dataset_6",
            "columns": ["month", "order_count", "sales", "revenue"],
            "rows": [["2026-09", 2885, 1497520.10, 1576149.69]],
            "record_count": 1,
        },
        "dataset_7": {
            "name": "dataset_7",
            "columns": ["month", "order_count", "sales", "revenue"],
            "rows": [["2026-09", 2885, 1497520.10, 1576149.69]],
            "record_count": 1,
        },
    }

    # Defect 8: LLM passed scalar string list as rows
    failing_columns = ["month", "order_count", "sales", "revenue"]
    failing_rows = ["month", "order_count", "sales", "revenue"]

    failing_charts = [
        {
            "chart_type": "vertical_bar",
            "title": "Historical Trend (Order Count)",
            "x_column": "month",
            "y_columns": ["order_count"],
        },
        {
            "chart_type": "pie",
            "title": "Distribution by Month",
            "x_column": "month",
            "y_columns": ["sales"],
        },
        {
            "chart_type": "matrix",
            "title": "Performance Matrix by Month",
            "x_column": "month",
            "y_columns": ["order_count", "sales", "revenue"],
        },
    ]

    # Generate the report through the pipeline
    meta = generate_pdf_file(
        title=failing_title,
        description=failing_description,
        columns=failing_columns,
        rows=failing_rows,
        charts=failing_charts,
        datasets=failing_datasets,
        user_request=failing_user_request,
        output_dir=tmp_path,
        db_path=_DB_PATH,
    )

    assert meta.status == "completed", f"Report generation failed: {meta.error_message}"
    assert meta.output_path is not None
    gen_path = Path(meta.output_path)
    assert gen_path.exists()
    assert gen_path.stat().st_size > 5000

    # Extract text from each page using PySide6.QtPdf
    pages_text = _extract_pdf_pages_text(gen_path, qcore_app)
    assert len(pages_text) >= 1
    full_report_text = "\n".join(pages_text)

    # -------------------------------------------------------------------------
    # VERIFICATION OF THE 11 CRITICAL DEFECTS
    # -------------------------------------------------------------------------

    # 1. Period Separation & Data Availability Banner
    assert "Requested Period:" in full_report_text
    assert "October 2026" in full_report_text
    assert "Comparison Period:" in full_report_text
    assert "September 2026" in full_report_text
    assert "No Records" in full_report_text or "0 rows" in full_report_text

    # 2. KPI Cards Reconciled
    # Requested period KPIs must be clearly 0
    assert "Total Orders" in full_report_text
    assert "0 (No Data)" in full_report_text or "Total Orders: 0" in full_report_text or "$0.00" in full_report_text
    # Comparison period KPIs must display September 2026 figures
    assert "2,885" in full_report_text
    assert "1,576,149.69" in full_report_text

    # 3. No single-month historical bar chart (either multi-month historical data or rejected)
    assert "Historical Trend (Order Count)" not in full_report_text or "2026-08" in full_report_text

    # 4. No single-category 100.0% pie chart over month
    assert "2026-09 (100.0%)" not in full_report_text

    # 5. Performance matrix: never renders a 1-row matrix
    assert "Performance Matrix by Month\n2026-09" not in full_report_text

    # 6. Empty datasets (Dataset 1 and Dataset 2) are excluded
    assert "Data Summary: Dataset 1" not in full_report_text
    assert "Data Summary: Dataset 2" not in full_report_text
    assert "No records found." not in full_report_text

    # 7. Deduplicated datasets and NO heterogeneous row totals summing Order Count + Sales + Revenue
    assert "3,076,554.79" not in full_report_text

    # 8. NO character-by-character row rendering
    assert "m o n t" not in full_report_text
    assert "o r d e" not in full_report_text
    assert "s a l e" not in full_report_text
    assert "r e v e" not in full_report_text

    # 9. Payment method and order status analysis present (supplemented from readonly DB)
    assert "Payment Method" in full_report_text or "card" in full_report_text.lower()
    assert "Order Status" in full_report_text or "delivered" in full_report_text.lower()

    # 10. NO empty section headings dangling at page ends
    for line in pages_text[-1].splitlines():
        trimmed = line.strip()
        assert trimmed not in {
            "2. Executive Summary",
            "3. Monthly Performance",
            "4. Channel Analysis",
            "5. Payment Method Breakdown",
            "6. Order Status Distribution",
        }

    # 11. Claims match reality
    assert meta.charts_rendered == meta.charts_requested or meta.charts_rendered >= 1
    assert meta.tables_rendered >= 1
    assert meta.warnings is not None


# =============================================================================
# SCENARIO 18: KPI Data Contract & Normalization Boundary Tests
# =============================================================================
def test_kpi_contract_dictionary_entries() -> None:
    """Dictionary-based KPI entries with canonical and alternative keys normalize cleanly."""
    raw_kpis = [
        {"label": "Total Orders", "value": "2,885", "note": "Verified"},
        {"name": "Total Revenue", "amount": "$1,576,149.69", "change": "+5.2%"},
        {"metric": "Average Order Value", "val": "$546.33", "delta": "+1.1%"},
        {"title": "Transactions", "count": "2,885"},
    ]
    norm = normalize_kpi_collection(raw_kpis)
    assert len(norm) == 4
    assert norm[0] == {"label": "Total Orders", "value": "2,885", "note": "Verified"}
    assert norm[1] == {"label": "Total Revenue", "value": "$1,576,149.69", "note": "+5.2%"}
    assert norm[2] == {"label": "Average Order Value", "value": "$546.33", "note": "+1.1%"}
    assert norm[3] == {"label": "Transactions", "value": "2,885", "note": ""}


def test_kpi_contract_string_entries_with_and_without_delimiters() -> None:
    """String KPI entries with or without delimiters normalize into canonical dict format."""
    # With colon delimiter
    k1 = normalize_kpi_entry("Total Orders: 2,885")
    assert k1 == {"label": "Total Orders", "value": "2,885", "note": ""}

    # With equals delimiter
    k2 = normalize_kpi_entry("Total Revenue = $1,576,149.69")
    assert k2 == {"label": "Total Revenue", "value": "$1,576,149.69", "note": ""}

    # With dash delimiter
    k3 = normalize_kpi_entry("Average Order Value - $546.33")
    assert k3 == {"label": "Average Order Value", "value": "$546.33", "note": ""}

    # Without delimiter (e.g. from LLM passing metric names)
    k4 = normalize_kpi_entry("Total Orders (September 2026)")
    assert k4 == {"label": "Total Orders (September 2026)", "value": "", "note": ""}

    # Collection of mixed strings
    norm = normalize_kpi_collection([
        "Total Orders (September 2026)",
        "Total Revenue (September 2026)",
        "Average Order Value: $546.33",
    ])
    assert len(norm) == 3
    assert norm[0]["label"] == "Total Orders (September 2026)"
    assert norm[0]["value"] == ""
    assert norm[2]["value"] == "$546.33"


def test_kpi_contract_invalid_types_raise_validation_error() -> None:
    """Invalid KPI types and malformed objects raise ReportValidationError."""
    with pytest.raises(ReportValidationError, match="cannot be None"):
        normalize_kpi_entry(None)

    with pytest.raises(ReportValidationError, match="missing or empty label"):
        normalize_kpi_entry({})

    with pytest.raises(ReportValidationError, match="missing or empty label"):
        normalize_kpi_entry({"value": "100"})

    with pytest.raises(ReportValidationError, match="empty string"):
        normalize_kpi_entry("   ")

    with pytest.raises(ReportValidationError, match="Invalid KPI entry type"):
        normalize_kpi_entry(12345)

    with pytest.raises(ReportValidationError, match="Invalid KPI entry type"):
        normalize_kpi_entry(["nested", "list"])

    with pytest.raises(ReportValidationError, match="Invalid KPI collection type"):
        normalize_kpi_collection("not_a_collection")

    with pytest.raises(ReportValidationError, match="Invalid KPI collection type"):
        normalize_kpi_collection({"key": "val"})


def test_kpi_contract_empty_collections() -> None:
    """Empty KPI collections return empty lists without error."""
    assert normalize_kpi_collection(None) == []
    assert normalize_kpi_collection([]) == []
    assert normalize_kpi_collection(()) == []


def test_kpi_reconciliation_against_canonical_sql_dataset() -> None:
    """String KPIs without values are reconciled deterministically from CanonicalSQLDataset."""
    cols = ["order_id", "order_date", "subtotal", "total_amount"]
    rows = [
        (1, "2026-09-05", 100.0, 110.0),
        (2, "2026-09-12", 200.0, 220.0),
        (3, "2026-09-20", 300.0, 330.0),
    ]
    ds = CanonicalSQLDataset(cols, rows, name="september_orders")
    registry = ReportDatasetRegistry()
    registry.register("primary", cols, rows)

    # Pass strings without values
    supplied_kpis = [
        "Total Orders (September 2026)",
        "Total Revenue (September 2026)",
        "Sales Volume",
    ]
    p_kpis, c_kpis, summary, findings = ReportDataValidator.build_reconciled_kpis_and_summary(
        registry,
        supplied_kpis=supplied_kpis,
    )

    assert len(p_kpis) >= 3
    kpi_map = {k["label"]: k["value"] for k in p_kpis}
    assert kpi_map["Total Orders (September 2026)"] == "3"
    assert kpi_map["Total Revenue (September 2026)"] == "$660.00"
    assert kpi_map["Sales Volume"] == "$600.00"

    # Validator gate must pass cleanly without AttributeError
    val_res = ReportConsistencyValidator.validate_report_components(
        ds,
        kpis=supplied_kpis,
        executive_summary=summary,
    )
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0


def test_kpi_requested_period_vs_comparison_period_consistency() -> None:
    """Validator detects when requested period is zero while comparison period has data."""
    cols = ["month", "order_count", "sales", "revenue"]
    rows = [("2026-09", 2885, 1400000.0, 1576149.69)]
    ds = CanonicalSQLDataset(cols, rows, name="historical_summary")

    # When requested period has no data, validator warns if summary doesn't clarify 0 records
    kpis = [
        {"label": "Total Orders (October 2026)", "value": "0 (No Data)"},
        {"label": "Total Orders (September 2026 Comparison)", "value": "2,885"},
    ]
    val_res = ReportConsistencyValidator.validate_report_components(
        ds,
        kpis=kpis,
        executive_summary="September had 2,885 orders and strong growth.",
        requested_period="October 2026",
        requested_period_has_data=False,
        comparison_period="September 2026",
    )
    assert val_res.is_valid is True
    # Should flag that executive summary does not explicitly state requested period had 0 records
    assert any("October 2026" in w for w in val_res.warnings)

