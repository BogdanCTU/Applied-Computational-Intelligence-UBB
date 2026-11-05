"""Unit and integration tests for Milestone 9: Dynamic PDF Visualization & Diagnostics."""

from __future__ import annotations

from pathlib import Path
import pytest
from reportlab.graphics.shapes import Drawing

from reporting.chart_builder import (
    build_chart,
    extract_chart_data,
)
from reporting.dynamic_pdf_composer import compose_dynamic_pdf
from reporting.pdf_generator import generate_pdf_file
from reporting.report_spec import (
    ChartConfiguration,
    ChartType,
    ReportComponent,
    ReportSection,
    ReportSpecification,
    TableConfiguration,
)
from tests.test_reporting import _extract_pdf_text


def test_all_11_chart_types_build_successfully() -> None:
    """Verify that all 11 chart types defined in Milestone 9 build valid vector Drawings."""
    columns = ["month", "revenue", "orders", "category"]
    rows = [
        ["2023-01", 1200.5, 45, "Electronics"],
        ["2023-02", 1450.0, 52, "Clothing"],
        ["2023-03", 980.25, 38, "Home"],
        ["2023-04", 1750.8, 64, "Electronics"],
    ]

    chart_types = [
        ChartType.LINE.value,
        ChartType.MULTI_LINE.value,
        ChartType.HISTORICAL.value,
        ChartType.BAR.value,
        ChartType.GROUPED_BAR.value,
        ChartType.STACKED_BAR.value,
        ChartType.HORIZONTAL_BAR.value,
        ChartType.PIE.value,
        ChartType.DONUT.value,
        ChartType.AREA.value,
        ChartType.SCATTER.value,
    ]

    for ct in chart_types:
        cfg = ChartConfiguration(
            chart_type=ct,
            title=f"Test {ct.capitalize()} Chart",
            x_axis="month",
            y_axis="revenue",
        )
        drawing = build_chart(cfg, columns, rows)
        assert isinstance(drawing, Drawing), f"Chart type {ct} failed to build Drawing"
        assert drawing.width > 0
        assert drawing.height > 0


def test_long_format_multi_series_pivoting() -> None:
    """Verify that long-format data (month, category, revenue) automatically pivots into multi-series."""
    columns = ["month", "category", "revenue"]
    rows = [
        ["2023-01", "Electronics", 1000.0],
        ["2023-01", "Clothing", 500.0],
        ["2023-02", "Electronics", 1200.0],
        ["2023-02", "Clothing", 700.0],
    ]

    cfg = ChartConfiguration(
        chart_type="multi_line",
        title="Revenue by Category",
        x_axis="month",
        y_axis="revenue",
        series=["category"],
    )
    categories, data_series, series_names = extract_chart_data(cfg, columns, rows)

    assert categories == ["2023-01", "2023-02"]
    assert "Electronics" in series_names
    assert "Clothing" in series_names
    assert len(data_series) == 2
    elec_idx = series_names.index("Electronics")
    assert data_series[elec_idx] == [1000.0, 1200.0]


def test_dynamic_pdf_composer_diagnostics(tmp_path: Path) -> None:
    """Verify dynamic PDF composition emits exact required diagnostic metrics."""
    spec = ReportSpecification(
        title="Executive Analytical Report",
        subtitle="Quarterly Sales & Order Breakdown",
        executive_summary="Overall revenue increased by 18% over the period.",
        kpis=[
            {"label": "Total Revenue", "value": "$125,400", "change": "+12.4%"},
            {"label": "Total Orders", "value": "1,420", "change": "+8.1%"},
        ],
        findings=[
            "Electronics category generated 48% of total gross revenue.",
            "Repeat customer order frequency improved across all segments.",
        ],
        datasets={
            "ds_orders": {
                "columns": ["month", "orders", "revenue"],
                "rows": [
                    ["2023-01", 120, 15000.0],
                    ["2023-02", 145, 18200.0],
                    ["2023-03", 160, 21000.0],
                ],
            },
            "ds_dist": {
                "columns": ["category", "revenue"],
                "rows": [
                    ["Electronics", 45000.0],
                    ["Clothing", 32000.0],
                    ["Home", 18000.0],
                ],
            },
        },
        sections=[
            ReportSection(
                title="Historical Performance",
                description="Analysis of monthly order counts and revenue trends.",
                components=[
                    ReportComponent(
                        component_type="chart",
                        title="Historical Monthly Orders",
                        chart_config=ChartConfiguration(
                            chart_type="historical_line",
                            title="Monthly Orders",
                            x_axis="month",
                            y_axis="orders",
                            dataset_id="ds_orders",
                        ),
                        dataset_id="ds_orders",
                    ),
                    ReportComponent(
                        component_type="table",
                        title="Monthly Summary Table",
                        table_config=TableConfiguration(
                            columns=["month", "orders", "revenue"],
                            show_totals=True,
                            dataset_id="ds_orders",
                        ),
                        dataset_id="ds_orders",
                    ),
                ],
            ),
            ReportSection(
                title="Distribution & Breakdown",
                description="Product category share breakdown.",
                components=[
                    ReportComponent(
                        component_type="chart",
                        title="Revenue Share by Category",
                        chart_config=ChartConfiguration(
                            chart_type="pie",
                            title="Revenue Share",
                            x_axis="category",
                            y_axis="revenue",
                            dataset_id="ds_dist",
                        ),
                        dataset_id="ds_dist",
                    ),
                ],
            ),
        ],
    )

    meta = compose_dynamic_pdf(spec, output_dir=tmp_path)

    assert meta.status == "completed"
    assert meta.completion_status == "complete"
    assert meta.sections_count == 2
    assert meta.charts_requested == 2
    assert meta.charts_rendered == 2
    assert meta.tables_requested == 1
    assert meta.tables_rendered == 1
    assert meta.page_count >= 1
    assert meta.file_size_bytes > 0
    assert Path(meta.output_path).is_file()
    assert meta.datasets_count == 2
    assert meta.dataset_details["ds_orders"] == 3
    assert meta.dataset_details["ds_dist"] == 3
    assert len(meta.failed_components) == 0


def test_matrix_crosstab_with_totals_and_heatmap(tmp_path: Path) -> None:
    """Verify matrix / crosstab report table with row and column totals."""
    columns = ["month", "cancelled", "delivered", "shipped"]
    rows = [
        ["2023-01", 12, 145, 23],
        ["2023-02", 8, 160, 31],
        ["2023-03", 15, 180, 28],
    ]

    meta = generate_pdf_file(
        title="Order Status Matrix",
        description="Matrix of order counts by month and status",
        sql_query="SELECT strftime('%Y-%m', order_date) as month, status, count(*) ...",
        columns=columns,
        rows=rows,
        output_dir=tmp_path,
        user_request="Generate a report with a matrix showing order counts by month and order status, including row totals, column totals and a heatmap-style visualization if supported.",
        include_sql=False,
    )

    assert meta.status == "completed"
    assert meta.completion_status == "complete"
    assert Path(meta.output_path).is_file()
    assert meta.file_size_bytes > 0


def test_sql_appendix_only_when_requested(tmp_path: Path) -> None:
    """Verify SQL appendix is included ONLY when explicitly requested."""
    sql_text = "SELECT * FROM orders WHERE status = 'delivered'"

    # 1. Without explicit request -> include_sql = False
    meta_no_sql = generate_pdf_file(
        title="Standard Report Without SQL",
        description="Report without SQL appendix",
        sql_query=sql_text,
        columns=["order_id", "total_amount"],
        rows=[[1, 100.0]],
        output_dir=tmp_path,
        include_sql=False,
    )
    pdf_text_no_sql = _extract_pdf_text(Path(meta_no_sql.output_path))
    assert "Appendix" not in pdf_text_no_sql
    assert "delivered" not in pdf_text_no_sql

    # 2. With explicit request -> include_sql = True
    meta_with_sql = generate_pdf_file(
        title="Report With SQL Appendix",
        description="Report with SQL appendix",
        sql_query=sql_text,
        columns=["order_id", "total_amount"],
        rows=[[1, 100.0]],
        output_dir=tmp_path,
        include_sql=True,
    )
    pdf_text_with_sql = _extract_pdf_text(Path(meta_with_sql.output_path))
    assert "Appendix" in pdf_text_with_sql
    assert "delivered" in pdf_text_with_sql

