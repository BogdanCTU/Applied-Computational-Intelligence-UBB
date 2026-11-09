"""Comprehensive integration tests for Task Recovery across Scenarios A through F.

Simulates application crashes, mid-step terminations, pending approvals,
corrupted checkpoints, and verifies idempotent resumption without duplicate side-effects.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from agent.checkpoint_manager import CheckpointManager
from agent.checkpoint_models import (
    CheckpointType,
    OperationStatus,
    PendingApprovalSnapshot,
    RecoveryPolicy,
    RecoveryStatus,
    TaskCheckpoint,
)
from agent.task_manager import TaskManager
from agent.task_models import (
    AgentTask,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from memory.repository import SQLiteMemoryRepository


# ---------------------------------------------------------------------------
# Scenario A: Closed between tasks (Pending, unstarted)
# ---------------------------------------------------------------------------


def test_recovery_scenario_a_pending_task(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_a.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    task = AgentTask(task_id="t_scen_a", user_request="Generate Q4 Sales", status=TaskStatus.PENDING)
    repo.save(task)

    res = cm.recover_task("t_scen_a")
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS
    assert "PENDING state; ready to start" in res.message

    reloaded = repo.get("t_scen_a")
    assert reloaded.status == TaskStatus.PENDING


# ---------------------------------------------------------------------------
# Scenario B: Crashed during planning
# ---------------------------------------------------------------------------


def test_recovery_scenario_b_interrupted_planning_without_plan(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_b1.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    task = AgentTask(task_id="t_scen_b1", user_request="Plan without steps", status=TaskStatus.PLANNING)
    repo.save(task)

    res = cm.recover_task("t_scen_b1")
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS

    # Reset to PENDING so planning can start cleanly
    reloaded = repo.get("t_scen_b1")
    assert reloaded.status == TaskStatus.PENDING


def test_recovery_scenario_b_interrupted_planning_with_persisted_plan(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_b2.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1")
    plan = TaskPlan(plan_id="p1", task_id="t_scen_b2", steps=[s1])
    task = AgentTask(
        task_id="t_scen_b2",
        user_request="Plan with steps",
        status=TaskStatus.PLANNING,
        steps=[s1],
        plan=plan,
    )
    repo.save(task)

    res = cm.recover_task("t_scen_b2")
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS

    reloaded = repo.get("t_scen_b2")
    assert reloaded.status == TaskStatus.PLANNING
    assert len(reloaded.steps) == 1


# ---------------------------------------------------------------------------
# Scenario C: Crashed between execution steps
# ---------------------------------------------------------------------------


def test_recovery_scenario_c_resume_next_eligible_step(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_c.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)
    tm = TaskManager(repository=repo, checkpoint_manager=cm)

    # 3-step pipeline: s1 -> s2 -> s3
    s1 = TaskStep(step_id="s1", name="Step 1")
    s2 = TaskStep(step_id="s2", name="Step 2", dependencies=["s1"])
    s3 = TaskStep(step_id="s3", name="Step 3", dependencies=["s2"])
    plan = TaskPlan(task_id="t_scen_c", steps=[s1, s2, s3])

    task = tm.create_task("Multi-step pipeline", task_id="t_scen_c")
    tm.register_plan("t_scen_c", plan)

    # Execute s1 to completion
    tm.start_step("t_scen_c", "s1")
    tm.complete_step("t_scen_c", "s1", output_reference="out_s1")

    # Start s2, then simulate crash mid-flight
    tm.start_step("t_scen_c", "s2")

    # Simulate restart: fresh manager instances
    fresh_cm = CheckpointManager(repository=repo)
    interrupted = fresh_cm.detect_interrupted_tasks()
    assert any(t.task_id == "t_scen_c" for t in interrupted)

    # Recover task
    res = fresh_cm.recover_task("t_scen_c", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS
    assert res.resumed_step_id == "s2"

    reloaded = repo.get("t_scen_c")
    assert reloaded.status == TaskStatus.RUNNING
    # Completed step 1 preserved
    assert reloaded.get_step("s1").status == StepStatus.COMPLETED
    assert reloaded.get_step("s1").output_reference == "out_s1"
    # Interrupted step 2 reset to READY for clean resumption
    assert reloaded.get_step("s2").status == StepStatus.READY
    # Downstream step 3 remains PENDING
    assert reloaded.get_step("s3").status == StepStatus.PENDING


# ---------------------------------------------------------------------------
# Scenario D: Crashed during SQL execution (Read-only safe retry)
# ---------------------------------------------------------------------------


def test_recovery_scenario_d_interrupted_sql_execution(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_d.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="sql_step", name="Execute Revenue SQL", status=StepStatus.RUNNING)
    task = AgentTask(
        task_id="t_sql_crash",
        user_request="Run complex SQL join",
        status=TaskStatus.RUNNING,
        current_step="sql_step",
        steps=[s1],
    )
    repo.save(task)
    cm.create_checkpoint("t_sql_crash", CheckpointType.STEP_STARTED, current_step_id="sql_step")

    # Record started SQL operation
    cm.record_operation_started(
        "t_sql_crash",
        "sql_execution",
        step_id="sql_step",
        payload={"query": "SELECT count(*) FROM orders JOIN order_items USING(order_id);"},
    )

    # Recover task
    res = cm.recover_task("t_sql_crash", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS
    assert any("read-only SQL" in a for a in res.actions_taken)

    # Verify operation was marked interrupted and step reset to READY
    reloaded = repo.get("t_sql_crash")
    assert reloaded.get_step("sql_step").status == StepStatus.READY

    ops = repo.get_interrupted_operations("t_sql_crash")
    assert len(ops) == 1
    assert ops[0].status == OperationStatus.INTERRUPTED


# ---------------------------------------------------------------------------
# Scenario E: Crashed during report generation (Artifact validation & reuse)
# ---------------------------------------------------------------------------


def test_recovery_scenario_e_reuse_valid_report_artifact(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_e1.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="report_step", name="Generate PDF", status=StepStatus.RUNNING)
    task = AgentTask(
        task_id="t_rep_reuse",
        user_request="Generate PDF report",
        status=TaskStatus.RUNNING,
        current_step="report_step",
        steps=[s1],
    )
    repo.save(task)

    # Valid completed PDF file on disk
    report_file = tmp_path / "sales_summary.pdf"
    content = b"%PDF-1.4 Valid Generated PDF Content"
    report_file.write_bytes(content)
    file_sha = hashlib.sha256(content).hexdigest()

    art = repo.save_artifact(
        "t_rep_reuse",
        "pdf_report",
        file_path=str(report_file),
        file_size_bytes=len(content),
        checksum=file_sha,
        step_id="report_step",
    )

    cm.create_checkpoint(
        "t_rep_reuse",
        CheckpointType.ARTIFACT_GENERATED,
        current_step_id="report_step",
    )

    cm.record_operation_started(
        "t_rep_reuse",
        "report_generation",
        step_id="report_step",
    )

    # Recovery: must reuse the valid completed report instead of re-generating
    res = cm.recover_task("t_rep_reuse", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert str(report_file) in res.reusable_artifacts
    assert any("reused without regeneration" in a for a in res.actions_taken)


def test_recovery_scenario_e_regenerate_when_artifact_missing(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_e2.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="report_step", name="Generate PDF", status=StepStatus.RUNNING)
    task = AgentTask(
        task_id="t_rep_missing",
        user_request="Generate PDF report",
        status=TaskStatus.RUNNING,
        current_step="report_step",
        steps=[s1],
    )
    repo.save(task)

    cm.create_checkpoint(
        "t_rep_missing",
        CheckpointType.STEP_STARTED,
        current_step_id="report_step",
    )

    cm.record_operation_started(
        "t_rep_missing",
        "report_generation",
        step_id="report_step",
    )

    # Recovery: artifact missing from disk -> schedules safe regeneration
    res = cm.recover_task("t_rep_missing", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert res.reusable_artifacts == []
    assert any("scheduled safe regeneration" in a for a in res.actions_taken)

    reloaded = repo.get("t_rep_missing")
    assert reloaded.get_step("report_step").status == StepStatus.READY


# ---------------------------------------------------------------------------
# Scenario F: Interrupted waiting for human approval
# ---------------------------------------------------------------------------


def test_recovery_scenario_f_restores_pending_approval_without_bypass(tmp_path: Path) -> None:
    db_file = tmp_path / "scenario_f.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="drop_step", name="Drop temp table", status=StepStatus.WAITING_FOR_APPROVAL)
    task = AgentTask(
        task_id="t_approval",
        user_request="Cleanup workspace",
        status=TaskStatus.WAITING_FOR_APPROVAL,
        current_step="drop_step",
        steps=[s1],
    )
    repo.save(task)

    approval = PendingApprovalSnapshot(
        step_id="drop_step",
        operation_type="protected_ddl",
        action_summary="Drop table temp_orders",
    )
    cm.create_checkpoint(
        "t_approval",
        CheckpointType.APPROVAL_REQUESTED,
        current_step_id="drop_step",
        pending_approval=approval,
    )

    # Recover task
    res = cm.recover_task("t_approval", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert res.status == RecoveryStatus.REQUIRES_CONFIRMATION
    assert res.requires_user_action is True
    assert "Awaiting explicit user approval decision" in res.message

    # Operation must NOT have been executed or bypassed
    reloaded = repo.get("t_approval")
    assert reloaded.status == TaskStatus.WAITING_FOR_APPROVAL
    assert reloaded.get_step("drop_step").status == StepStatus.WAITING_FOR_APPROVAL


# ---------------------------------------------------------------------------
# Fallback to Earlier Valid Checkpoint on Corruption
# ---------------------------------------------------------------------------


def test_recovery_fallback_to_earlier_valid_checkpoint(tmp_path: Path) -> None:
    db_file = tmp_path / "fallback.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.COMPLETED)
    s2 = TaskStep(step_id="s2", name="Step 2", status=StepStatus.RUNNING, dependencies=["s1"])
    task = AgentTask(
        task_id="t_fallback",
        user_request="Fallback test",
        status=TaskStatus.RUNNING,
        current_step="s2",
        steps=[s1, s2],
    )
    repo.save(task)

    # Checkpoint 1 (valid)
    chk1 = cm.create_checkpoint("t_fallback", CheckpointType.STEP_COMPLETED, current_step_id="s1")

    # Checkpoint 2 (valid when created)
    chk2 = cm.create_checkpoint("t_fallback", CheckpointType.STEP_STARTED, current_step_id="s2")

    # Deliberately corrupt Checkpoint 2 in SQLite database
    with repo.transaction() as conn:
        conn.execute(
            "UPDATE task_checkpoints SET checksum = 'tampered_bad_hash' WHERE checkpoint_id = ?;",
            (chk2.checkpoint_id,),
        )

    # Recover task: must detect chk2 is invalid, reject it, and fall back to chk1
    res = cm.recover_task("t_fallback", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is True
    assert res.resumed_from_checkpoint_id == chk1.checkpoint_id
    assert any("Skipped 1 corrupted checkpoint" in a for a in res.actions_taken)


# ---------------------------------------------------------------------------
# Completed Task Protection
# ---------------------------------------------------------------------------


def test_completed_task_is_never_resumed(tmp_path: Path) -> None:
    db_file = tmp_path / "completed_prot.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.COMPLETED)
    task = AgentTask(
        task_id="t_done",
        user_request="Completed task",
        status=TaskStatus.COMPLETED,
        steps=[s1],
    )
    repo.save(task)

    res = cm.recover_task("t_done")
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS
    assert "already COMPLETED" in res.message

    reloaded = repo.get("t_done")
    assert reloaded.status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# No Valid Checkpoint Handling & Policy Enforcement
# ---------------------------------------------------------------------------


def test_recovery_fails_safely_when_no_valid_checkpoint_exists(tmp_path: Path) -> None:
    db_file = tmp_path / "no_valid_chk.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.RUNNING)
    task = AgentTask(
        task_id="t_no_valid",
        user_request="No valid checkpoints",
        status=TaskStatus.RUNNING,
        steps=[s1],
    )
    repo.save(task)

    # Checkpoint exists but is corrupted
    chk = cm.create_checkpoint("t_no_valid", CheckpointType.STEP_STARTED, current_step_id="s1")
    with repo.transaction() as conn:
        conn.execute(
            "UPDATE task_checkpoints SET checksum = 'corrupted_hash' WHERE checkpoint_id = ?;",
            (chk.checkpoint_id,),
        )

    res = cm.recover_task("t_no_valid", policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert res.success is False
    assert res.status == RecoveryStatus.FAILED
    assert res.requires_user_action is True
    assert "REQUIRES_RECOVERY" in str(res.error)

    reloaded = repo.get("t_no_valid")
    assert reloaded.status == TaskStatus.REQUIRES_RECOVERY


def test_recovery_manual_only_policy_enforcement(tmp_path: Path) -> None:
    db_file = tmp_path / "manual_only.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.RUNNING)
    task = AgentTask(
        task_id="t_manual",
        user_request="Manual policy test",
        status=TaskStatus.RUNNING,
        steps=[s1],
    )
    repo.save(task)
    cm.create_checkpoint("t_manual", CheckpointType.STEP_STARTED, current_step_id="s1")

    res = cm.recover_task("t_manual", policy=RecoveryPolicy.MANUAL_ONLY)
    assert res.success is True
    assert res.status == RecoveryStatus.REQUIRES_CONFIRMATION
    assert res.requires_user_action is True
    assert "Execution paused for operator input" in res.message

    reloaded = repo.get("t_manual")
    assert reloaded.status == TaskStatus.REQUIRES_RECOVERY


def test_task_manager_delegated_recovery_and_lifecycle_checkpoints(tmp_path: Path) -> None:
    db_file = tmp_path / "tm_integrated.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)
    tm = TaskManager(repository=repo, checkpoint_manager=cm)

    s1 = TaskStep(step_id="s1", name="Step 1")
    plan = TaskPlan(task_id="t_integrated", steps=[s1])

    # 1. TASK_CREATED checkpoint
    task = tm.create_task("Integration test", task_id="t_integrated")
    # 2. PLAN_READY checkpoint
    tm.register_plan("t_integrated", plan)
    # 3. APPROVAL_REQUESTED checkpoint
    tm.request_step_approval("t_integrated", "s1")
    # 4. APPROVAL_RESOLVED checkpoint
    tm.approve_step("t_integrated", "s1")
    # 5. STEP_STARTED checkpoint
    tm.start_step("t_integrated", "s1")
    # 6. STEP_COMPLETED + 7. TASK_COMPLETED checkpoints
    tm.complete_step("t_integrated", "s1", output_reference="ref_fin")

    history = cm.get_checkpoint_history("t_integrated")
    types = [c.checkpoint_type for c in history]

    assert CheckpointType.TASK_CREATED in types
    assert CheckpointType.PLAN_READY in types
    assert CheckpointType.APPROVAL_REQUESTED in types
    assert CheckpointType.APPROVAL_RESOLVED in types
    assert CheckpointType.STEP_STARTED in types
    assert CheckpointType.STEP_COMPLETED in types
    assert CheckpointType.TASK_COMPLETED in types

    # Test delegated recovery call
    res = tm.recover_task("t_integrated")
    assert res.success is True
    assert res.status == RecoveryStatus.SUCCESS

