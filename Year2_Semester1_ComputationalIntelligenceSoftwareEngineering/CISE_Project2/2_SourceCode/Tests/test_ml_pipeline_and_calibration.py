"""Tests for Random Forest training, grouped CV isolation, threshold calibration, and persistence."""

from __future__ import annotations

import numpy as np

from bug_detector.config import AppConfig
from bug_detector.ml import (
    apply_three_way_decision,
    build_repository_splits,
    calibrate_three_way_thresholds,
    load_model_bundle,
    save_model_bundle,
    train_random_forest_with_cv,
    verify_zero_leakage,
)
from conftest import make_synthetic_records


def test_three_way_threshold_calibration_and_decisions() -> None:
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 4)
    p = np.array([0.05, 0.12, 0.20, 0.45, 0.49, 0.51, 0.56, 0.80, 0.90, 0.96] * 4)
    res = calibrate_three_way_thresholds(y, p, target_confident_error=0.20)
    assert 0.0 < res.threshold_low < res.threshold_center < res.threshold_high < 1.0
    assert apply_three_way_decision(0.05, res.threshold_low, res.threshold_high)[0] == "CLEAN"
    assert apply_three_way_decision(0.95, res.threshold_low, res.threshold_high)[0] == "BUG"
    assert apply_three_way_decision(res.threshold_center, res.threshold_low, res.threshold_high)[0] == "UNCERTAIN"


def test_random_forest_training_and_bundle_reload_parity(temp_config: AppConfig) -> None:
    records = make_synthetic_records(n_repos=12, per_repo=6)
    splits = build_repository_splits(records, independent_test_fraction=0.25, random_state=42)
    verify_zero_leakage(splits["dev"], splits["independent_test"], splits["hard_negative_test"])

    temp_config.random_forest.n_estimators = 40
    temp_config.validation.outer_folds = 3
    temp_config.features.tfidf_min_df = 1

    bundle = train_random_forest_with_cv(
        dev_records=splits["dev"],
        dataset_version="v5-unit",
        experiment_code="I",
        config=temp_config,
        tune_hyperparameters=False,
        tune_calibration=False,
    )
    bundle["model_version"] = "rf_unit_v5"
    bundle["dataset_version"] = "v5-unit"

    # Register dataset_version first to satisfy FK constraint
    from bug_detector.db import BugDetectorRepository, DatabaseManager

    repo = BugDetectorRepository(DatabaseManager(temp_config.db_path))
    repo.register_dataset_version("v5-unit", "unit test dataset", {"valid_records": len(records)})

    art_path, man_path = save_model_bundle("rf_unit_v5", bundle, config=temp_config, activate=True)
    assert art_path.exists()
    assert man_path.exists()

    reloaded = load_model_bundle("rf_unit_v5", config=temp_config)
    X_test, _ = reloaded["feature_pipeline"].transform(splits["independent_test"])
    probs_reloaded = reloaded["estimator"].predict_proba(X_test)[:, 1]
    X_orig, _ = bundle["feature_pipeline"].transform(splits["independent_test"])
    probs_orig = bundle["estimator"].predict_proba(X_orig)[:, 1]
    assert np.allclose(probs_reloaded, probs_orig)
