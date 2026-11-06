"""Data visualization module for ACL Seminar 3.

Generates high-resolution (300 DPI) publication-quality figures:
- Graph 1: English (Frankenstein) vs. Italian (Pinocchio) log-log rank-frequency.
- Graph 2: English comparison (Frankenstein vs. Brown Corpus) log-log rank-frequency.
- Graph 3: Individual corpus distributions with fitted regression lines (3 separate plots).
- Graph 4: Top 20 most frequent words for all three corpora.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

# Set non-interactive backend for headless execution across Windows, Linux, macOS
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.frequency_analyzer import FrequencyDistribution
from src.zipf_analyzer import ZipfRegressionResult

logger = logging.getLogger(__name__)

# Color palette: distinct, accessible, professional
COLOR_FRANKENSTEIN = "#1f77b4"  # Steel Blue
COLOR_PINOCCHIO = "#d62728"     # Crimson Red
COLOR_BROWN = "#2ca02c"         # Forest Green
COLOR_REGRESSION = "#333333"    # Charcoal for fit line


def _apply_plot_style() -> None:
    """Configure matplotlib global typography and layout settings."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.titlesize": 14,
            "figure.autolayout": False,
        }
    )


def plot_english_vs_italian(
    en_res: ZipfRegressionResult,
    it_res: ZipfRegressionResult,
    en_label: str = "Frankenstein (English, 1818)",
    it_label: str = "Pinocchio (Italian, 1883)",
    output_path: Optional[Path] = None,
) -> Path:
    """Generate Graph 1: Log-log rank-frequency comparison between English and Italian.

    Parameters
    ----------
    en_res : ZipfRegressionResult
        Zipf regression results for Frankenstein.
    it_res : ZipfRegressionResult
        Zipf regression results for Pinocchio.
    en_label : str
        Legend display label for English corpus.
    it_label : str
        Legend display label for Italian corpus.
    output_path : Optional[Path]
        Target image path.

    Returns
    -------
    Path
        Saved image path.
    """
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=(8.5, 6.0), dpi=300)

    # English data
    ax.scatter(
        en_res.log_ranks,
        en_res.log_frequencies,
        s=12,
        color=COLOR_FRANKENSTEIN,
        alpha=0.65,
        label=f"{en_label}\n(Slope = {en_res.slope:.4f}, s = {en_res.zipf_exponent:.4f}, R² = {en_res.r_squared:.4f})",
        rasterized=True,
    )
    # English linear fit
    ax.plot(
        en_res.log_ranks,
        en_res.predicted_log_frequencies,
        color=COLOR_FRANKENSTEIN,
        linestyle="--",
        linewidth=1.8,
        alpha=0.9,
    )

    # Italian data
    ax.scatter(
        it_res.log_ranks,
        it_res.log_frequencies,
        s=12,
        color=COLOR_PINOCCHIO,
        alpha=0.65,
        label=f"{it_label}\n(Slope = {it_res.slope:.4f}, s = {it_res.zipf_exponent:.4f}, R² = {it_res.r_squared:.4f})",
        rasterized=True,
    )
    # Italian linear fit
    ax.plot(
        it_res.log_ranks,
        it_res.predicted_log_frequencies,
        color=COLOR_PINOCCHIO,
        linestyle=":",
        linewidth=1.8,
        alpha=0.9,
    )

    ax.set_title("Graph 1: Zipf's Law Log-Log Rank-Frequency: English vs. Italian", pad=12, fontweight="bold")
    ax.set_xlabel(r"$\log_{10}(\text{Word Rank } r)$", labelpad=8)
    ax.set_ylabel(r"$\log_{10}(\text{Word Frequency } f)$", labelpad=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", edgecolor="#cccccc")

    fig.tight_layout()

    if output_path is None:
        output_path = Path("results/graphs/graph1_english_vs_italian.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info("Saved Graph 1 to %s", output_path)
    return output_path


def plot_english_comparison(
    en_res: ZipfRegressionResult,
    brown_res: ZipfRegressionResult,
    en_label: str = "Frankenstein (Shelley, 1818)",
    brown_label: str = "Brown Corpus (American English, 1961)",
    output_path: Optional[Path] = None,
) -> Path:
    """Generate Graph 2: Comparison between literary English and modern Brown Corpus.

    Parameters
    ----------
    en_res : ZipfRegressionResult
        Zipf results for Frankenstein.
    brown_res : ZipfRegressionResult
        Zipf results for Brown Corpus.
    en_label : str
        Label for literary English corpus.
    brown_label : str
        Label for modern comparison corpus.
    output_path : Optional[Path]
        Target image path.

    Returns
    -------
    Path
        Saved image path.
    """
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=(8.5, 6.0), dpi=300)

    # Frankenstein
    ax.scatter(
        en_res.log_ranks,
        en_res.log_frequencies,
        s=12,
        color=COLOR_FRANKENSTEIN,
        alpha=0.65,
        label=f"{en_label}\n(Slope = {en_res.slope:.4f}, s = {en_res.zipf_exponent:.4f}, R² = {en_res.r_squared:.4f})",
        rasterized=True,
    )
    ax.plot(
        en_res.log_ranks,
        en_res.predicted_log_frequencies,
        color=COLOR_FRANKENSTEIN,
        linestyle="--",
        linewidth=1.8,
        alpha=0.9,
    )

    # Brown Corpus
    ax.scatter(
        brown_res.log_ranks,
        brown_res.log_frequencies,
        s=12,
        color=COLOR_BROWN,
        alpha=0.65,
        label=f"{brown_label}\n(Slope = {brown_res.slope:.4f}, s = {brown_res.zipf_exponent:.4f}, R² = {brown_res.r_squared:.4f})",
        rasterized=True,
    )
    ax.plot(
        brown_res.log_ranks,
        brown_res.predicted_log_frequencies,
        color=COLOR_BROWN,
        linestyle="-.",
        linewidth=1.8,
        alpha=0.9,
    )

    ax.set_title("Graph 2: Zipf's Law Comparison: Literary English vs. Brown Corpus", pad=12, fontweight="bold")
    ax.set_xlabel(r"$\log_{10}(\text{Word Rank } r)$", labelpad=8)
    ax.set_ylabel(r"$\log_{10}(\text{Word Frequency } f)$", labelpad=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", edgecolor="#cccccc")

    fig.tight_layout()

    if output_path is None:
        output_path = Path("results/graphs/graph2_english_comparison.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info("Saved Graph 2 to %s", output_path)
    return output_path


def plot_individual_distribution(
    res: ZipfRegressionResult,
    title_corpus_name: str,
    color: str,
    output_path: Path,
) -> Path:
    """Generate Graph 3: Individual corpus rank-frequency scatter and fitted regression line.

    Parameters
    ----------
    res : ZipfRegressionResult
        Zipf regression results for the corpus.
    title_corpus_name : str
        Formatted corpus name for the title.
    color : str
        Hex color code for data points.
    output_path : Path
        Target image path.

    Returns
    -------
    Path
        Saved image path.
    """
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=(8.0, 5.5), dpi=300)

    # Scatter points
    ax.scatter(
        res.log_ranks,
        res.log_frequencies,
        s=14,
        color=color,
        alpha=0.7,
        label="Observed Word Distribution",
        rasterized=True,
    )

    # Linear regression line
    ax.plot(
        res.log_ranks,
        res.predicted_log_frequencies,
        color=COLOR_REGRESSION,
        linestyle="-",
        linewidth=2.0,
        label=(
            f"Fitted OLS Regression\n"
            f"{res.regression_equation_str}\n"
            f"Slope = {res.slope:.4f} (s = {res.zipf_exponent:.4f})\n"
            f"R² = {res.r_squared:.4f}, p < 1e-10"
        ),
    )

    ax.set_title(f"Graph 3: Zipf Fit – {title_corpus_name}", pad=12, fontweight="bold")
    ax.set_xlabel(r"$\log_{10}(\text{Word Rank } r)$", labelpad=8)
    ax.set_ylabel(r"$\log_{10}(\text{Word Frequency } f)$", labelpad=8)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", edgecolor="#cccccc")

    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info("Saved individual distribution plot to %s", output_path)
    return output_path


def plot_top20_words_comparison(
    distributions: Dict[str, FrequencyDistribution],
    output_path: Optional[Path] = None,
) -> Path:
    """Generate Graph 4: Side-by-side horizontal bar chart of top 20 words for each corpus.

    Parameters
    ----------
    distributions : Dict[str, FrequencyDistribution]
        Mapping from corpus_id to FrequencyDistribution.
    output_path : Optional[Path]
        Target image path.

    Returns
    -------
    Path
        Saved image path.
    """
    _apply_plot_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 7.5), dpi=300, sharey=False)

    corpus_configs = [
        ("frankenstein", "Frankenstein (English)", COLOR_FRANKENSTEIN, axes[0]),
        ("pinocchio", "Pinocchio (Italian)", COLOR_PINOCCHIO, axes[1]),
        ("brown", "Brown Corpus (Am. English)", COLOR_BROWN, axes[2]),
    ]

    for corpus_id, title, color, ax in corpus_configs:
        dist = distributions[corpus_id]
        top20 = dist.get_top_n(20)

        # Reverse order so highest frequency appears at the top
        words = [r.word for r in reversed(top20)]
        counts = [r.frequency for r in reversed(top20)]
        ranks = [r.rank for r in reversed(top20)]

        y_positions = np.arange(len(words))
        bars = ax.barh(y_positions, counts, color=color, alpha=0.85, height=0.7)

        # Label ticks with words
        ax.set_yticks(y_positions)
        ax.set_yticklabels(words, fontsize=9.5)
        ax.set_title(title, fontweight="bold", pad=10, fontsize=11)
        ax.set_xlabel("Frequency Count", labelpad=6)
        ax.grid(axis="x", linestyle="--", alpha=0.5)

        # Add frequency values at the bar tips
        max_c = max(counts) if counts else 1
        for bar, count in zip(bars, counts):
            ax.text(
                count + (max_c * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{count}",
                va="center",
                ha="left",
                fontsize=8,
                color="#333333",
            )
        ax.set_xlim(0, max_c * 1.18)

    fig.suptitle("Graph 4: Top 20 Most Frequent Words Across Corpora", fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    if output_path is None:
        output_path = Path("results/graphs/graph4_top20_words.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info("Saved Graph 4 to %s", output_path)
    return output_path

