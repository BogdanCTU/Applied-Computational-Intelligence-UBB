"""Unit tests for ContextBuilder stage construction, token budgeting, and component integration."""

from __future__ import annotations

import pytest

from agent.checkpoint_models import CheckpointType, TaskCheckpoint
from agent.context_builder import ContextBuilder
from agent.context_models import (
    ContextBudgetExceededError,
    ContextSection,
    ExecutionStage,
    InvalidStageError,
    SectionPriority,
)
from agent.skill_manager import SkillManager
from agent.task_models import AgentTask, TaskPlan, TaskStatus, TaskStep


def test_builder_initialization_defaults() -> None:
    builder = ContextBuilder()
    assert builder.num_ctx >= 2048
    assert builder.reserved_output_tokens == 1024
    assert builder.safety_margin_tokens == 256


def test_invalid_stage_handling() -> None:
    builder = ContextBuilder()
    with pytest.raises(InvalidStageError, match="Unknown execution stage"):
        builder.build("INVALID_STAGE_NAME")


def test_request_planning_stage_context() -> None:
    builder = ContextBuilder()
    ctx = builder.build(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Summarize quarterly revenue by product category",
    )
    assert ctx.stage == ExecutionStage.REQUEST_PLANNING
    assert "TASK PLANNING STAGE" in ctx.system_prompt
    assert "Summarize quarterly revenue by product category" in ctx.user_prompt
    assert len(ctx.messages) == 2
    assert ctx.report.estimated_input_tokens > 0
    assert ctx.report.remaining_tokens > 0


def test_sql_generation_stage_with_skill_manager() -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(skill_manager=skill_mgr)

    dummy_schema = "Table orders (order_id INT, customer_id INT, total_amount REAL)"
    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Find top 5 customers by spend",
        schema=dummy_schema,
    )

    # Should contain system instructions, SQL stage instructions, SQL skill, and schema
    assert "SQL GENERATION STAGE" in ctx.system_prompt
    assert "SQL Generation & Schema Analysis" in ctx.system_prompt
    assert "Table orders" in ctx.system_prompt
    assert "Find top 5 customers by spend" in ctx.user_prompt
    assert "skill_sql_generation" in ctx.report.included_sections
    assert "database_schema" in ctx.report.included_sections


def test_sql_validation_stage_includes_proposed_sql() -> None:
    builder = ContextBuilder()
    proposed = "SELECT customer_id, SUM(total_amount) FROM orders GROUP BY customer_id;"
    ctx = builder.build(
        ExecutionStage.SQL_VALIDATION,
        user_request="Check if query is safe",
        proposed_sql=proposed,
    )
    assert "SQL VALIDATION STAGE" in ctx.system_prompt
    assert proposed in ctx.user_prompt or proposed in ctx.system_prompt
    assert "proposed_sql" in ctx.report.included_sections


def test_data_analysis_stage_with_dataset_summary() -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(skill_manager=skill_mgr)
    dataset = {
        "columns": ["category", "revenue"],
        "row_count": 10,
        "sample": [["Electronics", 45000.0]],
    }
    ctx = builder.build(
        ExecutionStage.DATA_ANALYSIS,
        user_request="Analyze revenue distribution across categories",
        dataset_summary=dataset,
    )
    assert "DATA ANALYSIS STAGE" in ctx.system_prompt
    assert "Electronics" in ctx.user_prompt
    assert "skill_ecommerce_analysis" in ctx.report.included_sections


def test_report_generation_stage_skills() -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(skill_manager=skill_mgr)
    ctx = builder.build(
        ExecutionStage.REPORT_GENERATION,
        user_request="Generate monthly PDF report",
    )
    assert "REPORT GENERATION STAGE" in ctx.system_prompt
    assert "skill_report_design" in ctx.report.included_sections
    assert "skill_data_validation" in ctx.report.included_sections


def test_task_and_active_step_state_inclusion() -> None:
    builder = ContextBuilder()
    task = AgentTask(
        task_id="task_123",
        user_request="Produce sales report",
        status=TaskStatus.RUNNING,
    )
    step = TaskStep(
        step_id="step_1",
        name="Extract Sales",
        description="Run analytical SQL query for sales data",
        required_tools=["execute_readonly_sql"],
    )

    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        task=task,
        active_step=step,
    )
    assert "task_123" in ctx.user_prompt
    assert "Extract Sales" in ctx.user_prompt
    assert "execute_readonly_sql" in ctx.user_prompt
    assert "task_state" in ctx.report.included_sections


def test_checkpoint_state_inclusion() -> None:
    builder = ContextBuilder()
    chk = TaskCheckpoint(
        checkpoint_id="chk_abc123",
        task_id="task_123",
        sequence_number=3,
        checkpoint_type=CheckpointType.STEP_COMPLETED,
        task_status=TaskStatus.RUNNING,
        completed_step_ids=["step_1"],
        pending_step_ids=["step_2"],
        artifact_ids=["art_report_1"],
    )
    ctx = builder.build(
        ExecutionStage.DATA_ANALYSIS,
        checkpoint=chk,
        user_request="Next step analysis",
    )
    assert "chk_abc123" in ctx.user_prompt
    assert "checkpoint_state" in ctx.report.included_sections


def test_tool_results_formatting() -> None:
    builder = ContextBuilder()
    results = [
        {"tool_name": "execute_readonly_sql", "status": "success", "result": "100 rows returned"},
        {"tool_name": "inspect_database_schema", "status": "success", "result": "7 tables discovered"},
    ]
    ctx = builder.build(
        ExecutionStage.DATA_ANALYSIS,
        user_request="Examine outputs",
        tool_results=results,
    )
    assert '<tool_result name="execute_readonly_sql" status="success">' in ctx.user_prompt
    assert "100 rows returned" in ctx.user_prompt
    assert "tool_results" in ctx.report.included_sections


def test_budget_exceeded_for_mandatory_content() -> None:
    # A tiny context budget where mandatory system + user instructions cannot fit
    builder = ContextBuilder(
        num_ctx=200,
        reserved_output_tokens=100,
        safety_margin_tokens=50,
    )
    # Available input budget = 200 - 100 - 50 = 50 tokens
    # Mandatory system instructions take ~100 tokens -> should raise ContextBudgetExceededError
    with pytest.raises(ContextBudgetExceededError, match="Mandatory context sections require"):
        builder.build(
            ExecutionStage.REQUEST_PLANNING,
            user_request="A standard user request that takes tokens",
        )


def test_budget_prioritization_excludes_low_priority_first() -> None:
    # Budget tailored so mandatory fits, high fits, but low is excluded
    builder = ContextBuilder(
        num_ctx=1500,
        reserved_output_tokens=300,
        safety_margin_tokens=100,
    )
    # Available = 1100 tokens

    high_section = ContextSection(
        name="high_priority_schema",
        content="X" * 1600,  # ~400 tokens
        priority=SectionPriority.HIGH,
        is_mandatory=False,
        category="database_schema",
    )
    low_section = ContextSection(
        name="low_priority_notes",
        content="Y" * 3200,  # ~800 tokens
        priority=SectionPriority.LOW,
        is_mandatory=False,
        category="episodic_memory",
    )

    ctx = builder.build(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Plan work",
        custom_sections=[high_section, low_section],
    )

    # High priority section should be admitted, low priority should be excluded
    assert "high_priority_schema" in ctx.report.included_sections
    assert any(exc.name == "low_priority_notes" for exc in ctx.report.excluded_sections)

    # Check reason in excluded section
    excluded_note = next(exc for exc in ctx.report.excluded_sections if exc.name == "low_priority_notes")
    assert "Token budget exceeded" in excluded_note.reason


def test_build_messages_and_build_prompt_helpers() -> None:
    builder = ContextBuilder()
    messages = builder.build_messages(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Generate plan",
    )
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    prompt_str = builder.build_prompt(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Generate plan",
    )
    assert isinstance(prompt_str, str)
    assert "TASK PLANNING STAGE" in prompt_str
    assert "Generate plan" in prompt_str

