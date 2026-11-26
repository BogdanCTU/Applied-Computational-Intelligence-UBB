"""Shared pytest fixtures using isolated temporary SQLite databases and configs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bug_detector.config import AppConfig, get_project_root
from bug_detector.db import BugDetectorRepository, DatabaseManager


@pytest.fixture()
def fixtures_dir() -> Path:
    return get_project_root() / "2_SourceCode" / "Tests" / "fixtures"


@pytest.fixture()
def temp_config(tmp_path: Path) -> AppConfig:
    cfg = AppConfig()
    cfg.database_relpath = str(tmp_path / "test_bug_detector.db")
    cfg.datasets_dir_relpath = str(tmp_path / "datasets")
    cfg.models_dir_relpath = str(tmp_path / "models")
    cfg.results_dir_relpath = str(tmp_path / "results")
    cfg.config_relpath = str(tmp_path / "active_config.json")
    return cfg


@pytest.fixture()
def temp_repo(temp_config: AppConfig) -> BugDetectorRepository:
    return BugDetectorRepository(DatabaseManager(temp_config.db_path))


def make_synthetic_records(n_repos: int = 12, per_repo: int = 6) -> list[dict]:
    """Generate deterministic synthetic method feature records across distinct repos."""
    records = []
    for r in range(n_repos):
        repo_id = f"org/repo_{r:02d}"
        for j in range(per_repo):
            is_bug = (j % 2 == 0)
            sid = f"syn_{r}_{j}"
            tokens = (
                ["public", "void", "Run", "(", "string", "s", ")", "{", "var", "x", "=", "s", ".", "Length", ";", "}"]
                if is_bug
                else ["public", "int", "Safe", "(", "string", "s", ")", "{", "if", "(", "s", "is", "null", ")", "return", "0", ";", "return", "s", ".", "Length", ";", "}"]
            )
            records.append(
                {
                    "sample_id": sid,
                    "repository_id": repo_id,
                    "pair_id": f"pair_{r}_{j // 2}",
                    "commit_timestamp": f"2025-0{(r % 9) + 1}-15T10:00:00Z",
                    "file_path": f"src/File{j}.cs",
                    "class_name": f"Class{j}",
                    "method_name": "Run" if is_bug else "Safe",
                    "label": 1 if is_bug else 0,
                    "label_source": "inferredbugs_infersharp" if is_bug else "inferredbugs_post_fix",
                    "verification_status": "static_analyzer_verified_fix" if is_bug else "post_fix_verified",
                    "bug_type": "NULL_DEREFERENCE" if is_bug else "NONE",
                    "source_hash": f"hash_{r}_{j}_{'bug' if is_bug else 'fix'}",
                    "source_code": " ".join(tokens),
                    "split_partition": "unassigned",
                    "extraction_failed": False,
                    "semantic_model_available": True,
                    "tokens_normalized": tokens,
                    "api_calls": ["s.Length"] if is_bug else ["string.IsNullOrEmpty", "s.Length"],
                    "lexical_metrics": {
                        "token_count": float(len(tokens)),
                        "null_literal_count": 0.0 if is_bug else 1.0,
                        "api_call_count": 1.0 if is_bug else 2.0,
                    },
                    "ast_metrics": {
                        "ast_node_count": 20.0 if is_bug else 30.0,
                        "ast_null_comparison_count": 0.0 if is_bug else 1.0,
                        "ast_is_null_pattern_count": 0.0 if is_bug else 1.0,
                        "ast_null_syntax_density": 0.0 if is_bug else 0.08,
                    },
                    "cfg_metrics": {
                        "cfg_available": 1.0,
                        "cfg_succeeded": 1.0,
                        "cfg_branch_nodes": 0.0 if is_bug else 1.0,
                        "cfg_early_return_count": 0.0 if is_bug else 1.0,
                    },
                    "dfg_metrics": {
                        "semantic_model_available": 1.0,
                        "dfg_available": 1.0,
                        "dfg_succeeded": 1.0,
                        "dfg_checked_param_null_count": 0.0 if is_bug else 1.0,
                        "dfg_unchecked_param_deref_count": 1.0 if is_bug else 0.0,
                        "dfg_undisposed_resource_allocations": 1.0 if (is_bug and j == 0) else 0.0,
                    },
                    "structural_metrics": {
                        "struct_cyclomatic_complexity": 1.0 if is_bug else 2.0,
                        "struct_logical_loc": 5.0 if is_bug else 7.0,
                        "struct_parameter_count": 1.0,
                    },
                }
            )
    return records
