"""Unit and integration tests for Phase 5 Machine Learning Pipeline."""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.ml.preprocessing import DataPreprocessor, split_by_repository, PreprocessingError
from src.ml.trainer import ModelTrainer
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager, ModelManagerError


@pytest.fixture
def synthetic_ml_dataset():
    """Create controlled multi-repository dataset with known ground truth and features."""
    np.random.seed(42)
    n_samples = 60

    # 3 distinct repositories: 1, 2, 3
    repo_ids = np.repeat([1, 2, 3], 20)
    repo_names = [f"org/repo_{r}" for r in repo_ids]

    # Features: some correlated with bug, some random, one constant
    f_loc = np.random.randint(10, 200, size=n_samples)
    f_cc = np.random.randint(1, 25, size=n_samples)
    f_nesting = np.random.randint(0, 5, size=n_samples)
    f_constant = np.zeros(n_samples) # constant feature to test VarianceThreshold

    # Target: higher complexity has higher chance of bug
    prob = 1.0 / (1.0 + np.exp(-(-2.0 + 0.02 * f_loc + 0.15 * f_cc)))
    labels = (np.random.rand(n_samples) < prob).astype(int)

    # Ensure both classes are present
    labels[0] = 1
    labels[1] = 0

    X = pd.DataFrame({
        "loc": f_loc,
        "cyclomatic_complexity": f_cc,
        "max_nesting_depth": f_nesting,
        "constant_feature": f_constant,
    })
    # Add occasional missing value to test imputation
    X.loc[5, "cyclomatic_complexity"] = np.nan

    y = pd.Series(labels, name="label")
    metadata = pd.DataFrame({
        "observation_id": np.arange(1, n_samples + 1),
        "repository_id": repo_ids,
        "repository_name": repo_names,
    })

    return X, y, metadata


def test_preprocessing_and_constant_removal(synthetic_ml_dataset):
    X, y, _ = synthetic_ml_dataset
    preprocessor = DataPreprocessor(impute_missing=True, remove_constant=True)

    X_trans = preprocessor.fit_transform(X)

    # Constant feature should be eliminated
    assert "constant_feature" not in X_trans.columns
    assert "loc" in X_trans.columns
    assert "cyclomatic_complexity" in X_trans.columns
    # Missing value at index 5 should be imputed
    assert not X_trans["cyclomatic_complexity"].isna().any()
    assert len(preprocessor.feature_names_out_) == 3


def test_repository_aware_split_no_leakage(synthetic_ml_dataset):
    X, y, metadata = synthetic_ml_dataset

    X_train, X_test, y_train, y_test, meta_train, meta_test, summary = split_by_repository(
        X, y, metadata, test_size=0.33, random_state=42
    )

    train_repos = set(meta_train["repository_id"].unique())
    test_repos = set(meta_test["repository_id"].unique())

    # ZERO overlap between repositories
    assert len(train_repos.intersection(test_repos)) == 0
    assert len(train_repos) >= 1
    assert len(test_repos) >= 1
    assert summary["train_samples"] + summary["test_samples"] == len(X)


def test_insufficient_repositories_raises_error():
    X = pd.DataFrame({"loc": [10, 20, 30]})
    y = pd.Series([1, 0, 1])
    # Single repository
    meta = pd.DataFrame({"repository_id": [1, 1, 1]})

    with pytest.raises(PreprocessingError, match="requires at least 2 distinct repositories"):
        split_by_repository(X, y, meta)


def test_trainer_and_dummy_baseline(synthetic_ml_dataset):
    X, y, metadata = synthetic_ml_dataset
    X_train, X_test, y_train, y_test, meta_train, meta_test, _ = split_by_repository(
        X, y, metadata, test_size=0.33, random_state=42
    )

    preprocessor = DataPreprocessor().fit(X_train)
    X_train_proc = preprocessor.transform(X_train)

    trainer = ModelTrainer(n_estimators=20, max_depth=5, random_state=42)
    model, cv_summary, baseline_summary, duration = trainer.train_with_cv(
        X_train=X_train_proc,
        y_train=y_train,
        meta_train=meta_train,
        n_splits=2,
    )

    assert model is not None
    assert "f1" in cv_summary
    assert "accuracy" in cv_summary
    assert "f1" in baseline_summary
    assert duration >= 0.0


def test_model_evaluation_and_feature_importance(synthetic_ml_dataset):
    X, y, metadata = synthetic_ml_dataset
    X_train, X_test, y_train, y_test, meta_train, _, _ = split_by_repository(
        X, y, metadata, test_size=0.33, random_state=42
    )

    preprocessor = DataPreprocessor().fit(X_train)
    X_tr = preprocessor.transform(X_train)
    X_te = preprocessor.transform(X_test)

    trainer = ModelTrainer(n_estimators=20, max_depth=5, random_state=42)
    model, _, _, _ = trainer.train_with_cv(X_tr, y_train, meta_train, n_splits=2)

    evaluator = ModelEvaluator()
    eval_results = evaluator.evaluate(model, X_te, y_test)

    assert "accuracy" in eval_results
    assert "precision" in eval_results
    assert "recall" in eval_results
    assert "f1" in eval_results
    assert "confusion_matrix" in eval_results
    assert len(eval_results["mdi_feature_importances"]) > 0

    # Test visualization figures
    cm_fig = evaluator.create_confusion_matrix_figure(eval_results["confusion_matrix"])
    assert cm_fig is not None

    roc_fig = evaluator.create_roc_curve_figure(model, X_te, y_test)
    assert roc_fig is not None

    pr_fig = evaluator.create_pr_curve_figure(model, X_te, y_test)
    assert pr_fig is not None


def test_model_manager_save_reload_and_schema_validation(synthetic_ml_dataset, tmp_path):
    X, y, metadata = synthetic_ml_dataset
    X_train, X_test, y_train, y_test, meta_train, meta_test, split_sum = split_by_repository(
        X, y, metadata, test_size=0.33, random_state=42
    )

    preprocessor = DataPreprocessor().fit(X_train)
    X_tr = preprocessor.transform(X_train)
    X_te = preprocessor.transform(X_test)

    trainer = ModelTrainer(n_estimators=10, random_state=42)
    model, cv_sum, _, _ = trainer.train_with_cv(X_tr, y_train, meta_train, n_splits=2)

    evaluator = ModelEvaluator()
    eval_results = evaluator.evaluate(model, X_te, y_test)

    models_dir = tmp_path / "models"
    mgr = ModelManager(models_dir)

    # Save
    saved_path = mgr.save_model(
        model_name="test_rf_v1",
        model=model,
        preprocessor=preprocessor,
        feature_names=preprocessor.feature_names_out_,
        parameters=trainer.params,
        metrics=eval_results,
        split_summary=split_sum,
    )
    assert saved_path.exists()

    # Overwrite protection
    with pytest.raises(ModelManagerError, match="already exists"):
        mgr.save_model(
            model_name="test_rf_v1",
            model=model,
            preprocessor=preprocessor,
            feature_names=preprocessor.feature_names_out_,
            parameters=trainer.params,
            metrics=eval_results,
            overwrite=False,
        )

    # Reload
    bundle = mgr.load_model("test_rf_v1")
    reloaded_model = bundle["model"]
    reloaded_preprocessor = bundle["preprocessor"]

    # End-to-end inference on raw unseen data through reloaded preprocessor
    raw_unseen = X_test.iloc[:2].copy()
    proc_unseen = reloaded_preprocessor.transform(raw_unseen)
    preds = reloaded_model.predict(proc_unseen)
    assert len(preds) == 2
    assert set(preds).issubset({0, 1})
