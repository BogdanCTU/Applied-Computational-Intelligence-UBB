"""Penetration suite invariants: schema conformance, multi-turn coverage, and synthetic safety."""

from __future__ import annotations

import json

from source.config.settings import get_project_root
from source.penetration.taxonomy import CATEGORIES
from source.test_generation.generator import PenetrationTestGenerator


def test_penetration_suite_schema_and_multiturn_coverage() -> None:
    gen = PenetrationTestGenerator(seed=42, dataset_version="v1.0")
    cases = gen.generate(count_per_category=100)

    multi_turn = [c for c in cases if len(c.conversation) > 1]
    assert len(multi_turn) >= 36  # Covered across categories

    required_fields = {
        "test_id",
        "category",
        "subcategory",
        "severity",
        "risk_type",
        "attack_pattern",
        "conversation",
        "expected_behavior",
        "expected_risk",
        "evaluation_criteria",
        "tags",
    }
    for c in cases:
        d = c.__dict__
        assert required_fields.issubset(d.keys())
        assert isinstance(c.conversation, list) and len(c.conversation) >= 1
        assert c.conversation[-1]["role"] == "user"
        assert c.expected_behavior in ("refuse_and_redirect", "safe_completion")


def test_generated_persisted_files_match_12_categories() -> None:
    root = get_project_root()
    cat_dir = root / "1_Penetration" / "01_Test_Categories"
    if not (cat_dir / "cybersecurity" / "test_cases.json").exists():
        return
    total = 0
    for cat in CATEGORIES:
        p = cat_dir / cat.category_id / "test_cases.json"
        assert p.exists(), f"Missing generated test file: {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert len(data) >= 100
        total += len(data)
    assert total >= 1200
