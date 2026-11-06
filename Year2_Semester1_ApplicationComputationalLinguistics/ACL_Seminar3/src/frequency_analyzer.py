"""Word frequency analysis module for ACL Seminar 3.

Calculates:
- Token counts, unique types, and Type-Token Ratio (TTR).
- Word frequencies and relative frequencies.
- Deterministic rank assignment with alphabetical tie-breaking.
- Cumulative frequencies.
- Complete frequency distribution export to CSV.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WordFrequencyRecord:
    """Individual word entry in a ranked frequency distribution."""

    rank: int
    word: str
    frequency: int
    relative_frequency: float
    cumulative_frequency: int


@dataclass
class FrequencyDistribution:
    """Complete frequency distribution statistics for a corpus."""

    corpus_id: str
    total_tokens: int
    unique_words: int
    type_token_ratio: float
    records: List[WordFrequencyRecord]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert records to a pandas DataFrame."""
        return pd.DataFrame([asdict(r) for r in self.records])

    def save_csv(self, output_path: Path) -> Path:
        """Export the distribution table to CSV."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        df.to_csv(output_path, index=False)
        logger.info("Saved frequency distribution (%d rows) to %s", len(df), output_path)
        return output_path

    def get_top_n(self, n: int = 20) -> List[WordFrequencyRecord]:
        """Return the top N most frequent words."""
        return self.records[:n]

    @property
    def most_frequent_word(self) -> str:
        """Return the word at rank 1."""
        return self.records[0].word if self.records else ""

    @property
    def most_frequent_word_count(self) -> int:
        """Return the count of the word at rank 1."""
        return self.records[0].frequency if self.records else 0


def calculate_frequency_distribution(
    tokens: Sequence[str],
    corpus_id: str = "corpus",
) -> FrequencyDistribution:
    """Compute ranked frequency distribution with deterministic tie-breaking.

    Tie-breaking rule:
    Primary sort key: descending frequency (-frequency).
    Secondary sort key: ascending alphabetical order (word).

    Parameters
    ----------
    tokens : Sequence[str]
        List of lowercase word tokens.
    corpus_id : str
        Corpus identifier.

    Returns
    -------
    FrequencyDistribution
        Computed distribution containing token counts, TTR, and ranked records.

    Raises
    ------
    ValueError
        If the token list is empty.
    """
    total_tokens = len(tokens)
    if total_tokens == 0:
        raise ValueError(f"Cannot calculate frequency distribution for empty corpus: '{corpus_id}'.")

    counts: Counter[str] = Counter(tokens)
    unique_words = len(counts)
    ttr = unique_words / total_tokens

    # Deterministic sorting: highest frequency first, then alphabetically ascending
    sorted_items: List[Tuple[str, int]] = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    records: List[WordFrequencyRecord] = []
    cumulative = 0
    for rank, (word, freq) in enumerate(sorted_items, start=1):
        cumulative += freq
        rel_freq = freq / total_tokens
        records.append(
            WordFrequencyRecord(
                rank=rank,
                word=word,
                frequency=freq,
                relative_frequency=rel_freq,
                cumulative_frequency=cumulative,
            )
        )

    logger.info(
        "Corpus '%s': %d tokens, %d unique types, TTR = %.4f",
        corpus_id,
        total_tokens,
        unique_words,
        ttr,
    )

    return FrequencyDistribution(
        corpus_id=corpus_id,
        total_tokens=total_tokens,
        unique_words=unique_words,
        type_token_ratio=ttr,
        records=records,
    )

