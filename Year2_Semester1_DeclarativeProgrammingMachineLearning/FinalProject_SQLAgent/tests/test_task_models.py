"""Unit tests for Task and Step models, enums, lifecycle transitions, and serialization."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.task_models import (
    AgentTask,
    InvalidStateTransitionError,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)


def test_task_creation_valid() -> None:
    task = AgentTask(user_request="Generate monthly sales overview")
    assert task.task_id.startswith("task_")
    assert task.user_request == "Generate monthly sales overview"
    assert task.status == TaskStatus.PENDING
    assert task.current_step is None
    assert task.steps == []
    assert task.plan is None
    assert task.error is None
    assert not task.is_terminal
    assert task.created_at is not None
    assert task.updated_at is not None


def test_task_creation_invalid() -> None:
    with pytest.raises(ValidationError):
        AgentTask(user_request="")  # min_length=1

    with pytest.raises(ValidationError):
        AgentTask.model_validate({"user_request": None})


def test_task_state_transitions() -> None:
    task = AgentTask(user_request="Analyze customer cohorts")
    assert task.status == TaskStatus.PENDING

    # Valid path: PENDING -> PLANNING -> RUNNING -> WAITING_FOR_APPROVAL -> RUNNING -> COMPLETED
    task.transition_to(TaskStatus.PLANNING)
    assert task.status == TaskStatus.PLANNING

    task.transition_to(TaskStatus.RUNNING)
    assert task.status == TaskStatus.RUNNING

    task.transition_to(TaskStatus.WAITING_FOR_APPROVAL)
    assert task.status == TaskStatus.WAITING_FOR_APPROVAL

    task.transition_to(TaskStatus.RUNNING)
    assert task.status == TaskStatus.RUNNING

    task.transition_to(TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED
    assert task.is_terminal

    # Invalid: transition out of terminal state
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        task.transition_to(TaskStatus.RUNNING)
    assert "Cannot transition task" in str(exc_info.value)

    # Idempotent transition to same status succeeds without error
    task.transition_to(TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED


def test_task_invalid_transitions() -> None:
    task = AgentTask(user_request="Inspect returns")
    # PENDING cannot go directly to WAITING_FOR_APPROVAL
    with pytest.raises(InvalidStateTransitionError):
        task.transition_to(TaskStatus.WAITING_FOR_APPROVAL)

    # PENDING -> CANCELLED
    task.transition_to(TaskStatus.CANCELLED, error="User aborted")
    assert task.status == TaskStatus.CANCELLED
    assert task.error == "User aborted"
    assert task.is_terminal

    # CANCELLED cannot transition to RUNNING
    with pytest.raises(InvalidStateTransitionError):
        task.transition_to(TaskStatus.RUNNING)


def test_step_creation_and_attributes() -> None:
    step = TaskStep(
        name="Inspect Schema",
        description="Extract table catalog and columns",
        required_skill="sql/schema_analysis",
        required_tools=["inspect_database_schema"],
        dependencies=[],
        metadata={"priority": 1},
    )
    assert step.step_id.startswith("step_")
    assert step.name == "Inspect Schema"
    assert step.status == StepStatus.PENDING
    assert step.required_skill == "sql/schema_analysis"
    assert step.required_tools == ["inspect_database_schema"]
    assert step.dependencies == []
    assert step.output_reference is None
    assert not step.is_terminal


def test_step_state_transitions() -> None:
    step = TaskStep(name="Execute SQL")
    assert step.status == StepStatus.PENDING

    # Valid progression: PENDING -> READY -> RUNNING -> WAITING_FOR_APPROVAL -> RUNNING -> COMPLETED
    step.transition_to(StepStatus.READY)
    assert step.status == StepStatus.READY

    step.transition_to(StepStatus.RUNNING)
    assert step.status == StepStatus.RUNNING

    step.transition_to(StepStatus.WAITING_FOR_APPROVAL)
    assert step.status == StepStatus.WAITING_FOR_APPROVAL

    step.transition_to(StepStatus.RUNNING)
    assert step.status == StepStatus.RUNNING

    step.transition_to(StepStatus.COMPLETED, output_reference="dataset_orders_v1")
    assert step.status == StepStatus.COMPLETED
    assert step.output_reference == "dataset_orders_v1"
    assert step.is_terminal

    # Invalid: transition out of terminal state
    with pytest.raises(InvalidStateTransitionError):
        step.transition_to(StepStatus.RUNNING)

    # Idempotent: transitioning to COMPLETED again is allowed
    step.transition_to(StepStatus.COMPLETED)
    assert step.status == StepStatus.COMPLETED


def test_step_invalid_transitions() -> None:
    step = TaskStep(name="Generate PDF")
    # PENDING cannot jump directly to RUNNING without becoming READY
    with pytest.raises(InvalidStateTransitionError):
        step.transition_to(StepStatus.RUNNING)

    # PENDING -> SKIPPED
    step.transition_to(StepStatus.SKIPPED, error="Not needed")
    assert step.status == StepStatus.SKIPPED
    assert step.error == "Not needed"
    assert step.is_terminal

    # SKIPPED cannot transition to READY
    with pytest.raises(InvalidStateTransitionError):
        step.transition_to(StepStatus.READY)


def test_step_failure_transition() -> None:
    step = TaskStep(name="Validate SQL")
    step.transition_to(StepStatus.READY)
    step.transition_to(StepStatus.RUNNING)
    step.transition_to(StepStatus.FAILED, error="Syntax error near WHERE")
    assert step.status == StepStatus.FAILED
    assert step.error == "Syntax error near WHERE"
    assert step.is_terminal


def test_task_plan_duplicate_step_id_rejected() -> None:
    step1 = TaskStep(step_id="step_a", name="Step A")
    step2 = TaskStep(step_id="step_a", name="Duplicate Step A")
    with pytest.raises(ValidationError) as exc_info:
        TaskPlan(task_id="task_1", steps=[step1, step2])
    assert "Duplicate step_id detected in plan" in str(exc_info.value)


def test_task_and_step_serialization_roundtrip() -> None:
    step1 = TaskStep(
        step_id="s1",
        name="Inspect Schema",
        required_tools=["inspect_database_schema"],
        status=StepStatus.COMPLETED,
        output_reference="ref_schema",
    )
    step2 = TaskStep(
        step_id="s2",
        name="Generate Report",
        required_tools=["generate_pdf_report"],
        dependencies=["s1"],
        status=StepStatus.PENDING,
    )
    plan = TaskPlan(
        plan_id="plan_1",
        task_id="task_1",
        steps=[step1, step2],
        rationale="Two-step pipeline",
    )
    task = AgentTask(
        task_id="task_1",
        user_request="Create summary PDF",
        status=TaskStatus.RUNNING,
        current_step="s2",
        steps=[step1, step2],
        plan=plan,
        metadata={"client": "desktop"},
    )

    # Serialize to dictionary
    task_dict = task.to_dict()
    assert task_dict["task_id"] == "task_1"
    assert task_dict["status"] == "RUNNING"
    assert len(task_dict["steps"]) == 2
    assert task_dict["steps"][0]["status"] == "COMPLETED"
    assert task_dict["plan"]["rationale"] == "Two-step pipeline"

    # Deserialize back to AgentTask
    restored = AgentTask.from_dict(task_dict)
    assert restored.task_id == task.task_id
    assert restored.status == TaskStatus.RUNNING
    assert restored.current_step == "s2"
    assert len(restored.steps) == 2
    assert restored.steps[0].status == StepStatus.COMPLETED
    assert restored.steps[1].status == StepStatus.PENDING
    assert restored.steps[1].dependencies == ["s1"]
    assert restored.plan is not None
    assert restored.plan.plan_id == "plan_1"


def test_status_coercion_from_string() -> None:
    # Test case-insensitive string coercion
    step = TaskStep(name="Test", status="ready")  # type: ignore[arg-type]
    assert step.status == StepStatus.READY

    step2 = TaskStep(name="Test", status="FAILED")  # type: ignore[arg-type]
    assert step2.status == StepStatus.FAILED

    with pytest.raises(ValidationError):
        TaskStep(name="Test", status="INVALID_STATUS")  # type: ignore[arg-type]

