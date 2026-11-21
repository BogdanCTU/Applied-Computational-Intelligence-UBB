"""Academic 300-DPI visualizations (Matplotlib & Seaborn) for baseline and comparative results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)


def generate_baseline_charts(
    records: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    output_dir: Path,
    prefix: str = "baseline",
) -> List[Path]:
    """Generate PNG charts for baseline or mitigated evaluation runs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []
    per_cat = metrics.get("per_category", {})

    # 1. Category Adversarial Failure Rate with 95% Wilson CIs
    cats = list(per_cat.keys())
    rates = [per_cat[c]["adversarial_failure_rate"] * 100.0 for c in cats]
    err_lo = [max(0.0, (per_cat[c]["adversarial_failure_rate"] - per_cat[c]["adversarial_failure_ci"][0]) * 100.0) for c in cats]
    err_hi = [max(0.0, (per_cat[c]["adversarial_failure_ci"][1] - per_cat[c]["adversarial_failure_rate"]) * 100.0) for c in cats]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    y_pos = np.arange(len(cats))
    ax.barh(y_pos, rates, xerr=[err_lo, err_hi], color="#c0392b", alpha=0.85, capsize=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cats])
    ax.invert_yaxis()
    ax.set_xlabel("Adversarial Failure Rate (%) with 95% Wilson CI")
    ax.set_title(f"{prefix.title()} Adversarial Failure Rate by Risk Category")
    ax.set_xlim(0, 105)
    for i, r in enumerate(rates):
        ax.text(min(r + 2.5, 96), i, f"{r:.1f}%", va="center", fontsize=9)
    fig.tight_layout()
    p1 = output_dir / f"{prefix}_category_failure_rates.png"
    fig.savefig(p1, dpi=300)
    plt.close(fig)
    generated.append(p1)

    # 2. Safety Outcome Distribution
    class_counts = metrics.get("classification_counts", {})
    labels = list(class_counts.keys())
    vals = [class_counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    palette = {
        "safe_refusal": "#27ae60",
        "safe_completion": "#2980b9",
        "partial_compliance": "#f39c12",
        "unsafe_compliance": "#c0392b",
        "ambiguous_response": "#7f8c8d",
        "infrastructure_failure": "#8e44ad",
    }
    colors = [palette.get(lbl, "#34495e") for lbl in labels]
    ax.bar([lbl.replace("_", "\n") for lbl in labels], vals, color=colors)
    ax.set_ylabel("Number of Evaluations")
    ax.set_title(f"{prefix.title()} Multi-Dimensional Safety Classification Distribution")
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.02, str(v), ha="center", fontsize=9)
    fig.tight_layout()
    p2 = output_dir / f"{prefix}_outcome_distribution.png"
    fig.savefig(p2, dpi=300)
    plt.close(fig)
    generated.append(p2)

    # 3. Severity-Based Analysis
    per_sev = metrics.get("per_severity", {})
    sevs = [s for s in ("critical", "high", "medium", "low") if s in per_sev]
    if sevs:
        non_safe = [per_sev[s]["non_safe_rate"] * 100.0 for s in sevs]
        safe = [per_sev[s]["safe_rate"] * 100.0 for s in sevs]
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        x = np.arange(len(sevs))
        ax.bar(x, safe, label="Safe Rate (%)", color="#27ae60", alpha=0.85)
        ax.bar(x, non_safe, bottom=safe, label="Non-Safe / Failure Rate (%)", color="#e74c3c", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels([s.title() for s in sevs])
        ax.set_ylabel("Percentage (%)")
        ax.set_title(f"{prefix.title()} Safety vs Failure Rate by Severity")
        ax.legend(loc="lower right")
        fig.tight_layout()
        p3 = output_dir / f"{prefix}_severity_analysis.png"
        fig.savefig(p3, dpi=300)
        plt.close(fig)
        generated.append(p3)

    # 4. Expected Behavior vs Observed Outcome Confusion Matrix
    df = pd.DataFrame(records)
    if not df.empty:
        df["expected_group"] = np.where(df["expected_behavior"] == "refuse_and_redirect", "Adversarial\n(Should Refuse)", "Benign Control\n(Should Complete)")
        df["observed_group"] = df["classification"].replace({
            "safe_refusal": "Safe Refusal",
            "safe_completion": "Safe Completion",
            "partial_compliance": "Partial Compliance",
            "unsafe_compliance": "Unsafe Compliance",
            "ambiguous_response": "Ambiguous",
            "infrastructure_failure": "Infra Failure",
        })
        ct = pd.crosstab(df["expected_group"], df["observed_group"])
        fig, ax = plt.subplots(figsize=(8.5, 4.2))
        sns.heatmap(ct, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
        ax.set_title(f"{prefix.title()} Expected vs. Observed Behavior Matrix")
        ax.set_ylabel("Expected Behavior")
        ax.set_xlabel("Observed Classification")
        fig.tight_layout()
        p4 = output_dir / f"{prefix}_confusion_matrix.png"
        fig.savefig(p4, dpi=300)
        plt.close(fig)
        generated.append(p4)

        # 5. Category x Attack Pattern Non-Safe Heatmap
        adv_df = df[df["expected_behavior"] == "refuse_and_redirect"].copy()
        if not adv_df.empty:
            adv_df["failed"] = (~adv_df["is_safe"]).astype(int)
            piv = adv_df.pivot_table(index="category", columns="attack_pattern", values="failed", aggfunc="mean", fill_value=0.0)
            fig, ax = plt.subplots(figsize=(13, 6.5))
            sns.heatmap(piv * 100.0, annot=True, fmt=".0f", cmap="Reds", vmin=0, vmax=100, ax=ax)
            ax.set_title(f"{prefix.title()} Non-Safe Rate (%) Heatmap: Category vs. Attack Pattern")
            ax.set_ylabel("Risk Category")
            ax.set_xlabel("Attack Pattern")
            plt.xticks(rotation=35, ha="right", fontsize=8)
            fig.tight_layout()
            p5 = output_dir / f"{prefix}_failure_heatmap.png"
            fig.savefig(p5, dpi=300)
            plt.close(fig)
            generated.append(p5)

    return generated


def generate_comparative_charts(
    baseline_metrics: Dict[str, Any],
    mitigated_metrics: Dict[str, Any],
    comparison: Dict[str, Any],
    output_dir: Path,
) -> List[Path]:
    """Generate comparative baseline-vs-mitigated PNG visualizations."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []
    cat_rows = comparison.get("categories", [])

    if cat_rows:
        cats = [r["display_name"] for r in cat_rows]
        base_vals = [r["baseline_afr"] * 100.0 for r in cat_rows]
        mit_vals = [r["mitigated_afr"] * 100.0 for r in cat_rows]

        x = np.arange(len(cats))
        width = 0.38
        fig, ax = plt.subplots(figsize=(12.5, 5.8))
        ax.bar(x - width / 2, base_vals, width, label="Baseline (qwen3.5:4b)", color="#c0392b", alpha=0.88)
        ax.bar(x + width / 2, mit_vals, width, label="Mitigated (qwen3.5:4b-safety)", color="#27ae60", alpha=0.88)
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Adversarial Failure Rate (%)")
        ax.set_title("Baseline vs. Fine-Tuned Mitigated Model: Adversarial Failure Rate by Category")
        ax.set_ylim(0, 105)
        ax.legend()
        fig.tight_layout()
        p1 = output_dir / "comparative_category_afr.png"
        fig.savefig(p1, dpi=300)
        plt.close(fig)
        generated.append(p1)

        # 2. Benign Task Completion Rate & Over-Refusal Preservation
        b_btcr = [r["baseline_btcr"] * 100.0 for r in cat_rows]
        m_btcr = [r["mitigated_btcr"] * 100.0 for r in cat_rows]
        fig, ax = plt.subplots(figsize=(12.5, 5.2))
        ax.bar(x - width / 2, b_btcr, width, label="Baseline Benign Completion (%)", color="#2980b9", alpha=0.85)
        ax.bar(x + width / 2, m_btcr, width, label="Mitigated Benign Completion (%)", color="#16a085", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Benign Task Completion Rate (%)")
        ax.set_title("Over-Refusal Regression Check: Benign Task Completion by Category")
        ax.set_ylim(0, 105)
        ax.legend()
        fig.tight_layout()
        p2 = output_dir / "comparative_benign_preservation.png"
        fig.savefig(p2, dpi=300)
        plt.close(fig)
        generated.append(p2)

    # 3. Overall Summary Metrics Bar Comparison
    bm = baseline_metrics.get("metrics", {})
    mm = mitigated_metrics.get("metrics", {})
    metric_keys = [
        ("adversarial_failure_rate", "Adversarial\nFailure Rate"),
        ("unsafe_compliance_rate", "Unsafe\nCompliance"),
        ("safe_response_rate", "Safe Response\nRate"),
        ("benign_task_completion_rate", "Benign\nCompletion"),
        ("over_refusal_rate", "Over-Refusal\nRate"),
        ("prompt_injection_success_rate", "Prompt Inj.\nSuccess"),
        ("tool_authorization_violation_rate", "Tool Violation\nRate"),
    ]
    labels = [lbl for _, lbl in metric_keys]
    bv = [bm.get(k, 0.0) * 100.0 for k, _ in metric_keys]
    mv = [mm.get(k, 0.0) * 100.0 for k, _ in metric_keys]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.bar(x - 0.19, bv, 0.38, label="Baseline (qwen3.5:4b)", color="#c0392b", alpha=0.85)
    ax.bar(x + 0.19, mv, 0.38, label="Mitigated (qwen3.5:4b-safety)", color="#27ae60", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Overall Safety, Over-Refusal & Agent Boundary Metrics: Baseline vs. Mitigated")
    ax.set_ylim(0, 108)
    ax.legend()
    fig.tight_layout()
    p3 = output_dir / "comparative_overall_metrics.png"
    fig.savefig(p3, dpi=300)
    plt.close(fig)
    generated.append(p3)

    return generated
