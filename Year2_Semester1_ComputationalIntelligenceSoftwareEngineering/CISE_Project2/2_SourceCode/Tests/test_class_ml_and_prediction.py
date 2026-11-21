"""Tests for class-level ML models, precision threshold optimization, bundle thresholds, and file prediction."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from ml.cross_validation import (
    RepositoryGroupKFoldValidator,
    compute_bayesian_precision,
    compute_binary_classification_metrics,
    select_precision_optimal_threshold,
)
from ml.experiment_runner import build_estimator
from ml.model_manager import ModelManager
from ml.predictor import (
    BugPredictor,
    ModelCompatibilityError,
    NoClassesFoundError,
)
from ml.preprocessing import DataPreprocessor


@pytest.fixture
def synthetic_class_corpus():
    np.random.seed(7)
    n_repos = 10
    per_repo = 20
    n = n_repos * per_repo
    repo_ids = np.repeat(np.arange(1, n_repos + 1), per_repo)
    repo_names = [f"org/repo_{r}" for r in repo_ids]

    data = {col: np.random.randint(0, 8, size=n).astype(float) for col in CLASS_FEATURE_NAMES}
    data["class_loc"] = np.random.randint(15, 250, size=n).astype(float)
    data["total_cyclomatic_complexity"] = np.random.randint(2, 45, size=n).astype(float)
    data["max_nesting_depth"] = np.random.randint(0, 6, size=n).astype(float)
    X = pd.DataFrame(data)

    logits = -3.0 + 0.015 * X["class_loc"] + 0.08 * X["total_cyclomatic_complexity"]
    probs = 1.0 / (1.0 + np.exp(-logits))
    y = pd.Series((np.random.rand(n) < probs).astype(int), name="label")
    for r in range(1, n_repos + 1):
        idx = np.where(repo_ids == r)[0]
        y.iloc[idx[0]] = 1
        y.iloc[idx[1]] = 0

    meta = pd.DataFrame({
        "repository_id": repo_ids,
        "repository_name": repo_names,
    })
    return X, y, meta


def test_extended_model_families_instantiation():
    for algo in ["random_forest", "extra_trees", "hist_gb", "calibrated_rf", "logistic_regression", "decision_tree", "dummy"]:
        est, _ = build_estimator(algo, {"random_state": 42}, allow_extended=True)
        assert hasattr(est, "fit")


def test_precision_optimal_threshold_selection_tiers():
    y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 4)
    y_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.65, 0.55, 0.72, 0.80, 0.85, 0.90] * 4)

    res = select_precision_optimal_threshold(
        y_true, y_prob, min_precision_preferred=0.80, min_precision_acceptable=0.75, min_recall=0.50
    )
    assert res["selected_threshold"] >= 0.66
    assert res["inner_metrics"]["precision"] >= 0.80
    assert res["inner_metrics"]["recall"] >= 0.50

    m = compute_binary_classification_metrics(y_true, y_prob, threshold=res["selected_threshold"])
    assert m["precision"] >= 0.80
    assert 0.0 <= m["brier_score"] <= 1.0
    assert compute_bayesian_precision(0.80, 0.10, 0.05) < 0.80


def test_class_predictor_uses_stored_threshold_and_aggregates_file(synthetic_class_corpus, tmp_path):
    X, y, meta = synthetic_class_corpus

    # Fit on repos 1..8 cleanly
    train_mask = meta["repository_id"] <= 8
    preproc = DataPreprocessor(impute_missing=True, remove_constant=False).fit(X[train_mask])
    X_tr = preproc.transform(X[train_mask])

    est, _ = build_estimator("extra_trees", {"n_estimators": 30, "max_depth": 6, "random_state": 42}, allow_extended=True)
    est.fit(X_tr, y[train_mask])

    # Run GroupKFold check
    validator = RepositoryGroupKFoldValidator(n_splits=4, strict_repo_count=True)
    cv_res = validator.evaluate_model(
        model_factory=lambda: build_estimator("random_forest", {"n_estimators": 20, "max_depth": 5}, allow_extended=True)[0],
        X_train_raw=X[train_mask],
        y_train=y[train_mask],
        meta_train=meta[train_mask],
    )
    assert cv_res.n_splits == 4

    db = Database(tmp_path / "pred_test.db")
    repo_db = RepositoryDB(db)
    mgr = ModelManager(tmp_path / "models", db=repo_db)

    # Save with an explicit elevated threshold (0.78) to verify BugPredictor does NOT default to model.predict() 0.50
    bundle_path = mgr.save_model(
        model_name="class_test_et_v3",
        model=est,
        preprocessor=preproc,
        feature_names=preproc.feature_names_out_,
        parameters={"n_estimators": 30, "max_depth": 6},
        metrics={"precision": 0.81, "recall": 0.65, "f1": 0.72, "roc_auc": 0.85, "average_precision": 0.82},
        granularity="class",
        version="3.0.0",
        dataset_version="3.0.0",
        decision_threshold=0.78,
        threshold_selection_criterion="tier1_precision>=0.80",
    )
    assert bundle_path.exists()

    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_test_et_v3",
        models_dir=tmp_path / "models",
        db=repo_db,
        persist_history=True,
    )
    assert predictor.decision_threshold == pytest.approx(0.78)
    assert predictor.granularity == "class"

    # Mock a high-threshold check on synthetic metrics: if prob < 0.78, label must be 0 even if prob >= 0.50
    sample_metrics = {col: 10.0 for col in CLASS_FEATURE_NAMES}
    cp = predictor.predict_class_from_metrics(sample_metrics, class_name="ManualClass", qualified_class_name="Ns.ManualClass")
    assert cp.predicted_label == int(cp.defect_probability >= 0.78)

    # Full .cs file with 2 classes
    multi_cs = """namespace DemoApp
{
    public class SimpleDto
    {
        public string Name { get; set; } = "";
        public int Count => 1;
    }

    public class ComplexProcessor
    {
        public int Evaluate(int[] values, bool strict)
        {
            int sum = 0;
            foreach (var v in values)
            {
                if (v > 0 && strict)
                {
                    for (int k = 0; k < v; k++)
                    {
                        if (k % 2 == 0) sum += k;
                    }
                }
            }
            return sum;
        }
    }
}
"""
    fres = predictor.predict_csharp_file(code=multi_cs, file_name="Multi.cs")
    assert fres.classes_analyzed_count == 2
    assert len(fres.class_predictions) == 2
    assert fres.highest_class_risk_score == fres.max_defect_probability
    assert fres.classes_flagged_count == sum(1 for c in fres.class_predictions if c.predicted_label == 1)

    preds_in_db = repo_db.list_predictions(granularity="class")
    assert len(preds_in_db) >= 2
    assert preds_in_db[0]["decision_threshold"] == pytest.approx(0.78)
    assert preds_in_db[0]["dataset_version"] == "3.0.0"

    with pytest.raises(NoClassesFoundError):
        predictor.predict_csharp_file(code="   \n  ")


def test_legacy_method_model_rejected_for_class_file_prediction(tmp_path):
    X = pd.DataFrame({"loc": [10, 20, 30, 40], "cyclomatic_complexity": [1, 2, 4, 6]})
    y = pd.Series([0, 0, 1, 1])
    preproc = DataPreprocessor(impute_missing=True, remove_constant=False).fit(X)
    est, _ = build_estimator("random_forest", {"n_estimators": 10, "random_state": 42})
    est.fit(X, y)

    predictor = BugPredictor(
        model_bundle={
            "model_name": "legacy_method_rf",
            "granularity": "method",
            "model": est,
            "preprocessor": preproc,
            "feature_names": preproc.feature_names_out_,
            "parameters": {},
            "metrics": {},
        },
        persist_history=False,
    )
    with pytest.raises(ModelCompatibilityError, match="method"):
        predictor.predict_csharp_file(code="public class Foo { public void Bar() {} }")
