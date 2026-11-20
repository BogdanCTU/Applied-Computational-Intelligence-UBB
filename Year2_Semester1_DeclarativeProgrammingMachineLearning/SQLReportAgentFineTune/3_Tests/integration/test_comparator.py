"""Integration tests for benchmark comparator and delta calculation."""

import json
from pathlib import Path
from app.evaluation.comparator import ModelComparator


def test_model_comparator_diff_and_markdown(tmp_path: Path):
    results_dir = tmp_path / "7_Results"
    base_dir = results_dir / "base_run"
    tuned_dir = results_dir / "tuned_run"
    base_dir.mkdir(parents=True)
    tuned_dir.mkdir(parents=True)

    base_summary = {
        "total_samples": 20,
        "valid_sql_count": 18,
        "valid_sql_rate": 90.0,
        "exact_match_count": 8,
        "exact_match_rate": 40.0,
        "execution_match_count": 12,
        "execution_accuracy": 60.0,
        "average_latency_ms": 150.0,
    }
    tuned_summary = {
        "total_samples": 20,
        "valid_sql_count": 20,
        "valid_sql_rate": 100.0,
        "exact_match_count": 12,
        "exact_match_rate": 60.0,
        "execution_match_count": 17,
        "execution_accuracy": 85.0,
        "average_latency_ms": 140.0,
    }

    with open(base_dir / "summary.json", "w") as f:
        json.dump(base_summary, f)
    with open(tuned_dir / "summary.json", "w") as f:
        json.dump(tuned_summary, f)

    comparator = ModelComparator(results_dir=results_dir)
    diff = comparator.compare(baseline_name="base_run", finetuned_name="tuned_run")

    assert diff["delta"]["execution_accuracy"] == 25.0
    assert diff["delta"]["exact_match_rate"] == 20.0
    assert diff["delta"]["valid_sql_rate"] == 10.0

    report = comparator.generate_markdown_report(diff, "base_run", "tuned_run")
    assert "+25.0%" in report
    assert "Execution Accuracy (EX)" in report
