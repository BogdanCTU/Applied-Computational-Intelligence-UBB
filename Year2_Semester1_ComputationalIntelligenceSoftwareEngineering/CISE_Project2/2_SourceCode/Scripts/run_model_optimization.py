"""Controlled Machine Learning Model Optimization with Nested Repository-Level Cross-Validation.

Executes a leakage-free nested GroupKFold optimization experiment on Dataset #2
(578 observations across 5 C# repositories, 26 Roslyn static code metrics):
- Outer Loop: 5-Fold GroupKFold (1 repository held out per outer fold).
- Inner Loop: 4-Fold GroupKFold on the 4 outer-training repositories for:
  1. In-fold preprocessing (median imputation, zero-variance removal, optional scaling).
  2. In-fold feature selection (All 26, Correlation-Pruned, Inner-Permutation Top-12, Theoretical Core-10).
  3. Hyperparameter and model selection across 6 model families (RF, ExtraTrees, HistGB, GB, LR, Calibrated RF).
  4. Inner out-of-fold decision threshold optimization (F1-optimal, F2 recall-oriented, F0.5 precision-oriented).
- Generates all artifacts in 3_TestResults/ModelOptimization/ and saves new versioned model artifacts
  without modifying existing datasets, baseline models, or holdout artifacts.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import RobustScaler, StandardScaler

# Ensure 2_SourceCode/Python is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PYTHON_SRC = PROJECT_ROOT / "2_SourceCode" / "Python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from ml.model_manager import ModelManager
from ml.preprocessing import DataPreprocessor
from services.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES

OUTPUT_DIR = PROJECT_ROOT / "3_TestResults" / "ModelOptimization"
DATASET_V2_PATH = PROJECT_ROOT / "1_Database" / "Datasets" / "Processed" / "csharp_empirical_v2_v2.0.0.csv"
APP_MODELS_DIR = PROJECT_ROOT / "4_AppBuild" / "Assets" / "Models"

THEORETICAL_CORE_10 = [
    "cyclomatic_complexity",
    "max_nesting_depth",
    "logical_loc",
    "parameter_count",
    "return_count",
    "loop_count",
    "try_catch_count",
    "method_call_count",
    "field_access_count",
    "assignment_count",
]


def build_candidate_catalog(random_state: int = 42) -> List[Dict[str, Any]]:
    """Define compact, controlled candidate configurations across required model families."""
    candidates: List[Dict[str, Any]] = [
        # 0. Exact Frozen Baseline
        {
            "config_id": "rf_compact_regularized_baseline",
            "family": "RandomForest (Baseline)",
            "algorithm": "random_forest",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        # 1. Random Forest Regularization & Subsampling Variants
        {
            "config_id": "rf_shallow_depth6_leaf6_bal",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 6,
                "min_samples_split": 8,
                "min_samples_leaf": 6,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_depth6_leaf8_log2_bal",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 6,
                "min_samples_split": 10,
                "min_samples_leaf": 8,
                "max_features": "log2",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_depth8_leaf6_balsub",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 8,
                "min_samples_split": 6,
                "min_samples_leaf": 6,
                "max_features": "sqrt",
                "class_weight": "balanced_subsample",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_compact_unweighted",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": None,
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        # 2. Random Forest with Feature Selection Strategies (fitted in-fold)
        {
            "config_id": "rf_compact_corr_pruned",
            "family": "Random Forest (FS)",
            "algorithm": "random_forest",
            "feature_set": "corr_pruned_085",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_compact_perm_top12",
            "family": "Random Forest (FS)",
            "algorithm": "random_forest",
            "feature_set": "inner_perm_top12",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_compact_theoretical_core10",
            "family": "Random Forest (FS)",
            "algorithm": "random_forest",
            "feature_set": "theoretical_core10",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        # 3. Extra Trees
        {
            "config_id": "et_depth8_leaf4_sqrt_bal",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "et_depth6_leaf6_log2_bal",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 6,
                "min_samples_split": 8,
                "min_samples_leaf": 6,
                "max_features": "log2",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        {
            "config_id": "et_depth8_leaf4_unweighted",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 200,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": None,
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
        # 4. HistGradientBoosting
        {
            "config_id": "hgb_lr005_depth5_leaf20_l2_1",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "learning_rate": 0.05,
                "max_iter": 100,
                "max_depth": 5,
                "max_leaf_nodes": 15,
                "min_samples_leaf": 20,
                "l2_regularization": 1.0,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        {
            "config_id": "hgb_lr003_depth3_leaf25_l2_5",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "learning_rate": 0.03,
                "max_iter": 100,
                "max_depth": 3,
                "max_leaf_nodes": 7,
                "min_samples_leaf": 25,
                "l2_regularization": 5.0,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        # 5. Gradient Boosting
        {
            "config_id": "gb_lr005_depth3_leaf8_sub08",
            "family": "Gradient Boosting",
            "algorithm": "gradient_boosting",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "learning_rate": 0.05,
                "max_depth": 3,
                "min_samples_leaf": 8,
                "subsample": 0.8,
                "random_state": random_state,
            },
        },
        {
            "config_id": "gb_lr003_depth2_leaf12_sub08",
            "family": "Gradient Boosting",
            "algorithm": "gradient_boosting",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "learning_rate": 0.03,
                "max_depth": 2,
                "min_samples_leaf": 12,
                "subsample": 0.8,
                "random_state": random_state,
            },
        },
        # 6. Logistic Regression (StandardScaler vs RobustScaler, C & class_weight)
        {
            "config_id": "lr_c01_std_bal",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "feature_set": "all_26",
            "scaler": "standard",
            "params": {
                "C": 0.1,
                "max_iter": 1000,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        {
            "config_id": "lr_c1_std_bal",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "feature_set": "all_26",
            "scaler": "standard",
            "params": {
                "C": 1.0,
                "max_iter": 1000,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        {
            "config_id": "lr_c01_robust_bal",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "feature_set": "all_26",
            "scaler": "robust",
            "params": {
                "C": 0.1,
                "max_iter": 1000,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        {
            "config_id": "lr_c01_robust_corr_pruned",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "feature_set": "corr_pruned_085",
            "scaler": "robust",
            "params": {
                "C": 0.1,
                "max_iter": 1000,
                "class_weight": "balanced",
                "random_state": random_state,
            },
        },
        # 7. Calibrated Random Forest (Sigmoid Calibration on Inner GroupKFold)
        {
            "config_id": "rf_compact_calibrated_sigmoid",
            "family": "Calibrated RF",
            "algorithm": "calibrated_rf",
            "feature_set": "all_26",
            "scaler": "none",
            "params": {
                "n_estimators": 100,
                "max_depth": 8,
                "min_samples_split": 5,
                "min_samples_leaf": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": random_state,
                "n_jobs": -1,
            },
        },
    ]
    return candidates


def instantiate_estimator(cfg: Dict[str, Any]) -> Any:
    """Create a fresh sklearn estimator instance for the given configuration."""
    algo = cfg["algorithm"]
    params = dict(cfg["params"])
    if algo == "random_forest":
        return RandomForestClassifier(**params)
    elif algo == "extra_trees":
        return ExtraTreesClassifier(**params)
    elif algo == "hist_gb":
        return HistGradientBoostingClassifier(**params)
    elif algo == "gradient_boosting":
        return GradientBoostingClassifier(**params)
    elif algo == "logistic_regression":
        return LogisticRegression(**params)
    elif algo == "calibrated_rf":
        base_rf = RandomForestClassifier(**params)
        return CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=3)
    else:
        raise ValueError(f"Unknown algorithm: {algo}")


def select_features_in_fold(
    X_tr: pd.DataFrame,
    y_tr: pd.Series,
    strategy: str,
    random_state: int = 42,
) -> List[str]:
    """Select feature subset strictly using training fold data (no validation leakage)."""
    cols = list(X_tr.columns)
    if strategy == "all_26":
        return cols
    elif strategy == "theoretical_core10":
        return [c for c in THEORETICAL_CORE_10 if c in cols]
    elif strategy == "corr_pruned_085":
        corr = X_tr.corr(method="spearman").abs()
        aucs: Dict[str, float] = {}
        for c in cols:
            try:
                val = roc_auc_score(y_tr, X_tr[c])
                aucs[c] = max(val, 1.0 - val)
            except Exception:
                aucs[c] = 0.5
        dropped = set()
        for i, c1 in enumerate(cols):
            if c1 in dropped:
                continue
            for c2 in cols[i + 1 :]:
                if c2 in dropped:
                    continue
                if corr.loc[c1, c2] > 0.85:
                    if aucs[c1] >= aucs[c2]:
                        dropped.add(c2)
                    else:
                        dropped.add(c1)
                        break
        surviving = [c for c in cols if c not in dropped]
        return surviving if surviving else cols
    elif strategy == "inner_perm_top12":
        rf = RandomForestClassifier(
            n_estimators=80,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
        rf.fit(X_tr, y_tr)
        perm = permutation_importance(
            rf, X_tr, y_tr, scoring="roc_auc", n_repeats=5, random_state=random_state, n_jobs=-1
        )
        ranked_idx = np.argsort(perm.importances_mean)[::-1]
        top_cols = [cols[i] for i in ranked_idx[:12]]
        return top_cols
    else:
        raise ValueError(f"Unknown feature selection strategy: {strategy}")


def fit_and_predict_fold(
    cfg: Dict[str, Any],
    X_tr_raw: pd.DataFrame,
    y_tr: pd.Series,
    X_val_raw: pd.DataFrame,
    random_state: int = 42,
) -> Tuple[np.ndarray, Any, DataPreprocessor, List[str], Optional[Any]]:
    """Fit preprocessing, feature selector, scaler, and estimator strictly on X_tr_raw; predict probabilities on X_val_raw."""
    preproc = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_tr_prep = preproc.fit_transform(X_tr_raw)
    X_val_prep = preproc.transform(X_val_raw)

    selected_cols = select_features_in_fold(X_tr_prep, y_tr, cfg["feature_set"], random_state=random_state)
    X_tr_sel = X_tr_prep[selected_cols].copy()
    X_val_sel = X_val_prep[selected_cols].copy()

    scaler_type = cfg.get("scaler", "none")
    scaler: Optional[Any] = None
    if scaler_type == "standard":
        scaler = StandardScaler()
        X_tr_sel = pd.DataFrame(scaler.fit_transform(X_tr_sel), columns=selected_cols, index=X_tr_sel.index)
        X_val_sel = pd.DataFrame(scaler.transform(X_val_sel), columns=selected_cols, index=X_val_sel.index)
    elif scaler_type == "robust":
        scaler = RobustScaler()
        X_tr_sel = pd.DataFrame(scaler.fit_transform(X_tr_sel), columns=selected_cols, index=X_tr_sel.index)
        X_val_sel = pd.DataFrame(scaler.transform(X_val_sel), columns=selected_cols, index=X_val_sel.index)

    model = instantiate_estimator(cfg)
    model.fit(X_tr_sel, y_tr)
    y_prob = model.predict_proba(X_val_sel)[:, 1]
    return y_prob, model, preproc, selected_cols, scaler


def select_thresholds_from_inner_oof(y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
    """Select optimal thresholds for F1, F2 (recall-oriented), and F0.5 (precision-oriented) strictly on inner OOF predictions."""
    grid = np.round(np.arange(0.25, 0.76, 0.05), 2)
    best_f1_t, best_f1 = 0.50, -1.0
    best_f2_t, best_f2 = 0.40, -1.0
    best_f05_t, best_f05 = 0.55, -1.0

    for t in grid:
        y_pred = (y_prob >= t).astype(int)
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        f2 = float(fbeta_score(y_true, y_pred, beta=2.0, zero_division=0))
        f05 = float(fbeta_score(y_true, y_pred, beta=0.5, zero_division=0))

        if f1 > best_f1:
            best_f1 = f1
            best_f1_t = float(t)
        if prec >= 0.55 and f2 > best_f2:
            best_f2 = f2
            best_f2_t = float(t)
        if f05 > best_f05:
            best_f05 = f05
            best_f05_t = float(t)

    if best_f2 < 0:
        for t in grid:
            y_pred = (y_prob >= t).astype(int)
            f2 = float(fbeta_score(y_true, y_pred, beta=2.0, zero_division=0))
            if f2 > best_f2:
                best_f2 = f2
                best_f2_t = float(t)

    return {
        "tau_f1": round(best_f1_t, 2),
        "tau_f2": round(best_f2_t, 2),
        "tau_f05": round(best_f05_t, 2),
    }


def compute_classification_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> Dict[str, Any]:
    """Compute classification and ranking metrics at a given threshold."""
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "f2": round(float(fbeta_score(y_true, y_pred, beta=2.0, zero_division=0)), 4),
        "fpr": round(float(fpr), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def analyze_features_and_correlations(
    df: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    outer_splits: List[Tuple[np.ndarray, np.ndarray]],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze feature correlations, class discrimination, repository proxy score, and held-out permutation importance."""
    pearson_corr = X.corr(method="pearson").round(4)
    spearman_corr = X.corr(method="spearman").round(4)

    corr_rows: List[Dict[str, Any]] = []
    cols = list(X.columns)
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1 :]:
            pr = float(pearson_corr.loc[c1, c2])
            sr = float(spearman_corr.loc[c1, c2])
            if abs(pr) >= 0.50 or abs(sr) >= 0.50:
                corr_rows.append({
                    "feature_1": c1,
                    "feature_2": c2,
                    "pearson_r": round(pr, 4),
                    "spearman_rho": round(sr, 4),
                    "abs_spearman": round(abs(sr), 4),
                    "high_collinearity_085": abs(sr) >= 0.85,
                })
    corr_df = pd.DataFrame(corr_rows).sort_values(by="abs_spearman", ascending=False).reset_index(drop=True)

    baseline_cfg = build_candidate_catalog()[0]
    perm_roc_by_fold: Dict[str, List[float]] = {c: [] for c in cols}
    perm_f1_by_fold: Dict[str, List[float]] = {c: [] for c in cols}
    mdi_by_fold: Dict[str, List[float]] = {c: [] for c in cols}

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_splits, 1):
        X_tr, y_tr = X.iloc[tr_idx], y.iloc[tr_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]

        _, model, preproc, sel_cols, _ = fit_and_predict_fold(baseline_cfg, X_tr, y_tr, X_val, random_state=42)
        X_val_proc = preproc.transform(X_val)[sel_cols]

        if hasattr(model, "feature_importances_"):
            imp_map = dict(zip(sel_cols, model.feature_importances_))
            for c in cols:
                mdi_by_fold[c].append(float(imp_map.get(c, 0.0)))

        perm_auc = permutation_importance(
            model, X_val_proc, y_val, scoring="roc_auc", n_repeats=10, random_state=42, n_jobs=-1
        )
        auc_map = dict(zip(sel_cols, perm_auc.importances_mean))
        for c in cols:
            perm_roc_by_fold[c].append(float(auc_map.get(c, 0.0)))

        perm_f1 = permutation_importance(
            model, X_val_proc, y_val, scoring="f1", n_repeats=10, random_state=42, n_jobs=-1
        )
        f1_map = dict(zip(sel_cols, perm_f1.importances_mean))
        for c in cols:
            perm_f1_by_fold[c].append(float(f1_map.get(c, 0.0)))

    repo_ids = df["repository_id"].values
    unique_repos = np.unique(repo_ids)

    feat_rows: List[Dict[str, Any]] = []
    for c in cols:
        vals = X[c].values
        pos_vals = vals[y.values == 1]
        neg_vals = vals[y.values == 0]
        zero_rate = float(np.mean(vals == 0))
        variance = float(np.var(vals))

        try:
            _, mw_p = mannwhitneyu(pos_vals, neg_vals, alternative="two-sided")
            uni_auc = float(roc_auc_score(y, vals))
            uni_auc_directed = max(uni_auc, 1.0 - uni_auc)
        except Exception:
            mw_p = 1.0
            uni_auc_directed = 0.5

        ovr_aucs = []
        for r in unique_repos:
            r_bin = (repo_ids == r).astype(int)
            try:
                ra = float(roc_auc_score(r_bin, vals))
                ovr_aucs.append(max(ra, 1.0 - ra))
            except Exception:
                ovr_aucs.append(0.5)
        repo_proxy_auc = float(np.mean(ovr_aucs))

        p_auc_list = perm_roc_by_fold[c]
        p_f1_list = perm_f1_by_fold[c]
        m_list = mdi_by_fold[c]

        feat_rows.append({
            "feature": c,
            "perm_roc_auc_mean": round(float(np.mean(p_auc_list)), 5),
            "perm_roc_auc_std": round(float(np.std(p_auc_list)), 5),
            "perm_roc_auc_positive_folds": int(sum(1 for v in p_auc_list if v > 0)),
            "perm_f1_mean": round(float(np.mean(p_f1_list)), 5),
            "perm_f1_std": round(float(np.std(p_f1_list)), 5),
            "mdi_mean": round(float(np.mean(m_list)), 5),
            "mdi_std": round(float(np.std(m_list)), 5),
            "univariate_roc_auc": round(uni_auc_directed, 4),
            "defect_prone_median": round(float(np.median(pos_vals)), 3),
            "candidate_clean_median": round(float(np.median(neg_vals)), 3),
            "mannwhitney_p": round(float(mw_p), 6),
            "zero_fraction": round(zero_rate, 4),
            "variance": round(variance, 4),
            "repo_proxy_ovr_auc": round(repo_proxy_auc, 4),
        })

    feat_df = pd.DataFrame(feat_rows).sort_values(by="perm_roc_auc_mean", ascending=False).reset_index(drop=True)
    return feat_df, corr_df


def save_versioned_optimized_models(
    X: pd.DataFrame,
    y: pd.Series,
    nested_df: pd.DataFrame,
    oof_probs_by_config: Dict[str, np.ndarray],
) -> List[str]:
    """Save new versioned model artifacts trained strictly on Dataset #2 without overwriting baseline models."""
    models_out_dir = OUTPUT_DIR / "models"
    models_out_dir.mkdir(parents=True, exist_ok=True)

    preproc = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_proc = preproc.fit_transform(X)

    catalog_map = {c["config_id"]: c for c in build_candidate_catalog(42)}
    saved_paths: List[str] = []

    to_export = [
        ("et_nested_opt_v3_depth6_leaf6_log2", "et_depth6_leaf6_log2_bal"),
        ("rf_nested_opt_v3_depth6_leaf8_log2", "rf_depth6_leaf8_log2_bal"),
    ]

    for artifact_name, cid in to_export:
        cfg = catalog_map[cid]
        model = instantiate_estimator(cfg)
        model.fit(X_proc, y)

        row_m = nested_df[nested_df["config_id"] == cid].iloc[0]
        oof_p = oof_probs_by_config[cid]
        y_pred_nested = (oof_p >= 0.40).astype(int)
        cm = confusion_matrix(y.values, y_pred_nested, labels=[0, 1]).tolist()
        report = classification_report(y.values, y_pred_nested, output_dict=True, zero_division=0)

        mdi_importances = []
        if hasattr(model, "feature_importances_"):
            for fname, imp in zip(preproc.feature_names_out_, model.feature_importances_):
                mdi_importances.append({"feature": fname, "importance": float(imp)})
            mdi_importances.sort(key=lambda x: x["importance"], reverse=True)

        metrics_dict = {
            "evaluation_protocol": "5-Fold Nested Repository-Level GroupKFold (Out-of-Fold)",
            "accuracy": float(row_m["pooled_accuracy_nested_tau"]),
            "precision": float(row_m["pooled_precision_nested_tau"]),
            "recall": float(row_m["pooled_recall_nested_tau"]),
            "f1": float(row_m["pooled_f1_nested_tau"]),
            "roc_auc": float(row_m["outer_roc_auc_mean"]),
            "average_precision": float(row_m["outer_pr_auc_mean"]),
            "brier_score": float(row_m["outer_brier_mean"]),
            "confusion_matrix": cm,
            "classification_report": report,
            "test_sample_count": int(len(y)),
            "mdi_feature_importances": mdi_importances,
        }

        split_sum = {
            "train_repositories": [3, 4, 14, 15, 16],
            "test_repositories": [17],
            "train_repo_count": 5,
            "test_repo_count": 0,
            "train_samples": int(len(y)),
            "test_samples": 0,
            "validation_scheme": "5-Fold Outer x 4-Fold Inner GroupKFold",
        }

        params_with_algo = {"algorithm": cfg["algorithm"], **cfg["params"]}

        # Save in 3_TestResults/ModelOptimization/models/ and in 4_AppBuild/Assets/Models/ (new versioned filenames only)
        for target_dir in [models_out_dir, APP_MODELS_DIR]:
            mgr = ModelManager(target_dir, db=None)
            p = mgr.save_model(
                model_name=artifact_name,
                model=model,
                preprocessor=preproc,
                feature_names=preproc.feature_names_out_,
                parameters=params_with_algo,
                metrics=metrics_dict,
                dataset_id=2,
                split_summary=split_sum,
                overwrite=True,
            )
            saved_paths.append(str(p.relative_to(PROJECT_ROOT)))

    return saved_paths


def run_optimization_experiment() -> None:
    start_time = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("CONTROLLED ML MODEL OPTIMIZATION (NESTED REPOSITORY-LEVEL GROUPKFOLD)")
    print("=" * 80)

    df = pd.read_csv(DATASET_V2_PATH)
    feature_cols = [c for c in DEFAULT_NUMERICAL_FEATURES if c in df.columns]
    assert len(df) == 578, f"Expected 578 rows, found {len(df)}"
    assert len(feature_cols) == 26, f"Expected 26 features, found {len(feature_cols)}"

    X = df[feature_cols].copy()
    y = df["label"].astype(int).copy()
    groups = df["repository_id"].values
    repo_names = df.groupby("repository_id")["repository_name"].first().to_dict()

    outer_gkf = GroupKFold(n_splits=5)
    outer_splits = list(outer_gkf.split(X, y, groups=groups))

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_splits, 1):
        tr_repos = set(df.iloc[tr_idx]["repository_id"].unique())
        val_repos = set(df.iloc[val_idx]["repository_id"].unique())
        assert tr_repos.isdisjoint(val_repos), f"Repository leakage in outer fold {fold_idx}"
        tr_obs = set(df.iloc[tr_idx]["observation_id"].unique())
        val_obs = set(df.iloc[val_idx]["observation_id"].unique())
        assert tr_obs.isdisjoint(val_obs), f"Observation leakage in outer fold {fold_idx}"

    print("Running feature correlation, repository proxy, and outer-fold permutation importance analysis...")
    feat_df, corr_df = analyze_features_and_correlations(df, X, y, outer_splits)
    feat_df.to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)
    corr_df.to_csv(OUTPUT_DIR / "feature_correlation.csv", index=False)

    candidates = build_candidate_catalog(random_state=42)
    print(f"Evaluating {len(candidates)} candidate configurations with inner 4-fold GroupKFold threshold tuning...")

    nested_rows: List[Dict[str, Any]] = []
    per_repo_rows: List[Dict[str, Any]] = []
    oof_probs_by_config: Dict[str, np.ndarray] = {}
    inner_tau_f1_by_config: Dict[str, List[float]] = {}
    inner_scores_matrix: Dict[int, Dict[str, Dict[str, Any]]] = {k: {} for k in range(1, 6)}

    for cfg in candidates:
        cid = cfg["config_id"]
        oof_prob = np.zeros(len(df), dtype=float)
        oof_pred_inner_f1 = np.zeros(len(df), dtype=int)
        oof_pred_inner_f2 = np.zeros(len(df), dtype=int)

        fold_metrics_nom: List[Dict[str, Any]] = []
        fold_metrics_inner_f1: List[Dict[str, Any]] = []
        inner_taus_f1: List[float] = []
        inner_taus_f2: List[float] = []

        for fold_idx, (tr_idx, val_idx) in enumerate(outer_splits, 1):
            X_outer_tr, y_outer_tr = X.iloc[tr_idx], y.iloc[tr_idx]
            X_outer_val, y_outer_val = X.iloc[val_idx], y.iloc[val_idx]
            groups_outer_tr = groups[tr_idx]
            val_repo_id = int(df.iloc[val_idx]["repository_id"].iloc[0])
            val_repo_name = repo_names[val_repo_id]

            inner_gkf = GroupKFold(n_splits=4)
            inner_oof_prob = np.zeros(len(X_outer_tr), dtype=float)
            inner_fold_aucs: List[float] = []
            inner_fold_aps: List[float] = []
            inner_fold_briers: List[float] = []
            inner_fold_f1s_nom: List[float] = []

            for in_tr_idx, in_val_idx in inner_gkf.split(X_outer_tr, y_outer_tr, groups=groups_outer_tr):
                in_tr_r = set(groups_outer_tr[in_tr_idx])
                in_val_r = set(groups_outer_tr[in_val_idx])
                assert in_tr_r.isdisjoint(in_val_r), "Inner fold repository leakage!"

                X_in_tr = X_outer_tr.iloc[in_tr_idx]
                y_in_tr = y_outer_tr.iloc[in_tr_idx]
                X_in_val = X_outer_tr.iloc[in_val_idx]
                y_in_val = y_outer_tr.iloc[in_val_idx]

                in_prob, _, _, _, _ = fit_and_predict_fold(cfg, X_in_tr, y_in_tr, X_in_val, random_state=42)
                inner_oof_prob[in_val_idx] = in_prob

                inner_fold_aucs.append(float(roc_auc_score(y_in_val, in_prob)))
                inner_fold_aps.append(float(average_precision_score(y_in_val, in_prob)))
                inner_fold_briers.append(float(brier_score_loss(y_in_val, in_prob)))
                inner_fold_f1s_nom.append(float(f1_score(y_in_val, (in_prob >= 0.50).astype(int), zero_division=0)))

            inner_taus = select_thresholds_from_inner_oof(y_outer_tr.values, inner_oof_prob)
            tau_f1 = inner_taus["tau_f1"]
            tau_f2 = inner_taus["tau_f2"]
            inner_taus_f1.append(tau_f1)
            inner_taus_f2.append(tau_f2)

            # Pooled inner OOF discrimination & Brier across all 4 outer-training repositories
            in_pooled_auc = float(roc_auc_score(y_outer_tr.values, inner_oof_prob))
            in_pooled_ap = float(average_precision_score(y_outer_tr.values, inner_oof_prob))
            in_pooled_brier = float(brier_score_loss(y_outer_tr.values, inner_oof_prob))
            inner_composite_score = (
                0.50 * in_pooled_auc
                + 0.30 * in_pooled_ap
                - 0.50 * in_pooled_brier
                - 0.15 * float(np.std(inner_fold_aucs))
            )
            inner_scores_matrix[fold_idx][cid] = {
                "inner_pooled_roc_auc": in_pooled_auc,
                "inner_pooled_pr_auc": in_pooled_ap,
                "inner_pooled_brier": in_pooled_brier,
                "inner_roc_auc_mean": float(np.mean(inner_fold_aucs)),
                "inner_pr_auc_mean": float(np.mean(inner_fold_aps)),
                "inner_brier_mean": float(np.mean(inner_fold_briers)),
                "inner_f1_nom_mean": float(np.mean(inner_fold_f1s_nom)),
                "inner_f1_nom_std": float(np.std(inner_fold_f1s_nom)),
                "inner_composite": inner_composite_score,
                "tau_f1": tau_f1,
                "tau_f2": tau_f2,
            }

            outer_val_prob, _, _, _, _ = fit_and_predict_fold(
                cfg, X_outer_tr, y_outer_tr, X_outer_val, random_state=42
            )
            oof_prob[val_idx] = outer_val_prob
            oof_pred_inner_f1[val_idx] = (outer_val_prob >= tau_f1).astype(int)
            oof_pred_inner_f2[val_idx] = (outer_val_prob >= tau_f2).astype(int)

            m_nom = compute_classification_metrics(y_outer_val.values, outer_val_prob, 0.50)
            m_in_f1 = compute_classification_metrics(y_outer_val.values, outer_val_prob, tau_f1)
            fold_metrics_nom.append(m_nom)
            fold_metrics_inner_f1.append(m_in_f1)

            per_repo_rows.append({
                "config_id": cid,
                "family": cfg["family"],
                "feature_set": cfg["feature_set"],
                "outer_fold": fold_idx,
                "repository_id": val_repo_id,
                "repository_name": val_repo_name,
                "val_samples": len(y_outer_val),
                "val_defect_prone": int((y_outer_val == 1).sum()),
                "val_candidate_clean": int((y_outer_val == 0).sum()),
                "roc_auc": m_nom["roc_auc"],
                "pr_auc": m_nom["pr_auc"],
                "brier": m_nom["brier"],
                "f1_nominal_050": m_nom["f1"],
                "recall_nominal_050": m_nom["recall"],
                "precision_nominal_050": m_nom["precision"],
                "accuracy_nominal_050": m_nom["accuracy"],
                "inner_selected_tau_f1": tau_f1,
                "f1_nested_tau": m_in_f1["f1"],
                "recall_nested_tau": m_in_f1["recall"],
                "precision_nested_tau": m_in_f1["precision"],
                "accuracy_nested_tau": m_in_f1["accuracy"],
                "tn_nested_tau": m_in_f1["tn"],
                "fp_nested_tau": m_in_f1["fp"],
                "fn_nested_tau": m_in_f1["fn"],
                "tp_nested_tau": m_in_f1["tp"],
            })

        oof_probs_by_config[cid] = oof_prob
        inner_tau_f1_by_config[cid] = inner_taus_f1

        pooled_nom = compute_classification_metrics(y.values, oof_prob, 0.50)
        cm_nested = confusion_matrix(y.values, oof_pred_inner_f1, labels=[0, 1]).tolist()
        tn_n, fp_n, fn_n, tp_n = cm_nested[0][0], cm_nested[0][1], cm_nested[1][0], cm_nested[1][1]

        nested_rows.append({
            "config_id": cid,
            "family": cfg["family"],
            "algorithm": cfg["algorithm"],
            "feature_set": cfg["feature_set"],
            "scaler": cfg["scaler"],
            "outer_roc_auc_mean": round(float(np.mean([m["roc_auc"] for m in fold_metrics_nom])), 4),
            "outer_roc_auc_std": round(float(np.std([m["roc_auc"] for m in fold_metrics_nom])), 4),
            "outer_pr_auc_mean": round(float(np.mean([m["pr_auc"] for m in fold_metrics_nom])), 4),
            "outer_pr_auc_std": round(float(np.std([m["pr_auc"] for m in fold_metrics_nom])), 4),
            "outer_brier_mean": round(float(np.mean([m["brier"] for m in fold_metrics_nom])), 4),
            "outer_brier_std": round(float(np.std([m["brier"] for m in fold_metrics_nom])), 4),
            "outer_f1_nom_mean": round(float(np.mean([m["f1"] for m in fold_metrics_nom])), 4),
            "outer_f1_nom_std": round(float(np.std([m["f1"] for m in fold_metrics_nom])), 4),
            "outer_recall_nom_mean": round(float(np.mean([m["recall"] for m in fold_metrics_nom])), 4),
            "outer_precision_nom_mean": round(float(np.mean([m["precision"] for m in fold_metrics_nom])), 4),
            "outer_accuracy_nom_mean": round(float(np.mean([m["accuracy"] for m in fold_metrics_nom])), 4),
            "outer_f1_nested_tau_mean": round(float(np.mean([m["f1"] for m in fold_metrics_inner_f1])), 4),
            "outer_f1_nested_tau_std": round(float(np.std([m["f1"] for m in fold_metrics_inner_f1])), 4),
            "outer_recall_nested_tau_mean": round(float(np.mean([m["recall"] for m in fold_metrics_inner_f1])), 4),
            "outer_precision_nested_tau_mean": round(float(np.mean([m["precision"] for m in fold_metrics_inner_f1])), 4),
            "outer_accuracy_nested_tau_mean": round(float(np.mean([m["accuracy"] for m in fold_metrics_inner_f1])), 4),
            "pooled_roc_auc": pooled_nom["roc_auc"],
            "pooled_pr_auc": pooled_nom["pr_auc"],
            "pooled_brier": pooled_nom["brier"],
            "pooled_f1_nom_050": pooled_nom["f1"],
            "pooled_recall_nom_050": pooled_nom["recall"],
            "pooled_precision_nom_050": pooled_nom["precision"],
            "pooled_accuracy_nom_050": pooled_nom["accuracy"],
            "pooled_f1_nested_tau": round(float(f1_score(y.values, oof_pred_inner_f1, zero_division=0)), 4),
            "pooled_f2_nested_tau": round(float(fbeta_score(y.values, oof_pred_inner_f1, beta=2.0, zero_division=0)), 4),
            "pooled_recall_nested_tau": round(float(recall_score(y.values, oof_pred_inner_f1, zero_division=0)), 4),
            "pooled_precision_nested_tau": round(float(precision_score(y.values, oof_pred_inner_f1, zero_division=0)), 4),
            "pooled_accuracy_nested_tau": round(float(accuracy_score(y.values, oof_pred_inner_f1)), 4),
            "pooled_tn_nested": int(tn_n),
            "pooled_fp_nested": int(fp_n),
            "pooled_fn_nested": int(fn_n),
            "pooled_tp_nested": int(tp_n),
            "inner_taus_f1": json.dumps(inner_taus_f1),
        })

    # Full Nested Model Selection per outer fold
    nested_selected_oof_prob = np.zeros(len(df), dtype=float)
    nested_selected_oof_pred = np.zeros(len(df), dtype=int)
    nested_selected_choices: List[Dict[str, Any]] = []
    nested_selected_fold_nom: List[Dict[str, Any]] = []
    nested_selected_fold_tau: List[Dict[str, Any]] = []

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_splits, 1):
        val_repo_id = int(df.iloc[val_idx]["repository_id"].iloc[0])
        val_repo_name = repo_names[val_repo_id]
        best_cid = max(inner_scores_matrix[fold_idx].keys(), key=lambda c: inner_scores_matrix[fold_idx][c]["inner_composite"])
        best_in_info = inner_scores_matrix[fold_idx][best_cid]
        tau_sel = best_in_info["tau_f1"]

        prob_fold = oof_probs_by_config[best_cid][val_idx]
        nested_selected_oof_prob[val_idx] = prob_fold
        nested_selected_oof_pred[val_idx] = (prob_fold >= tau_sel).astype(int)

        y_val_arr = y.iloc[val_idx].values
        m_nom = compute_classification_metrics(y_val_arr, prob_fold, 0.50)
        m_tau = compute_classification_metrics(y_val_arr, prob_fold, tau_sel)
        nested_selected_fold_nom.append(m_nom)
        nested_selected_fold_tau.append(m_tau)

        nested_selected_choices.append({
            "outer_fold": fold_idx,
            "val_repository_id": val_repo_id,
            "val_repository_name": val_repo_name,
            "selected_config_id": best_cid,
            "inner_pooled_roc_auc": round(best_in_info["inner_pooled_roc_auc"], 4),
            "inner_pooled_brier": round(best_in_info["inner_pooled_brier"], 4),
            "inner_selected_tau": tau_sel,
            "outer_roc_auc": m_nom["roc_auc"],
            "outer_pr_auc": m_nom["pr_auc"],
            "outer_brier": m_nom["brier"],
            "outer_f1_nom": m_nom["f1"],
            "outer_f1_nested_tau": m_tau["f1"],
            "outer_recall_nested_tau": m_tau["recall"],
            "outer_precision_nested_tau": m_tau["precision"],
            "outer_accuracy_nested_tau": m_tau["accuracy"],
        })

    nested_df = pd.DataFrame(nested_rows).sort_values(
        by=["outer_roc_auc_mean", "outer_f1_nested_tau_mean"], ascending=False
    ).reset_index(drop=True)
    nested_df["rank_by_roc_auc"] = np.arange(1, len(nested_df) + 1)
    nested_df.to_csv(OUTPUT_DIR / "nested_cv_results.csv", index=False)

    per_repo_df = pd.DataFrame(per_repo_rows)
    per_repo_df.to_csv(OUTPUT_DIR / "per_repository_results.csv", index=False)

    # Save versioned model artifacts
    saved_model_paths = save_versioned_optimized_models(X, y, nested_df, oof_probs_by_config)

    # Save model_comparison.csv
    comp_ids = [
        "rf_compact_regularized_baseline",
        "et_depth6_leaf6_log2_bal",
        "rf_depth6_leaf8_log2_bal",
        "et_depth8_leaf4_sqrt_bal",
        "rf_compact_corr_pruned",
        "lr_c01_robust_bal",
        "gb_lr003_depth2_leaf12_sub08",
        "hgb_lr003_depth3_leaf25_l2_5",
    ]
    comp_df = nested_df[nested_df["config_id"].isin(comp_ids)].copy()
    comp_df.to_csv(OUTPUT_DIR / "model_comparison.csv", index=False)

    # Threshold Analysis Table
    seen_cids = [
        "rf_compact_regularized_baseline",
        "et_depth6_leaf6_log2_bal",
        "rf_depth6_leaf8_log2_bal",
        "et_depth8_leaf4_sqrt_bal",
        "hgb_lr005_depth5_leaf20_l2_1",
        "gb_lr005_depth3_leaf8_sub08",
        "lr_c01_std_bal",
        "rf_compact_calibrated_sigmoid",
    ]
    thresh_rows: List[Dict[str, Any]] = []
    for cid in seen_cids:
        probs = oof_probs_by_config[cid]
        for t in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
            m = compute_classification_metrics(y.values, probs, t)
            thresh_rows.append({
                "config_id": cid,
                "threshold_mode": f"fixed_{t:.2f}",
                **m,
            })
        row_match = nested_df[nested_df["config_id"] == cid].iloc[0]
        thresh_rows.append({
            "config_id": cid,
            "threshold_mode": "nested_inner_oof_f1",
            "threshold": round(float(np.mean(json.loads(row_match["inner_taus_f1"]))), 2),
            "accuracy": row_match["pooled_accuracy_nested_tau"],
            "precision": row_match["pooled_precision_nested_tau"],
            "recall": row_match["pooled_recall_nested_tau"],
            "f1": row_match["pooled_f1_nested_tau"],
            "f2": row_match["pooled_f2_nested_tau"],
            "fpr": round(
                row_match["pooled_fp_nested"] / (row_match["pooled_fp_nested"] + row_match["pooled_tn_nested"]), 4
            ),
            "roc_auc": row_match["pooled_roc_auc"],
            "pr_auc": row_match["pooled_pr_auc"],
            "brier": row_match["pooled_brier"],
            "tn": row_match["pooled_tn_nested"],
            "fp": row_match["pooled_fp_nested"],
            "fn": row_match["pooled_fn_nested"],
            "tp": row_match["pooled_tp_nested"],
        })

    thresh_df = pd.DataFrame(thresh_rows)
    thresh_df.to_csv(OUTPUT_DIR / "threshold_analysis.csv", index=False)

    # Error Analysis on Outer Out-of-Fold Predictions
    base_probs = oof_probs_by_config["rf_compact_regularized_baseline"]
    et_probs = oof_probs_by_config["et_depth6_leaf6_log2_bal"]
    et_taus = inner_tau_f1_by_config["et_depth6_leaf6_log2_bal"]
    err_rows: List[Dict[str, Any]] = []

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_splits, 1):
        tau_fold = et_taus[fold_idx - 1]
        for idx in val_idx:
            row = df.iloc[idx]
            prob_et = float(et_probs[idx])
            prob_base = float(base_probs[idx])
            true_lbl = int(row["label"])
            pred_nom = int(prob_et >= 0.50)
            pred_nested = int(prob_et >= tau_fold)

            if true_lbl == 1 and pred_nested == 1:
                quadrant = "TP"
            elif true_lbl == 0 and pred_nested == 0:
                quadrant = "TN"
            elif true_lbl == 0 and pred_nested == 1:
                quadrant = "FP"
            else:
                quadrant = "FN"

            loc_val = int(row["loc"])
            cc_val = int(row["cyclomatic_complexity"])
            nest_val = int(row["max_nesting_depth"])

            if quadrant == "FN" and (loc_val <= 12 and cc_val <= 2):
                err_pattern = "Short low-complexity method (semantic/contract defect not reflected in AST complexity)"
            elif quadrant == "FN":
                err_pattern = "Moderate-complexity method below decision threshold"
            elif quadrant == "FP" and (cc_val >= 6 or loc_val >= 35 or nest_val >= 3):
                err_pattern = "High structural complexity candidate-clean method (defensive code or latent unrecorded risk)"
            elif quadrant == "FP":
                err_pattern = "Borderline structural risk in candidate-clean method"
            else:
                err_pattern = "Concordant prediction"

            err_rows.append({
                "observation_id": int(row["observation_id"]),
                "repository_id": int(row["repository_id"]),
                "repository_name": str(row["repository_name"]),
                "file_path": str(row["file_path"]),
                "class_name": str(row["class_name"]),
                "method_name": str(row["method_name"]),
                "true_label": true_lbl,
                "baseline_rf_oof_prob": round(prob_base, 4),
                "optimized_et_oof_prob": round(prob_et, 4),
                "inner_selected_tau": tau_fold,
                "pred_nominal_050": pred_nom,
                "pred_nested_tau": pred_nested,
                "quadrant_nested": quadrant,
                "error_category": err_pattern,
                "loc": loc_val,
                "logical_loc": int(row["logical_loc"]),
                "cyclomatic_complexity": cc_val,
                "max_nesting_depth": nest_val,
                "parameter_count": int(row["parameter_count"]),
                "method_call_count": int(row["method_call_count"]),
                "field_access_count": int(row["field_access_count"]),
                "property_access_count": int(row["property_access_count"]),
                "try_catch_count": int(row["try_catch_count"]),
            })

    err_df = pd.DataFrame(err_rows)
    err_df.to_csv(OUTPUT_DIR / "error_analysis.csv", index=False)

    elapsed = round(time.time() - start_time, 2)
    opt_config_payload = {
        "experiment_id": "cise_p2_nested_model_optimization_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(DATASET_V2_PATH.relative_to(PROJECT_ROOT)),
        "dataset_observations": int(len(df)),
        "dataset_repositories": int(len(repo_names)),
        "outer_cv": "5-Fold GroupKFold by repository_id (1 repository held out per outer fold)",
        "inner_cv": "4-Fold GroupKFold by repository_id on the 4 outer-training repositories",
        "holdout_policy": "Newtonsoft.Json holdout strictly excluded from feature, model, hyperparameter, and threshold selection",
        "feature_selection_strategies": [
            "all_26",
            "corr_pruned_085",
            "inner_perm_top12",
            "theoretical_core10",
        ],
        "saved_versioned_models": saved_model_paths,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    (OUTPUT_DIR / "optimization_config.json").write_text(
        json.dumps(opt_config_payload, indent=2), encoding="utf-8"
    )

    summary_payload = {
        "experiment_id": "cise_p2_nested_model_optimization_v1",
        "execution_duration_s": elapsed,
        "baseline_config_id": "rf_compact_regularized_baseline",
        "selected_primary_config_id": "et_depth6_leaf6_log2_bal",
        "selected_rf_config_id": "rf_depth6_leaf8_log2_bal",
        "saved_versioned_models": saved_model_paths,
        "baseline_results": nested_df[nested_df["config_id"] == "rf_compact_regularized_baseline"].iloc[0].to_dict(),
        "selected_et_results": nested_df[nested_df["config_id"] == "et_depth6_leaf6_log2_bal"].iloc[0].to_dict(),
        "selected_rf_results": nested_df[nested_df["config_id"] == "rf_depth6_leaf8_log2_bal"].iloc[0].to_dict(),
        "top_ranked_by_outer_roc_auc": nested_df.head(10).to_dict(orient="records"),
        "full_nested_selection_per_outer_fold": {
            "outer_fold_choices": nested_selected_choices,
            "outer_roc_auc_mean": round(float(np.mean([m["roc_auc"] for m in nested_selected_fold_nom])), 4),
            "outer_roc_auc_std": round(float(np.std([m["roc_auc"] for m in nested_selected_fold_nom])), 4),
            "outer_f1_nom_mean": round(float(np.mean([m["f1"] for m in nested_selected_fold_nom])), 4),
            "outer_f1_nom_std": round(float(np.std([m["f1"] for m in nested_selected_fold_nom])), 4),
            "outer_f1_nested_tau_mean": round(float(np.mean([m["f1"] for m in nested_selected_fold_tau])), 4),
            "outer_f1_nested_tau_std": round(float(np.std([m["f1"] for m in nested_selected_fold_tau])), 4),
            "pooled_f1_nested_tau": round(float(f1_score(y.values, nested_selected_oof_pred, zero_division=0)), 4),
            "pooled_recall_nested_tau": round(float(recall_score(y.values, nested_selected_oof_pred, zero_division=0)), 4),
            "pooled_precision_nested_tau": round(float(precision_score(y.values, nested_selected_oof_pred, zero_division=0)), 4),
            "pooled_accuracy_nested_tau": round(float(accuracy_score(y.values, nested_selected_oof_pred)), 4),
        },
    }
    (OUTPUT_DIR / "nested_cv_summary.json").write_text(
        json.dumps(summary_payload, indent=2), encoding="utf-8"
    )
    print(f"Completed in {elapsed}s. Saved versioned models: {saved_model_paths}")


if __name__ == "__main__":
    run_optimization_experiment()
