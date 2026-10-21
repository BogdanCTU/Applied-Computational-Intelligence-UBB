"""Metrics, comparison table and plots - identical for every classifier."""

from pathlib import Path

import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)

from src import config


def compute_metrics(y_true, y_pred) -> dict:
    """Binary metrics with 'yes' explicitly set as the positive class."""
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: {len(y_true)} true labels vs {len(y_pred)} predictions.")
    if len(y_true) == 0:
        raise ValueError("Cannot compute metrics on empty input.")
    invalid = set(pd.Series(y_pred).unique()) - set(config.LABELS)
    if invalid:
        raise ValueError(f"Invalid predicted labels: {invalid}")
    kwargs = dict(pos_label=config.POSITIVE_LABEL, zero_division=0)
    # labels=[no, yes] fixes the matrix order: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=config.LABELS).ravel()
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, **kwargs),
        "recall": recall_score(y_true, y_pred, **kwargs),
        "f1": f1_score(y_true, y_pred, **kwargs),
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
    }


def comparison_table(y_true, predictions: dict) -> pd.DataFrame:
    """One row per classifier. `predictions` maps classifier name -> predicted labels."""
    rows = {name: compute_metrics(y_true, pred) for name, pred in predictions.items()}
    return pd.DataFrame(rows).T


def report_text(y_true, y_pred) -> str:
    return classification_report(y_true, y_pred, labels=config.LABELS, zero_division=0)


def save_results(table: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index_label="classifier")


def plot_confusion_matrix(y_true, y_pred, title: str, path: Path) -> None:
    """Save a heatmap of the confusion matrix (rows = actual, columns = predicted)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    matrix = confusion_matrix(y_true, y_pred, labels=config.LABELS)
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                xticklabels=config.LABELS, yticklabels=config.LABELS)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def find_optimal_threshold(
    y_val, proba_val: pd.Series, thresholds: list[float] | None = None
) -> tuple[float, float]:
    """Find the threshold tau that maximizes F1-score on validation data (strictly no test leakage)."""
    import numpy as np

    if thresholds is None:
        thresholds = list(np.linspace(0.10, 0.50, 41))
    best_t = 0.50
    best_f1 = -1.0
    for t in thresholds:
        pred = (proba_val >= t).map(lambda x: config.POSITIVE_LABEL if x else config.NEGATIVE_LABEL)
        f1 = f1_score(y_val, pred, pos_label=config.POSITIVE_LABEL, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = round(float(t), 4)
    return best_t, best_f1


def threshold_sweep_table(y_true, probas: pd.Series, thresholds: list[float]) -> pd.DataFrame:
    """Compute performance metrics across a range of classification thresholds."""
    rows = []
    for t in thresholds:
        pred = (probas >= t).map(lambda x: config.POSITIVE_LABEL if x else config.NEGATIVE_LABEL)
        m = compute_metrics(y_true, pred)
        m["threshold"] = round(float(t), 2)
        rows.append(m)
    return pd.DataFrame(rows).set_index("threshold")


def aggregate_cv_metrics(fold_metrics_list: list[dict]) -> tuple[dict[str, float], dict[str, float]]:
    """Compute mean and sample standard deviation (ddof=1) across cross-validation folds."""
    if not fold_metrics_list:
        raise ValueError("Cannot aggregate empty fold metrics list.")
    keys = ["accuracy", "precision", "recall", "f1", "TN", "FP", "FN", "TP"]
    means = {}
    stds = {}
    for k in keys:
        vals = [float(m[k]) for m in fold_metrics_list]
        means[k] = float(pd.Series(vals).mean())
        stds[k] = float(pd.Series(vals).std(ddof=1)) if len(vals) > 1 else 0.0
    return means, stds


def plot_cv_comparison(summary_df: pd.DataFrame, path: Path) -> None:
    """Save a bar chart with standard deviation error bars comparing classifiers across folds."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    metrics = ["accuracy", "precision", "recall", "f1"]
    metric_labels = ["Accuracy", "Precision (yes)", "Recall (yes)", "F1-Score (yes)"]
    classifiers = list(summary_df.index)

    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor="#ffffff")
    x = np.arange(len(metrics))
    width = 0.26
    colors = ["#2563eb", "#16a34a", "#94a3b8"]

    for i, clf in enumerate(classifiers):
        means = [float(summary_df.loc[clf, f"{m}_mean"]) for m in metrics]
        stds = [float(summary_df.loc[clf, f"{m}_std"]) for m in metrics]
        offset = (i - (len(classifiers) - 1) / 2) * width
        ax.bar(
            x + offset, means, width, yerr=stds, capsize=4,
            label=clf, color=colors[i % len(colors)], alpha=0.9, edgecolor="#334155"
        )

    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontweight="bold", fontsize=10)
    ax.set_ylabel("Score", fontweight="bold", fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.set_title("Stratified 5-Fold Cross-Validation Performance (Mean ± Std)", fontweight="bold", fontsize=12, pad=12)
    ax.legend(loc="lower right", framealpha=0.95)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)

