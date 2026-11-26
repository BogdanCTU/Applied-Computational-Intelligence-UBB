"""Control-flow feature extractor."""

from __future__ import annotations

from typing import Any

from scipy import sparse

from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats, extract_fixed_dense_matrix

CFG_COLUMNS = [
    "cfg_available",
    "cfg_succeeded",
    "cfg_endpoint_reachable",
    "cfg_return_stmt_count",
    "cfg_exit_points_count",
    "cfg_branch_nodes",
    "cfg_loop_nodes",
    "cfg_switch_arms",
    "cfg_switch_without_default",
    "cfg_return_paths",
    "cfg_early_return_count",
    "cfg_throw_exit_count",
    "cfg_break_continue_count",
    "cfg_goto_count",
    "cfg_try_count",
    "cfg_catch_count",
    "cfg_empty_catch_count",
    "cfg_broad_catch_count",
    "cfg_conditional_complexity",
    "cfg_max_nesting_depth",
    "cfg_unreachable_post_jump_count",
]


class ControlFlowFeatureExtractor(BaseFeatureExtractor):
    """Extracts method-level control-flow structure and Roslyn AnalyzeControlFlow features."""

    group_name = "control_flow"
    version = "1.0.0"

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        return extract_fixed_dense_matrix(
            records,
            payload_key="cfg_metrics",
            columns=CFG_COLUMNS,
            group_name=self.group_name,
            version=self.version,
        )

    def get_feature_names(self) -> list[str]:
        return list(CFG_COLUMNS)
