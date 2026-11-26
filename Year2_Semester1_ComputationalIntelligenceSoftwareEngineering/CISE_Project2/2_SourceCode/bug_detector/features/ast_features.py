"""AST syntax-tree feature extractor."""

from __future__ import annotations

from typing import Any

from scipy import sparse

from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats, extract_fixed_dense_matrix

AST_COLUMNS = [
    "ast_node_count",
    "ast_expression_count",
    "ast_statement_count",
    "ast_conditional_expr_count",
    "ast_binary_expr_count",
    "ast_unary_expr_count",
    "ast_assignment_count",
    "ast_compound_assignment_count",
    "ast_invocation_count",
    "ast_member_access_count",
    "ast_element_access_count",
    "ast_object_creation_count",
    "ast_array_or_collection_creation_count",
    "ast_cast_expr_count",
    "ast_as_expr_count",
    "ast_is_pattern_count",
    "ast_lambda_count",
    "ast_interpolated_string_count",
    "ast_await_count",
    "ast_if_stmt_count",
    "ast_else_clause_count",
    "ast_switch_stmt_count",
    "ast_switch_expr_count",
    "ast_for_stmt_count",
    "ast_foreach_stmt_count",
    "ast_while_stmt_count",
    "ast_do_stmt_count",
    "ast_try_stmt_count",
    "ast_catch_clause_count",
    "ast_catch_filter_count",
    "ast_finally_clause_count",
    "ast_using_stmt_count",
    "ast_lock_stmt_count",
    "ast_throw_count",
    "ast_return_stmt_count",
    "ast_yield_stmt_count",
    "ast_local_decl_stmt_count",
    "ast_null_conditional_count",
    "ast_null_coalescing_count",
    "ast_null_coalescing_assign_count",
    "ast_null_comparison_count",
    "ast_is_null_pattern_count",
    "ast_is_not_null_pattern_count",
    "ast_null_forgiving_count",
    "ast_linq_invocation_count",
    "ast_unsafe_or_fixed_count",
    "ast_null_syntax_density",
    "ast_cast_density",
    "ast_exception_density",
]


class AstFeatureExtractor(BaseFeatureExtractor):
    """Extracts Roslyn C# AST expression, statement, null-syntax, and LINQ features."""

    group_name = "ast"
    version = "1.0.0"

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        return extract_fixed_dense_matrix(
            records,
            payload_key="ast_metrics",
            columns=AST_COLUMNS,
            group_name=self.group_name,
            version=self.version,
        )

    def get_feature_names(self) -> list[str]:
        return list(AST_COLUMNS)
