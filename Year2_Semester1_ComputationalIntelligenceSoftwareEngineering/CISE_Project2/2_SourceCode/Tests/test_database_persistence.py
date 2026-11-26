"""Tests for SQLite schema migrations, foreign keys, blob deduplication, and CRUD."""

from __future__ import annotations

import sqlite3

import pytest

from bug_detector.db import BugDetectorRepository


def test_schema_enforces_foreign_keys_and_deduplicates_blobs(temp_repo: BugDetectorRepository) -> None:
    with temp_repo.db.connect() as conn:
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1

    # Blob content-addressing avoids duplicating identical source text
    with temp_repo.db.transaction() as conn:
        h1 = temp_repo.ensure_source_blob(conn, "public void Foo() { return; }")
        h2 = temp_repo.ensure_source_blob(conn, "public void Foo() { return; }")
        assert h1 == h2
        cnt = conn.execute("SELECT COUNT(*) FROM source_blobs WHERE source_hash = ?", (h1,)).fetchone()[0]
        assert cnt == 1

    # Invalid dataset_version FK on dataset_samples must raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        with temp_repo.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO dataset_samples (
                    sample_id, dataset_version, repository_id, commit_sha, file_path,
                    class_name, method_name, method_signature, source_hash, structural_hash,
                    label, label_source, verification_status, bug_type, collection_timestamp
                ) VALUES ('x', 'missing_ver', 'missing_repo', 'sha', 'f.cs', 'C', 'M', 'void M()', ?, 'sh', 1, 'src', 'v', 'b', '2026-01-01')
                """,
                (h1,),
            )


def test_dataset_and_detection_run_persistence(temp_repo: BugDetectorRepository) -> None:
    temp_repo.register_dataset_version("v5-dbtest", "db test", {"valid_records": 1})
    temp_repo.register_model_version(
        {
            "model_version": "m_db_1",
            "dataset_version": "v5-dbtest",
            "algorithm": "RandomForestClassifier",
            "experiment_code": "I",
            "feature_groups": ["lexical", "ast"],
            "feature_schema": {"total_features": 10},
            "hyperparameters": {"n_estimators": 50},
            "threshold_low": 0.4,
            "threshold_center": 0.5,
            "threshold_high": 0.6,
            "calibration_method": "none",
            "artifact_path": "/tmp/model.joblib",
            "manifest_path": "/tmp/manifest.json",
            "dependency_versions": {"python": "3.13"},
        },
        activate=True,
    )
    assert temp_repo.get_active_model()["model_version"] == "m_db_1"

    temp_repo.save_detection_run(
        run_id="run_db_1",
        model_version="m_db_1",
        input_mode="paste",
        file_name="Demo.cs",
        source_code="public class Demo { public void M() {} }",
        analysis_status="OK",
        syntax_error_count=0,
        predictions=[
            {
                "file_name": "Demo.cs",
                "class_name": "Demo",
                "method_name": "M",
                "method_signature": "void M()",
                "start_line": 1,
                "end_line": 1,
                "classification": "UNCERTAIN",
                "probability": 0.51,
                "threshold_low": 0.4,
                "threshold_center": 0.5,
                "threshold_high": 0.6,
                "uncertainty_status": "within_uncertainty_band_[0.400, 0.600]",
                "feature_extraction_status": "complete",
                "suspicious_rank": 1,
                "method_source_hash": "abc",
            }
        ],
    )
    runs = temp_repo.list_detection_runs()
    assert len(runs) == 1
    assert runs[0]["uncertain_count"] == 1
    preds = temp_repo.query_predictions(classification="UNCERTAIN")
    assert len(preds) == 1
    assert preds[0]["method_name"] == "M"
