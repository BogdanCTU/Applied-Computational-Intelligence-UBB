"""Comprehensive ML evaluation metrics, calibration curves, and FP/FN error analysis."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold_low: float,
    threshold_center: float,
    threshold_high: float,
    repository_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Compute full binary + 3-way selective metrics, confusion matrix, and calibration bins."""
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    n = len(y_true)
    bug_count = int(np.sum(y_true == 1))
    clean_count = int(np.sum(y_true == 0))
    repo_count = len(set(repository_ids)) if repository_ids else 0

    if n == 0:
        return {
            "sample_count": 0,
            "bug_count": 0,
            "clean_count": 0,
            "repository_count": repo_count,
            "confusion_matrix": [[0, 0], [0, 0]],
        }

    y_pred = (y_prob >= threshold_center).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1]))

    specificity = tn / (tn + fp) if (tn + fp) > 0 else None
    fpr = fp / (fp + tn) if (fp + tn) > 0 else None
    fnr = fn / (fn + tp) if (fn + tp) > 0 else None

    both_classes = len(np.unique(y_true)) >= 2
    roc_auc = float(roc_auc_score(y_true, y_prob)) if both_classes else None
    pr_auc = float(average_precision_score(y_true, y_prob)) if (both_classes and bug_count > 0) else None
    brier = float(brier_score_loss(y_true, y_prob)) if both_classes else float(np.mean((y_prob - y_true) ** 2))

    # 3-way selective evaluation (BUG / CLEAN / UNCERTAIN)
    is_bug = y_prob > threshold_high
    is_clean = y_prob < threshold_low
    is_uncertain = (~is_bug) & (~is_clean)
    uncertain_count = int(np.sum(is_uncertain))
    uncertain_rate = uncertain_count / n

    confident_mask = ~is_uncertain
    if np.any(confident_mask):
        y_true_c = y_true[confident_mask]
        y_pred_c = is_bug[confident_mask].astype(int)
        cm_c = confusion_matrix(y_true_c, y_pred_c, labels=[0, 1])
        tn_c, fp_c, fn_c, tp_c = int(cm_c[0, 0]), int(cm_c[0, 1]), int(cm_c[1, 0]), int(cm_c[1, 1])
        sel_prec = float(precision_score(y_true_c, y_pred_c, zero_division=0)) if (tp_c + fp_c) > 0 else 0.0
        sel_rec = float(recall_score(y_true_c, y_pred_c, zero_division=0)) if (tp_c + fn_c) > 0 else None
        sel_f1 = float(f1_score(y_true_c, y_pred_c, zero_division=0)) if (tp_c + fn_c) > 0 else None
        sel_fpr = float(fp_c / (fp_c + tn_c)) if (fp_c + tn_c) > 0 else None
    else:
        sel_prec = sel_rec = sel_f1 = sel_fpr = None

    cal_bins: list[dict[str, float]] = []
    if both_classes and n >= 20:
        try:
            prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=8, strategy="quantile")
            cal_bins = [
                {"mean_predicted": round(float(pp), 4), "fraction_positive": round(float(pt), 4)}
                for pt, pp in zip(prob_true, prob_pred)
            ]
        except Exception:
            cal_bins = []

    cls_report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["CLEAN", "BUG"],
        output_dict=True,
        zero_division=0,
    )

    return {
        "sample_count": n,
        "bug_count": bug_count,
        "clean_count": clean_count,
        "bug_ratio": round(bug_count / n, 4),
        "repository_count": repo_count,
        "threshold_low": round(threshold_low, 4),
        "threshold_center": round(threshold_center, 4),
        "threshold_high": round(threshold_high, 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4) if (tp + fp) > 0 or bug_count > 0 else 0.0,
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4) if bug_count > 0 else None,
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4) if bug_count > 0 else None,
        "specificity": round(float(specificity), 4) if specificity is not None else None,
        "fpr": round(float(fpr), 4) if fpr is not None else None,
        "fnr": round(float(fnr), 4) if fnr is not None else None,
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "brier_score": round(brier, 4),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "uncertain_count": uncertain_count,
        "uncertain_rate": round(uncertain_rate, 4),
        "confident_bug_count": int(np.sum(is_bug)),
        "confident_clean_count": int(np.sum(is_clean)),
        "selective_precision": round(sel_prec, 4) if sel_prec is not None else None,
        "selective_recall": round(sel_rec, 4) if sel_rec is not None else None,
        "selective_f1": round(sel_f1, 4) if sel_f1 is not None else None,
        "selective_fpr": round(sel_fpr, 4) if sel_fpr is not None else None,
        "calibration_bins": cal_bins,
        "classification_report": cls_report,
    }


def analyze_false_positives_and_negatives(
    records: list[dict[str, Any]],
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold_center: float,
    limit: int = 15,
) -> dict[str, Any]:
    """Extract representative False Positives and False Negatives for error analysis."""
    y_pred = (y_prob >= threshold_center).astype(int)
    fps: list[dict[str, Any]] = []
    fns: list[dict[str, Any]] = []

    for rec, yt, yp_bin, prob in zip(records, y_true, y_pred, y_prob):
        entry = {
            "sample_id": rec["sample_id"],
            "repository_id": rec["repository_id"],
            "file_path": rec["file_path"],
            "class_name": rec["class_name"],
            "method_name": rec["method_name"],
            "label_source": rec["label_source"],
            "bug_type": rec["bug_type"],
            "probability": round(float(prob), 4),
            "logical_loc": rec.get("structural_metrics", {}).get("struct_logical_loc"),
            "cyclomatic_complexity": rec.get("structural_metrics", {}).get("struct_cyclomatic_complexity"),
            "source_preview": (rec.get("source_code") or "")[:320],
        }
        if yt == 0 and yp_bin == 1:
            fps.append(entry)
        elif yt == 1 and yp_bin == 0:
            fns.append(entry)

    fps.sort(key=lambda x: x["probability"], reverse=True)
    fns.sort(key=lambda x: x["probability"])

    return {
        "total_false_positives": len(fps),
        "total_false_negatives": len(fns),
        "highest_confidence_false_positives": fps[:limit],
        "lowest_confidence_false_negatives": fns[:limit],
    }
