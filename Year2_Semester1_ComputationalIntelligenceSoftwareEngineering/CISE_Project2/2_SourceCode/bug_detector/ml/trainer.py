"""Random Forest grouped-CV trainer, hyperparameter optimizer, and baseline comparisons."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.preprocessing import MaxAbsScaler

from bug_detector.config.settings import (
    EXPERIMENT_DEFINITIONS,
    AppConfig,
    FeatureConfig,
    RandomForestConfig,
    load_config,
)
from bug_detector.db import BugDetectorRepository, DatabaseManager
from bug_detector.explainability.global_importance import compute_global_importances
from bug_detector.features import FeaturePipeline
from bug_detector.logging_utils import get_logger
from bug_detector.ml.calibration import calibrate_three_way_thresholds
from bug_detector.ml.evaluator import compute_classification_metrics
from bug_detector.ml.registry import get_dependency_versions
from bug_detector.ml.splitting import make_grouped_cv_splits

logger = get_logger(__name__)


def load_dataset_records_from_db(dataset_version: str, config: AppConfig | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load dataset sample records + extracted feature JSON payloads + dataset metadata."""
    cfg = config or load_config()
    repo = BugDetectorRepository(DatabaseManager(cfg.db_path))
    with repo.db.connect() as conn:
        drow = conn.execute(
            "SELECT * FROM dataset_versions WHERE dataset_version = ?", (dataset_version,)
        ).fetchone()
        if not drow:
            raise ValueError(f"Dataset version not found in database: {dataset_version}")
        rows = conn.execute(
            """
            SELECT s.*, b.raw_source, b.normalized_source,
                   f.semantic_model_available, f.cfg_available, f.dfg_available, f.extraction_failed,
                   f.tokens_json, f.api_calls_json, f.lexical_json, f.ast_json,
                   f.cfg_json, f.dfg_json, f.structural_json
            FROM dataset_samples s
            JOIN source_blobs b ON b.source_hash = s.source_hash
            LEFT JOIN feature_extractions f ON f.sample_id = s.sample_id
            WHERE s.dataset_version = ?
            ORDER BY s.sample_id
            """,
            (dataset_version,),
        ).fetchall()

    records: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["source_code"] = d.pop("raw_source")
        d["semantic_model_available"] = bool(d.get("semantic_model_available", 0))
        d["cfg_available"] = bool(d.get("cfg_available", 0))
        d["dfg_available"] = bool(d.get("dfg_available", 0))
        d["extraction_failed"] = bool(d.get("extraction_failed", 0))
        d["tokens_normalized"] = json.loads(d.pop("tokens_json") or "[]")
        d["api_calls"] = json.loads(d.pop("api_calls_json") or "[]")
        d["lexical_metrics"] = json.loads(d.pop("lexical_json") or "{}")
        d["ast_metrics"] = json.loads(d.pop("ast_json") or "{}")
        d["cfg_metrics"] = json.loads(d.pop("cfg_json") or "{}")
        d["dfg_metrics"] = json.loads(d.pop("dfg_json") or "{}")
        d["structural_metrics"] = json.loads(d.pop("structural_json") or "{}")
        records.append(d)
    return records, dict(drow)


def _fit_and_predict_rf(
    X_train: Any,
    y_train: np.ndarray,
    X_val: Any,
    rf_cfg: RandomForestConfig,
    calibration_method: str = "none",
) -> tuple[Any, np.ndarray]:
    base = RandomForestClassifier(
        n_estimators=rf_cfg.n_estimators,
        max_depth=rf_cfg.max_depth,
        min_samples_split=rf_cfg.min_samples_split,
        min_samples_leaf=rf_cfg.min_samples_leaf,
        max_features=rf_cfg.max_features,
        class_weight=rf_cfg.class_weight,
        random_state=rf_cfg.random_state,
        n_jobs=rf_cfg.n_jobs,
    )
    if calibration_method in {"sigmoid", "isotonic"} and len(y_train) >= 60:
        clf: Any = CalibratedClassifierCV(base, method=calibration_method, cv=3)
    else:
        clf = base
    clf.fit(X_train, y_train)
    probs = clf.predict_proba(X_val)[:, 1]
    return clf, probs


def select_best_rf_hyperparameters(
    dev_records: list[dict[str, Any]],
    feature_groups: list[str],
    feature_cfg: FeatureConfig,
    base_rf_cfg: RandomForestConfig,
    n_splits: int = 3,
    random_state: int = 42,
) -> tuple[RandomForestConfig, list[dict[str, Any]]]:
    """Perform inner repository-grouped CV search for Random Forest hyperparameters."""
    candidates = [
        base_rf_cfg.model_copy(update={"n_estimators": 250, "max_depth": 16, "min_samples_leaf": 2, "max_features": "sqrt", "class_weight": "balanced_subsample"}),
        base_rf_cfg.model_copy(update={"n_estimators": 350, "max_depth": 24, "min_samples_leaf": 1, "max_features": "sqrt", "class_weight": "balanced_subsample"}),
        base_rf_cfg.model_copy(update={"n_estimators": 300, "max_depth": None, "min_samples_leaf": 2, "max_features": "log2", "class_weight": "balanced"}),
        base_rf_cfg.model_copy(update={"n_estimators": 300, "max_depth": 12, "min_samples_leaf": 4, "max_features": "sqrt", "class_weight": "balanced"}),
    ]
    folds = make_grouped_cv_splits(dev_records, n_splits=n_splits, random_state=random_state)
    y_all = np.array([int(r["label"]) for r in dev_records], dtype=int)

    # Pre-fit fold feature pipelines once across candidates
    fold_matrices: list[tuple[Any, np.ndarray, Any, np.ndarray]] = []
    for tr_idx, va_idx in folds:
        tr_recs = [dev_records[i] for i in tr_idx]
        va_recs = [dev_records[i] for i in va_idx]
        pipe = FeaturePipeline(groups=feature_groups, feature_config=feature_cfg)
        X_tr, _ = pipe.fit_transform(tr_recs)
        X_va, _ = pipe.transform(va_recs)
        fold_matrices.append((X_tr, y_all[tr_idx], X_va, y_all[va_idx]))

    search_log: list[dict[str, Any]] = []
    best_cfg = candidates[0]
    best_ap = -1.0

    for idx_c, cand in enumerate(candidates):
        oof_y: list[np.ndarray] = []
        oof_p: list[np.ndarray] = []
        for X_tr, y_tr, X_va, y_va in fold_matrices:
            _, probs = _fit_and_predict_rf(X_tr, y_tr, X_va, cand, calibration_method="none")
            oof_y.append(y_va)
            oof_p.append(probs)
        y_cat = np.concatenate(oof_y)
        p_cat = np.concatenate(oof_p)
        ap = float(average_precision_score(y_cat, p_cat)) if len(np.unique(y_cat)) >= 2 else 0.0
        brier = float(brier_score_loss(y_cat, p_cat)) if len(np.unique(y_cat)) >= 2 else 1.0
        search_log.append(
            {
                "candidate_index": idx_c,
                "hyperparameters": cand.model_dump(),
                "inner_oof_pr_auc": round(ap, 4),
                "inner_oof_brier": round(brier, 4),
            }
        )
        if ap > best_ap:
            best_ap = ap
            best_cfg = cand

    return best_cfg, search_log


def train_random_forest_with_cv(
    dev_records: list[dict[str, Any]],
    dataset_version: str,
    dataset_sha256: str | None = None,
    experiment_code: str = "I",
    feature_groups: list[str] | None = None,
    config: AppConfig | None = None,
    tune_hyperparameters: bool = True,
    tune_calibration: bool = True,
) -> dict[str, Any]:
    """
    Train Random Forest strictly on `dev_records` using repository-grouped CV:
      1. Optional inner grouped-CV hyperparameter selection.
      2. Outer grouped-CV OOF probabilities (with FeaturePipeline fitted strictly per fold!).
      3. Optional calibration comparison ('none' vs 'sigmoid' vs 'isotonic') on OOF Brier score.
      4. Validation-based 3-way threshold calibration on OOF predictions.
      5. Final model + FeaturePipeline refitted on full `dev_records` for independent evaluation.
    """
    t0 = time.perf_counter()
    cfg = config or load_config()
    groups = list(feature_groups or EXPERIMENT_DEFINITIONS.get(experiment_code, cfg.features.enabled_groups))
    feat_cfg = cfg.features.model_copy(update={"enabled_groups": groups})
    if experiment_code in EXPERIMENT_DEFINITIONS:
        feat_cfg = feat_cfg.model_copy(update={"experiment_code": experiment_code})

    rf_cfg = cfg.random_forest
    hpo_log: list[dict[str, Any]] = []
    if tune_hyperparameters and len({r["repository_id"] for r in dev_records}) >= 6:
        rf_cfg, hpo_log = select_best_rf_hyperparameters(
            dev_records=dev_records,
            feature_groups=groups,
            feature_cfg=feat_cfg,
            base_rf_cfg=cfg.random_forest,
            n_splits=cfg.validation.inner_folds,
            random_state=cfg.validation.random_state,
        )

    outer_folds = make_grouped_cv_splits(
        dev_records,
        n_splits=cfg.validation.outer_folds,
        random_state=cfg.validation.random_state,
    )
    y_dev = np.array([int(r["label"]) for r in dev_records], dtype=int)
    dev_repos = [str(r["repository_id"]) for r in dev_records]

    # Compare calibration modes strictly on outer CV OOF predictions
    cal_modes = ["none", "sigmoid", "isotonic"] if tune_calibration else [cfg.thresholds.calibration_method]
    oof_probs_by_mode: dict[str, np.ndarray] = {m: np.zeros(len(dev_records), dtype=float) for m in cal_modes}

    for tr_idx, va_idx in outer_folds:
        tr_recs = [dev_records[i] for i in tr_idx]
        va_recs = [dev_records[i] for i in va_idx]
        pipe = FeaturePipeline(groups=groups, feature_config=feat_cfg)
        X_tr, _ = pipe.fit_transform(tr_recs)
        X_va, _ = pipe.transform(va_recs)
        for m in cal_modes:
            _, probs = _fit_and_predict_rf(X_tr, y_dev[tr_idx], X_va, rf_cfg, calibration_method=m)
            oof_probs_by_mode[m][va_idx] = probs

    chosen_cal = "none"
    best_brier = float("inf")
    for m, probs in oof_probs_by_mode.items():
        b = float(brier_score_loss(y_dev, probs)) if len(np.unique(y_dev)) >= 2 else float(np.mean((probs - y_dev) ** 2))
        if b < best_brier:
            best_brier = b
            chosen_cal = m

    oof_probs = oof_probs_by_mode[chosen_cal]
    thr_res = calibrate_three_way_thresholds(
        y_true=y_dev,
        y_prob=oof_probs,
        target_confident_error=cfg.thresholds.target_confident_error,
    )

    cv_metrics = compute_classification_metrics(
        y_true=y_dev,
        y_prob=oof_probs,
        threshold_low=thr_res.threshold_low,
        threshold_center=thr_res.threshold_center,
        threshold_high=thr_res.threshold_high,
        repository_ids=dev_repos,
    )
    cv_metrics["oof_probabilities_count"] = len(oof_probs)
    cv_metrics["calibration_method_selected"] = chosen_cal
    cv_metrics["hpo_candidates"] = hpo_log

    # Refit final FeaturePipeline + Random Forest exclusively on full dev_records
    final_pipeline = FeaturePipeline(groups=groups, feature_config=feat_cfg)
    X_dev, _ = final_pipeline.fit_transform(dev_records)
    final_estimator, _ = _fit_and_predict_rf(
        X_dev, y_dev, X_dev, rf_cfg, calibration_method=chosen_cal
    )

    # Compute held-out-OOF-like permutation importance on dev subset as diagnostic (final test importances computed in evaluation)
    global_imp = compute_global_importances(
        estimator=final_estimator,
        X_eval=X_dev,
        y_eval=y_dev,
        feature_names=final_pipeline.get_feature_names(),
        group_map=final_pipeline.get_feature_group_map(),
        n_repeats=3,
        random_state=cfg.validation.random_state,
    )

    duration_s = round(time.perf_counter() - t0, 2)
    bundle = {
        "algorithm": "RandomForestClassifier",
        "experiment_code": experiment_code,
        "dataset_version": dataset_version,
        "dataset_sha256": dataset_sha256,
        "feature_groups": groups,
        "feature_schema": final_pipeline.schema_dict(),
        "feature_pipeline": final_pipeline,
        "estimator": final_estimator,
        "hyperparameters": rf_cfg.model_dump(),
        "calibration_method": chosen_cal,
        "threshold_low": thr_res.threshold_low,
        "threshold_center": thr_res.threshold_center,
        "threshold_high": thr_res.threshold_high,
        "cv_metrics": cv_metrics,
        "dev_global_importance": global_imp,
        "normalization_config": cfg.normalization.model_dump(),
        "dependency_versions": get_dependency_versions(),
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_s,
    }
    return bundle


def train_secondary_baseline(
    algorithm_name: str,
    dev_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
    feature_groups: list[str],
    feature_cfg: FeatureConfig,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train and evaluate a secondary baseline classifier (ExtraTrees, HistGradientBoosting, LogisticRegression)."""
    t0 = time.perf_counter()
    pipe = FeaturePipeline(groups=feature_groups, feature_config=feature_cfg)
    X_dev, _ = pipe.fit_transform(dev_records)
    X_test, _ = pipe.transform(test_records)
    y_dev = np.array([int(r["label"]) for r in dev_records], dtype=int)
    y_test = np.array([int(r["label"]) for r in test_records], dtype=int)

    if algorithm_name == "ExtraTreesClassifier":
        clf: Any = ExtraTreesClassifier(
            n_estimators=300, max_depth=24, min_samples_leaf=2, class_weight="balanced_subsample", random_state=random_state, n_jobs=-1
        )
        clf.fit(X_dev, y_dev)
        probs = clf.predict_proba(X_test)[:, 1]
    elif algorithm_name == "HistGradientBoostingClassifier":
        clf = HistGradientBoostingClassifier(max_iter=200, max_depth=8, learning_rate=0.06, random_state=random_state)
        clf.fit(X_dev.toarray(), y_dev)
        probs = clf.predict_proba(X_test.toarray())[:, 1]
    elif algorithm_name == "LogisticRegression":
        scaler = MaxAbsScaler()
        X_dev_s = scaler.fit_transform(X_dev)
        X_test_s = scaler.transform(X_test)
        clf = LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0, random_state=random_state)
        clf.fit(X_dev_s, y_dev)
        probs = clf.predict_proba(X_test_s)[:, 1]
    else:
        raise ValueError(f"Unsupported secondary baseline: {algorithm_name}")

    metrics = compute_classification_metrics(
        y_true=y_test,
        y_prob=probs,
        threshold_low=0.40,
        threshold_center=0.50,
        threshold_high=0.60,
        repository_ids=[str(r["repository_id"]) for r in test_records],
    )
    metrics["algorithm"] = algorithm_name
    metrics["duration_seconds"] = round(time.perf_counter() - t0, 2)
    return metrics
