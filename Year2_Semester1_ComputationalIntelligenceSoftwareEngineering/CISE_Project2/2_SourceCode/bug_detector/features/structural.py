"""Supplementary structural metrics feature extractor."""

from __future__ import annotations

from typing import Any

from scipy import sparse

from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats, extract_fixed_dense_matrix

STRUCTURAL_COLUMNS = [
    "struct_cyclomatic_complexity",
    "struct_method_loc",
    "struct_logical_loc",
    "struct_parameter_count",
    "struct_max_nesting_depth",
    "struct_local_variable_count",
    "struct_branch_count",
    "struct_loop_count",
    "struct_invocation_count",
    "struct_exception_handler_count",
    "struct_statement_count",
    "struct_is_static",
    "struct_is_async",
    "struct_is_generic",
    "struct_is_expression_bodied",
    "struct_is_constructor",
]


class StructuralFeatureExtractor(BaseFeatureExtractor):
    """Supplementary method-level structural metrics (retained strictly for comparison/combination)."""

    group_name = "structural"
    version = "1.0.0"

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        return extract_fixed_dense_matrix(
            records,
            payload_key="structural_metrics",
            columns=STRUCTURAL_COLUMNS,
            group_name=self.group_name,
            version=self.version,
        )

    def get_feature_names(self) -> list[str]:
        return list(STRUCTURAL_COLUMNS)
