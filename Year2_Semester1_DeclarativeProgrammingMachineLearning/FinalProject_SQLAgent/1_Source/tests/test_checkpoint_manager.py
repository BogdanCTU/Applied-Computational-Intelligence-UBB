"""Unit tests for CheckpointManager creation, validation, restoration, and corruption handling."""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from agent.checkpoint_manager import (
    CheckpointManager,
    CheckpointNotFoundError,
    CorruptedCheckpointError,
    RecoveryValidator,
)
from agent.checkpoint_models import (
    CURRENT_CHECKPOINT_SCHEMA_VERSION,
    CheckpointType,
    PendingApprovalSnapshot,
    StepExecutionSnapshot,
    TaskCheckpoint,
)
from agent.task_models import AgentTask, StepStatus, TaskStatus, TaskStep
from memory.repository import SQLiteMemoryRepository


def test_checkpoint_manager_create_and_validate(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_val.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Inspect Schema", status=StepStatus.COMPLETED)
    s2 = TaskStep(step_id="s2", name="Execute SQL", status=StepStatus.RUNNING, dependencies=["s1"])
    task = AgentTask(task_id="t_val_1", user_request="Validation test", steps=[s1, s2], status=TaskStatus.RUNNING)
    repo.save(task)

    chk = cm.create_checkpoint(
        "t_val_1",
        CheckpointType.STEP_STARTED,
        current_step_id="s2",
    )
    assert chk.checkpoint_id.startswith("chk_")
    assert chk.verify_checksum() is True

    # Validate via CheckpointManager
    val_res = cm.validate_checkpoint(chk.checkpoint_id)
    assert val_res.is_valid is True
    assert val_res.errors == []


def test_validator_detects_corrupted_checksum(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_tamper.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    validator = RecoveryValidator(repository=repo)

    task = AgentTask(task_id="t_tamper", user_request="Tamper test")
    repo.save(task)

    chk = TaskCheckpoint(
        task_id="t_tamper",
        sequence_number=1,
        checkpoint_type=CheckpointType.TASK_CREATED,
        task_status=TaskStatus.PENDING,
    ).set_checksum()

    # Tamper with checksum directly
    chk.checksum = "bad_checksum_000000000000000000000000000000000000000000000000000000"
    repo.save_checkpoint(chk)

    val = validator.validate_checkpoint(chk)
    assert val.is_valid is False
    assert any("Checksum mismatch" in e for e in val.errors)


def test_validator_detects_missing_and_corrupted_artifacts(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_art_val.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    validator = RecoveryValidator(repository=repo)

    task = AgentTask(task_id="t_art_val", user_request="Artifact validation test")
    repo.save(task)

    # 1. Artifact missing from disk
    missing_file = tmp_path / "non_existent.pdf"
    art_rec = repo.save_artifact(
        task_id="t_art_val",
        artifact_type="pdf_report",
        file_path=str(missing_file),
        file_size_bytes=1000,
        checksum="dummy_checksum",
    )

    chk = TaskCheckpoint(
        task_id="t_art_val",
        sequence_number=1,
        checkpoint_type=CheckpointType.ARTIFACT_GENERATED,
        task_status=TaskStatus.RUNNING,
        artifact_ids=[art_rec.artifact_id],
    ).set_checksum()
    repo.save_checkpoint(chk)

    val = validator.validate_checkpoint(chk)
    assert val.is_valid is False
    assert any("artifact file missing on disk" in e.lower() for e in val.errors)

    # 2. Artifact exists but checksum mismatches
    real_file = tmp_path / "real_report.pdf"
    real_file.write_bytes(b"%PDF-1.4 actual content here")
    art_rec2 = repo.save_artifact(
        task_id="t_art_val",
        artifact_type="pdf_report",
        file_path=str(real_file),
        file_size_bytes=len(real_file.read_bytes()),
        checksum="invalid_recorded_checksum_hash",
    )
    chk2 = TaskCheckpoint(
        task_id="t_art_val",
        sequence_number=2,
        checkpoint_type=CheckpointType.ARTIFACT_GENERATED,
        task_status=TaskStatus.RUNNING,
        artifact_ids=[art_rec2.artifact_id],
    ).set_checksum()
    repo.save_checkpoint(chk2)

    val2 = validator.validate_checkpoint(chk2)
    assert val2.is_valid is False
    assert any("checksum mismatch" in e.lower() for e in val2.errors)

    # 3. Artifact exists and checksum matches
    correct_sha = hashlib.sha256(real_file.read_bytes()).hexdigest()
    art_rec3 = repo.save_artifact(
        task_id="t_art_val",
        artifact_type="pdf_report",
        file_path=str(real_file),
        file_size_bytes=len(real_file.read_bytes()),
        checksum=correct_sha,
    )
    chk3 = TaskCheckpoint(
        task_id="t_art_val",
        sequence_number=3,
        checkpoint_type=CheckpointType.ARTIFACT_GENERATED,
        task_status=TaskStatus.RUNNING,
        artifact_ids=[art_rec3.artifact_id],
    ).set_checksum()
    repo.save_checkpoint(chk3)

    val3 = validator.validate_checkpoint(chk3)
    assert val3.is_valid is True


def test_validator_detects_dependency_inconsistency(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_dep_inconsistent.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    validator = RecoveryValidator(repository=repo)

    # s2 depends on s1, but checkpoint marks s2 completed while s1 is not completed!
    s1 = TaskStep(step_id="s1", name="Step 1")
    s2 = TaskStep(step_id="s2", name="Step 2", dependencies=["s1"])
    task = AgentTask(task_id="t_dep_err", user_request="Dep error", steps=[s1, s2])
    repo.save(task)

    inconsistent_chk = TaskCheckpoint(
        task_id="t_dep_err",
        sequence_number=1,
        checkpoint_type=CheckpointType.STEP_COMPLETED,
        task_status=TaskStatus.RUNNING,
        completed_step_ids=["s2"],  # s1 missing!
    ).set_checksum()
    repo.save_checkpoint(inconsistent_chk)

    val = validator.validate_checkpoint(inconsistent_chk)
    assert val.is_valid is False
    assert any("dependency 's1' is not in completed_step_ids" in e for e in val.errors)


def test_restore_checkpoint_reconstructs_task(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_restore.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.PENDING)
    s2 = TaskStep(step_id="s2", name="Step 2", status=StepStatus.PENDING, dependencies=["s1"])
    task = AgentTask(task_id="t_res_1", user_request="Restore test", steps=[s1, s2])
    repo.save(task)

    # Execute step 1 and checkpoint
    s1.status = StepStatus.COMPLETED
    s1.output_reference = "ref_out_1"
    s2.status = StepStatus.RUNNING
    task.status = TaskStatus.RUNNING
    task.current_step = "s2"
    repo.save(task)

    chk = cm.create_checkpoint("t_res_1", CheckpointType.STEP_STARTED, current_step_id="s2")

    # Simulate memory mutation or crash corrupting active in-memory task
    task.status = TaskStatus.FAILED
    task.current_step = None
    s2.status = StepStatus.FAILED
    repo.save(task)

    # Restore from checkpoint
    restored = cm.restore_checkpoint(chk.checkpoint_id)
    assert restored.status == TaskStatus.RUNNING
    assert restored.current_step == "s2"
    assert restored.get_step("s1").status == StepStatus.COMPLETED
    assert restored.get_step("s1").output_reference == "ref_out_1"
    assert restored.get_step("s2").status == StepStatus.RUNNING


def test_restore_checkpoint_raises_on_corrupted_snapshot(tmp_path: Path) -> None:
    db_file = tmp_path / "cm_corrupt_restore.db"
    repo = SQLiteMemoryRepository(db_path=db_file)
    cm = CheckpointManager(repository=repo)

    task = AgentTask(task_id="t_corrupt_1", user_request="Corrupt restore")
    repo.save(task)

    chk = cm.create_checkpoint("t_corrupt_1", CheckpointType.TASK_CREATED)

    # Corrupt checksum in SQLite
    with repo.transaction() as conn:
        conn.execute(
            "UPDATE task_checkpoints SET checksum = 'tampered' WHERE checkpoint_id = ?;",
            (chk.checkpoint_id,),
        )

    with pytest.raises(CorruptedCheckpointError) as exc_info:
        cm.restore_checkpoint(chk.checkpoint_id)
    assert "Cannot restore corrupted checkpoint" in str(exc_info.value)

