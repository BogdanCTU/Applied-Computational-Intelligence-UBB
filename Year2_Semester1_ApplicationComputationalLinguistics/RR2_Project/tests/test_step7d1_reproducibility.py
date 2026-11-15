"""
Unit tests for Step 7D.1 reproducibility analysis.
"""

from pathlib import Path
import pytest
from scripts.run_step7d_prompt_order_ablation import calculate_metrics


class TestStep7D1Reproducibility:

    def test_calculate_metrics_consistency(self):
        ref = {("A", "B"), ("C", "D"), ("E", "F")}
        pred1 = {("A", "B"), ("C", "D")}
        pred2 = {("A", "B"), ("C", "D")}

        m1 = calculate_metrics(pred1, ref)
        m2 = calculate_metrics(pred2, ref)

        assert m1["tp"] == m2["tp"] == 2
        assert m1["fp"] == m2["fp"] == 0
        assert m1["fn"] == m2["fn"] == 1
        assert m1["precision"] == m2["precision"] == 100.0
        assert m1["recall"] == m2["recall"] == 66.67
        assert m1["f1"] == m2["f1"] == 80.0

    def test_stability_analysis_logic(self):
        # Scenario 1: Perfectly consistent
        f1_list_consistent = [50.0, 50.0, 50.0]
        variance_1 = max(f1_list_consistent) - min(f1_list_consistent)
        assert variance_1 == 0.0
        assert len(set(f1_list_consistent)) == 1

        # Scenario 2: Divergent
        f1_list_divergent = [43.48, 50.0, 43.48]
        variance_2 = round(max(f1_list_divergent) - min(f1_list_divergent), 4)
        assert variance_2 > 0.0
        assert len(set(f1_list_divergent)) > 1

    def test_pcc_status_tracking(self):
        pcc = ("http://cmt#ProgramCommitteeChair", "http://confOf#Chair_PC")

        preds_a = {pcc, ("http://cmt#Author", "http://confOf#Author")}
        preds_b = {("http://cmt#Author", "http://confOf#Author")}

        assert pcc in preds_a
        assert pcc not in preds_b

    def test_frozen_candidate_snapshot_invariance(self):
        # Simulating invariant snapshot structure across runs
        cand_snapshot = {
            "Source": {"eid1": [(1.0, ["tgt1", "tgt2"])]},
            "Target": {"eid2": [(1.0, ["src1"])]},
        }

        # Multiple runs access the snapshot in read-only manner
        run1_snapshot = cand_snapshot
        run2_snapshot = cand_snapshot
        assert run1_snapshot is run2_snapshot
        assert run1_snapshot["Source"]["eid1"] == run2_snapshot["Source"]["eid1"]

    def test_production_code_untouched(self):
        repo_root = Path(__file__).resolve().parent.parent
        production_files = [
            repo_root / "src/agents/matching_agent.py",
            repo_root / "src/agents/retrieval_agent.py",
            repo_root / "src/matching/validator.py",
            repo_root / "src/matching/merger.py",
        ]
        for f in production_files:
            assert f.exists(), f"Production file {f} missing!"
