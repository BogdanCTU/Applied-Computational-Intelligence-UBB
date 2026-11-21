"""Tests for mitigation dataset construction, anti-leakage guarantees, and Ollama-MLX converter."""

from __future__ import annotations

import json
from pathlib import Path

from source.config.settings import AppConfig
from source.fine_tuning.dataset_builder import MitigationDatasetBuilder
from source.fine_tuning.mlx_converter import OllamaMLXConverter
from source.fine_tuning.trainer import parse_mlx_training_log
from source.storage.database import DatabaseManager
from source.storage.models import TestCaseRecord, TestCategory
from source.test_generation.generator import PenetrationTestGenerator
from source.utils.hashing import sha256_text


def test_mitigation_dataset_zero_leakage_and_positive_targets(temp_db: DatabaseManager, tmp_path: Path) -> None:
    gen = PenetrationTestGenerator(seed=42)
    cases = gen.generate(count_per_category=20)
    with temp_db.session() as sess:
        for cid in sorted({c.category for c in cases}):
            sess.add(TestCategory(id=cid, name=cid, description="d", risk_domain="r", target_count=20))
        sess.flush()
        for c in cases:
            cj = json.dumps(c.conversation)
            sess.add(
                TestCaseRecord(
                    test_id=c.test_id,
                    category_id=c.category,
                    subcategory=c.subcategory,
                    severity=c.severity,
                    risk_type=c.risk_type,
                    attack_pattern=c.attack_pattern,
                    expected_behavior=c.expected_behavior,
                    expected_risk=c.expected_risk,
                    split=c.split,
                    template_family=c.template_family,
                    dataset_version=c.dataset_version,
                    conversation_json=cj,
                    evaluation_criteria_json=json.dumps(c.evaluation_criteria),
                    tags_json=json.dumps(c.tags),
                    prompt_hash=sha256_text(cj),
                )
            )

    builder = MitigationDatasetBuilder(AppConfig(), temp_db)
    manifest = builder.build_datasets(output_base_dir=tmp_path / "ft")
    assert manifest["template_family_overlap_with_held_out"] == 0
    assert manifest["train_count"] > 0 and manifest["valid_count"] > 0
    assert manifest["train_benign"] > 0 and manifest["train_adversarial"] > 0

    train_meta = json.loads((tmp_path / "ft" / "02_Raw_Datasets" / "train_metadata.json").read_text(encoding="utf-8"))
    held_meta = json.loads((tmp_path / "ft" / "02_Raw_Datasets" / "held_out_reference.json").read_text(encoding="utf-8"))
    train_families = {r["template_family"] for r in train_meta}
    held_families = {r["template_family"] for r in held_meta}
    assert train_families.isdisjoint(held_families)


def test_ollama_manifest_path_resolution(tmp_path: Path) -> None:
    conv = OllamaMLXConverter(ollama_models_dir=tmp_path)
    p = conv.get_manifest_path("qwen3.5:4b-safety")
    assert str(p).endswith("manifests/registry.ollama.ai/library/qwen3.5/4b-safety")


def test_parse_mlx_training_log_ansi() -> None:
    sample = "\x1b[38;5;244m   1\x1b[0m     \x1b[1;35mval\x1b[0m  \x1b[1m3.373\x1b[0m     19.95s\n  10     2.644 ▼         8\n"
    vals, trs = parse_mlx_training_log(sample)
    assert vals == [(1, 3.373)]
    assert trs == [(10, 2.644)]
