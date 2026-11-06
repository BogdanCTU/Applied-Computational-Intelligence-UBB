"""Unit tests for SkillManager discovery, loading, token budgeting, and repository synchronization."""

from __future__ import annotations

from pathlib import Path
import pytest

from agent.skill_manager import (
    SkillError,
    SkillManager,
    SkillNotFoundError,
    SkillValidationError,
)
from memory.repository import SQLiteMemoryRepository


def test_discover_default_skills() -> None:
    manager = SkillManager()
    skills = manager.discover_skills()
    skill_ids = [s.skill_id for s in skills]

    assert "sql_generation" in skill_ids
    assert "ecommerce_analysis" in skill_ids
    assert "report_design" in skill_ids
    assert "data_validation" in skill_ids

    # Verify alphabetical / deterministic ordering of discovered subdirectories
    assert len(skills) >= 4


def test_get_skill_metadata() -> None:
    manager = SkillManager()
    sql_meta = manager.get_skill_metadata("sql_generation")
    assert sql_meta.skill_id == "sql_generation"
    assert sql_meta.category == "sql"
    assert sql_meta.version == "1.0.0"
    assert "sqlite" in sql_meta.tags

    with pytest.raises(SkillNotFoundError):
        manager.get_skill_metadata("non_existent_skill_id")


def test_list_skills_filtering() -> None:
    manager = SkillManager()
    all_skills = manager.list_skills()
    assert len(all_skills) >= 4

    # Filter by category
    sql_skills = manager.list_skills(category="sql")
    assert len(sql_skills) == 1
    assert sql_skills[0].skill_id == "sql_generation"

    reporting_skills = manager.list_skills(category="reporting")
    assert len(reporting_skills) == 1
    assert reporting_skills[0].skill_id == "report_design"

    # Filter nonexistent category
    assert manager.list_skills(category="unknown_category") == []


def test_load_single_skill() -> None:
    manager = SkillManager()
    loaded = manager.load_skill("sql_generation")

    assert loaded.skill_id == "sql_generation"
    assert "SQL Generation" in loaded.name
    assert len(loaded.content) > 0
    assert "SELECT" in loaded.content or "SQLite" in loaded.content
    assert loaded.estimated_tokens > 0
    assert loaded.char_count == len(loaded.content)


def test_load_skills_respects_token_budget() -> None:
    manager = SkillManager()

    # Load with infinite budget
    full_result = manager.load_skills(["ecommerce_analysis"])
    # ecommerce_analysis depends on sql_generation -> both loaded
    loaded_ids = [s.skill_id for s in full_result.loaded_skills]
    assert loaded_ids == ["sql_generation", "ecommerce_analysis"]
    assert full_result.excluded_skills == []
    assert full_result.total_tokens > 0

    # Load with constrained budget that allows only the first skill (sql_generation)
    sql_skill = manager.load_skill("sql_generation")
    sql_tokens = sql_skill.estimated_tokens

    # Set budget exactly to sql_tokens
    tight_result = manager.load_skills(["ecommerce_analysis"], max_total_tokens=sql_tokens)
    assert len(tight_result.loaded_skills) == 1
    assert tight_result.loaded_skills[0].skill_id == "sql_generation"
    assert "ecommerce_analysis" in tight_result.excluded_skills
    # Verify no partial truncation occurred
    assert tight_result.loaded_skills[0].content == sql_skill.content

    # Load with budget 0 -> all excluded
    zero_result = manager.load_skills(["sql_generation"], max_total_tokens=0)
    assert len(zero_result.loaded_skills) == 0
    assert "sql_generation" in zero_result.excluded_skills


def test_enable_disable_skill_workflow() -> None:
    manager = SkillManager()
    meta = manager.get_skill_metadata("ecommerce_analysis")
    assert meta.is_enabled is True

    # Disable skill
    manager.disable_skill("ecommerce_analysis")
    assert manager.get_skill_metadata("ecommerce_analysis").is_enabled is False

    # Excluded from enabled_only listing
    enabled_list = manager.list_skills(enabled_only=True)
    assert "ecommerce_analysis" not in [s.skill_id for s in enabled_list]

    # Still in all listing
    all_list = manager.list_skills(enabled_only=False)
    assert "ecommerce_analysis" in [s.skill_id for s in all_list]

    # Loading disabled skill directly raises error
    with pytest.raises(SkillError, match="Cannot load disabled skill"):
        manager.load_skill("ecommerce_analysis")

    # Re-enable
    manager.enable_skill("ecommerce_analysis")
    assert manager.get_skill_metadata("ecommerce_analysis").is_enabled is True
    reloaded = manager.load_skill("ecommerce_analysis")
    assert reloaded.skill_id == "ecommerce_analysis"


def test_load_skills_cascades_exclusion_when_prerequisite_excluded() -> None:
    manager = SkillManager()
    sql_skill = manager.load_skill("sql_generation")
    ecom_skill = manager.load_skill("ecommerce_analysis")

    # Set budget lower than sql_skill, even if large enough for ecom_skill alone
    budget = min(sql_skill.estimated_tokens - 1, ecom_skill.estimated_tokens + 50)
    result = manager.load_skills(["ecommerce_analysis"], max_total_tokens=budget)

    # Both must be excluded: sql_generation due to budget, and ecommerce_analysis due to missing prerequisite
    assert "sql_generation" in result.excluded_skills
    assert "ecommerce_analysis" in result.excluded_skills
    assert len(result.loaded_skills) == 0


def test_sqlite_repository_persistence_across_restarts(tmp_path: Path) -> None:
    db_file = tmp_path / "agent_memory_restart_test.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    # Initial manager disables a skill
    manager1 = SkillManager(repository=repo, auto_sync_repo=True)
    manager1.disable_skill("data_validation")
    assert manager1.get_skill_metadata("data_validation").is_enabled is False

    # Second manager simulates application restart
    manager2 = SkillManager(repository=repo, auto_sync_repo=True)
    assert manager2.get_skill_metadata("data_validation").is_enabled is False
    assert "data_validation" not in [s.skill_id for s in manager2.list_skills(enabled_only=True)]


def test_sqlite_repository_synchronization(tmp_path: Path) -> None:
    db_file = tmp_path / "agent_memory_test.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    manager = SkillManager(repository=repo, auto_sync_repo=True)

    # Verify skills were registered in SQLite repository
    db_skills = repo.get_registered_skills(enabled_only=False)
    db_skill_ids = [s["skill_id"] for s in db_skills]
    assert "sql_generation" in db_skill_ids
    assert "ecommerce_analysis" in db_skill_ids

    # Disable skill in manager and verify repository updated
    manager.disable_skill("sql_generation")
    db_skill = repo.get_registered_skill("sql_generation")
    assert db_skill is not None
    assert db_skill["is_enabled"] == 0

    # Enable skill and verify repository updated
    manager.enable_skill("sql_generation")
    db_skill = repo.get_registered_skill("sql_generation")
    assert db_skill is not None
    assert db_skill["is_enabled"] == 1


def test_validate_skill_integrity() -> None:
    manager = SkillManager()
    # Check that all default skills are valid
    for sid in ["sql_generation", "ecommerce_analysis", "report_design", "data_validation"]:
        res = manager.validate_skill(sid)
        assert res.is_valid is True
        assert res.errors == []
        assert res.skill_id == sid


def test_validate_nonexistent_skill() -> None:
    manager = SkillManager()
    res = manager.validate_skill("ghost_skill")
    assert res.is_valid is False
    assert any("not found" in err.lower() for err in res.errors)

