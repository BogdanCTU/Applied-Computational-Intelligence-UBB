"""Statistical metric calculations for Text-to-SQL benchmarks.

Implements Execution Accuracy (EX), Exact Match (EM), Valid SQL Rate (VSR),
Fine-grained Error Categorization (12 categories), McNemar's Test,
and Paired Bootstrap Confidence Intervals.
"""

import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
from app.utils.sql_sanitizer import normalize_sql


class ErrorCategory:
    NONE = "none"
    SCHEMA_LINKING_ERROR = "schema_linking_error"
    JOIN_ERROR = "join_error"
    FILTER_ERROR = "filter_error"
    AGGREGATION_ERROR = "aggregation_error"
    ORDER_LIMIT_ERROR = "order_limit_error"
    SUBQUERY_ERROR = "subquery_error"
    CTE_ERROR = "cte_error"
    DATE_ERROR = "date_error"
    NULL_ERROR = "null_error"
    DISTINCT_ERROR = "distinct_error"
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_MISMATCH = "semantic_mismatch"
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


def classify_sql_error(
    pred_error: Optional[str] = None,
    is_exec_match: bool = False,
    gold_sql: str = "",
    pred_sql: str = "",
) -> str:
    """Classifies SQL failures into 12 fine-grained diagnostic failure categories."""
    if is_exec_match:
        return ErrorCategory.NONE

    # Case 1: SQLite execution raised an error (non-executable or runtime error)
    if pred_error:
        err = pred_error.lower()
        if "timeout" in err or "interrupted" in err:
            return ErrorCategory.TIMEOUT_ERROR
        if (
            "no such table" in err
            or "no such column" in err
            or "ambiguous column" in err
            or "has no column" in err
        ):
            return ErrorCategory.SCHEMA_LINKING_ERROR
        if "join" in err or "on clause" in err:
            return ErrorCategory.JOIN_ERROR
        if "syntax" in err or "near " in err or "incomplete input" in err or "unrecognized token" in err:
            return ErrorCategory.SYNTAX_ERROR
        return ErrorCategory.SYNTAX_ERROR

    # Case 2: Query executed without SQLite exception, but returned incorrect data
    g = gold_sql.upper()
    p = pred_sql.upper()

    # 1. DISTINCT discrepancy
    if ("DISTINCT" in g) != ("DISTINCT" in p):
        return ErrorCategory.DISTINCT_ERROR

    # 2. Aggregation & GROUP BY / HAVING discrepancy
    g_agg = len(re.findall(r"\b(COUNT|AVG|SUM|MIN|MAX)\b", g))
    p_agg = len(re.findall(r"\b(COUNT|AVG|SUM|MIN|MAX)\b", p))
    if g_agg != p_agg or ("GROUP BY" in g) != ("GROUP BY" in p) or ("HAVING" in g) != ("HAVING" in p):
        return ErrorCategory.AGGREGATION_ERROR

    # 3. Ordering & LIMIT discrepancy
    if (
        ("ORDER BY" in g) != ("ORDER BY" in p)
        or ("LIMIT" in g) != ("LIMIT" in p)
        or ("DESC" in g) != ("DESC" in p)
        or ("ASC" in g) != ("ASC" in p)
    ):
        return ErrorCategory.ORDER_LIMIT_ERROR

    # 4. Subquery discrepancy
    g_sub = len(re.findall(r"\bSELECT\b", g))
    p_sub = len(re.findall(r"\bSELECT\b", p))
    if g_sub != p_sub or ("EXISTS" in g) != ("EXISTS" in p):
        return ErrorCategory.SUBQUERY_ERROR

    # 5. CTE discrepancy
    if ("WITH" in g) != ("WITH" in p):
        return ErrorCategory.CTE_ERROR

    # 6. Dates discrepancy
    date_kws = ["STRFTIME", "DATE(", "JULIANDAY", "YEAR", "MONTH", "DAY"]
    if any(k in g or k in p for k in date_kws):
        return ErrorCategory.DATE_ERROR

    # 7. NULL handling discrepancy
    null_kws = ["IS NULL", "IS NOT NULL", "COALESCE", "IFNULL"]
    if any(k in g or k in p for k in null_kws):
        return ErrorCategory.NULL_ERROR

    # 8. JOIN discrepancy
    g_joins = len(re.findall(r"\bJOIN\b", g))
    p_joins = len(re.findall(r"\bJOIN\b", p))
    if g_joins != p_joins:
        return ErrorCategory.JOIN_ERROR

    # 9. Filter / WHERE condition discrepancy
    if ("WHERE" in g) != ("WHERE" in p) or any(
        op in g != op in p for op in ["LIKE", "BETWEEN", "IN (", "NOT IN"]
    ):
        return ErrorCategory.FILTER_ERROR

    return ErrorCategory.SEMANTIC_MISMATCH


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


def compute_paired_bootstrap_ci(
    baseline_outcomes: Sequence[int],
    tuned_outcomes: Sequence[int],
    num_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Computes non-parametric paired bootstrap confidence interval for Delta Execution Accuracy."""
    n = min(len(baseline_outcomes), len(tuned_outcomes))
    if n == 0:
        return 0.0, 0.0

    rng = random.Random(seed)
    deltas = []

    for _ in range(num_bootstrap):
        indices = [rng.randint(0, n - 1) for _ in range(n)]
        b_acc = sum(baseline_outcomes[i] for i in indices) / n * 100.0
        t_acc = sum(tuned_outcomes[i] for i in indices) / n * 100.0
        deltas.append(t_acc - b_acc)

    deltas.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(alpha / 2.0 * num_bootstrap)
    upper_idx = int((1.0 - alpha / 2.0) * num_bootstrap)

    lower = round(deltas[max(0, lower_idx)], 2)
    upper = round(deltas[min(num_bootstrap - 1, upper_idx)], 2)
    return lower, upper


def compute_mcnemar_test(
    baseline_outcomes: Sequence[int],
    tuned_outcomes: Sequence[int],
) -> Dict[str, Any]:
    """Calculates McNemar's test for paired binary classification outcomes.
    
    Returns contingency matrix, continuity-corrected chi2 statistic, and p-value.
    Uses exact binomial test when discordant pairs (b + c) < 25.
    """
    n = min(len(baseline_outcomes), len(tuned_outcomes))
    both_correct = 0
    base_correct_tuned_wrong = 0  # c
    base_wrong_tuned_correct = 0  # b
    both_wrong = 0

    for i in range(n):
        b = bool(baseline_outcomes[i])
        t = bool(tuned_outcomes[i])
        if b and t:
            both_correct += 1
        elif b and not t:
            base_correct_tuned_wrong += 1
        elif not b and t:
            base_wrong_tuned_correct += 1
        else:
            both_wrong += 1

    b = base_wrong_tuned_correct
    c = base_correct_tuned_wrong
    discordant = b + c
    diff = abs(b - c)
    chi2 = ((diff - 1.0) ** 2) / float(discordant) if (discordant > 0 and diff >= 1.0) else 0.0

    if discordant == 0:
        p_val = 1.0
    elif discordant < 25:
        # Exact two-sided binomial test for small sample sizes
        k = min(b, c)
        p_val = min(1.0, 2.0 * sum(math.comb(discordant, i) * (0.5**discordant) for i in range(k + 1)))
    else:
        # Asymptotic chi-square test with continuity correction
        p_val = math.erfc(math.sqrt(chi2 / 2.0))

    return {
        "contingency_matrix": {
            "both_correct": both_correct,
            "base_wrong_tuned_correct": b,
            "base_correct_tuned_wrong": c,
            "both_wrong": both_wrong,
            "discordant_pairs": discordant,
            "total_pairs": n,
        },
        "chi2_statistic": round(chi2, 4),
        "p_value": round(p_val, 4),
        "significant": p_val < 0.05,
    }


@dataclass
class EvaluationMetrics:
    """Aggregated benchmark metrics with statistical confidence intervals and breakdowns."""

    total_samples: int = 0
    valid_sql_count: int = 0
    executable_sql_count: int = 0
    exact_match_count: int = 0
    execution_match_count: int = 0
    total_latency_ms: float = 0.0
    latencies_ms: List[float] = field(default_factory=list)
    prompt_tokens_list: List[int] = field(default_factory=list)
    completion_tokens_list: List[int] = field(default_factory=list)
    error_distribution: Dict[str, int] = field(default_factory=dict)
    binary_ex_outcomes: List[int] = field(default_factory=list)
    accuracy_by_db: Dict[str, float] = field(default_factory=dict)
    accuracy_by_complexity: Dict[str, float] = field(default_factory=dict)
    accuracy_by_source: Dict[str, float] = field(default_factory=dict)
    # Schema Grounding Metrics (Phase II)
    schema_table_precision: float = 0.0
    schema_table_recall: float = 0.0
    schema_table_f1: float = 0.0
    schema_col_precision: float = 0.0
    schema_col_recall: float = 0.0
    schema_col_f1: float = 0.0
    schema_sql_contingency: Dict[str, int] = field(default_factory=dict)

    @property
    def valid_sql_rate(self) -> float:
        """Format validity rate (parsed as recognized SQL statement)."""
        return (
            round((self.valid_sql_count / self.total_samples * 100.0), 2)
            if self.total_samples
            else 0.0
        )

    @property
    def executable_sql_rate(self) -> float:
        """Executable SQL rate (successfully executes in SQLite without operational/syntax error)."""
        return (
            round((self.executable_sql_count / self.total_samples * 100.0), 2)
            if self.total_samples
            else 0.0
        )

    @property
    def exact_match_rate(self) -> float:
        return (
            round((self.exact_match_count / self.total_samples * 100.0), 2)
            if self.total_samples
            else 0.0
        )

    @property
    def execution_accuracy(self) -> float:
        return (
            round((self.execution_match_count / self.total_samples * 100.0), 2)
            if self.total_samples
            else 0.0
        )

    @property
    def average_latency_ms(self) -> float:
        return (
            round(self.total_latency_ms / self.total_samples, 2)
            if self.total_samples
            else 0.0
        )

    @property
    def median_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        mid = len(s) // 2
        return round((s[mid] if len(s) % 2 != 0 else (s[mid - 1] + s[mid]) / 2.0), 2)

    @property
    def p90_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = int(0.90 * len(s))
        return round(s[min(len(s) - 1, idx)], 2)

    @property
    def avg_prompt_tokens(self) -> float:
        return (
            round(sum(self.prompt_tokens_list) / len(self.prompt_tokens_list), 1)
            if self.prompt_tokens_list
            else 0.0
        )

    @property
    def avg_completion_tokens(self) -> float:
        return (
            round(sum(self.completion_tokens_list) / len(self.completion_tokens_list), 1)
            if self.completion_tokens_list
            else 0.0
        )

    @property
    def bootstrap_ci_95(self) -> Tuple[float, float]:
        return compute_bootstrap_ci(self.binary_ex_outcomes)

    def to_dict(self) -> dict:
        ci_low, ci_high = self.bootstrap_ci_95
        d = {
            "total_samples": self.total_samples,
            "valid_sql_count": self.valid_sql_count,
            "valid_sql_rate": self.valid_sql_rate,
            "executable_sql_count": self.executable_sql_count,
            "executable_sql_rate": self.executable_sql_rate,
            "exact_match_count": self.exact_match_count,
            "exact_match_rate": self.exact_match_rate,
            "execution_match_count": self.execution_match_count,
            "execution_accuracy": self.execution_accuracy,
            "execution_accuracy_ci_95": [ci_low, ci_high],
            "average_latency_ms": self.average_latency_ms,
            "median_latency_ms": self.median_latency_ms,
            "p90_latency_ms": self.p90_latency_ms,
            "avg_prompt_tokens": self.avg_prompt_tokens,
            "avg_completion_tokens": self.avg_completion_tokens,
            "error_distribution": self.error_distribution,
            "accuracy_by_db": self.accuracy_by_db,
            "accuracy_by_complexity": self.accuracy_by_complexity,
            "accuracy_by_source": self.accuracy_by_source,
        }
        if self.schema_table_f1 > 0 or self.schema_col_f1 > 0:
            d["schema_grounding"] = {
                "table_precision": self.schema_table_precision,
                "table_recall": self.schema_table_recall,
                "table_f1": self.schema_table_f1,
                "col_precision": self.schema_col_precision,
                "col_recall": self.schema_col_recall,
                "col_f1": self.schema_col_f1,
                "contingency": self.schema_sql_contingency,
            }
        return d
