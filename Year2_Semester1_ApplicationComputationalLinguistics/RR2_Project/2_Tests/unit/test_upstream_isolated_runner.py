"""Tests for repository integrity manifests, database isolation, and upstream launcher guards."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verify_repo_integrity import build_directory_manifest, compare_manifests
from scripts.run_upstream_isolated import (
    ORIGINAL_REPO,
    PROTECTED_DB_NAME,
    SITECUSTOMIZE_TEMPLATE,
    _compute_alignment_metrics,
    _verify_postgres_isolation,
)


def test_directory_manifest_detects_modifications_and_additions(tmp_path: Path) -> None:
    sample = tmp_path / "repo"
    sample.mkdir()
    (sample / "a.txt").write_text("hello", encoding="utf-8")
    sub = sample / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("world", encoding="utf-8")

    baseline = build_directory_manifest(sample)
    assert baseline["file_count"] == 2
    assert compare_manifests(baseline, build_directory_manifest(sample))["identical"] is True

    (sample / "a.txt").write_text("modified", encoding="utf-8")
    (sample / "extra.txt").write_text("new", encoding="utf-8")
    diff = compare_manifests(baseline, build_directory_manifest(sample))
    assert diff["identical"] is False
    assert diff["added_files"] == ["extra.txt"]
    assert len(diff["modified_files"]) == 1
    assert diff["modified_files"][0]["path"] == "a.txt"


def test_postgres_isolation_rejects_protected_db_and_external_host() -> None:
    with pytest.raises(PermissionError, match=PROTECTED_DB_NAME):
        _verify_postgres_isolation("127.0.0.1", 5432, "postgres", PROTECTED_DB_NAME)

    with pytest.raises(ValueError, match="127.0.0.1"):
        _verify_postgres_isolation("0.0.0.0", 5432, "postgres", "agent_om_upstream")


def test_sitecustomize_audit_guard_blocks_protected_writes_and_external_sockets(
    tmp_path: Path,
) -> None:
    protected_dir = tmp_path / "protected_original"
    protected_dir.mkdir()
    (protected_dir / "source.xml").write_text("<rdf/>", encoding="utf-8")

    boot_dir = tmp_path / "_bootstrap"
    boot_dir.mkdir()
    overrides = {
        "original_repo": str(ORIGINAL_REPO),
        "protected_roots": [str(protected_dir)],
        "telemetry_path": str(tmp_path / "tel.jsonl"),
        "llm_model": "llama3:8b",
        "embedding_model": "llama3:8b",
        "ollama_chat_base_url": "http://127.0.0.1:11434",
        "ollama_embed_base_url": "http://127.0.0.1:11434",
        "temperature": 0.0,
        "seed": 42,
        "llm_top_k": 1,
        "top_p": 1.0,
        "repeat_penalty": 1.0,
        "smoke_limit": 0,
        "scalars": {},
    }
    (boot_dir / "overrides.json").write_text(json.dumps(overrides), encoding="utf-8")
    (boot_dir / "sitecustomize.py").write_text(SITECUSTOMIZE_TEMPLATE, encoding="utf-8")

    env = {"PYTHONPATH": str(boot_dir), "SYSTEMROOT": "C:\\Windows", "PATH": ""}
    # 1. Attempting to open a file inside protected_dir for writing must fail with PermissionError
    write_probe = (
        f"import pathlib; p = pathlib.Path(r'{protected_dir}') / 'hack.txt'; "
        f"p.write_text('blocked')"
    )
    proc_w = subprocess.run([sys.executable, "-c", write_probe], env=env, capture_output=True, text=True)
    assert proc_w.returncode != 0
    assert "PermissionError" in proc_w.stderr
    assert not (protected_dir / "hack.txt").exists()

    # 2. Attempting an external socket connection must fail with PermissionError
    net_probe = "import socket; s = socket.socket(); s.connect(('93.184.216.34', 80))"
    proc_n = subprocess.run([sys.executable, "-c", net_probe], env=env, capture_output=True, text=True)
    assert proc_n.returncode != 0
    assert "PermissionError" in proc_n.stderr


def test_compute_alignment_metrics_respects_named_columns(tmp_path: Path) -> None:
    true_csv = tmp_path / "true.csv"
    true_csv.write_text(
        "Entity1,Entity2\nhttp://cmt#Author,http://confOf#Author\nhttp://cmt#Paper,http://confOf#Paper\n",
        encoding="utf-8",
    )
    # Upstream predict_target.csv reverses column order to Entity2,Entity1!
    pred_target_csv = tmp_path / "predict_target.csv"
    pred_target_csv.write_text(
        "Entity2,Entity1\nhttp://confOf#Author,http://cmt#Author\nhttp://confOf#Poster,http://cmt#Paper\n",
        encoding="utf-8",
    )
    res = _compute_alignment_metrics(true_csv, pred_target_csv)
    assert res["tp"] == 1
    assert res["fp"] == 1
    assert res["fn"] == 1
    assert res["precision_pct"] == 50.0
    assert res["recall_pct"] == 50.0
    assert res["f1_pct"] == 50.0

