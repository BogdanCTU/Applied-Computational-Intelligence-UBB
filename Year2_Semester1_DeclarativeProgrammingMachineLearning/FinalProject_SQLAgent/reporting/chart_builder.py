"""ReportLab vector chart generator supporting 11 dynamic chart types."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Group, Line, Rect, String
from reportlab.lib import colors

from .report_spec import ChartConfiguration, ChartType

log = logging.getLogger(__name__)

# Professional corporate palette
PALETTE = [
    colors.HexColor("#2563EB"),  # Royal Blue
    colors.HexColor("#10B981"),  # Emerald Green
    colors.HexColor("#F59E0B"),  # Amber
    colors.HexColor("#8B5CF6"),  # Violet
    colors.HexColor("#EF4444"),  # Crimson Red
    colors.HexColor("#06B6D4"),  # Cyan
    colors.HexColor("#EC4899"),  # Pink
    colors.HexColor("#84CC16"),  # Lime
    colors.HexColor("#64748B"),  # Slate
]


def _format_val(val: Any, fmt: str) -> str:
    if val is None:
        return "—"
    try:
        num = float(val)
        if fmt == "currency":
            return f"${num:,.2f}" if abs(num) >= 1 else f"${num:.2f}"
        if fmt == "percentage" or fmt == "percent":
            return f"{num:.1f}%"
        if fmt == "integer" or num.is_integer():
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _empty_chart_drawing(width: float, height: float, title: str, msg: str) -> Drawing:
    d = Drawing(width, height)
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=4, ry=4))
    if title:
        d.add(String(16, height - 20, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#1E293B")))
    d.add(String(width / 2, height / 2 - 5, msg, fontName="Helvetica-Oblique", fontSize=9.5, textAnchor="middle", fillColor=colors.HexColor("#94A3B8")))
    return d


def extract_chart_data(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> tuple[list[str], list[list[float]], list[str]]:
    """Extract category labels, numeric data series, and series names from tabular rows."""
    if not columns or not rows:
        return [], [], []

    # Normalize rows to list of dicts
    dict_rows: list[dict[str, Any]] = []
    if isinstance(rows[0], dict):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    else:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    # 1. Identify category/x-axis column
    x_col = config.x_axis
    if not x_col or x_col not in columns:
        # Default: first non-numeric column or first column
        for c in columns:
            if any(not isinstance(r.get(c), (int, float)) for r in dict_rows[:5]):
                x_col = c
                break
        if not x_col:
            x_col = columns[0]

    categories = [str(r.get(x_col, "")) for r in dict_rows]

    # 2. Identify value/y-axis series
    y_cols: list[str] = []
    if isinstance(config.y_axis, list):
        y_cols = [c for c in config.y_axis if c in columns]
    elif isinstance(config.y_axis, str) and config.y_axis and config.y_axis in columns:
        y_cols = [config.y_axis]
    elif config.series:
        y_cols = [c for c in config.series if c in columns]

    if not y_cols:
        # Default: all numeric columns other than x_col
        for c in columns:
            if c != x_col:
                # check if values are convertible to float
                sample_vals = [r.get(c) for r in dict_rows[:10]]
                if any(_safe_float(v, None) is not None for v in sample_vals):  # type: ignore[arg-type]
                    y_cols.append(c)

    if not y_cols:
        # Fallback to second column
        if len(columns) > 1 and columns[1] != x_col:
            y_cols = [columns[1]]

    # 3. Build data matrix: [series_0_vals, series_1_vals, ...]
    data_series: list[list[float]] = []
    for y in y_cols:
        s_vals = [_safe_float(r.get(y)) for r in dict_rows]
        data_series.append(s_vals)

    series_names = [y.replace("_", " ").title() for y in y_cols]
    return categories, data_series, series_names


def build_chart(
    config: ChartConfiguration,
    columns: Sequence[str] | Sequence[Mapping[str, Any]],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]] | None = None,
    *,
    width: float | None = None,
    height: float | None = None,
    max_categories: int = 24,
) -> Drawing:
    """Build a publication-quality ReportLab vector Drawing according to config."""
    if rows is None and columns and isinstance(columns[0], (dict, Mapping)):
        actual_rows = columns
        actual_columns = list(columns[0].keys())
    else:
        actual_columns = list(columns) if columns else []
        actual_rows = rows or []

    if width is not None:
        config.width = width
    if height is not None:
        config.height = height

    title = config.title or ""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)

    categories, data_series, series_names = extract_chart_data(config, actual_columns, actual_rows)

    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for chart visualization.")

    # Limit category count for visual legibility
    if len(categories) > max_categories:
        categories = categories[:max_categories]
        data_series = [s[:max_categories] for s in data_series]

    chart_type = config.chart_type.lower()

    if chart_type in {ChartType.PIE.value, ChartType.DONUT.value}:
        return _build_pie_or_donut_chart(
            width=w,
            height=h,
            title=title,
            categories=categories,
            values=data_series[0],
            is_donut=(chart_type == ChartType.DONUT.value),
            fmt=config.format,
        )

    if chart_type == ChartType.HORIZONTAL_BAR.value:
        return _build_horizontal_bar_chart(
            width=w,
            height=h,
            title=title,
            categories=categories,
            data_series=data_series,
            series_names=series_names,
            fmt=config.format,
            has_legend=config.legend and len(series_names) > 1,
        )

    if chart_type in {ChartType.BAR.value, ChartType.GROUPED_BAR.value, ChartType.STACKED_BAR.value}:
        return _build_vertical_bar_chart(
            width=w,
            height=h,
            title=title,
            categories=categories,
            data_series=data_series,
            series_names=series_names,
            is_stacked=(chart_type == ChartType.STACKED_BAR.value),
            fmt=config.format,
            has_legend=config.legend and len(series_names) > 1,
        )

    # Default to Line / Time-series / Multi-line / Area / Scatter
    return _build_line_chart(
        width=w,
        height=h,
        title=title,
        categories=categories,
        data_series=data_series,
        series_names=series_names,
        fmt=config.format,
        has_legend=config.legend and len(series_names) > 1,
    )


# ---------------------------------------------------------------------------
# Specific Chart Implementations
# ---------------------------------------------------------------------------


def _build_pie_or_donut_chart(
    *,
    width: float,
    height: float,
    title: str,
    categories: list[str],
    values: list[float],
    is_donut: bool,
    fmt: str,
) -> Drawing:
    d = Drawing(width, height)
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FFFFFF"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))

    if title:
        d.add(String(16, height - 18, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#0F172A")))

    # Positive values only for pie
    filtered_cats: list[str] = []
    filtered_vals: list[float] = []
    total = sum(v for v in values if v > 0) or 1.0

    for c, v in zip(categories, values):
        if v > 0:
            filtered_cats.append(c)
            filtered_vals.append(v)

    if not filtered_vals:
        return _empty_chart_drawing(width, height, title, "All values are zero or negative.")

    pie = Pie()
    pie_radius = min(width * 0.35, (height - 35) * 0.42)
    pie.width = pie_radius * 2
    pie.height = pie_radius * 2
    pie.x = 24
    pie.y = (height - 25 - pie.height) / 2 + 5
    pie.data = filtered_vals
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white

    if is_donut:
        pie.innerRadiusFraction = 0.52

    # Color palette
    for idx in range(len(filtered_vals)):
        pie.slices[idx].fillColor = PALETTE[idx % len(PALETTE)]

    d.add(pie)

    # Side Legend
    leg = Legend()
    leg.x = pie.x + pie.width + 24
    leg.y = height - 32
    leg.dx = 8
    leg.dy = 8
    leg.fontName = "Helvetica"
    leg.fontSize = 8.5
    leg.boxAnchor = "nw"
    leg.columnMaximum = 8
    leg.strokeWidth = 0.5
    leg.strokeColor = colors.transparent
    leg.colorNamePairs = [
        (
            PALETTE[i % len(PALETTE)],
            f"{filtered_cats[i][:20]} ({filtered_vals[i] * 100.0 / total:.1f}%)"
        )
        for i in range(min(8, len(filtered_vals)))
    ]
    d.add(leg)
    return d


def _build_vertical_bar_chart(
    *,
    width: float,
    height: float,
    title: str,
    categories: list[str],
    data_series: list[list[float]],
    series_names: list[str],
    is_stacked: bool,
    fmt: str,
    has_legend: bool,
) -> Drawing:
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FFFFFF"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))

    top_margin = 32 if title else 16
    bottom_margin = 35
    left_margin = 52
    right_margin = 110 if has_legend else 24

    if title:
        d.add(String(16, height - 18, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#0F172A")))

    chart = VerticalBarChart()
    chart.x = left_margin
    chart.y = bottom_margin
    chart.width = max(100, width - left_margin - right_margin)
    chart.height = max(60, height - top_margin - bottom_margin)
    chart.data = data_series
    chart.categoryAxis.categoryNames = [c[:12] for c in categories]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.dy = -10
    chart.valueAxis.labels.fontSize = 7.5
    chart.valueAxis.labels.fontName = "Helvetica"

    if is_stacked:
        chart.categoryAxis.style = "stacked"

    for idx in range(len(data_series)):
        chart.bars[idx].fillColor = PALETTE[idx % len(PALETTE)]
        chart.bars[idx].strokeColor = colors.transparent

    d.add(chart)

    if has_legend:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = height - top_margin
        leg.dx = 8
        leg.dy = 8
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [
            (PALETTE[i % len(PALETTE)], series_names[i][:18])
            for i in range(len(series_names))
        ]
        d.add(leg)

    return d


def _build_horizontal_bar_chart(
    *,
    width: float,
    height: float,
    title: str,
    categories: list[str],
    data_series: list[list[float]],
    series_names: list[str],
    fmt: str,
    has_legend: bool,
) -> Drawing:
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FFFFFF"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))

    top_margin = 32 if title else 16
    bottom_margin = 25
    left_margin = 75
    right_margin = 110 if has_legend else 24

    if title:
        d.add(String(16, height - 18, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#0F172A")))

    chart = HorizontalBarChart()
    chart.x = left_margin
    chart.y = bottom_margin
    chart.width = max(100, width - left_margin - right_margin)
    chart.height = max(60, height - top_margin - bottom_margin)
    chart.data = data_series
    chart.categoryAxis.categoryNames = [c[:14] for c in categories]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7.5
    chart.valueAxis.labels.fontName = "Helvetica"

    for idx in range(len(data_series)):
        chart.bars[idx].fillColor = PALETTE[idx % len(PALETTE)]
        chart.bars[idx].strokeColor = colors.transparent

    d.add(chart)

    if has_legend:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = height - top_margin
        leg.dx = 8
        leg.dy = 8
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [
            (PALETTE[i % len(PALETTE)], series_names[i][:18])
            for i in range(len(series_names))
        ]
        d.add(leg)

    return d


def _build_line_chart(
    *,
    width: float,
    height: float,
    title: str,
    categories: list[str],
    data_series: list[list[float]],
    series_names: list[str],
    fmt: str,
    has_legend: bool,
) -> Drawing:
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FFFFFF"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))

    top_margin = 32 if title else 16
    bottom_margin = 35
    left_margin = 52
    right_margin = 110 if has_legend else 24

    if title:
        d.add(String(16, height - 18, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#0F172A")))

    chart = HorizontalLineChart()
    chart.x = left_margin
    chart.y = bottom_margin
    chart.width = max(100, width - left_margin - right_margin)
    chart.height = max(60, height - top_margin - bottom_margin)
    chart.data = data_series
    chart.categoryAxis.categoryNames = [c[:12] for c in categories]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.dy = -10
    chart.valueAxis.labels.fontSize = 7.5
    chart.valueAxis.labels.fontName = "Helvetica"

    for idx in range(len(data_series)):
        chart.lines[idx].strokeColor = PALETTE[idx % len(PALETTE)]
        chart.lines[idx].strokeWidth = 2.0

    d.add(chart)

    if has_legend:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = height - top_margin
        leg.dx = 12
        leg.dy = 6
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [
            (PALETTE[i % len(PALETTE)], series_names[i][:18])
            for i in range(len(series_names))
        ]
        d.add(leg)

    return d
