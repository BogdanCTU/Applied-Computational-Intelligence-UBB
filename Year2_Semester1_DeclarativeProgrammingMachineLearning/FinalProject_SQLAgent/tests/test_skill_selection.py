"""Unit tests for deterministic skill selection and dependency resolution ordering."""

from __future__ import annotations

import pytest

from agent.skill_manager import SkillManager


def test_select_skills_for_sql_query() -> None:
    manager = SkillManager()
    selected = manager.select_skills(task_type="sql_query")
    # Should select sql_generation directly with no additional dependencies
    assert selected == ["sql_generation"]


def test_select_skills_for_analytics() -> None:
    manager = SkillManager()
    selected = manager.select_skills(task_type="analytics")
    # ecommerce_analysis requires sql_generation
    assert "sql_generation" in selected
    assert "ecommerce_analysis" in selected
    # Dependency must precede dependent skill
    assert selected.index("sql_generation") < selected.index("ecommerce_analysis")


def test_select_skills_for_report() -> None:
    manager = SkillManager()
    selected = manager.select_skills(task_type="report")
    # report matches report_design and ecommerce_analysis
    # dependencies: data_validation and sql_generation
    assert "sql_generation" in selected
    assert "data_validation" in selected
    assert "report_design" in selected
    assert "ecommerce_analysis" in selected

    # Check topological ordering
    assert selected.index("sql_generation") < selected.index("data_validation")
    assert selected.index("data_validation") < selected.index("report_design")
    assert selected.index("sql_generation") < selected.index("ecommerce_analysis")


def test_select_skills_by_capabilities() -> None:
    manager = SkillManager()
    selected = manager.select_skills(required_capabilities=["dataset_validation"])
    assert selected == ["sql_generation", "data_validation"]

    selected_report = manager.select_skills(required_capabilities=["report_generation"])
    assert "report_design" in selected_report
    assert "data_validation" in selected_report
    assert "sql_generation" in selected_report
    assert selected_report.index("sql_generation") < selected_report.index("data_validation")
    assert selected_report.index("data_validation") < selected_report.index("report_design")


def test_select_skills_by_tags() -> None:
    manager = SkillManager()
    selected = manager.select_skills(tags=["reconciliation"])
    assert selected == ["sql_generation", "data_validation"]

    selected_kpi = manager.select_skills(tags=["kpi"])
    assert selected_kpi == ["sql_generation", "ecommerce_analysis"]


def test_select_skills_explicit_ids() -> None:
    manager = SkillManager()
    selected = manager.select_skills(explicit_skill_ids=["data_validation"])
    assert selected == ["sql_generation", "data_validation"]


def test_select_skills_disabled_skill_excluded() -> None:
    manager = SkillManager()
    manager.disable_skill("ecommerce_analysis")

    selected = manager.select_skills(task_type="analytics")
    # Disabled skill should not be selected
    assert "ecommerce_analysis" not in selected

    # Re-enable
    manager.enable_skill("ecommerce_analysis")
    selected_after = manager.select_skills(task_type="analytics")
    assert "ecommerce_analysis" in selected_after


def test_select_skills_empty_for_unmatched_criteria() -> None:
    manager = SkillManager()
    assert manager.select_skills(task_type="completely_unknown_task_type") == []
    assert manager.select_skills() == []
    assert manager.select_skills(tags=["nonexistent_tag_xyz"]) == []


def test_dependency_resolution_deterministic_order() -> None:
    manager = SkillManager()
    res1 = manager.resolve_dependencies(["report_design", "ecommerce_analysis"])
    res2 = manager.resolve_dependencies(["ecommerce_analysis", "report_design"])
    # Both calls must resolve to the identical deterministic order
    assert res1 == res2
    assert res1[0] == "sql_generation"
