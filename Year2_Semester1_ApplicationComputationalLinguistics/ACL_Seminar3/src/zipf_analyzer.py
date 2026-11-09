"""Zipf's Law mathematical analysis and linear regression fitting module for ACL Seminar 3.

Models the power-law relationship:
    f(r) = C / (r ^ s)
Log-transformed:
    log10(f(r)) = log10(C) - s * log10(r) = intercept + slope * log10(r)

Calculates:
- Zipf slope (empirical slope from linregress)
- Zipf exponent (absolute value of slope, s)
- Log-intercept and theoretical constant C = 10^intercept
- Pearson correlation coefficient (r)
- Coefficient of determination (R-squared)
- Two-tailed p-value
- Standard error of the slope
- Both full-distribution fit and top-100 ranks fit
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from scipy import stats

from src.frequency_analyzer import FrequencyDistribution

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZipfRegressionResult:
    """Statistical output of a Zipf linear regression fit."""

    corpus_id: str
    n_points: int
    is_top_n_fit: bool
    top_n_limit: Optional[int]
    slope: float
    zipf_exponent: float
    intercept: float
    constant_c: float
    r_squared: float
    pearson_correlation: float
    p_value: float
    std_err: float
    log_ranks: np.ndarray
    log_frequencies: np.ndarray
    predicted_log_frequencies: np.ndarray

    @property
    def regression_equation_str(self) -> str:
        """Formatted linear regression equation string."""
        sign = "+" if self.intercept >= 0 else "-"
        return f"log10(f) = {self.slope:.4f} * log10(r) {sign} {abs(self.intercept):.4f}"


def fit_zipf_distribution(
    distribution: FrequencyDistribution,
    top_n: Optional[int] = None,
) -> ZipfRegressionResult:
    """Perform ordinary least squares linear regression on log10(rank) vs log10(frequency).

    Parameters
    ----------
    distribution : FrequencyDistribution
        Corpus frequency distribution.
    top_n : Optional[int]
        If provided, fit only ranks 1..top_n (e.g. top 100 ranks).
        If None, fit the complete distribution.

    Returns
    -------
    ZipfRegressionResult
        Regression parameters, goodness of fit metrics, and arrays for plotting.

    Raises
    ------
    ValueError
        If fewer than 2 valid points exist or frequencies/ranks are invalid.
    """
    records = distribution.records
    if top_n is not None and top_n > 0:
        records = records[:top_n]

    if len(records) < 2:
        raise ValueError(
            f"Insufficient data to fit Zipf's Law for corpus '{distribution.corpus_id}'. "
            f"Need at least 2 points, got {len(records)}."
        )

    ranks = np.array([r.rank for r in records], dtype=np.float64)
    frequencies = np.array([r.frequency for r in records], dtype=np.float64)

    # Validate strictly positive values for logarithm
    valid_mask = (ranks > 0) & (frequencies > 0)
    if not np.all(valid_mask):
        logger.warning(
            "Found %d non-positive values in distribution for '%s'; filtering.",
            int(np.sum(~valid_mask)),
            distribution.corpus_id,
        )
        ranks = ranks[valid_mask]
        frequencies = frequencies[valid_mask]

    if len(ranks) < 2:
        raise ValueError(f"Fewer than 2 valid positive points after filtering for '{distribution.corpus_id}'.")

    log_ranks = np.log10(ranks)
    log_freqs = np.log10(frequencies)

    reg = stats.linregress(log_ranks, log_freqs)

    slope = float(reg.slope)
    intercept = float(reg.intercept)
    r_val = float(reg.rvalue)
    p_val = float(reg.pvalue)
    std_err = float(reg.stderr) if reg.stderr is not None else 0.0

    zipf_exponent = abs(slope)
    r_squared = r_val ** 2
    constant_c = float(10.0 ** intercept)

    predicted_log_freqs = intercept + slope * log_ranks

    fit_label = f"top {top_n}" if top_n else "full"
    logger.info(
        "Zipf fit (%s) for '%s': slope=%.4f, s=%.4f, R²=%.4f, r=%.4f, p=%.2e",
        fit_label,
        distribution.corpus_id,
        slope,
        zipf_exponent,
        r_squared,
        r_val,
        p_val,
    )

    return ZipfRegressionResult(
        corpus_id=distribution.corpus_id,
        n_points=len(ranks),
        is_top_n_fit=top_n is not None,
        top_n_limit=top_n,
        slope=slope,
        zipf_exponent=zipf_exponent,
        intercept=intercept,
        constant_c=constant_c,
        r_squared=r_squared,
        pearson_correlation=r_val,
        p_value=p_val,
        std_err=std_err,
        log_ranks=log_ranks,
        log_frequencies=log_freqs,
        predicted_log_frequencies=predicted_log_freqs,
    )


def compare_zipf_fits(
    distribution: FrequencyDistribution,
) -> Tuple[ZipfRegressionResult, ZipfRegressionResult]:
    """Fit both full rank-frequency distribution and top-100 ranks.

    Returns
    -------
    Tuple[ZipfRegressionResult, ZipfRegressionResult]
        (full_fit_result, top100_fit_result)
    """
    full_fit = fit_zipf_distribution(distribution, top_n=None)
    top100_fit = fit_zipf_distribution(distribution, top_n=100)
    return full_fit, top100_fit

