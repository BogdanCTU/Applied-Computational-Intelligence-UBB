"""Tests for evaluation module: Precision@k, denominator conventions, export formats."""

from pathlib import Path
import sys
import tempfile
import unittest

# Ensure modules can be imported
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "1_Solution"))
sys.path.insert(0, str(root_dir / "1_Solution" / "src"))

from evaluation import (
    calculate_precision_at_k,
    create_default_relevance_judgments,
    export_results_to_csv,
    export_results_to_json,
    QueryEvaluationResult,
)


class TestEvaluation(unittest.TestCase):
    """Test suite for IR evaluation metrics and data exports."""

    def test_precision_at_k_standard(self):
        """Test Precision@k calculation under standard conditions."""
        retrieved = ["DOC-1", "DOC-2", "DOC-3", "DOC-4", "DOC-5", "DOC-6", "DOC-7"]
        relevant = {"DOC-1", "DOC-3", "DOC-5"}

        # Top 3: DOC-1 (rel), DOC-2 (not), DOC-3 (rel) -> 2/3
        p3 = calculate_precision_at_k(retrieved, relevant, 3)
        self.assertAlmostEqual(p3, 2.0 / 3.0)

        # Top 7: DOC-1, 3, 5 are relevant -> 3/7
        p7 = calculate_precision_at_k(retrieved, relevant, 7)
        self.assertAlmostEqual(p7, 3.0 / 7.0)

    def test_precision_at_k_fewer_than_k_retrieved(self):
        """Test denominator convention when retrieved documents count is less than k.
        
        The standard Cranfield/TREC convention requires dividing by k.
        """
        # Only 2 documents retrieved
        retrieved = ["DOC-1", "DOC-2"]
        relevant = {"DOC-1", "DOC-2"}

        # Even though all retrieved are relevant, for k=3: 2 / 3 = 0.6667
        p3 = calculate_precision_at_k(retrieved, relevant, 3)
        self.assertAlmostEqual(p3, 2.0 / 3.0)

        # For k=7: 2 / 7 = 0.2857
        p7 = calculate_precision_at_k(retrieved, relevant, 7)
        self.assertAlmostEqual(p7, 2.0 / 7.0)

    def test_precision_at_k_zero_relevant(self):
        """Test precision when none of the retrieved documents are relevant."""
        retrieved = ["DOC-1", "DOC-2", "DOC-3"]
        relevant = {"DOC-99"}

        p3 = calculate_precision_at_k(retrieved, relevant, 3)
        self.assertEqual(p3, 0.0)

    def test_precision_at_k_invalid_k(self):
        """Test handling of invalid k values (<= 0)."""
        retrieved = ["DOC-1", "DOC-2"]
        relevant = {"DOC-1"}
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, 0), 0.0)
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, -1), 0.0)

    def test_export_results_json_and_csv(self):
        """Test serializing evaluation results to JSON and CSV."""
        sample_results = [
            QueryEvaluationResult(
                query_word="database",
                matching_documents=14,
                top_3=["CACM-2876", "CACM-2816", "CACM-2817"],
                top_7=["CACM-2876", "CACM-2816", "CACM-2817", "CACM-2882", "CACM-2957", "CACM-3087", "CACM-3164"],
                precision_at_3=1.0,
                precision_at_7=1.0,
                retrieval_time_ms=0.005,
                median_retrieval_time_ms=0.004,
                relevant_retrieved_at_3=3,
                relevant_retrieved_at_7=7,
                top_7_tfs={"CACM-2876": 7, "CACM-2816": 4},
                top_7_relevance_details={"CACM-2876": True, "CACM-2816": True},
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "results.json"
            csv_file = Path(tmpdir) / "results.csv"

            export_results_to_json(sample_results, json_file)
            export_results_to_csv(sample_results, csv_file)

            self.assertTrue(json_file.is_file())
            self.assertTrue(csv_file.is_file())

            # Verify CSV content
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("query_word", content)
                self.assertIn("database", content)
                self.assertIn("1.0000", content)


if __name__ == "__main__":
    unittest.main()
