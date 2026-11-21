"""Retrieval module for Seminar 4 IR System (Part 1).

Implements single-word query retrieval using the inverted index:
- Query validation and preprocessing
- O(1) postings list retrieval via inverted index
- Deterministic ranking: Term Frequency (TF) descending, Document ID ascending
- Retrieval execution timing via time.perf_counter_ns()
- Extraction of Top-3 and Top-7 results
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Sequence

try:
    from .indexer import InvertedIndex
    from .preprocessing import Preprocessor
except ImportError:
    from indexer import InvertedIndex
    from preprocessing import Preprocessor


@dataclass
class SearchResult:
    """Encapsulates the result of a single-word query execution."""
    query_raw: str
    query_term: str
    total_matching: int
    ranked_docs: List[str]
    top_3: List[str]
    top_7: List[str]
    execution_time_ms: float
    doc_tfs: Dict[str, int] = field(default_factory=dict)

    def get_top_k(self, k: int) -> List[str]:
        """Return the top k retrieved document identifiers."""
        return self.ranked_docs[:k]


class RetrievalSystem:
    """IR Search Engine operating strictly over an InvertedIndex.
    
    Ensures:
    - Queries undergo the exact same preprocessing pipeline.
    - Empty queries and multi-term queries are rejected.
    - Inverted index is queried directly (no full-corpus scans).
    - Ranking is deterministic (TF descending, doc_id ascending).
    """

    def __init__(self, index: InvertedIndex, preprocessor: Preprocessor) -> None:
        self.index = index
        self.preprocessor = preprocessor

    def search(
        self,
        query: str,
        measure_time: bool = True
    ) -> SearchResult:
        """Execute a single-word query against the inverted index.
        
        Args:
            query: The raw query string (e.g. "database", "COMPILER").
            measure_time: Whether to time the retrieval operation.
            
        Returns:
            SearchResult with matching count, top-3, top-7, and timing.
            
        Raises:
            ValueError: If the query is empty, multiple words, or a stop word.
        """
        # Validate and preprocess query
        query_term = self.preprocessor.preprocess_query(query)

        t_start = time.perf_counter_ns() if measure_time else 0

        # Retrieve postings list directly from inverted index in O(1)
        matching_docs = self.index.get_postings(query_term)
        total_matching = len(matching_docs)

        if total_matching == 0:
            t_end = time.perf_counter_ns() if measure_time else 0
            elapsed_ms = (t_end - t_start) / 1_000_000 if measure_time else 0.0
            return SearchResult(
                query_raw=query,
                query_term=query_term,
                total_matching=0,
                ranked_docs=[],
                top_3=[],
                top_7=[],
                execution_time_ms=elapsed_ms,
                doc_tfs={},
            )

        # Retrieve TF for each document
        # Ranking criteria:
        # 1. Term frequency (TF) descending (-tf)
        # 2. Document ID ascending (deterministic tie-breaker)
        doc_tfs = {did: self.index.get_term_frequency(query_term, did) for did in matching_docs}

        ranked_docs = sorted(
            matching_docs,
            key=lambda did: (-doc_tfs[did], did)
        )

        t_end = time.perf_counter_ns() if measure_time else 0
        elapsed_ms = (t_end - t_start) / 1_000_000 if measure_time else 0.0

        top_3 = ranked_docs[:3]
        top_7 = ranked_docs[:7]

        return SearchResult(
            query_raw=query,
            query_term=query_term,
            total_matching=total_matching,
            ranked_docs=ranked_docs,
            top_3=top_3,
            top_7=top_7,
            execution_time_ms=elapsed_ms,
            doc_tfs={did: doc_tfs[did] for did in top_7},
        )
