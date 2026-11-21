"""Tests for indexer module: Inverted index construction, uniqueness, persistence."""

from pathlib import Path
import sys
import tempfile
import unittest

# Ensure modules can be imported
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "1_Solution"))
sys.path.insert(0, str(root_dir / "1_Solution" / "src"))

from indexer import InvertedIndex
from preprocessing import Document, Preprocessor


class TestIndexer(unittest.TestCase):
    """Test suite for InvertedIndex construction, TF tracking, and JSON I/O."""

    def setUp(self):
        """Prepare sample documents and preprocessor."""
        self.stop_words = {"the", "a", "is", "and"}
        self.preprocessor = Preprocessor(stop_words=self.stop_words)
        self.docs = [
            Document(
                doc_id="CACM-001",
                doc_num=1,
                title="Algorithm Design",
                abstract="The algorithm is fast and efficient. Another algorithm is tested."
            ),
            Document(
                doc_id="CACM-002",
                doc_num=2,
                title="Database Systems",
                abstract="A relational database system. The database is reliable."
            ),
            Document(
                doc_id="CACM-003",
                doc_num=3,
                title="Compiler and Algorithm",
                abstract="A compiler optimization algorithm for computers."
            ),
        ]

    def test_build_inverted_index_structure(self):
        """Test inverted index logical mapping and document uniqueness in postings."""
        index = InvertedIndex().build(self.docs, self.preprocessor)

        # 'algorithm' appears in CACM-001 and CACM-003
        postings = index.get_postings("algorithm")
        self.assertEqual(postings, ["CACM-001", "CACM-003"])

        # 'database' appears only in CACM-002
        postings_db = index.get_postings("database")
        self.assertEqual(postings_db, ["CACM-002"])

        # Check uniqueness: no document should appear twice in any posting list
        for term, docs in index.index.items():
            self.assertEqual(len(docs), len(set(docs)), f"Duplicates found in postings for {term}")

    def test_term_frequency_tracking(self):
        """Test term frequency tracking within documents."""
        index = InvertedIndex().build(self.docs, self.preprocessor)

        # In CACM-001: "algorithm" appears 3 times (Algorithm Design, The algorithm..., Another algorithm...)
        tf_001 = index.get_term_frequency("algorithm", "CACM-001")
        self.assertEqual(tf_001, 3)

        # In CACM-003: "algorithm" appears 2 times (Algorithm in title, algorithm in abstract)
        tf_003 = index.get_term_frequency("algorithm", "CACM-003")
        self.assertEqual(tf_003, 2)

        # In CACM-002: "algorithm" does not appear -> TF = 0
        self.assertEqual(index.get_term_frequency("algorithm", "CACM-002"), 0)

        # In CACM-002: "database" appears 3 times (Database in title, database twice in abstract)
        self.assertEqual(index.get_term_frequency("database", "CACM-002"), 3)

    def test_document_frequency_and_vocab_size(self):
        """Test DF calculations and vocabulary size."""
        index = InvertedIndex().build(self.docs, self.preprocessor)

        self.assertEqual(index.get_document_frequency("algorithm"), 2)
        self.assertEqual(index.get_document_frequency("database"), 1)
        self.assertEqual(index.get_document_frequency("compiler"), 1)
        self.assertEqual(index.get_document_frequency("nonexistent"), 0)

        self.assertGreater(index.vocabulary_size, 0)
        self.assertIn("algorithm", index.vocabulary)
        self.assertNotIn("the", index.vocabulary)  # Stop word must not be in vocab

    def test_save_and_load_persistence(self):
        """Test saving index to JSON and restoring it."""
        index = InvertedIndex().build(self.docs, self.preprocessor)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test_index.json"
            index.save(json_path)

            self.assertTrue(json_path.is_file())

            # Load into a new InvertedIndex instance
            loaded_index = InvertedIndex().load(json_path)

            self.assertEqual(loaded_index.vocabulary_size, index.vocabulary_size)
            self.assertEqual(loaded_index.get_postings("algorithm"), ["CACM-001", "CACM-003"])
            self.assertEqual(loaded_index.get_term_frequency("algorithm", "CACM-001"), 3)
            self.assertEqual(loaded_index.get_document_frequency("database"), 1)


if __name__ == "__main__":
    unittest.main()
