"""Curated Report Dataset Registry for filtering, classifying, deduplicating, and validating SQL datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

from reporting.canonical_data import (
    AUTHORITATIVE_METRIC_DEFINITIONS,
    CanonicalSQLDataset,
    is_numeric_value,
    safe_float,
    validate_tabular_rows_structure,
)
from reporting.date_utils import (
    PeriodAvailabilityContext,
    ReportingPeriod,
    calculate_calendar_month,
    parse_year_month_from_date_str,
    resolve_requested_period,
)


_METADATA_PROBE_COL_PATTERNS = (
    "min(",
    "max(",
    "min_date",
    "max_date",
    "earliest",
    "latest",
    "sqlite_master",
    "table_name",
    "pragma",
)


def _is_metadata_probe_dataset(columns: Sequence[str], rows: Sequence[Sequence[Any]], sql_query: str = "") -> bool:
    """Return True if dataset is an internal schema or date-range probe rather than business data."""
    if not columns:
        return True
    cols_lower = [str(c).lower().strip() for c in columns]
    sql_lower = (sql_query or "").lower()

    if "sqlite_master" in sql_lower or "pragma_" in sql_lower or "pragma " in sql_lower:
        return True

    # Single-row MIN/MAX date boundary probe (e.g., SELECT MIN(order_date), MAX(order_date) FROM orders)
    if len(rows) == 1 and len(cols_lower) <= 4:
        if all(
            any(pat in c for pat in ("min", "max", "earliest", "latest", "start_date", "end_date"))
            for c in cols_lower
        ):
            return True
    return False


def _infer_column_metric_definition(col_name: str) -> dict[str, Any] | None:
    """Match a SQL column name to its authoritative metric definition if applicable."""
    cl = col_name.lower().strip()
    # Exact or alias match
    for metric_key, defn in AUTHORITATIVE_METRIC_DEFINITIONS.items():
        if cl == metric_key or cl in defn["aliases"]:
            return dict(defn, metric_key=metric_key)
    if any(k in cl for k in ("order_count", "total_orders", "orders_count", "num_orders")):
        return dict(AUTHORITATIVE_METRIC_DEFINITIONS["orders"], metric_key="orders")
    if any(k in cl for k in ("transaction_count", "total_transactions", "transactions_count", "num_transactions", "tx_cnt")):
        return dict(AUTHORITATIVE_METRIC_DEFINITIONS["transactions"], metric_key="transactions")
    if any(k in cl for k in ("sales_volume", "gross_sales", "subtotal", "gross_amount")) or (
        "sales" in cl and "revenue" not in cl
    ):
        return dict(AUTHORITATIVE_METRIC_DEFINITIONS["sales"], metric_key="sales")
    if any(k in cl for k in ("total_revenue", "net_revenue", "revenue", "total_amount", "captured_revenue", "rev")):
        return dict(AUTHORITATIVE_METRIC_DEFINITIONS["revenue"], metric_key="revenue")
    if any(k in cl for k in ("avg_order_value", "aov", "average_order_value")):
        return dict(AUTHORITATIVE_METRIC_DEFINITIONS["avg_order_value"], metric_key="avg_order_value")
    return None


@dataclass
class CuratedDataset:
    """Structured, validated dataset entry in the ReportDatasetRegistry."""

    dataset_id: str
    title: str
    analytical_purpose: str
    reporting_period: str
    column_definitions: list[dict[str, str]]
    data_types: dict[str, str]
    rows: list[list[Any]]
    row_count: int
    metric_definitions: dict[str, dict[str, Any]]
    visualization_mapping: list[dict[str, Any]] = field(default_factory=list)
    validation_status: str = "valid"
    validation_notes: list[str] = field(default_factory=list)
    is_comparison_data: bool = False
    include_in_pdf: bool = True
    sql_query: str = ""
    canonical: CanonicalSQLDataset | None = None

    @property
    def columns(self) -> list[str]:
        return [c["name"] for c in self.column_definitions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "title": self.title,
            "analytical_purpose": self.analytical_purpose,
            "reporting_period": self.reporting_period,
            "is_comparison_data": self.is_comparison_data,
            "column_definitions": list(self.column_definitions),
            "data_types": dict(self.data_types),
            "columns": self.columns,
            "rows": list(self.rows),
            "row_count": self.row_count,
            "metric_definitions": dict(self.metric_definitions),
            "visualization_mapping": list(self.visualization_mapping),
            "validation_status": self.validation_status,
            "validation_notes": list(self.validation_notes),
            "include_in_pdf": self.include_in_pdf,
            "sql_query": self.sql_query,
        }


class ReportDatasetRegistry:
    """Curates raw SQL session datasets into validated, non-redundant analytical report datasets."""

    def __init__(
        self,
        requested_period: ReportingPeriod | None = None,
        reference_date: datetime | None = None,
    ) -> None:
        self.requested_period = requested_period
        self.reference_date = reference_date or datetime.now()
        self._datasets: dict[str, CuratedDataset] = {}
        self._seen_signatures: dict[tuple[Any, ...], str] = {}
        self.period_context = PeriodAvailabilityContext(
            requested_period=requested_period,
            requested_period_has_data=False if requested_period else True,
        )

    @property
    def all_datasets(self) -> dict[str, CuratedDataset]:
        return dict(self._datasets)

    @property
    def included_datasets(self) -> list[CuratedDataset]:
        """Return only validated datasets selected for inclusion in the final report."""
        return [ds for ds in self._datasets.values() if ds.include_in_pdf and ds.row_count > 0]

    def register(
        self,
        dataset_id: str,
        columns: Sequence[str],
        rows: Any,
        *,
        sql_query: str = "",
        explicit_title: str = "",
    ) -> CuratedDataset:
        """Validate, classify, and register a candidate dataset."""
        clean_cols = [str(c).strip() for c in (columns or []) if str(c).strip()]
        is_struct_valid, sanitized_rows, struct_errors = validate_tabular_rows_structure(clean_cols, rows)

        canonical = CanonicalSQLDataset(
            clean_cols,
            sanitized_rows if is_struct_valid else [],
            name=dataset_id,
            sql_query=sql_query,
        )

        # Build column definitions & metric mappings
        col_defs: list[dict[str, str]] = []
        data_types: dict[str, str] = {}
        metric_defs: dict[str, dict[str, Any]] = {}

        for c in clean_cols:
            m_def = _infer_column_metric_definition(c)
            c_type = canonical.column_types.get(c, "text")
            fmt = "text"
            if m_def:
                metric_defs[c] = m_def
                fmt = m_def["unit"]
                c_type = "numeric"
            elif c_type == "numeric":
                cl = c.lower()
                if any(k in cl for k in ("pct", "percent", "share", "rate", "margin")):
                    fmt = "percentage"
                elif any(k in cl for k in ("amount", "price", "cost", "fee", "tax", "discount", "value")):
                    fmt = "currency"
                else:
                    fmt = "integer"
            elif c_type == "date":
                fmt = "temporal"

            data_types[c] = c_type
            col_defs.append({"name": c, "data_type": c_type, "format": fmt})

        # 1. Reject corrupted payload (e.g. scalar strings passed as rows)
        if not is_struct_valid and rows:
            curated = CuratedDataset(
                dataset_id=dataset_id,
                title=explicit_title or f"Rejected Dataset ({dataset_id})",
                analytical_purpose="corrupted_payload",
                reporting_period="Invalid",
                column_definitions=col_defs,
                data_types=data_types,
                rows=[],
                row_count=0,
                metric_definitions=metric_defs,
                validation_status="rejected_invalid",
                validation_notes=struct_errors,
                include_in_pdf=False,
                sql_query=sql_query,
                canonical=canonical,
            )
            self._datasets[dataset_id] = curated
            return curated

        table_rows = canonical.table_rows

        # 2. Check if this is an internal metadata probe (e.g. SELECT MIN(order_date), MAX(order_date))
        if _is_metadata_probe_dataset(clean_cols, table_rows, sql_query):
            self._extract_date_bounds_from_probe(clean_cols, table_rows)
            curated = CuratedDataset(
                dataset_id=dataset_id,
                title=explicit_title or "Database Date Boundary Probe",
                analytical_purpose="metadata_probe",
                reporting_period="Database Metadata",
                column_definitions=col_defs,
                data_types=data_types,
                rows=table_rows,
                row_count=len(table_rows),
                metric_definitions=metric_defs,
                validation_status="excluded_metadata",
                validation_notes=["Internal database metadata probe excluded from business report tables."],
                include_in_pdf=False,
                sql_query=sql_query,
                canonical=canonical,
            )
            self._datasets[dataset_id] = curated
            return curated

        # 3. Handle empty dataset (0 rows)
        if canonical.is_empty:
            self._check_if_empty_dataset_targeted_requested_period(sql_query)
            curated = CuratedDataset(
                dataset_id=dataset_id,
                title=explicit_title or f"Empty Query ({dataset_id})",
                analytical_purpose="empty_intermediate",
                reporting_period=(
                    self.requested_period.period_label if self.requested_period else "Requested Period"
                ),
                column_definitions=col_defs,
                data_types=data_types,
                rows=[],
                row_count=0,
                metric_definitions=metric_defs,
                validation_status="excluded_empty",
                validation_notes=["Query returned 0 records; excluded from individual table rendering."],
                include_in_pdf=False,
                sql_query=sql_query,
                canonical=canonical,
            )
            self._datasets[dataset_id] = curated
            return curated

        # 4. Detect duplicate datasets by canonical column + row values signature
        signature = (
            tuple(c.lower() for c in clean_cols),
            tuple(tuple(str(v) for v in r) for r in table_rows),
        )
        if signature in self._seen_signatures:
            orig_id = self._seen_signatures[signature]
            curated = CuratedDataset(
                dataset_id=dataset_id,
                title=explicit_title or f"Duplicate of {orig_id}",
                analytical_purpose="duplicate_intermediate",
                reporting_period="",
                column_definitions=col_defs,
                data_types=data_types,
                rows=table_rows,
                row_count=len(table_rows),
                metric_definitions=metric_defs,
                validation_status="excluded_duplicate",
                validation_notes=[f"Identical schema and row values to dataset '{orig_id}'; deduplicated."],
                include_in_pdf=False,
                sql_query=sql_query,
                canonical=canonical,
            )
            self._datasets[dataset_id] = curated
            return curated

        self._seen_signatures[signature] = dataset_id

        # 5. Classify analytical purpose, period label, and comparison status
        purpose, human_title, period_label, is_comp, viz_map = self._classify_dataset(
            dataset_id=dataset_id,
            columns=clean_cols,
            rows=table_rows,
            sql_query=sql_query,
            explicit_title=explicit_title,
            metric_defs=metric_defs,
        )

        curated = CuratedDataset(
            dataset_id=dataset_id,
            title=human_title,
            analytical_purpose=purpose,
            reporting_period=period_label,
            column_definitions=col_defs,
            data_types=data_types,
            rows=table_rows,
            row_count=len(table_rows),
            metric_definitions=metric_defs,
            visualization_mapping=viz_map,
            validation_status="valid",
            validation_notes=list(struct_errors),
            is_comparison_data=is_comp,
            include_in_pdf=True,
            sql_query=sql_query,
            canonical=canonical,
        )
        self._datasets[dataset_id] = curated
        return curated

    def finalize_curation(self) -> PeriodAvailabilityContext:
        """Finalize dataset selection, suppress superseded single-month tables, and compute period context."""
        # If a multi-month historical dataset is present, any 1-row monthly dataset whose single month
        # is already inside the historical dataset does not need its own redundant table in the PDF
        historical_datasets = [
            ds
            for ds in self._datasets.values()
            if ds.include_in_pdf and ds.analytical_purpose == "historical_monthly" and ds.row_count >= 2
        ]
        if historical_datasets:
            for ds in self._datasets.values():
                if (
                    ds.include_in_pdf
                    and ds.analytical_purpose in {"comparison_period_summary", "requested_period_summary"}
                    and ds.row_count == 1
                ):
                    ds.include_in_pdf = False
                    ds.validation_status = "excluded_superseded_single_month"
                    ds.validation_notes.append(
                        "Single-month summary row is already represented in KPI cards and multi-month historical table."
                    )

        # Build PeriodAvailabilityContext notes
        ctx = self.period_context
        if ctx.requested_period and not ctx.requested_period_has_data:
            ctx.missing_data_reason = "no_records"
            req_lbl = ctx.requested_period.period_label
            req_bounds = f"[{ctx.requested_period.start_date_str}, {ctx.requested_period.end_date_str})"
            note = (
                f"Requested Period ({req_lbl}, boundaries {req_bounds}): 0 records found in the database."
            )
            if note not in ctx.data_availability_notes:
                ctx.data_availability_notes.append(note)

            if ctx.available_min_date or ctx.available_max_date:
                range_note = (
                    f"Available Database Date Range: {ctx.available_min_date or 'N/A'} to "
                    f"{ctx.available_max_date or 'N/A'}."
                )
                if range_note not in ctx.data_availability_notes:
                    ctx.data_availability_notes.append(range_note)

            if ctx.comparison_period:
                comp_note = (
                    f"Historical Comparison Period ({ctx.comparison_period.period_label}, boundaries "
                    f"[{ctx.comparison_period.start_date_str}, {ctx.comparison_period.end_date_str})): "
                    f"Included explicitly as historical reference ({ctx.comparison_period_record_count:,} orders)."
                )
                if comp_note not in ctx.data_availability_notes:
                    ctx.data_availability_notes.append(comp_note)

        return ctx

    def get_requested_period_dataset(self) -> CuratedDataset | None:
        """Return dataset matching the requested period if available."""
        for ds in self._datasets.values():
            if ds.analytical_purpose == "requested_period_summary" and not ds.is_comparison_data and ds.row_count > 0:
                return ds
        return None

    def get_comparison_period_dataset(self) -> CuratedDataset | None:
        """Return dataset representing the historical comparison period (e.g. September 2026)."""
        for ds in self._datasets.values():
            if ds.analytical_purpose == "comparison_period_summary" and ds.row_count > 0:
                return ds
        # Or extract the latest month from a historical_monthly dataset
        for ds in self._datasets.values():
            if ds.analytical_purpose == "historical_monthly" and ds.row_count > 0:
                last_row = ds.rows[-1]
                return CuratedDataset(
                    dataset_id=f"{ds.dataset_id}_latest_month",
                    title=f"Latest Available Month ({last_row[0]})",
                    analytical_purpose="comparison_period_summary",
                    reporting_period=str(last_row[0]),
                    column_definitions=ds.column_definitions,
                    data_types=ds.data_types,
                    rows=[last_row],
                    row_count=1,
                    metric_definitions=ds.metric_definitions,
                    is_comparison_data=True,
                    include_in_pdf=False,
                    canonical=CanonicalSQLDataset(ds.columns, [last_row], name="comparison_latest"),
                )
        return None

    def _extract_date_bounds_from_probe(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        if not rows or not rows[0]:
            return
        row = rows[0]
        for idx, c in enumerate(columns):
            if idx >= len(row) or row[idx] is None:
                continue
            cl = c.lower()
            val_str = str(row[idx]).strip()
            if "min" in cl or "earliest" in cl or "start" in cl:
                self.period_context.available_min_date = val_str
            elif "max" in cl or "latest" in cl or "end" in cl:
                self.period_context.available_max_date = val_str
                ym = parse_year_month_from_date_str(val_str)
                if ym and self.requested_period:
                    req_ym = (self.requested_period.year, self.requested_period.month)
                    if ym < req_ym and self.period_context.comparison_period is None:
                        self.period_context.comparison_period = calculate_calendar_month(ym[0], ym[1])

    def _check_if_empty_dataset_targeted_requested_period(self, sql_query: str) -> None:
        if not self.requested_period:
            return
        if self.requested_period.start_date_str in (sql_query or "") or self.requested_period.year_month in (
            sql_query or ""
        ):
            self.period_context.requested_period_has_data = False
            self.period_context.requested_period_record_count = 0

    def _classify_dataset(
        self,
        *,
        dataset_id: str,
        columns: list[str],
        rows: list[list[Any]],
        sql_query: str,
        explicit_title: str,
        metric_defs: dict[str, dict[str, Any]],
    ) -> tuple[str, str, str, bool, list[dict[str, Any]]]:
        cols_lower = [c.lower() for c in columns]
        first_col = cols_lower[0] if cols_lower else ""

        # Extract any YYYY-MM values in temporal columns
        months_in_data: list[str] = []
        for idx, cl in enumerate(cols_lower):
            if any(k in cl for k in ("month", "date", "period", "year")):
                for r in rows:
                    if idx < len(r) and r[idx] is not None:
                        ym = parse_year_month_from_date_str(str(r[idx]))
                        if ym:
                            ym_str = f"{ym[0]:04d}-{ym[1]:02d}"
                            if ym_str not in months_in_data:
                                months_in_data.append(ym_str)

        for m_str in months_in_data:
            if m_str not in self.period_context.actual_periods_present:
                self.period_context.actual_periods_present.append(m_str)

        req_ym = self.requested_period.year_month if self.requested_period else None
        is_comparison = False
        period_label = ""

        if months_in_data:
            if len(months_in_data) == 1:
                only_ym = months_in_data[0]
                parsed = parse_year_month_from_date_str(only_ym)
                p_obj = calculate_calendar_month(parsed[0], parsed[1]) if parsed else None
                lbl = p_obj.period_label if p_obj else only_ym
                if req_ym and only_ym != req_ym:
                    is_comparison = True
                    period_label = f"{lbl} (Historical Comparison)"
                    if self.period_context.comparison_period is None and p_obj:
                        self.period_context.comparison_period = p_obj
                else:
                    period_label = lbl
                    if req_ym and only_ym == req_ym:
                        self.period_context.requested_period_has_data = True
            else:
                sorted_m = sorted(months_in_data)
                period_label = f"{sorted_m[0]} to {sorted_m[-1]} ({len(sorted_m)} Months Historical)"
                if req_ym and req_ym in sorted_m:
                    self.period_context.requested_period_has_data = True
                elif req_ym and req_ym not in sorted_m:
                    is_comparison = True
                    latest_ym = parse_year_month_from_date_str(sorted_m[-1])
                    if latest_ym and self.period_context.comparison_period is None:
                        self.period_context.comparison_period = calculate_calendar_month(
                            latest_ym[0], latest_ym[1]
                        )
        else:
            # Check SQL filter for date bounds
            sql_months = re.findall(r"\b(20\d{2}-\d{2})-\d{2}\b", sql_query or "")
            if sql_months:
                start_ym = sql_months[0]
                if req_ym and start_ym != req_ym:
                    is_comparison = True
                    parsed = parse_year_month_from_date_str(start_ym)
                    p_obj = calculate_calendar_month(parsed[0], parsed[1]) if parsed else None
                    lbl = p_obj.period_label if p_obj else start_ym
                    period_label = f"{lbl} (Historical Comparison)"
                    if self.period_context.comparison_period is None and p_obj:
                        self.period_context.comparison_period = p_obj
                elif self.requested_period:
                    period_label = self.requested_period.period_label
            elif self.requested_period and not self.period_context.requested_period_has_data:
                is_comparison = True
                comp_lbl = (
                    self.period_context.comparison_period.period_label
                    if self.period_context.comparison_period
                    else "Historical Comparison"
                )
                period_label = f"{comp_lbl} (Historical Comparison)"
            elif self.requested_period:
                period_label = self.requested_period.period_label
            else:
                period_label = "All Available Periods"

        # Classify analytical purpose by dimensions
        has_month = any(k in c for c in cols_lower for k in ("month", "order_date", "period", "quarter", "year"))
        has_channel = any("channel" in c for c in cols_lower)
        has_payment = any(k in c for c in cols_lower for k in ("payment_method", "method", "payment"))
        has_status = any("status" in c for c in cols_lower)
        has_category = any("category" in c for c in cols_lower)

        metric_cols = [c for c in columns if c in metric_defs or c.lower() not in {"month", "channel", "method", "payment_method", "status", "order_status", "category"}]
        primary_metric = next((c for c in columns if "revenue" in c.lower() or "total_amount" in c.lower()), None) or (
            metric_cols[0] if metric_cols else columns[-1]
        )
        order_metric = next((c for c in columns if "order" in c.lower()), primary_metric)

        viz_map: list[dict[str, Any]] = []

        if has_month and has_channel and len(rows) >= 2:
            purpose = "cross_dimensional_matrix"
            m_col = next(c for c in columns if "month" in c.lower() or "date" in c.lower())
            ch_col = next(c for c in columns if "channel" in c.lower())
            title = explicit_title or f"Monthly Channel Performance Matrix ({period_label})"
            viz_map.append({
                "chart_type": "grouped_bar",
                "title": f"Revenue by Month & Channel ({period_label})",
                "x_column": m_col,
                "y_columns": [primary_metric],
                "series_column": ch_col,
                "dataset_id": dataset_id,
            })
        elif has_channel and not has_month:
            purpose = "channel_breakdown"
            ch_col = next(c for c in columns if "channel" in c.lower())
            title = explicit_title or f"Channel Performance Breakdown ({period_label})"
            if len(rows) >= 2:
                viz_map.append({
                    "chart_type": "pie",
                    "title": f"Revenue Share by Channel ({period_label})",
                    "x_column": ch_col,
                    "y_columns": [primary_metric],
                    "dataset_id": dataset_id,
                })
                viz_map.append({
                    "chart_type": "vertical_bar",
                    "title": f"Orders & Revenue by Channel ({period_label})",
                    "x_column": ch_col,
                    "y_columns": [order_metric],
                    "dataset_id": dataset_id,
                })
        elif has_payment and not has_month:
            purpose = "payment_method_breakdown"
            pm_col = next(c for c in columns if any(k in c.lower() for k in ("payment_method", "method", "payment")))
            title = explicit_title or f"Payment Method Analysis ({period_label})"
            if len(rows) >= 2:
                viz_map.append({
                    "chart_type": "donut",
                    "title": f"Payment Method Distribution ({period_label})",
                    "x_column": pm_col,
                    "y_columns": [primary_metric],
                    "dataset_id": dataset_id,
                })
        elif has_status and not has_month:
            purpose = "order_status_breakdown"
            st_col = next(c for c in columns if "status" in c.lower())
            title = explicit_title or f"Order Status Distribution ({period_label})"
            if len(rows) >= 2:
                viz_map.append({
                    "chart_type": "pie",
                    "title": f"Order Count Share by Status ({period_label})",
                    "x_column": st_col,
                    "y_columns": [order_metric],
                    "dataset_id": dataset_id,
                })
        elif has_category and not has_month:
            purpose = "category_breakdown"
            cat_col = next(c for c in columns if "category" in c.lower())
            title = explicit_title or f"Product Category Breakdown ({period_label})"
            if len(rows) >= 2:
                viz_map.append({
                    "chart_type": "horizontal_bar",
                    "title": f"Revenue by Product Category ({period_label})",
                    "x_column": cat_col,
                    "y_columns": [primary_metric],
                    "dataset_id": dataset_id,
                })
        elif has_month:
            m_col = next(c for c in columns if any(k in c.lower() for k in ("month", "order_date", "period", "quarter", "year")))
            if len(rows) >= 2:
                purpose = "historical_monthly"
                title = explicit_title or f"Historical Monthly Performance ({period_label})"
                viz_map.append({
                    "chart_type": "vertical_bar",
                    "title": f"Historical Monthly Order Volume ({period_label})",
                    "x_column": m_col,
                    "y_columns": [order_metric],
                    "dataset_id": dataset_id,
                })
                if primary_metric != order_metric:
                    viz_map.append({
                        "chart_type": "historical_line",
                        "title": f"Historical Monthly Revenue & Sales Trend ({period_label})",
                        "x_column": m_col,
                        "y_columns": [c for c in columns if c in metric_defs and metric_defs[c]["unit"] == "currency"][:2] or [primary_metric],
                        "dataset_id": dataset_id,
                    })
                if len(metric_cols) >= 2:
                    viz_map.append({
                        "chart_type": "matrix",
                        "title": f"Monthly Performance Matrix ({period_label})",
                        "x_column": m_col,
                        "y_columns": metric_cols[:4],
                        "dataset_id": dataset_id,
                    })
            else:
                purpose = "comparison_period_summary" if is_comparison else "requested_period_summary"
                title = explicit_title or f"Monthly Summary ({period_label})"
                # Record comparison period order count if applicable
                if is_comparison and order_metric in columns:
                    ord_idx = columns.index(order_metric)
                    self.period_context.comparison_period_record_count = int(
                        safe_float(rows[0][ord_idx], 0.0)
                    )
        else:
            purpose = "general_analytical"
            title = explicit_title or f"Analytical Summary ({period_label})"

        return purpose, title, period_label, is_comparison, viz_map

    def supplement_from_readonly_database(
        self,
        db_path: str | Any,
        *,
        required_breakdowns: Sequence[str] | None = None,
        requested_chart_types: Sequence[str] | None = None,
    ) -> list[str]:
        """Supplement missing required breakdowns using read-only SQLite queries against ``db_path``.

        Preserves strict read-only URI connection semantics and avoids fan-out double-counting.
        Returns a list of supplemented dataset IDs.
        """
        import sqlite3
        from pathlib import Path

        path_obj = Path(str(db_path)).expanduser().resolve()
        if not path_obj.is_file():
            return []

        supplemented_ids: list[str] = []
        try:
            conn = sqlite3.connect(f"file:{path_obj}?mode=ro", uri=True, timeout=5.0)
        except Exception:
            return []

        try:
            cur = conn.cursor()
            tables = {
                str(r[0]).lower()
                for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            if "orders" not in tables:
                return []

            order_cols = {
                str(r[1]).lower()
                for r in cur.execute("PRAGMA table_info(orders)").fetchall()
            }
            if not {"order_id", "order_date", "total_amount"}.issubset(order_cols):
                return []

            has_subtotal = "subtotal" in order_cols
            has_channel = "channel" in order_cols
            has_status = "status" in order_cols
            has_payments = "payments" in tables
            payment_cols: set[str] = set()
            if has_payments:
                payment_cols = {
                    str(r[1]).lower()
                    for r in cur.execute("PRAGMA table_info(payments)").fetchall()
                }

            # 1. Discover min/max order_date if not already known
            bounds_row = cur.execute("SELECT MIN(order_date), MAX(order_date) FROM orders").fetchone()
            if bounds_row and bounds_row[0] and bounds_row[1]:
                self.period_context.available_min_date = str(bounds_row[0])
                self.period_context.available_max_date = str(bounds_row[1])

            # 2. Verify requested period record count & determine active comparison period
            req_p = self.requested_period
            if req_p is not None:
                req_cnt_row = cur.execute(
                    "SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_date >= ? AND order_date < ?",
                    (req_p.start_date_str, req_p.end_date_str),
                ).fetchone()
                req_cnt = int(req_cnt_row[0] or 0) if req_cnt_row else 0
                self.period_context.requested_period_record_count = req_cnt
                self.period_context.requested_period_has_data = req_cnt > 0

                if req_cnt == 0 and self.period_context.comparison_period is None:
                    max_before_row = cur.execute(
                        "SELECT MAX(order_date) FROM orders WHERE order_date < ?",
                        (req_p.start_date_str,),
                    ).fetchone()
                    max_before = str(max_before_row[0] or "") if max_before_row else ""
                    ym = parse_year_month_from_date_str(max_before)
                    if ym:
                        self.period_context.comparison_period = calculate_calendar_month(ym[0], ym[1])

            active_period = (
                req_p
                if (req_p and self.period_context.requested_period_has_data)
                else self.period_context.comparison_period
            )
            if active_period and not self.period_context.requested_period_has_data:
                comp_cnt_row = cur.execute(
                    "SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_date >= ? AND order_date < ?",
                    (active_period.start_date_str, active_period.end_date_str),
                ).fetchone()
                if comp_cnt_row:
                    self.period_context.comparison_period_record_count = int(comp_cnt_row[0] or 0)

            present_purposes = {
                ds.analytical_purpose for ds in self._datasets.values() if ds.include_in_pdf and ds.row_count > 0
            }
            req_b_set = set(required_breakdowns or ["historical_monthly", "channel_breakdown", "payment_method_breakdown", "order_status_breakdown"])
            sales_expr = "ROUND(SUM(o.subtotal), 2)" if has_subtotal else "ROUND(SUM(o.total_amount), 2)"

            # 3. Historical Monthly Series (at least up to 12 available months)
            has_multi_month = any(
                ds.analytical_purpose == "historical_monthly" and ds.row_count >= 2
                for ds in self._datasets.values()
                if ds.include_in_pdf
            )
            if "historical_monthly" in req_b_set and not has_multi_month:
                end_bound = req_p.end_date_str if req_p else "9999-12-31"
                if has_payments and "payment_id" in payment_cols:
                    hist_sql = (
                        "SELECT * FROM ("
                        "SELECT strftime('%Y-%m', o.order_date) AS month, "
                        "COUNT(DISTINCT o.order_id) AS order_count, "
                        "COALESCE(SUM(p.tx_cnt), 0) AS transaction_count, "
                        f"{sales_expr} AS sales, "
                        "ROUND(SUM(o.total_amount), 2) AS revenue, "
                        "ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS avg_order_value "
                        "FROM orders o "
                        "LEFT JOIN (SELECT order_id, COUNT(DISTINCT payment_id) AS tx_cnt FROM payments GROUP BY order_id) p "
                        "ON o.order_id = p.order_id "
                        f"WHERE o.order_date < '{end_bound}' "
                        "GROUP BY strftime('%Y-%m', o.order_date) "
                        "ORDER BY month DESC LIMIT 12"
                        ") ORDER BY month ASC"
                    )
                else:
                    hist_sql = (
                        "SELECT * FROM ("
                        "SELECT strftime('%Y-%m', o.order_date) AS month, "
                        "COUNT(DISTINCT o.order_id) AS order_count, "
                        f"{sales_expr} AS sales, "
                        "ROUND(SUM(o.total_amount), 2) AS revenue, "
                        "ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS avg_order_value "
                        "FROM orders o "
                        f"WHERE o.order_date < '{end_bound}' "
                        "GROUP BY strftime('%Y-%m', o.order_date) "
                        "ORDER BY month DESC LIMIT 12"
                        ") ORDER BY month ASC"
                    )
                cur.execute(hist_sql)
                h_cols = [d[0] for d in cur.description]
                h_rows = [list(r) for r in cur.fetchall()]
                if len(h_rows) >= 2:
                    self.register(
                        "curated_historical_monthly",
                        h_cols,
                        h_rows,
                        sql_query=hist_sql,
                        explicit_title=f"Historical Monthly Performance ({h_rows[0][0]} to {h_rows[-1][0]})",
                    )
                    supplemented_ids.append("curated_historical_monthly")

            # Active period filter for dimensional breakdowns
            where_clause = ""
            period_suffix = "All Available Data"
            if active_period:
                where_clause = (
                    f"WHERE o.order_date >= '{active_period.start_date_str}' "
                    f"AND o.order_date < '{active_period.end_date_str}' "
                )
                period_suffix = (
                    f"{active_period.period_label} Historical Comparison"
                    if (req_p and not self.period_context.requested_period_has_data)
                    else active_period.period_label
                )

            # 4. Channel Breakdown
            if "channel_breakdown" in req_b_set and "channel_breakdown" not in present_purposes and has_channel:
                ch_sql = (
                    "SELECT o.channel AS channel, "
                    "COUNT(DISTINCT o.order_id) AS order_count, "
                    f"{sales_expr} AS sales, "
                    "ROUND(SUM(o.total_amount), 2) AS revenue, "
                    "ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS avg_order_value "
                    f"FROM orders o {where_clause}"
                    "GROUP BY o.channel ORDER BY revenue DESC"
                )
                cur.execute(ch_sql)
                c_cols = [d[0] for d in cur.description]
                c_rows = [list(r) for r in cur.fetchall()]
                if c_rows:
                    self.register(
                        "curated_channel_breakdown",
                        c_cols,
                        c_rows,
                        sql_query=ch_sql,
                        explicit_title=f"Channel Performance Breakdown ({period_suffix})",
                    )
                    supplemented_ids.append("curated_channel_breakdown")

            # 5. Payment Method Breakdown
            if (
                "payment_method_breakdown" in req_b_set
                and "payment_method_breakdown" not in present_purposes
                and has_payments
                and {"method", "payment_id", "order_id"}.issubset(payment_cols)
            ):
                pm_sql = (
                    "SELECT p.method AS payment_method, "
                    "COUNT(DISTINCT p.payment_id) AS transaction_count, "
                    "COUNT(DISTINCT o.order_id) AS order_count, "
                    f"{sales_expr} AS sales, "
                    "ROUND(SUM(o.total_amount), 2) AS revenue "
                    "FROM payments p JOIN orders o ON p.order_id = o.order_id "
                    f"{where_clause}"
                    "GROUP BY p.method ORDER BY revenue DESC"
                )
                cur.execute(pm_sql)
                pm_cols = [d[0] for d in cur.description]
                pm_rows = [list(r) for r in cur.fetchall()]
                if pm_rows:
                    self.register(
                        "curated_payment_breakdown",
                        pm_cols,
                        pm_rows,
                        sql_query=pm_sql,
                        explicit_title=f"Payment Method Analysis ({period_suffix})",
                    )
                    supplemented_ids.append("curated_payment_breakdown")

            # 6. Order Status Breakdown
            if "order_status_breakdown" in req_b_set and "order_status_breakdown" not in present_purposes and has_status:
                st_sql = (
                    "SELECT o.status AS order_status, "
                    "COUNT(DISTINCT o.order_id) AS order_count, "
                    f"{sales_expr} AS sales, "
                    "ROUND(SUM(o.total_amount), 2) AS revenue "
                    f"FROM orders o {where_clause}"
                    "GROUP BY o.status ORDER BY order_count DESC"
                )
                cur.execute(st_sql)
                st_cols = [d[0] for d in cur.description]
                st_rows = [list(r) for r in cur.fetchall()]
                if st_rows:
                    self.register(
                        "curated_status_breakdown",
                        st_cols,
                        st_rows,
                        sql_query=st_sql,
                        explicit_title=f"Order Status Distribution ({period_suffix})",
                    )
                    supplemented_ids.append("curated_status_breakdown")

            # 7. Cross-Dimensional Month x Channel Revenue Matrix (when matrix chart is requested)
            if (
                requested_chart_types
                and "matrix" in requested_chart_types
                and "cross_dimensional_matrix" not in present_purposes
                and has_channel
            ):
                end_bound = req_p.end_date_str if req_p else "9999-12-31"
                mat_sql = (
                    "SELECT * FROM ("
                    "SELECT strftime('%Y-%m', o.order_date) AS month, "
                    "ROUND(SUM(CASE WHEN o.channel = 'web' THEN o.total_amount ELSE 0 END), 2) AS web, "
                    "ROUND(SUM(CASE WHEN o.channel = 'app' THEN o.total_amount ELSE 0 END), 2) AS app, "
                    "ROUND(SUM(CASE WHEN o.channel = 'marketplace' THEN o.total_amount ELSE 0 END), 2) AS marketplace, "
                    "ROUND(SUM(CASE WHEN o.channel = 'store' THEN o.total_amount ELSE 0 END), 2) AS store "
                    f"FROM orders o WHERE o.order_date < '{end_bound}' "
                    "GROUP BY strftime('%Y-%m', o.order_date) "
                    "ORDER BY month DESC LIMIT 6"
                    ") ORDER BY month ASC"
                )
                cur.execute(mat_sql)
                m_cols = [d[0] for d in cur.description]
                m_rows = [list(r) for r in cur.fetchall()]
                if len(m_rows) >= 2:
                    ds_mat = self.register(
                        "curated_month_channel_matrix",
                        m_cols,
                        m_rows,
                        sql_query=mat_sql,
                        explicit_title=f"Monthly Channel Revenue Matrix ({m_rows[0][0]} to {m_rows[-1][0]})",
                    )
                    ds_mat.analytical_purpose = "cross_dimensional_matrix"
                    ds_mat.visualization_mapping = [
                        {
                            "chart_type": "matrix",
                            "title": f"Monthly Revenue Matrix by Channel ({m_rows[0][0]} to {m_rows[-1][0]})",
                            "x_column": "month",
                            "y_columns": ["web", "app", "marketplace", "store"],
                            "dataset_id": "curated_month_channel_matrix",
                        }
                    ]
                    supplemented_ids.append("curated_month_channel_matrix")

        except Exception:
            pass
        finally:
            conn.close()

        return supplemented_ids

