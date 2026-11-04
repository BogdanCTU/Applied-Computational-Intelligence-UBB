"""Structured specification models for dynamic multi-component report generation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ChartType(str, Enum):
    LINE = "line"
    MULTI_LINE = "multi_line"
    HISTORICAL = "historical"
    HISTORICAL_LINE = "historical"
    BAR = "bar"
    VERTICAL_BAR = "bar"
    GROUPED_BAR = "grouped_bar"
    STACKED_BAR = "stacked_bar"
    HORIZONTAL_BAR = "horizontal_bar"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    SCATTER = "scatter"


@dataclass
class ChartConfiguration:
    """Configuration for a vector data chart in a report."""

    chart_type: str = ChartType.BAR.value
    title: str = ""
    x_axis: str = ""
    y_axis: str | list[str] = ""
    series: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    legend: bool = True
    format: str = "number"  # "currency", "percentage", "number", "integer"
    dataset_id: str | None = None
    width: float = 460.0
    height: float = 190.0

    def __init__(
        self,
        chart_type: str | ChartType = ChartType.BAR.value,
        title: str = "",
        x_axis: str = "",
        y_axis: str | list[str] = "",
        series: list[str] | None = None,
        labels: list[str] | None = None,
        legend: bool = True,
        format: str = "number",
        dataset_id: str | None = None,
        width: float = 460.0,
        height: float = 190.0,
        *,
        x_column: str = "",
        y_columns: str | list[str] = "",
        series_column: str = "",
        **kwargs: Any,
    ) -> None:
        self.chart_type = (
            chart_type.value if isinstance(chart_type, ChartType) else str(chart_type).lower()
        )
        self.title = title
        self.x_axis = x_axis or x_column
        self.y_axis = y_axis or y_columns
        self.series = series or ([series_column] if series_column else [])
        self.labels = labels or []
        self.legend = legend
        self.format = format
        self.dataset_id = dataset_id
        self.width = width
        self.height = height

    @property
    def x_column(self) -> str:
        return self.x_axis

    @property
    def y_columns(self) -> list[str]:
        if isinstance(self.y_axis, list):
            return self.y_axis
        return [self.y_axis] if self.y_axis else []

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChartConfiguration":
        t = str(data.get("chart_type") or data.get("type") or "bar").lower()
        x_val = str(data.get("x_axis") or data.get("x") or data.get("x_column") or "")
        y_val = data.get("y_axis") or data.get("y") or data.get("y_columns") or ""
        s_val = list(
            data.get("series") or ([data["series_column"]] if "series_column" in data else [])
        )
        return cls(
            chart_type=t,
            title=str(data.get("title") or ""),
            x_axis=x_val,
            y_axis=y_val,
            series=s_val,
            labels=list(data.get("labels") or []),
            legend=bool(data.get("legend", True)),
            format=str(data.get("format") or "number"),
            dataset_id=data.get("dataset_id"),
            width=float(data.get("width", 460.0)),
            height=float(data.get("height", 190.0)),
        )


@dataclass
class TableConfiguration:
    """Configuration for a tabular component in a report."""

    title: str = ""
    columns: list[str] = field(default_factory=list)
    sort_by: str | None = None
    limit: int | None = None
    show_totals: bool = False
    formatting: dict[str, str] = field(default_factory=dict)  # col -> "currency" | "percent" | "number"
    dataset_id: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TableConfiguration":
        return cls(
            title=str(data.get("title") or ""),
            columns=list(data.get("columns") or []),
            sort_by=data.get("sort_by"),
            limit=int(data["limit"]) if data.get("limit") is not None else None,
            show_totals=bool(data.get("show_totals", False)),
            formatting=dict(data.get("formatting") or {}),
            dataset_id=data.get("dataset_id"),
        )


@dataclass
class ReportComponent:
    """Individual visual or tabular component inside a report section."""

    component_type: str  # "chart", "table", "kpis", "findings", "text"
    title: str = ""
    description: str = ""
    dataset_id: str | None = None
    chart_config: ChartConfiguration | None = None
    table_config: TableConfiguration | None = None
    content: Any = None

    def __init__(
        self,
        component_type: str,
        title: str = "",
        description: str = "",
        dataset_id: str | None = None,
        chart_config: ChartConfiguration | None = None,
        table_config: TableConfiguration | None = None,
        content: Any = None,
        *,
        dataset_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.component_type = component_type
        self.title = title
        self.description = description
        self.dataset_id = dataset_id or dataset_name
        self.chart_config = chart_config
        self.table_config = table_config
        self.content = content

    @property
    def dataset_name(self) -> str | None:
        return self.dataset_id

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportComponent":
        c_type = str(data.get("component_type") or data.get("type") or "text").lower()
        chart_cfg = None
        if c_type == "chart" or "chart_config" in data or "chart_type" in data:
            chart_raw = data.get("chart_config") or data
            chart_cfg = ChartConfiguration.from_dict(chart_raw)
            c_type = "chart"

        table_cfg = None
        if c_type == "table" or "table_config" in data or "columns" in data:
            table_raw = data.get("table_config") or data
            table_cfg = TableConfiguration.from_dict(table_raw)
            if c_type != "chart":
                c_type = "table"

        return cls(
            component_type=c_type,
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            dataset_id=data.get("dataset_id") or data.get("dataset_name"),
            chart_config=chart_cfg,
            table_config=table_cfg,
            content=data.get("content"),
        )


@dataclass
class ReportSection:
    """Topical section grouping charts, tables, and narrative paragraphs."""

    title: str
    description: str = ""
    components: list[ReportComponent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportSection":
        raw_comps = data.get("components") or []
        components = [ReportComponent.from_dict(c) for c in raw_comps if isinstance(c, dict)]
        return cls(
            title=str(data.get("title") or "Section"),
            description=str(data.get("description") or ""),
            components=components,
        )


@dataclass
class ReportSpecification:
    """Dynamic, validated multi-component report blueprint."""

    title: str
    subtitle: str = ""
    executive_summary: str = ""
    kpis: list[dict[str, Any]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    datasets: dict[str, dict[str, Any]] = field(default_factory=dict)
    include_sql: bool = False
    sql_queries: list[dict[str, str]] = field(default_factory=list)  # [{"query": "...", "purpose": "..."}]
    page_size: str = "A4"

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        executive_summary: str = "",
        kpis: list[dict[str, Any]] | None = None,
        findings: list[str] | None = None,
        sections: list[ReportSection] | None = None,
        datasets: dict[str, dict[str, Any]] | None = None,
        include_sql: bool = False,
        sql_queries: list[dict[str, str]] | None = None,
        page_size: str = "A4",
        *,
        key_findings: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.executive_summary = executive_summary
        self.kpis = kpis or []
        self.findings = findings or key_findings or []
        self.sections = sections or []
        self.datasets = datasets or {}
        self.include_sql = include_sql
        self.sql_queries = sql_queries or []
        self.page_size = page_size

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportSpecification":
        raw_sections = data.get("sections") or []
        sections = [ReportSection.from_dict(s) for s in raw_sections if isinstance(s, dict)]

        raw_kpis = data.get("kpis") or []
        kpis = [dict(k) for k in raw_kpis if isinstance(k, dict)]

        raw_findings = data.get("findings") or []
        findings = [str(f) for f in raw_findings if f]

        raw_datasets = data.get("datasets") or {}
        datasets = {str(k): dict(v) for k, v in raw_datasets.items() if isinstance(v, dict)}

        raw_sql = data.get("sql_queries") or []
        sql_queries = [dict(s) for s in raw_sql if isinstance(s, dict)]

        return cls(
            title=str(data.get("title") or "Executive Analytical Report"),
            subtitle=str(data.get("subtitle") or ""),
            executive_summary=str(data.get("executive_summary") or data.get("summary") or ""),
            kpis=kpis,
            findings=findings,
            sections=sections,
            datasets=datasets,
            include_sql=bool(data.get("include_sql", False)),
            sql_queries=sql_queries,
            page_size=str(data.get("page_size") or "A4"),
        )
