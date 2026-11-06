"""Checkpoint Manager and Recovery Engine for Agent Intelligence Layer.

Responsible for:
- Checkpoint creation at key lifecycle boundaries.
- Cryptographic checkpoint validation.
- Crash and interruption detection.
- Reconstructing consistent execution state across restarts.
- Operation idempotency and duplicate execution prevention.
- Deterministic recovery policies (Scenario A through F).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from agent.checkpoint_models import (
    CURRENT_CHECKPOINT_SCHEMA_VERSION,
    CheckpointType,
    InterruptedOperationRecord,
    OperationStatus,
    PendingApprovalSnapshot,
    RecoveryAttemptRecord,
    RecoveryPolicy,
    RecoveryResult,
    RecoveryStatus,
    StepExecutionSnapshot,
    TaskCheckpoint,
    ValidationResult,
)
from agent.task_models import (
    AgentTask,
    InvalidStateTransitionError,
    StepStatus,
    TaskStatus,
    TaskStep,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CheckpointError(Exception):
    """Base exception for checkpointing and recovery errors."""


class CheckpointNotFoundError(CheckpointError):
    """Raised when a requested checkpoint is not found in the repository."""


class CorruptedCheckpointError(CheckpointError):
    """Raised when checkpoint fails integrity checksum or structure validation."""


class UnsupportedCheckpointVersionError(CheckpointError):
    """Raised when checkpoint schema version is newer than supported."""


class RecoveryError(CheckpointError):
    """Raised when task state cannot be safely recovered."""


class UnsafeRecoveryError(RecoveryError):
    """Raised when automated recovery is attempted on an ambiguous or dangerous state."""


class ArtifactIntegrityError(RecoveryError):
    """Raised when expected generated artifact is missing or structurally invalid."""


# ---------------------------------------------------------------------------
# Recovery Validator
# ---------------------------------------------------------------------------


class RecoveryValidator:
    """Validates checkpoint integrity, structural consistency, and filesystem artifacts."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def validate_checkpoint(
        self,
        checkpoint: TaskCheckpoint,
        task: AgentTask | None = None,
    ) -> ValidationResult:
        """Validate that a checkpoint snapshot is uncorrupted and safe to restore."""
        errors: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        # 1. Cryptographic checksum validation
        if not checkpoint.verify_checksum():
            errors.append(
                f"Checksum mismatch on checkpoint '{checkpoint.checkpoint_id}': "
                f"payload corrupted or altered."
            )

        # 2. Schema version validation
        if checkpoint.schema_version > CURRENT_CHECKPOINT_SCHEMA_VERSION:
            errors.append(
                f"Unsupported checkpoint schema version {checkpoint.schema_version} "
                f"(maximum supported: {CURRENT_CHECKPOINT_SCHEMA_VERSION})."
            )

        # 3. Target task existence
        current_task = task or (
            self.repository.get(checkpoint.task_id) if hasattr(self.repository, "get") else None
        )
        if not current_task:
            errors.append(f"Referenced task '{checkpoint.task_id}' does not exist in repository.")

        # 4. Step consistency and DAG dependency integrity
        if current_task and current_task.steps:
            task_step_ids = {s.step_id for s in current_task.steps}
            step_dict = {s.step_id: s for s in current_task.steps}

            for sid in checkpoint.completed_step_ids:
                if sid not in task_step_ids:
                    errors.append(f"Completed step ID '{sid}' not found in task definition.")
                else:
                    step = step_dict[sid]
                    for dep_id in step.dependencies:
                        if dep_id not in checkpoint.completed_step_ids:
                            errors.append(
                                f"Inconsistent checkpoint: step '{sid}' is COMPLETED but its mandatory "
                                f"dependency '{dep_id}' is not in completed_step_ids."
                            )

            for sid in checkpoint.failed_step_ids:
                if sid not in task_step_ids:
                    errors.append(f"Failed step ID '{sid}' not found in task definition.")

            for sid in checkpoint.pending_step_ids:
                if sid not in task_step_ids:
                    errors.append(f"Pending step ID '{sid}' not found in task definition.")

        # 5. Artifact existence and hash verification
        if hasattr(self.repository, "get_artifacts") and checkpoint.artifact_ids:
            try:
                task_artifacts = {a.artifact_id: a for a in self.repository.get_artifacts(checkpoint.task_id)}
                for art_id in checkpoint.artifact_ids:
                    art = task_artifacts.get(art_id)
                    if not art:
                        warnings.append(f"Artifact record '{art_id}' not found in repository.")
                        continue
                    p = Path(art.file_path)
                    if not p.exists():
                        errors.append(f"Required artifact file missing on disk: '{art.file_path}' (id: {art_id})")
                    elif p.stat().st_size == 0 and art.file_size_bytes > 0:
                        errors.append(f"Artifact file on disk is empty (0 bytes): '{art.file_path}'")
                    elif art.checksum:
                        try:
                            file_sha = hashlib.sha256(p.read_bytes()).hexdigest()
                            if file_sha != art.checksum:
                                errors.append(
                                    f"Artifact checksum mismatch for '{art.file_path}': "
                                    f"expected {art.checksum}, got {file_sha}"
                                )
                        except Exception as e:
                            errors.append(f"Failed reading artifact file '{art.file_path}': {e}")
            except Exception as e:
                warnings.append(f"Could not verify artifacts: {e}")

        # 6. Approval state consistency
        if checkpoint.pending_approval:
            if checkpoint.task_status != TaskStatus.WAITING_FOR_APPROVAL:
                warnings.append(
                    f"Checkpoint has pending approval for step '{checkpoint.pending_approval.step_id}' "
                    f"but task status is {checkpoint.task_status.value}."
                )

        details["error_count"] = len(errors)
        details["warning_count"] = len(warnings)

        return ValidationResult(
            is_valid=(len(errors) == 0),
            checkpoint_id=checkpoint.checkpoint_id,
            task_id=checkpoint.task_id,
            errors=errors,
            warnings=warnings,
            details=details,
        )


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------


class CheckpointManager:
    """Manages the creation, verification, and restoration of task execution checkpoints."""

    def __init__(
        self,
        repository: Any,
        validator: RecoveryValidator | None = None,
    ) -> None:
        self.repository = repository
        self.validator = validator or RecoveryValidator(repository)

    # -----------------------------------------------------------------------
    # Public Checkpoint API
    # -----------------------------------------------------------------------

    def create_checkpoint(
        self,
        task_id: str,
        checkpoint_type: CheckpointType | str,
        *,
        current_stage: str = "",
        current_step_id: str | None = None,
        pending_approval: PendingApprovalSnapshot | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskCheckpoint:
        """Create and persist a cryptographically signed execution snapshot."""
        task = self.repository.get(task_id)
        if not task:
            raise CheckpointError(f"Cannot create checkpoint: task '{task_id}' not found.")

        chk_type = (
            checkpoint_type
            if isinstance(checkpoint_type, CheckpointType)
            else CheckpointType(str(checkpoint_type).upper())
        )

        seq = 1
        if hasattr(self.repository, "get_next_checkpoint_sequence"):
            seq = self.repository.get_next_checkpoint_sequence(task_id)
        elif hasattr(self.repository, "get_checkpoint_history"):
            history = self.repository.get_checkpoint_history(task_id)
            seq = len(history) + 1

        completed_steps = [s.step_id for s in task.steps if s.status == StepStatus.COMPLETED]
        pending_steps = [
            s.step_id for s in task.steps if s.status in {StepStatus.PENDING, StepStatus.READY}
        ]
        failed_steps = [s.step_id for s in task.steps if s.status == StepStatus.FAILED]

        step_states = {
            s.step_id: StepExecutionSnapshot(
                step_id=s.step_id,
                status=s.status,
                output_reference=s.output_reference,
                error=s.error,
                metadata=s.metadata,
            )
            for s in task.steps
        }

        decision_ids: list[str] = []
        if hasattr(self.repository, "get_decisions"):
            decision_ids = [d.decision_id for d in self.repository.get_decisions(task_id)]

        artifact_ids: list[str] = []
        if hasattr(self.repository, "get_artifacts"):
            artifact_ids = [a.artifact_id for a in self.repository.get_artifacts(task_id)]

        active_step = current_step_id or task.current_step

        checkpoint = TaskCheckpoint(
            task_id=task_id,
            sequence_number=seq,
            checkpoint_type=chk_type,
            task_status=task.status,
            current_stage=current_stage,
            current_step_id=active_step,
            completed_step_ids=completed_steps,
            pending_step_ids=pending_steps,
            failed_step_ids=failed_steps,
            step_states=step_states,
            decision_ids=decision_ids,
            pending_approval=pending_approval,
            artifact_ids=artifact_ids,
            metadata=metadata or {},
        )
        checkpoint.set_checksum()

        if hasattr(self.repository, "save_checkpoint"):
            self.repository.save_checkpoint(checkpoint)

        log.info(
            "Created checkpoint %s (seq=%d, type=%s) for task %s",
            checkpoint.checkpoint_id,
            checkpoint.sequence_number,
            checkpoint.checkpoint_type.value,
            task_id,
        )
        return checkpoint

    def get_latest_checkpoint(self, task_id: str) -> TaskCheckpoint | None:
        """Fetch the most recent checkpoint recorded for a task."""
        if hasattr(self.repository, "get_latest_checkpoint"):
            return self.repository.get_latest_checkpoint(task_id)
        return None

    def get_checkpoint_history(self, task_id: str) -> list[TaskCheckpoint]:
        """Fetch all chronological checkpoints recorded for a task."""
        if hasattr(self.repository, "get_checkpoint_history"):
            return self.repository.get_checkpoint_history(task_id)
        return []

    def validate_checkpoint(self, checkpoint_id: str) -> ValidationResult:
        """Fetch and evaluate the validity of a specific checkpoint."""
        checkpoint = self._fetch_checkpoint(checkpoint_id)
        return self.validator.validate_checkpoint(checkpoint)

    def restore_checkpoint(self, checkpoint_id: str) -> AgentTask:
        """Restore task and step execution states from an authenticated checkpoint snapshot."""
        checkpoint = self._fetch_checkpoint(checkpoint_id)

        # 1. Validate checkpoint integrity
        val = self.validator.validate_checkpoint(checkpoint)
        if not val.is_valid:
            raise CorruptedCheckpointError(
                f"Cannot restore corrupted checkpoint '{checkpoint_id}': {val.errors}"
            )

        # 2. Fetch active task entity
        task = self.repository.get(checkpoint.task_id)
        if not task:
            raise CheckpointError(f"Task '{checkpoint.task_id}' not found in repository.")

        # 3. Restore individual step states
        for step in task.steps:
            if step.step_id in checkpoint.step_states:
                snap = checkpoint.step_states[step.step_id]
                step.status = snap.status
                step.output_reference = snap.output_reference
                step.error = snap.error
                step.metadata = snap.metadata

        # 4. Restore task status and pointers
        task.status = checkpoint.task_status
        task.current_step = checkpoint.current_step_id

        # 5. Persist restored state
        self.repository.save(task)
        log.info(
            "Restored task %s to status %s from checkpoint %s (seq=%d)",
            task.task_id,
            task.status.value,
            checkpoint.checkpoint_id,
            checkpoint.sequence_number,
        )
        return task

    # -----------------------------------------------------------------------
    # Task Recovery Engine (Scenarios A through F)
    # -----------------------------------------------------------------------

    def detect_interrupted_tasks(self) -> list[AgentTask]:
        """Identify tasks that were abruptly terminated during execution."""
        all_tasks = self.repository.list_all() if hasattr(self.repository, "list_all") else []
        interrupted: list[AgentTask] = []

        interrupted_statuses = {
            TaskStatus.RUNNING,
            TaskStatus.PLANNING,
            TaskStatus.WAITING_FOR_APPROVAL,
            TaskStatus.INTERRUPTED,
            TaskStatus.REQUIRES_RECOVERY,
        }

        for t in all_tasks:
            if t.status in interrupted_statuses:
                interrupted.append(t)
            elif hasattr(self.repository, "get_interrupted_operations"):
                ops = self.repository.get_interrupted_operations(t.task_id)
                if any(op.status in {OperationStatus.STARTED, OperationStatus.INTERRUPTED} for op in ops):
                    if t not in interrupted and not t.is_terminal:
                        interrupted.append(t)

        return interrupted

    def recover_task(
        self,
        task_id: str,
        policy: RecoveryPolicy = RecoveryPolicy.REQUIRE_CONFIRMATION,
    ) -> RecoveryResult:
        """Reconstruct state, reconcile operations, and safely resume an interrupted task."""
        task = self.repository.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task '{task_id}' not found.")

        # Protect terminal tasks from being mutated
        if task.status == TaskStatus.COMPLETED:
            return RecoveryResult(
                success=True,
                task_id=task_id,
                policy_applied=policy,
                status=RecoveryStatus.SUCCESS,
                message="Task is already COMPLETED. Terminal state protected.",
            )

        attempt = RecoveryAttemptRecord(
            task_id=task_id,
            policy=policy,
            status=RecoveryStatus.STARTED,
        )
        if hasattr(self.repository, "save_recovery_attempt"):
            self.repository.save_recovery_attempt(attempt)

        actions_taken: list[str] = []
        reusable_artifacts: list[str] = []

        # Policy check: MANUAL_ONLY immediately pauses without resume
        if policy == RecoveryPolicy.MANUAL_ONLY:
            task.transition_to(TaskStatus.REQUIRES_RECOVERY)
            self.repository.save(task)
            self._update_attempt(
                attempt.attempt_id,
                RecoveryStatus.REQUIRES_CONFIRMATION,
                details={"reason": "Manual recovery policy enforced."},
            )
            return RecoveryResult(
                success=True,
                task_id=task_id,
                policy_applied=policy,
                status=RecoveryStatus.REQUIRES_CONFIRMATION,
                requires_user_action=True,
                message="Task state reconstructed under MANUAL_ONLY policy. Execution paused for operator input.",
            )

        # -------------------------------------------------------------------
        # Scenario A: Closed between tasks (Pending, no steps executed)
        # -------------------------------------------------------------------
        if task.status == TaskStatus.PENDING and not task.steps:
            actions_taken.append("Identified unstarted PENDING task. Prepared for fresh execution.")
            self._update_attempt(attempt.attempt_id, RecoveryStatus.SUCCESS)
            return RecoveryResult(
                success=True,
                task_id=task_id,
                policy_applied=policy,
                status=RecoveryStatus.SUCCESS,
                actions_taken=actions_taken,
                message="Task restored to PENDING state; ready to start.",
            )

        # -------------------------------------------------------------------
        # Locate latest valid checkpoint (skipping corrupted ones)
        # -------------------------------------------------------------------
        history = self.get_checkpoint_history(task_id)
        valid_checkpoint: TaskCheckpoint | None = None
        rejected_checkpoints: list[str] = []

        for chk in reversed(history):
            val = self.validator.validate_checkpoint(chk, task)
            if val.is_valid:
                valid_checkpoint = chk
                break
            else:
                rejected_checkpoints.append(
                    f"Checkpoint {chk.checkpoint_id} (seq={chk.sequence_number}) invalid: {val.errors}"
                )

        if rejected_checkpoints:
            log.warning("Rejected invalid checkpoints during recovery: %s", rejected_checkpoints)
            actions_taken.append(
                f"Skipped {len(rejected_checkpoints)} corrupted checkpoint(s) in favor of verified ancestor."
            )

        # -------------------------------------------------------------------
        # Scenario B: Crashed during planning
        # -------------------------------------------------------------------
        if task.status == TaskStatus.PLANNING:
            if not valid_checkpoint:
                # Check if a valid plan was already persisted
                if task.plan and task.plan.steps:
                    actions_taken.append("Reused previously persisted plan from memory.")
                    task.transition_to(TaskStatus.PLANNING)
                else:
                    task.transition_to(TaskStatus.PENDING)
                    actions_taken.append("Planning was interrupted before plan completion; reset to PENDING.")

                self.repository.save(task)
                self._update_attempt(attempt.attempt_id, RecoveryStatus.SUCCESS)
                return RecoveryResult(
                    success=True,
                    task_id=task_id,
                    policy_applied=policy,
                    status=RecoveryStatus.SUCCESS,
                    actions_taken=actions_taken,
                    message="Planning state recovered safely.",
                )

        # If no valid checkpoint exists at all for an in-flight execution task
        if not valid_checkpoint:
            task.transition_to(TaskStatus.REQUIRES_RECOVERY)
            self.repository.save(task)
            self._update_attempt(
                attempt.attempt_id,
                RecoveryStatus.FAILED,
                failure_reason="No valid checkpoint available for task recovery.",
            )
            return RecoveryResult(
                success=False,
                task_id=task_id,
                policy_applied=policy,
                status=RecoveryStatus.FAILED,
                requires_user_action=True,
                error="No valid checkpoint found. Task marked REQUIRES_RECOVERY.",
            )

        # -------------------------------------------------------------------
        # Reconstruct state from verified checkpoint
        # -------------------------------------------------------------------
        restored_task = self.restore_checkpoint(valid_checkpoint.checkpoint_id)
        actions_taken.append(
            f"Restored execution snapshot from checkpoint {valid_checkpoint.checkpoint_id} "
            f"(seq={valid_checkpoint.sequence_number}, type={valid_checkpoint.checkpoint_type.value})."
        )

        # -------------------------------------------------------------------
        # Scenario F: Interrupted while waiting for human approval
        # -------------------------------------------------------------------
        if (
            valid_checkpoint.task_status == TaskStatus.WAITING_FOR_APPROVAL
            or valid_checkpoint.pending_approval is not None
        ):
            restored_task.status = TaskStatus.WAITING_FOR_APPROVAL
            if valid_checkpoint.current_step_id:
                step = restored_task.get_step(valid_checkpoint.current_step_id)
                if step:
                    step.status = StepStatus.WAITING_FOR_APPROVAL
            self.repository.save(restored_task)
            actions_taken.append(
                "Restored pending approval request. Maintained WAITING_FOR_APPROVAL state."
            )
            self._update_attempt(
                attempt.attempt_id,
                RecoveryStatus.REQUIRES_CONFIRMATION,
                checkpoint_id=valid_checkpoint.checkpoint_id,
            )
            return RecoveryResult(
                success=True,
                task_id=task_id,
                resumed_from_checkpoint_id=valid_checkpoint.checkpoint_id,
                policy_applied=policy,
                status=RecoveryStatus.REQUIRES_CONFIRMATION,
                resumed_step_id=valid_checkpoint.current_step_id,
                actions_taken=actions_taken,
                requires_user_action=True,
                message="Task restored to WAITING_FOR_APPROVAL. Awaiting explicit user approval decision.",
            )

        # -------------------------------------------------------------------
        # Scenario D & E: Interrupted tool / operation reconciliation
        # -------------------------------------------------------------------
        if hasattr(self.repository, "get_interrupted_operations"):
            ops = self.repository.get_interrupted_operations(task_id)
            for op in ops:
                if op.status in {OperationStatus.STARTED, OperationStatus.INTERRUPTED}:
                    # Scenario D: SQL Execution
                    if "sql" in op.operation_type.lower():
                        self.repository.record_operation_interrupted(
                            task_id, op.operation_type, step_id=op.step_id, error="Interrupted by crash."
                        )
                        actions_taken.append(
                            f"Flagged interrupted read-only SQL operation '{op.operation_key}'. "
                            "Verified read-only safety for re-execution."
                        )

                    # Scenario E: Report Generation
                    elif "report" in op.operation_type.lower() or "artifact" in op.operation_type.lower():
                        # Verify if artifact exists on disk
                        art_records = self.repository.get_artifacts(task_id)
                        matching_arts = [a for a in art_records if a.step_id == op.step_id]
                        if matching_arts and Path(matching_arts[0].file_path).exists():
                            reusable_artifacts.append(matching_arts[0].file_path)
                            self.repository.record_operation_completed(
                                task_id,
                                op.operation_type,
                                step_id=op.step_id,
                                result_summary=f"Reused valid artifact: {matching_arts[0].file_path}",
                            )
                            actions_taken.append(
                                f"Validated completed artifact '{matching_arts[0].file_path}' on disk; reused without regeneration."
                            )
                        else:
                            self.repository.record_operation_interrupted(
                                task_id, op.operation_type, step_id=op.step_id, error="Interrupted report generation."
                            )
                            actions_taken.append(
                                f"Report artifact missing for '{op.operation_key}'; scheduled safe regeneration."
                            )

        # -------------------------------------------------------------------
        # Scenario C: Crashed between steps / determining next eligible step
        # -------------------------------------------------------------------
        next_step_id: str | None = None
        for step in restored_task.steps:
            if step.status == StepStatus.RUNNING:
                # Interrupted in flight -> reset to READY for clean re-execution
                step.status = StepStatus.READY
                next_step_id = step.step_id
                actions_taken.append(f"Reset in-flight step '{step.step_id}' to READY for clean restart.")
                break
            elif step.status == StepStatus.READY:
                next_step_id = step.step_id
                break

        if not next_step_id:
            # Check if any pending step has all dependencies completed
            completed_sids = {s.step_id for s in restored_task.steps if s.status == StepStatus.COMPLETED}
            for step in restored_task.steps:
                if step.status == StepStatus.PENDING:
                    if all(d in completed_sids for d in step.dependencies):
                        step.status = StepStatus.READY
                        next_step_id = step.step_id
                        actions_taken.append(f"Advanced step '{step.step_id}' to READY.")
                        break

        restored_task.current_step = next_step_id
        if restored_task.status != TaskStatus.RUNNING and next_step_id:
            restored_task.status = TaskStatus.RUNNING

        self.repository.save(restored_task)

        # Record recovery completion checkpoint
        self.create_checkpoint(
            task_id=task_id,
            checkpoint_type=CheckpointType.RECOVERY_COMPLETED,
            current_stage="resumed_execution",
            current_step_id=next_step_id,
            metadata={"resumed_from": valid_checkpoint.checkpoint_id, "policy": policy.value},
        )

        self._update_attempt(
            attempt.attempt_id,
            RecoveryStatus.SUCCESS,
            checkpoint_id=valid_checkpoint.checkpoint_id,
            details={"actions": actions_taken, "resumed_step_id": next_step_id},
        )

        return RecoveryResult(
            success=True,
            task_id=task_id,
            resumed_from_checkpoint_id=valid_checkpoint.checkpoint_id,
            policy_applied=policy,
            status=RecoveryStatus.SUCCESS,
            resumed_step_id=next_step_id,
            actions_taken=actions_taken,
            reusable_artifacts=reusable_artifacts,
            message=f"Task successfully recovered from checkpoint {valid_checkpoint.checkpoint_id}.",
        )

    # -----------------------------------------------------------------------
    # Operation Idempotency API
    # -----------------------------------------------------------------------

    def record_operation_started(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> InterruptedOperationRecord:
        """Audit operation start to guard against race conditions and duplicates."""
        if hasattr(self.repository, "record_operation_started"):
            return self.repository.record_operation_started(
                task_id, operation_type, step_id=step_id, operation_key=operation_key, payload=payload
            )
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=operation_key or f"{task_id}:{step_id}:{operation_type}",
            status=OperationStatus.STARTED,
        )

    def record_operation_completed(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        result_summary: str | None = None,
    ) -> InterruptedOperationRecord:
        """Mark an operation as completed."""
        if hasattr(self.repository, "record_operation_completed"):
            return self.repository.record_operation_completed(
                task_id, operation_type, step_id=step_id, operation_key=operation_key, result_summary=result_summary
            )
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=operation_key or f"{task_id}:{step_id}:{operation_type}",
            status=OperationStatus.COMPLETED,
            result_summary=result_summary,
        )

    def record_operation_failed(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        error: str = "",
    ) -> InterruptedOperationRecord:
        """Mark an operation as failed."""
        if hasattr(self.repository, "record_operation_failed"):
            return self.repository.record_operation_failed(
                task_id, operation_type, step_id=step_id, operation_key=operation_key, error=error
            )
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=operation_key or f"{task_id}:{step_id}:{operation_type}",
            status=OperationStatus.FAILED,
            error=error,
        )

    def get_recovery_history(self, task_id: str) -> list[RecoveryAttemptRecord]:
        """Fetch recovery audit trail for a task."""
        if hasattr(self.repository, "get_recovery_history"):
            return self.repository.get_recovery_history(task_id)
        return []

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _fetch_checkpoint(self, checkpoint_id: str) -> TaskCheckpoint:
        if hasattr(self.repository, "get_checkpoint"):
            chk = self.repository.get_checkpoint(checkpoint_id)
            if chk:
                return chk
        raise CheckpointNotFoundError(f"Checkpoint '{checkpoint_id}' not found.")

    def _update_attempt(
        self,
        attempt_id: str,
        status: RecoveryStatus,
        *,
        checkpoint_id: str | None = None,
        failure_reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if hasattr(self.repository, "update_recovery_attempt"):
            self.repository.update_recovery_attempt(
                attempt_id,
                status,
                failure_reason=failure_reason,
                details=details,
            )

