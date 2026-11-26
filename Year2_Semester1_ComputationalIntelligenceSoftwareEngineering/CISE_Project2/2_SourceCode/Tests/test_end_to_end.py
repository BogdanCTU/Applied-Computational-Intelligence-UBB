"""End-to-end tests on representative C# fixtures (buggy, fixed, hard negative, malformed, constructs)."""

from __future__ import annotations

from pathlib import Path

from bug_detector.config import AppConfig
from bug_detector.db import BugDetectorRepository, DatabaseManager
from bug_detector.ml import (
    BugDetectorPredictor,
    build_repository_splits,
    save_model_bundle,
    train_random_forest_with_cv,
)
from conftest import make_synthetic_records


def _build_temp_predictor(temp_config: AppConfig) -> BugDetectorPredictor:
    records = make_synthetic_records(n_repos=10, per_repo=6)
    splits = build_repository_splits(records, independent_test_fraction=0.2, random_state=42)
    temp_config.random_forest.n_estimators = 30
    temp_config.validation.outer_folds = 3
    temp_config.features.tfidf_min_df = 1

    repo = BugDetectorRepository(DatabaseManager(temp_config.db_path))
    repo.register_dataset_version("v5-e2e", "e2e", {"valid_records": len(records)})

    bundle = train_random_forest_with_cv(
        dev_records=splits["dev"],
        dataset_version="v5-e2e",
        experiment_code="I",
        config=temp_config,
        tune_hyperparameters=False,
        tune_calibration=False,
    )
    bundle["model_version"] = "rf_e2e_v5"
    save_model_bundle("rf_e2e_v5", bundle, config=temp_config, activate=True)
    return BugDetectorPredictor(model_path_or_version="rf_e2e_v5", config=temp_config)


def test_end_to_end_fixtures_classification_and_error_guards(
    fixtures_dir: Path, temp_config: AppConfig
) -> None:
    predictor = _build_temp_predictor(temp_config)

    # 1. Malformed syntax must NEVER produce CLEAN
    malformed_src = (fixtures_dir / "malformed_syntax.cs").read_text(encoding="utf-8")
    res_bad = predictor.predict_source(malformed_src, file_name="malformed_syntax.cs", input_mode="cli")
    assert res_bad["analysis_status"] == "ANALYSIS_ERROR"
    assert res_bad["has_syntax_errors"] is True
    assert all(m["classification"] == "ANALYSIS_ERROR" for m in res_bad["methods"])

    # 2. Valid multi-method files produce structured BUG/CLEAN/UNCERTAIN outputs with local evidence
    for fname in ["verified_buggy.cs", "verified_fixed.cs", "complex_clean_hard_negative.cs", "diverse_constructs.cs"]:
        src = (fixtures_dir / fname).read_text(encoding="utf-8")
        res = predictor.predict_source(src, file_name=fname, input_mode="cli")
        assert res["analysis_status"] == "OK"
        assert len(res["methods"]) >= 1
        for m in res["methods"]:
            assert m["classification"] in {"BUG", "CLEAN", "UNCERTAIN"}
            assert 0.0 <= m["probability"] <= 1.0
            assert m["model_version"] == "rf_e2e_v5"
            assert m["suspicious_rank"] is not None
            assert m["local_evidence"]["method"] == "tree_path_saabas_decomposition"
