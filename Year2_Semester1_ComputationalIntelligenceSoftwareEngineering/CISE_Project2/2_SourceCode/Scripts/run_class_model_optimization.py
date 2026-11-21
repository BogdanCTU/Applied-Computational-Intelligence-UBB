"""Class-Level Machine Learning Benchmark & Precision Optimization Pipeline.

Evaluates all 7 required model families on Dataset #3 (csharp_class_empirical_v3 v3.0.0)
across >= 100 C# repositories using:
1. Strict repository-level separation into Development Corpus (~80% repos) and
   Untouched Independent Repository Holdout (~20% repos).
2. Nested GroupKFold cross-validation (5 outer folds x 4 inner folds) inside Development Corpus.
3. In-fold preprocessing (median imputation, zero-variance filtering, optional correlation pruning,
   and scaling for Logistic Regression) fitted strictly on training partitions.
4. Inner-fold precision-oriented threshold selection targeting Precision >= 80% (min 75%)
   with meaningful Recall >= 50%.
5. Single-shot evaluation on the untouched Independent Repository Holdout.
6. Persistence of versioned class-level model bundles (storing selected decision_threshold)
   and complete experimental artifacts in 3_TestResults/ClassModelOptimization/.
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
    select_precision_optimal_threshold,
)
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager
from ml.preprocessing import DataPreprocessor
from services.dataset.dataset_builder import DatasetBuilder

OUTPUT_DIR = PROJECT_ROOT / "3_TestResults" / "ClassModelOptimization"


def build_class_candidate_catalog(random_state: int = 42) -> List[Dict[str, Any]]:
    """Define model configurations spanning all 7 required model families."""
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
            "bundle_name": "lr_class_v3",
            "scaler": "standard",
            "corr_prune": True,
            "params": {"C": 0.1, "max_iter": 1000, "class_weight": "balanced", "random_state": random_state},
        },
        {
            "config_id": "lr_robust_l2_c01",
            "family": "Logistic Regression",
            "algorithm": "logistic_regression",
            "bundle_name": None,
            "scaler": "robust",
            "corr_prune": True,
            "params": {"C": 0.1, "max_iter": 1000, "class_weight": None, "random_state": random_state},
        },
        # 3. Decision Tree
        {
            "config_id": "dt_depth6_leaf10_bal",
            "family": "Decision Tree",
            "algorithm": "decision_tree",
            "bundle_name": "dt_class_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {"max_depth": 6, "min_samples_split": 12, "min_samples_leaf": 10, "class_weight": "balanced", "random_state": random_state},
        },
        {
            "config_id": "dt_depth5_leaf15",
            "family": "Decision Tree",
            "algorithm": "decision_tree",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {"max_depth": 5, "min_samples_split": 15, "min_samples_leaf": 15, "class_weight": None, "random_state": random_state},
        },
        # 4. Random Forest (Baseline & Precision-Oriented Variants)
        {
            "config_id": "rf_baseline_compact",
            "family": "Random Forest (Baseline)",
            "algorithm": "random_forest",
            "bundle_name": "rf_class_baseline_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 100, "max_depth": 8, "min_samples_split": 5,
                "min_samples_leaf": 4, "max_features": "sqrt", "class_weight": "balanced",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_opt_depth12_leaf4_log2",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "bundle_name": "rf_class_opt_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 300, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced_subsample",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "rf_opt_depth10_leaf6_unweighted",
            "family": "Random Forest",
            "algorithm": "random_forest",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 300, "max_depth": 10, "min_samples_split": 10,
                "min_samples_leaf": 6, "max_features": "sqrt", "class_weight": None,
                "random_state": random_state, "n_jobs": -1,
            },
        },
        # 5. Extra Trees
        {
            "config_id": "et_opt_depth10_leaf4_log2_bal",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "bundle_name": "et_class_opt_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 300, "max_depth": 10, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced",
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "et_opt_depth12_leaf5_sqrt",
            "family": "Extra Trees",
            "algorithm": "extra_trees",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 300, "max_depth": 12, "min_samples_split": 8,
                "min_samples_leaf": 5, "max_features": "sqrt", "class_weight": None,
                "random_state": random_state, "n_jobs": -1,
            },
        },
        # 6. Histogram Gradient Boosting
        {
            "config_id": "hgb_depth5_leaf20_l2_2",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "bundle_name": "hgb_class_opt_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "learning_rate": 0.05, "max_iter": 180, "max_depth": 5,
                "max_leaf_nodes": 20, "min_samples_leaf": 20, "l2_regularization": 2.0,
                "class_weight": "balanced", "random_state": random_state,
            },
        },
        {
            "config_id": "hgb_depth4_leaf25_unweighted",
            "family": "HistGradientBoosting",
            "algorithm": "hist_gb",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "learning_rate": 0.04, "max_iter": 180, "max_depth": 4,
                "max_leaf_nodes": 15, "min_samples_leaf": 25, "l2_regularization": 5.0,
                "class_weight": None, "random_state": random_state,
            },
        },
        # 7. Calibrated Tree Ensemble (Platt Sigmoid Calibration)
        {
            "config_id": "calibrated_rf_sigmoid",
            "family": "Calibrated Ensemble",
            "algorithm": "calibrated_rf",
            "bundle_name": "calibrated_class_v3",
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 200, "max_depth": 10, "min_samples_split": 8,
                "min_samples_leaf": 5, "max_features": "log2", "class_weight": "balanced",
                "calibration_method": "sigmoid", "calibration_cv": 3,
                "random_state": random_state, "n_jobs": -1,
            },
        },
        {
            "config_id": "calibrated_et_isotonic",
            "family": "Calibrated Ensemble",
            "algorithm": "calibrated_et",
            "bundle_name": None,
            "scaler": "none",
            "corr_prune": False,
            "params": {
                "n_estimators": 200, "max_depth": 10, "min_samples_split": 8,
                "min_samples_leaf": 4, "max_features": "log2", "class_weight": "balanced",
                "calibration_method": "isotonic", "calibration_cv": 3,
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
    """Run strict 5-outer x 4-inner GroupKFold nested validation with precision-oriented inner threshold tuning."""
    groups_dev = meta_dev["repository_id"].values
    outer_gkf = GroupKFold(n_splits=min(n_outer, len(np.unique(groups_dev))))

    outer_fold_rows: List[Dict[str, Any]] = []
    oof_y_true: List[int] = []
    oof_y_prob: List[float] = []
    oof_y_pred_tuned: List[int] = []
    oof_repo_names: List[str] = []
    selected_thresholds: List[float] = []

    for fold_idx, (tr_idx, val_idx) in enumerate(outer_gkf.split(X_dev, y_dev, groups=groups_dev), 1):
        X_out_tr, X_out_val = X_dev.iloc[tr_idx], X_dev.iloc[val_idx]
        y_out_tr, y_out_val = y_dev.iloc[tr_idx], y_dev.iloc[val_idx]
        meta_out_tr, meta_out_val = meta_dev.iloc[tr_idx], meta_dev.iloc[val_idx]

        # Inner 4-fold GroupKFold strictly inside outer-train repositories
        inner_groups = meta_out_tr["repository_id"].values
        inner_splits = min(n_inner, len(np.unique(inner_groups)))
        inner_gkf = GroupKFold(n_splits=inner_splits)

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

        thresh_res = select_precision_optimal_threshold(
            np.array(inner_y_true),
            np.array(inner_y_prob),
            min_precision_preferred=0.80,
            min_precision_acceptable=0.75,
            min_recall=0.50,
            min_predicted_positives=max(10, int(0.03 * len(inner_y_true))),
        )
        tau_inner = float(thresh_res["selected_threshold"])
        selected_thresholds.append(tau_inner)

        # Fit on outer-train and evaluate on untouched outer-val fold
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
            "roc_auc": metrics_opt["roc_auc"],
            "pr_auc": metrics_opt["pr_auc"],
            "brier_score": metrics_opt["brier_score"],
        })

        oof_y_true.extend(y_out_val.tolist())
        oof_y_prob.extend(probs_out.tolist())
        oof_y_pred_tuned.extend((probs_out >= tau_inner).astype(int).tolist())
        oof_repo_names.extend(meta_out_val["repository_name"].tolist())

    # Outer fold mean +/- std
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
        "roc_auc_mean": round(float(fold_df["roc_auc"].mean()), 4),
        "roc_auc_std": round(float(fold_df["roc_auc"].std(ddof=0)), 4),
        "pr_auc_mean": round(float(fold_df["pr_auc"].mean()), 4),
        "pr_auc_std": round(float(fold_df["pr_auc"].std(ddof=0)), 4),
        "brier_mean": round(float(fold_df["brier_score"].mean()), 4),
        "brier_std": round(float(fold_df["brier_score"].std(ddof=0)), 4),
    }

    # Pooled OOF predictions using nested per-fold predictions
    y_oof_arr = np.array(oof_y_true)
    p_oof_arr = np.array(oof_y_prob)
    pred_oof_arr = np.array(oof_y_pred_tuned)
    from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
    pooled_oof = {
        "precision": round(float(precision_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "recall": round(float(recall_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "f1": round(float(f1_score(y_oof_arr, pred_oof_arr, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_oof_arr, pred_oof_arr)), 4),
        "roc_auc": round(float(roc_auc_score(y_oof_arr, p_oof_arr)), 4),
        "pr_auc": round(float(average_precision_score(y_oof_arr, p_oof_arr)), 4),
        "brier_score": round(float(brier_score_loss(y_oof_arr, p_oof_arr)), 4),
        "confusion_matrix": confusion_matrix(y_oof_arr, pred_oof_arr, labels=[0, 1]).tolist(),
    }

    # Global inner-CV threshold (median of inner-fold optimal thresholds)
    median_tau = round(float(np.median(selected_thresholds)), 2)

    return {
        "config": cfg,
        "outer_folds": outer_fold_rows,
        "outer_fold_summary": fold_means,
        "pooled_oof": pooled_oof,
        "selected_thresholds_per_fold": selected_thresholds,
        "recommended_threshold": median_tau,
        "oof_y_true": oof_y_true,
        "oof_y_prob": oof_y_prob,
        "oof_y_pred_tuned": oof_y_pred_tuned,
        "oof_repo_names": oof_repo_names,
    }


def main() -> None:
    t_start = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    builder = DatasetBuilder(repo_db)
    model_mgr = ModelManager(settings.storage.models_dir, db=repo_db)

    ds3 = repo_db.get_dataset_by_name("csharp_class_empirical_v3")
    if not ds3:
        raise RuntimeError("Dataset 'csharp_class_empirical_v3' not found in SQLite. Run run_100_repo_class_pipeline.py first.")

    ds3_id = ds3["id"]
    X_all, y_all, meta_all = builder.get_class_features_and_labels(ds3_id, list(CLASS_FEATURE_NAMES))

    n_repos = meta_all["repository_id"].nunique()
    print(f"Loaded Dataset #3 (ID #{ds3_id}): {len(X_all)} class observations across {n_repos} repositories.")
    print(f"Class balance: {int((y_all == 1).sum())} defect-prone ({y_all.mean()*100:.2f}%), {int((y_all == 0).sum())} candidate-clean.")

    # Partition into ~80% Development Repos (Nested 5x4 CV) and ~20% Untouched Independent Holdout Repos
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    dev_idx, holdout_idx = next(gss.split(X_all, y_all, groups=meta_all["repository_id"].values))

    X_dev, y_dev, meta_dev = X_all.iloc[dev_idx].reset_index(drop=True), y_all.iloc[dev_idx].reset_index(drop=True), meta_all.iloc[dev_idx].reset_index(drop=True)
    X_ho, y_ho, meta_ho = X_all.iloc[holdout_idx].reset_index(drop=True), y_all.iloc[holdout_idx].reset_index(drop=True), meta_all.iloc[holdout_idx].reset_index(drop=True)

    dev_repos = set(meta_dev["repository_id"].unique())
    ho_repos = set(meta_ho["repository_id"].unique())
    assert len(dev_repos.intersection(ho_repos)) == 0, "Repository leakage between dev and holdout!"
    dev_fps = set(meta_dev["source_fingerprint"].unique())
    ho_fps = set(meta_ho["source_fingerprint"].unique())
    assert len(dev_fps.intersection(ho_fps)) == 0, "Fingerprint leakage between dev and holdout!"

    print(f"Development partition: {len(dev_repos)} repos ({len(X_dev)} classes, {y_dev.mean()*100:.2f}% positive)")
    print(f"Untouched Holdout partition: {len(ho_repos)} repos ({len(X_ho)} classes, {y_ho.mean()*100:.2f}% positive)")

    catalog = build_class_candidate_catalog(random_state=42)
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
            "outer_accuracy_mean": ofs["accuracy_mean"],
            "outer_accuracy_std": ofs["accuracy_std"],
            "outer_roc_auc_mean": ofs["roc_auc_mean"],
            "outer_roc_auc_std": ofs["roc_auc_std"],
            "outer_pr_auc_mean": ofs["pr_auc_mean"],
            "outer_pr_auc_std": ofs["pr_auc_std"],
            "outer_brier_mean": ofs["brier_mean"],
            "outer_brier_std": ofs["brier_std"],
            "oof_precision": oof["precision"],
            "oof_recall": oof["recall"],
            "oof_f1": oof["f1"],
            "oof_accuracy": oof["accuracy"],
            "oof_roc_auc": oof["roc_auc"],
            "oof_pr_auc": oof["pr_auc"],
            "oof_brier": oof["brier_score"],
            "oof_confusion_matrix": json.dumps(oof["confusion_matrix"]),
        })

    # Rank non-dummy models by precision target compliance first, then F1/PR-AUC
    def selection_rank_key(row: Dict[str, Any]) -> Tuple[int, float, float, float]:
        if row["algorithm"] == "dummy":
            return (-1, 0.0, 0.0, 0.0)
        prec = row["oof_precision"]
        rec = row["oof_recall"]
        tier = 2 if (prec >= 0.80 and rec >= 0.50) else (1 if (prec >= 0.75 and rec >= 0.50) else 0)
        return (tier, row["oof_f1"], row["oof_pr_auc"], row["oof_roc_auc"])

    comparison_rows.sort(key=selection_rank_key, reverse=True)
    pd.DataFrame(comparison_rows).to_csv(OUTPUT_DIR / "class_model_comparison.csv", index=False)

    champion_row = comparison_rows[0]
    champion_id = champion_row["config_id"]
    print(f"\nChampion by Nested CV: {champion_id} (OOF Prec={champion_row['oof_precision']:.4f}, Rec={champion_row['oof_recall']:.4f}, F1={champion_row['oof_f1']:.4f}, tau={champion_row['recommended_threshold']})")

    # Fit final models on Development Corpus and perform ONE-SHOT evaluation on Untouched Holdout
    holdout_rows: List[Dict[str, Any]] = []
    champion_holdout_details: Dict[str, Any] = {}
    champion_probs_ho: Optional[np.ndarray] = None

    split_summary = {
        "train_repositories": [int(r) for r in sorted(dev_repos)],
        "test_repositories": [int(r) for r in sorted(ho_repos)],
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
            "ho_confusion_matrix": json.dumps(ho_metrics_tau["confusion_matrix"]),
            "ho_nom_precision": ho_metrics_nom["precision"],
            "ho_nom_recall": ho_metrics_nom["recall"],
            "ho_nom_f1": ho_metrics_nom["f1"],
        }
        holdout_rows.append(ho_row)

        if cid == champion_id:
            champion_holdout_details = ho_metrics_tau
            champion_probs_ho = probs_ho

        # Persist serialized model bundles for champion & representative models per family
        bundle_name = cfg.get("bundle_name")
        save_names: List[str] = []
        if bundle_name:
            save_names.append(bundle_name)
        if cid == champion_id:
            save_names.append("class_precision_champion_v3")

        if save_names:
            # Compute feature importances on dev+holdout test cleanly
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
                    dataset_id=ds3_id,
                    split_summary=split_summary,
                    overwrite=True,
                    granularity="class",
                    version="3.0.0",
                    dataset_version="3.0.0",
                    decision_threshold=tau_cv,
                    threshold_selection_criterion="inner_fold_precision_optimized",
                )

    pd.DataFrame(holdout_rows).to_csv(OUTPUT_DIR / "class_holdout_results.csv", index=False)

    # Save champion per-repository performance & error analysis on Holdout
    champ_nested = next(r for r in nested_results if r["config"]["config_id"] == champion_id)
    pd.DataFrame(champ_nested["outer_folds"]).to_csv(OUTPUT_DIR / "champion_outer_folds.csv", index=False)

    if champion_probs_ho is not None:
        tau_c = champion_row["recommended_threshold"]
        ho_eval_df = meta_ho[["repository_name", "class_name", "qualified_class_name", "file_path", "label"]].copy()
        ho_eval_df["predicted_prob"] = np.round(champion_probs_ho, 4)
        ho_eval_df["predicted_label"] = (champion_probs_ho >= tau_c).astype(int)
        ho_eval_df["class_loc"] = X_ho["class_loc"].values
        ho_eval_df["method_count"] = X_ho["method_count"].values
        ho_eval_df["total_cyclomatic_complexity"] = X_ho["total_cyclomatic_complexity"].values
        ho_eval_df["max_nesting_depth"] = X_ho["max_nesting_depth"].values
        ho_eval_df.to_csv(OUTPUT_DIR / "holdout_error_analysis.csv", index=False)

        # Per-repository holdout summary
        repo_ho_rows = []
        for rname, grp in ho_eval_df.groupby("repository_name"):
            m_repo = compute_binary_classification_metrics(grp["label"].values, grp["predicted_prob"].values, threshold=tau_c)
            repo_ho_rows.append({
                "repository_name": rname,
                "samples": len(grp),
                "positive": int((grp["label"] == 1).sum()),
                "clean": int((grp["label"] == 0).sum()),
                "precision": m_repo["precision"],
                "recall": m_repo["recall"],
                "f1": m_repo["f1"],
                "roc_auc": m_repo["roc_auc"],
            })
        pd.DataFrame(repo_ho_rows).to_csv(OUTPUT_DIR / "holdout_per_repository.csv", index=False)

    # Base-rate Bayesian precision sensitivity analysis
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
            "id": ds3_id,
            "name": "csharp_class_empirical_v3",
            "version": "3.0.0",
            "total_repositories": n_repos,
            "total_classes": len(X_all),
            "positive_classes": int((y_all == 1).sum()),
            "clean_classes": int((y_all == 0).sum()),
            "positive_prevalence": round(float(y_all.mean()), 4),
            "feature_count": len(CLASS_FEATURE_NAMES),
        },
        "partitioning": split_summary,
        "champion_model": {
            "config_id": champion_id,
            "family": champion_row["family"],
            "threshold_cv_selected": champion_row["recommended_threshold"],
            "nested_cv_oof": champ_nested["pooled_oof"],
            "nested_cv_outer_mean": champ_nested["outer_fold_summary"],
            "holdout_evaluation": champion_holdout_details,
            "precision_target_75_achieved_oof": champ_nested["pooled_oof"]["precision"] >= 0.75,
            "precision_target_80_achieved_oof": champ_nested["pooled_oof"]["precision"] >= 0.80,
            "precision_target_75_achieved_holdout": champion_holdout_details.get("precision", 0.0) >= 0.75,
            "precision_target_80_achieved_holdout": champion_holdout_details.get("precision", 0.0) >= 0.80,
        },
        "base_rate_precision_analysis": base_rate_table,
        "nested_cv_comparison": comparison_rows,
        "holdout_comparison": holdout_rows,
    }
    (OUTPUT_DIR / "class_optimization_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Ensure existing 4 historical method-level bundles are also reflected cleanly without modifying them
    print("\n=== CLASS ML OPTIMIZATION COMPLETE ===")
    print(f"Holdout Champion ({champion_id}) at tau={champion_row['recommended_threshold']}: "
          f"Prec={champion_holdout_details.get('precision'):.4f}, Rec={champion_holdout_details.get('recall'):.4f}, "
          f"F1={champion_holdout_details.get('f1'):.4f}, AUC={champion_holdout_details.get('roc_auc'):.4f}")


if __name__ == "__main__":
    main()
