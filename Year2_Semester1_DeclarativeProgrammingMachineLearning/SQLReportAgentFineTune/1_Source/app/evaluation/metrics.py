"""Metric calculations for Text-to-SQL: Execution Accuracy (EX) and Exact Match (EM)."""

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple
from app.utils.sql_sanitizer import normalize_sql


def compute_exact_match(predicted_sql: str, golden_sql: str) -> bool:
    """Calculates structural exact match after normalizing tokens and whitespace."""
    norm_pred = normalize_sql(predicted_sql)
    norm_gold = normalize_sql(golden_sql)
    return norm_pred == norm_gold and bool(norm_pred)


def _normalize_cell(val: Any) -> Any:
    """Normalizes cell values (e.g. floats with rounding tolerance, string lowercasing)."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val):
            return "NAN"
        return round(val, 4)
    if isinstance(val, (int, bool)):
        return val
    return str(val).strip().lower()


def compare_execution_results(
    pred_rows: Sequence[Tuple[Any, ...]],
    gold_rows: Sequence[Tuple[Any, ...]],
    strict_order: bool = False,
) -> bool:
    """Compares SQLite result sets for semantic execution equivalence."""
    if len(pred_rows) != len(gold_rows):
        return False

    norm_pred = [[_normalize_cell(c) for c in row] for row in pred_rows]
    norm_gold = [[_normalize_cell(c) for c in row] for row in gold_rows]

    if strict_order:
        return norm_pred == norm_gold

    # Multiset comparison (unordered comparison)
    try:
        # Convert rows to sorted string representations
        sorted_pred = sorted([str(row) for row in norm_pred])
        sorted_gold = sorted([str(row) for row in norm_gold])
        return sorted_pred == sorted_gold
    except Exception:
        return False


@dataclass
class EvaluationMetrics:
    """Aggregated benchmark metrics."""
    total_samples: int = 0
    valid_sql_count: int = 0
    exact_match_count: int = 0
    execution_match_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def valid_sql_rate(self) -> float:
        """Percentage of generated queries with valid SQL syntax."""
        return round((self.valid_sql_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def exact_match_rate(self) -> float:
        """Percentage of queries matching reference SQL string exactly."""
        return round((self.exact_match_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def execution_accuracy(self) -> float:
        """Primary Metric: Percentage of queries producing identical database outputs."""
        return round((self.execution_match_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def average_latency_ms(self) -> float:
        """Average latency per query in milliseconds."""
        return round(self.total_latency_ms / self.total_samples, 2) if self.total_samples else 0.0

    def to_dict(self) -> dict:
        return {
            "total_samples": self.total_samples,
            "valid_sql_count": self.valid_sql_count,
            "valid_sql_rate": self.valid_sql_rate,
            "exact_match_count": self.exact_match_count,
            "exact_match_rate": self.exact_match_rate,
            "execution_match_count": self.execution_match_count,
            "execution_accuracy": self.execution_accuracy,
            "average_latency_ms": self.average_latency_ms,
        }
