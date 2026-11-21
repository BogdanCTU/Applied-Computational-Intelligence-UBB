"""Offline unit tests for test generation, ID uniqueness, diversity, and template-family split isolation."""

from __future__ import annotations

from pathlib import Path

from source.config.settings import load_config
from source.penetration.taxonomy import CATEGORIES
from source.test_generation.diversity import compute_diversity_report
from source.test_generation.generator import PenetrationTestGenerator


def test_config_validation() -> None:
    cfg = load_config()
    assert cfg.project.local_only is True
    assert cfg.model.provider == "ollama"
    assert cfg.penetration.categories >= 12
    assert cfg.penetration.minimum_tests_per_category >= 100


def test_generation_1200_cases_and_diversity(tmp_path: Path) -> None:
    gen = PenetrationTestGenerator(seed=42, dataset_version="v1.0")
    cases = gen.generate(count_per_category=100)
    assert len(cases) == 1200
    assert len({c.category for c in cases}) == len(CATEGORIES) == 12

    report = compute_diversity_report(cases, output_path=tmp_path / "div.json")
    assert report["total_cases"] == 1200
    assert report["unique_test_ids"] == 1200
    assert report["duplicate_test_ids"] == 0
    assert report["duplicate_prompts"] == 0
    assert report["template_family_leakage_count"] == 0
    for cat_id, stats in report["categories"].items():
        assert stats["count"] == 100
        assert stats["unique_subcategories"] == 10
        assert stats["unique_attack_patterns"] >= 10
        assert stats["mean_pairwise_tfidf_similarity"] < 0.35


def test_dataset_save_and_split_balance(tmp_path: Path) -> None:
    gen = PenetrationTestGenerator(seed=42)
    cases = gen.generate(count_per_category=100)
    info = gen.save_dataset(cases, base_dir=tmp_path)
    assert info["total_cases"] == 1200
    assert (tmp_path / "1_Penetration" / "02_Test_Cases" / "penetration_dataset_v1.0.json").exists()
    assert (tmp_path / "1_Penetration" / "01_Test_Categories" / "cybersecurity" / "test_cases.jsonl").exists()
    held_out = [c for c in cases if c.split == "held_out_eval"]
    assert len(held_out) == 300
    assert any(c.expected_behavior == "safe_completion" for c in held_out)
    assert any(c.expected_behavior == "refuse_and_redirect" for c in held_out)
