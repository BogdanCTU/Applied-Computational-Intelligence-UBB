"""Unit and integration tests for Phase 6 BugPredictor and real-time inference."""
import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.ml.preprocessing import DataPreprocessor, split_by_repository
from src.ml.trainer import ModelTrainer
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager
from src.ml.predictor import (
    BugPredictor,
    MethodPrediction,
    PredictorError,
    NoMethodsFoundError,
    ModelCompatibilityError,
)


@pytest.fixture
def trained_predictor_bundle(tmp_path):
    """Train a simple Random Forest model on synthetic data and return the model bundle and manager."""
    np.random.seed(42)
    n_samples = 40

    # Synthetic features matching 24 metrics
    feature_cols = [
        "loc", "logical_loc", "method_length", "parameter_count", "local_variable_count",
        "statement_count", "return_count", "cyclomatic_complexity", "max_nesting_depth",
        "boolean_operator_count", "logical_operator_count", "conditional_expression_count",
        "if_count", "switch_count", "loop_count", "try_catch_count", "throw_count",
        "break_continue_count", "method_call_count", "field_access_count", "property_access_count",
        "assignment_count", "object_creation_count", "is_static", "is_async", "is_generic"
    ]

    data = {col: np.random.randint(0, 10, size=n_samples) for col in feature_cols}
    # Correlate cyclomatic complexity and loc with bug label
    data["loc"] = np.random.randint(5, 100, size=n_samples)
    data["cyclomatic_complexity"] = np.random.randint(1, 20, size=n_samples)
    X = pd.DataFrame(data)

    prob = 1.0 / (1.0 + np.exp(-(-2.0 + 0.05 * data["loc"] + 0.2 * data["cyclomatic_complexity"])))
    labels = (np.random.rand(n_samples) < prob).astype(int)
    labels[0] = 1
    labels[1] = 0
    y = pd.Series(labels, name="label")

    meta = pd.DataFrame({
        "repository_id": np.repeat([1, 2], 20),
        "repository_name": ["repo1"] * 20 + ["repo2"] * 20,
    })

    X_train, X_test, y_train, y_test, meta_train, meta_test, split_sum = split_by_repository(
        X, y, meta, test_size=0.5, random_state=42
    )

    preproc = DataPreprocessor(impute_missing=True, remove_constant=False).fit(X_train)
    X_tr = preproc.transform(X_train)
    X_te = preproc.transform(X_test)

    trainer = ModelTrainer(n_estimators=15, max_depth=4, random_state=42)
    model, _, _, _ = trainer.train_with_cv(X_tr, y_train, meta_train, n_splits=2)

    evaluator = ModelEvaluator()
    eval_res = evaluator.evaluate(model, X_te, y_test)

    models_dir = tmp_path / "models"
    mgr = ModelManager(models_dir)
    mgr.save_model(
        model_name="test_rf_predictor",
        model=model,
        preprocessor=preproc,
        feature_names=preproc.feature_names_out_,
        parameters=trainer.params,
        metrics=eval_res,
        split_summary=split_sum,
    )

    bundle = mgr.load_model("test_rf_predictor")
    return bundle, models_dir


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_predictor.db"
    db = Database(db_file)
    return RepositoryDB(db)


def test_predictor_single_method(trained_predictor_bundle, test_db):
    bundle, _ = trained_predictor_bundle
    predictor = BugPredictor(
        model_bundle=bundle,
        model_id=1,
        db=test_db,
        low_threshold=0.30,
        medium_threshold=0.60,
        persist_history=True,
        persist_source_code=False,
    )

    csharp_code = """
    public int CalculateSum(int a, int b)
    {
        int result = a + b;
        if (result > 100)
        {
            return 100;
        }
        return result;
    }
    """

    predictions = predictor.predict_code(csharp_code)
    assert len(predictions) == 1
    p = predictions[0]

    assert p.method_name == "CalculateSum"
    assert p.predicted_label in (0, 1)
    assert 0.0 <= p.risk_score <= 1.0
    assert p.risk_category in ("Low risk", "Medium risk", "High risk")
    assert "cyclomatic_complexity" in p.metrics
    assert p.metrics["cyclomatic_complexity"] >= 2
    assert p.metrics["loc"] > 0
    assert p.source_code is None  # Privacy: source code not persisted by default

    # Verify history recorded in SQLite
    history = test_db.list_predictions()
    assert len(history) == 1
    assert history[0]["method_name"] == "CalculateSum"
    assert history[0]["source_code"] is None


def test_predictor_multi_method_file(trained_predictor_bundle, tmp_path):
    bundle, _ = trained_predictor_bundle
    predictor = BugPredictor(model_bundle=bundle, persist_history=False)

    csharp_file_content = """
    namespace MathLibrary
    {
        public class Calculator
        {
            public int Add(int x, int y) => x + y;

            public int Factorial(int n)
            {
                if (n <= 1) return 1;
                int res = 1;
                for (int i = 2; i <= n; i++)
                {
                    res *= i;
                }
                return res;
            }
        }
    }
    """
    file_path = tmp_path / "Calculator.cs"
    file_path.write_text(csharp_file_content, encoding="utf-8")

    predictions = predictor.predict_file(file_path)
    assert len(predictions) == 2

    names = {p.method_name for p in predictions}
    assert "Add" in names
    assert "Factorial" in names

    fact_pred = next(p for p in predictions if p.method_name == "Factorial")
    assert fact_pred.metrics["loop_count"] == 1
    assert fact_pred.metrics["if_count"] == 1
    assert fact_pred.class_name == "Calculator"


def test_predictor_empty_or_no_methods(trained_predictor_bundle):
    bundle, _ = trained_predictor_bundle
    predictor = BugPredictor(model_bundle=bundle, persist_history=False)

    # Empty code
    with pytest.raises(NoMethodsFoundError, match="empty or contains only whitespace"):
        predictor.predict_code("   \n\t  ")

    # Code without methods
    with pytest.raises(NoMethodsFoundError, match="No eligible C# methods"):
        predictor.predict_code("namespace Foo { public class Bar { int x = 10; } }")


def test_predictor_incompatible_bundle():
    with pytest.raises(ModelCompatibilityError, match="missing essential component"):
        BugPredictor(model_bundle={"model": None})

    with pytest.raises(ModelCompatibilityError, match="missing essential component"):
        BugPredictor(model_bundle={"model": "not_none", "preprocessor": None})


def test_predictor_from_model_identifier(trained_predictor_bundle, tmp_path):
    _, models_dir = trained_predictor_bundle

    predictor = BugPredictor.from_model_identifier(
        model_identifier="test_rf_predictor",
        models_dir=models_dir,
    )
    assert predictor.model_name == "test_rf_predictor"
    assert len(predictor.feature_names) > 0


def test_prediction_history_privacy_and_clear(trained_predictor_bundle, test_db):
    bundle, _ = trained_predictor_bundle

    # 1. With persist_source_code = True
    predictor_with_src = BugPredictor(
        model_bundle=bundle,
        db=test_db,
        persist_history=True,
        persist_source_code=True,
    )
    code = "public void TestMethod() { Console.WriteLine(1); }"
    predictor_with_src.predict_code(code)

    history = test_db.list_predictions()
    assert len(history) == 1
    assert history[0]["source_code"] is not None
    assert "Console.WriteLine" in history[0]["source_code"]

    # 2. Clear history
    deleted = test_db.clear_predictions()
    assert deleted == 1
    assert len(test_db.list_predictions()) == 0


def test_predictor_influential_metrics_attribution(trained_predictor_bundle):
    bundle, _ = trained_predictor_bundle
    predictor = BugPredictor(model_bundle=bundle, persist_history=False)

    # Method with extreme complexity and nesting
    complex_code = """
    public void OverlyComplexMethod(int x)
    {
        if (x > 1) {
            for (int i = 0; i < x; i++) {
                while (x > 0) {
                    try {
                        if (x % 2 == 0) throw new Exception();
                    } catch {
                        Console.WriteLine("error");
                    }
                }
            }
        }
    }
    """
    preds = predictor.predict_code(complex_code)
    assert len(preds) == 1
    p = preds[0]
    # Check that influential metrics were flagged
    assert len(p.influential_metrics) > 0
    # Metrics like max_nesting_depth or loop_count or try_catch_count or throw_count should be identified
    features_flagged = {m["feature"] for m in p.influential_metrics}
    assert any(f in features_flagged for f in ["max_nesting_depth", "loop_count", "try_catch_count", "throw_count", "if_count"])

