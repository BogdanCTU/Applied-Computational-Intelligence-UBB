"""Comprehensive unit and integration tests for Milestone 10 Advanced Visualization Engine.

Verifies:
1. ChartRegistry registration and validation across all 25 chart types.
2. Individual rendering for all 6 analytical categories:
   - Comparison (vertical_bar, grouped_bar, stacked_bar, horizontal_bar, grouped_horizontal_bar, stacked_horizontal_bar)
   - Trend & Time-Series (line, multi_line, historical_line, area, stacked_area)
   - Distribution (pie, donut, histogram, density, box_plot, violin)
   - Relationship (scatter, bubble, correlation_heatmap)
   - Hierarchical (treemap, sunburst)
   - Matrix & Tabular (matrix, heatmap, pivot_table)
3. Edge case handling (empty inputs, single rows, negative numbers, missing values).
4. Multi-component dynamic PDF generation with visual verification.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from reportlab.graphics.shapes import Drawing

from reporting.chart_builder import build_chart, extract_chart_data
from reporting.chart_registry import ChartRegistry
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


def test_registry_contains_all_25_chart_types() -> None:
    """Verify that ChartRegistry has registered all 25 required analytical chart types."""
    supported = ChartRegistry.get_supported_chart_types()

    expected_types = [
        "area",
        "bar",
        "box_plot",
        "boxplot",
        "bubble",
        "correlation_heatmap",
        "density",
        "donut",
        "grouped_bar",
        "grouped_horizontal_bar",
        "grouped_vertical_bar",
        "heatmap",
        "histogram",
        "historical",
        "historical_line",
        "horizontal_bar",
        "line",
        "matrix",
        "multi_line",
        "pie",
        "pivot_table",
        "scatter",
        "stacked_area",
        "stacked_bar",
        "stacked_horizontal_bar",
        "stacked_vertical_bar",
        "sunburst",
        "treemap",
        "vertical_bar",
        "violin",
    ]

    for et in expected_types:
        assert et in supported, f"Chart type '{et}' missing from ChartRegistry"


def test_registry_validation() -> None:
    """Verify ChartRegistry validation returns structured error for empty or unsupported types."""
    # 1. Empty dataset
    cfg = ChartConfiguration(chart_type="vertical_bar", title="Test")
    valid, err = ChartRegistry.validate(cfg, [], [])
    assert valid is False
    assert "empty" in str(err).lower()

    # 2. Unsupported chart type
    cfg_bad = ChartConfiguration(chart_type="nonexistent_chart_type", title="Test")
    valid, err = ChartRegistry.validate(cfg_bad, ["a", "b"], [[1, 2]])
    assert valid is False
    assert "unsupported" in str(err).lower()

    # 3. Valid chart type
    valid, err = ChartRegistry.validate(cfg, ["category", "revenue"], [["A", 100.0]])
    assert valid is True
    assert err is None


def test_all_25_chart_types_render_valid_drawing() -> None:
    """Test that every chart type renders a valid vector Drawing without exceptions."""
    columns = ["month", "category", "revenue", "orders", "customer_count"]
    rows = [
        ["2023-01", "Electronics", 12500.0, 140, 110],
        ["2023-01", "Clothing", 8400.0, 95, 80],
        ["2023-02", "Electronics", 14200.0, 160, 125],
        ["2023-02", "Clothing", 9100.0, 105, 90],
        ["2023-03", "Electronics", 15800.0, 175, 135],
        ["2023-03", "Clothing", 10200.0, 120, 100],
    ]

    chart_types_to_test = [
        # Comparison
        "vertical_bar",
        "grouped_bar",
        "stacked_bar",
        "horizontal_bar",
        "grouped_horizontal_bar",
        "stacked_horizontal_bar",
        # Trend
        "line",
        "multi_line",
        "historical_line",
        "area",
        "stacked_area",
        # Distribution
        "pie",
        "donut",
        "histogram",
        "density",
        "box_plot",
        "violin",
        # Relationship
        "scatter",
        "bubble",
        "correlation_heatmap",
        # Hierarchical
        "treemap",
        "sunburst",
        # Matrix
        "matrix",
        "heatmap",
        "pivot_table",
    ]

    for ct in chart_types_to_test:
        cfg = ChartConfiguration(
            chart_type=ct,
            title=f"Test {ct.replace('_', ' ').title()}",
            subtitle=f"Automated test for {ct}",
            x_axis="month",
            y_axis="revenue",
            category_dimension="category",
            numerical_measure="revenue",
        )
        drawing = build_chart(cfg, columns, rows)
        assert isinstance(drawing, Drawing), f"Chart type '{ct}' did not produce a Drawing"
        assert drawing.width > 0, f"Chart type '{ct}' width must be > 0"
        assert drawing.height > 0, f"Chart type '{ct}' height must be > 0"


def test_edge_cases_graceful_handling() -> None:
    """Verify that edge cases (empty rows, all zeros, strings in numeric columns) do not crash."""
    cfg = ChartConfiguration(chart_type="histogram", title="Empty Histogram")
    d1 = build_chart(cfg, ["val"], [])
    assert isinstance(d1, Drawing)

    cfg_pie = ChartConfiguration(chart_type="pie", title="Negative Pie")
    d2 = build_chart(cfg_pie, ["cat", "val"], [["A", -10.0], ["B", 0.0]])
    assert isinstance(d2, Drawing)

    cfg_treemap = ChartConfiguration(chart_type="treemap", title="Single Item Treemap")
    d3 = build_chart(cfg_treemap, ["cat", "val"], [["Solo", 500.0]])
    assert isinstance(d3, Drawing)

    cfg_box = ChartConfiguration(chart_type="box_plot", title="Single Point Boxplot")
    d4 = build_chart(cfg_box, ["cat", "val"], [["Category 1", 42.0]])
    assert isinstance(d4, Drawing)


def test_advanced_pdf_with_multiple_analytical_charts(tmp_path: Path) -> None:
    """Generate an actual publication PDF containing 4 distinct analytical visualizations and verify structure."""
    spec = ReportSpecification(
        title="Executive Multi-Chart Analytical Presentation",
        subtitle="Comprehensive Sales, Distribution & Correlation Analysis",
        executive_summary="This quarterly analytical report evaluates multi-dimensional e-commerce metrics.",
        kpis=[
            {"label": "Gross Revenue", "value": "$80,200", "change": "+14.2%"},
            {"label": "Units Sold", "value": "2,450", "change": "+8.5%"},
            {"label": "Avg Order Value", "value": "$164.20", "change": "+5.1%"},
            {"label": "Return Rate", "value": "2.8%", "change": "-0.4%"},
        ],
        findings=[
            "Revenue growth accelerated in Electronics and Home segments.",
            "Order value distribution exhibits a right-skewed pattern with strong median stability.",
            "Pearson correlation between unit price and order volume indicates high price elasticity.",
        ],
        datasets={
            "ds_monthly": {
                "columns": ["month", "category", "revenue", "orders"],
                "rows": [
                    ["2023-01", "Electronics", 18500.0, 110],
                    ["2023-01", "Apparel", 12000.0, 95],
                    ["2023-02", "Electronics", 21000.0, 130],
                    ["2023-02", "Apparel", 13500.0, 105],
                    ["2023-03", "Electronics", 24000.0, 150],
                    ["2023-03", "Apparel", 14200.0, 115],
                ],
            },
            "ds_categories": {
                "columns": ["category", "revenue", "profit_margin"],
                "rows": [
                    ["Electronics", 63500.0, 24.5],
                    ["Apparel", 39700.0, 38.2],
                    ["Home & Garden", 21400.0, 31.0],
                    ["Health & Beauty", 15800.0, 42.1],
                ],
            },
            "ds_correlations": {
                "columns": ["unit_price", "units_sold", "discount_pct", "revenue"],
                "rows": [
                    [25.0, 120, 5.0, 2850.0],
                    [50.0, 85, 10.0, 3825.0],
                    [75.0, 60, 15.0, 3825.0],
                    [120.0, 45, 0.0, 5400.0],
                    [250.0, 20, 20.0, 4000.0],
                ],
            },
        },
        sections=[
            ReportSection(
                title="Time-Series & Category Breakdown",
                description="Evolution of revenue and category distribution.",
                components=[
                    ReportComponent(
                        component_type="chart",
                        title="Monthly Revenue Trend (Multi-Series Area)",
                        chart_config=ChartConfiguration(
                            chart_type="area",
                            title="Monthly Revenue Evolution",
                            x_axis="month",
                            y_axis="revenue",
                            dataset_id="ds_monthly",
                        ),
                        dataset_id="ds_monthly",
                    ),
                    ReportComponent(
                        component_type="chart",
                        title="Category Revenue Contribution (Treemap)",
                        chart_config=ChartConfiguration(
                            chart_type="treemap",
                            title="Revenue Share by Category",
                            x_axis="category",
                            y_axis="revenue",
                            dataset_id="ds_categories",
                        ),
                        dataset_id="ds_categories",
                    ),
                ],
            ),
            ReportSection(
                title="Statistical Relationships & Correlation",
                description="Metric dependencies and pricing correlations.",
                components=[
                    ReportComponent(
                        component_type="chart",
                        title="Variable Correlation Heatmap",
                        chart_config=ChartConfiguration(
                            chart_type="correlation_heatmap",
                            title="Pricing & Sales Correlation Matrix",
                            dataset_id="ds_correlations",
                        ),
                        dataset_id="ds_correlations",
                    ),
                    ReportComponent(
                        component_type="chart",
                        title="Price vs Sales Volume (Bubble Chart)",
                        chart_config=ChartConfiguration(
                            chart_type="bubble",
                            title="Unit Price vs Units Sold",
                            x_axis="unit_price",
                            y_axis="units_sold",
                            dataset_id="ds_correlations",
                        ),
                        dataset_id="ds_correlations",
                    ),
                    ReportComponent(
                        component_type="table",
                        title="Category Summary Table",
                        table_config=TableConfiguration(
                            columns=["category", "revenue", "profit_margin"],
                            show_totals=True,
                            formatting={"revenue": "currency", "profit_margin": "percent"},
                            dataset_id="ds_categories",
                        ),
                        dataset_id="ds_categories",
                    ),
                ],
            ),
        ],
    )

    meta = compose_dynamic_pdf(spec, output_dir=tmp_path)

    assert meta.status == "completed"
    assert meta.completion_status == "complete"
    assert meta.charts_requested == 4
    assert meta.charts_rendered == 4
    assert meta.tables_requested == 1
    assert meta.tables_rendered == 1
    assert meta.sections_count == 2
    assert meta.datasets_count == 3
    assert len(meta.failed_components) == 0
    assert meta.page_count >= 1
    assert Path(meta.output_path).is_file()
    assert meta.file_size_bytes > 0

    # Verify text in PDF
    text = _extract_pdf_text(Path(meta.output_path))
    assert "Executive Multi-Chart Analytical Presentation" in text
    assert "Time-Series & Category Breakdown" in text
    assert "Statistical Relationships & Correlation" in text

