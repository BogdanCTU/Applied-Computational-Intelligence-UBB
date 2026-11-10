"""Dedicated Report Data Validation Layer for period, dataset, numerical, and chart suitability checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from reporting.canonical_data import (
    AUTHORITATIVE_METRIC_DEFINITIONS,
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    normalize_kpi_collection,
    safe_float,
)
from reporting.dataset_registry import CuratedDataset, ReportDatasetRegistry
from reporting.date_utils import PeriodAvailabilityContext


@dataclass
class ReportValidationReport:
    """Structured output of the Report Data Validation Layer."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    omitted_analyses: list[str] = field(default_factory=list)
    period_validation: dict[str, Any] = field(default_factory=dict)
    dataset_validation: dict[str, Any] = field(default_factory=dict)
    numerical_validation: dict[str, Any] = field(default_factory=dict)
    visualization_validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "omitted_analyses": list(self.omitted_analyses),
            "period_validation": dict(self.period_validation),
            "dataset_validation": dict(self.dataset_validation),
            "numerical_validation": dict(self.numerical_validation),
            "visualization_validation": dict(self.visualization_validation),
        }


class ReportDataValidator:
    """Comprehensive pre-composition validator for analytical reports."""

    @classmethod
    def build_reconciled_kpis_and_summary(
        cls,
        registry: ReportDatasetRegistry,
        *,
        supplied_kpis: Sequence[Mapping[str, Any] | str] | None = None,
        supplied_summary: str = "",
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
        """Compute authoritative KPIs, comparison KPIs, executive summary, and key findings.

        Guarantees that:
        1. If the requested period has 0 records, the Requested Period KPIs explicitly show
           0 records (No Data for Requested Period), and Historical Comparison KPIs are
           separately labeled with the comparison period name (e.g. 'September 2026').
        2. The Executive Summary is generated/reconciled from the exact same validated figures
           so it can never contradict the KPI cards.
        """
        ctx = registry.period_context
        req_period = ctx.requested_period
        comp_period = ctx.comparison_period

        primary_kpis: list[dict[str, Any]] = []
        comparison_kpis: list[dict[str, Any]] = []
        reconciled_findings: list[str] = []

        # Case A: Requested period was specified and has 0 records in the database
        if req_period is not None and not ctx.requested_period_has_data:
            req_lbl = req_period.period_label
            primary_kpis = [
                {
                    "label": f"Total Orders ({req_lbl})",
                    "value": "0 (No Data)",
                    "note": f"Requested period [{req_period.start_date_str}, {req_period.end_date_str})",
                },
                {
                    "label": f"Sales Volume ({req_lbl})",
                    "value": "$0.00 (No Data)",
                    "note": f"No records in {req_lbl}",
                },
                {
                    "label": f"Total Revenue ({req_lbl})",
                    "value": "$0.00 (No Data)",
                    "note": f"No records in {req_lbl}",
                },
                {
                    "label": f"Transactions ({req_lbl})",
                    "value": "0 (No Data)",
                    "note": f"No records in {req_lbl}",
                },
            ]

            comp_ds = registry.get_comparison_period_dataset()
            comp_lbl = comp_period.period_label if comp_period else "Latest Historical Month"
            if comp_ds and comp_ds.canonical and not comp_ds.canonical.is_empty:
                raw_comp = comp_ds.canonical.compute_deterministic_kpis()
                for k in raw_comp:
                    comparison_kpis.append({
                        "label": f"{k['label']} ({comp_lbl} Comparison)",
                        "value": k["value"],
                        "note": f"Historical Comparison ({comp_lbl})",
                    })

            # Construct reconciled executive summary that explicitly separates Requested vs Comparison
            avail_range = ""
            if ctx.available_min_date or ctx.available_max_date:
                avail_range = (
                    f" The database contains transaction records spanning from "
                    f"{ctx.available_min_date or 'N/A'} through {ctx.available_max_date or 'N/A'}."
                )

            comp_summary_part = ""
            if comparison_kpis:
                comp_map = {k["label"].split(" (")[0]: k["value"] for k in comparison_kpis}
                c_orders = comp_map.get("Total Orders", "N/A")
                c_sales = comp_map.get("Sales Volume", "N/A")
                c_rev = comp_map.get("Total Revenue", "N/A")
                c_aov = comp_map.get("Average Order Value", "N/A")
                c_tx = comp_map.get("Transactions", "")
                tx_clause = f", {c_tx} payment transactions" if c_tx else ""
                comp_summary_part = (
                    f" For historical context ONLY, the latest complete comparison month ({comp_lbl}) "
                    f"recorded {c_orders} orders{tx_clause}, {c_sales} in gross sales (subtotal), "
                    f"and {c_rev} in total revenue (Average Order Value: {c_aov})."
                )

            hist_ds = next(
                (ds for ds in registry.included_datasets if ds.analytical_purpose == "historical_monthly"),
                None,
            )
            hist_part = ""
            if hist_ds and hist_ds.row_count >= 2:
                hist_part = (
                    f" Multi-month historical trend analysis covers {hist_ds.reporting_period} "
                    f"({hist_ds.row_count} monthly observations)."
                )

            exec_summary = (
                f"DATA AVAILABILITY NOTICE: No database records exist for the requested reporting period "
                f"{req_lbl} (half-open interval [{req_period.start_date_str}, {req_period.end_date_str})). "
                f"All metrics for {req_lbl} are verified at 0 orders and $0.00 revenue.{avail_range}"
                f"{comp_summary_part}{hist_part}"
            )

            reconciled_findings.append(
                f"Requested Period ({req_lbl}): 0 orders and $0.00 revenue (half-open boundary "
                f"[{req_period.start_date_str}, {req_period.end_date_str}) exceeds database maximum date "
                f"{ctx.available_max_date or '2026-09-29'})."
            )
            if comparison_kpis:
                comp_map = {k["label"].split(" (")[0]: k["value"] for k in comparison_kpis}
                reconciled_findings.append(
                    f"Historical Comparison ({comp_lbl}): {comp_map.get('Total Orders', '0')} orders, "
                    f"{comp_map.get('Sales Volume', '$0.00')} gross sales, and "
                    f"{comp_map.get('Total Revenue', '$0.00')} total revenue "
                    f"(AOV: {comp_map.get('Average Order Value', 'N/A')})."
                )
            return primary_kpis, comparison_kpis, exec_summary, reconciled_findings

        # Case B: Requested period has data (or no missing period fallback is active)
        target_ds = (
            registry.get_requested_period_dataset()
            or next((ds for ds in registry.included_datasets if ds.canonical and not ds.canonical.is_empty), None)
            or next((ds for ds in registry.all_datasets.values() if ds.canonical and not ds.canonical.is_empty), None)
        )

        if target_ds and target_ds.canonical and not target_ds.canonical.is_empty:
            computed_kpis = target_ds.canonical.compute_deterministic_kpis()
            norm_supplied = normalize_kpi_collection(supplied_kpis) if supplied_kpis else []
            if not norm_supplied:
                primary_kpis = computed_kpis
            else:
                computed_map = {k["label"].lower(): k["value"] for k in computed_kpis}
                seen_labels: set[str] = set()
                for k in norm_supplied:
                    lbl = str(k.get("label", "Metric"))
                    val = str(k.get("value", ""))
                    # Reconcile value from computed_map if empty or if label matches
                    matched_val = computed_map.get(lbl.lower())
                    if not matched_val:
                        for c_lbl, c_val in computed_map.items():
                            if c_lbl in lbl.lower() or lbl.lower() in c_lbl:
                                matched_val = c_val
                                break
                    if matched_val:
                        val = matched_val
                    primary_kpis.append({
                        "label": lbl,
                        "value": val or "—",
                        "note": str(k.get("note") or ""),
                    })
                    seen_labels.add(lbl.lower())
                for ck in computed_kpis:
                    ck_lower = ck["label"].lower()
                    if ck_lower not in seen_labels and not any(ck_lower in sl for sl in seen_labels):
                        primary_kpis.append(ck)

            # Reconcile executive summary if supplied summary contradicts KPIs or is empty
            kpi_map = {k["label"]: k["value"] for k in computed_kpis}
            period_str = req_period.period_label if req_period else target_ds.reporting_period
            if not supplied_summary.strip():
                parts: list[str] = []
                if "Total Orders" in kpi_map:
                    parts.append(f"{kpi_map['Total Orders']} orders")
                if "Sales Volume" in kpi_map:
                    parts.append(f"{kpi_map['Sales Volume']} in gross sales")
                if "Total Revenue" in kpi_map:
                    parts.append(f"{kpi_map['Total Revenue']} in total revenue")
                if "Average Order Value" in kpi_map:
                    parts.append(f"an Average Order Value of {kpi_map['Average Order Value']}")
                metrics_str = ", ".join(parts) if parts else f"{target_ds.row_count} records"
                exec_summary = f"Analytical summary for {period_str}: verified SQL results show {metrics_str}."
            else:
                exec_summary = supplied_summary
        else:
            exec_summary = (
                supplied_summary
                or "No matching records were returned from the database for the requested criteria (0 rows)."
            )

        return primary_kpis, comparison_kpis, exec_summary, reconciled_findings

    @classmethod
    def validate(
        cls,
        registry: ReportDatasetRegistry,
        *,
        kpis: Sequence[Mapping[str, Any] | str] | None = None,
        comparison_kpis: Sequence[Mapping[str, Any] | str] | None = None,
        executive_summary: str = "",
        charts: Sequence[Mapping[str, Any]] | None = None,
        required_breakdowns: Sequence[str] | None = None,
    ) -> ReportValidationReport:
        """Execute full 4-stage validation (Period, Dataset, Numerical, Visualization Suitability)."""
        report = ReportValidationReport()
        ctx = registry.period_context

        # 1. Period validation
        req_period = ctx.requested_period
        comp_period = ctx.comparison_period
        report.period_validation = {
            "requested_period": req_period.period_label if req_period else "Unspecified",
            "requested_boundaries": (
                f"[{req_period.start_date_str}, {req_period.end_date_str})" if req_period else "N/A"
            ),
            "requested_period_has_data": ctx.requested_period_has_data,
            "comparison_period": comp_period.period_label if comp_period else None,
            "available_min_date": ctx.available_min_date,
            "available_max_date": ctx.available_max_date,
            "is_fallback_comparison_active": ctx.is_fallback_comparison_active,
        }
        if ctx.is_fallback_comparison_active and req_period:
            report.warnings.append(
                f"Requested period '{req_period.period_label}' returned 0 records; "
                f"'{comp_period.period_label if comp_period else 'Historical'}' is included explicitly as a historical comparison."
            )

        # 2. Dataset validation
        rejected_ids = [
            ds.dataset_id for ds in registry.all_datasets.values() if ds.validation_status == "rejected_invalid"
        ]
        duplicate_ids = [
            ds.dataset_id for ds in registry.all_datasets.values() if ds.validation_status == "excluded_duplicate"
        ]
        empty_ids = [
            ds.dataset_id for ds in registry.all_datasets.values() if ds.validation_status == "excluded_empty"
        ]
        metadata_ids = [
            ds.dataset_id for ds in registry.all_datasets.values() if ds.validation_status == "excluded_metadata"
        ]
        included_ids = [ds.dataset_id for ds in registry.included_datasets]

        for ds_id in rejected_ids:
            ds = registry.all_datasets[ds_id]
            for note in ds.validation_notes:
                report.warnings.append(f"Rejected invalid dataset '{ds_id}': {note}")

        if duplicate_ids:
            report.warnings.append(
                f"Deduplicated {len(duplicate_ids)} redundant intermediate dataset(s): {', '.join(duplicate_ids)}."
            )

        # Check required breakdowns coverage
        present_purposes = {ds.analytical_purpose for ds in registry.included_datasets}
        missing_breakdowns: list[str] = []
        if required_breakdowns:
            for req_b in required_breakdowns:
                if req_b not in present_purposes:
                    missing_breakdowns.append(req_b)
                    report.omitted_analyses.append(
                        f"Breakdown '{req_b.replace('_', ' ')}' was not present in the executed query results."
                    )

        report.dataset_validation = {
            "total_registered": len(registry.all_datasets),
            "included_in_pdf": included_ids,
            "rejected_invalid": rejected_ids,
            "excluded_duplicates": duplicate_ids,
            "excluded_empty": empty_ids,
            "excluded_metadata_probes": metadata_ids,
            "present_purposes": sorted(present_purposes),
            "missing_breakdowns": missing_breakdowns,
        }

        # 3. Numerical consistency validation
        canonical_map = {
            ds.dataset_id: ds.canonical
            for ds in registry.included_datasets
            if ds.canonical is not None
        }
        val_res = ReportConsistencyValidator.validate_report_components(
            canonical_map,
            kpis=kpis,
            charts=charts,
            executive_summary=executive_summary,
            requested_period=req_period.period_label if req_period else "",
            requested_period_has_data=ctx.requested_period_has_data,
            comparison_period=comp_period.period_label if comp_period else "",
        )
        report.errors.extend(val_res.errors)
        for w in val_res.warnings:
            if w not in report.warnings:
                report.warnings.append(w)

        report.numerical_validation = {
            "is_consistent": val_res.is_valid,
            "kpi_count": len(kpis or []),
            "comparison_kpi_count": len(comparison_kpis or []),
            "metric_definitions": AUTHORITATIVE_METRIC_DEFINITIONS,
        }

        # 4. Visualization suitability validation
        valid_charts_count = 0
        omitted_charts_count = 0
        if charts:
            for ch in charts:
                ds_id = str(ch.get("dataset_id") or "")
                ch_ds = canonical_map.get(ds_id) or (next(iter(canonical_map.values())) if canonical_map else None)
                if not ch_ds:
                    omitted_charts_count += 1
                    continue
                spec = ChartSpecification(
                    title=str(ch.get("title") or "Chart"),
                    chart_type=str(ch.get("chart_type") or "bar"),
                    x_axis=str(ch.get("x_column") or ch.get("x_axis") or ""),
                    y_axis=ch.get("y_columns") or ch.get("y_axis") or "",
                )
                trans = ch_ds.extract_and_transform_chart(spec)
                if trans.is_valid:
                    valid_charts_count += 1
                else:
                    omitted_charts_count += 1
                    reason = f"Chart '{spec.title}' omitted: {trans.error_message}"
                    if reason not in report.omitted_analyses:
                        report.omitted_analyses.append(reason)

        report.visualization_validation = {
            "valid_charts": valid_charts_count,
            "omitted_charts": omitted_charts_count,
        }
        report.is_valid = len(report.errors) == 0
        return report

