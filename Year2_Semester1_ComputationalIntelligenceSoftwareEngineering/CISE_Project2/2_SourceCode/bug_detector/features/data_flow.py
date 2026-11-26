"""Data-flow, nullability, and resource-lifecycle feature extractor."""

from __future__ import annotations

from typing import Any

from scipy import sparse

from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats, extract_fixed_dense_matrix

DFG_COLUMNS = [
    "semantic_model_available",
    "dfg_available",
    "dfg_succeeded",
    "dfg_unresolved_symbol_ratio",
    "dfg_variables_declared",
    "dfg_always_assigned",
    "dfg_data_flows_in",
    "dfg_data_flows_out",
    "dfg_read_inside",
    "dfg_written_inside",
    "dfg_captured",
    "dfg_unsafe_address_taken",
    "dfg_unassigned_read_proxy",
    "dfg_local_decls_count",
    "dfg_unused_local_count",
    "dfg_multi_assigned_local_count",
    "dfg_conditional_assigned_var_count",
    "dfg_checked_param_null_count",
    "dfg_unchecked_param_deref_count",
    "dfg_nullable_assigned_var_count",
    "dfg_unchecked_nullable_var_deref_count",
    "dfg_unchecked_nullable_call_deref_count",
    "dfg_disposable_allocations",
    "dfg_using_wrapped_allocations",
    "dfg_explicit_dispose_calls",
    "dfg_undisposed_resource_allocations",
    "dfg_field_read_count",
    "dfg_field_write_count",
    "dfg_total_var_reads",
    "dfg_total_var_writes",
]


class DataFlowFeatureExtractor(BaseFeatureExtractor):
    """Extracts Roslyn data-flow, def-use, null-safety, and resource-disposal features."""

    group_name = "data_flow"
    version = "1.0.0"

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        return extract_fixed_dense_matrix(
            records,
            payload_key="dfg_metrics",
            columns=DFG_COLUMNS,
            group_name=self.group_name,
            version=self.version,
        )

    def get_feature_names(self) -> list[str]:
        return list(DFG_COLUMNS)
