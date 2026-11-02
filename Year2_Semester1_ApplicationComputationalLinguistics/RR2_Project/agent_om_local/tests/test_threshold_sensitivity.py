"""
Unit tests for Step 7A Threshold Sensitivity Analysis.
Verifies metrics calculation, threshold filtering, dummy exclusion,
and retrieval ranking structure.
"""

from unittest.mock import MagicMock
import pytest

from scripts.run_threshold_sensitivity import calculate_metrics, fmt_pair
from src.retrieval.rank_fusion import reciprocal_rank_fusion


class TestThresholdSensitivity:
    def test_calculate_metrics_perfect_match(self):
        ref = {("A", "1"), ("B", "2")}
        pred = {("A", "1"), ("B", "2")}
        m = calculate_metrics(pred, ref)
        assert m["tp"] == 2
        assert m["fp"] == 0
        assert m["fn"] == 0
        assert m["precision"] == 100.0
        assert m["recall"] == 100.0
        assert m["f1"] == 100.0

    def test_calculate_metrics_partial_match(self):
        ref = {("A", "1"), ("B", "2"), ("C", "3")}
        pred = {("A", "1"), ("D", "4")}
        m = calculate_metrics(pred, ref)
        assert m["tp"] == 1
        assert m["fp"] == 1
        assert m["fn"] == 2
        assert m["precision"] == 50.0
        assert m["recall"] == round(1 / 3 * 100, 2)

    def test_calculate_metrics_empty_predictions(self):
        ref = {("A", "1")}
        pred = set()
        m = calculate_metrics(pred, ref)
        assert m["tp"] == 0
        assert m["fp"] == 0
        assert m["fn"] == 1
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0

    def test_fmt_pair(self):
        p = ("http://cmt#Author", "http://confOf#Author")
        assert fmt_pair(p) == "Author = Author"

    def test_rrf_dummy_exclusion_in_sensitivity(self):
        r1 = ["c1", "Entity-Dummy", "c2"]
        r2 = ["c1", "c3"]
        fused = reciprocal_rank_fusion(r1, r2, k=0, exclude_items=["Entity-Dummy"])
        flat_cands = [item for _, items in fused for item in items]
        assert "Entity-Dummy" not in flat_cands
        assert flat_cands[0] == "c1"

