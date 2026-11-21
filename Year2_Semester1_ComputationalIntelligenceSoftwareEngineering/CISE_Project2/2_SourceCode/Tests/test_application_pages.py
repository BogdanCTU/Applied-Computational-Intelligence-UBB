"""Tests for application pages, unified model registry discovery, and input parsing."""
from __future__ import annotations

import pandas as pd
import pytest

from application.pages.bug_prediction import _highlight_class_rows
from application.pages.repository_collection import parse_github_url
from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from ml.experiment_runner import build_estimator
from ml.model_manager import ModelManager
from ml.preprocessing import DataPreprocessor


def test_parse_github_url_variants():
    assert parse_github_url("https://github.com/Humanizr/Humanizer.git") == ("Humanizr", "Humanizer")
    assert parse_github_url("App-vNext/Polly") == ("App-vNext", "Polly")
    with pytest.raises(ValueError):
        parse_github_url("invalid-single-token")


def test_highlight_class_rows_styling():
    flagged_row = pd.Series({"Predicted Classification": "Defect-Prone (1)", "Risk Category": "High risk"})
    clean_row = pd.Series({"Predicted Classification": "Candidate-Clean (0)", "Risk Category": "Low risk"})
    styles_flagged = _highlight_class_rows(flagged_row)
    styles_clean = _highlight_class_rows(clean_row)
    assert all("rgba" in s for s in styles_flagged)
    assert all(s == "" for s in styles_clean)


def test_unified_model_registry_prioritizes_class_champion(tmp_path):
    db = Database(tmp_path / "ui_reg.db")
    repo_db = RepositoryDB(db)
    mgr = ModelManager(tmp_path / "models", db=repo_db)

    X_m = pd.DataFrame({"loc": [5, 25, 45, 65], "cyclomatic_complexity": [1, 3, 7, 10]})
    y = pd.Series([0, 0, 1, 1])
    prep_m = DataPreprocessor(remove_constant=False).fit(X_m)
    est_m, _ = build_estimator("random_forest", {"n_estimators": 5, "random_state": 42})
    est_m.fit(X_m, y)
    mgr.save_model(
        model_name="rf_csharp_empirical_model",
        model=est_m,
        preprocessor=prep_m,
        feature_names=prep_m.feature_names_out_,
        parameters={},
        metrics={"f1": 0.70},
        granularity="method",
    )

    X_c = pd.DataFrame({f: [1.0, 2.0, 8.0, 12.0] for f in CLASS_FEATURE_NAMES})
    prep_c = DataPreprocessor(remove_constant=False).fit(X_c)
    est_c, _ = build_estimator("extra_trees", {"n_estimators": 5, "random_state": 42}, allow_extended=True)
    est_c.fit(X_c, y)
    mgr.save_model(
        model_name="class_precision_champion_v3",
        model=est_c,
        preprocessor=prep_c,
        feature_names=prep_c.feature_names_out_,
        parameters={},
        metrics={"precision": 0.82, "f1": 0.76},
        granularity="class",
        dataset_version="3.0.0",
        decision_threshold=0.68,
    )

    listed = mgr.list_saved_models()
    assert len(listed) == 2
    assert listed[0]["name"] == "class_precision_champion_v3"
    assert listed[0]["granularity"] == "class"
    assert listed[0]["decision_threshold"] == pytest.approx(0.68)


def test_all_streamlit_page_modules_import_cleanly():
    import app
    from application.pages import (
        bug_analysis,
        bug_prediction,
        dashboard,
        dataset_management,
        model_evaluation,
        model_training,
        repository_collection,
        settings,
    )
    assert callable(app.main)
    assert callable(dashboard.render_dashboard)
    assert callable(repository_collection.render_repository_collection)
    assert callable(bug_analysis.render_bug_analysis)
    assert callable(dataset_management.render_dataset_management)
    assert callable(model_training.render_model_training)
    assert callable(model_evaluation.render_model_evaluation)
    assert callable(bug_prediction.render_bug_prediction)
    assert callable(settings.render_settings)
