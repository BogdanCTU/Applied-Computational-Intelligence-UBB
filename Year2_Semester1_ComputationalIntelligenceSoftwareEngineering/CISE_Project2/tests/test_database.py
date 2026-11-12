"""Tests for database layer: schema creation, constraints, and repository operations."""
import pytest
from src.database.connection import Database
from src.database.repository import RepositoryDB


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_bugs.db"
    db = Database(db_file)
    return db, RepositoryDB(db)


def test_database_initialization(temp_db):
    db, repo_db = temp_db
    stats = repo_db.get_summary_statistics()
    assert stats["repositories_total"] == 0
    assert stats["commits_total"] == 0
    assert stats["observations_total"] == 0


def test_repository_lifecycle(temp_db):
    _, repo_db = temp_db
    repo_data = {
        "full_name": "dotnet/runtime",
        "name": "runtime",
        "owner": "dotnet",
        "url": "https://github.com/dotnet/runtime",
        "license": "MIT",
        "default_branch": "main",
        "stars": 15000,
        "forks": 4000,
        "is_cloned": 0,
        "local_path": None,
    }
    repo_id = repo_db.upsert_repository(repo_data)
    assert repo_id > 0

    fetched = repo_db.get_repository_by_id(repo_id)
    assert fetched is not None
    assert fetched["full_name"] == "dotnet/runtime"
    assert fetched["stars"] == 15000

    # Test update
    repo_db.update_repository_cloned_status(repo_id, True, "data/repositories/dotnet/runtime")
    updated = repo_db.get_repository_by_id(repo_id)
    assert updated["is_cloned"] == 1
    assert updated["local_path"] == "data/repositories/dotnet/runtime"


def test_commit_and_observation_lifecycle(temp_db):
    _, repo_db = temp_db
    repo_id = repo_db.upsert_repository({
        "full_name": "test/repo",
        "name": "repo",
        "owner": "test",
        "url": "https://github.com/test/repo",
        "license": "MIT",
        "default_branch": "main",
        "stars": 10,
        "forks": 1,
        "is_cloned": 1,
        "local_path": "/fake/path",
    })

    # Add commit
    commit_id = repo_db.upsert_commit({
        "repository_id": repo_id,
        "commit_sha": "abc1234",
        "parent_sha": "def5678",
        "author_name": "Alice Developer",
        "author_email": "alice@example.com",
        "committed_date": "2026-01-01 10:00:00",
        "message": "Fix null reference in Parser.ParseMethod",
        "is_bug_fix": 1,
        "bug_fix_confidence": 0.95,
        "bug_fix_evidence": "keyword: fix, null reference",
    })
    assert commit_id > 0

    # Add observation
    obs_id = repo_db.insert_observation({
        "repository_id": repo_id,
        "commit_sha": "def5678",
        "parent_sha": "999aaaa",
        "bug_fix_commit_sha": "abc1234",
        "file_path": "src/Parser.cs",
        "class_name": "Parser",
        "method_name": "ParseMethod",
        "method_signature": "ParseMethod(string)",
        "source_code": "public void ParseMethod(string s) { if (s == null) return; }",
        "corrected_code": "public void ParseMethod(string s) { ArgumentNullException.ThrowIfNull(s); }",
        "label": 1,
        "label_confidence": 0.95,
        "evidence_category": "szz_bic",
        "bug_fixing_commit_message": "Fix null reference in Parser.ParseMethod",
        "issue_or_pr_url": None,
    })
    assert obs_id > 0

    # Add features for observation
    feat_id = repo_db.upsert_features({
        "observation_id": obs_id,
        "loc": 10,
        "method_length": 80,
        "num_statements": 3,
        "num_parameters": 1,
        "num_local_vars": 0,
        "num_returns": 1,
        "num_assignments": 0,
        "cyclomatic_complexity": 2,
        "max_nesting_depth": 1,
        "num_conditionals": 1,
        "num_boolean_expressions": 1,
        "num_logical_operators": 0,
        "num_loops": 0,
        "num_try_catch": 0,
        "num_throw": 0,
        "num_method_calls": 0,
        "num_field_references": 0,
        "num_property_references": 0,
        "is_static": 0,
        "is_async": 0,
        "is_generic": 0,
        "num_comments": 0,
        "num_lambdas": 0,
        "num_linq_operations": 0,
        "raw_metrics_json": "{}",
    })
    assert feat_id > 0

    features = repo_db.get_features_by_observation_id(obs_id)
    assert features is not None
    assert features["loc"] == 10
    assert features["cyclomatic_complexity"] == 2

    # Create dataset snapshot
    ds_id = repo_db.create_dataset(
        name="test_dataset_v1",
        version="1.0.0",
        description="Unit test dataset",
        observation_ids=[obs_id],
        feature_names=["loc", "cyclomatic_complexity"],
    )
    assert ds_id > 0

    df_records = repo_db.get_dataset_dataframe_records(ds_id)
    assert len(df_records) == 1
    assert df_records[0]["observation_id"] == obs_id
    assert df_records[0]["label"] == 1
    assert df_records[0]["repository_name"] == "test/repo"
    assert df_records[0]["loc"] == 10

    # Verify summary statistics
    stats = repo_db.get_summary_statistics()
    assert stats["repositories_total"] == 1
    assert stats["commits_total"] == 1
    assert stats["observations_total"] == 1
    assert stats["observations_buggy"] == 1
    assert stats["features_extracted"] == 1

