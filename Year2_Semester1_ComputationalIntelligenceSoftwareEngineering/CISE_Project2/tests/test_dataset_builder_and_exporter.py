"""Unit and integration tests for FeatureExtractor, DatasetBuilder, and DatasetExporter."""
import pytest
from pathlib import Path

from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.dataset.feature_extractor import FeatureExtractor
from src.dataset.dataset_builder import DatasetBuilder, DEFAULT_NUMERICAL_FEATURES, IDENTIFIER_COLUMNS
from src.dataset.exporter import DatasetExporter


@pytest.fixture
def dataset_env(tmp_path):
    db_file = tmp_path / "dataset_test.db"
    db = Database(db_file)
    repo_db = RepositoryDB(db)

    repo_id = repo_db.upsert_repository({
        "full_name": "org/calc",
        "name": "calc",
        "owner": "org",
        "url": "https://github.com/org/calc",
    })

    # Add 3 observations: 1 Buggy (1), 1 Clean (0), 1 Uncertain (-1)
    obs1 = repo_db.insert_observation({
        "repository_id": repo_id,
        "commit_sha": "aaaa111",
        "file_path": "Calculator.cs",
        "class_name": "Calculator",
        "method_name": "Divide",
        "method_signature": "int Divide(int a, int b)",
        "source_code": "public int Divide(int a, int b) { if (b == 0) return 0; return a / b; }",
        "label": 1,
        "evidence_category": "szz_bic",
    })

    obs2 = repo_db.insert_observation({
        "repository_id": repo_id,
        "commit_sha": "aaaa111",
        "file_path": "Calculator.cs",
        "class_name": "Calculator",
        "method_name": "Add",
        "method_signature": "int Add(int a, int b)",
        "source_code": "public int Add(int a, int b) => a + b;",
        "label": 0,
        "evidence_category": "stable_version",
    })

    obs3 = repo_db.insert_observation({
        "repository_id": repo_id,
        "commit_sha": "aaaa111",
        "file_path": "Calculator.cs",
        "class_name": "Calculator",
        "method_name": "Ambiguous",
        "method_signature": "void Ambiguous()",
        "source_code": "public void Ambiguous() {}",
        "label": -1,
        "evidence_category": "ambiguous_commit",
    })

    return repo_db, repo_id, [obs1, obs2, obs3], tmp_path


def test_feature_extractor_lifecycle(dataset_env):
    repo_db, repo_id, obs_ids, _ = dataset_env
    extractor = FeatureExtractor(repo_db)

    # Batch extraction
    res = extractor.batch_extract(repository_id=repo_id)
    assert res["total"] == 3
    assert res["success"] == 3
    assert res["failed"] == 0

    # Verify features table entries
    feat1 = repo_db.get_features_by_observation_id(obs_ids[0])
    assert feat1 is not None
    assert feat1["status"] == "success"
    assert feat1["cyclomatic_complexity"] >= 2
    assert feat1["parameter_count"] == 2

    # Verify incremental skip: second call processes 0
    res2 = extractor.batch_extract(repository_id=repo_id)
    assert res2["total"] == 0


def test_dataset_builder_excludes_uncertain_and_leakage(dataset_env):
    repo_db, repo_id, obs_ids, _ = dataset_env
    extractor = FeatureExtractor(repo_db)
    extractor.batch_extract(repository_id=repo_id)

    builder = DatasetBuilder(repo_db)
    dataset_id, stats = builder.generate_dataset_snapshot(
        name="test_ml_dataset",
        version="1.0.0",
        exclude_uncertain=True,
    )

    assert dataset_id > 0
    assert stats["total_observations"] == 2
    assert stats["buggy_count"] == 1
    assert stats["clean_count"] == 1
    assert stats["uncertain_excluded"] == 1

    # Extract X, y, metadata
    X, y, metadata = builder.get_features_and_labels(dataset_id)
    assert len(X) == 2
    assert len(y) == 2
    assert set(y.unique()) == {0, 1}

    # Verify NO leakage identifiers exist in feature matrix X
    for col in IDENTIFIER_COLUMNS:
        assert col not in X.columns
    for feat in DEFAULT_NUMERICAL_FEATURES:
        assert feat in X.columns


def test_dataset_exporter_csv_and_metadata(dataset_env):
    repo_db, repo_id, _, tmp_path = dataset_env
    extractor = FeatureExtractor(repo_db)
    extractor.batch_extract(repository_id=repo_id)

    builder = DatasetBuilder(repo_db)
    dataset_id, _ = builder.generate_dataset_snapshot(name="export_dataset", version="1.0.0")

    exports_dir = tmp_path / "exports"
    exporter = DatasetExporter(repo_db, exports_dir)

    exp_res = exporter.export_to_csv(dataset_id)
    csv_path = Path(exp_res["csv_path"])
    meta_path = Path(exp_res["metadata_path"])

    assert csv_path.exists()
    assert meta_path.exists()
    assert exp_res["rows_exported"] == 2

    # Verify duplicate export prevention without overwrite=True
    with pytest.raises(FileExistsError):
        exporter.export_to_csv(dataset_id, overwrite=False)

