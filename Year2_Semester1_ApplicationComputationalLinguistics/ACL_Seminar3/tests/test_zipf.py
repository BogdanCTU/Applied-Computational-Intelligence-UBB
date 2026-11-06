"""Unit tests for Zipf's Law analysis and linear regression fitting."""

from __future__ import annotations

import numpy as np
import pytest

from src.frequency_analyzer import FrequencyDistribution, WordFrequencyRecord
from src.zipf_analyzer import compare_zipf_fits, fit_zipf_distribution


def _make_synthetic_distribution(
    n_words: int = 150,
    c: float = 5000.0,
    exponent: float = 1.0,
) -> FrequencyDistribution:
    """Helper to generate an exact synthetic power-law distribution f(r) = round(C / r^s)."""
    records = []
    cum = 0
    total_tokens = 0
    for r in range(1, n_words + 1):
        freq = max(1, int(round(c / (r ** exponent))))
        total_tokens += freq
        records.append(
            WordFrequencyRecord(
                rank=r,
                word=f"word_{r}",
                frequency=freq,
                relative_frequency=0.0,  # filled after
                cumulative_frequency=0,
            )
        )

    # Compute rel and cum frequencies
    new_records = []
    for r in records:
        cum += r.frequency
        new_records.append(
            WordFrequencyRecord(
                rank=r.rank,
                word=r.word,
                frequency=r.frequency,
                relative_frequency=r.frequency / total_tokens,
                cumulative_frequency=cum,
            )
        )

    return FrequencyDistribution(
        corpus_id="synthetic",
        total_tokens=total_tokens,
        unique_words=n_words,
        type_token_ratio=n_words / total_tokens,
        records=new_records,
    )


def test_zipf_regression_ideal_power_law():
    """Verify regression on exact synthetic power law with s = 1.0 yields slope ~ -1.0 and R² ~ 1.0."""
    dist = _make_synthetic_distribution(n_words=100, c=10000.0, exponent=1.0)
    res = fit_zipf_distribution(dist)

    assert res.n_points == 100
    assert res.slope == pytest.approx(-1.0, abs=0.05)
    assert res.zipf_exponent == pytest.approx(1.0, abs=0.05)
    assert res.r_squared > 0.99
    assert res.pearson_correlation < -0.99
    assert res.p_value < 1e-10


def test_zipf_regression_arbitrary_exponent():
    """Verify regression correctly recovers a non-unity exponent (s = 1.25)."""
    dist = _make_synthetic_distribution(n_words=100, c=20000.0, exponent=1.25)
    res = fit_zipf_distribution(dist)

    assert res.slope == pytest.approx(-1.25, abs=0.06)
    assert res.zipf_exponent == pytest.approx(1.25, abs=0.06)
    assert res.r_squared > 0.98


def test_compare_zipf_fits_full_vs_top100():
    """Verify full and top-100 fits return separate valid results."""
    dist = _make_synthetic_distribution(n_words=200, c=5000.0, exponent=1.0)
    full_fit, top100_fit = compare_zipf_fits(dist)

    assert full_fit.n_points == 200
    assert full_fit.is_top_n_fit is False
    assert full_fit.top_n_limit is None

    assert top100_fit.n_points == 100
    assert top100_fit.is_top_n_fit is True
    assert top100_fit.top_n_limit == 100


def test_insufficient_data_raises_value_error():
    """Verify that fewer than 2 data points raises ValueError."""
    single_record = [
        WordFrequencyRecord(
            rank=1,
            word="lonely",
            frequency=10,
            relative_frequency=1.0,
            cumulative_frequency=10,
        )
    ]
    dist = FrequencyDistribution(
        corpus_id="single",
        total_tokens=10,
        unique_words=1,
        type_token_ratio=0.1,
        records=single_record,
    )
    with pytest.raises(ValueError, match="Need at least 2 points"):
        fit_zipf_distribution(dist)

