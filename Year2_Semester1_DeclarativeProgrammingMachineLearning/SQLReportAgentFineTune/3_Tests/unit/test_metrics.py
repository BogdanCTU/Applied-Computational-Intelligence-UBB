"""Unit tests for Execution Accuracy (EX) and Exact Match (EM) metrics."""

from app.evaluation.metrics import (
    EvaluationMetrics,
    compare_execution_results,
    compute_exact_match,
)


def test_compute_exact_match():
    q1 = "SELECT id, name FROM users WHERE age > 18"
    q2 = "select id, name from users where age > 18;"
    q3 = "SELECT name, id FROM users WHERE age > 18"
    assert compute_exact_match(q1, q2) is True
    assert compute_exact_match(q1, q3) is False


def test_compare_execution_results_unordered():
    res1 = [(1, "Alice", 100.0), (2, "Bob", 200.0)]
    res2 = [(2, "bob", 200.00001), (1, "alice", 100.0)]
    assert compare_execution_results(res1, res2, strict_order=False) is True


def test_compare_execution_results_ordered_strict():
    res1 = [(1, "Alice"), (2, "Bob")]
    res2 = [(2, "Bob"), (1, "Alice")]
    assert compare_execution_results(res1, res2, strict_order=True) is False


def test_evaluation_metrics_rates():
    m = EvaluationMetrics(
        total_samples=10,
        valid_sql_count=9,
        exact_match_count=4,
        execution_match_count=8,
        total_latency_ms=1000.0,
    )
    assert m.valid_sql_rate == 90.0
    assert m.exact_match_rate == 40.0
    assert m.execution_accuracy == 80.0
    assert m.average_latency_ms == 100.0
