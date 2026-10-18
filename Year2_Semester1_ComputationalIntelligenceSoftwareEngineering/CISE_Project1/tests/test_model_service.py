"""Tests for ModelService: training orchestration, single inference, configuration
invalidation, execution trace, and GUI compatibility.
"""

import pandas as pd
import numpy as np
import pytest

from src import config
from src.model_service import ModelConfig, ModelService, TrainedArtifacts
from src.preprocessing import BankPreprocessor, split_data


def make_dummy_data(n: int = 150, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "age": rng.integers(20, 70, n),
        "job": rng.choice(["management", "technician", "admin."], n),
        "marital": rng.choice(["married", "single"], n),
        "education": rng.choice(["secondary", "tertiary"], n),
        "default": rng.choice(["no", "yes"], n),
        "balance": rng.integers(0, 5000, n),
        "housing": rng.choice(["no", "yes"], n),
        "loan": rng.choice(["no", "yes"], n),
        "contact": rng.choice(["cellular", "telephone"], n),
        "day": rng.integers(1, 28, n),
        "month": rng.choice(["may", "jul", "mar", "sep"], n),
        "duration": rng.integers(10, 500, n),
        "campaign": rng.integers(1, 5, n),
        "pdays": rng.choice([-1, 100], n),
        "previous": rng.choice([0, 1], n),
        "poutcome": rng.choice(["unknown", "success", "failure"], n),
    })
    df["y"] = rng.choice(["no", "yes"], n, p=[0.8, 0.2])
    return df


def test_model_config_signature_invalidation():
    cfg1 = ModelConfig(random_seed=42)
    cfg2 = ModelConfig(random_seed=42)
    cfg3 = ModelConfig(random_seed=99)
    cfg4 = ModelConfig(max_indegree=2)

    assert cfg1.get_signature() == cfg2.get_signature()
    assert cfg1.get_signature() != cfg3.get_signature()
    assert cfg1.get_signature() != cfg4.get_signature()


def test_service_invalidation_logic():
    service = ModelService()
    assert not service.is_trained()

    cfg = ModelConfig()
    # Mocking artifacts
    service._artifacts = "mock_artifact"
    assert service.is_trained()

    service.invalidate_model(reason="Testing invalidation")
    assert not service.is_trained()
    assert service.get_artifacts() is None


def test_rule_based_single_prediction_traces():
    service = ModelService()

    # Case 1: poutcome == success
    rec1 = {"poutcome": "success", "month": "may"}
    res1 = service.predict_single_rule_based(rec1)
    assert res1["prediction"] == "yes"
    assert res1["matched_rule_id"] == "RULE_1"
    assert any(step["rule"] == "Rule 1" and step["result"] is True for step in res1["trace"] if "rule" in step)

    # Case 2: high month
    rec2 = {"poutcome": "failure", "month": "mar"}
    res2 = service.predict_single_rule_based(rec2)
    assert res2["prediction"] == "yes"
    assert res2["matched_rule_id"] == "RULE_2"
    assert any(step["rule"] == "Rule 2" and step["result"] is True for step in res2["trace"] if "rule" in step)

    # Case 3: default rule
    rec3 = {"poutcome": "unknown", "month": "aug"}
    res3 = service.predict_single_rule_based(rec3)
    assert res3["prediction"] == "no"
    assert res3["matched_rule_id"] == "RULE_DEFAULT"
    assert any("Default" in step["rule"] for step in res3["trace"] if "rule" in step)


def test_gui_modules_importable():
    """Verify that all core modules required by Streamlit can be imported."""
    import src.config
    import src.preprocessing
    import src.evaluation
    import src.execution_log
    import src.model_service
    import data_loader
    import bayesian_network
    import rule_based
    import branch_counter

    assert hasattr(rule_based, "classify_client")
    assert hasattr(bayesian_network, "learn_structure")
    assert hasattr(branch_counter, "check_file")


def test_bayesian_network_single_prediction_with_mocked_small_model():
    """Verify inference pipeline on a small synthetic Bayesian Network without full training."""
    from pgmpy.models import DiscreteBayesianNetwork
    from pgmpy.factors.discrete import TabularCPD

    # Create tiny model: month -> y, poutcome -> y
    model = DiscreteBayesianNetwork([("month", "y"), ("poutcome", "y")])
    # Define dummy CPDs
    cpd_month = TabularCPD("month", 2, [[0.5], [0.5]], state_names={"month": ["may", "mar"]})
    cpd_poutcome = TabularCPD("poutcome", 2, [[0.7], [0.3]], state_names={"poutcome": ["failure", "success"]})
    # y given month (2) and poutcome (2) -> 4 columns
    cpd_y = TabularCPD(
        "y", 2,
        [[0.9, 0.4, 0.6, 0.1],   # no
         [0.1, 0.6, 0.4, 0.9]],  # yes
        evidence=["month", "poutcome"],
        evidence_card=[2, 2],
        state_names={"y": ["no", "yes"], "month": ["may", "mar"], "poutcome": ["failure", "success"]}
    )
    model.add_cpds(cpd_month, cpd_poutcome, cpd_y)
    assert model.check_model()

    # Preprocessor mock
    raw_df = pd.DataFrame([
        {"age": 30, "job": "admin.", "marital": "married", "education": "secondary",
         "default": "no", "balance": 100, "housing": "no", "loan": "no", "contact": "cellular",
         "day": 5, "month": "may", "campaign": 1, "pdays": -1, "previous": 0, "poutcome": "failure"},
        {"age": 40, "job": "admin.", "marital": "married", "education": "secondary",
         "default": "no", "balance": 500, "housing": "no", "loan": "no", "contact": "cellular",
         "day": 10, "month": "mar", "campaign": 2, "pdays": 50, "previous": 1, "poutcome": "success"}
    ])
    preprocessor = BankPreprocessor().fit(raw_df)

    service = ModelService()
    # Construct mock artifacts
    from src.model_service import ModelConfig, TrainedArtifacts
    dummy_cfg = ModelConfig()
    dummy_artifacts = TrainedArtifacts(
        config=dummy_cfg,
        signature="mock_sig",
        model=model,
        preprocessor=preprocessor,
        edges=[("month", "y"), ("poutcome", "y")],
        X_train=raw_df,
        X_test=raw_df,
        y_train=pd.Series(["no", "yes"]),
        y_test=pd.Series(["no", "yes"]),
        bn_predictions=pd.Series(["no", "yes"]),
        bn_proba_yes=pd.Series([0.1, 0.9]),
        bn_metrics={"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
        rule_predictions=pd.Series(["no", "yes"]),
        rule_metrics={"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
        baseline_metrics={"accuracy": 0.5, "precision": 0.0, "recall": 0.0, "f1": 0.0},
        training_duration=1.2,
        stage_durations={}
    )

    res = service.predict_single_bn(raw_df.iloc[1].to_dict(), artifacts=dummy_artifacts)
    assert res["prediction"] in config.LABELS
    assert 0.0 <= res["p_yes"] <= 1.0
    assert 0.0 <= res["p_no"] <= 1.0
    assert pytest.approx(res["p_yes"] + res["p_no"]) == 1.0
    assert "disclaimer" in res
