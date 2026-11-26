"""Top-200 Star-Ranked C# Bug Detection Classifier & Method Localization Optimization.

Evaluates the 40 Roslyn class metrics (and tests feature-selection sufficiency)
across 7 required ML families on Dataset #4 (csharp_class_top200_v4 v4.0.0) using:
1. Strict repository-level split into ~80% Development Repos and ~20% Untouched Independent Holdout.
2. Nested 5-outer x 4-inner GroupKFold inside Development Repos.
3. In-fold preprocessing (median imputation, zero-variance pruning, correlation pruning, scaling for LR).
4. Inner-CV threshold selection targeting Precision >= 75% (with >= 77% inner margin) while maximizing F1 and Recall.
5. One-shot evaluation on Untouched Holdout reporting Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix, FPR, FNR.
6. Separately validated Method Localization model trained strictly on the Development repositories and evaluated
   on Untouched Holdout BUG classes to distinguish verified historical SZZ locations from ML suspicious method predictions.
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.tree import DecisionTreeClassifier

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PYTHON_SRC = PROJECT_ROOT / "2_SourceCode" / "Python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from core.settings import get_settings
from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from ml.cross_validation import (
    compute_bayesian_precision,
    compute_binary_classification_metrics,
    select_classifier_threshold,
)
from ml.model_manager import ModelManager
from ml.preprocessing import DataPreprocessor
from services.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES, DatasetBuilder

OUTPUT_DIR = PROJECT_ROOT / "3_TestResults" / "Top200ClassifierOptimization"


def build_classifier_catalog(random_state: int = 42) -> List[Dict[str, Any]]:
    """Define classifier configurations spanning all 7 ML families plus feature-sufficiency ablations."""
    return [
        # 1. DummyClassifier Baseline
        {
            "config_id": "dummy_stratified",
            "family": "DummyClassifier",
            "algorithm": "dummy",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {"strategy": "stratified", "random_state": random_state},
        },
        # 2. Logistic Regression
        {
            "config_id": "lr_std_l2_c01_bal",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "bundle_name": "lr_class_top200_v4",
            "scaler": "standard",
            "corr_prune": True,
            "params": {"C": 0.1, "max_iter": 1000, "class_weight": "balanced", "random_state": random_state},
        },
        {
            "config_id": "lr_robust_l2_c02",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "bundle_name": None,
            "scaler": "robust",
            "corr_prune": True,
            "params": {"C": 0.2, "max_iter": 1000, "class_weight": None, "random_state": random_state},
        },
        # 3. Decision Tree
        {
            "config_id": "dt_depth6_leaf12_bal",
            "family": "Decision Tree",
            "algorithm": "decision_tree",
            "bundle_name": "dt_class_top200_v4",
            "scaler": "none",
            "corr_prune": False,
            "params": {"max_depth": 6, "min_samples_split": 14, "min_samples_leaf": 12, "class_weight": "balanced", "random_state": random_state},
        },
        # 4. Random Forest (Full 40 vs Correlation-Pruned Ablation)
        {
            "config_id": "rf_depth12_leaf4_log2_all40",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "bundle_name": "rf_class_top200_v4",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 350, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced_subsample",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_depth12_leaf4_corr_pruned",
            "family": "Random Forest (Pruned Features)",
            "algorithm": "random_forest",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": True,
            "params": {
                "n_estimators": 350, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced_subsample",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_depth14_leaf3_sqrt_unweighted",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 350, "max_depth": 14, "min_samples_split": 8,
                "min_samples_leaf": 3, "max_features": "sqrt", "class_weight": None,
                "random_state": random_state, "n_jobs": -1,
            },
        },
        # 5. Extra Trees
        {
            "config_id": "et_depth12_leaf4_log2_bal",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "bundle_name": "et_class_top200_v4",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 350, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "et_depth14_leaf5_sqrt",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 350, "max_depth": 14, "min_samples_split": 8,
                "min_samples_leaf": 5, "max_features": "sqrt", "class_weight": None,
                "random_state": random_state, "n_jobs": -1,
            },
        },
        # 6. HistGradientBoosting
        {
            "config_id": "hgb_depth5_leaf20_l2_2",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "bundle_name": "hgb_class_top200_v4",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "learning_rate": 0.05, "max_iter": 220, "max_depth": 5,
                "max_leaf_nodes": 20, "min_samples_leaf": 20, "l2_regularization": 2.0,
                "class_weight": "balanced", "random_state": random_state,
            },
        },
        {
            "config_id": "hgb_depth4_leaf15_unweighted",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "learning_rate": 0.05, "max_iter": 200, "max_depth": 4,
                "max_leaf_nodes": 15, "min_samples_leaf": 20, "l2_regularization": 3.0,
                "class_weight": None, "random_state": random_state,
            },
        },
        # 7. Calibrated Classifier
        {
            "config_id": "calibrated_rf_sigmoid",
            "family": "Calibrated Ensemble",
            "algorithm": "calibrated_rf",
            "bundle_name": "calibrated_class_top200_v4",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 250, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced",
                "calibration_method": "sigmoid", "calibration_cv": 3,
                "random_state": random_state, "n_jobs": -1,
            },
        },
    ]


def instantiate_model(cfg: Dict[str, Any]) -> Any:
    algo = cfg["algorithm"]
    p = cfg["params"]
    if algo == "dummy":
        est = DummyClassifier(**p)
    elif algo == "logistic_regression":
        est = LogisticRegression(**p)
    elif algo == "decision_tree":
        est = DecisionTreeClassifier(**p)
    elif algo == "random_forest":
        est = RandomForestClassifier(**p)
    elif algo == "extra_trees":
        est = ExtraTreesClassifier(**p)
    elif algo == "hist_gb":
        est = HistGradientBoostingClassifier(**p)
    elif algo in ("calibrated_rf", "calibrated_et"):
        base_cls = ExtraTreesClassifier if algo == "calibrated_et" else RandomForestClassifier
        base = base_cls(
            n_estimators=p["n_estimators"],
            max_depth=p["max_depth"],
            min_samples_split=p["min_samples_split"],
            min_samples_leaf=p["min_samples_leaf"],
            max_features=p["max_features"],
            class_weight=p["class_weight"],
            random_state=p["random_state"],
            n_jobs=p.get("n_jobs", -1),
        )
        est = CalibratedClassifierCV(
            estimator=base,
            method=p.get("calibration_method", "sigmoid"),
            cv=p.get("calibration_cv", 3),
        )
    else:
        raise ValueError(f"Unknown algorithm: {algo}")

    if cfg.get("scaler") == "standard":
        return Pipeline([("scaler", StandardScaler()), ("classifier", est)])
    if cfg.get("scaler") == "robust":
        return Pipeline([("scaler", RobustScaler()), ("classifier", est)])
    return est


def select_infold_features(X_tr: pd.DataFrame, corr_prune: bool, threshold: float = 0.90) -> List[str]:
    cols = list(X_tr.columns)
    if not corr_prune or len(cols) <= 2:
        return cols
    corr = X_tr.corr(method="spearman").abs().fillna(0.0)
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    kept = [c for c in cols if c not in to_drop]
    return kept if kept else cols


def fit_and_predict_fold(
    cfg: Dict[str, Any],
    X_tr_raw: pd.DataFrame,
    y_tr: pd.Series,
    X_val_raw: pd.DataFrame,
) -> Tuple[np.ndarray, Any, DataPreprocessor, List[str]]:
    preproc = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_tr_proc = preproc.fit_transform(X_tr_raw)
    X_val_proc = preproc.transform(X_val_raw)

    selected_cols = select_infold_features(X_tr_proc, corr_prune=bool(cfg.get("corr_prune", False)))
    X_tr_sel = X_tr_proc[selected_cols]
    X_val_sel = X_val_proc[selected_cols]

    model = instantiate_model(cfg)
    model.fit(X_tr_sel, y_tr)
    y_prob = model.predict_proba(X_val_sel)[:, 1]
    return y_prob, model, preproc, selected_cols


def evaluate_nested_cv(
    cfg: Dict[str, Any],
    X_dev: pd.DataFrame,
    y_dev: pd.Series,
    meta_dev: pd.DataFrame,
    n_outer: int = 5,
    n_inner: int = 4,
) -> Dict[str, Any]:
    """Run strict 5-outer x 4-inner GroupKFold nested validation selecting tau for >= 75% precision + high recall."""
    groups_dev = meta_dev["repository_id"].values
    outer_gkf = GroupKFold(n_splits=min(n_outer, len(np.unique(groups_dev))))

    outer_fold_rows: List[Dict[str, Any]] = []
    oof_y_true: List[int] = []
    oof_y_prob: List[float] = []
    oof_y_pred_tuned: List[int] = []
    selected_thresholds: List[float] = []
    criteria_used: List[str] = []

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_gkf.split(X_dev, y_dev, groups=groups_dev), 1):
        X_out_tr, X_out_val = X_dev.iloc[tr_idx], X_dev.iloc[val_idx]
        y_out_tr, y_out_val = y_dev.iloc[tr_idx], y_dev.iloc[val_idx]
        meta_out_tr, meta_out_val = meta_dev.iloc[tr_idx], meta_dev.iloc[val_idx]

        inner_groups = meta_out_tr["repository_id"].values
        inner_gkf = GroupKFold(n_splits=min(n_inner, len(np.unique(inner_groups))))

        inner_y_true: List[int] = []
        inner_y_prob: List[float] = []
        for in_tr_idx, in_val_idx in inner_gkf.split(X_out_tr, y_out_tr, groups=inner_groups):
            probs_in, _, _, _ = fit_and_predict_fold(
                cfg,
                X_out_tr.iloc[in_tr_idx],
                y_out_tr.iloc[in_tr_idx],
                X_out_tr.iloc[in_val_idx],
            )
            inner_y_true.extend(y_out_tr.iloc[in_val_idx].tolist())
            inner_y_prob.extend(probs_in.tolist())

        thresh_res = select_classifier_threshold(
            np.array(inner_y_true),
            np.array(inner_y_prob),
            min_precision_target=0.77,
            min_precision_floor=0.75,
            min_recall=0.50,
            min_predicted_positives=max(10, int(0.03 * len(inner_y_true))),
        )
        tau_inner = float(thresh_res["selected_threshold"])
        selected_thresholds.append(tau_inner)
        criteria_used.append(thresh_res["criterion"])

        probs_out, _, _, _ = fit_and_predict_fold(cfg, X_out_tr, y_out_tr, X_out_val)
        metrics_nom = compute_binary_classification_metrics(y_out_val.values, probs_out, threshold=0.50)
        metrics_opt = compute_binary_classification_metrics(y_out_val.values, probs_out, threshold=tau_inner)

        outer_fold_rows.append({
            "fold": fold_idx,
            "val_repo_count": int(meta_out_val["repository_id"].nunique()),
            "val_samples": len(y_out_val),
            "tau_inner": tau_inner,
            "criterion": thresh_res["criterion"],
            "nom_precision": metrics_nom["precision"],
            "nom_recall": metrics_nom["recall"],
            "nom_f1": metrics_nom["f1"],
            "opt_precision": metrics_opt["precision"],
            "opt_recall": metrics_opt["recall"],
            "opt_f1": metrics_opt["f1"],
            "opt_accuracy": metrics_opt["accuracy"],
            "opt_fpr": metrics_opt["fpr"],
            "opt_fnr": metrics_opt["fnr"],
            "roc_auc": metrics_opt["roc_auc"],
            "pr_auc": metrics_opt["pr_auc"],
            "brier_score": metrics_opt["brier_score"],
        })

        oof_y_true.extend(y_out_val.tolist())
        oof_y_prob.extend(probs_out.tolist())
        oof_y_pred_tuned.extend((probs_out >= tau_inner).astype(int).tolist())

    fold_df = pd.DataFrame(outer_fold_rows)
    fold_means = {
        "precision_mean": round(float(fold_df["opt_precision"].mean()), 4),
        "precision_std": round(float(fold_df["opt_precision"].std(ddof=0)), 4),
        "recall_mean": round(float(fold_df["opt_recall"].mean()), 4),
        "recall_std": round(float(fold_df["opt_recall"].std(ddof=0)), 4),
        "f1_mean": round(float(fold_df["opt_f1"].mean()), 4),
        "f1_std": round(float(fold_df["opt_f1"].std(ddof=0)), 4),
        "accuracy_mean": round(float(fold_df["opt_accuracy"].mean()), 4),
        "accuracy_std": round(float(fold_df["opt_accuracy"].std(ddof=0)), 4),
        "fpr_mean": round(float(fold_df["opt_fpr"].mean()), 4),
        "fnr_mean": round(float(fold_df["opt_fnr"].mean()), 4),
        "roc_auc_mean": round(float(fold_df["roc_auc"].mean()), 4),
        "roc_auc_std": round(float(fold_df["roc_auc"].std(ddof=0)), 4),
        "pr_auc_mean": round(float(fold_df["pr_auc"].mean()), 4),
        "pr_auc_std": round(float(fold_df["pr_auc"].std(ddof=0)), 4),
        "brier_mean": round(float(fold_df["brier_score"].mean()), 4),
        "brier_std": round(float(fold_df["brier_score"].std(ddof=0)), 4),
    }

    y_oof_arr = np.array(oof_y_true)
    p_oof_arr = np.array(oof_y_prob)
    pred_oof_arr = np.array(oof_y_pred_tuned)
    from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
    cm_oof = confusion_matrix(y_oof_arr, pred_oof_arr, labels=[0, 1]).tolist()
    tn_o, fp_o = cm_oof[0][0], cm_oof[0][1]
    fn_o, tp_o = cm_oof[1][0], cm_oof[1][1]

    pooled_oof = {
        "precision": round(float(precision_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "recall": round(float(recall_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "f1": round(float(f1_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_oof_arr, pred_oof_arr)), 4),
        "fpr": round(float(fp_o / max(1, fp_o + tn_o)), 4),
        "fnr": round(float(fn_o / max(1, fn_o + tp_o)), 4),
        "roc_auc": round(float(roc_auc_score(y_oof_arr, p_oof_arr)), 4),
        "pr_auc": round(float(average_precision_score(y_oof_arr, p_oof_arr)), 4),
        "brier_score": round(float(brier_score_loss(y_oof_arr, p_oof_arr)), 4),
        "confusion_matrix": cm_oof,
    }

    median_tau = round(float(np.median(selected_thresholds)), 2)
    return {
        "config": cfg,
        "outer_folds": outer_fold_rows,
        "outer_fold_summary": fold_means,
        "pooled_oof": pooled_oof,
        "selected_thresholds_per_fold": selected_thresholds,
        "recommended_threshold": median_tau,
        "criterion": criteria_used[0] if criteria_used else "tier1",
    }


def train_and_evaluate_method_localizer(
    method_csv_path: Path,
    dev_repo_ids: set[int],
    ho_repo_ids: set[int],
    model_mgr: ModelManager,
    ds4_id: int,
) -> Optional[Dict[str, Any]]:
    """Train and validate a separate Method Localization model using strict repository split consistency."""
    if not method_csv_path.exists():
        logger.warning(f"Method localization CSV missing at {method_csv_path}; skipping localizer training.")
        return None

    df_m = pd.read_csv(method_csv_path)
    df_m["repository_id"] = df_m["repository_id"].astype(int)
    feat_cols = [c for c in DEFAULT_NUMERICAL_FEATURES if c in df_m.columns]
    for c in feat_cols:
        df_m[c] = pd.to_numeric(df_m[c], errors="coerce").fillna(0.0)

    dev_m = df_m[df_m["repository_id"].isin(dev_repo_ids)].reset_index(drop=True)
    ho_m = df_m[df_m["repository_id"].isin(ho_repo_ids)].reset_index(drop=True)
    if len(dev_m) < 50 or len(ho_m) < 20:
        logger.warning(f"Insufficient method localization rows (dev={len(dev_m)}, ho={len(ho_m)}).")
        return None

    X_tr, y_tr = dev_m[feat_cols], dev_m["is_buggy_method"].astype(int)
    X_ho, y_ho = ho_m[feat_cols], ho_m["is_buggy_method"].astype(int)

    # Inner GroupKFold threshold calibration inside dev_m
    gkf = GroupKFold(n_splits=min(5, int(dev_m["repository_id"].nunique())))
    oof_y, oof_p = [], []
    for itr, ival in gkf.split(X_tr, y_tr, groups=dev_m["repository_id"].values):
        prep = DataPreprocessor(impute_missing=True, remove_constant=True)
        X_i_tr = prep.fit_transform(X_tr.iloc[itr])
        X_i_va = prep.transform(X_tr.iloc[ival])
        clf = RandomForestClassifier(
            n_estimators=250, max_depth=10, min_samples_leaf=4,
            max_features="sqrt", class_weight="balanced", random_state=42, n_jobs=-1,
        )
        clf.fit(X_i_tr, y_tr.iloc[itr])
        oof_p.extend(clf.predict_proba(X_i_va)[..., 1].tolist())
        oof_y.extend(y_tr.iloc[ival].tolist())

    # Choose threshold maximizing F1 for ranking suspicious methods inside flagged classes
    from ml.cross_validation import compute_threshold_curve
    curve = compute_threshold_curve(np.array(oof_y), np.array(oof_p), thresholds=[round(x, 2) for x in np.arange(0.35, 0.80, 0.05)])
    best_pt = max(curve, key=lambda c: (c["f1"], c["precision"], c["recall"]))
    tau_m = float(best_pt["threshold"])

    prep_full = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_tr_proc = prep_full.fit_transform(X_tr)
    X_ho_proc = prep_full.transform(X_ho)[prep_full.feature_names_out_]

    clf_full = RandomForestClassifier(
        n_estimators=250, max_depth=10, min_samples_leaf=4,
        max_features="sqrt", class_weight="balanced", random_state=42, n_jobs=-1,
    )
    clf_full.fit(X_tr_proc, y_tr)
    ho_probs = clf_full.predict_proba(X_ho_proc)[:, 1]
    ho_metrics = compute_binary_classification_metrics(y_ho.values, ho_probs, threshold=tau_m)

    # Evaluate Top-1 and Top-3 method hit rate per BUG class in holdout
    ho_eval = ho_m[["class_observation_id", "is_buggy_method"]].copy()
    ho_eval["prob"] = ho_probs
    top1_hits, top3_hits, total_classes = 0, 0, 0
    for _, grp in ho_eval.groupby("class_observation_id"):
        if grp["is_buggy_method"].sum() == 0:
            continue
        total_classes += 1
        ranked = grp.sort_values("prob", ascending=False)
        if int(ranked.iloc[0]["is_buggy_method"]) == 1:
            top1_hits += 1
        if int(ranked.iloc[:3]["is_buggy_method"].sum()) > 0:
            top3_hits += 1

    loc_summary = {
        "dev_methods": int(len(dev_m)),
        "dev_classes": int(dev_m["class_observation_id"].nunique()),
        "dev_repos": int(dev_m["repository_id"].nunique()),
        "holdout_methods": int(len(ho_m)),
        "holdout_classes": int(total_classes),
        "holdout_repos": int(ho_m["repository_id"].nunique()),
        "holdout_positive_rate": round(float(y_ho.mean()), 4),
        "cv_threshold": tau_m,
        "holdout_metrics": ho_metrics,
        "holdout_top1_class_hit_rate": round(top1_hits / max(1, total_classes), 4),
        "holdout_top3_class_hit_rate": round(top3_hits / max(1, total_classes), 4),
    }

    model_mgr.save_model(
        model_name="method_localizer_top200_v4",
        model=clf_full,
        preprocessor=prep_full,
        feature_names=prep_full.feature_names_out_,
        parameters={"n_estimators": 250, "max_depth": 10, "min_samples_leaf": 4, "max_features": "sqrt", "class_weight": "balanced"},
        metrics=ho_metrics,
        dataset_id=ds4_id,
        split_summary={"train_repositories": sorted(dev_repo_ids), "test_repositories": sorted(ho_repo_ids)},
        overwrite=True,
        granularity="method_localizer",
        version="4.0.0",
        dataset_version="4.0.0",
        decision_threshold=tau_m,
        threshold_selection_criterion="inner_cv_max_f1",
    )
    (OUTPUT_DIR / "method_localizer_evaluation.json").write_text(json.dumps(loc_summary, indent=2), encoding="utf-8")
    return loc_summary


def main() -> None:
    t_start = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    builder = DatasetBuilder(repo_db)
    model_mgr = ModelManager(settings.storage.models_dir, db=repo_db)

    ds4 = repo_db.get_dataset_by_name("csharp_class_top200_v4")
    if not ds4:
        raise RuntimeError("Dataset 'csharp_class_top200_v4' not found in SQLite. Run run_top200_csharp_pipeline.py first.")

    ds4_id = ds4["id"]
    X_all, y_all, meta_all = builder.get_class_features_and_labels(ds4_id, list(CLASS_FEATURE_NAMES))

    n_repos = meta_all["repository_id"].nunique()
    print(f"Loaded Dataset #4 (ID #{ds4_id}): {len(X_all)} classes across {n_repos} repositories.")
    print(f"Class balance: {int((y_all == 1).sum())} BUG ({y_all.mean()*100:.2f}%), {int((y_all == 0).sum())} CLEAN.")

    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    dev_idx, holdout_idx = next(gss.split(X_all, y_all, groups=meta_all["repository_id"].values))

    X_dev, y_dev, meta_dev = X_all.iloc[dev_idx].reset_index(drop=True), y_all.iloc[dev_idx].reset_index(drop=True), meta_all.iloc[dev_idx].reset_index(drop=True)
    X_ho, y_ho, meta_ho = X_all.iloc[holdout_idx].reset_index(drop=True), y_all.iloc[holdout_idx].reset_index(drop=True), meta_all.iloc[holdout_idx].reset_index(drop=True)

    dev_repos = set(int(r) for r in meta_dev["repository_id"].unique())
    ho_repos = set(int(r) for r in meta_ho["repository_id"].unique())
    assert len(dev_repos.intersection(ho_repos)) == 0, "Repository leakage between dev and holdout!"
    dev_fps = set(meta_dev["source_fingerprint"].unique())
    ho_fps = set(meta_ho["source_fingerprint"].unique())
    assert len(dev_fps.intersection(ho_fps)) == 0, "Source fingerprint leakage between dev and holdout!"

    # Audit feature correlation and variance strictly on Dev split
    prep_audit = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_dev_audit = prep_audit.fit_transform(X_dev)
    corr_kept = select_infold_features(X_dev_audit, corr_prune=True, threshold=0.90)
    dropped_corr = [c for c in X_dev_audit.columns if c not in corr_kept]
    feature_audit = {
        "input_features": len(CLASS_FEATURE_NAMES),
        "nonzero_variance_features": len(prep_audit.feature_names_out_),
        "spearman_gt_0_90_redundant_candidates": dropped_corr,
        "retained_after_corr_pruning": len(corr_kept),
    }
    (OUTPUT_DIR / "feature_sufficiency_audit.json").write_text(json.dumps(feature_audit, indent=2), encoding="utf-8")

    catalog = build_classifier_catalog(random_state=42)
    nested_results: List[Dict[str, Any]] = []
    comparison_rows: List[Dict[str, Any]] = []

    for cfg in catalog:
        print(f"Evaluating {cfg['config_id']} ({cfg['family']}) in 5x4 Nested GroupKFold...")
        res = evaluate_nested_cv(cfg, X_dev, y_dev, meta_dev, n_outer=5, n_inner=4)
        nested_results.append(res)

        ofs = res["outer_fold_summary"]
        oof = res["pooled_oof"]
        comparison_rows.append({
            "config_id": cfg["config_id"],
            "family": cfg["family"],
            "algorithm": cfg["algorithm"],
            "bundle_name": cfg.get("bundle_name") or "",
            "recommended_threshold": res["recommended_threshold"],
            "outer_precision_mean": ofs["precision_mean"],
            "outer_precision_std": ofs["precision_std"],
            "outer_recall_mean": ofs["recall_mean"],
            "outer_recall_std": ofs["recall_std"],
            "outer_f1_mean": ofs["f1_mean"],
            "outer_f1_std": ofs["f1_std"],
            "outer_roc_auc_mean": ofs["roc_auc_mean"],
            "outer_pr_auc_mean": ofs["pr_auc_mean"],
            "oof_precision": oof["precision"],
            "oof_recall": oof["recall"],
            "oof_f1": oof["f1"],
            "oof_accuracy": oof["accuracy"],
            "oof_fpr": oof["fpr"],
            "oof_fnr": oof["fnr"],
            "oof_roc_auc": oof["roc_auc"],
            "oof_pr_auc": oof["pr_auc"],
            "oof_brier": oof["brier_score"],
            "oof_confusion_matrix": json.dumps(oof["confusion_matrix"]),
        })

    def selection_rank_key(row: Dict[str, Any]) -> Tuple[int, float, float, float]:
        if row["algorithm"] == "dummy":
            return (-1, 0.0, 0.0, 0.0)
        prec = row["oof_precision"]
        rec = row["oof_recall"]
        tier = 2 if (prec >= 0.77 and rec >= 0.50) else (1 if (prec >= 0.75 and rec >= 0.50) else 0)
        return (tier, row["oof_f1"], row["oof_recall"], row["oof_roc_auc"])

    comparison_rows.sort(key=selection_rank_key, reverse=True)
    pd.DataFrame(comparison_rows).to_csv(OUTPUT_DIR / "top200_model_comparison.csv", index=False)

    champion_row = comparison_rows[0]
    champion_id = champion_row["config_id"]
    print(f"\nChampion by Nested CV: {champion_id} (OOF Prec={champion_row['oof_precision']:.4f}, Rec={champion_row['oof_recall']:.4f}, F1={champion_row['oof_f1']:.4f}, tau={champion_row['recommended_threshold']})")

    holdout_rows: List[Dict[str, Any]] = []
    champion_holdout_details: Dict[str, Any] = {}
    champion_probs_ho: Optional[np.ndarray] = None

    split_summary = {
        "train_repositories": sorted(dev_repos),
        "test_repositories": sorted(ho_repos),
        "train_repo_count": len(dev_repos),
        "test_repo_count": len(ho_repos),
        "train_samples": len(X_dev),
        "test_samples": len(X_ho),
        "train_buggy_count": int((y_dev == 1).sum()),
        "train_clean_count": int((y_dev == 0).sum()),
        "test_buggy_count": int((y_ho == 1).sum()),
        "test_clean_count": int((y_ho == 0).sum()),
    }

    for res in nested_results:
        cfg = res["config"]
        cid = cfg["config_id"]
        tau_cv = res["recommended_threshold"]
        probs_ho, fitted_model, fitted_preproc, sel_cols = fit_and_predict_fold(cfg, X_dev, y_dev, X_ho)
        ho_metrics_tau = compute_binary_classification_metrics(y_ho.values, probs_ho, threshold=tau_cv)
        ho_metrics_nom = compute_binary_classification_metrics(y_ho.values, probs_ho, threshold=0.50)

        ho_row = {
            "config_id": cid,
            "family": cfg["family"],
            "algorithm": cfg["algorithm"],
            "threshold_cv_selected": tau_cv,
            "ho_precision": ho_metrics_tau["precision"],
            "ho_recall": ho_metrics_tau["recall"],
            "ho_f1": ho_metrics_tau["f1"],
            "ho_accuracy": ho_metrics_tau["accuracy"],
            "ho_roc_auc": ho_metrics_tau["roc_auc"],
            "ho_pr_auc": ho_metrics_tau["pr_auc"],
            "ho_brier": ho_metrics_tau["brier_score"],
            "ho_fpr": ho_metrics_tau["fpr"],
            "ho_fnr": ho_metrics_tau["fnr"],
            "ho_confusion_matrix": json.dumps(ho_metrics_tau["confusion_matrix"]),
            "ho_nom_precision": ho_metrics_nom["precision"],
            "ho_nom_recall": ho_metrics_nom["recall"],
            "ho_nom_f1": ho_metrics_nom["f1"],
        }
        holdout_rows.append(ho_row)

        if cid == champion_id:
            champion_holdout_details = ho_metrics_tau
            champion_probs_ho = probs_ho

        bundle_name = cfg.get("bundle_name")
        save_names: List[str] = []
        if bundle_name:
            save_names.append(bundle_name)
        if cid == champion_id:
            save_names.append("class_bug_classifier_top200_v4")

        if save_names:
            mdi_imp = []
            raw_est = fitted_model.named_steps["classifier"] if hasattr(fitted_model, "named_steps") else fitted_model
            if hasattr(raw_est, "feature_importances_"):
                mdi_imp = sorted(
                    [{"feature": f, "importance": float(v)} for f, v in zip(sel_cols, raw_est.feature_importances_)],
                    key=lambda x: x["importance"],
                    reverse=True,
                )
            perm_imp = []
            try:
                X_ho_sel = fitted_preproc.transform(X_ho)[sel_cols]
                perm = permutation_importance(fitted_model, X_ho_sel, y_ho, n_repeats=5, random_state=42, n_jobs=-1)
                perm_imp = sorted(
                    [
                        {"feature": f, "importance_mean": float(m), "importance_std": float(s)}
                        for f, m, s in zip(sel_cols, perm.importances_mean, perm.importances_std)
                    ],
                    key=lambda x: x["importance_mean"],
                    reverse=True,
                )
            except Exception:
                pass

            metrics_payload = {
                "accuracy": ho_metrics_tau["accuracy"],
                "precision": ho_metrics_tau["precision"],
                "recall": ho_metrics_tau["recall"],
                "f1": ho_metrics_tau["f1"],
                "fpr": ho_metrics_tau["fpr"],
                "fnr": ho_metrics_tau["fnr"],
                "roc_auc": ho_metrics_tau["roc_auc"],
                "average_precision": ho_metrics_tau["pr_auc"],
                "brier_score": ho_metrics_tau["brier_score"],
                "confusion_matrix": ho_metrics_tau["confusion_matrix"],
                "decision_threshold": tau_cv,
                "nested_cv_oof": res["pooled_oof"],
                "nested_cv_outer_mean": res["outer_fold_summary"],
                "mdi_feature_importances": mdi_imp,
                "permutation_feature_importances": perm_imp,
            }
            for sname in save_names:
                model_mgr.save_model(
                    model_name=sname,
                    model=fitted_model,
                    preprocessor=fitted_preproc,
                    feature_names=sel_cols,
                    parameters=cfg["params"],
                    metrics=metrics_payload,
                    dataset_id=ds4_id,
                    split_summary=split_summary,
                    overwrite=True,
                    granularity="class",
                    version="4.0.0",
                    dataset_version="4.0.0",
                    decision_threshold=tau_cv,
                    threshold_selection_criterion=res.get("criterion", "inner_cv_precision_75_f1_recall"),
                )

    pd.DataFrame(holdout_rows).to_csv(OUTPUT_DIR / "top200_holdout_results.csv", index=False)

    champ_nested = next(r for r in nested_results if r["config"]["config_id"] == champion_id)
    pd.DataFrame(champ_nested["outer_folds"]).to_csv(OUTPUT_DIR / "top200_champion_outer_folds.csv", index=False)

    if champion_probs_ho is not None:
        tau_c = champion_row["recommended_threshold"]
        ho_eval_df = meta_ho[["repository_name", "class_name", "qualified_class_name", "file_path", "label"]].copy()
        ho_eval_df["predicted_prob"] = np.round(champion_probs_ho, 4)
        ho_eval_df["predicted_label"] = (champion_probs_ho >= tau_c).astype(int)
        ho_eval_df["predicted_classification"] = np.where(ho_eval_df["predicted_label"] == 1, "BUG", "CLEAN")
        ho_eval_df["class_loc"] = X_ho["class_loc"].values
        ho_eval_df["method_count"] = X_ho["method_count"].values
        ho_eval_df["total_cyclomatic_complexity"] = X_ho["total_cyclomatic_complexity"].values
        ho_eval_df["max_nesting_depth"] = X_ho["max_nesting_depth"].values
        ho_eval_df.to_csv(OUTPUT_DIR / "top200_holdout_error_analysis.csv", index=False)

        repo_ho_rows = []
        for rname, grp in ho_eval_df.groupby("repository_name"):
            m_repo = compute_binary_classification_metrics(grp["label"].values, grp["predicted_prob"].values, threshold=tau_c)
            repo_ho_rows.append({
                "repository_name": rname,
                "samples": len(grp),
                "bug_classes": int((grp["label"] == 1).sum()),
                "clean_classes": int((grp["label"] == 0).sum()),
                "precision": m_repo["precision"],
                "recall": m_repo["recall"],
                "f1": m_repo["f1"],
                "fpr": m_repo["fpr"],
                "fnr": m_repo["fnr"],
                "roc_auc": m_repo["roc_auc"],
            })
        pd.DataFrame(repo_ho_rows).to_csv(OUTPUT_DIR / "top200_holdout_per_repository.csv", index=False)

    method_loc_summary = train_and_evaluate_method_localizer(
        method_csv_path=settings.storage.processed_dir / "method_localization_top200_v4.csv",
        dev_repo_ids=dev_repos,
        ho_repo_ids=ho_repos,
        model_mgr=model_mgr,
        ds4_id=ds4_id,
    )

    ho_tp = champion_holdout_details.get("true_positives", 0)
    ho_fn = champion_holdout_details.get("false_negatives", 0)
    ho_fp = champion_holdout_details.get("false_positives", 0)
    ho_tn = champion_holdout_details.get("true_negatives", 0)
    sens = ho_tp / max(1, ho_tp + ho_fn)
    fpr = ho_fp / max(1, ho_fp + ho_tn)
    base_rate_table = [
        {"assumed_prevalence": p, "bayesian_precision": compute_bayesian_precision(sens, fpr, p)}
        for p in [0.02, 0.05, 0.10, 0.20, round(float(y_all.mean()), 4)]
    ]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.time() - t_start, 2),
        "dataset": {
            "id": ds4_id,
            "name": "csharp_class_top200_v4",
            "version": "4.0.0",
            "total_repositories": n_repos,
            "total_classes": len(X_all),
            "bug_classes": int((y_all == 1).sum()),
            "clean_classes": int((y_all == 0).sum()),
            "bug_prevalence": round(float(y_all.mean()), 4),
            "feature_count": len(CLASS_FEATURE_NAMES),
        },
        "feature_sufficiency_audit": feature_audit,
        "partitioning": split_summary,
        "champion_model": {
            "config_id": champion_id,
            "family": champion_row["family"],
            "threshold_cv_selected": champion_row["recommended_threshold"],
            "nested_cv_oof": champ_nested["pooled_oof"],
            "nested_cv_outer_mean": champ_nested["outer_fold_summary"],
            "holdout_evaluation": champion_holdout_details,
            "precision_target_75_achieved_oof": champ_nested["pooled_oof"]["precision"] >= 0.75,
            "precision_target_75_achieved_holdout": champion_holdout_details.get("precision", 0.0) >= 0.75,
        },
        "method_localizer": method_loc_summary,
        "base_rate_precision_analysis": base_rate_table,
        "nested_cv_comparison": comparison_rows,
        "holdout_comparison": holdout_rows,
    }
    (OUTPUT_DIR / "top200_classifier_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== TOP-200 CLASSIFIER OPTIMIZATION COMPLETE ===")
    print(f"Holdout Champion ({champion_id}) at tau={champion_row['recommended_threshold']}: "
          f"Prec={champion_holdout_details.get('precision'):.4f}, Rec={champion_holdout_details.get('recall'):.4f}, "
          f"F1={champion_holdout_details.get('f1'):.4f}, FPR={champion_holdout_details.get('fpr'):.4f}, "
          f"FNR={champion_holdout_details.get('fnr'):.4f}, AUC={champion_holdout_details.get('roc_auc'):.4f}")
    if method_loc_summary:
        hm = method_loc_summary["holdout_metrics"]
        print(f"Method Localizer Holdout: Prec={hm['precision']:.4f}, Rec={hm['recall']:.4f}, F1={hm['f1']:.4f}, "
              f"AUC={hm['roc_auc']:.4f}, Top-1 hit={method_loc_summary['holdout_top1_class_hit_rate']:.4f}, "
              f"Top-3 hit={method_loc_summary['holdout_top3_class_hit_rate']:.4f}")


if __name__ == "__main__":
    main()
