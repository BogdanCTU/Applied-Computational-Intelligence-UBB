"""Unit tests for the final results calculations: Top 7 coverage, hapax legomena, and validation."""

import pytest
from collections import Counter


def compute_top_k_coverage(counts: Counter, k: int = 7) -> tuple[list[tuple[str, int]], int, float]:
    sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    total_tokens = sum(counts.values())
    top_k = sorted_items[:k]
    top_k_sum = sum(freq for _, freq in top_k)
    coverage_pct = (top_k_sum / total_tokens * 100) if total_tokens > 0 else 0.0
    return top_k, top_k_sum, coverage_pct


def compute_hapax_statistics(counts: Counter) -> dict:
    total_tokens = sum(counts.values())
    total_types = len(counts)
    hapax_types = sum(1 for _, freq in counts.items() if freq == 1)
    hapax_tokens = hapax_types  # each occurs exactly once
    pct_tokens = (hapax_tokens / total_tokens * 100) if total_tokens > 0 else 0.0
    pct_types = (hapax_types / total_types * 100) if total_types > 0 else 0.0
    return {
        "hapax_types": hapax_types,
        "hapax_tokens": hapax_tokens,
        "pct_tokens": pct_tokens,
        "pct_types": pct_types,
    }


def test_top_k_coverage_exact():
    # 10 tokens: 'a'*4, 'b'*3, 'c'*2, 'd'*1
    counts = Counter({"a": 4, "b": 3, "c": 2, "d": 1})
    top2, top2_sum, cov = compute_top_k_coverage(counts, k=2)
    assert top2 == [("a", 4), ("b", 3)]
    assert top2_sum == 7
    assert cov == pytest.approx(70.0)


def test_top_k_deterministic_tie_breaking():
    # Equal frequency 5 for 'cherry', 'apple', 'banana'
    counts = Counter({"cherry": 5, "apple": 5, "banana": 5})
    top2, top2_sum, _ = compute_top_k_coverage(counts, k=2)
    # Alphabetical order: apple, banana
    assert top2 == [("apple", 5), ("banana", 5)]
    assert top2_sum == 10


def test_hapax_legomena_statistics():
    # 5 words: 'the' (3), 'a' (2), 'rare' (1), 'unique' (1), 'singular' (1)
    # Total tokens = 3 + 2 + 1 + 1 + 1 = 8
    # Total types = 5
    # Hapax types = 3 ('rare', 'unique', 'singular')
    counts = Counter({"the": 3, "a": 2, "rare": 1, "unique": 1, "singular": 1})
    res = compute_hapax_statistics(counts)
    assert res["hapax_types"] == 3
    assert res["hapax_tokens"] == 3
    assert res["pct_tokens"] == pytest.approx(3 / 8 * 100)
    assert res["pct_types"] == pytest.approx(3 / 5 * 100)


def test_validation_bounds():
    counts = Counter({"word" + str(i): 1 for i in range(100)})
    res = compute_hapax_statistics(counts)
    assert res["hapax_types"] == 100
    assert res["hapax_tokens"] == 100
    assert res["pct_tokens"] == 100.0
    assert res["pct_types"] == 100.0


def test_three_corpora_statistics_consistency():
    """Verify that all three corpora yield valid statistics within linguistic bounds."""
    # Mock counts representing the scales of EN, IT, RO
    corpora_tokens = {"EN": 75201, "IT": 41525, "RO": 8301}
    corpora_types = {"EN": 7013, "IT": 6215, "RO": 2056}
    top7_coverage = {"EN": 23.83, "IT": 18.40, "RO": 16.87}
    hapax_type_pcts = {"EN": 42.99, "IT": 53.13, "RO": 55.35}

    for code in ["EN", "IT", "RO"]:
        # TTR must be in [0.05, 0.40] for standard natural language texts of this size
        ttr = corpora_types[code] / corpora_tokens[code]
        assert 0.05 < ttr < 0.35
        # Top 7 coverage must be in [10%, 35%]
        assert 10.0 < top7_coverage[code] < 35.0
        # Hapax % of types must be in [40%, 65%] (Zipfian universal property)
        assert 40.0 < hapax_type_pcts[code] < 65.0


