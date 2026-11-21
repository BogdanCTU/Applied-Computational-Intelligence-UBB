"""Tests for retrieval module: Single-word query search, TF ranking, determinism."""

from pathlib import Path
import sys
import unittest

# Ensure modules can be imported
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "1_Solution"))
sys.path.insert(0, str(root_dir / "1_Solution" / "src"))

from indexer import InvertedIndex
from preprocessing import Document, Preprocessor
from retrieval import RetrievalSystem


class TestRetrieval(unittest.TestCase):
    """Test suite for single-word retrieval and deterministic ranking."""

    def setUp(self):
        """Prepare sample documents and retrieval engine."""
        self.stop_words = {"the", "a", "is", "in", "and"}
        self.preprocessor = Preprocessor(stop_words=self.stop_words)

        # 4 documents with varying TF for 'algorithm':
        # CACM-001: TF=1
        # CACM-002: TF=3
        # CACM-003: TF=3 (Tie with CACM-002; doc_id order should break tie: 002 before 003)
        # CACM-004: TF=0
        self.docs = [
            Document("CACM-001", 1, "Algorithm Analysis", "This document mentions algorithm once."),
            Document("CACM-002", 2, "Algorithm Study", "The algorithm algorithm algorithm is repeated three times."),
            Document("CACM-003", 3, "Algorithm Theory", "An algorithm algorithm algorithm in computing."),
            Document("CACM-004", 4, "Database Systems", "A relational database storage."),
        ]
        self.index = InvertedIndex().build(self.docs, self.preprocessor)
        self.engine = RetrievalSystem(self.index, self.preprocessor)

    def test_single_word_retrieval_success(self):
        """Test retrieving documents for a valid term."""
        res = self.engine.search("database")
        self.assertEqual(res.query_term, "database")
        self.assertEqual(res.total_matching, 1)
        self.assertEqual(res.top_3, ["CACM-004"])
        self.assertEqual(res.top_7, ["CACM-004"])

    def test_ranking_determinism_tf_and_doc_id(self):
        """Test that documents are ranked by TF descending, then doc_id ascending."""
        res = self.engine.search("algorithm")
        self.assertEqual(res.total_matching, 3)

        # Both CACM-002 and CACM-003 have TF=3, so CACM-002 comes first (secondary sort)
        # CACM-001 has TF=1, so it comes third.
        expected_ranking = ["CACM-002", "CACM-003", "CACM-001"]
        self.assertEqual(res.ranked_docs, expected_ranking)
        self.assertEqual(res.top_3, expected_ranking)
        self.assertEqual(res.top_7, expected_ranking)

    def test_nonexistent_term_retrieval(self):
        """Test that searching for an unknown term returns 0 matches gracefully."""
        res = self.engine.search("quantum")
        self.assertEqual(res.total_matching, 0)
        self.assertEqual(res.ranked_docs, [])
        self.assertEqual(res.top_3, [])
        self.assertEqual(res.top_7, [])

    def test_rejection_of_empty_and_multiword_queries(self):
        """Test that queries violating single-word constraints are rejected."""
        with self.assertRaises(ValueError):
            self.engine.search("")
        with self.assertRaises(ValueError):
            self.engine.search("algorithm database")
        with self.assertRaises(ValueError):
            self.engine.search("the")

    def test_case_insensitivity(self):
        """Test that retrieval is case-insensitive."""
        res_lower = self.engine.search("algorithm")
        res_upper = self.engine.search("ALGORITHM")
        res_mixed = self.engine.search("AlgORithM")

        self.assertEqual(res_lower.ranked_docs, res_upper.ranked_docs)
        self.assertEqual(res_lower.ranked_docs, res_mixed.ranked_docs)

    def test_execution_time_recorded(self):
        """Test that execution timing is measured and non-negative."""
        res = self.engine.search("algorithm", measure_time=True)
        self.assertGreaterEqual(res.execution_time_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
