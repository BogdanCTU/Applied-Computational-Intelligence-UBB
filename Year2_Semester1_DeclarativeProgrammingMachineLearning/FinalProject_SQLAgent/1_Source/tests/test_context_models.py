"""Unit tests for context models, priorities, execution stages, and build reports."""

from __future__ import annotations

import pytest

from agent.context_models import (
    AssembledContext,
    ContextBuildReport,
    ContextBudgetExceededError,
    ContextComponentBreakdown,
    ContextError,
    ContextSection,
    ExcludedSection,
    ExecutionStage,
    InvalidStageError,
    SectionPriority,
)


def test_execution_stage_enum_values() -> None:
    expected_stages = {
        "REQUEST_PLANNING",
        "SCHEMA_DISCOVERY",
        "SQL_GENERATION",
        "SQL_VALIDATION",
        "DATA_ANALYSIS",
        "CHART_PLANNING",
        "REPORT_GENERATION",
        "FINAL_RESPONSE",
    }
    actual_stages = {stage.value for stage in ExecutionStage}
    assert actual_stages == expected_stages


def test_section_priority_ordering() -> None:
    assert SectionPriority.MANDATORY.value > SectionPriority.HIGH.value
    assert SectionPriority.HIGH.value > SectionPriority.MEDIUM.value
    assert SectionPriority.MEDIUM.value > SectionPriority.LOW.value


def test_context_section_creation() -> None:
    sec = ContextSection(
        name="test_sec",
        content="Some test content",
        priority=SectionPriority.HIGH,
        is_mandatory=False,
        category="skills",
        estimated_tokens=5,
    )
    assert sec.name == "test_sec"
    assert sec.content == "Some test content"
    assert sec.priority == SectionPriority.HIGH
    assert not sec.is_mandatory
    assert sec.category == "skills"
    assert sec.estimated_tokens == 5


def test_excluded_section_creation() -> None:
    exc = ExcludedSection(
        name="optional_skill",
        category="skills",
        priority=SectionPriority.LOW,
        estimated_tokens=120,
        reason="Budget exhausted",
    )
    assert exc.name == "optional_skill"
    assert exc.priority == SectionPriority.LOW
    assert exc.estimated_tokens == 120
    assert "Budget exhausted" in exc.reason


def test_context_component_breakdown() -> None:
    breakdown = ContextComponentBreakdown(
        system_instructions=100,
        skills=200,
        database_schema=150,
        user_request=50,
    )
    assert breakdown.total() == 500
    d = breakdown.to_dict()
    assert d["system_instructions"] == 100
    assert d["skills"] == 200
    assert d["database_schema"] == 150
    assert d["user_request"] == 50
    assert "other" not in d  # 0 values excluded from to_dict()


def test_context_build_report_summary_text() -> None:
    report = ContextBuildReport(
        stage=ExecutionStage.SQL_GENERATION,
        num_ctx=8192,
        reserved_output_tokens=1024,
        safety_margin_tokens=256,
        available_input_tokens=6912,
        estimated_input_tokens=2450,
        remaining_tokens=4462,
        component_breakdown={
            "system_instructions": 850,
            "skills": 620,
            "database_schema": 480,
            "user_request": 500,
        },
        included_sections=["system_instructions", "stage_instructions", "skill_sql_generation", "user_request"],
        excluded_sections=[
            ExcludedSection(
                name="optional_facts",
                category="semantic_memory",
                priority=SectionPriority.LOW,
                estimated_tokens=300,
                reason="Budget tight",
            )
        ],
        warnings=["Low remaining space"],
    )

    summary = report.summary_text()
    assert "Context Assembly Report" in summary
    assert "SQL_GENERATION" in summary
    assert "8,192" in summary
    assert "6,912" in summary
    assert "2,450" in summary
    assert "system_instructions: 850" in summary
    assert "Included Sections:" in summary
    assert "optional_facts" in summary
    assert "Low remaining space" in summary


def test_assembled_context_properties() -> None:
    report = ContextBuildReport(
        stage=ExecutionStage.DATA_ANALYSIS,
        num_ctx=4096,
        reserved_output_tokens=512,
        safety_margin_tokens=128,
        available_input_tokens=3456,
        estimated_input_tokens=800,
        remaining_tokens=2656,
    )
    ctx = AssembledContext(
        stage=ExecutionStage.DATA_ANALYSIS,
        system_prompt="You are an analyst.",
        user_prompt="Analyze revenue trends.",
        messages=[
            {"role": "system", "content": "You are an analyst."},
            {"role": "user", "content": "Analyze revenue trends."},
        ],
        report=report,
    )
    assert ctx.stage == ExecutionStage.DATA_ANALYSIS
    assert ctx.estimated_input_tokens == 800
    assert len(ctx.messages) == 2
    assert ctx.messages[0]["role"] == "system"
    assert ctx.messages[1]["role"] == "user"


def test_exception_hierarchy() -> None:
    assert issubclass(ContextBudgetExceededError, ContextError)
    assert issubclass(InvalidStageError, ContextError)

