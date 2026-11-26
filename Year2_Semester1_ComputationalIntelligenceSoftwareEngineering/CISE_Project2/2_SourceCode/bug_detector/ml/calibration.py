"""Validation-based probability calibration and 3-way BUG / UNCERTAIN / CLEAN thresholding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.metrics import brier_score_loss, f1_score


@dataclass(frozen=True)
class ThresholdCalibrationResult:
    """Calibrated thresholds and validation diagnostics."""

    threshold_low: float
    threshold_center: float
    threshold_high: float
    calibration_method: str
    oof_brier_raw: float
    oof_f1_at_center: float
    oof_uncertain_rate: float
    oof_selective_error: float


def calibrate_three_way_thresholds(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    target_confident_error: float = 0.25,
    min_low: float = 0.15,
    max_high: float = 0.85,
) -> ThresholdCalibrationResult:
    """
    Derive (threshold_low, threshold_center, threshold_high) strictly from OOF validation probabilities:
      1. threshold_center maximizes binary F1 on validation OOF predictions.
      2. threshold_low / threshold_high form an uncertainty band around threshold_center based on
         empirical OOF error rates in probability bins while keeping thresholds well-ordered and
         avoiding degenerate 0% or >60% abstention.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    best_t = 0.50
    best_score_t = -1.0
    for cand in np.linspace(0.30, 0.70, 81):
        preds = (y_prob >= cand).astype(int)
        tp = int(np.sum((preds == 1) & (y_true == 1)))
        tn = int(np.sum((preds == 0) & (y_true == 0)))
        fp = int(np.sum((preds == 1) & (y_true == 0)))
        fn = int(np.sum((preds == 0) & (y_true == 1)))
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = float(f1_score(y_true, preds, zero_division=0))
        # Require non-degenerate specificity >= 0.45 to prevent predict-all-BUG collapse;
        # optimize balanced harmonic/Youden trade-off with F1.
        if spec < 0.45:
            continue
        score = 0.5 * f1 + 0.5 * (0.5 * (rec + spec))
        if score > best_score_t or (abs(score - best_score_t) < 1e-9 and abs(cand - 0.50) < abs(best_t - 0.50)):
            best_score_t = score
            best_t = float(cand)

    if best_score_t < 0:
        # Fallback: maximize balanced accuracy (Youden's J) across [0.30, 0.70]
        best_bal = -1.0
        for cand in np.linspace(0.30, 0.70, 81):
            preds = (y_prob >= cand).astype(int)
            tp = int(np.sum((preds == 1) & (y_true == 1)))
            tn = int(np.sum((preds == 0) & (y_true == 0)))
            fp = int(np.sum((preds == 1) & (y_true == 0)))
            fn = int(np.sum((preds == 0) & (y_true == 1)))
            spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            bal = 0.5 * (rec + spec)
            if bal > best_bal:
                best_bal = bal
                best_t = float(cand)

    best_f1 = float(f1_score(y_true, (y_prob >= best_t).astype(int), zero_division=0))

    # Search uncertainty band [tl, th] around best_t targeting confident error <= target_confident_error
    # while keeping coverage in [0.40, 0.85] so borderline cases are honestly marked UNCERTAIN.
    best_low = max(min_low, round(best_t - 0.07, 3))
    best_high = min(max_high, round(best_t + 0.07, 3))

    candidate_lows = sorted({round(float(x), 3) for x in np.linspace(min_low, max(min_low + 0.02, best_t - 0.03), 18)})
    candidate_highs = sorted({round(float(x), 3) for x in np.linspace(min(max_high - 0.02, best_t + 0.03), max_high, 18)})

    chosen = None
    best_score = -1e9
    for tl in candidate_lows:
        if tl >= best_t:
            continue
        for th in candidate_highs:
            if th <= best_t:
                continue
            confident_mask = (y_prob < tl) | (y_prob > th)
            coverage = float(np.mean(confident_mask))
            if coverage < 0.40 or coverage > 0.88:
                continue
            y_conf_pred = (y_prob[confident_mask] > th).astype(int)
            err = float(np.mean(y_conf_pred != y_true[confident_mask]))
            meets = 1.0 if err <= target_confident_error else 0.0
            objective = meets * 10.0 + coverage - 5.0 * err
            if objective > best_score:
                best_score = objective
                chosen = (tl, th, 1.0 - coverage, err)

    if chosen is not None:
        best_low, best_high, unc_rate, sel_err = chosen
    else:
        conf = (y_prob < best_low) | (y_prob > best_high)
        unc_rate = float(1.0 - np.mean(conf))
        sel_err = float(np.mean((y_prob[conf] > best_high).astype(int) != y_true[conf])) if np.any(conf) else 0.5

    brier_raw = float(brier_score_loss(y_true, y_prob)) if len(np.unique(y_true)) >= 2 else float(np.mean((y_prob - y_true) ** 2))
    return ThresholdCalibrationResult(
        threshold_low=round(best_low, 4),
        threshold_center=round(best_t, 4),
        threshold_high=round(best_high, 4),
        calibration_method="none",
        oof_brier_raw=round(brier_raw, 6),
        oof_f1_at_center=round(best_f1, 6),
        oof_uncertain_rate=round(unc_rate, 6),
        oof_selective_error=round(sel_err, 6),
    )


def apply_three_way_decision(
    probability: float,
    threshold_low: float,
    threshold_high: float,
) -> tuple[Literal["BUG", "CLEAN", "UNCERTAIN"], str]:
    """Map predicted probability into BUG, CLEAN, or UNCERTAIN plus human-readable status."""
    if probability > threshold_high:
        return "BUG", "confident_bug"
    if probability < threshold_low:
        return "CLEAN", "confident_clean"
    return "UNCERTAIN", f"within_uncertainty_band_[{threshold_low:.3f}, {threshold_high:.3f}]"
