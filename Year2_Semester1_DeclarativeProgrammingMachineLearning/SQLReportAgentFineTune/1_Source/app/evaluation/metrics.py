"""Statistical metric calculations for Text-to-SQL benchmarks.

Implements Execution Accuracy (EX), Exact Match (EM), Valid SQL Rate (VSR),
Error Categorization, and Bootstrap Confidence Intervals.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
from app.utils.sql_sanitizer import normalize_sql


class ErrorCategory:
    NONE = "none"
    SYNTAX_ERROR = "syntax_error"
    SCHEMA_LINKING_ERROR = "schema_linking_error"
    JOIN_ERROR = "join_error"
    EXECUTION_MISMATCH = "execution_mismatch"
    TIMEOUT_ERROR = "timeout_error"


def compute_exact_match(predicted_sql: str, golden_sql: str) -> bool:
    """Calculates structural exact match after normalizing tokens and whitespace."""
    norm_pred = normalize_sql(predicted_sql)
    norm_gold = normalize_sql(golden_sql)
    return norm_pred == norm_gold and bool(norm_pred)


def _normalize_cell(val: Any) -> Any:
    """Normalizes cell values (floats with tolerance, strings stripped and lowercased)."""
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

    # Multiset comparison
    try:
        sorted_pred = sorted([str(row) for row in norm_pred])
        sorted_gold = sorted([str(row) for row in norm_gold])
        return sorted_pred == sorted_gold
    except Exception:
        return False


def classify_sql_error(pred_error: Optional[str], is_exec_match: bool) -> str:
    """Classifies SQL failures into standard diagnostic categories."""
    if is_exec_match:
        return ErrorCategory.NONE
    if not pred_error:
        return ErrorCategory.EXECUTION_MISMATCH

    err = pred_error.lower()
    if "timeout" in err or "interrupted" in err:
        return ErrorCategory.TIMEOUT_ERROR
    if "no such table" in err or "no such column" in err or "ambiguous column" in err:
        return ErrorCategory.SCHEMA_LINKING_ERROR
    if "syntax" in err or "near " in err or "incomplete input" in err:
        return ErrorCategory.SYNTAX_ERROR
    if "join" in err or "on clause" in err:
        return ErrorCategory.JOIN_ERROR
    return ErrorCategory.SYNTAX_ERROR


def compute_bootstrap_ci(
    binary_outcomes: List[int],
    num_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Computes non-parametric bootstrap confidence interval for proportion metric."""
    if not binary_outcomes:
        return 0.0, 0.0

    rng = random.Random(seed)
    n = len(binary_outcomes)
    means = []

    for _ in range(num_bootstrap):
        sample = [binary_outcomes[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(sample) / n * 100.0)

    means.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(alpha / 2.0 * num_bootstrap)
    upper_idx = int((1.0 - alpha / 2.0) * num_bootstrap)

    lower = round(means[max(0, lower_idx)], 2)
    upper = round(means[min(num_bootstrap - 1, upper_idx)], 2)
    return lower, upper


@dataclass
class EvaluationMetrics:
    """Aggregated benchmark metrics with statistical confidence intervals."""
    total_samples: int = 0
    valid_sql_count: int = 0
    exact_match_count: int = 0
    execution_match_count: int = 0
    total_latency_ms: float = 0.0
    error_distribution: Dict[str, int] = field(default_factory=dict)
    binary_ex_outcomes: List[int] = field(default_factory=list)

    @property
    def valid_sql_rate(self) -> float:
        return round((self.valid_sql_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def exact_match_rate(self) -> float:
        return round((self.exact_match_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def execution_accuracy(self) -> float:
        return round((self.execution_match_count / self.total_samples * 100.0), 2) if self.total_samples else 0.0

    @property
    def average_latency_ms(self) -> float:
        return round(self.total_latency_ms / self.total_samples, 2) if self.total_samples else 0.0

    @property
    def bootstrap_ci_95(self) -> Tuple[float, float]:
        return compute_bootstrap_ci(self.binary_ex_outcomes)

    def to_dict(self) -> dict:
        ci_low, ci_high = self.bootstrap_ci_95
        return {
            "total_samples": self.total_samples,
            "valid_sql_count": self.valid_sql_count,
            "valid_sql_rate": self.valid_sql_rate,
            "exact_match_count": self.exact_match_count,
            "exact_match_rate": self.exact_match_rate,
            "execution_match_count": self.execution_match_count,
            "execution_accuracy": self.execution_accuracy,
            "execution_accuracy_ci_95": [ci_low, ci_high],
            "average_latency_ms": self.average_latency_ms,
            "error_distribution": self.error_distribution,
        }
