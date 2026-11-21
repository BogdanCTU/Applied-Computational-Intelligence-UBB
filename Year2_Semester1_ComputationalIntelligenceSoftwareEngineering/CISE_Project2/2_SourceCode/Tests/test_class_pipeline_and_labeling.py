"""Tests for repository discovery/ranking, DB migrations, class-level SZZ labeling, and deduplicated datasets."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import git
import pytest

from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from repositories.github_client import GitHubClient, evaluate_repository_candidate
from services.dataset.dataset_builder import CLASS_IDENTIFIER_COLUMNS, DatasetBuilder
from services.dataset.exporter import DatasetExporter
from services.labeling.label_manager import LabelManager, compute_source_fingerprints
from services.mining.szz_analyzer import SZZAnalyzer


def test_repository_evaluation_and_exclusions():
    good = {
        "full_name": "org/lib", "stars": 1500, "forks": 200, "size_kb": 4000,
        "is_fork": False, "is_archived": False, "language": "C#",
        "pushed_at": "2026-10-01T00:00:00Z",
    }
    ok, score, reason, excl = evaluate_repository_candidate(good, min_stars=50, min_size_kb=100)
    assert ok is True
    assert score > 0.5
    assert excl is None
    assert "Selected" in reason

    fork_repo = dict(good, is_fork=True)
    ok_f, _, _, excl_f = evaluate_repository_candidate(fork_repo)
    assert ok_f is False and excl_f == "excluded_fork"

    archived_repo = dict(good, is_archived=True)
    ok_a, _, _, excl_a = evaluate_repository_candidate(archived_repo)
    assert ok_a is False and excl_a == "excluded_archived"

    empty_repo = dict(good, size_kb=0)
    ok_e, _, _, excl_e = evaluate_repository_candidate(empty_repo)
    assert ok_e is False and excl_e == "excluded_empty_repository"

    python_repo = dict(good, language="Python")
    ok_p, _, _, excl_p = evaluate_repository_candidate(python_repo)
    assert ok_p is False and "excluded_primary_language" in excl_p


@patch("time.sleep", return_value=None)
@patch("requests.Session.get")
def test_github_discovery_pagination_and_deduplication(mock_get, _mock_sleep):
    item1 = {
        "id": 1, "full_name": "org/RepoA", "name": "RepoA", "owner": {"login": "org"},
        "html_url": "https://github.com/org/RepoA", "clone_url": "https://github.com/org/RepoA.git",
        "description": "A", "language": "C#", "stargazers_count": 4000, "forks_count": 200,
        "size": 2500, "default_branch": "main", "license": {"spdx_id": "MIT"},
        "fork": False, "archived": False, "pushed_at": "2026-10-01T00:00:00Z",
    }
    item_dup = dict(item1)
    item_fork = dict(item1, id=2, full_name="forker/RepoA", fork=True)

    resp1 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "9"})
    resp1.json.return_value = {"total_count": 2, "items": [item1, item_fork, item_dup]}
    resp_empty = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "8"})
    resp_empty.json.return_value = {"total_count": 0, "items": []}
    mock_get.side_effect = [resp1, resp_empty, resp_empty, resp_empty]

    client = GitHubClient()
    disc = client.discover_csharp_repositories(target_count=10, max_pages_per_query=1)
    assert disc["discovered_total"] == 2
    assert disc["selected_total"] == 1
    assert disc["excluded_total"] == 1
    assert disc["selected"][0]["full_name"] == "org/RepoA"


def test_class_szz_labeling_duplicate_detection_and_export(tmp_path):
    # Create synthetic git repo with one buggy class and one clean class
    repo_dir = tmp_path / "class_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    buggy_cs = repo_dir / "OrderService.cs"
    clean_cs = repo_dir / "TaxHelper.cs"

    buggy_v1 = """namespace Store
{
    public class OrderService
    {
        public decimal Apply(decimal amount, int qty)
        {
            if (qty < 0) return amount;
            decimal total = amount * qty;
            if (total > 100m) total -= 10m;
            return total;
        }

        public bool IsValid(int qty) => qty > 0;
    }
}
"""
    clean_v1 = """namespace Store
{
    public class TaxHelper
    {
        public decimal ComputeTax(decimal amount)
        {
            if (amount <= 0) return 0m;
            return amount * 0.19m;
        }
    }
}
"""
    buggy_cs.write_text(buggy_v1, encoding="utf-8")
    clean_cs.write_text(clean_v1, encoding="utf-8")
    repo.index.add(["OrderService.cs", "TaxHelper.cs"])
    repo.index.commit("Initial commit")

    buggy_v2 = buggy_v1.replace("if (qty < 0) return amount;", "if (qty <= 0) throw new System.ArgumentException();")
    buggy_cs.write_text(buggy_v2, encoding="utf-8")
    repo.index.add(["OrderService.cs"])
    fix_commit = repo.index.commit("Fix #42: invalid quantity check in OrderService")

    db = Database(tmp_path / "class_pipeline.db")
    repo_db = RepositoryDB(db)
    repo_id = repo_db.upsert_repository({
        "full_name": "store/core",
        "name": "core",
        "owner": "store",
        "url": str(repo_dir),
    })
    repo_db.upsert_commit({
        "repository_id": repo_id,
        "commit_sha": fix_commit.hexsha,
        "message": "Fix #42: invalid quantity check in OrderService",
        "modifies_csharp": 1,
        "is_bug_fix": 1,
        "bug_fix_confidence": 0.90,
    })

    szz = SZZAnalyzer(repo_db)
    traces = szz.analyze_commit(repo, fix_commit.hexsha, repo_id)
    assert len(traces) >= 1

    mgr = LabelManager(repo_db)
    buggy_obs = mgr.create_class_observations_from_szz(repo_id, repo_dir)
    assert len(buggy_obs) == 1
    assert buggy_obs[0]["class_name"] == "OrderService"
    assert buggy_obs[0]["label"] == 1
    assert buggy_obs[0]["szz_trace_count"] >= 1
    assert "ArgumentException" in (buggy_obs[0]["corrected_code"] or "")

    clean_obs = mgr.sample_candidate_clean_classes(repo_id, repo_dir, target_count=5)
    assert len(clean_obs) == 1
    assert clean_obs[0]["class_name"] == "TaxHelper"
    assert clean_obs[0]["label"] == 0

    # Insert an exact duplicate clean observation in another repo to verify cross-repo dedup
    repo2_id = repo_db.upsert_repository({
        "full_name": "store/forked-copy", "name": "forked-copy", "owner": "store", "url": str(repo_dir),
    })
    clean_class_src = clean_obs[0]["source_code"]
    src_fp, struct_fp = compute_source_fingerprints(clean_class_src)
    dup_id = repo_db.insert_class_observation({
        "repository_id": repo2_id,
        "commit_sha": "deadbeef",
        "file_path": "TaxHelper.cs",
        "namespace_name": "Store",
        "class_name": "TaxHelper",
        "qualified_class_name": "Store.TaxHelper",
        "source_code": clean_class_src,
        "source_fingerprint": src_fp,
        "structural_fingerprint": struct_fp,
        "label": 0,
        "evidence_category": "stable_head_class",
    })
    feat = dict(repo_db.get_class_features_by_observation_id(clean_obs[0]["id"]))
    feat["class_observation_id"] = dup_id
    repo_db.upsert_class_features(feat)

    builder = DatasetBuilder(repo_db)
    ds_id, stats = builder.generate_class_dataset_snapshot(
        name="test_class_ds",
        version="3.0.0",
        deduplicate_exact_source=True,
    )
    assert stats["total_observations"] == 2
    assert stats["duplicate_analysis"]["cross_repo_exact_duplicates_removed"] == 1

    X, y, meta = builder.get_class_features_and_labels(ds_id)
    assert list(X.columns) == CLASS_FEATURE_NAMES
    for col in CLASS_IDENTIFIER_COLUMNS:
        assert col not in X.columns
    assert set(y.unique()) == {0, 1}
    assert set(meta["repository_id"].unique()) == {repo_id}

    exporter = DatasetExporter(repo_db, tmp_path / "exports")
    exp = exporter.export_to_csv(ds_id, duplicate_analysis=stats["duplicate_analysis"])
    assert Path(exp["csv_path"]).exists()
    assert Path(exp["manifest_path"]).exists()
    manifest = json.loads(Path(exp["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["feature_count"] == 40
    assert manifest["sha256_checksum"] == exp["sha256_checksum"]


def test_legacy_database_migration_preserves_existing_records(tmp_path):
    import sqlite3
    db_file = tmp_path / "legacy_v2.db"
    conn = sqlite3.connect(str(db_file))
    conn.executescript("""
        CREATE TABLE repositories (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT UNIQUE NOT NULL, name TEXT NOT NULL, owner TEXT NOT NULL, url TEXT NOT NULL);
        CREATE TABLE datasets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, version TEXT NOT NULL, total_count INTEGER DEFAULT 0, buggy_count INTEGER DEFAULT 0, non_buggy_count INTEGER DEFAULT 0, uncertain_count INTEGER DEFAULT 0, feature_names TEXT NOT NULL);
        CREATE TABLE models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, algorithm TEXT NOT NULL, parameters_json TEXT NOT NULL, metrics_json TEXT NOT NULL, feature_names_json TEXT NOT NULL, model_file_path TEXT NOT NULL);
        CREATE TABLE predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, model_name TEXT NOT NULL, method_name TEXT NOT NULL, metrics_json TEXT NOT NULL, predicted_label INTEGER NOT NULL, risk_score REAL NOT NULL, risk_category TEXT NOT NULL);
        INSERT INTO repositories (full_name, name, owner, url) VALUES ('org/legacy', 'legacy', 'org', 'https://github.com/org/legacy');
        INSERT INTO datasets (name, version, total_count, feature_names) VALUES ('legacy_ds', '1.0.0', 10, '["loc"]');
    """)
    conn.commit()
    conn.close()

    migrated_db = Database(db_file)
    repo_db = RepositoryDB(migrated_db)
    assert repo_db.get_repository_by_full_name("org/legacy") is not None
    assert repo_db.get_dataset_by_name("legacy_ds")["total_count"] == 10
    stats = repo_db.get_summary_statistics()
    assert stats["class_observations_total"] == 0


@patch("time.sleep", return_value=None)
@patch("requests.Session.get")
def test_github_client_rate_limit_retry_and_recovery(mock_get, _mock_sleep):
    import time as pytime
    rate_resp = MagicMock(status_code=403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(pytime.time()) + 1)})
    rate_resp.text = "API rate limit exceeded"
    ok_resp = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "59"})
    ok_resp.json.return_value = {
        "id": 9, "full_name": "org/recovered", "name": "recovered", "owner": {"login": "org"},
        "html_url": "https://github.com/org/recovered", "clone_url": "https://github.com/org/recovered.git",
        "stargazers_count": 500, "forks_count": 50, "size": 1000,
    }
    mock_get.side_effect = [rate_resp, ok_resp]
    client = GitHubClient(max_retries=2)
    repo = client.get_repository("org", "recovered")
    assert repo["full_name"] == "org/recovered"
    assert mock_get.call_count == 2
