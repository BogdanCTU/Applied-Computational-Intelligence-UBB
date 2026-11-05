"""Deterministic Single Source of Truth architecture and validated chart specifications.

Enforces that the executed SQL query result is the authoritative dataset
for all reporting components: KPIs, tables, charts, summaries, PDF and CSV.
Python performs all deterministic calculations, data transformations,
type validations, and consistency checks.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator

log = logging.getLogger(__name__)

# Supported chart types
SupportedChartType = Literal[
    "bar",
    "vertical_bar",
    "horizontal_bar",
    "grouped_bar",
    "stacked_bar",
    "line",
    "multi_line",
    "historical",
    "historical_line",
    "area",
    "stacked_area",
    "pie",
    "donut",
    "scatter",
    "bubble",
    "matrix",
    "heatmap",
    "histogram",
    "density",
    "box_plot",
    "violin",
    "treemap",
]

AggregationMethod = Literal["sum", "avg", "count", "min", "max", "none"]
SortingOrder = Literal["asc", "desc", "none"]


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling strings with currency symbols and commas."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return default
        return float(val)
    try:
        cleaned = str(val).replace("$", "").replace(",", "").replace("%", "").strip()
        f = float(cleaned)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def is_numeric_value(val: Any) -> bool:
    """Check if value is numeric or can be safely parsed as a finite float."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return not (math.isnan(val) or math.isinf(val))
    if isinstance(val, str):
        cleaned = val.replace("$", "").replace(",", "").replace("%", "").strip()
        if not cleaned:
            return False
        try:
            f = float(cleaned)
            return not (math.isnan(f) or math.isinf(f))
        except ValueError:
            return False
    return False


class ChartSpecification(BaseModel):
    """Pydantic validated vector chart specification.
    
    The LLM generates chart configuration only; Python validates against actual
    SQL result columns and transforms data deterministically.
    """

    model_config = ConfigDict(extra="ignore")

    title: str = Field(default="Chart", description="Descriptive title of the chart")
    chart_type: str = Field(default="bar", description="Chart visualization type")
    x_axis: str = Field(default="", description="Column name for categories / X-axis")
    y_axis: str | list[str] = Field(default="", description="Column name(s) for metric / Y-axis")
    aggregation_method: AggregationMethod | None = Field(
        default=None, description="Deterministic aggregation function"
    )
    sorting: SortingOrder | None = Field(default=None, description="Optional sort order")
    grouping: str | None = Field(default=None, description="Optional secondary grouping column")
    chart_settings: dict[str, Any] = Field(default_factory=dict, description="Chart options")

    @field_validator("chart_type", mode="before")
    @classmethod
    def _normalize_chart_type(cls, v: Any) -> str:
        s = str(v or "bar").lower().strip()
        mapping = {
            "column": "bar",
            "vertical_bar": "bar",
            "historical_bar": "bar",
            "trend": "line",
            "historical_line": "line",
            "timeseries": "line",
            "time_series": "line",
            "distribution": "pie",
            "donut": "pie",
            "crosstab": "matrix",
        }
        return mapping.get(s, s)

    @field_validator("aggregation_method", mode="before")
    @classmethod
    def _normalize_aggregation(cls, v: Any) -> str | None:
        if not v:
            return None
        s = str(v).lower().strip()
        if s in {"avg", "average", "mean"}:
            return "avg"
        if s in {"sum", "total"}:
            return "sum"
        if s in {"count", "total_records"}:
            return "count"
        if s in {"min", "minimum"}:
            return "min"
        if s in {"max", "maximum"}:
            return "max"
        if s in {"none", "raw"}:
            return "none"
        return "sum"

    @field_validator("sorting", mode="before")
    @classmethod
    def _normalize_sorting(cls, v: Any) -> str | None:
        if not v:
            return None
        s = str(v).lower().strip()
        if s in {"asc", "ascending"}:
            return "asc"
        if s in {"desc", "descending"}:
            return "desc"
        return "none"

    @property
    def primary_y_axis(self) -> str:
        if isinstance(self.y_axis, list):
            return self.y_axis[0] if self.y_axis else ""
        return str(self.y_axis or "")

    @property
    def all_y_axes(self) -> list[str]:
        if isinstance(self.y_axis, list):
            return [str(c) for c in self.y_axis if str(c).strip()]
        if self.y_axis:
            return [str(self.y_axis).strip()]
        return []


@dataclass
class TransformedChartData:
    """Authoritative, validated data ready for ReportLab vector rendering."""

    title: str
    chart_type: str
    x_axis: str
    y_axes: list[str]
    categories: list[str]
    data_series: list[list[float]]
    series_names: list[str]
    percentages: list[float] | None = None
    is_valid: bool = True
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)


class CanonicalSQLDataset:
    """Authoritative, single source of truth for all reporting components."""

    def __init__(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any] | Mapping[str, Any]],
        *,
        name: str = "dataset_1",
        sql_query: str = "",
    ) -> None:
        self.name = name
        self.sql_query = sql_query or ""
        self.columns = [str(c) for c in (columns or [])]
        
        # Normalize rows to list of lists and list of dicts
        self._dict_rows: list[dict[str, Any]] = []
        self._table_rows: list[list[Any]] = []

        if rows:
            first = rows[0]
            if isinstance(first, Mapping):
                for r in rows:
                    d = dict(r)  # type: ignore[arg-type]
                    self._dict_rows.append(d)
                    self._table_rows.append([d.get(c) for c in self.columns])
            else:
                for r in rows:
                    row_list = list(r)  # type: ignore[arg-type]
                    self._table_rows.append(row_list)
                    d = {
                        self.columns[i]: (row_list[i] if i < len(row_list) else None)
                        for i in range(len(self.columns))
                    }
                    self._dict_rows.append(d)

        # Infer column data types
        self.column_types: dict[str, str] = {}
        for c in self.columns:
            vals = [r.get(c) for r in self._dict_rows if r.get(c) is not None]
            if not vals:
                self.column_types[c] = "unknown"
            elif all(is_numeric_value(v) for v in vals[:20]):
                self.column_types[c] = "numeric"
            elif any(k in c.lower() for k in ["date", "time", "month", "year", "day"]):
                self.column_types[c] = "date"
            else:
                self.column_types[c] = "text"

    @property
    def is_empty(self) -> bool:
        return len(self._dict_rows) == 0

    @property
    def row_count(self) -> int:
        return len(self._dict_rows)

    @property
    def dict_rows(self) -> list[dict[str, Any]]:
        return list(self._dict_rows)

    @property
    def table_rows(self) -> list[list[Any]]:
        return list(self._table_rows)

    def get_column_values(self, column_name: str) -> list[Any]:
        if column_name not in self.columns:
            return []
        return [r.get(column_name) for r in self._dict_rows]

    def get_numeric_column_values(self, column_name: str) -> list[float]:
        if column_name not in self.columns:
            return []
        return [safe_float(r.get(column_name), 0.0) for r in self._dict_rows]

    def compute_deterministic_kpis(self) -> list[dict[str, Any]]:
        """Calculate verified KPI cards directly from the authoritative dataset."""
        if self.is_empty:
            return []

        kpis: list[dict[str, Any]] = []
        cols_lower = [c.lower() for c in self.columns]

        # 1. Total Orders
        order_col = next(
            (
                c
                for c, cl in zip(self.columns, cols_lower)
                if any(k in cl for k in ["order_count", "total_orders", "orders_count", "num_orders"])
                or cl == "orders"
            ),
            None,
        )
        if order_col:
            total_orders = sum(safe_float(r.get(order_col), 0.0) for r in self._dict_rows)
            kpis.append({
                "label": "Total Orders",
                "value": f"{int(total_orders):,}",
                "note": f"Summed from {order_col}",
            })
        elif "order_id" in cols_lower:
            # Count distinct orders
            oid_col = self.columns[cols_lower.index("order_id")]
            unique_orders = len({r.get(oid_col) for r in self._dict_rows if r.get(oid_col) is not None})
            kpis.append({
                "label": "Total Orders",
                "value": f"{unique_orders:,}",
                "note": "Distinct count",
            })
        elif self.row_count > 0 and not any("order" in cl for cl in cols_lower):
            kpis.append({
                "label": "Total Records",
                "value": f"{self.row_count:,}",
                "note": "Dataset row count",
            })

        # 2. Sales Volume
        sales_col = next(
            (
                c
                for c, cl in zip(self.columns, cols_lower)
                if any(k in cl for k in ["sales_volume", "gross_sales", "subtotal", "gross_amount", "gross_item_sales"])
                or (("sales" in cl or "sale" in cl) and "net" not in cl and "revenue" not in cl)
            ),
            None,
        )
        if sales_col:
            total_sales = sum(safe_float(r.get(sales_col), 0.0) for r in self._dict_rows)
            kpis.append({
                "label": "Sales Volume",
                "value": f"${total_sales:,.2f}",
                "note": f"Calculated from {sales_col}",
            })

        # 3. Total Revenue
        rev_col = next(
            (
                c
                for c, cl in zip(self.columns, cols_lower)
                if any(k in cl for k in ["total_revenue", "net_revenue", "revenue", "total_amount", "net_amount", "captured_revenue"])
                or (cl == "amount" and c != sales_col)
                or ("revenue" in cl and c != sales_col)
            ),
            None,
        )
        if not rev_col and not sales_col:
            # Fallback if only 'amount' or 'total' is available
            rev_col = next(
                (
                    c
                    for c, cl in zip(self.columns, cols_lower)
                    if any(k in cl for k in ["amount", "total", "price", "subtotal"])
                ),
                None,
            )
        if rev_col and rev_col != sales_col:
            total_rev = sum(safe_float(r.get(rev_col), 0.0) for r in self._dict_rows)
            kpis.append({
                "label": "Total Revenue",
                "value": f"${total_rev:,.2f}",
                "note": f"Calculated from {rev_col}",
            })

        # 4. Transactions
        txn_col = next(
            (
                c
                for c, cl in zip(self.columns, cols_lower)
                if any(k in cl for k in ["transaction_count", "total_transactions", "transactions_count", "transactions", "num_transactions"])
            ),
            None,
        )
        if txn_col:
            total_txn = sum(safe_float(r.get(txn_col), 0.0) for r in self._dict_rows)
            kpis.append({
                "label": "Transactions",
                "value": f"{int(total_txn):,}",
                "note": f"Summed from {txn_col}",
            })
        elif "payment_id" in cols_lower or "transaction_id" in cols_lower:
            pid_col = self.columns[cols_lower.index("payment_id" if "payment_id" in cols_lower else "transaction_id")]
            unique_txns = len({r.get(pid_col) for r in self._dict_rows if r.get(pid_col) is not None})
            kpis.append({
                "label": "Transactions",
                "value": f"{unique_txns:,}",
                "note": "Distinct count",
            })

        # 4. Average Order Value (AOV)
        if len(kpis) >= 2:
            rev_kpi = next((k for k in kpis if "Revenue" in k["label"]), None) or next((k for k in kpis if "Sales" in k["label"]), None)
            ord_kpi = next((k for k in kpis if "Order" in k["label"]), None)
            if rev_kpi and ord_kpi:
                try:
                    r_val = float(rev_kpi["value"].replace("$", "").replace(",", ""))
                    o_val = float(ord_kpi["value"].replace(",", ""))
                    if o_val > 0:
                        aov = r_val / o_val
                        kpis.append({
                            "label": "Average Order Value",
                            "value": f"${aov:,.2f}",
                            "note": "Revenue / Orders",
                        })
                except (ValueError, TypeError):
                    pass

        return kpis

    def extract_and_transform_chart(
        self,
        spec: ChartSpecification,
    ) -> TransformedChartData:
        """Extract and deterministically transform chart data according to specification."""
        warnings: list[str] = []

        if self.is_empty:
            return TransformedChartData(
                title=spec.title,
                chart_type=spec.chart_type,
                x_axis=spec.x_axis,
                y_axes=spec.all_y_axes,
                categories=[],
                data_series=[],
                series_names=[],
                is_valid=False,
                error_message="Dataset is empty: no rows returned from query.",
            )

        # 1. Resolve X-Axis Column
        x_col = spec.x_axis
        if not x_col:
            cand_x = next(
                (c for c in self.columns if self.column_types.get(c) in {"date", "text"}),
                self.columns[0] if self.columns else "",
            )
            if not cand_x:
                return TransformedChartData(
                    title=spec.title,
                    chart_type=spec.chart_type,
                    x_axis="",
                    y_axes=[],
                    categories=[],
                    data_series=[],
                    series_names=[],
                    is_valid=False,
                    error_message=f"No suitable X-axis column found in dataset columns: {self.columns}",
                )
            warnings.append(f"X-axis column defaulted to '{cand_x}'")
            x_col = cand_x
        elif x_col not in self.columns:
            return TransformedChartData(
                title=spec.title,
                chart_type=spec.chart_type,
                x_axis=x_col,
                y_axes=[],
                categories=[],
                data_series=[],
                series_names=[],
                is_valid=False,
                error_message=f"X-axis column '{spec.x_axis}' not found in dataset columns: {self.columns}",
            )

        # 2. Resolve Y-Axis Column(s)
        y_cols = [c for c in spec.all_y_axes if c in self.columns]
        if not y_cols:
            # Fallback to numeric columns
            y_cols = [c for c in self.columns if c != x_col and self.column_types.get(c) == "numeric"]
            if not y_cols and len(self.columns) > 1:
                y_cols = [c for c in self.columns if c != x_col][:1]

        for y in y_cols:
            if self.column_types.get(y) == "text":
                warnings.append(f"Y-axis column '{y}' contains non-numeric text data; values converted to numbers.")

        if not y_cols and spec.aggregation_method != "count":
            return TransformedChartData(
                title=spec.title,
                chart_type=spec.chart_type,
                x_axis=x_col,
                y_axes=[],
                categories=[],
                data_series=[],
                series_names=[],
                is_valid=False,
                error_message=f"No valid numeric Y-axis column found in dataset columns: {self.columns}",
            )

        # 3. Check for Long-Format Data (Secondary Grouping)
        group_col = spec.grouping
        if group_col and group_col in self.columns and group_col != x_col and y_cols:
            metric_col = y_cols[0]
            unique_cats: list[str] = []
            unique_groups: list[str] = []
            lookup: dict[tuple[str, str], list[float]] = {}

            for r in self._dict_rows:
                xv = str(r.get(x_col, "") or "Unknown")
                gv = str(r.get(group_col, "") or "Unknown")
                val = safe_float(r.get(metric_col), 0.0)
                if xv not in unique_cats:
                    unique_cats.append(xv)
                if gv not in unique_groups:
                    unique_groups.append(gv)
                lookup.setdefault((xv, gv), []).append(val)

            # Aggregate cells
            agg = spec.aggregation_method or "sum"
            series_data: list[list[float]] = []
            for g in unique_groups:
                g_vals: list[float] = []
                for cat in unique_cats:
                    cell_vals = lookup.get((cat, g), [0.0])
                    if agg == "avg":
                        g_vals.append(sum(cell_vals) / len(cell_vals) if cell_vals else 0.0)
                    elif agg == "count":
                        g_vals.append(float(len(cell_vals)))
                    elif agg == "max":
                        g_vals.append(max(cell_vals) if cell_vals else 0.0)
                    elif agg == "min":
                        g_vals.append(min(cell_vals) if cell_vals else 0.0)
                    else:
                        g_vals.append(sum(cell_vals))
                series_data.append(g_vals)

            return TransformedChartData(
                title=spec.title,
                chart_type=spec.chart_type,
                x_axis=x_col,
                y_axes=y_cols,
                categories=unique_cats,
                data_series=series_data,
                series_names=unique_groups,
                warnings=warnings,
            )

        # 4. Standard Aggregation by Category
        # Check if multiple rows share the same X value
        x_vals_raw = [str(r.get(x_col, "") or "Unknown") for r in self._dict_rows]
        has_duplicates = len(x_vals_raw) != len(set(x_vals_raw))
        need_aggregation = has_duplicates or (spec.aggregation_method is not None and spec.aggregation_method != "none")

        if need_aggregation:
            agg_method = spec.aggregation_method or "sum"
            grouped: dict[str, dict[str, list[float]]] = {}
            ordered_cats: list[str] = []

            for r in self._dict_rows:
                cat = str(r.get(x_col, "") or "Unknown")
                if cat not in grouped:
                    grouped[cat] = {y: [] for y in y_cols}
                    ordered_cats.append(cat)
                for y in y_cols:
                    v = safe_float(r.get(y), 0.0)
                    grouped[cat][y].append(v)

            # Apply aggregation function
            final_categories: list[str] = []
            final_data_series: list[list[float]] = [[] for _ in y_cols]

            for cat in ordered_cats:
                final_categories.append(cat)
                for idx, y in enumerate(y_cols):
                    vals = grouped[cat][y]
                    if not vals:
                        val = 0.0
                    elif agg_method == "avg":
                        val = sum(vals) / len(vals)
                    elif agg_method == "count":
                        val = float(len(vals))
                    elif agg_method == "max":
                        val = max(vals)
                    elif agg_method == "min":
                        val = min(vals)
                    else:
                        val = sum(vals)
                    final_data_series[idx].append(val)
        else:
            final_categories = [str(r.get(x_col, "") or "Unknown") for r in self._dict_rows]
            final_data_series = [
                [safe_float(r.get(y), 0.0) for r in self._dict_rows]
                for y in y_cols
            ]

        # 5. Apply Sorting
        if spec.sorting in {"asc", "desc"} and final_categories and final_data_series and final_data_series[0]:
            primary_vals = final_data_series[0]
            paired = list(zip(final_categories, primary_vals, *final_data_series[1:]))
            reverse = (spec.sorting == "desc")
            paired.sort(key=lambda item: item[1], reverse=reverse)
            final_categories = [p[0] for p in paired]
            for s_idx in range(len(final_data_series)):
                final_data_series[s_idx] = [p[s_idx + 1] for p in paired]
        elif self.column_types.get(x_col) == "date" and spec.chart_type in {"line", "historical", "historical_line"}:
            # Chronological date sort for line charts
            primary_vals = final_data_series[0] if final_data_series else []
            paired = list(zip(final_categories, *final_data_series))
            paired.sort(key=lambda item: item[0])
            final_categories = [p[0] for p in paired]
            for s_idx in range(len(final_data_series)):
                final_data_series[s_idx] = [p[s_idx + 1] for p in paired]

        # 6. Chart-Specific Validations
        percentages: list[float] | None = None

        if spec.chart_type in {"pie", "donut"}:
            if not final_data_series or not final_data_series[0]:
                return TransformedChartData(
                    title=spec.title,
                    chart_type=spec.chart_type,
                    x_axis=x_col,
                    y_axes=y_cols,
                    categories=[],
                    data_series=[],
                    series_names=[],
                    is_valid=False,
                    error_message="Insufficient data points for pie chart.",
                )
            
            pie_vals = final_data_series[0]
            has_negatives = any(v < 0 for v in pie_vals)
            if has_negatives:
                warnings.append("Pie chart data contained negative values; filtered non-negative values.")
                # Filter non-negative
                valid_pairs = [(c, v) for c, v in zip(final_categories, pie_vals) if v >= 0]
                if not valid_pairs:
                    return TransformedChartData(
                        title=spec.title,
                        chart_type=spec.chart_type,
                        x_axis=x_col,
                        y_axes=y_cols,
                        categories=[],
                        data_series=[],
                        series_names=[],
                        is_valid=False,
                        error_message="Cannot generate pie chart: all data values are negative.",
                    )
                final_categories = [p[0] for p in valid_pairs]
                pie_vals = [p[1] for p in valid_pairs]
                final_data_series = [pie_vals]

            total_val = sum(pie_vals)
            if total_val <= 0:
                return TransformedChartData(
                    title=spec.title,
                    chart_type=spec.chart_type,
                    x_axis=x_col,
                    y_axes=y_cols,
                    categories=[],
                    data_series=[],
                    series_names=[],
                    is_valid=False,
                    error_message="Cannot generate pie chart: sum of slice values is zero.",
                )

            # Cap pie slices at top 7 + 'Other' to ensure legend and slices sum to 100%
            if len(pie_vals) > 8:
                sorted_pairs = sorted(zip(final_categories, pie_vals), key=lambda x: x[1], reverse=True)
                top_pairs = sorted_pairs[:7]
                other_val = sum(p[1] for p in sorted_pairs[7:])
                final_categories = [p[0] for p in top_pairs] + ["Other"]
                pie_vals = [p[1] for p in top_pairs] + [other_val]
                final_data_series = [pie_vals]

            # Calculate exact percentages
            percentages = [round(v * 100.0 / total_val, 1) for v in pie_vals]

        series_names = [y.replace("_", " ").title() for y in y_cols]
        return TransformedChartData(
            title=spec.title,
            chart_type=spec.chart_type,
            x_axis=x_col,
            y_axes=y_cols,
            categories=final_categories,
            data_series=final_data_series,
            series_names=series_names,
            percentages=percentages,
            is_valid=True,
            warnings=warnings,
        )


def extract_and_transform_chart(
    dataset: CanonicalSQLDataset,
    spec: ChartSpecification,
) -> TransformedChartData:
    """Convenience module-level function extracting transformed chart data from a canonical dataset."""
    return dataset.extract_and_transform_chart(spec)


class ValidationResult(tuple):
    """Result of consistency validation supporting tuple unpacking, dict keys, and attribute access."""

    def __new__(cls, is_valid: bool, errors: list[str], warnings: list[str]):
        return super().__new__(cls, (is_valid, errors, warnings))

    def __init__(self, is_valid: bool, errors: list[str], warnings: list[str]):
        self.is_valid = bool(is_valid)
        self.errors = list(errors)
        self.warnings = list(warnings)
        self.is_consistent = self.is_valid
        self.issues = self.errors

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item in ("is_valid", "is_consistent"):
                return self.is_valid
            if item in ("errors", "issues"):
                return self.errors
            if item == "warnings":
                return self.warnings
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


class ReportConsistencyValidator:
    """Deterministic validation of reporting data consistency before rendering."""

    @classmethod
    def validate_report_components(
        cls,
        datasets: Mapping[str, CanonicalSQLDataset] | CanonicalSQLDataset,
        *,
        kpis: Sequence[Mapping[str, Any]] | None = None,
        charts: Sequence[ChartSpecification | TransformedChartData | Mapping[str, Any]] | None = None,
    ) -> ValidationResult:
        """Validate consistency across KPIs, charts, and source datasets.
        
        Returns ValidationResult(is_valid, validation_errors, validation_warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        if isinstance(datasets, CanonicalSQLDataset):
            datasets = {datasets.name: datasets}

        if not datasets:
            return ValidationResult(True, [], ["No datasets present in report."])

        primary_ds = next(iter(datasets.values()))

        # 1. Validate empty SQL result
        if all(ds.is_empty for ds in datasets.values()):
            warnings.append("All SQL query results returned 0 rows. A clean 'No Data' report should be produced.")
            return ValidationResult(True, [], warnings)

        # 2. Validate Chart Specifications & Transformed Data
        if charts:
            for idx, raw_ch in enumerate(charts, start=1):
                if isinstance(raw_ch, TransformedChartData):
                    transformed = raw_ch
                    if transformed.is_valid and transformed.y_axes and transformed.data_series:
                        y_col = transformed.y_axes[0]
                        if y_col in primary_ds.columns:
                            table_sum = sum(primary_ds.get_numeric_column_values(y_col))
                            chart_sum = sum(transformed.data_series[0]) if transformed.data_series else 0.0
                            if table_sum > 0 and abs(chart_sum - table_sum) > 0.01:
                                errors.append(
                                    f"Chart '{transformed.title}' series total ({chart_sum}) does not match table total ({table_sum})."
                                )
                    continue

                try:
                    if isinstance(raw_ch, ChartSpecification):
                        spec = raw_ch
                    elif isinstance(raw_ch, Mapping):
                        spec = ChartSpecification(**dict(raw_ch))
                    else:
                        continue
                except Exception as e:
                    warnings.append(f"Chart #{idx} failed specification validation: {e}")
                    continue

                transformed = primary_ds.extract_and_transform_chart(spec)
                if not transformed.is_valid:
                    warnings.append(f"Chart '{spec.title}' omitted: {transformed.error_message}")
                else:
                    # Verify pie chart percentages sum to approx 100%
                    if spec.chart_type in {"pie", "donut"} and transformed.percentages:
                        pct_sum = sum(transformed.percentages)
                        if not (98.0 <= pct_sum <= 102.0):
                            warnings.append(
                                f"Pie chart '{spec.title}' percentage sum {pct_sum:.1f}% deviates from 100%."
                            )

        # 3. Validate KPI Alignment
        if kpis and not primary_ds.is_empty:
            computed = primary_ds.compute_deterministic_kpis()
            computed_map = {k["label"].lower(): k["value"] for k in computed}
            for k in kpis:
                lbl = str(k.get("label", "")).lower()
                val = str(k.get("value", ""))
                if lbl in computed_map and computed_map[lbl] != val:
                    warnings.append(
                        f"KPI '{k.get('label')}' supplied value '{val}' adjusted to match SQL dataset calculation '{computed_map[lbl]}'."
                    )

        return ValidationResult(len(errors) == 0, errors, warnings)

