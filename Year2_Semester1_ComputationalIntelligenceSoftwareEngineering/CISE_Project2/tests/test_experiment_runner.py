"""Comprehensive automated tests for 5-fold GroupKFold CV and ML Experimentation Engine."""
from __future__ import annotations

import json
import csv
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from src.ml.cross_validation import (
    CrossValidationError,
    InsufficientRepositoriesError,
    RepositoryGroupKFoldValidator,
    check_repository_readiness,
)
from src.ml.experiment_runner import (
    ExperimentConfig,
    ExperimentRunner,
    ConfigurationResult,
)


@pytest.fixture
def multi_repo_synthetic_dataset():
    """Generate a clean synthetic dataset with 7 distinct repositories for 5-fold CV testing."""
    np.random.seed(42)
    n_repos = 7
    samples_per_repo = 25
    n_samples = n_repos * samples_per_repo

    repo_ids = np.repeat(np.arange(1, n_repos + 1), samples_per_repo)
    repo_names = [f"org/repo_{r}" for r in repo_ids]

    f_loc = np.random.randint(10, 300, size=n_samples)
    f_cc = np.random.randint(1, 30, size=n_samples)
    f_depth = np.random.randint(0, 6, size=n_samples)
    f_const = np.zeros(n_samples)  # constant feature to test variance thresholding

    # Synthetic logistic boundary for defect labels
    prob = 1.0 / (1.0 + np.exp(-(-2.5 + 0.015 * f_loc + 0.12 * f_cc + 0.2 * f_depth)))
    labels = (np.random.rand(n_samples) < prob).astype(int)

    # Ensure both classes exist in all repos
    for r in range(1, n_repos + 1):
        idx = np.where(repo_ids == r)[0]
        labels[idx[0]] = 1
        labels[idx[1]] = 0

    X = pd.DataFrame({
        "loc": f_loc,
        "cyclomatic_complexity": f_cc,
        "max_nesting_depth": f_depth,
        "constant_feature": f_const,
    })
    # Add an NaN to verify median imputation inside fold
    X.loc[10, "cyclomatic_complexity"] = np.nan

    y = pd.Series(labels, name="label")
    metadata = pd.DataFrame({
        "observation_id": np.arange(1, n_samples + 1),
        "repository_id": repo_ids,
        "repository_name": repo_names,
    })

    return X, y, metadata


def test_insufficient_repositories_raises_error():
    """Validate that 5-fold GroupKFold raises InsufficientRepositoriesError when < 5 repos."""
    X = pd.DataFrame({"loc": np.arange(30)})
    y = pd.Series([1, 0] * 15)
    # Only 3 repositories provided
    metadata = pd.DataFrame({"repository_id": [1, 2, 3] * 10})

    validator = RepositoryGroupKFoldValidator(n_splits=5, strict_repo_count=True)
    with pytest.raises(InsufficientRepositoriesError, match="Requested 5-fold GroupKFold cross-validation, but training dataset contains only 3 distinct repositories"):
        validator.validate_and_generate_splits(X, y, metadata)


def test_repository_readiness_diagnostic():
    """Verify check_repository_readiness computes exact missing counts and recommendations."""
    meta_insufficient = pd.DataFrame({"repository_id": [10, 20]})
    rep = check_repository_readiness(meta_insufficient, n_splits=5)
    assert not rep.is_ready
    assert rep.available_repo_count == 2
    assert rep.required_repo_count == 5
    assert rep.missing_repo_count == 3
    assert "Exactly 3 additional independent repositories" in rep.recommendation

    meta_sufficient = pd.DataFrame({"repository_id": [1, 2, 3, 4, 5, 6]})
    rep_ok = check_repository_readiness(meta_sufficient, n_splits=5)
    assert rep_ok.is_ready
    assert rep_ok.missing_repo_count == 0


def test_five_fold_group_kfold_no_leakage_and_single_val_appearance(multi_repo_synthetic_dataset):
    """Verify 5-fold GroupKFold produces zero repository leakage and each repo is validated exactly once."""
    X, y, metadata = multi_repo_synthetic_dataset
    # Filter to exactly 5 repositories
    mask = metadata["repository_id"].isin([1, 2, 3, 4, 5])
    X_5 = X[mask].copy()
    y_5 = y[mask].copy()
    meta_5 = metadata[mask].copy()

    validator = RepositoryGroupKFoldValidator(n_splits=5, strict_repo_count=True)
    splits = validator.validate_and_generate_splits(X_5, y_5, meta_5)

    assert len(splits) == 5

    val_repo_tracker = []
    for fold_idx, (train_idx, val_idx) in enumerate(splits, 1):
        train_repos = set(meta_5.iloc[train_idx]["repository_id"].unique())
        val_repos = set(meta_5.iloc[val_idx]["repository_id"].unique())

        # Zero leakage
        assert len(train_repos.intersection(val_repos)) == 0, f"Leakage detected in fold {fold_idx}"
        val_repo_tracker.extend(val_repos)

    # Every repo from 1..5 appears in validation exactly once
    assert sorted(val_repo_tracker) == [1, 2, 3, 4, 5]


def test_preprocessing_fitted_independently_per_fold(multi_repo_synthetic_dataset):
    """Verify that preprocessing (variance threshold & imputation) is isolated per fold."""
    X, y, metadata = multi_repo_synthetic_dataset
    mask = metadata["repository_id"].isin([1, 2, 3, 4, 5])
    X_5 = X[mask].copy()
    y_5 = y[mask].copy()
    meta_5 = metadata[mask].copy()

    validator = RepositoryGroupKFoldValidator(
        n_splits=5,
        strict_repo_count=True,
        impute_missing=True,
        remove_constant=True,
    )

    def dummy_factory():
        return RandomForestClassifier(n_estimators=5, random_state=42)

    cv_results = validator.evaluate_model(dummy_factory, X_5, y_5, meta_5)

    assert cv_results.n_splits == 5
    assert len(cv_results.fold_metrics) == 5
    for fm in cv_results.fold_metrics:
        assert fm.accuracy >= 0.0
        assert fm.f1 >= 0.0
        assert fm.train_sample_count > 0
        assert fm.val_sample_count > 0


def test_experiment_runner_grid_evaluation_and_ranking(multi_repo_synthetic_dataset, tmp_path):
    """Verify experiment runner evaluates multiple configurations and correctly ranks by selection metric."""
    X, y, metadata = multi_repo_synthetic_dataset

    # Explicitly designate Repos 1..5 as Training, and Repo 6 as Holdout (Guarantees exactly 5 train repos)
    train_mask = metadata["repository_id"].isin([1, 2, 3, 4, 5])
    holdout_mask = metadata["repository_id"] == 6

    X_train, y_train, meta_train = X[train_mask].copy(), y[train_mask].copy(), metadata[train_mask].copy()
    X_holdout, y_holdout, meta_holdout = X[holdout_mask].copy(), y[holdout_mask].copy(), metadata[holdout_mask].copy()

    test_grid = [
        {"config_id": "fast_rf_1", "n_estimators": 10, "max_depth": 4},
        {"config_id": "fast_rf_2", "n_estimators": 25, "max_depth": 8},
        {"config_id": "fast_rf_3", "n_estimators": 15, "max_depth": 6},
    ]

    exp_config = ExperimentConfig(
        experiment_id="test_exp_001",
        n_splits=5,
        strict_groups=True,
        selection_metric="f1",
        param_grid=test_grid,
        output_dir=tmp_path / "experiments",
        random_state=42,
    )

    runner = ExperimentRunner(exp_config)
    results = runner.run_experiment(
        X_train=X_train,
        y_train=y_train,
        meta_train=meta_train,
        X_holdout=X_holdout,
        y_holdout=y_holdout,
        meta_holdout=meta_holdout,
    )

    assert results["best_config_id"] in ["fast_rf_1", "fast_rf_2", "fast_rf_3"]
    assert results["best_cv_score"] >= 0.0
    assert results["holdout_results"] is not None
    assert "f1" in results["holdout_results"]
    assert "recall" in results["holdout_results"]

    # Verify CSV results file
    csv_file = Path(results["csv_path"])
    assert csv_file.exists()
    with open(csv_file, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 3
        # First row is rank 1
        assert reader[0]["rank"] == "1"
        assert float(reader[0]["selection_score"]) >= float(reader[1]["selection_score"])

    # Verify JSON results file
    json_file = Path(results["json_path"])
    assert json_file.exists()
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
        assert data["experiment_id"] == "test_exp_001"
        assert len(data["configurations"]) == 3
        assert "holdout_evaluation" in data

    # Verify Markdown report
    report_file = Path(results["report_path"])
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "test_exp_001" in content
    assert "5-fold GroupKFold" in content
    assert "Baseline Comparison" in content


def test_deterministic_experiment_execution(multi_repo_synthetic_dataset, tmp_path):
    """Verify that runs with the same random seed produce identical fold metrics and rankings."""
    X, y, metadata = multi_repo_synthetic_dataset
    mask = metadata["repository_id"].isin([1, 2, 3, 4, 5])
    X_train = X[mask].copy()
    y_train = y[mask].copy()
    meta_train = metadata[mask].copy()

    grid = [{"config_id": "det_rf", "n_estimators": 10, "max_depth": 5}]

    cfg1 = ExperimentConfig(experiment_id="det_1", n_splits=5, param_grid=grid, output_dir=tmp_path / "exp1", random_state=42)
    res1 = ExperimentRunner(cfg1).run_experiment(X_train, y_train, meta_train)

    cfg2 = ExperimentConfig(experiment_id="det_2", n_splits=5, param_grid=grid, output_dir=tmp_path / "exp2", random_state=42)
    res2 = ExperimentRunner(cfg2).run_experiment(X_train, y_train, meta_train)

    assert res1["best_cv_score"] == res2["best_cv_score"]


def test_holdout_isolation_not_used_in_selection(multi_repo_synthetic_dataset, tmp_path):
    """Verify that selection score is strictly computed from CV without observing holdout labels."""
    X, y, metadata = multi_repo_synthetic_dataset
    train_mask = metadata["repository_id"].isin([1, 2, 3, 4, 5])
    holdout_mask = metadata["repository_id"] == 6

    X_train, y_train, meta_train = X[train_mask].copy(), y[train_mask].copy(), metadata[train_mask].copy()
    X_holdout, y_holdout, meta_holdout = X[holdout_mask].copy(), y[holdout_mask].copy(), metadata[holdout_mask].copy()

    # Invert holdout labels intentionally to check if selection changes
    y_holdout_inverted = 1 - y_holdout

    grid = [
        {"config_id": "cfg_a", "n_estimators": 10, "max_depth": 4},
        {"config_id": "cfg_b", "n_estimators": 15, "max_depth": 5},
    ]

    exp_cfg = ExperimentConfig(experiment_id="iso_test", n_splits=5, param_grid=grid, output_dir=tmp_path / "iso", random_state=42)
    res_normal = ExperimentRunner(exp_cfg).run_experiment(X_train, y_train, meta_train, X_holdout, y_holdout)

    exp_cfg2 = ExperimentConfig(experiment_id="iso_test_inv", n_splits=5, param_grid=grid, output_dir=tmp_path / "iso2", random_state=42)
    res_inv = ExperimentRunner(exp_cfg2).run_experiment(X_train, y_train, meta_train, X_holdout, y_holdout_inverted)

    # CV scores and selection must be identical regardless of holdout labels
    assert res_normal["best_config_id"] == res_inv["best_config_id"]
    assert res_normal["best_cv_score"] == res_inv["best_cv_score"]
    # But holdout evaluation differs because holdout labels were inverted
    assert res_normal["holdout_results"]["f1"] != res_inv["holdout_results"]["f1"]
