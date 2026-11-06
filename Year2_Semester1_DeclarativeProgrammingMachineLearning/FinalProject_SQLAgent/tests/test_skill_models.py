"""Unit tests for Skill models, safe YAML parser, token estimation, and metadata schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.skill_models import (
    CURRENT_SKILL_SYSTEM_VERSION,
    LoadedSkill,
    SkillCategory,
    SkillLoadResult,
    SkillMetadata,
    SkillValidationResult,
    estimate_tokens,
    safe_parse_yaml,
)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("a") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2
    assert estimate_tokens("12345678") == 2
    assert estimate_tokens("123456789") == 3
    # Check that longer text scales deterministically
    text = "x" * 400
    assert estimate_tokens(text) == 100


def test_safe_parse_yaml_empty_and_comments() -> None:
    assert safe_parse_yaml("") == {}
    assert safe_parse_yaml("   \n\n  ") == {}
    yaml_with_comments = """
    # This is a full comment line
    # Another comment
    """
    assert safe_parse_yaml(yaml_with_comments) == {}


def test_safe_parse_yaml_inline_comments() -> None:
    doc = """
    skill_id: my_skill # this is an inline comment
    version: 1.0.0 # semver comment
    count: 10 # integer comment
    is_enabled: true # boolean comment
    """
    data = safe_parse_yaml(doc)
    assert data["skill_id"] == "my_skill"
    assert data["version"] == "1.0.0"
    assert data["count"] == 10
    assert data["is_enabled"] is True


def test_safe_parse_yaml_scalars() -> None:
    doc = """
    # Metadata for skill
    skill_id: my_skill
    name: "Quoted Name"
    author: 'Single Quoted'
    is_enabled: true
    is_experimental: false
    count: 42
    ratio: 3.14
    empty_field: null
    """
    data = safe_parse_yaml(doc)
    assert data["skill_id"] == "my_skill"
    assert data["name"] == "Quoted Name"
    assert data["author"] == "Single Quoted"
    assert data["is_enabled"] is True
    assert data["is_experimental"] is False
    assert data["count"] == 42
    assert data["ratio"] == 3.14
    assert data["empty_field"] is None


def test_safe_parse_yaml_inline_lists() -> None:
    doc = """
    tags: [sql, analytics, metrics]
    numbers: [1, 2, 3]
    """
    data = safe_parse_yaml(doc)
    assert data["tags"] == ["sql", "analytics", "metrics"]
    assert data["numbers"] == [1, 2, 3]


def test_safe_parse_yaml_block_lists() -> None:
    doc = """
    skill_id: test_skill
    dependencies:
      - sql_generation
      - data_validation
    tags:
      - sqlite
      - queries
    """
    data = safe_parse_yaml(doc)
    assert data["skill_id"] == "test_skill"
    assert data["dependencies"] == ["sql_generation", "data_validation"]
    assert data["tags"] == ["sqlite", "queries"]


def test_safe_parse_yaml_json_fallback() -> None:
    json_doc = '{"skill_id": "json_skill", "name": "From JSON", "version": "1.0.0"}'
    data = safe_parse_yaml(json_doc)
    assert data["skill_id"] == "json_skill"
    assert data["name"] == "From JSON"
    assert data["version"] == "1.0.0"


def test_skill_metadata_valid() -> None:
    meta = SkillMetadata(
        skill_id="ecommerce_analysis",
        name="E-Commerce Analysis Skill",
        description="Analyzes revenue, cohorts, and customer trends.",
        version="1.0.0",
        category="data_analysis",
        tags=["ecommerce", "revenue"],
        supported_task_types=["analytics", "report"],
        dependencies=["sql_generation"],
    )
    assert meta.skill_id == "ecommerce_analysis"
    assert meta.name == "E-Commerce Analysis Skill"
    assert meta.version == "1.0.0"
    assert meta.category == "data_analysis"
    assert meta.is_enabled is True
    assert meta.min_system_version == CURRENT_SKILL_SYSTEM_VERSION
    assert meta.created_at is not None
    assert meta.updated_at is not None


def test_skill_metadata_invalid_id() -> None:
    # Contains uppercase letters
    with pytest.raises(ValidationError):
        SkillMetadata(
            skill_id="Ecommerce_Analysis",
            name="Analysis",
            description="Desc",
            version="1.0.0",
            category="data_analysis",
        )

    # Contains hyphens
    with pytest.raises(ValidationError):
        SkillMetadata(
            skill_id="ecommerce-analysis",
            name="Analysis",
            description="Desc",
            version="1.0.0",
            category="data_analysis",
        )

    # Contains spaces
    with pytest.raises(ValidationError):
        SkillMetadata(
            skill_id="ecommerce analysis",
            name="Analysis",
            description="Desc",
            version="1.0.0",
            category="data_analysis",
        )


def test_skill_metadata_semver_validation() -> None:
    valid_versions = ["0.1.0", "1.0.0", "2.15.30", "10.0.1"]
    for v in valid_versions:
        meta = SkillMetadata(
            skill_id="test_skill",
            name="Test",
            description="Desc",
            version=v,
            category="sql",
        )
        assert meta.version == v

    invalid_versions = ["1.0", "v1.0.0", "1.0.0-beta", "1.0.0.0", "latest", "alpha"]
    for inv in invalid_versions:
        with pytest.raises(ValidationError, match="Invalid semver version"):
            SkillMetadata(
                skill_id="test_skill",
                name="Test",
                description="Desc",
                version=inv,
                category="sql",
            )


def test_skill_metadata_system_version_check() -> None:
    # Future unsupported system version
    with pytest.raises(ValidationError, match="requires system version"):
        SkillMetadata(
            skill_id="test_skill",
            name="Test",
            description="Desc",
            version="1.0.0",
            category="sql",
            min_system_version=CURRENT_SKILL_SYSTEM_VERSION + 1,
        )


def test_loaded_skill_model() -> None:
    meta = SkillMetadata(
        skill_id="sql_generation",
        name="SQL Generation",
        description="Generates compliant SQLite queries.",
        version="1.0.0",
        category="sql",
    )
    content = "# SQL Generation Skill Guidelines\n\nAlways use parameterized queries."
    loaded = LoadedSkill(
        metadata=meta,
        content=content,
        file_path="/skills/sql/SKILL.md",
        char_count=len(content),
        estimated_tokens=estimate_tokens(content),
    )
    assert loaded.skill_id == "sql_generation"
    assert loaded.name == "SQL Generation"
    assert loaded.char_count == len(content)
    assert loaded.estimated_tokens > 0
    assert loaded.loaded_at is not None


def test_skill_load_result_model() -> None:
    meta = SkillMetadata(
        skill_id="sql_generation",
        name="SQL Generation",
        description="Generates compliant SQLite queries.",
        version="1.0.0",
        category="sql",
    )
    loaded = LoadedSkill(
        metadata=meta,
        content="content",
        file_path="/skills/sql/SKILL.md",
        char_count=7,
        estimated_tokens=2,
    )
    result = SkillLoadResult(
        loaded_skills=[loaded],
        excluded_skills=["ecommerce_analysis"],
        total_tokens=2,
        token_budget=1000,
        errors=[],
    )
    assert len(result.loaded_skills) == 1
    assert result.excluded_skills == ["ecommerce_analysis"]
    assert result.total_tokens == 2
    assert result.token_budget == 1000


def test_skill_validation_result_model() -> None:
    res = SkillValidationResult(
        is_valid=True,
        skill_id="sql_generation",
        errors=[],
        warnings=["Non-critical warning"],
        details={"version": "1.0.0"},
    )
    assert res.is_valid is True
    assert res.skill_id == "sql_generation"
    assert len(res.warnings) == 1

