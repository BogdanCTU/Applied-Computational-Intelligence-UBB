"""Unit tests for TaskManager lifecycle, DAG validation, dependency execution, and progress reporting."""

from __future__ import annotations

import pytest

from agent.task_manager import (
    CyclicDependencyError,
    DependencyError,
    InMemoryTaskRepository,
    MissingDependencyError,
    SelfDependencyError,
    StepNotFoundError,
    TaskManager,
    TaskNotFoundError,
    TaskValidationError,
    validate_plan_dag,
)
from agent.task_models import (
    AgentTask,
    InvalidStateTransitionError,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)


def test_task_creation() -> None:
    tm = TaskManager()
    task = tm.create_task("Generate Q3 Revenue Report", metadata={"user_id": "analyst_1"})
    assert task.task_id.startswith("task_")
    assert task.user_request == "Generate Q3 Revenue Report"
    assert task.status == TaskStatus.PENDING
    assert task.metadata.get("user_id") == "analyst_1"

    # Verify retrieval
    retrieved = tm.get_task(task.task_id)
    assert retrieved.task_id == task.task_id
    assert retrieved.user_request == task.user_request


def test_task_creation_empty_request_rejected() -> None:
    tm = TaskManager()
    with pytest.raises(TaskValidationError):
        tm.create_task("")

    with pytest.raises(TaskValidationError):
        tm.create_task("   ")


def test_task_not_found_raises() -> None:
    tm = TaskManager()
    with pytest.raises(TaskNotFoundError):
        tm.get_task("nonexistent_task_id")


def test_plan_dag_validation_clean_linear() -> None:
    steps = [
        TaskStep(step_id="s1", name="Step 1", dependencies=[]),
        TaskStep(step_id="s2", name="Step 2", dependencies=["s1"]),
        TaskStep(step_id="s3", name="Step 3", dependencies=["s2"]),
    ]
    order = validate_plan_dag(steps)
    assert order == ["s1", "s2", "s3"]


def test_plan_dag_validation_branching() -> None:
    # A -> B, A -> C, (B, C) -> D
    steps = [
        TaskStep(step_id="A", name="Start"),
        TaskStep(step_id="B", name="Branch B", dependencies=["A"]),
        TaskStep(step_id="C", name="Branch C", dependencies=["A"]),
        TaskStep(step_id="D", name="Join", dependencies=["B", "C"]),
    ]
    order = validate_plan_dag(steps)
    assert order.index("A") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")


def test_plan_dag_self_dependency_rejected() -> None:
    steps = [
        TaskStep(step_id="s1", name="Step 1", dependencies=["s1"]),
    ]
    with pytest.raises(SelfDependencyError) as exc_info:
        validate_plan_dag(steps)
    assert "cannot depend on itself" in str(exc_info.value)


def test_plan_dag_missing_dependency_rejected() -> None:
    steps = [
        TaskStep(step_id="s1", name="Step 1", dependencies=["ghost_step"]),
    ]
    with pytest.raises(MissingDependencyError) as exc_info:
        validate_plan_dag(steps)
    assert "references unknown dependency 'ghost_step'" in str(exc_info.value)


def test_plan_dag_cyclic_dependency_rejected() -> None:
    # Cycle: s1 -> s2 -> s3 -> s1
    steps = [
        TaskStep(step_id="s1", name="Step 1", dependencies=["s3"]),
        TaskStep(step_id="s2", name="Step 2", dependencies=["s1"]),
        TaskStep(step_id="s3", name="Step 3", dependencies=["s2"]),
    ]
    with pytest.raises(CyclicDependencyError) as exc_info:
        validate_plan_dag(steps)
    assert "Cyclic dependency detected" in str(exc_info.value)


def test_plan_registration_and_initial_readiness() -> None:
    tm = TaskManager()
    task = tm.create_task("Monthly sales analysis")

    s1 = TaskStep(step_id="s1", name="Schema Inspection", dependencies=[])
    s2 = TaskStep(step_id="s2", name="SQL Execution", dependencies=["s1"])
    s3 = TaskStep(step_id="s3", name="PDF Generation", dependencies=["s2"])

    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3], rationale="Linear plan")
    updated_task = tm.register_plan(task.task_id, plan)

    assert updated_task.status == TaskStatus.PLANNING
    assert len(updated_task.steps) == 3
    # Step with 0 dependencies is promoted to READY immediately
    assert updated_task.get_step("s1").status == StepStatus.READY
    # Steps with dependencies remain PENDING
    assert updated_task.get_step("s2").status == StepStatus.PENDING
    assert updated_task.get_step("s3").status == StepStatus.PENDING

    ready_steps = tm.get_ready_steps(task.task_id)
    assert len(ready_steps) == 1
    assert ready_steps[0].step_id == "s1"


def test_step_execution_lifecycle_full_success() -> None:
    tm = TaskManager()
    task = tm.create_task("End-to-end report workflow")

    s1 = TaskStep(step_id="s1", name="Step 1", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Step 2", dependencies=["s1"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2])
    tm.register_plan(task.task_id, plan)

    # Cannot start s2 before s1 is completed
    with pytest.raises(DependencyError) as exc_info:
        tm.start_step(task.task_id, "s2")
    assert "dependency 's1' is not COMPLETED" in str(exc_info.value)

    # Start s1
    st1 = tm.start_step(task.task_id, "s1")
    assert st1.status == StepStatus.RUNNING
    curr_task = tm.get_task(task.task_id)
    assert curr_task.status == TaskStatus.RUNNING
    assert curr_task.current_step == "s1"

    # Complete s1
    st1_done = tm.complete_step(task.task_id, "s1", output_reference="dataset_schema")
    assert st1_done.status == StepStatus.COMPLETED
    assert st1_done.output_reference == "dataset_schema"
    curr_task = tm.get_task(task.task_id)
    assert curr_task.current_step is None

    # Now s2 should be READY
    ready = tm.get_ready_steps(task.task_id)
    assert len(ready) == 1 and ready[0].step_id == "s2"

    # Start and complete s2
    tm.start_step(task.task_id, "s2")
    tm.complete_step(task.task_id, "s2", output_reference="output.pdf")

    # All steps completed -> task transitions to COMPLETED automatically
    final_task = tm.get_task(task.task_id)
    assert final_task.status == TaskStatus.COMPLETED
    assert final_task.is_terminal

    summary = tm.get_progress_summary(task.task_id)
    assert summary["total_steps"] == 2
    assert summary["completed_steps"] == 2
    assert summary["percent_complete"] == 100.0


def test_step_failure_propagates_to_task() -> None:
    tm = TaskManager()
    task = tm.create_task("Failing workflow")

    s1 = TaskStep(step_id="s1", name="Step 1", dependencies=[])
    plan = TaskPlan(task_id=task.task_id, steps=[s1])
    tm.register_plan(task.task_id, plan)

    tm.start_step(task.task_id, "s1")
    failed_step = tm.fail_step(task.task_id, "s1", error="Database connection lost")
    assert failed_step.status == StepStatus.FAILED
    assert failed_step.error == "Database connection lost"

    t = tm.get_task(task.task_id)
    assert t.status == TaskStatus.FAILED
    assert "Database connection lost" in (t.error or "")

    summary = tm.get_progress_summary(task.task_id)
    assert summary["status"] == "FAILED"
    assert summary["failed_steps"] == 1
    assert summary["percent_complete"] == 0.0


def test_step_skipping_allows_downstream_execution_when_optional() -> None:
    tm = TaskManager()
    task = tm.create_task("Workflow with optional step")

    s1 = TaskStep(step_id="s1", name="Mandatory Prep", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Optional Profiling", dependencies=["s1"])
    s3 = TaskStep(step_id="s3", name="Final Report", dependencies=["s1"], optional_dependencies=["s2"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3])
    tm.register_plan(task.task_id, plan)

    tm.start_step(task.task_id, "s1")
    tm.complete_step(task.task_id, "s1")

    # Skip s2
    skipped = tm.skip_step(task.task_id, "s2", reason="Not requested by user")
    assert skipped.status == StepStatus.SKIPPED

    # Downstream s3 should now be READY because s2 is optional
    ready = tm.get_ready_steps(task.task_id)
    assert len(ready) == 1 and ready[0].step_id == "s3"

    tm.start_step(task.task_id, "s3")
    tm.complete_step(task.task_id, "s3")

    final_task = tm.get_task(task.task_id)
    assert final_task.status == TaskStatus.COMPLETED


def test_mandatory_dependency_skipped_blocks_downstream() -> None:
    tm = TaskManager()
    task = tm.create_task("Workflow with mandatory step skipped")

    s1 = TaskStep(step_id="s1", name="Step 1", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Step 2 (Mandatory)", dependencies=["s1"])
    s3 = TaskStep(step_id="s3", name="Step 3", dependencies=["s2"])  # mandatory dependency!
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3])
    tm.register_plan(task.task_id, plan)

    tm.start_step(task.task_id, "s1")
    tm.complete_step(task.task_id, "s1")

    # Skip mandatory prerequisite s2
    tm.skip_step(task.task_id, "s2", reason="Skipped accidentally")

    # Downstream s3 should NOT become READY
    ready = tm.get_ready_steps(task.task_id)
    assert len(ready) == 0

    # Attempting to start s3 raises DependencyError
    with pytest.raises(DependencyError) as exc_info:
        tm.start_step(task.task_id, "s3")
    assert "mandatory dependency 's2' is not COMPLETED" in str(exc_info.value)


def test_step_approval_flow() -> None:
    tm = TaskManager()
    task = tm.create_task("Workflow with SQL approval")

    s1 = TaskStep(step_id="s1", name="Execute Readonly SQL", dependencies=[])
    plan = TaskPlan(task_id=task.task_id, steps=[s1])
    tm.register_plan(task.task_id, plan)

    # Request approval
    st = tm.request_step_approval(task.task_id, "s1")
    assert st.status == StepStatus.WAITING_FOR_APPROVAL
    t = tm.get_task(task.task_id)
    assert t.status == TaskStatus.WAITING_FOR_APPROVAL
    assert t.current_step == "s1"

    # User approves
    approved = tm.approve_step(task.task_id, "s1")
    assert approved.status == StepStatus.RUNNING
    t2 = tm.get_task(task.task_id)
    assert t2.status == TaskStatus.RUNNING

    # Complete
    tm.complete_step(task.task_id, "s1")
    assert tm.get_task(task.task_id).status == TaskStatus.COMPLETED


def test_task_cancellation_cascades_to_steps() -> None:
    tm = TaskManager()
    task = tm.create_task("Long running pipeline")

    s1 = TaskStep(step_id="s1", name="Step 1", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Step 2", dependencies=["s1"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2])
    tm.register_plan(task.task_id, plan)

    tm.start_step(task.task_id, "s1")
    cancelled_task = tm.cancel_task(task.task_id, reason="User clicked stop")

    assert cancelled_task.status == TaskStatus.CANCELLED
    assert cancelled_task.error == "User clicked stop"
    assert cancelled_task.get_step("s1").status == StepStatus.CANCELLED
    assert cancelled_task.get_step("s2").status == StepStatus.CANCELLED

    summary = tm.get_progress_summary(task.task_id)
    assert summary["status"] == "CANCELLED"
    assert summary["cancelled_steps"] == 2


def test_in_memory_repository_methods() -> None:
    repo = InMemoryTaskRepository()
    t1 = AgentTask(task_id="t1", user_request="Task 1")
    t2 = AgentTask(task_id="t2", user_request="Task 2")

    repo.save(t1)
    repo.save(t2)

    assert repo.get("t1") is not None
    assert len(repo.list_all()) == 2

    assert repo.delete("t1") is True
    assert repo.get("t1") is None
    assert len(repo.list_all()) == 1

    repo.clear()
    assert len(repo.list_all()) == 0


def test_cannot_register_plan_on_terminal_task() -> None:
    tm = TaskManager()
    task = tm.create_task("Quick task")
    tm.cancel_task(task.task_id)

    plan = TaskPlan(task_id=task.task_id, steps=[TaskStep(step_id="s1", name="Step")])
    with pytest.raises(InvalidStateTransitionError):
        tm.register_plan(task.task_id, plan)


def test_step_not_found_raises() -> None:
    tm = TaskManager()
    task = tm.create_task("Empty task")
    with pytest.raises(StepNotFoundError):
        tm.start_step(task.task_id, "nonexistent_step")
