"""Tests for global permutation importance, TreeInterpreter local evidence, and ranking."""

from __future__ import annotations

import numpy as np

from bug_detector.config import AppConfig
from bug_detector.explainability import (
    compute_global_importances,
    compute_tree_path_contributions,
    rank_suspicious_methods,
)
from bug_detector.ml import build_repository_splits, train_random_forest_with_cv
from conftest import make_synthetic_records


def test_tree_path_decomposition_additive_and_global_importance(temp_config: AppConfig) -> None:
    records = make_synthetic_records(n_repos=10, per_repo=6)
    splits = build_repository_splits(records, independent_test_fraction=0.2, random_state=42)
    temp_config.random_forest.n_estimators = 30
    temp_config.validation.outer_folds = 3
    temp_config.features.tfidf_min_df = 1

    bundle = train_random_forest_with_cv(
        dev_records=splits["dev"],
        dataset_version="v5-exp",
        experiment_code="I",
        config=temp_config,
        tune_hyperparameters=False,
        tune_calibration=False,
    )
    pipe = bundle["feature_pipeline"]
    est = bundle["estimator"]
    X_test, _ = pipe.transform(splits["independent_test"])
    y_test = np.array([int(r["label"]) for r in splits["independent_test"]], dtype=int)

    # Check exact Saabas decomposition identity: bias + sum(contribs) == predict_proba(row)[1]
    ev = compute_tree_path_contributions(
        estimator=est,
        X_row=X_test[0],
        feature_names=pipe.get_feature_names(),
        group_map=pipe.get_feature_group_map(),
        top_k=5,
    )
    assert ev["method"] == "tree_path_saabas_decomposition"
    expected_prob = float(est.predict_proba(X_test[0])[0, 1])
    assert abs(ev["raw_forest_probability"] - expected_prob) < 1e-4
    group_sum = sum(ev["group_contributions"].values())
    assert abs((ev["base_rate_bias"] + group_sum) - expected_prob) < 1e-3

    g_imp = compute_global_importances(
        estimator=est,
        X_eval=X_test,
        y_eval=y_test,
        feature_names=pipe.get_feature_names(),
        group_map=pipe.get_feature_group_map(),
        n_repeats=2,
    )
    assert set(g_imp["group_importance"].keys()) == set(pipe.groups)
    assert len(g_imp["top_permutation_features"]) > 0


def test_suspicious_method_ranking_orders_descending() -> None:
    preds = [
        {"method_name": "Low", "probability": 0.12},
        {"method_name": "High", "probability": 0.91},
        {"method_name": "Mid", "probability": 0.55},
    ]
    rank_suspicious_methods(preds)
    ranks = {p["method_name"]: p["suspicious_rank"] for p in preds}
    assert ranks == {"High": 1, "Mid": 2, "Low": 3}
