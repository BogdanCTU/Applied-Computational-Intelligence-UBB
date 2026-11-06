"""Unit tests for Checkpoint Pydantic v2 models, deterministic checksums, and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.checkpoint_models import (
    CURRENT_CHECKPOINT_SCHEMA_VERSION,
    CheckpointType,
    OperationStatus,
    PendingApprovalSnapshot,
    RecoveryPolicy,
    RecoveryStatus,
    StepExecutionSnapshot,
    TaskCheckpoint,
)
from agent.task_models import StepStatus, TaskStatus


def test_checkpoint_model_creation_and_defaults() -> None:
    chk = TaskCheckpoint(
        task_id="task_test_1",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
    )
    assert chk.checkpoint_id.startswith("chk_")
    assert chk.task_id == "task_test_1"
    assert chk.sequence_number == 1
    assert chk.checkpoint_type == CheckpointType.TASK_CREATED
    assert chk.schema_version == CURRENT_CHECKPOINT_SCHEMA_VERSION
    assert chk.task_status == TaskStatus.PENDING
    assert chk.completed_step_ids == []
    assert chk.step_states == {}
    assert chk.checksum == ""


def test_checkpoint_deterministic_checksum() -> None:
    s1 = StepExecutionSnapshot(step_id="step_1", status=StepStatus.COMPLETED)
    chk1 = TaskCheckpoint(
        checkpoint_id="chk_fixed_id",
        task_id="task_test_1",
        sequence_number=2,
        checkpoint_type=CheckpointType.STEP_COMPLETED,
        task_status=TaskStatus.RUNNING,
        current_step_id="step_1",
        completed_step_ids=["step_1"],
        step_states={"step_1": s1},
        created_at="2026-11-06T10:00:00Z",
    )
    chk1.set_checksum()
    assert chk1.checksum != ""
    assert chk1.verify_checksum() is True

    # Same content constructed in different dict order yields exact same checksum
    chk2 = TaskCheckpoint(
        checkpoint_id="chk_fixed_id",
        created_at="2026-11-06T10:00:00Z",
        step_states={"step_1": s1},
        completed_step_ids=["step_1"],
        current_step_id="step_1",
        task_status=TaskStatus.RUNNING,
        checkpoint_type=CheckpointType.STEP_COMPLETED,
        sequence_number=2,
        task_id="task_test_1",
    )
    chk2.set_checksum()
    assert chk1.checksum == chk2.checksum


def test_checksum_detects_mutation() -> None:
    chk = TaskCheckpoint(
        task_id="task_test_tamper",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
    )
    chk.set_checksum()
    assert chk.verify_checksum() is True

    # Mutate field after checksum calculation
    chk.task_status = TaskStatus.RUNNING
    assert chk.verify_checksum() is False


def test_checkpoint_serialization_roundtrip() -> None:
    approval = PendingApprovalSnapshot(
        step_id="s_approve",
        operation_type="sql_write_action",
        action_summary="Drop and recreate index",
    )
    chk = TaskCheckpoint(
        task_id="task_ser_1",
        sequence_number=3,
        checkpoint_type=CheckpointType.APPROVAL_REQUESTED,
        task_status=TaskStatus.WAITING_FOR_APPROVAL,
        current_step_id="s_approve",
        pending_approval=approval,
        metadata={"operator": "analyst"},
    )
    chk.set_checksum()

    # Serialization
    as_dict = chk.to_dict()
    assert as_dict["checkpoint_type"] == "APPROVAL_REQUESTED"
    assert as_dict["task_status"] == "WAITING_FOR_APPROVAL"
    assert as_dict["pending_approval"]["step_id"] == "s_approve"

    # Deserialization
    restored = TaskCheckpoint.from_dict(as_dict)
    assert restored.checkpoint_id == chk.checkpoint_id
    assert restored.task_id == chk.task_id
    assert restored.pending_approval is not None
    assert restored.pending_approval.step_id == "s_approve"
    assert restored.verify_checksum() is True


def test_invalid_checkpoint_schema_version_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCheckpoint(
            task_id="task_1",
            sequence_number=1,
            checkpoint_type=CheckpointType.TASK_CREATED,
            task_status=TaskStatus.PENDING,
            schema_version=0,  # ge=1 constraint
        )


def test_invalid_checkpoint_sequence_number_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCheckpoint(
            task_id="task_1",
            sequence_number=-1,  # ge=1 constraint
            checkpoint_type=CheckpointType.TASK_CREATED,
            task_status=TaskStatus.PENDING,
        )

