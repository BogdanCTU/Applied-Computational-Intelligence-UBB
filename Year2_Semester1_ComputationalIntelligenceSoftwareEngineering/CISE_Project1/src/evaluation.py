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
