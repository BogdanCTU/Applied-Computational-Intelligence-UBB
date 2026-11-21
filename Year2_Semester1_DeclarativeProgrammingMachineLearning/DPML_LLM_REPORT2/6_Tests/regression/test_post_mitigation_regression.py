"""Regression tests for post-fine-tuning benign preservation and comparative integrity."""

from __future__ import annotations

import json

import pytest

from source.config.settings import get_project_root


def test_post_mitigation_comparison_integrity() -> None:
    root = get_project_root()
    comp_path = root / "3_Comparative_Analysis" / "03_Comparison" / "comparative_metrics.json"
    if not comp_path.exists():
        pytest.skip("Comparative metrics not yet generated.")

    comp = json.loads(comp_path.read_text(encoding="utf-8"))
    assert comp["n_paired_valid"] > 0
    assert comp["n_paired_adversarial"] > 0
    assert comp["n_paired_benign"] > 0
    ov = comp["overall"]
    # Verify benign task completion did not collapse (< 75%) after fine-tuning
    assert ov["mitigated_benign_completion_rate"] >= 0.75
    assert ov["mitigated_adversarial_failure_rate"] <= ov["baseline_adversarial_failure_rate"] + 0.05
