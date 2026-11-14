"""Regression and integrity tests for the FluentValidation pilot collection (v1 and v2 corrected)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from config.settings import get_settings
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.utils.source_classifier import is_production_csharp_file, is_test_source_path


def test_fluentvalidation_pilot_database_integrity():
    """Verify that FluentValidation data was ingested with full production integrity."""
    settings = get_settings()
    db_path = settings.storage.database_path
    assert db_path.exists(), "Production database file missing."

    db = Database(db_path)
    repo_db = RepositoryDB(db)

    # 1. Verify FluentValidation repository record
    fv_repo = repo_db.get_repository_by_full_name("FluentValidation/FluentValidation")
    assert fv_repo is not None, "FluentValidation repository not found in database."
    assert fv_repo["name"] == "FluentValidation"
    assert fv_repo["owner"] == "FluentValidation"
    assert fv_repo["default_branch"] == "main"
    assert fv_repo["is_cloned"] == 1

    # 2. Verify observation and feature counts (v2 corrected: 28 production observations)
    fv_id = fv_repo["id"]
    obs = repo_db.list_observations(repository_id=fv_id)
    assert len(obs) == 28, f"Expected 28 production observations for FluentValidation, found {len(obs)}"

    buggy_obs = [o for o in obs if o["label"] == 1]
    clean_obs = [o for o in obs if o["label"] == 0]
    assert len(buggy_obs) == 14, "Expected exactly 14 Label 1 (production buggy) observations"
    assert len(clean_obs) == 14, "Expected exactly 14 Label 0 (candidate clean) observations"

    # 3. Assert zero test files leaked into either buggy or clean observations
    for o in obs:
        assert is_production_csharp_file(o["file_path"]) is True, f"Non-production file found: {o['file_path']}"
        assert is_test_source_path(o["file_path"]) is False, f"Test file leaked into observations: {o['file_path']}"

    # 4. Verify that all 28 observations have successfully extracted features
    for o in obs:
        feat = repo_db.get_features_by_observation_id(o["id"])
        assert feat is not None, f"Observation #{o['id']} missing features record"
        assert feat.get("status") == "success"
        assert feat.get("loc") is not None
        assert feat.get("cyclomatic_complexity") is not None
        assert feat.get("method_length") is not None

    # 5. Verify that historical dataset snapshot csharp_empirical_v1 is untouched
    with db.session() as conn:
        ds_row = conn.execute("SELECT * FROM datasets WHERE id = 1").fetchone()
        assert ds_row is not None, "Historical dataset snapshot missing"
        assert ds_row["name"] == "csharp_empirical_v1"
        assert ds_row["version"] == "1.0.0"
        assert ds_row["total_count"] == 483, f"Historical snapshot size changed! Expected 483, got {ds_row['total_count']}"

        # Ensure no FluentValidation observations leaked into dataset 1
        leaked = conn.execute(
            """
            SELECT COUNT(*) FROM dataset_observations do
            JOIN observations o ON do.observation_id = o.id
            WHERE do.dataset_id = 1 AND o.repository_id = :fv_id
            """,
            {"fv_id": fv_id}
        ).fetchone()[0]
        assert leaked == 0, f"Found {leaked} FluentValidation observations in historical snapshot #1!"


def test_fluentvalidation_pilot_artifact_consistency():
    """Verify that both v1 historical and v2 corrected pilot reports exist and match expectations."""
    settings = get_settings()
    reports_dir = settings.storage.reports_dir / "pilot"

    # 1. Verify v1 historical artifact is preserved
    v1_path = reports_dir / "fluentvalidation_pilot_results.json"
    assert v1_path.exists(), f"Original v1 pilot summary report missing at {v1_path}"

    with open(v1_path, encoding="utf-8") as f:
        v1_data = json.load(f)

    assert v1_data["repository"]["full_name"] == "FluentValidation/FluentValidation"
    assert v1_data["mining_stats"]["commits_requested"] == 350
    assert v1_data["mining_stats"]["bug_fixing_commits"] == 11
    assert v1_data["szz_stats"]["total_bic_line_traces"] == 28
    assert v1_data["observation_stats"]["total_observations"] == 34
    assert v1_data["observation_stats"]["buggy_label_1"] == 17
    assert v1_data["observation_stats"]["candidate_clean_label_0"] == 17

    # 2. Verify v2 corrected artifact
    v2_path = reports_dir / "fluentvalidation_pilot_v2_corrected.json"
    assert v2_path.exists(), f"Corrected v2 pilot report missing at {v2_path}"

    with open(v2_path, encoding="utf-8") as f:
        v2_data = json.load(f)

    assert v2_data["repository"]["full_name"] == "FluentValidation/FluentValidation"
    assert v2_data["commit_sampling_audit"]["commits_requested"] == 350
    assert v2_data["bug_fixing_commit_audit"]["total_classified_fixes"] == 11
    assert v2_data["bug_fixing_commit_audit"]["manual_audit_verified_true_defects"] == 10
    assert v2_data["filtering_comparison_v1_vs_v2"]["v2_corrected_production_only"]["total_observations"] == 28
    assert v2_data["filtering_comparison_v1_vs_v2"]["v2_corrected_production_only"]["test_code_leakage_detected"] is False
    assert v2_data["calibrated_yield_metrics"]["positive_method_yield"] == 0.04
    assert v2_data["calibrated_yield_metrics"]["bug_fix_detection_rate"] == 0.0314
    assert v2_data["calibrated_yield_metrics"]["szz_trace_success_rate"] == 0.9091
    assert v2_data["feature_extraction_stats"]["success"] == 28
