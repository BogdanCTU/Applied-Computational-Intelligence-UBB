"""Unit tests for word frequency analysis and rank calculation."""

from __future__ import annotations

import pytest

from src.frequency_analyzer import calculate_frequency_distribution


def test_frequency_calculation_and_counts():
    """Verify exact frequency counts, unique types, and TTR."""
    tokens = ["the", "cat", "sat", "on", "the", "mat", "the", "cat"]
    dist = calculate_frequency_distribution(tokens, corpus_id="test")

    assert dist.total_tokens == 8
    assert dist.unique_words == 5  # the, cat, sat, on, mat
    assert dist.type_token_ratio == pytest.approx(5 / 8, rel=1e-5)
    assert dist.most_frequent_word == "the"
    assert dist.most_frequent_word_count == 3


def test_rank_assignment_and_tie_breaking():
    """Verify rank assignment starts at 1 and equal frequencies are broken alphabetically."""
    # Frequencies:
    # 'apple': 2
    # 'banana': 2
    # 'cherry': 2
    # 'date': 1
    tokens = ["banana", "cherry", "apple", "date", "banana", "cherry", "apple"]
    dist = calculate_frequency_distribution(tokens, corpus_id="ties")

    words_in_order = [r.word for r in dist.records]
    ranks_in_order = [r.rank for r in dist.records]

    assert ranks_in_order == [1, 2, 3, 4]
    # Equal frequency 2 should be sorted alphabetically: apple, banana, cherry
    assert words_in_order == ["apple", "banana", "cherry", "date"]


def test_relative_and_cumulative_frequencies():
    """Verify relative frequency sums to 1.0 and cumulative frequency accumulates correctly."""
    tokens = ["a", "b", "c", "d", "a", "b", "a"]  # a: 3, b: 2, c: 1, d: 1 -> total: 7
    dist = calculate_frequency_distribution(tokens, corpus_id="rel_cum")

    # Sum of relative frequencies must equal 1.0
    rel_sum = sum(r.relative_frequency for r in dist.records)
    assert rel_sum == pytest.approx(1.0, rel=1e-5)

    # Cumulative frequencies: rank 1=3, rank 2=5, rank 3=6, rank 4=7
    assert dist.records[0].cumulative_frequency == 3
    assert dist.records[1].cumulative_frequency == 5
    assert dist.records[2].cumulative_frequency == 6
    assert dist.records[3].cumulative_frequency == 7
    assert dist.records[-1].cumulative_frequency == dist.total_tokens


def test_top_n_extraction():
    """Verify top N extraction returns expected subset."""
    tokens = ["w" + str(i) for i in range(50)] * 2
    dist = calculate_frequency_distribution(tokens, corpus_id="top_n")
    top20 = dist.get_top_n(20)
    assert len(top20) == 20
    assert top20[0].rank == 1
    assert top20[19].rank == 20


def test_empty_tokens_raises_value_error():
    """Verify empty corpus raises descriptive ValueError."""
    with pytest.raises(ValueError, match="Cannot calculate frequency distribution for empty corpus"):
        calculate_frequency_distribution([], corpus_id="empty")

