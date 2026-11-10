"""Structured specification models for dynamic multi-component report generation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ChartType(str, Enum):
    # Comparison
    BAR = "bar"
    VERTICAL_BAR = "bar"
    GROUPED_BAR = "grouped_bar"
    STACKED_BAR = "stacked_bar"
    HORIZONTAL_BAR = "horizontal_bar"
    GROUPED_HORIZONTAL_BAR = "grouped_horizontal_bar"
    STACKED_HORIZONTAL_BAR = "stacked_horizontal_bar"

    # Trend & Time-Series
    LINE = "line"
    MULTI_LINE = "multi_line"
    HISTORICAL = "historical"
    HISTORICAL_LINE = "historical"
    AREA = "area"
    STACKED_AREA = "stacked_area"

    # Distribution
    PIE = "pie"
    DONUT = "donut"
    HISTOGRAM = "histogram"
    DENSITY = "density"
    BOX_PLOT = "box_plot"
    VIOLIN = "violin"

    # Relationship
    SCATTER = "scatter"
    BUBBLE = "bubble"
    CORRELATION_HEATMAP = "correlation_heatmap"

    # Hierarchical
    TREEMAP = "treemap"
    SUNBURST = "sunburst"

    # Matrix & Tabular
    MATRIX = "matrix"
    HEATMAP = "heatmap"
    PIVOT_TABLE = "pivot_table"


@dataclass
class ChartConfiguration:
    """Configuration for a vector data chart in a report."""

    chart_type: str = ChartType.BAR.value
    title: str = ""
    subtitle: str = ""
    x_axis: str = ""
    y_axis: str | list[str] = ""
    category_dimension: str | None = None
    numerical_measure: str | None = None
    series: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    legend: bool = True
    format: str = "number"  # "currency", "percentage", "number", "integer"
    dataset_id: str | None = None
    width: float = 460.0
    height: float = 190.0
    date_grouping: str | None = None  # "day", "week", "month", "quarter", "year"
    aggregation: str | None = None  # "sum", "avg", "count", "min", "max"
    sorting: str | None = None  # "asc", "desc"
    data_labels: bool = False
    chart_options: dict[str, Any] = field(default_factory=dict)

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
        subtitle: str = "",
        category_dimension: str | None = None,
        numerical_measure: str | None = None,
        date_grouping: str | None = None,
        aggregation: str | None = None,
        sorting: str | None = None,
        data_labels: bool = False,
        chart_options: dict[str, Any] | None = None,
        x_column: str = "",
        y_columns: str | list[str] = "",
        series_column: str = "",
        **kwargs: Any,
    ) -> None:
        self.chart_type = (
            chart_type.value if isinstance(chart_type, ChartType) else str(chart_type).lower()
        )
        self.title = title
        self.subtitle = subtitle
        self.category_dimension = category_dimension
        self.numerical_measure = numerical_measure
        self.x_axis = x_axis or x_column or category_dimension or ""
        self.y_axis = y_axis or y_columns or (numerical_measure if numerical_measure else "")
        self.series = series or ([series_column] if series_column else [])
        self.labels = labels or []
        self.legend = legend
        self.format = format
        self.dataset_id = dataset_id
        self.width = width
        self.height = height
        self.date_grouping = date_grouping
        self.aggregation = aggregation
        self.sorting = sorting
        self.data_labels = data_labels
        self.chart_options = dict(chart_options or {})

    @property
    def x_column(self) -> str:
        return self.x_axis or self.category_dimension or ""

    @property
    def y_columns(self) -> list[str]:
        if isinstance(self.y_axis, list):
            return self.y_axis
        if self.y_axis:
            return [self.y_axis]
        if self.numerical_measure:
            return [self.numerical_measure]
        return []

    @classmethod
    def from_dict(cls, data: Any) -> "ChartConfiguration":
        if isinstance(data, str):
            chart_str = data.lower()
            ct = "vertical_bar"
            if any(w in chart_str for w in ["bar", "column"]):
                ct = "vertical_bar"
            elif any(w in chart_str for w in ["pie", "donut", "distribution"]):
                ct = "pie"
            elif any(w in chart_str for w in ["matrix", "heatmap"]):
                ct = "matrix"
            elif any(w in chart_str for w in ["line", "trend"]):
                ct = "historical_line"
            data = {"chart_type": ct, "title": data.strip()}
        elif not isinstance(data, Mapping):
            data = {}

        t = str(data.get("chart_type") or data.get("type") or "bar").lower()
        x_val = str(
            data.get("x_axis")
            or data.get("x")
            or data.get("x_column")
            or data.get("category_dimension")
            or ""
        )
        y_val = (
            data.get("y_axis")
            or data.get("y")
            or data.get("y_columns")
            or data.get("numerical_measure")
            or ""
        )
        s_val = list(
            data.get("series") or ([data["series_column"]] if "series_column" in data else [])
        )
        return cls(
            chart_type=t,
            title=str(data.get("title") or ""),
            subtitle=str(data.get("subtitle") or ""),
            x_axis=x_val,
            y_axis=y_val,
            category_dimension=data.get("category_dimension"),
            numerical_measure=data.get("numerical_measure"),
            series=s_val,
            labels=list(data.get("labels") or []),
            legend=bool(data.get("legend", True)),
            format=str(data.get("format") or "number"),
            dataset_id=data.get("dataset_id"),
            width=float(data.get("width", 460.0)),
            height=float(data.get("height", 190.0)),
            date_grouping=data.get("date_grouping"),
            aggregation=data.get("aggregation"),
            sorting=data.get("sorting"),
            data_labels=bool(data.get("data_labels", False)),
            chart_options=dict(data.get("chart_options") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "x_column": self.x_column,
            "y_columns": self.y_columns,
            "category_dimension": self.category_dimension,
            "numerical_measure": self.numerical_measure,
            "series": self.series,
            "labels": self.labels,
            "legend": self.legend,
            "format": self.format,
            "dataset_id": self.dataset_id,
            "width": self.width,
            "height": self.height,
            "date_grouping": self.date_grouping,
            "aggregation": self.aggregation,
            "sorting": self.sorting,
            "data_labels": self.data_labels,
            "chart_options": self.chart_options,
        }


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
    def from_dict(cls, data: Any) -> "TableConfiguration":
        if isinstance(data, (list, tuple)):
            return cls(columns=[str(c) for c in data])
        if not isinstance(data, Mapping):
            return cls()
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
    def from_dict(cls, data: Any) -> "ReportComponent":
        if isinstance(data, str):
            return cls(component_type="text", title="", description="", content=data)
        if not isinstance(data, Mapping):
            return cls(component_type="text", title=str(data), description="", content="")
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
    def from_dict(cls, data: Any) -> "ReportSection":
        if isinstance(data, str):
            return cls(title=data, description="", components=[])
        if not isinstance(data, Mapping):
            return cls(title=str(data or "Section"), description="", components=[])
        raw_comps = data.get("components") or []
        components = [ReportComponent.from_dict(c) for c in raw_comps if isinstance(c, (dict, Mapping, str))]
        return cls(
            title=str(data.get("title") or "Section"),
            description=str(data.get("description") or ""),
            components=components,
        )


@dataclass
class ReportSpecification:
    """Dynamic, validated multi-component report blueprint capturing user analytical intent."""

    title: str
    subtitle: str = ""
    executive_summary: str = ""
    kpis: list[dict[str, Any]] = field(default_factory=list)
    comparison_kpis: list[dict[str, Any]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    datasets: dict[str, dict[str, Any]] = field(default_factory=dict)
    include_sql: bool = False
    sql_queries: list[dict[str, str]] = field(default_factory=list)  # [{"query": "...", "purpose": "..."}]
    page_size: str = "A4"

    # Explicit analytical intent & period separation fields
    requested_period: str = ""
    period_boundaries: dict[str, str] = field(default_factory=dict)
    reporting_frequency: str = "monthly"
    historical_comparison_period: str = ""
    comparison_period_boundaries: dict[str, str] = field(default_factory=dict)
    available_data_range: dict[str, str] = field(default_factory=dict)
    actual_data_period: str = ""
    requested_period_has_data: bool = True
    requested_period_record_count: int = 0
    requested_metrics: list[str] = field(default_factory=list)
    requested_dimensions: list[str] = field(default_factory=list)
    required_breakdowns: list[str] = field(default_factory=list)
    requested_chart_types: list[str] = field(default_factory=list)
    required_tables: list[str] = field(default_factory=list)
    currency_format: str = "USD ($#,##0.00)"
    numeric_formatting: dict[str, str] = field(
        default_factory=lambda: {
            "currency": "${:,.2f}",
            "integer": "{:,}",
            "percentage": "{:.1f}%",
        }
    )
    missing_data_policy: str = "explicit_no_data_with_labeled_historical_comparison"
    output_format: str = "PDF"
    data_availability_notes: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    omitted_analyses: list[str] = field(default_factory=list)

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
        comparison_kpis: list[dict[str, Any]] | None = None,
        requested_period: str = "",
        period_boundaries: dict[str, str] | None = None,
        reporting_frequency: str = "monthly",
        historical_comparison_period: str = "",
        comparison_period_boundaries: dict[str, str] | None = None,
        available_data_range: dict[str, str] | None = None,
        actual_data_period: str = "",
        requested_period_has_data: bool = True,
        requested_period_record_count: int = 0,
        requested_metrics: list[str] | None = None,
        requested_dimensions: list[str] | None = None,
        required_breakdowns: list[str] | None = None,
        requested_chart_types: list[str] | None = None,
        required_tables: list[str] | None = None,
        currency_format: str = "USD ($#,##0.00)",
        numeric_formatting: dict[str, str] | None = None,
        missing_data_policy: str = "explicit_no_data_with_labeled_historical_comparison",
        output_format: str = "PDF",
        data_availability_notes: list[str] | None = None,
        validation_warnings: list[str] | None = None,
        omitted_analyses: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.executive_summary = executive_summary
        self.kpis = kpis or []
        self.comparison_kpis = comparison_kpis or []
        self.findings = findings or key_findings or []
        self.sections = sections or []
        self.datasets = datasets or {}
        self.include_sql = include_sql
        self.sql_queries = sql_queries or []
        self.page_size = page_size
        self.requested_period = requested_period
        self.period_boundaries = period_boundaries or {}
        self.reporting_frequency = reporting_frequency
        self.historical_comparison_period = historical_comparison_period
        self.comparison_period_boundaries = comparison_period_boundaries or {}
        self.available_data_range = available_data_range or {}
        self.actual_data_period = actual_data_period
        self.requested_period_has_data = requested_period_has_data
        self.requested_period_record_count = requested_period_record_count
        self.requested_metrics = requested_metrics or []
        self.requested_dimensions = requested_dimensions or []
        self.required_breakdowns = required_breakdowns or []
        self.requested_chart_types = requested_chart_types or []
        self.required_tables = required_tables or []
        self.currency_format = currency_format
        self.numeric_formatting = numeric_formatting or {
            "currency": "${:,.2f}",
            "integer": "{:,}",
            "percentage": "{:.1f}%",
        }
        self.missing_data_policy = missing_data_policy
        self.output_format = output_format
        self.data_availability_notes = data_availability_notes or []
        self.validation_warnings = validation_warnings or []
        self.omitted_analyses = omitted_analyses or []

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_user_intent(
        cls,
        user_request: str,
        title: str = "",
        description: str = "",
        reference_date: Any = None,
        output_format: str = "PDF",
    ) -> "ReportSpecification":
        """Construct a structured ReportSpecification directly from natural-language user intent."""
        from reporting.date_utils import resolve_requested_period

        combined = f"{user_request or ''} {title or ''} {description or ''}".lower()
        period_obj = resolve_requested_period(
            user_request=user_request,
            title=title,
            reference_date=reference_date,
        )

        req_period_label = period_obj.period_label if period_obj else ""
        boundaries: dict[str, str] = {}
        if period_obj:
            boundaries = {
                "start_date": period_obj.start_date_str,
                "end_date_exclusive": period_obj.end_date_str,
                "interval": f"[{period_obj.start_date_str}, {period_obj.end_date_str})",
                "sql_filter": period_obj.sql_filter_clause,
            }

        # Frequency detection
        freq = "monthly"
        if "daily" in combined or "by day" in combined:
            freq = "daily"
        elif "quarter" in combined or "quarterly" in combined:
            freq = "quarterly"
        elif "annual" in combined or "yearly" in combined:
            freq = "annual"

        # Metrics detection
        metrics: list[str] = []
        if any(k in combined for k in ("order", "orders", "volume")):
            metrics.append("orders")
        if any(k in combined for k in ("transaction", "transactions", "payment")):
            metrics.append("transactions")
        if any(k in combined for k in ("sale", "sales", "subtotal", "gross")):
            metrics.append("sales")
        if any(k in combined for k in ("revenue", "total_amount", "income", "net")):
            metrics.append("revenue")
        if any(k in combined for k in ("aov", "average order value", "avg order")):
            metrics.append("avg_order_value")
        if not metrics:
            metrics = ["orders", "sales", "revenue"]

        # Dimensions & breakdowns detection
        dimensions: list[str] = ["month"]
        breakdowns: list[str] = ["historical_monthly"]
        if any(k in combined for k in ("channel", "channels", "distribution", "pie", "matrix", "performance", "sales report")):
            if "channel" not in dimensions:
                dimensions.append("channel")
            if "channel_breakdown" not in breakdowns:
                breakdowns.append("channel_breakdown")
        if any(k in combined for k in ("payment", "method", "transactions", "distribution", "pie", "sales report")):
            if "payment_method" not in dimensions:
                dimensions.append("payment_method")
            if "payment_method_breakdown" not in breakdowns:
                breakdowns.append("payment_method_breakdown")
        if any(k in combined for k in ("status", "fulfillment", "delivered", "cancelled", "distribution", "pie", "sales report")):
            if "order_status" not in dimensions:
                dimensions.append("order_status")
            if "order_status_breakdown" not in breakdowns:
                breakdowns.append("order_status_breakdown")
        if any(k in combined for k in ("category", "categories", "product")):
            if "category" not in dimensions:
                dimensions.append("category")
            if "category_breakdown" not in breakdowns:
                breakdowns.append("category_breakdown")

        # Requested chart types
        chart_types: list[str] = []
        if any(k in combined for k in ("bar", "historical", "comparison")):
            chart_types.append("vertical_bar")
        if any(k in combined for k in ("line", "trend", "historical")):
            chart_types.append("historical_line")
        if any(k in combined for k in ("pie", "donut", "distribution", "share")):
            chart_types.append("pie")
        if any(k in combined for k in ("matrix", "heatmap", "crosstab", "pivot")):
            chart_types.append("matrix")
        if not chart_types:
            chart_types = ["vertical_bar", "pie"]

        # Required tables
        req_tables = list(breakdowns)

        resolved_title = title or (
            f"{req_period_label} Sales & Performance Report"
            if req_period_label
            else "Executive Analytical Report"
        )

        return cls(
            title=resolved_title,
            subtitle=description or "",
            requested_period=req_period_label,
            period_boundaries=boundaries,
            reporting_frequency=freq,
            requested_metrics=metrics,
            requested_dimensions=dimensions,
            required_breakdowns=breakdowns,
            requested_chart_types=chart_types,
            required_tables=req_tables,
            output_format=output_format.upper(),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportSpecification":
        raw_sections = data.get("sections") or []
        sections = [ReportSection.from_dict(s) for s in raw_sections if isinstance(s, dict)]

        raw_kpis = data.get("kpis") or []
        kpis = [dict(k) for k in raw_kpis if isinstance(k, dict)]

        raw_comp_kpis = data.get("comparison_kpis") or []
        comparison_kpis = [dict(k) for k in raw_comp_kpis if isinstance(k, dict)]

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
            comparison_kpis=comparison_kpis,
            findings=findings,
            sections=sections,
            datasets=datasets,
            include_sql=bool(data.get("include_sql", False)),
            sql_queries=sql_queries,
            page_size=str(data.get("page_size") or "A4"),
            requested_period=str(data.get("requested_period") or ""),
            period_boundaries=dict(data.get("period_boundaries") or {}),
            reporting_frequency=str(data.get("reporting_frequency") or "monthly"),
            historical_comparison_period=str(data.get("historical_comparison_period") or ""),
            comparison_period_boundaries=dict(data.get("comparison_period_boundaries") or {}),
            available_data_range=dict(data.get("available_data_range") or {}),
            actual_data_period=str(data.get("actual_data_period") or ""),
            requested_period_has_data=bool(data.get("requested_period_has_data", True)),
            requested_period_record_count=int(data.get("requested_period_record_count", 0)),
            requested_metrics=list(data.get("requested_metrics") or []),
            requested_dimensions=list(data.get("requested_dimensions") or []),
            required_breakdowns=list(data.get("required_breakdowns") or []),
            requested_chart_types=list(data.get("requested_chart_types") or []),
            required_tables=list(data.get("required_tables") or []),
            currency_format=str(data.get("currency_format") or "USD ($#,##0.00)"),
            numeric_formatting=dict(data.get("numeric_formatting") or {}),
            missing_data_policy=str(
                data.get("missing_data_policy") or "explicit_no_data_with_labeled_historical_comparison"
            ),
            output_format=str(data.get("output_format") or "PDF"),
            data_availability_notes=list(data.get("data_availability_notes") or []),
            validation_warnings=list(data.get("validation_warnings") or []),
            omitted_analyses=list(data.get("omitted_analyses") or []),
        )
