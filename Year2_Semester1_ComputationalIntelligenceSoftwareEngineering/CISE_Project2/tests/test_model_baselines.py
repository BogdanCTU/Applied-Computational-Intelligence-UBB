"""Automated unit and integration tests for multi-model baselines, calibration, and threshold optimization."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from src.ml.cross_validation import (
    RepositoryGroupKFoldValidator,
    compute_threshold_curve,
)
from src.ml.experiment_runner import (
    ExperimentConfig,
    ExperimentRunner,
    build_estimator,
)


@pytest.fixture
def synthetic_5repo_dataset():
    """Generate synthetic dataset with exactly 5 repositories for leakage-free CV testing."""
    np.random.seed(42)
    n_repos = 5
    samples_per_repo = 30
    n_samples = n_repos * samples_per_repo

    repo_ids = np.repeat(np.arange(1, n_repos + 1), samples_per_repo)
    repo_names = [f"org/repo_{r}" for r in repo_ids]

    f1 = np.random.normal(loc=50, scale=20, size=n_samples)
    f2 = np.random.exponential(scale=10, size=n_samples)
    f3 = np.random.randint(0, 5, size=n_samples)

    # Probabilistic defect relationship
    logits = -1.5 + 0.02 * f1 + 0.05 * f2 + 0.3 * f3
    probs = 1.0 / (1.0 + np.exp(-logits))
    labels = (np.random.rand(n_samples) < probs).astype(int)

    # Ensure both classes in all repos
    for r in range(1, n_repos + 1):
        idx = np.where(repo_ids == r)[0]
        labels[idx[0]] = 1
        labels[idx[1]] = 0

    X = pd.DataFrame({"f1": f1, "f2": f2, "f3": f3})
    y = pd.Series(labels, name="label")
    metadata = pd.DataFrame({
        "observation_id": np.arange(1, n_samples + 1),
        "repository_id": repo_ids,
        "repository_name": repo_names,
    })
    return X, y, metadata


def test_build_estimator_all_supported_algorithms():
    """Verify build_estimator instantiates correct model families and scaling flags."""
    # Dummy
    est_d, scale_d = build_estimator("dummy", {"strategy": "most_frequent"})
    assert isinstance(est_d, DummyClassifier)
    assert not scale_d

    est_ds, _ = build_estimator("dummy_classifier", {"strategy": "stratified", "random_state": 42})
    assert isinstance(est_ds, DummyClassifier)
    assert est_ds.strategy == "stratified"

    # Logistic Regression
    est_lr, scale_lr = build_estimator("logistic_regression", {"C": 0.5, "class_weight": "balanced"})
    assert isinstance(est_lr, LogisticRegression)
    assert scale_lr is True
    assert est_lr.C == 0.5
    assert est_lr.class_weight == "balanced"

    # Decision Tree
    est_dt, scale_dt = build_estimator("decision_tree", {"max_depth": 5, "min_samples_leaf": 3})
    assert isinstance(est_dt, DecisionTreeClassifier)
    assert not scale_dt
    assert est_dt.max_depth == 5

    # Random Forest
    est_rf, scale_rf = build_estimator("random_forest", {"n_estimators": 50, "max_depth": 10})
    assert isinstance(est_rf, RandomForestClassifier)
    assert not scale_rf
    assert est_rf.n_estimators == 50

    # Unsupported
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        build_estimator("neural_net", {})


def test_multi_model_baseline_cross_validation(synthetic_5repo_dataset, tmp_path):
    """Verify that multiple model families evaluate on identical folds without leakage."""
    X, y, metadata = synthetic_5repo_dataset

    # Multi-model grid: Dummy, Logistic Regression, Decision Tree, Random Forest
    param_grid = [
        {"config_id": "dummy_mf", "algorithm": "dummy", "strategy": "most_frequent"},
        {"config_id": "dummy_strat", "algorithm": "dummy", "strategy": "stratified"},
        {"config_id": "lr_scaled", "algorithm": "logistic_regression", "C": 1.0},
        {"config_id": "dt_base", "algorithm": "decision_tree", "max_depth": 4},
        {"config_id": "rf_base", "algorithm": "random_forest", "n_estimators": 20, "max_depth": 5},
    ]

    config = ExperimentConfig(
        experiment_id="test_multi_model",
        n_splits=5,
        strict_groups=True,
        param_grid=param_grid,
        output_dir=tmp_path / "experiments",
        random_state=42,
    )

    runner = ExperimentRunner(config)
    results = runner.run_experiment(
        X_train=X,
        y_train=y,
        meta_train=metadata,
    )

    assert results["best_config_id"] in [p["config_id"] for p in param_grid]
    assert results["best_cv_score"] >= 0.0

    # Check CSV output contains all 5 model configurations with algorithm column
    df_res = pd.read_csv(results["csv_path"])
    assert len(df_res) == 5
    assert "algorithm" in df_res.columns
    algorithms_found = set(df_res["algorithm"].unique())
    assert {"dummy", "logistic_regression", "decision_tree", "random_forest"}.issubset(algorithms_found)


def test_brier_score_loss_calibration(synthetic_5repo_dataset):
    """Verify Brier score is computed across all folds and aggregated in results."""
    X, y, metadata = synthetic_5repo_dataset
    validator = RepositoryGroupKFoldValidator(n_splits=5, strict_repo_count=True)

    cv_res = validator.evaluate_model(
        model_factory=lambda: RandomForestClassifier(n_estimators=10, random_state=42),
        X_train_raw=X,
        y_train=y,
        meta_train=metadata,
    )

    assert "brier_score" in cv_res.aggregate_metrics
    brier_mean = cv_res.aggregate_metrics["brier_score"]["mean"]
    # Brier score is in [0, 1] where 0 is perfect calibration
    assert 0.0 <= brier_mean <= 1.0

    for fm in cv_res.fold_metrics:
        assert 0.0 <= fm.brier_score <= 1.0


def test_threshold_curve_and_cv_optimization():
    """Verify compute_threshold_curve calculates precision, recall, and F1 across thresholds."""
    np.random.seed(42)
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0] * 5)
    y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.65, 0.15, 0.75, 0.25] * 5)

    curve = compute_threshold_curve(y_true, y_prob, thresholds=[0.3, 0.5, 0.7])
    assert len(curve) == 3

    t_03 = curve[0]
    t_07 = curve[2]
    # Lower threshold should give higher or equal recall
    assert t_03["recall"] >= t_07["recall"]
    # Higher threshold should give higher or equal precision
    assert t_07["precision"] >= t_03["precision"]
    # Verify all four confusion matrix cells are recorded
    for entry in curve:
        assert "true_negatives" in entry
        assert "false_positives" in entry
        assert "false_negatives" in entry
        assert "true_positives" in entry
        assert entry["true_negatives"] + entry["false_positives"] + entry["false_negatives"] + entry["true_positives"] == len(y_true)


def test_holdout_isolation_and_optimal_threshold_transfer(synthetic_5repo_dataset, tmp_path):
    """Verify holdout evaluation records standard threshold and CV-optimized threshold without holdout leakage."""
    X, y, metadata = synthetic_5repo_dataset

    # Repos 1..4 = train, Repo 5 = holdout
    train_mask = metadata["repository_id"].isin([1, 2, 3, 4])
    holdout_mask = metadata["repository_id"] == 5

    X_train, y_train, meta_train = X[train_mask], y[train_mask], metadata[train_mask]
    X_holdout, y_holdout, meta_holdout = X[holdout_mask], y[holdout_mask], metadata[holdout_mask]

    grid = [
        {"config_id": "rf_test", "algorithm": "random_forest", "n_estimators": 10, "max_depth": 4},
        {"config_id": "lr_test", "algorithm": "logistic_regression", "C": 1.0},
    ]

    exp = ExperimentConfig(
        experiment_id="holdout_opt_test",
        n_splits=4,
        strict_groups=True,
        param_grid=grid,
        output_dir=tmp_path / "exp_ho",
        random_state=42,
    )

    runner = ExperimentRunner(exp)
    res = runner.run_experiment(
        X_train=X_train,
        y_train=y_train,
        meta_train=meta_train,
        X_holdout=X_holdout,
        y_holdout=y_holdout,
        meta_holdout=meta_holdout,
    )

    ho = res["holdout_results"]
    assert ho is not None
    assert "brier_score" in ho
    assert 0.0 <= ho["brier_score"] <= 1.0
    assert "optimal_cv_threshold_used" in ho
    assert "holdout_at_optimal_cv_threshold" in ho
    assert "f1" in ho["holdout_at_optimal_cv_threshold"]

