"""Integration tests for TaskManager backed by persistent SQLiteMemoryRepository."""

from __future__ import annotations

from pathlib import Path
import pytest

from agent.task_manager import (
    DependencyError,
    TaskManager,
    TaskNotFoundError,
)
from agent.task_models import (
    AgentTask,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from memory.repository import SQLiteMemoryRepository


def test_task_manager_sqlite_full_lifecycle(tmp_path: Path) -> None:
    db_file = tmp_path / "tm_lifecycle.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    tm = TaskManager(repository=repo)

    # 1. Create task
    task = tm.create_task("Generate Q4 executive overview", metadata={"client": "web"})
    assert task.status == TaskStatus.PENDING

    # 2. Register plan
    s1 = TaskStep(step_id="s1", name="Inspect Schema", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Execute Readonly SQL", dependencies=["s1"])
    s3 = TaskStep(step_id="s3", name="Compose PDF", dependencies=["s2"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3], rationale="3-stage pipeline")
    tm.register_plan(task.task_id, plan)

    # Verify state on disk
    loaded = repo.get(task.task_id)
    assert loaded is not None
    assert loaded.status == TaskStatus.PLANNING
    assert len(loaded.steps) == 3
    assert loaded.get_step("s1").status == StepStatus.READY

    # 3. Start task & step 1
    tm.start_task(task.task_id)
    tm.start_step(task.task_id, "s1")
    tm.complete_step(task.task_id, "s1", output_reference="schema_cached")

    # Verify step 2 is promoted to READY on disk
    ready = tm.get_ready_steps(task.task_id)
    assert len(ready) == 1 and ready[0].step_id == "s2"

    # 4. Execute step 2 with approval
    tm.request_step_approval(task.task_id, "s2")
    loaded_app = repo.get(task.task_id)
    assert loaded_app.status == TaskStatus.WAITING_FOR_APPROVAL
    assert loaded_app.get_step("s2").status == StepStatus.WAITING_FOR_APPROVAL

    tm.approve_step(task.task_id, "s2")
    tm.complete_step(task.task_id, "s2", output_reference="dataset_q4")

    # 5. Complete step 3
    ready3 = tm.get_ready_steps(task.task_id)
    assert len(ready3) == 1 and ready3[0].step_id == "s3"
    tm.start_step(task.task_id, "s3")
    tm.complete_step(task.task_id, "s3", output_reference="reports/q4.pdf")

    # 6. Verify task auto-completes on disk
    final_task = repo.get(task.task_id)
    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED

    summary = tm.get_progress_summary(task.task_id)
    assert summary["percent_complete"] == 100.0
    assert summary["completed_steps"] == 3


def test_task_manager_sqlite_crash_restart_simulation(tmp_path: Path) -> None:
    """Simulate application crash after step 1 and verify seamless resume from disk."""
    db_file = tmp_path / "tm_crash.db"

    # Session 1: Pre-crash
    repo1 = SQLiteMemoryRepository(db_path=db_file)
    tm1 = TaskManager(repository=repo1)

    task = tm1.create_task("Multi-step financial analysis")
    s1 = TaskStep(step_id="step_discover", name="Discover Schema", dependencies=[])
    s2 = TaskStep(step_id="step_query", name="Query Revenue", dependencies=["step_discover"])
    s3 = TaskStep(step_id="step_pdf", name="Generate PDF", dependencies=["step_query"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3])
    tm1.register_plan(task.task_id, plan)

    tm1.start_task(task.task_id)
    tm1.start_step(task.task_id, "step_discover")
    tm1.complete_step(task.task_id, "step_discover", output_reference="schema_dump_json")

    # Record intermediate decision and tool call before crash
    repo1.save_decision(
        task_id=task.task_id,
        step_id="step_discover",
        decision_type="schema_mapping",
        summary="Found orders and order_items tables",
    )
    repo1.save_tool_call(
        task_id=task.task_id,
        step_id="step_discover",
        tool_name="inspect_database_schema",
        result_summary="Discovered 8 tables",
        status="success",
    )

    # --- SIMULATE APPLICATION RESTART ---
    del tm1
    del repo1

    # Session 2: Post-restart
    repo2 = SQLiteMemoryRepository(db_path=db_file)
    tm2 = TaskManager(repository=repo2)

    # Task and its steps are completely reconstructed from SQLite
    reconstructed_task = tm2.get_task(task.task_id)
    assert reconstructed_task is not None
    assert reconstructed_task.task_id == task.task_id
    assert reconstructed_task.status == TaskStatus.RUNNING

    # Step 1 is already COMPLETED on disk
    assert reconstructed_task.get_step("step_discover").status == StepStatus.COMPLETED
    assert reconstructed_task.get_step("step_discover").output_reference == "schema_dump_json"

    # Step 2 is READY to execute next without repeating Step 1!
    ready_steps = tm2.get_ready_steps(task.task_id)
    assert len(ready_steps) == 1
    assert ready_steps[0].step_id == "step_query"

    # Verify decisions and tool call audits survived restart
    decisions = repo2.get_decisions(task.task_id)
    assert len(decisions) == 1
    assert decisions[0].decision_type == "schema_mapping"

    tool_calls = repo2.get_tool_calls(task.task_id)
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "inspect_database_schema"

    # Resume and finish task
    tm2.start_step(task.task_id, "step_query")
    tm2.complete_step(task.task_id, "step_query", output_reference="revenue_sql_dataset")

    tm2.start_step(task.task_id, "step_pdf")
    tm2.complete_step(task.task_id, "step_pdf", output_reference="revenue_report.pdf")

    final_task = tm2.get_task(task.task_id)
    assert final_task.status == TaskStatus.COMPLETED


def test_task_manager_sqlite_optional_dependencies_survive_reload(tmp_path: Path) -> None:
    db_file = tmp_path / "tm_opt_dep.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    tm = TaskManager(repository=repo)

    task = tm.create_task("Task with optional dependencies")
    s1 = TaskStep(step_id="s1", name="Mandatory Prep", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Optional Sampling", dependencies=["s1"])
    s3 = TaskStep(
        step_id="s3",
        name="Final Export",
        dependencies=["s1"],
        optional_dependencies=["s2"],
    )
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2, s3])
    tm.register_plan(task.task_id, plan)

    tm.start_task(task.task_id)
    tm.start_step(task.task_id, "s1")
    tm.complete_step(task.task_id, "s1")

    # Skip optional step s2
    tm.skip_step(task.task_id, "s2", reason="Not required")

    # Reconstruct from disk
    tm_fresh = TaskManager(repository=SQLiteMemoryRepository(db_path=db_file))
    ready = tm_fresh.get_ready_steps(task.task_id)
    assert len(ready) == 1 and ready[0].step_id == "s3"

    tm_fresh.start_step(task.task_id, "s3")
    tm_fresh.complete_step(task.task_id, "s3")

    assert tm_fresh.get_task(task.task_id).status == TaskStatus.COMPLETED


def test_task_manager_sqlite_cancellation(tmp_path: Path) -> None:
    db_file = tmp_path / "tm_cancel.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    tm = TaskManager(repository=repo)

    task = tm.create_task("Long task")
    s1 = TaskStep(step_id="s1", name="Step 1", dependencies=[])
    s2 = TaskStep(step_id="s2", name="Step 2", dependencies=["s1"])
    plan = TaskPlan(task_id=task.task_id, steps=[s1, s2])
    tm.register_plan(task.task_id, plan)

    tm.start_task(task.task_id)
    tm.start_step(task.task_id, "s1")
    tm.cancel_task(task.task_id, reason="User requested cancellation")

    # Recheck directly from SQLite
    loaded = repo.get(task.task_id)
    assert loaded is not None
    assert loaded.status == TaskStatus.CANCELLED
    assert loaded.error == "User requested cancellation"
    assert loaded.get_step("s1").status == StepStatus.CANCELLED
    assert loaded.get_step("s2").status == StepStatus.CANCELLED

