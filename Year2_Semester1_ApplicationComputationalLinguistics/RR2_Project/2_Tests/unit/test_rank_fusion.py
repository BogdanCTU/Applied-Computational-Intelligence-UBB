"""Unit tests for Reciprocal Rank Fusion (RRF) matching Agent-OM."""

import pytest
from src.retrieval.rank_fusion import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """Test suite for reciprocal_rank_fusion."""

    def test_single_ranking_k0(self):
        """Verify RRF with k=0 gives 1/pos scores: 1.0, 0.5, 0.3333..."""
        ranking = ["A", "B", "C"]
        fused = reciprocal_rank_fusion(ranking, k=0)
        assert len(fused) == 3
        # Check scores
        score_a, items_a = fused[0]
        score_b, items_b = fused[1]
        score_c, items_c = fused[2]
        assert score_a == pytest.approx(1.0)
        assert items_a == ["A"]
        assert score_b == pytest.approx(0.5)
        assert items_b == ["B"]
        assert score_c == pytest.approx(1.0 / 3.0)
        assert items_c == ["C"]

    def test_multi_ranking_accumulation(self):
        """Verify items present in multiple rankings accumulate reciprocal ranks."""
        r1 = ["A", "B"]
        r2 = ["B", "A"]
        # A: 1/1 + 1/2 = 1.5
        # B: 1/2 + 1/1 = 1.5
        fused = reciprocal_rank_fusion(r1, r2, k=0)
        assert len(fused) == 1
        score, items = fused[0]
        assert score == pytest.approx(1.5)
        # Tie-breaking must be lexicographical: ['A', 'B']
        assert items == ["A", "B"]

    def test_tie_breaking_lexicographical(self):
        """Verify identical scores are tie-broken alphabetically."""
        r1 = ["Z", "M", "A"]
        # All rank 1 from different lists? If single list, scores differ.
        # Let's give three items identical score across 3 lists
        l1 = ["Z"]
        l2 = ["M"]
        l3 = ["A"]
        # Z: 1.0, M: 1.0, A: 1.0
        fused = reciprocal_rank_fusion(l1, l2, l3, k=0)
        assert len(fused) == 1
        score, items = fused[0]
        assert score == pytest.approx(1.0)
        assert items == ["A", "M", "Z"]

    def test_exclusion_of_dummy_items(self):
        """Verify Entity-Dummy and null placeholders are filtered out."""
        r1 = ["A", "Entity-Dummy", "B"]
        r2 = ["Entity-Dummy", "C"]
        fused = reciprocal_rank_fusion(r1, r2, k=0, exclude_items=["Entity-Dummy"])
        # A was rank 1 in r1 -> 1.0
        # B was rank 2 (after dummy skipped) -> 1/2 = 0.5
        # C was rank 1 in r2 (after dummy skipped) -> 1.0
        items_all = [item for _, items in fused for item in items]
        assert "Entity-Dummy" not in items_all

    def test_standard_rrf_k60(self):
        """Verify standard RRF with k=60 produces 1/(60+pos)."""
        r1 = ["A", "B"]
        fused = reciprocal_rank_fusion(r1, k=60)
        score_a, _ = fused[0]
        score_b, _ = fused[1]
        assert score_a == pytest.approx(1.0 / 61.0)
        assert score_b == pytest.approx(1.0 / 62.0)

    def test_empty_or_none_rankings(self):
        """Verify handling of empty or None rankings."""
        assert reciprocal_rank_fusion([], None, []) == []
        assert reciprocal_rank_fusion() == []

