"""Integration tests verifying Phase I benchmark artifact persistence and schema integrity."""

import json
from pathlib import Path
from app.core.config import get_project_root


def test_phase1_benchmark_artifacts_exist_and_valid():
    root = get_project_root()
    results_dir = root / "7_Results"

    required_runs = [
        "phase1_baseline_unseen200",
        "phase1_exp_a_lora_r8_unseen200",
        "phase1_exp_b_lora_r16_unseen200",
        "phase1_exp_c_lora_r32_unseen200",
        "phase1_baseline_known100",
        "phase1_exp_b_lora_r16_known100",
    ]

    for run_name in required_runs:
        run_dir = results_dir / run_name
        assert run_dir.exists(), f"Missing run directory: {run_dir}"

        summary_file = run_dir / "summary.json"
        details_file = run_dir / "detailed_samples.json"

        assert summary_file.exists(), f"Missing summary: {summary_file}"
        assert details_file.exists(), f"Missing detailed samples: {details_file}"

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        expected_count = 100 if "known100" in run_name else 200
        assert summary["total_samples"] == expected_count
        assert 0.0 <= summary["execution_accuracy"] <= 100.0
        assert 0.0 <= summary["valid_sql_rate"] <= 100.0
        assert summary["average_latency_ms"] > 0
        assert "execution_accuracy_ci_95" in summary
        assert "accuracy_by_complexity" in summary
        assert "error_distribution" in summary

        with open(details_file, "r", encoding="utf-8") as f:
            details = json.load(f)

        assert len(details) == expected_count
        for sample in details[:10]:
            assert "example_id" in sample
            assert "db_id" in sample
            assert "is_execution_match" in sample
            assert "error_category" in sample


def test_phase1_comparisons_exist_and_valid():
    root = get_project_root()
    comp_dir = root / "7_Results" / "comparisons"

    required_comparisons = [
        "phase1_baseline_unseen200_vs_phase1_exp_a_lora_r8_unseen200",
        "phase1_baseline_unseen200_vs_phase1_exp_b_lora_r16_unseen200",
        "phase1_baseline_unseen200_vs_phase1_exp_c_lora_r32_unseen200",
        "phase1_baseline_known100_vs_phase1_exp_b_lora_r16_known100",
    ]

    for comp_name in required_comparisons:
        json_file = comp_dir / f"{comp_name}.json"
        csv_file = comp_dir / f"{comp_name}.csv"
        md_file = comp_dir / f"{comp_name}.md"

        assert json_file.exists(), f"Missing comparison JSON: {json_file}"
        assert csv_file.exists(), f"Missing comparison CSV: {csv_file}"
        assert md_file.exists(), f"Missing comparison Markdown: {md_file}"

        with open(json_file, "r", encoding="utf-8") as f:
            comp_data = json.load(f)

        assert "delta" in comp_data
        assert "mcnemar_test" in comp_data
        assert "paired_bootstrap_ci_95" in comp_data["delta"]
