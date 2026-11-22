"""Regression verification for the full 2,400-case evaluation package."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from source.config.settings import get_project_root


def test_full_2400_evaluations_and_package() -> None:
    root = get_project_root()
    full_dir = root / "3_Comparative_Analysis" / "08_Full_Evaluation"
    summary_p = full_dir / "08_Reproducibility" / "full_evaluation_summary.json"
    if not summary_p.exists():
        pytest.skip("Full 2,400-case evaluation package not yet generated.")

    summary = json.loads(summary_p.read_text(encoding="utf-8"))
    assert summary["shared_test_ids_count"] == 1200

    # Verify DB records & identical test ID coverage
    conn = sqlite3.connect(root / "5_Data" / "sqlite" / "research.db")
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        b_ids = {
            r[0]
            for r in conn.execute(
                "SELECT test_id FROM test_executions WHERE experiment_id='exp_baseline_full_v3' AND status='completed'"
            ).fetchall()
        }
        m_ids = {
            r[0]
            for r in conn.execute(
                "SELECT test_id FROM test_executions WHERE experiment_id='exp_mitigated_full_v3' AND status='completed'"
            ).fetchall()
        }
        assert len(b_ids) == 1200
        assert len(m_ids) == 1200
        assert b_ids == m_ids
    finally:
        conn.close()

    # Verify raw responses, 12 charts, human review, and 3 academic reports (MD + PDF)
    assert (root / "1_Penetration" / "04_Raw_Results" / "exp_baseline_full_v3_raw.jsonl").exists()
    assert (root / "3_Comparative_Analysis" / "02_Mitigated" / "exp_mitigated_full_v3_raw.jsonl").exists()

    charts = list((full_dir / "05_Visualizations").glob("*.png"))
    assert len(charts) == 12

    assert (full_dir / "06_Human_Review" / "human_review_annotation_template.csv").exists()
    assert (full_dir / "06_Human_Review" / "human_review_annotation_template.jsonl").exists()

    for name in (
        "Report_A_Baseline_Penetration_Evaluation",
        "Report_B_Fine_Tuned_Model_Evaluation",
        "Report_C_Comparative_Academic_Analysis",
    ):
        assert (full_dir / "07_Reports" / f"{name}.md").exists()
        assert (full_dir / "07_Reports" / f"{name}.pdf").exists()
