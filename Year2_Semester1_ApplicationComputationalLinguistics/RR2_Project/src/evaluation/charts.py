"""Matplotlib figure builders for Phase 5 reports and PySide6 GUI Evaluation canvas."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import matplotlib
import numpy as np

# Use Agg by default when imported outside a Qt GUI event loop; Figure objects work in both!
if not matplotlib.get_backend().lower().startswith("qt"):
    matplotlib.use("Agg")

from matplotlib.figure import Figure


def build_prf1_comparison_figure(
    experiments: Sequence[Dict[str, Any]],
    title: str = "Agent-OM Replication: Precision, Recall, and F1 Comparison (CMT–ConfOf)",
) -> Figure:
    """Create grouped bar chart comparing Precision, Recall, and F1 (%) across experiments."""
    fig = Figure(figsize=(9.5, 5.2), dpi=160)
    ax = fig.add_subplot(111)

    labels = [str(e.get("short_label", e.get("label", ""))) for e in experiments]
    prec = [float(e.get("precision_pct", 0.0)) for e in experiments]
    rec = [float(e.get("recall_pct", 0.0)) for e in experiments]
    f1 = [float(e.get("f1_pct", 0.0)) for e in experiments]

    x = np.arange(len(labels))
    width = 0.25

    bars_p = ax.bar(x - width, prec, width, label="Precision (%)", color="#2563EB")
    bars_r = ax.bar(x, rec, width, label="Recall (%)", color="#059669")
    bars_f = ax.bar(x + width, f1, width, label="F1 (%)", color="#D97706")

    for bars in (bars_p, bars_r, bars_f):
        for b in bars:
            h = b.get_height()
            ax.annotate(
                f"{h:.1f}",
                xy=(b.get_x() + b.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_ylabel("Percentage (%)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=12, ha="right", fontsize=9)
    ax.set_ylim(0, 108)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    return fig


def build_precision_recall_scatter_figure(
    experiments: Sequence[Dict[str, Any]],
    title: str = "Precision vs. Recall Trade-off with Iso-F1 Contours",
) -> Figure:
    """Create Precision-Recall scatter plot with iso-F1 reference curves."""
    fig = Figure(figsize=(7.5, 5.5), dpi=160)
    ax = fig.add_subplot(111)

    r_grid = np.linspace(1.0, 100.0, 300)
    for f1_target in (20, 40, 60, 80):
        denom = 2.0 * r_grid - f1_target
        valid = denom > 0
        r_v = r_grid[valid]
        p_v = (f1_target * r_v) / denom[valid]
        mask = (p_v >= 0) & (p_v <= 105)
        if np.any(mask):
            ax.plot(r_v[mask], p_v[mask], linestyle=":", color="#9CA3AF", linewidth=1.0)
            idx = np.argmin(np.abs(r_v[mask] - 85.0))
            ax.text(
                r_v[mask][idx],
                min(p_v[mask][idx] + 1.5, 102),
                f"F1={f1_target}%",
                fontsize=7.5,
                color="#6B7280",
            )

    palette = ["#1D4ED8", "#DC2626", "#7C3AED", "#059669", "#D97706", "#0891B2"]
    for idx, exp in enumerate(experiments):
        r_val = float(exp.get("recall_pct", 0.0))
        p_val = float(exp.get("precision_pct", 0.0))
        lbl = str(exp.get("short_label", exp.get("label", f"Exp {idx + 1}")))
        color = palette[idx % len(palette)]
        ax.scatter([r_val], [p_val], s=95, color=color, edgecolors="black", zorder=4, label=lbl)
        ax.annotate(
            f"{lbl} (F1={float(exp.get('f1_pct', 0.0)):.1f}%)",
            xy=(r_val, p_val),
            xytext=(6, 5),
            textcoords="offset points",
            fontsize=8.5,
        )

    ax.set_xlabel("Recall (%)")
    ax.set_ylabel("Precision (%)")
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    return fig


def build_stage_attrition_figure(
    attrition_by_run: Dict[str, Sequence[Dict[str, Any]]],
    title: str = "Stage-by-Stage True Positive Retention Across Pipeline Stages",
) -> Figure:
    """Create stage-by-stage TP retention line/bar chart comparing pipeline attrition."""
    fig = Figure(figsize=(9.8, 5.2), dpi=160)
    ax = fig.add_subplot(111)

    palette = ["#DC2626", "#7C3AED", "#059669", "#2563EB"]
    markers = ["o", "s", "^", "D"]
    stage_labels: List[str] = []

    for idx, (run_label, stages) in enumerate(attrition_by_run.items()):
        if not stage_labels:
            stage_labels = [str(s.get("label", s.get("stage", ""))) for s in stages]
        tps = [int(s.get("tp", 0)) for s in stages]
        x = np.arange(len(tps))
        ax.plot(
            x,
            tps,
            marker=markers[idx % len(markers)],
            linewidth=2.0,
            color=palette[idx % len(palette)],
            label=run_label,
        )
        for xi, yi in zip(x, tps):
            ax.annotate(
                str(yi),
                xy=(xi, yi),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

    if stage_labels:
        ax.set_xticks(np.arange(len(stage_labels)))
        ax.set_xticklabels(stage_labels, rotation=24, ha="right", fontsize=8.5)
    ax.set_ylabel("True Positive Pairs Retained (TP)")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()
    return fig


def build_threshold_sensitivity_figure(
    threshold_rows: Sequence[Dict[str, Any]],
    title: str = "Similarity Threshold Sensitivity Analysis",
) -> Figure:
    """Create Precision / Recall / F1 vs cosine similarity threshold figure."""
    fig = Figure(figsize=(8.2, 4.8), dpi=160)
    ax = fig.add_subplot(111)

    rows = sorted(threshold_rows, key=lambda r: float(r.get("threshold", 0.0)))
    xs = [float(r.get("threshold", 0.0)) for r in rows]
    ps = [float(r.get("precision_pct", r.get("precision", 0.0))) for r in rows]
    rs = [float(r.get("recall_pct", r.get("recall", 0.0))) for r in rows]
    f1s = [float(r.get("f1_pct", r.get("f1", 0.0))) for r in rows]

    ax.plot(xs, ps, marker="o", linewidth=2.0, color="#2563EB", label="Precision (%)")
    ax.plot(xs, rs, marker="s", linewidth=2.0, color="#059669", label="Recall (%)")
    ax.plot(xs, f1s, marker="^", linewidth=2.2, color="#D97706", label="F1 (%)")

    ax.set_xlabel("Cosine Similarity Threshold")
    ax.set_ylabel("Score (%)")
    ax.set_ylim(0, 105)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    return fig


def build_runtime_and_calls_figure(
    experiments: Sequence[Dict[str, Any]],
    title: str = "Execution Runtime (s) and Total LLM Calls Across Runs",
) -> Figure:
    """Create dual-subplot figure comparing execution runtime and LLM call counts."""
    fig = Figure(figsize=(9.5, 4.6), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)

    labels = [str(e.get("short_label", e.get("label", ""))) for e in experiments]
    runtimes = [float(e.get("runtime_s", 0.0)) for e in experiments]
    calls = [int(e.get("llm_calls", 0)) for e in experiments]
    x = np.arange(len(labels))

    b1 = ax1.bar(x, runtimes, color="#0891B2", width=0.55)
    for b in b1:
        h = b.get_height()
        ax1.annotate(
            f"{h:.1f}s" if h > 0 else "Ref",
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax1.set_title("Wall-Clock Runtime (s)", fontsize=10, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.5)
    ax1.grid(axis="y", linestyle="--", alpha=0.35)

    b2 = ax2.bar(x, calls, color="#7C3AED", width=0.55)
    for b in b2:
        h = b.get_height()
        ax2.annotate(
            f"{int(h)}" if h > 0 else "Ref",
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax2.set_title("Total Local LLM Calls", fontsize=10, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.35)

    fig.suptitle(title, fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


def save_figure(fig: Figure, output_path: str | Path, dpi: int = 200) -> Path:
    """Save a Matplotlib Figure cleanly to PNG."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=dpi, bbox_inches="tight")
    return out
