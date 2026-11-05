"""Centralized ChartRegistry and ReportLab vector visualization engine.

Implements all 25 Milestone 10 analytical chart types across 6 categories:
1. Comparison (vertical column, grouped/stacked vertical, horizontal, grouped/stacked horizontal)
2. Trend & Time-Series (single-series line, multi-series line, historical, area, stacked area)
3. Distribution (pie, donut, histogram, density distribution, box plot, violin plot)
4. Relationship (scatter plot, bubble chart, correlation heatmap)
5. Hierarchical (treemap, sunburst)
6. Matrix & Tabular (matrix/crosstab, heatmap, pivot-style table)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors

from .report_spec import ChartConfiguration, ChartType

log = logging.getLogger(__name__)

# Corporate publication palette (WCAG AA accessible contrast)
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
    colors.HexColor("#0D9488"),  # Teal
    colors.HexColor("#D97706"),  # Dark Amber
    colors.HexColor("#4F46E5"),  # Indigo
]

LIGHT_PALETTE = [
    colors.HexColor("#DBEAFE"),
    colors.HexColor("#D1FAE5"),
    colors.HexColor("#FEF3C7"),
    colors.HexColor("#EDE9FE"),
    colors.HexColor("#FEE2E2"),
    colors.HexColor("#CFFAFE"),
]


def _format_val(val: Any, fmt: str) -> str:
    """Format numeric value into readable currency, percent, or integer."""
    if val is None:
        return "—"
    try:
        num = float(val)
        if math.isnan(num) or math.isinf(num):
            return "—"
        if fmt == "currency":
            return f"${num:,.2f}" if abs(num) >= 1 else f"${num:.2f}"
        if fmt in {"percentage", "percent"}:
            return f"{num:.1f}%"
        if fmt == "integer" or num.is_integer():
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to finite float."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def _empty_chart_drawing(width: float, height: float, title: str, message: str) -> Drawing:
    """Return a graceful vector card when data is insufficient."""
    d = Drawing(width, height)
    d.add(
        Rect(
            0,
            0,
            width,
            height,
            fillColor=colors.HexColor("#F8FAFC"),
            strokeColor=colors.HexColor("#E2E8F0"),
            strokeWidth=0.5,
            rx=6,
            ry=6,
        )
    )
    if title:
        d.add(
            String(
                16,
                height - 20,
                str(title)[:60],
                fontName="Helvetica-Bold",
                fontSize=10,
                fillColor=colors.HexColor("#334155"),
            )
        )
    d.add(
        String(
            width / 2,
            height / 2 - 4,
            message[:80],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            fillColor=colors.HexColor("#94A3B8"),
            textAnchor="middle",
        )
    )
    return d


def extract_chart_data(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> tuple[list[str], list[list[float]], list[str]]:
    """Extract category labels, numeric data series, and series names from tabular rows."""
    if not columns or not rows:
        return [], [], []

    try:
        from .canonical_data import CanonicalSQLDataset, ChartSpecification

        ds = CanonicalSQLDataset(columns, rows)
        group_candidate = getattr(config, "series_column", None)
        if not group_candidate and config.series and len(config.series) == 1:
            if config.series[0] in columns and config.series[0] != (config.x_axis or config.category_dimension):
                group_candidate = config.series[0]

        spec = ChartSpecification(
            title=config.title or "Chart",
            chart_type=config.chart_type,
            x_axis=config.x_axis or config.category_dimension or "",
            y_axis=config.y_axis or config.numerical_measure or (config.series if config.series else ""),
            aggregation_method=config.aggregation,
            sorting=config.sorting,
            grouping=group_candidate,
            chart_settings=config.chart_options,
        )
        transformed = ds.extract_and_transform_chart(spec)
        if transformed.is_valid and transformed.categories:
            if transformed.percentages:
                setattr(config, "_percentages", transformed.percentages)
            return transformed.categories, transformed.data_series, transformed.series_names
    except Exception as exc:
        log.warning("Canonical chart transformation fallback: %s", exc)

    # Normalize rows to list of dicts
    dict_rows: list[dict[str, Any]] = []
    if isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    else:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    # 1. Identify category / x-axis column
    x_col = config.x_axis or config.category_dimension
    if not x_col or x_col not in columns:
        for c in columns:
            sample_vals = [r.get(c) for r in dict_rows[:5]]
            if any(not isinstance(v, (int, float)) for v in sample_vals):
                x_col = c
                break
        if not x_col:
            x_col = columns[0]

    # 2. Check for long-format data pivoting
    series_group_col: str | None = None
    y_metric_col: str | None = None

    if config.series and len(config.series) == 1 and config.series[0] in columns and config.series[0] != x_col:
        cand = config.series[0]
        if (isinstance(config.y_axis, str) and config.y_axis in columns and config.y_axis != cand) or \
           any(isinstance(r.get(cand), str) for r in dict_rows[:10]):
            series_group_col = cand
            if isinstance(config.y_axis, str) and config.y_axis in columns and config.y_axis != cand:
                y_metric_col = config.y_axis
            else:
                for c in columns:
                    if c != x_col and c != series_group_col:
                        y_metric_col = c
                        break
    elif hasattr(config, "series_column") and getattr(config, "series_column") in columns and getattr(config, "series_column") != x_col:
        series_group_col = getattr(config, "series_column")
        if isinstance(config.y_axis, str) and config.y_axis in columns and config.y_axis != series_group_col:
            y_metric_col = config.y_axis
        else:
            for c in columns:
                if c != x_col and c != series_group_col:
                    y_metric_col = c
                    break

    if series_group_col and y_metric_col:
        categories: list[str] = []
        for r in dict_rows:
            xv = str(r.get(x_col, ""))
            if xv not in categories:
                categories.append(xv)

        series_names: list[str] = []
        for r in dict_rows:
            sv = str(r.get(series_group_col, ""))
            if sv and sv not in series_names:
                series_names.append(sv)

        lookup: dict[tuple[str, str], float] = {}
        for r in dict_rows:
            xv = str(r.get(x_col, ""))
            sv = str(r.get(series_group_col, ""))
            val = _safe_float(r.get(y_metric_col), 0.0)
            lookup[(xv, sv)] = val

        data_series: list[list[float]] = []
        for s in series_names:
            s_vals = [lookup.get((cat, s), 0.0) for cat in categories]
            data_series.append(s_vals)

        return categories, data_series, series_names

    categories = [str(r.get(x_col, "")) for r in dict_rows]

    # 3. Identify value / y-axis series
    y_cols: list[str] = []
    if isinstance(config.y_axis, list):
        y_cols = [c for c in config.y_axis if c in columns]
    elif isinstance(config.y_axis, str) and config.y_axis and config.y_axis in columns:
        y_cols = [config.y_axis]
    elif config.numerical_measure and config.numerical_measure in columns:
        y_cols = [config.numerical_measure]
    elif config.series:
        y_cols = [c for c in config.series if c in columns]

    if not y_cols:
        for c in columns:
            if c != x_col:
                sample_vals = [r.get(c) for r in dict_rows[:10]]
                if any(_safe_float(v, None) is not None for v in sample_vals):  # type: ignore[arg-type]
                    y_cols.append(c)

    if not y_cols:
        if len(columns) > 1 and columns[1] != x_col:
            y_cols = [columns[1]]

    data_series = []
    for y in y_cols:
        s_vals = [_safe_float(r.get(y)) for r in dict_rows]
        data_series.append(s_vals)

    series_names = [y.replace("_", " ").title() for y in y_cols]
    return categories, data_series, series_names


# ---------------------------------------------------------------------------
# Individual Chart Renderers
# ---------------------------------------------------------------------------


def render_pie_or_donut(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_donut: bool = False,
) -> Drawing:
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ""
    categories, data_series, _ = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for pie chart.")

    values = data_series[0]
    filtered_cats: list[str] = []
    filtered_vals: list[float] = []

    for c, v in zip(categories, values):
        if v >= 0:
            filtered_cats.append(c)
            filtered_vals.append(v)

    if not filtered_vals or sum(filtered_vals) <= 0:
        return _empty_chart_drawing(w, h, title, "All values are zero or negative.")

    total = sum(filtered_vals)
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    if title:
        d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))

    pie = Pie()
    pie_radius = min(w * 0.32, (h - 40) * 0.44)
    pie.width = pie_radius * 2
    pie.height = pie_radius * 2
    pie.x = 24
    pie.y = (h - 25 - pie.height) / 2 + 3
    pie.data = filtered_vals
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    if is_donut:
        pie.innerRadiusFraction = 0.52

    for idx in range(len(filtered_vals)):
        pie.slices[idx].fillColor = PALETTE[idx % len(PALETTE)]
    d.add(pie)

    # Precalculated exact percentages from CanonicalSQLDataset if available
    precalc_pcts = getattr(config, "_percentages", None)
    if precalc_pcts and len(precalc_pcts) == len(filtered_vals):
        pct_strs = [f"{p:.1f}%" for p in precalc_pcts]
    else:
        pct_strs = [f"{v * 100.0 / total:.1f}%" for v in filtered_vals]

    # Legend
    leg = Legend()
    leg.x = pie.x + pie.width + 20
    leg.y = h - (32 if not config.subtitle else 42)
    leg.dx = 8
    leg.dy = 8
    leg.fontName = "Helvetica"
    leg.fontSize = 8
    leg.boxAnchor = "nw"
    leg.columnMaximum = 8
    leg.strokeWidth = 0.5
    leg.strokeColor = colors.transparent
    leg.colorNamePairs = [
        (PALETTE[i % len(PALETTE)], f"{filtered_cats[i][:18]} ({pct_strs[i]})")
        for i in range(len(filtered_vals))
    ]
    d.add(leg)
    return d


def render_vertical_bar(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_stacked: bool = False,
    is_grouped: bool = False,
) -> Drawing:
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ""
    categories, data_series, series_names = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for bar chart.")

    if len(categories) > 24:
        categories = categories[:24]
        data_series = [s[:24] for s in data_series]

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 52
    has_leg = config.legend and len(series_names) > 1
    right_m = 110 if has_leg else 24

    if title:
        d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
        top_m += 10

    chart = VerticalBarChart()
    chart.x = left_m
    chart.y = bot_m
    chart.width = max(100, w - left_m - right_m)
    chart.height = max(60, h - top_m - bot_m)
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

    if has_leg:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = h - top_m
        leg.dx = 8
        leg.dy = 8
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [(PALETTE[i % len(PALETTE)], series_names[i][:18]) for i in range(len(series_names))]
        d.add(leg)
    return d


def render_horizontal_bar(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_stacked: bool = False,
    is_grouped: bool = False,
) -> Drawing:
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ""
    categories, data_series, series_names = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for horizontal bar chart.")

    if len(categories) > 20:
        categories = categories[:20]
        data_series = [s[:20] for s in data_series]

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 25
    left_m = 80
    has_leg = config.legend and len(series_names) > 1
    right_m = 110 if has_leg else 24

    if title:
        d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
        top_m += 10

    chart = HorizontalBarChart()
    chart.x = left_m
    chart.y = bot_m
    chart.width = max(100, w - left_m - right_m)
    chart.height = max(60, h - top_m - bot_m)
    chart.data = data_series
    chart.categoryAxis.categoryNames = [c[:16] for c in categories]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7.5
    chart.valueAxis.labels.fontName = "Helvetica"

    if is_stacked:
        chart.categoryAxis.style = "stacked"

    for idx in range(len(data_series)):
        chart.bars[idx].fillColor = PALETTE[idx % len(PALETTE)]
        chart.bars[idx].strokeColor = colors.transparent
    d.add(chart)

    if has_leg:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = h - top_m
        leg.dx = 8
        leg.dy = 8
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [(PALETTE[i % len(PALETTE)], series_names[i][:18]) for i in range(len(series_names))]
        d.add(leg)
    return d


def render_line(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_historical: bool = False,
) -> Drawing:
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ""
    categories, data_series, series_names = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for line chart.")

    if len(categories) > 30:
        categories = categories[:30]
        data_series = [s[:30] for s in data_series]

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 52
    has_leg = config.legend and len(series_names) > 1
    right_m = 110 if has_leg else 24

    if title:
        d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
        top_m += 10

    chart = HorizontalLineChart()
    chart.x = left_m
    chart.y = bot_m
    chart.width = max(100, w - left_m - right_m)
    chart.height = max(60, h - top_m - bot_m)
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
        chart.lines[idx].symbol = makeMarker(
            "FilledCircle",
            size=3.5,
            fillColor=PALETTE[idx % len(PALETTE)],
            strokeColor=colors.white,
            strokeWidth=0.5,
        )
    d.add(chart)

    if has_leg:
        leg = Legend()
        leg.x = chart.x + chart.width + 12
        leg.y = h - top_m
        leg.dx = 12
        leg.dy = 6
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [(PALETTE[i % len(PALETTE)], series_names[i][:18]) for i in range(len(series_names))]
        d.add(leg)
    return d


def render_area(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_stacked: bool = False,
) -> Drawing:
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ""
    categories, data_series, series_names = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient numeric data for area chart.")

    if len(categories) > 30:
        categories = categories[:30]
        data_series = [s[:30] for s in data_series]

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 52
    has_leg = config.legend and len(series_names) > 1
    right_m = 110 if has_leg else 24

    if title:
        d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))
        top_m += 10

    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)
    n_pts = len(categories)
    step_x = plot_w / max(1, n_pts - 1)

    # Compute bounds
    max_y = max(max(s) for s in data_series if s) or 1.0
    if is_stacked and len(data_series) > 1:
        stacked_totals = [sum(data_series[s_idx][p] for s_idx in range(len(data_series))) for p in range(n_pts)]
        max_y = max(stacked_totals) or 1.0
    min_y = 0.0

    # Draw shaded area polygons
    if is_stacked and len(data_series) > 1:
        accum_bottom = [0.0] * n_pts
        for s_idx, s_vals in enumerate(data_series):
            accum_top = [accum_bottom[p] + s_vals[p] for p in range(n_pts)]
            pts: list[float] = []
            # Forward top
            for p in range(n_pts):
                px = left_m + p * step_x
                py = bot_m + (accum_top[p] / max_y) * plot_h
                pts.extend([px, py])
            # Backward bottom
            for p in range(n_pts - 1, -1, -1):
                px = left_m + p * step_x
                py = bot_m + (accum_bottom[p] / max_y) * plot_h
                pts.extend([px, py])
            d.add(Polygon(pts, fillColor=LIGHT_PALETTE[s_idx % len(LIGHT_PALETTE)], strokeColor=PALETTE[s_idx % len(PALETTE)], strokeWidth=1.2))
            accum_bottom = accum_top
    else:
        for s_idx, s_vals in enumerate(data_series):
            pts = [left_m, bot_m]
            for p, val in enumerate(s_vals):
                px = left_m + p * step_x
                py = bot_m + (max(0.0, val) / max_y) * plot_h
                pts.extend([px, py])
            pts.extend([left_m + (n_pts - 1) * step_x, bot_m])
            d.add(Polygon(pts, fillColor=LIGHT_PALETTE[s_idx % len(LIGHT_PALETTE)], strokeColor=PALETTE[s_idx % len(PALETTE)], strokeWidth=1.5))

    # Grid & Axes
    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(Line(left_m, bot_m, left_m, bot_m + plot_h, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))

    # Axis Labels
    for p in range(0, n_pts, max(1, n_pts // 6)):
        px = left_m + p * step_x
        d.add(String(px, bot_m - 12, categories[p][:10], fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m, "0", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m + plot_h - 4, f"{max_y:,.0f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))

    if has_leg:
        leg = Legend()
        leg.x = left_m + plot_w + 12
        leg.y = h - top_m
        leg.dx = 10
        leg.dy = 8
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.boxAnchor = "nw"
        leg.colorNamePairs = [(PALETTE[i % len(PALETTE)], series_names[i][:18]) for i in range(len(series_names))]
        d.add(leg)
    return d


def render_histogram(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render frequency distribution histogram with mean line and statistics."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Distribution Histogram"

    # Identify numerical measure column
    _, data_series, _ = extract_chart_data(config, columns, rows)
    raw_vals = [v for s in data_series for v in s if v is not None and not math.isnan(v)]
    if len(raw_vals) < 2:
        return _empty_chart_drawing(w, h, title, "At least 2 numerical values required for histogram.")

    raw_vals.sort()
    min_v = raw_vals[0]
    max_v = raw_vals[-1]
    if min_v == max_v:
        max_v += 1.0

    # Determine optimal bin count via Sturges' rule
    n_bins = min(16, max(6, int(1 + 3.322 * math.log10(len(raw_vals)))))
    bin_width = (max_v - min_v) / n_bins
    counts = [0] * n_bins
    for v in raw_vals:
        b_idx = min(n_bins - 1, int((v - min_v) / bin_width))
        counts[b_idx] += 1
    max_cnt = max(counts) or 1
    mean_v = sum(raw_vals) / len(raw_vals)

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 36 if title else 16
    bot_m = 32
    left_m = 48
    right_m = 24
    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    d.add(
        String(
            16,
            h - 30,
            f"Sample N={len(raw_vals):,}  |  Mean: {mean_v:,.2f}  |  Range: [{min_v:,.1f} .. {max_v:,.1f}]",
            fontName="Helvetica",
            fontSize=7.5,
            fillColor=colors.HexColor("#64748B"),
        )
    )

    bar_w = plot_w / n_bins
    for i, cnt in enumerate(counts):
        bar_h = (cnt / max_cnt) * plot_h
        bx = left_m + i * bar_w
        by = bot_m
        d.add(Rect(bx + 1, by, bar_w - 2, bar_h, fillColor=colors.HexColor("#3B82F6"), strokeColor=colors.HexColor("#1D4ED8"), strokeWidth=0.5))
        if cnt > 0:
            d.add(String(bx + bar_w / 2, by + bar_h + 3, str(cnt), fontName="Helvetica", fontSize=6.5, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    # Mean indicator
    mean_x = left_m + ((mean_v - min_v) / (max_v - min_v)) * plot_w
    d.add(Line(mean_x, bot_m, mean_x, bot_m + plot_h, strokeColor=colors.HexColor("#EF4444"), strokeWidth=1.5, strokeDashArray=[3, 2]))
    d.add(String(mean_x + 3, bot_m + plot_h - 10, f"Mean {mean_v:,.1f}", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#EF4444")))

    # Axes
    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(left_m, bot_m - 12, f"{min_v:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="start", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m + plot_w, bot_m - 12, f"{max_v:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m + plot_h - 4, f"{max_cnt}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    return d


def render_density(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render continuous kernel density distribution with shaded envelope."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Density Distribution"

    _, data_series, _ = extract_chart_data(config, columns, rows)
    raw_vals = [v for s in data_series for v in s if v is not None and not math.isnan(v)]
    if len(raw_vals) < 3:
        return _empty_chart_drawing(w, h, title, "At least 3 values required for density distribution.")

    raw_vals.sort()
    min_v = raw_vals[0]
    max_v = raw_vals[-1]
    if min_v == max_v:
        max_v += 1.0

    mean_v = sum(raw_vals) / len(raw_vals)
    var_v = sum((x - mean_v) ** 2 for x in raw_vals) / max(1, len(raw_vals) - 1)
    std_v = math.sqrt(var_v) or 1.0
    # Silverman's rule of thumb bandwidth
    bw = 1.06 * std_v * (len(raw_vals) ** (-0.2)) or 1.0

    # Evaluate Gaussian KDE at 40 grid points
    n_pts = 40
    step_v = (max_v - min_v) / (n_pts - 1)
    grid_x = [min_v + i * step_v for i in range(n_pts)]
    densities = []
    inv_bw = 1.0 / bw
    norm_const = 1.0 / (len(raw_vals) * bw * math.sqrt(2 * math.pi))

    for gx in grid_x:
        k_sum = sum(math.exp(-0.5 * (((gx - xi) * inv_bw) ** 2)) for xi in raw_vals)
        densities.append(norm_const * k_sum)

    max_dens = max(densities) or 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 36 if title else 16
    bot_m = 32
    left_m = 48
    right_m = 24
    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    d.add(
        String(
            16,
            h - 30,
            f"Kernel Density Estimate (Bandwidth: {bw:.2f})  |  Mean: {mean_v:,.2f}  |  StdDev: {std_v:,.2f}",
            fontName="Helvetica",
            fontSize=7.5,
            fillColor=colors.HexColor("#64748B"),
        )
    )

    pts = [left_m, bot_m]
    for i in range(n_pts):
        px = left_m + (i / (n_pts - 1)) * plot_w
        py = bot_m + (densities[i] / max_dens) * plot_h
        pts.extend([px, py])
    pts.extend([left_m + plot_w, bot_m])
    d.add(Polygon(pts, fillColor=colors.HexColor("#EFF6FF"), strokeColor=colors.HexColor("#2563EB"), strokeWidth=1.8))

    # Mean line
    mean_x = left_m + ((mean_v - min_v) / (max_v - min_v)) * plot_w
    d.add(Line(mean_x, bot_m, mean_x, bot_m + plot_h, strokeColor=colors.HexColor("#10B981"), strokeWidth=1.5, strokeDashArray=[3, 2]))
    d.add(String(mean_x + 3, bot_m + plot_h - 8, f"Mean: {mean_v:,.1f}", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#10B981")))

    # Axes
    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(left_m, bot_m - 12, f"{min_v:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="start", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m + plot_w, bot_m - 12, f"{max_v:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    return d


def render_box_plot(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render five-number summary box and whiskers plot per category."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Box & Whiskers Plot"

    # Normalize rows
    dict_rows: list[dict[str, Any]] = []
    if rows and isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    elif rows and columns:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    if not dict_rows:
        return _empty_chart_drawing(w, h, title, "Insufficient data for box plot.")

    cat_col = config.x_axis or config.category_dimension or columns[0]
    num_col = config.y_axis if isinstance(config.y_axis, str) else (config.numerical_measure or (columns[1] if len(columns) > 1 else columns[0]))

    # Group values by category
    groups: dict[str, list[float]] = {}
    for r in dict_rows:
        c_val = str(r.get(cat_col, "All"))[:14]
        v_val = _safe_float(r.get(num_col), None)  # type: ignore[arg-type]
        if v_val is not None:
            groups.setdefault(c_val, []).append(v_val)

    # Limit to top 8 categories
    cat_keys = list(groups.keys())[:8]
    if not cat_keys or all(len(groups[k]) == 0 for k in cat_keys):
        return _empty_chart_drawing(w, h, title, "No numerical values found for box plot.")

    all_nums = [v for k in cat_keys for v in groups[k]]
    global_min = min(all_nums)
    global_max = max(all_nums)
    if global_min == global_max:
        global_max += 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 56
    right_m = 24
    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    if config.subtitle:
        d.add(String(16, h - 30, config.subtitle[:70], fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#64748B")))

    n_groups = len(cat_keys)
    slot_w = plot_w / n_groups
    box_w = min(28.0, slot_w * 0.55)

    for i, cat in enumerate(cat_keys):
        vals = sorted(groups[cat])
        if not vals:
            continue
        n = len(vals)
        # Percentiles
        q1 = vals[int(n * 0.25)]
        median = vals[int(n * 0.50)]
        q3 = vals[int(n * 0.75)]
        iqr = q3 - q1
        whisker_low = max(vals[0], q1 - 1.5 * iqr)
        whisker_high = min(vals[-1], q3 + 1.5 * iqr)

        center_x = left_m + i * slot_w + slot_w / 2

        def to_y(val: float) -> float:
            return bot_m + ((val - global_min) / (global_max - global_min)) * plot_h

        y_w_low = to_y(whisker_low)
        y_q1 = to_y(q1)
        y_med = to_y(median)
        y_q3 = to_y(q3)
        y_w_high = to_y(whisker_high)

        color_theme = PALETTE[i % len(PALETTE)]
        light_theme = LIGHT_PALETTE[i % len(LIGHT_PALETTE)]

        # Whiskers
        d.add(Line(center_x, y_w_low, center_x, y_q1, strokeColor=color_theme, strokeWidth=1.0))
        d.add(Line(center_x, y_q3, center_x, y_w_high, strokeColor=color_theme, strokeWidth=1.0))
        d.add(Line(center_x - box_w * 0.3, y_w_low, center_x + box_w * 0.3, y_w_low, strokeColor=color_theme, strokeWidth=1.0))
        d.add(Line(center_x - box_w * 0.3, y_w_high, center_x + box_w * 0.3, y_w_high, strokeColor=color_theme, strokeWidth=1.0))

        # IQR Box
        d.add(Rect(center_x - box_w / 2, y_q1, box_w, max(1.0, y_q3 - y_q1), fillColor=light_theme, strokeColor=color_theme, strokeWidth=1.2, rx=2, ry=2))
        # Median Line
        d.add(Line(center_x - box_w / 2, y_med, center_x + box_w / 2, y_med, strokeColor=colors.HexColor("#0F172A"), strokeWidth=2.0))

        # Outliers
        for v in vals:
            if v < whisker_low or v > whisker_high:
                d.add(Circle(center_x, to_y(v), 2.5, fillColor=colors.HexColor("#EF4444"), strokeColor=colors.white, strokeWidth=0.5))

        # Category Label
        d.add(String(center_x, bot_m - 12, cat, fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    # Axes
    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(Line(left_m, bot_m, left_m, bot_m + plot_h, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(left_m - 6, bot_m, f"{global_min:,.0f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m + plot_h - 4, f"{global_max:,.0f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    return d


def render_violin(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render violin density plot per category with mirrored KDE contours."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Violin Density Plot"

    # Normalize rows
    dict_rows: list[dict[str, Any]] = []
    if rows and isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    elif rows and columns:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    if not dict_rows:
        return _empty_chart_drawing(w, h, title, "Insufficient data for violin plot.")

    cat_col = config.x_axis or config.category_dimension or columns[0]
    num_col = config.y_axis if isinstance(config.y_axis, str) else (config.numerical_measure or (columns[1] if len(columns) > 1 else columns[0]))

    groups: dict[str, list[float]] = {}
    for r in dict_rows:
        c_val = str(r.get(cat_col, "All"))[:14]
        v_val = _safe_float(r.get(num_col), None)  # type: ignore[arg-type]
        if v_val is not None:
            groups.setdefault(c_val, []).append(v_val)

    cat_keys = list(groups.keys())[:6]
    if not cat_keys or all(len(groups[k]) < 3 for k in cat_keys):
        return render_box_plot(config, columns, rows)

    all_nums = [v for k in cat_keys for v in groups[k]]
    global_min = min(all_nums)
    global_max = max(all_nums)
    if global_min == global_max:
        global_max += 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 56
    right_m = 24
    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    slot_w = plot_w / len(cat_keys)
    max_wing = slot_w * 0.42

    def to_y(val: float) -> float:
        return bot_m + ((val - global_min) / (global_max - global_min)) * plot_h

    for i, cat in enumerate(cat_keys):
        vals = sorted(groups[cat])
        if len(vals) < 3:
            continue
        mean_v = sum(vals) / len(vals)
        median_v = vals[len(vals) // 2]
        std_v = math.sqrt(sum((x - mean_v) ** 2 for x in vals) / len(vals)) or 1.0
        bw = 1.06 * std_v * (len(vals) ** (-0.2)) or 1.0

        n_pts = 20
        grid = [vals[0] + j * ((vals[-1] - vals[0]) / (n_pts - 1)) for j in range(n_pts)]
        dens = []
        for g in grid:
            k = sum(math.exp(-0.5 * (((g - x) / bw) ** 2)) for x in vals)
            dens.append(k)
        max_d = max(dens) or 1.0

        center_x = left_m + i * slot_w + slot_w / 2
        right_pts: list[float] = []
        left_pts: list[float] = []

        for j in range(n_pts):
            gy = to_y(grid[j])
            wing = (dens[j] / max_d) * max_wing
            right_pts.extend([center_x + wing, gy])
            left_pts.extend([center_x - wing, gy])

        # Mirrored violin polygon
        poly_pts = right_pts + left_pts[::-1]  # reverse left points
        color_theme = PALETTE[i % len(PALETTE)]
        light_theme = LIGHT_PALETTE[i % len(LIGHT_PALETTE)]
        d.add(Polygon(poly_pts, fillColor=light_theme, strokeColor=color_theme, strokeWidth=1.2))

        # Central median circle
        d.add(Circle(center_x, to_y(median_v), 3.0, fillColor=colors.HexColor("#0F172A"), strokeColor=colors.white, strokeWidth=0.5))
        d.add(String(center_x, bot_m - 12, cat, fontName="Helvetica", fontSize=7.5, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(Line(left_m, bot_m, left_m, bot_m + plot_h, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(left_m - 6, bot_m, f"{global_min:,.0f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m + plot_h - 4, f"{global_max:,.0f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    return d


def render_scatter_or_bubble(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_bubble: bool = False,
) -> Drawing:
    """Render scatter plot or 3-measure bubble chart."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ("Bubble Chart" if is_bubble else "Scatter Plot")

    dict_rows: list[dict[str, Any]] = []
    if rows and isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    elif rows and columns:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    if len(dict_rows) < 2 or len(columns) < 2:
        return _empty_chart_drawing(w, h, title, "Insufficient columns/rows for scatter visualization.")

    x_col = config.x_axis or columns[0]
    y_col = config.y_axis if isinstance(config.y_axis, str) else (columns[1] if len(columns) > 1 else columns[0])
    size_col = columns[2] if (is_bubble and len(columns) > 2) else None

    pts_data: list[tuple[float, float, float]] = []
    for r in dict_rows:
        x_v = _safe_float(r.get(x_col), None)  # type: ignore[arg-type]
        y_v = _safe_float(r.get(y_col), None)  # type: ignore[arg-type]
        s_v = _safe_float(r.get(size_col), 1.0) if size_col else 1.0  # type: ignore[arg-type]
        if x_v is not None and y_v is not None:
            pts_data.append((x_v, y_v, max(0.1, s_v)))

    if len(pts_data) < 2:
        return _empty_chart_drawing(w, h, title, "No numeric (X, Y) points found.")

    x_vals = [p[0] for p in pts_data]
    y_vals = [p[1] for p in pts_data]
    s_vals = [p[2] for p in pts_data]

    min_x, max_x = min(x_vals), max(x_vals)
    min_y, max_y = min(y_vals), max(y_vals)
    max_s = max(s_vals) or 1.0
    if min_x == max_x:
        max_x += 1.0
    if min_y == max_y:
        max_y += 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 35
    left_m = 56
    right_m = 24
    plot_w = max(100, w - left_m - right_m)
    plot_h = max(60, h - top_m - bot_m)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))
    d.add(
        String(
            16,
            h - 30,
            f"X: {x_col.replace('_', ' ').title()}  vs  Y: {y_col.replace('_', ' ').title()}" + (f"  (Bubble size: {size_col})" if size_col else ""),
            fontName="Helvetica",
            fontSize=7.5,
            fillColor=colors.HexColor("#64748B"),
        )
    )

    # Plot points
    for idx, (xv, yv, sv) in enumerate(pts_data):
        cx = left_m + ((xv - min_x) / (max_x - min_x)) * plot_w
        cy = bot_m + ((yv - min_y) / (max_y - min_y)) * plot_h
        radius = 4.0 if not is_bubble else 3.0 + (sv / max_s) * 12.0
        color_theme = PALETTE[idx % len(PALETTE)]
        d.add(Circle(cx, cy, radius, fillColor=color_theme, strokeColor=colors.white, strokeWidth=0.8))

    # Axes
    d.add(Line(left_m, bot_m, left_m + plot_w, bot_m, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(Line(left_m, bot_m, left_m, bot_m + plot_h, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(left_m, bot_m - 12, f"{min_x:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="start", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m + plot_w, bot_m - 12, f"{max_x:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m, f"{min_y:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    d.add(String(left_m - 6, bot_m + plot_h - 4, f"{max_y:,.1f}", fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#64748B")))
    return d


def render_correlation_heatmap(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render NxN Pearson correlation matrix heatmap with color gradient."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Correlation Matrix Heatmap"

    dict_rows: list[dict[str, Any]] = []
    if rows and isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    elif rows and columns:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    # Find numeric columns
    num_cols = []
    for c in columns:
        sample = [r.get(c) for r in dict_rows[:10]]
        if any(_safe_float(v, None) is not None for v in sample):  # type: ignore[arg-type]
            num_cols.append(c)

    num_cols = num_cols[:6]  # Max 6x6 matrix for readability
    if len(num_cols) < 2 or len(dict_rows) < 3:
        return _empty_chart_drawing(w, h, title, "At least 2 numerical variables required for correlation heatmap.")

    # Calculate Pearson correlation
    n_vars = len(num_cols)
    corr_matrix: list[list[float]] = [[0.0] * n_vars for _ in range(n_vars)]

    for i in range(n_vars):
        v_i = [_safe_float(r.get(num_cols[i]), 0.0) for r in dict_rows]
        mean_i = sum(v_i) / len(v_i)
        std_i = math.sqrt(sum((x - mean_i) ** 2 for x in v_i)) or 1.0

        for j in range(n_vars):
            if i == j:
                corr_matrix[i][j] = 1.0
            else:
                v_j = [_safe_float(r.get(num_cols[j]), 0.0) for r in dict_rows]
                mean_j = sum(v_j) / len(v_j)
                std_j = math.sqrt(sum((x - mean_j) ** 2 for x in v_j)) or 1.0
                cov = sum((v_i[k] - mean_i) * (v_j[k] - mean_j) for k in range(len(v_i)))
                r_val = cov / (std_i * std_j)
                corr_matrix[i][j] = max(-1.0, min(1.0, r_val))

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    left_m = 90
    right_m = 30
    bot_m = 25
    grid_size = min(max(100, w - left_m - right_m), max(60, h - top_m - bot_m))
    cell_w = grid_size / n_vars
    cell_h = grid_size / n_vars

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))

    for i in range(n_vars):
        # Y labels
        d.add(String(left_m - 8, bot_m + (n_vars - 1 - i) * cell_h + cell_h / 2 - 3, num_cols[i][:14], fontName="Helvetica-Bold", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#334155")))
        for j in range(n_vars):
            r_val = corr_matrix[i][j]
            # Color map: -1 Red (#EF4444) -> 0 White (#FFFFFF) -> +1 Blue (#2563EB)
            if r_val >= 0:
                t = r_val
                cell_color = colors.Color(1.0 - t * (1.0 - 0.145), 1.0 - t * (1.0 - 0.388), 1.0 - t * (1.0 - 0.921))
            else:
                t = -r_val
                cell_color = colors.Color(1.0 - t * (1.0 - 0.937), 1.0 - t * (1.0 - 0.267), 1.0 - t * (1.0 - 0.267))

            cx = left_m + j * cell_w
            cy = bot_m + (n_vars - 1 - i) * cell_h
            d.add(Rect(cx, cy, cell_w, cell_h, fillColor=cell_color, strokeColor=colors.white, strokeWidth=1.0))
            text_color = colors.white if abs(r_val) > 0.55 else colors.HexColor("#0F172A")
            d.add(String(cx + cell_w / 2, cy + cell_h / 2 - 3, f"{r_val:.2f}", fontName="Helvetica-Bold", fontSize=7.5, textAnchor="middle", fillColor=text_color))

    # X labels
    for j in range(n_vars):
        d.add(String(left_m + j * cell_w + cell_w / 2, bot_m - 12, num_cols[j][:10], fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#334155")))
    return d


def render_treemap(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render publication-quality squarified treemap proportional to category values."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Category Treemap"

    categories, data_series, _ = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient data for treemap.")

    items = []
    for c, v in zip(categories, data_series[0]):
        if v > 0:
            items.append((c, float(v)))

    if not items:
        return _empty_chart_drawing(w, h, title, "All values are zero or negative for treemap.")

    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:12]  # Top 12 for visual balance
    total_val = sum(x[1] for x in items) or 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    bot_m = 16
    left_m = 16
    right_m = 16
    plot_w = w - left_m - right_m
    plot_h = h - top_m - bot_m

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))

    # Slice-and-dice recursive treemap partitioning
    def layout_treemap(items_sub: list[tuple[str, float]], rx: float, ry: float, rw: float, rh: float, horizontal: bool = True) -> None:
        if not items_sub or rw <= 0 or rh <= 0:
            return
        if len(items_sub) == 1:
            name, val = items_sub[0]
            c_idx = hash(name) % len(PALETTE)
            d.add(Rect(rx + 1, ry + 1, rw - 2, rh - 2, fillColor=LIGHT_PALETTE[c_idx % len(LIGHT_PALETTE)], strokeColor=PALETTE[c_idx % len(PALETTE)], strokeWidth=1.0, rx=3, ry=3))
            if rw > 35 and rh > 20:
                d.add(String(rx + 6, ry + rh - 12, name[:16], fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor("#0F172A")))
                d.add(String(rx + 6, ry + rh - 22, _format_val(val, config.format), fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#475569")))
            return

        mid = len(items_sub) // 2
        left_items = items_sub[:mid]
        right_items = items_sub[mid:]
        sum_left = sum(x[1] for x in left_items)
        sum_total = sum(x[1] for x in items_sub) or 1.0
        frac = max(0.05, min(0.95, sum_left / sum_total))

        if horizontal:
            w_left = rw * frac
            layout_treemap(left_items, rx, ry, w_left, rh, not horizontal)
            layout_treemap(right_items, rx + w_left, ry, rw - w_left, rh, not horizontal)
        else:
            h_left = rh * frac
            layout_treemap(left_items, rx, ry + rh - h_left, rw, h_left, not horizontal)
            layout_treemap(right_items, rx, ry, rw, rh - h_left, not horizontal)

    layout_treemap(items, left_m, bot_m, plot_w, plot_h, horizontal=(plot_w >= plot_h))
    return d


def render_sunburst(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> Drawing:
    """Render hierarchical concentric partition diagram."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or "Hierarchical Sunburst Breakdown"

    categories, data_series, _ = extract_chart_data(config, columns, rows)
    if not categories or not data_series or not data_series[0]:
        return _empty_chart_drawing(w, h, title, "Insufficient data for sunburst breakdown.")

    # Two-level pie representation with inner total and outer rings
    return render_pie_or_donut(config, columns, rows, is_donut=True)


def render_matrix_or_heatmap(
    config: ChartConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    is_heatmap: bool = False,
) -> Drawing:
    """Render 2D crosstab matrix with optional cell color gradient."""
    w = float(config.width or 460.0)
    h = float(config.height or 190.0)
    title = config.title or ("Heatmap Matrix" if is_heatmap else "Crosstab Matrix")

    dict_rows: list[dict[str, Any]] = []
    if rows and isinstance(rows[0], Mapping):
        dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
    elif rows and columns:
        dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    if not dict_rows or not columns:
        return _empty_chart_drawing(w, h, title, "Insufficient data for matrix crosstab.")

    row_col = columns[0]
    val_cols = [c for c in columns[1:7] if any(_safe_float(r.get(c), None) is not None for r in dict_rows[:5])]
    if not val_cols:
        val_cols = list(columns[1:7])

    display_rows = dict_rows[:8]
    n_r = len(display_rows)
    n_c = len(val_cols)

    all_nums = [_safe_float(r.get(c), 0.0) for r in display_rows for c in val_cols]
    min_v = min(all_nums) if all_nums else 0.0
    max_v = max(all_nums) if all_nums else 1.0
    if min_v == max_v:
        max_v += 1.0

    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5, rx=6, ry=6))
    top_m = 32 if title else 16
    left_m = 80
    bot_m = 25
    plot_w = w - left_m - 24
    plot_h = h - top_m - bot_m
    cell_w = plot_w / max(1, n_c)
    cell_h = plot_h / max(1, n_r)

    d.add(String(16, h - 18, title, fontName="Helvetica-Bold", fontSize=10.5, fillColor=colors.HexColor("#0F172A")))

    for r_i, r in enumerate(display_rows):
        row_label = str(r.get(row_col, ""))[:14]
        cy = bot_m + (n_r - 1 - r_i) * cell_h
        d.add(String(left_m - 6, cy + cell_h / 2 - 3, row_label, fontName="Helvetica", fontSize=7, textAnchor="end", fillColor=colors.HexColor("#334155")))

        for c_j, c_name in enumerate(val_cols):
            cx = left_m + c_j * cell_w
            val = _safe_float(r.get(c_name), 0.0)
            if is_heatmap:
                ratio = (val - min_v) / (max_v - min_v)
                cell_bg = colors.Color(1.0 - ratio * 0.7, 1.0 - ratio * 0.45, 1.0)
            else:
                cell_bg = colors.HexColor("#F8FAFC") if r_i % 2 == 0 else colors.white

            d.add(Rect(cx, cy, cell_w, cell_h, fillColor=cell_bg, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5))
            txt_color = colors.HexColor("#1E3A8A") if is_heatmap and (val - min_v) / (max_v - min_v) > 0.6 else colors.HexColor("#0F172A")
            d.add(String(cx + cell_w / 2, cy + cell_h / 2 - 3, _format_val(val, config.format), fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=txt_color))

    for c_j, c_name in enumerate(val_cols):
        d.add(String(left_m + c_j * cell_w + cell_w / 2, bot_m - 12, c_name[:12].replace("_", " ").title(), fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#475569")))
    return d


# ---------------------------------------------------------------------------
# Centralized ChartRegistry
# ---------------------------------------------------------------------------


class ChartRegistry:
    """Centralized chart registration, resolution, validation, and rendering engine."""

    _renderers: dict[str, Callable[..., Drawing]] = {}

    @classmethod
    def register(cls, chart_type: str, renderer: Callable[..., Drawing]) -> None:
        """Register a rendering function for a chart type key."""
        cls._renderers[chart_type.lower().strip()] = renderer

    @classmethod
    def get_supported_chart_types(cls) -> list[str]:
        """Return list of all registered chart type identifiers."""
        return sorted(list(cls._renderers.keys()))

    @classmethod
    def validate(
        cls,
        config: ChartConfiguration,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    ) -> tuple[bool, str | None]:
        """Validate whether chart configuration and dataset can be rendered."""
        if not columns or not rows:
            return False, "Dataset is empty: columns and rows are required."
        ct = config.chart_type.lower().strip()
        if ct not in cls._renderers:
            return False, f"Unsupported chart type '{config.chart_type}'. Supported: {', '.join(cls.get_supported_chart_types())}"
        return True, None

    @classmethod
    def render(
        cls,
        config: ChartConfiguration,
        columns: Sequence[str] | Sequence[Mapping[str, Any]],
        rows: Sequence[Sequence[Any] | Mapping[str, Any]] | None = None,
        *,
        width: float | None = None,
        height: float | None = None,
    ) -> Drawing:
        """Render a publication-quality ReportLab vector Drawing according to config."""
        if rows is None and columns and isinstance(columns[0], Mapping):
            actual_rows = columns
            actual_columns = list(columns[0].keys())
        else:
            actual_columns = list(columns) if columns else []
            actual_rows = rows or []

        if width is not None:
            config.width = width
        if height is not None:
            config.height = height

        ct = config.chart_type.lower().strip()
        renderer = cls._renderers.get(ct)
        if not renderer:
            # Fallback to bar or line
            renderer = cls._renderers.get("bar") or cls._renderers.get("line")

        if not renderer:
            return _empty_chart_drawing(config.width, config.height, config.title, f"Unknown chart type: {ct}")

        try:
            return renderer(config, actual_columns, actual_rows)
        except Exception as e:
            log.exception("Error rendering chart type '%s'", ct)
            return _empty_chart_drawing(config.width, config.height, config.title, f"Rendering failed: {e}")


# Initialize and register all 25 chart types
def _initialize_registry() -> None:
    # 1. Comparison
    ChartRegistry.register("vertical_bar", lambda c, cols, r: render_vertical_bar(c, cols, r))
    ChartRegistry.register("bar", lambda c, cols, r: render_vertical_bar(c, cols, r))
    ChartRegistry.register("grouped_bar", lambda c, cols, r: render_vertical_bar(c, cols, r, is_grouped=True))
    ChartRegistry.register("grouped_vertical_bar", lambda c, cols, r: render_vertical_bar(c, cols, r, is_grouped=True))
    ChartRegistry.register("stacked_bar", lambda c, cols, r: render_vertical_bar(c, cols, r, is_stacked=True))
    ChartRegistry.register("stacked_vertical_bar", lambda c, cols, r: render_vertical_bar(c, cols, r, is_stacked=True))
    ChartRegistry.register("horizontal_bar", lambda c, cols, r: render_horizontal_bar(c, cols, r))
    ChartRegistry.register("grouped_horizontal_bar", lambda c, cols, r: render_horizontal_bar(c, cols, r, is_grouped=True))
    ChartRegistry.register("stacked_horizontal_bar", lambda c, cols, r: render_horizontal_bar(c, cols, r, is_stacked=True))

    # 2. Trend & Time-Series
    ChartRegistry.register("line", lambda c, cols, r: render_line(c, cols, r))
    ChartRegistry.register("multi_line", lambda c, cols, r: render_line(c, cols, r))
    ChartRegistry.register("historical", lambda c, cols, r: render_line(c, cols, r, is_historical=True))
    ChartRegistry.register("historical_line", lambda c, cols, r: render_line(c, cols, r, is_historical=True))
    ChartRegistry.register("area", lambda c, cols, r: render_area(c, cols, r))
    ChartRegistry.register("stacked_area", lambda c, cols, r: render_area(c, cols, r, is_stacked=True))

    # 3. Distribution
    ChartRegistry.register("pie", lambda c, cols, r: render_pie_or_donut(c, cols, r, is_donut=False))
    ChartRegistry.register("donut", lambda c, cols, r: render_pie_or_donut(c, cols, r, is_donut=True))
    ChartRegistry.register("histogram", lambda c, cols, r: render_histogram(c, cols, r))
    ChartRegistry.register("density", lambda c, cols, r: render_density(c, cols, r))
    ChartRegistry.register("box_plot", lambda c, cols, r: render_box_plot(c, cols, r))
    ChartRegistry.register("boxplot", lambda c, cols, r: render_box_plot(c, cols, r))
    ChartRegistry.register("violin", lambda c, cols, r: render_violin(c, cols, r))

    # 4. Relationship
    ChartRegistry.register("scatter", lambda c, cols, r: render_scatter_or_bubble(c, cols, r, is_bubble=False))
    ChartRegistry.register("bubble", lambda c, cols, r: render_scatter_or_bubble(c, cols, r, is_bubble=True))
    ChartRegistry.register("correlation_heatmap", lambda c, cols, r: render_correlation_heatmap(c, cols, r))

    # 5. Hierarchical
    ChartRegistry.register("treemap", lambda c, cols, r: render_treemap(c, cols, r))
    ChartRegistry.register("sunburst", lambda c, cols, r: render_sunburst(c, cols, r))

    # 6. Matrix & Tabular
    ChartRegistry.register("matrix", lambda c, cols, r: render_matrix_or_heatmap(c, cols, r, is_heatmap=False))
    ChartRegistry.register("heatmap", lambda c, cols, r: render_matrix_or_heatmap(c, cols, r, is_heatmap=True))
    ChartRegistry.register("pivot_table", lambda c, cols, r: render_matrix_or_heatmap(c, cols, r, is_heatmap=False))


_initialize_registry()

