"""Unit tests for SQLite persistent storage of checkpoints, recovery attempts, and operations."""

from __future__ import annotations

from pathlib import Path
import pytest

from agent.checkpoint_models import (
    CheckpointType,
    OperationStatus,
    PendingApprovalSnapshot,
    RecoveryAttemptRecord,
    RecoveryPolicy,
    RecoveryStatus,
    StepExecutionSnapshot,
    TaskCheckpoint,
)
from agent.task_models import AgentTask, StepStatus, TaskStatus, TaskStep
from memory.repository import SQLiteMemoryRepository


def test_save_and_retrieve_checkpoint(tmp_path: Path) -> None:
    db_file = tmp_path / "chk_repo.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_repo_1", user_request="Repo checkpoint test")
    repo.save(task)

    chk = TaskCheckpoint(
        task_id="t_repo_1",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
        metadata={"worker": "test_runner"},
    )
    chk.set_checksum()
    repo.save_checkpoint(chk)

    # Fetch by ID
    loaded = repo.get_checkpoint(chk.checkpoint_id)
    assert loaded is not None
    assert loaded.checkpoint_id == chk.checkpoint_id
    assert loaded.task_id == "t_repo_1"
    assert loaded.sequence_number == 1
    assert loaded.checkpoint_type == CheckpointType.TASK_CREATED
    assert loaded.metadata.get("worker") == "test_runner"
    assert loaded.verify_checksum() is True


def test_checkpoint_sequence_and_history(tmp_path: Path) -> None:
    db_file = tmp_path / "chk_history.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_seq_1", user_request="Sequence test")
    repo.save(task)

    assert repo.get_next_checkpoint_sequence("t_seq_1") == 1

    # Checkpoint 1
    c1 = TaskCheckpoint(
        task_id="t_seq_1",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
    ).set_checksum()
    repo.save_checkpoint(c1)

    assert repo.get_next_checkpoint_sequence("t_seq_1") == 2

    # Checkpoint 2
    c2 = TaskCheckpoint(
        task_id="t_seq_1",
        sequence_number=2,
        checkpoint_type=CheckpointType.PLAN_READY,
        task_status=TaskStatus.PLANNING,
    ).set_checksum()
    repo.save_checkpoint(c2)

    # Checkpoint 3
    c3 = TaskCheckpoint(
        task_id="t_seq_1",
        sequence_number=3,
        checkpoint_type=CheckpointType.STEP_STARTED,
        task_status=TaskStatus.RUNNING,
        current_step_id="step_1",
    ).set_checksum()
    repo.save_checkpoint(c3)

    # Latest
    latest = repo.get_latest_checkpoint("t_seq_1")
    assert latest is not None
    assert latest.checkpoint_id == c3.checkpoint_id
    assert latest.sequence_number == 3

    # History ordered ASC
    history = repo.get_checkpoint_history("t_seq_1")
    assert len(history) == 3
    assert [c.sequence_number for c in history] == [1, 2, 3]


def test_cascade_delete_removes_checkpoints(tmp_path: Path) -> None:
    db_file = tmp_path / "chk_cascade.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_del_1", user_request="To be deleted")
    repo.save(task)

    chk = TaskCheckpoint(
        task_id="t_del_1",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
    ).set_checksum()
    repo.save_checkpoint(chk)

    assert repo.get_checkpoint(chk.checkpoint_id) is not None

    # Delete task
    assert repo.delete("t_del_1") is True
    assert repo.get_checkpoint(chk.checkpoint_id) is None
    assert repo.get_checkpoint_history("t_del_1") == []


def test_recovery_attempts_persistence(tmp_path: Path) -> None:
    db_file = tmp_path / "rec_attempts.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_rec_1", user_request="Recovery test")
    repo.save(task)

    attempt = RecoveryAttemptRecord(
        task_id="t_rec_1",
        policy=RecoveryPolicy.REQUIRE_CONFIRMATION,
        status=RecoveryStatus.STARTED,
        details={"trigger": "app_startup_scan"},
    )
    repo.save_recovery_attempt(attempt)

    history = repo.get_recovery_history("t_rec_1")
    assert len(history) == 1
    assert history[0].attempt_id == attempt.attempt_id
    assert history[0].status == RecoveryStatus.STARTED

    # Update attempt
    repo.update_recovery_attempt(
        attempt.attempt_id,
        RecoveryStatus.SUCCESS,
        details={"trigger": "app_startup_scan", "resumed_step": "step_2"},
    )
    updated_history = repo.get_recovery_history("t_rec_1")
    assert len(updated_history) == 1
    assert updated_history[0].status == RecoveryStatus.SUCCESS
    assert updated_history[0].details.get("resumed_step") == "step_2"


def test_interrupted_operations_idempotency_lifecycle(tmp_path: Path) -> None:
    db_file = tmp_path / "ops_lifecycle.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_op_1", user_request="Op idempotency test")
    repo.save(task)

    # 1. Start operation
    op1 = repo.record_operation_started(
        "t_op_1",
        "sql_execution",
        step_id="step_sql_1",
        payload={"query": "SELECT count(*) FROM orders;"},
    )
    assert op1.status == OperationStatus.STARTED

    in_flight = repo.get_interrupted_operations("t_op_1")
    assert len(in_flight) == 1
    assert in_flight[0].operation_type == "sql_execution"

    # 2. Crash / Mark interrupted
    op_interrupted = repo.record_operation_interrupted(
        "t_op_1",
        "sql_execution",
        step_id="step_sql_1",
        error="Simulated process kill during SQL execution",
    )
    assert op_interrupted.status == OperationStatus.INTERRUPTED

    # 3. Successful retry and completion
    op_completed = repo.record_operation_completed(
        "t_op_1",
        "sql_execution",
        step_id="step_sql_1",
        result_summary="Returned 99441 rows",
    )
    assert op_completed.status == OperationStatus.COMPLETED

    # No in-flight operations remaining
    remaining = repo.get_interrupted_operations("t_op_1")
    assert len(remaining) == 0

