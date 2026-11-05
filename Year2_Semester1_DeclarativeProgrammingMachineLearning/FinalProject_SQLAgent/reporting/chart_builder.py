"""Vector chart builder entry point delegating to the centralized ChartRegistry."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from reportlab.graphics.shapes import Drawing

from .chart_registry import (
    LIGHT_PALETTE,
    PALETTE,
    ChartRegistry,
    _empty_chart_drawing,
    _format_val,
    _safe_float,
    extract_chart_data,
)
from .report_spec import ChartConfiguration, ChartType


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
    return ChartRegistry.render(config, columns, rows, width=width, height=height)
