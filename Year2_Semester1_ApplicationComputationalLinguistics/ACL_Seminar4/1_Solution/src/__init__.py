"""Information Retrieval System (Seminar 4 - Part 1)

Components:
- preprocessing: Dataset parsing, tokenization, stop-word discovery & removal
- indexer: Inverted index construction, persistence, term frequency tracking
- retrieval: Deterministic single-word retrieval using inverted index & TF ranking
- evaluation: P@k calculation and evaluation against ground-truth judgments
"""

from .preprocessing import Document, Preprocessor, load_cacm_collection, extract_alphabetic_tokens, compute_corpus_stop_words
from .indexer import InvertedIndex
from .retrieval import RetrievalSystem, SearchResult
from .evaluation import calculate_precision_at_k, evaluate_queries

__all__ = [
    "Document",
    "Preprocessor",
    "load_cacm_collection",
    "extract_alphabetic_tokens",
    "compute_corpus_stop_words",
    "InvertedIndex",
    "RetrievalSystem",
    "SearchResult",
    "calculate_precision_at_k",
    "evaluate_queries",
]
