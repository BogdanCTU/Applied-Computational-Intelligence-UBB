"""Tests for preprocessing module: tokenization, stop-word removal, and query validation."""

from pathlib import Path
import sys
import unittest

# Ensure modules can be imported
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "1_Solution"))
sys.path.insert(0, str(root_dir / "1_Solution" / "src"))

from preprocessing import (
    Document,
    Preprocessor,
    compute_corpus_stop_words,
    extract_alphabetic_tokens,
    format_doc_id,
    load_cacm_collection,
    parse_doc_id,
)


class TestPreprocessing(unittest.TestCase):
    """Test suite for preprocessing functions and classes."""

    def test_doc_id_formatting(self):
        """Test document identifier formatting and parsing."""
        self.assertEqual(format_doc_id(1), "CACM-001")
        self.assertEqual(format_doc_id(15), "CACM-015")
        self.assertEqual(format_doc_id(100), "CACM-100")
        self.assertEqual(format_doc_id(1410), "CACM-1410")
        self.assertEqual(parse_doc_id("CACM-001"), 1)
        self.assertEqual(parse_doc_id("CACM-1410"), 1410)

    def test_extract_alphabetic_tokens(self):
        """Test lowercasing and alphabetic tokenization."""
        text = "The quick 123 Brown-Fox jumps over 45.6 Lazy Dogs!"
        tokens = extract_alphabetic_tokens(text)
        expected = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dogs"]
        self.assertEqual(tokens, expected)

    def test_extract_alphabetic_tokens_empty(self):
        """Test token extraction on empty and symbol-only strings."""
        self.assertEqual(extract_alphabetic_tokens(""), [])
        self.assertEqual(extract_alphabetic_tokens("   \n\t  "), [])
        self.assertEqual(extract_alphabetic_tokens("12345 !@#$%^&*()"), [])

    def test_compute_corpus_stop_words(self):
        """Test identifying top N most frequent corpus words."""
        docs = [
            Document("CACM-001", 1, "The algorithm and the database", "The computer and database"),
            Document("CACM-002", 2, "A compiler for the computer", "The algorithm is fast"),
        ]
        # Word counts:
        # the: 5
        # and: 2, database: 2, algorithm: 2, computer: 2
        # a: 1, compiler: 1, for: 1, is: 1, fast: 1
        stop_words, freqs, total_before = compute_corpus_stop_words(docs, num_stop_words=3)
        self.assertEqual(len(stop_words), 3)
        self.assertEqual(stop_words[0], "the")
        self.assertEqual(freqs["the"], 5)
        self.assertEqual(total_before, 18)

    def test_preprocessor_stop_word_removal(self):
        """Test stop word removal without stemming or lemmatization."""
        stop_words = {"the", "of", "a", "and", "to", "is", "in"}
        preprocessor = Preprocessor(stop_words=stop_words)

        text = "The quick algorithms in a database and the optimization of computers"
        tokens = preprocessor.preprocess_text(text)
        # Should remove: the, in, a, and, the, of
        # Remaining: quick, algorithms, database, optimization, computers
        expected = ["quick", "algorithms", "database", "optimization", "computers"]
        self.assertEqual(tokens, expected)
        # Verify no stemming has been applied (e.g. algorithms not stemmed to algorithm)
        self.assertIn("algorithms", tokens)
        self.assertIn("computers", tokens)

    def test_preprocess_query_valid(self):
        """Test valid single-word queries with various casing."""
        preprocessor = Preprocessor(stop_words={"the", "a", "in"})
        self.assertEqual(preprocessor.preprocess_query("Database"), "database")
        self.assertEqual(preprocessor.preprocess_query("COMPILER"), "compiler")
        self.assertEqual(preprocessor.preprocess_query("  algorithm  "), "algorithm")

    def test_preprocess_query_invalid_empty(self):
        """Test query rejection for empty or whitespace query."""
        preprocessor = Preprocessor(stop_words={"the"})
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("")
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("   ")
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("12345 !!!")

    def test_preprocess_query_invalid_stop_word(self):
        """Test query rejection when query consists only of a stop word."""
        preprocessor = Preprocessor(stop_words={"the", "is", "in"})
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("the")
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("THE")

    def test_preprocess_query_invalid_multiple_terms(self):
        """Test rejection of multi-word queries."""
        preprocessor = Preprocessor(stop_words={"the"})
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("database systems")
        with self.assertRaises(ValueError):
            preprocessor.preprocess_query("fast compiler design")

    def test_load_cacm_collection_malformed_graceful(self, tmp_path=None):
        """Test that loader handles incomplete records gracefully."""
        import tempfile
        content = """
.I 1
.T
Only Title Document
.B
CACM 1958
.I 2
.W
Only abstract document without title
.B
CACM 1959
.I 3
.T
Valid Title
.W
Valid Abstract
.X
1 2 3
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(content)
            temp_name = f.name

        try:
            docs = load_cacm_collection(temp_name)
            self.assertEqual(len(docs), 3)
            self.assertEqual(docs[0].doc_id, "CACM-001")
            self.assertEqual(docs[0].title, "Only Title Document")
            self.assertEqual(docs[0].abstract, "")
            self.assertEqual(docs[1].doc_id, "CACM-002")
            self.assertEqual(docs[1].title, "")
            self.assertEqual(docs[1].abstract, "Only abstract document without title")
            self.assertEqual(docs[2].doc_id, "CACM-003")
            self.assertEqual(docs[2].title, "Valid Title")
            self.assertEqual(docs[2].abstract, "Valid Abstract")
        finally:
            Path(temp_name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
