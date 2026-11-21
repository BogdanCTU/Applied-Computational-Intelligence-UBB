"""Indexer module for Seminar 4 IR System (Part 1).

Constructs, serializes, and manages an Inverted Index mapping terms to
unique matching document identifiers:
    {
        "algorithm": ["CACM-001", "CACM-015"],
        "database": ["CACM-003", "CACM-012"]
    }
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

try:
    from .preprocessing import Document, Preprocessor
except ImportError:
    from preprocessing import Document, Preprocessor


class InvertedIndex:
    """Inverted Index with term-frequency tracking and persistent JSON storage.
    
    Attributes:
        index: Mapping from term -> list of matching document IDs (unique, sorted).
        term_doc_tf: Mapping from term -> {doc_id: term_frequency}.
        doc_lengths: Mapping from doc_id -> total terms in document after preprocessing.
        vocabulary: Set of all unique terms.
        total_tokens_after: Total count of non-stop-word tokens across the corpus.
    """

    def __init__(self) -> None:
        self.index: Dict[str, List[str]] = {}
        self.term_doc_tf: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.doc_lengths: Dict[str, int] = {}
        self.total_tokens_after: int = 0

    @property
    def vocabulary(self) -> Set[str]:
        """Set of unique terms in the index."""
        return set(self.index.keys())

    @property
    def vocabulary_size(self) -> int:
        """Total number of unique indexed terms."""
        return len(self.index)

    @property
    def total_postings(self) -> int:
        """Sum of all postings list lengths."""
        return sum(len(postings) for postings in self.index.values())

    def get_document_frequency(self, term: str) -> int:
        """Return the number of documents containing the term (DF)."""
        return len(self.index.get(term.lower(), []))

    def get_term_frequency(self, term: str, doc_id: str) -> int:
        """Return the occurrence count of a term within a specific document (TF)."""
        return self.term_doc_tf.get(term.lower(), {}).get(doc_id, 0)

    def get_postings(self, term: str) -> List[str]:
        """Return the list of document identifiers matching the term in O(1) time."""
        return list(self.index.get(term.lower(), []))

    def build(self, documents: List[Document], preprocessor: Preprocessor) -> "InvertedIndex":
        """Build the inverted index from a collection of Document objects."""
        self.index.clear()
        self.term_doc_tf.clear()
        self.doc_lengths.clear()
        self.total_tokens_after = 0

        postings_dict: Dict[str, Set[str]] = defaultdict(set)

        for doc in documents:
            tokens = preprocessor.preprocess_text(doc.searchable_text)
            self.doc_lengths[doc.doc_id] = len(tokens)
            self.total_tokens_after += len(tokens)

            tf_counter = Counter(tokens)
            for term, count in tf_counter.items():
                postings_dict[term].add(doc.doc_id)
                self.term_doc_tf[term][doc.doc_id] = count

        # Convert sets to sorted lists for deterministic ordering and uniqueness
        self.index = {term: sorted(list(docs)) for term, docs in sorted(postings_dict.items())}
        return self

    def save(self, file_path: Union[str, Path], save_metadata: bool = True) -> None:
        """Save the inverted index to a persistent JSON representation.
        
        Saves exactly the required logical structure:
            {
                "algorithm": ["CACM-001", "CACM-015"],
                "database": ["CACM-003", "CACM-012"]
            }
        Optionally saves accompanying metadata (TFs, doc lengths) in a sidecar file.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

        if save_metadata:
            meta_path = path.with_name(path.stem + "_metadata.json")
            meta_data = {
                "vocabulary_size": self.vocabulary_size,
                "total_postings": self.total_postings,
                "total_tokens_after": self.total_tokens_after,
                "doc_lengths": self.doc_lengths,
                "term_doc_tf": {term: dict(tf) for term, tf in self.term_doc_tf.items()},
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)

    def load(self, file_path: Union[str, Path]) -> "InvertedIndex":
        """Load inverted index from a persistent JSON file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Index file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            self.index = json.load(f)

        # Ensure postings are unique lists
        self.index = {k: sorted(list(set(v))) for k, v in self.index.items()}

        # Attempt to load sidecar metadata if present
        meta_path = path.with_name(path.stem + "_metadata.json")
        if meta_path.is_file():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
            self.doc_lengths = meta_data.get("doc_lengths", {})
            self.total_tokens_after = meta_data.get("total_tokens_after", 0)
            self.term_doc_tf = defaultdict(dict, meta_data.get("term_doc_tf", {}))
        else:
            # Reconstruct basic TF (binary presence = 1) if metadata is missing
            self.term_doc_tf = defaultdict(dict)
            for term, docs in self.index.items():
                for d in docs:
                    self.term_doc_tf[term][d] = 1

        return self
