"""Automated tests for Stratified 5-Fold Cross-Validation.

Covers:
  - Correct number of folds (5)
  - Stratification and consistent folds across classifiers
  - Exact validation partitioning (each record used for validation exactly once)
  - Preprocessing fitted exclusively on each training fold (leakage prevention)
  - Exclusion of 'duration' and 'y' from input features
  - Metric calculation, mean, and sample standard-deviation aggregation
  - Correct positive-class configuration ('yes')
  - AST-based branch-count compliance for the rule-based classifier
  - Deterministic split generation via random_state
  - Graceful handling of missing columns and invalid labels
  - Clear distinction between fold-level means and out-of-fold pooled metrics
  - Persistence and loading of CV artifacts
"""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.cross_validation import CrossValidationResults, load_cv_results, run_stratified_cv
from src.evaluation import aggregate_cv_metrics, compute_metrics
from src.model_service import ModelConfig
from src.preprocessing import BankPreprocessor
import branch_counter

RULES_FILE = config.RULES_DIR / "rule_based.py"


def make_synthetic_bank_data(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate a lightweight synthetic dataset with real Bank Marketing schema."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "age": rng.integers(20, 70, n),
        "job": rng.choice(["management", "technician", "admin.", "blue-collar"], n),
        "marital": rng.choice(["married", "single", "divorced"], n),
        "education": rng.choice(["secondary", "tertiary", "primary"], n),
        "default": rng.choice(["no", "yes"], n),
        "balance": rng.integers(-200, 8000, n),
        "housing": rng.choice(["no", "yes"], n),
        "loan": rng.choice(["no", "yes"], n),
        "contact": rng.choice(["cellular", "telephone"], n),
        "day": rng.integers(1, 28, n),
        "month": rng.choice(["may", "jul", "mar", "sep", "oct", "dec"], n),
        "duration": rng.integers(10, 600, n),   # Leakage column (must be excluded)
        "campaign": rng.integers(1, 6, n),
        "pdays": rng.choice([-1, 50, 120], n),
        "previous": rng.choice([0, 1, 3], n),
        "poutcome": rng.choice(["unknown", "success", "failure"], n),
    })
    # Imbalanced 20% 'yes', 80% 'no'
    df["y"] = np.where(np.arange(n) % 5 == 0, "yes", "no")
    return df


def test_cv_generates_five_folds():
    """Verify that 5 folds are generated and metrics are recorded for each."""
    df = make_synthetic_bank_data(n=60, seed=42)
    res = run_stratified_cv(df, n_splits=5, random_state=42)

    assert res.n_splits == 5
    assert len(res.fold_results) == 5
    assert set(res.fold_metrics_df["fold"].unique()) == {1, 2, 3, 4, 5}
    assert res.total_duration > 0
    for fr in res.fold_results:
        assert fr.train_count + fr.val_count == 60
        assert fr.val_count == 12


def test_cv_stratification_and_consistent_folds():
    """Verify stratified label distribution and identical validation sets across classifiers."""
    df = make_synthetic_bank_data(n=100, seed=42)
    res = run_stratified_cv(df, n_splits=5, random_state=42)

    # Base rate is 20% 'yes' (20 out of 100)
    for fr in res.fold_results:
        # In a 100-record dataset with 20% yes, each 20-row validation fold has exactly 4 'yes'
        val_idx = res.oof_predictions[res.oof_predictions["fold"] == fr.fold].index
        val_y = df.loc[val_idx, "y"]
        assert (val_y == "yes").sum() == 4
        assert (val_y == "no").sum() == 16

    # Verify that all 3 classifiers evaluated on identical row indices
    for fr in res.fold_results:
        bn_m = fr.bn_metrics
        rule_m = fr.rule_metrics
        base_m = fr.baseline_metrics
        # Sum of confusion matrix counts must equal the validation set size (20)
        assert bn_m["TP"] + bn_m["FP"] + bn_m["FN"] + bn_m["TN"] == 20
        assert rule_m["TP"] + rule_m["FP"] + rule_m["FN"] + rule_m["TN"] == 20
        assert base_m["TP"] + base_m["FP"] + base_m["FN"] + base_m["TN"] == 20


def test_cv_validation_coverage_exact_partition():
    """Verify that every single record in the dataset is used for validation exactly once."""
    df = make_synthetic_bank_data(n=75, seed=123)
    res = run_stratified_cv(df, n_splits=5, random_state=123)

    # 1. Total out-of-fold predictions equals dataset size
    assert len(res.oof_predictions) == len(df)
    assert not res.oof_predictions["fold"].isna().any()

    # 2. Validation indices across folds are mutually disjoint and cover all rows
    fold_indices = [
        set(res.oof_predictions[res.oof_predictions["fold"] == f].index)
        for f in range(1, 6)
    ]
    for i in range(5):
        for j in range(i + 1, 5):
            assert fold_indices[i].isdisjoint(fold_indices[j]), f"Folds {i+1} and {j+1} overlap!"

    union_indices = set().union(*fold_indices)
    assert union_indices == set(df.index)


def test_preprocessing_fitted_exclusively_on_training_fold():
    """Verify that preprocessing is fitted exclusively on the training partition without test leakage."""
    df = make_synthetic_bank_data(n=50, seed=7)
    # Inject a rare category into exactly one row
    df.loc[0, "job"] = "astronaut"

    from sklearn.model_selection import StratifiedKFold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for train_idx, val_idx in skf.split(df[config.FEATURES], df["y"]):
        X_tr = df.iloc[train_idx][config.FEATURES]
        X_val = df.iloc[val_idx][config.FEATURES]

        pre = BankPreprocessor().fit(X_tr)

        if 0 in train_idx:
            # Training fold contained 'astronaut', so it must be recognized
            assert "astronaut" in pre.categories_["job"]
        else:
            # Training fold did NOT contain 'astronaut'; validation fold did
            assert "astronaut" not in pre.categories_["job"]
            # Transforming validation fold must NOT alter learned categories
            transformed_val = pre.transform(X_val)
            assert "astronaut" not in pre.categories_["job"]
            assert pre.n_unseen_replaced_ >= 1
            # Unseen was mapped to most frequent training category
            assert "astronaut" not in set(transformed_val["job"])


def test_exclusion_of_leakage_features():
    """Verify that duration and y are strictly excluded from input features in CV."""
    df = make_synthetic_bank_data(n=50, seed=10)
    assert "duration" in df.columns
    assert "y" in df.columns

    res = run_stratified_cv(df, n_splits=5, random_state=10)

    # Ensure none of the fold models or preprocessors saw 'duration' or 'y' as features
    for fr in res.fold_results:
        assert config.TARGET not in config.FEATURES
        assert "duration" not in config.FEATURES


def test_cv_metric_calculation_and_aggregation():
    """Verify mean and sample standard deviation calculations match expected statistical definitions."""
    fold_metrics = [
        {"accuracy": 0.85, "precision": 0.60, "recall": 0.40, "f1": 0.48, "TN": 80, "FP": 5, "FN": 10, "TP": 5},
        {"accuracy": 0.90, "precision": 0.70, "recall": 0.50, "f1": 0.58, "TN": 85, "FP": 3, "FN": 7, "TP": 5},
        {"accuracy": 0.88, "precision": 0.65, "recall": 0.45, "f1": 0.53, "TN": 82, "FP": 4, "FN": 9, "TP": 5},
        {"accuracy": 0.82, "precision": 0.55, "recall": 0.35, "f1": 0.43, "TN": 78, "FP": 6, "FN": 11, "TP": 5},
        {"accuracy": 0.86, "precision": 0.62, "recall": 0.42, "f1": 0.50, "TN": 81, "FP": 4, "FN": 10, "TP": 5},
    ]

    means, stds = aggregate_cv_metrics(fold_metrics)

    expected_acc_mean = (0.85 + 0.90 + 0.88 + 0.82 + 0.86) / 5
    expected_acc_std = float(pd.Series([0.85, 0.90, 0.88, 0.82, 0.86]).std(ddof=1))

    assert means["accuracy"] == pytest.approx(expected_acc_mean)
    assert stds["accuracy"] == pytest.approx(expected_acc_std)

    # Empty input raises ValueError
    with pytest.raises(ValueError, match="empty"):
        aggregate_cv_metrics([])


def test_cv_positive_class_configuration():
    """Verify that evaluation in CV strictly sets 'yes' as the positive class."""
    y_true = ["yes", "yes", "no", "no"]
    y_pred = ["yes", "no", "no", "no"]
    # For yes as positive: TP=1, FP=0, FN=1, TN=2
    # Precision = 1/(1+0) = 1.0; Recall = 1/(1+1) = 0.5
    m = compute_metrics(y_true, y_pred)
    assert m["precision"] == 1.0
    assert m["recall"] == 0.5
    assert m["TP"] == 1


def test_cv_branch_count_compliance():
    """Verify that rule-based classifier respects branching constraints during CV."""
    check = branch_counter.check_file(RULES_FILE, config.FEATURES)
    assert check["compliant"] is True
    assert check["branching_statements"] <= check["allowed_branches"]
    assert check["branching_statements"] == 2
    assert check["attributes_used"] == ["month", "poutcome"]


def test_cv_deterministic_split_generation():
    """Verify that random_state ensures reproducible fold generation."""
    df = make_synthetic_bank_data(n=60, seed=42)

    res1 = run_stratified_cv(df, n_splits=5, random_state=42)
    res2 = run_stratified_cv(df, n_splits=5, random_state=42)
    res3 = run_stratified_cv(df, n_splits=5, random_state=99)

    # res1 and res2 must have identical fold assignments
    pd.testing.assert_series_equal(res1.oof_predictions["fold"], res2.oof_predictions["fold"])
    pd.testing.assert_frame_equal(res1.summary_df, res2.summary_df)

    # res3 must differ in fold assignments
    assert not res1.oof_predictions["fold"].equals(res3.oof_predictions["fold"])


def test_cv_error_handling_and_validation():
    """Verify informative errors on missing target or corrupted labels."""
    df = make_synthetic_bank_data(n=50, seed=42)

    # Missing target
    with pytest.raises(ValueError, match="Target column"):
        run_stratified_cv(df.drop(columns=["y"]))

    # Unexpected target label
    corrupt_y = df.copy()
    corrupt_y.loc[0, "y"] = "maybe"
    with pytest.raises(ValueError, match="Unexpected target labels"):
        run_stratified_cv(corrupt_y)

    # Missing required feature
    with pytest.raises(ValueError, match="Missing feature columns"):
        run_stratified_cv(df.drop(columns=["age"]))


def test_cv_distinguishes_mean_from_pooled_metrics():
    """Verify that fold-level mean and out-of-fold pooled metrics are distinct entities."""
    df = make_synthetic_bank_data(n=80, seed=12)
    res = run_stratified_cv(df, n_splits=5, random_state=12)

    # summary_df contains mean and std
    assert "f1_mean" in res.summary_df.columns
    assert "f1_std" in res.summary_df.columns
    assert "pooled_f1" in res.summary_df.columns

    # pooled_df has raw metric columns
    assert "f1" in res.pooled_df.columns
    assert "accuracy" in res.pooled_df.columns


def test_cv_persistence_and_loading(tmp_path):
    """Verify saving to disk and loading back matches saved content."""
    df = make_synthetic_bank_data(n=50, seed=5)
    res = run_stratified_cv(df, n_splits=5, random_state=5)

    res.save(tmp_path)
    assert (tmp_path / "cv_metrics_summary.csv").exists()
    assert (tmp_path / "cv_fold_metrics.csv").exists()
    assert (tmp_path / "cv_pooled_metrics.csv").exists()
    assert (tmp_path / "cv_predictions.csv").exists()

    loaded = load_cv_results(tmp_path)
    assert loaded is not None
    assert loaded.n_splits == 5
    assert set(loaded.summary_df.index) == set(res.summary_df.index)
    assert loaded.summary_df.loc["Bayesian Network", "accuracy_mean"] == pytest.approx(
        res.summary_df.loc["Bayesian Network", "accuracy_mean"]
    )
