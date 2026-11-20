"""Unit tests for paired statistics (McNemar, paired bootstrap) and fine-grained error taxonomy."""

from app.evaluation.metrics import (
    ErrorCategory,
    classify_sql_error,
    compute_mcnemar_test,
    compute_paired_bootstrap_ci,
)


def test_mcnemar_contingency_and_significance():
    # Symmetric outcomes: no change
    base = [1, 0, 1, 0, 1, 1, 0, 0]
    tuned = [1, 0, 1, 0, 1, 1, 0, 0]
    res = compute_mcnemar_test(base, tuned)
    assert res["chi2_statistic"] == 0.0
    assert res["p_value"] == 1.0
    assert not res["significant"]

    # Highly asymmetrical outcomes (tuned significantly worse)
    base_large = [1] * 80 + [0] * 20
    tuned_large = [0] * 70 + [1] * 10 + [0] * 20
    res_large = compute_mcnemar_test(base_large, tuned_large)
    assert res_large["chi2_statistic"] > 3.84
    assert res_large["p_value"] < 0.05
    assert res_large["significant"]


def test_paired_bootstrap_ci():
    base = [1] * 50 + [0] * 50
    tuned = [1] * 30 + [0] * 70
    low, high = compute_paired_bootstrap_ci(base, tuned, num_bootstrap=500, seed=42)
    # Delta is around -20%
    assert low < 0.0
    assert high < 0.0
    assert low <= -10.0


def test_fine_grained_error_taxonomy():
    # None when execution matches
    assert classify_sql_error(None, is_exec_match=True) == ErrorCategory.NONE

    # Schema linking
    assert (
        classify_sql_error("sqlite3.OperationalError: no such column: age", is_exec_match=False)
        == ErrorCategory.SCHEMA_LINKING_ERROR
    )

    # Distinct error
    assert (
        classify_sql_error(
            None,
            is_exec_match=False,
            gold_sql="SELECT DISTINCT name FROM users;",
            pred_sql="SELECT name FROM users;",
        )
        == ErrorCategory.DISTINCT_ERROR
    )

    # Aggregation error
    assert (
        classify_sql_error(
            None,
            is_exec_match=False,
            gold_sql="SELECT department, count(*) FROM employees GROUP BY department;",
            pred_sql="SELECT department, count(*) FROM employees;",
        )
        == ErrorCategory.AGGREGATION_ERROR
    )

    # Order/Limit error
    assert (
        classify_sql_error(
            None,
            is_exec_match=False,
            gold_sql="SELECT name FROM users ORDER BY age DESC LIMIT 5;",
            pred_sql="SELECT name FROM users ORDER BY age ASC LIMIT 5;",
        )
        == ErrorCategory.ORDER_LIMIT_ERROR
    )
