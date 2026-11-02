"""
Unit tests for reciprocal merger.
Verifies bidirectional intersection, pair orientation normalization,
dropped pair accounting, and edge cases.
"""

import pytest
from src.matching.merger import ReciprocalMerger


class TestReciprocalMerger:
    @pytest.fixture
    def merger(self):
        return ReciprocalMerger()

    def test_merge_exact_match(self, merger):
        s2t = {("Author", "Author"), ("Person", "Person")}
        t2s = {("Author", "Author"), ("Person", "Person")}
        merged = merger.merge_alignments(s2t, t2s)
        assert merged == {("Author", "Author"), ("Person", "Person")}

    def test_merge_asymmetric_drops(self, merger):
        s2t = {
            ("Author", "Author"),
            ("Person", "Person"),
            ("Paper", "Article"),  # only in s2t
        }
        t2s = {
            ("Author", "Author"),
            ("Person", "Person"),
            ("Conference", "Workshop"),  # only in t2s
        }
        merged = merger.merge_alignments(s2t, t2s)
        assert merged == {("Author", "Author"), ("Person", "Person")}

    def test_merge_with_reversed_target_orientation(self, merger):
        s2t = {
            ("ProgramCommitteeChair", "Chair_PC"),
            ("Author", "Author"),
        }
        # When target-to-source is stored as (target, source):
        t2s_reversed = [
            ("Chair_PC", "ProgramCommitteeChair"),
            ("Author", "Author"),
            ("Organization", "Publisher"),
        ]
        merged = merger.merge_alignments(s2t, t2s_reversed, target_to_source_is_reversed=True)
        assert merged == {
            ("ProgramCommitteeChair", "Chair_PC"),
            ("Author", "Author"),
        }

    def test_analyze_merger(self, merger):
        s2t = [("A", "1"), ("B", "2"), ("C", "3")]
        t2s = [("A", "1"), ("B", "2"), ("D", "4")]

        analysis = merger.analyze_merger(s2t, t2s)
        assert analysis["source_to_target_count"] == 3
        assert analysis["target_to_source_count"] == 3
        assert analysis["merged_count"] == 2
        assert set(analysis["merged_pairs"]) == {("A", "1"), ("B", "2")}
        assert set(analysis["dropped_from_source_pairs"]) == {("C", "3")}
        assert set(analysis["dropped_from_target_pairs"]) == {("D", "4")}

    def test_empty_alignments(self, merger):
        assert merger.merge_alignments([], []) == set()
        assert merger.merge_alignments([("A", "1")], []) == set()
        assert merger.merge_alignments([], [("A", "1")]) == set()

    def test_disjoint_alignments(self, merger):
        s2t = [("A", "1"), ("B", "2")]
        t2s = [("X", "8"), ("Y", "9")]
        assert merger.merge_alignments(s2t, t2s) == set()
