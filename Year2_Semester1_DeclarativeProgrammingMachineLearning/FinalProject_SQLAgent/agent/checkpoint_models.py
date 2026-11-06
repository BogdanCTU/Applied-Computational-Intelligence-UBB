"""Versioned data models and deterministic checksums for Checkpointing and Task Recovery.

Uses Pydantic v2 to define immutable snapshots, lifecycle states,
recovery policies, and cryptographic integrity verification.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent.task_models import StepStatus, TaskStatus

CURRENT_CHECKPOINT_SCHEMA_VERSION = 1


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CheckpointType(str, Enum):
    """Execution boundaries where a durable checkpoint snapshot is recorded."""

    TASK_CREATED = "TASK_CREATED"
    PLAN_READY = "PLAN_READY"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"
    ARTIFACT_GENERATED = "ARTIFACT_GENERATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"


class RecoveryPolicy(str, Enum):
    """Policies governing automated vs manual execution resumption."""

    AUTOMATIC_SAFE = "AUTOMATIC_SAFE"  # Resume only operations proven safe to retry
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"  # Ask for explicit confirmation on ambiguous state (Default)
    MANUAL_ONLY = "MANUAL_ONLY"  # Reconstruct state but never resume execution automatically


class RecoveryStatus(str, Enum):
    """Lifecycle state of a recovery attempt."""

    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    REJECTED = "REJECTED"


class OperationStatus(str, Enum):
    """Granular state of an individual tool call or execution operation."""

    NOT_STARTED = "NOT_STARTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class StepExecutionSnapshot(BaseModel):
    """Lightweight immutable snapshot of a single step's state at checkpoint time."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    step_id: str
    status: StepStatus
    output_reference: str | None = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingApprovalSnapshot(BaseModel):
    """Snapshot of a sensitive action awaiting human confirmation."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    step_id: str
    operation_type: str
    action_summary: str
    requested_at: str = Field(default_factory=_utc_iso_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskCheckpoint(BaseModel):
    """Cryptographically verifiable execution snapshot of an AgentTask."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Target task identifier")
    sequence_number: int = Field(default=1, ge=1, description="Strictly incrementing checkpoint order")
    checkpoint_type: CheckpointType = Field(..., description="Lifecycle event that triggered snapshot")
    schema_version: int = Field(default=CURRENT_CHECKPOINT_SCHEMA_VERSION, ge=1)
    task_status: TaskStatus = Field(..., description="Task lifecycle status at snapshot time")
    current_stage: str = Field(default="", description="High level execution stage: planning, executing, etc.")
    current_step_id: str | None = Field(default=None, description="Active step ID if executing")
    completed_step_ids: list[str] = Field(default_factory=list)
    pending_step_ids: list[str] = Field(default_factory=list)
    failed_step_ids: list[str] = Field(default_factory=list)
    step_states: dict[str, StepExecutionSnapshot] = Field(default_factory=dict)
    decision_ids: list[str] = Field(default_factory=list, description="IDs of decisions leading to this state")
    pending_approval: PendingApprovalSnapshot | None = Field(default=None)
    artifact_ids: list[str] = Field(default_factory=list, description="IDs of persisted artifacts generated so far")
    metadata: dict[str, Any] = Field(default_factory=dict)
    checksum: str = Field(default="", description="Deterministic SHA-256 payload digest excluding checksum")
    created_at: str = Field(default_factory=_utc_iso_now)

    def compute_checksum(self) -> str:
        """Calculate deterministic SHA-256 hash over payload excluding checksum."""
        data = self.model_dump(mode="json", exclude={"checksum"})
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_checksum(self) -> bool:
        """Verify that self.checksum matches the cryptographic digest of its contents."""
        if not self.checksum:
            return False
        return self.checksum == self.compute_checksum()

    def set_checksum(self) -> TaskCheckpoint:
        """Compute and populate the checksum field."""
        self.checksum = self.compute_checksum()
        return self

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["checkpoint_type"] = self.checkpoint_type.value
        d["task_status"] = self.task_status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskCheckpoint:
        return cls.model_validate(data)


class RecoveryAttemptRecord(BaseModel):
    """Audit log of a task recovery evaluation and execution."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    attempt_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Target task identifier")
    checkpoint_id: str | None = Field(default=None, description="Checkpoint restored from, if any")
    policy: RecoveryPolicy = Field(..., description="Policy used for recovery")
    status: RecoveryStatus = Field(default=RecoveryStatus.STARTED)
    failure_reason: str | None = Field(default=None)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_iso_now)
    completed_at: str | None = Field(default=None)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["policy"] = self.policy.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecoveryAttemptRecord:
        return cls.model_validate(data)


class InterruptedOperationRecord(BaseModel):
    """Tracking record for granular operations to guarantee idempotency and crash recovery."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    operation_id: str = Field(default_factory=lambda: f"op_{uuid.uuid4().hex[:8]}")
    task_id: str
    step_id: str | None = None
    operation_type: str  # e.g., 'sql_execution', 'report_generation', 'approval'
    operation_key: str  # Deterministic unique key: e.g. {task_id}:{step_id}:{operation_type}
    status: OperationStatus = Field(default=OperationStatus.NOT_STARTED)
    error: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    created_at: str = Field(default_factory=_utc_iso_now)
    updated_at: str = Field(default_factory=_utc_iso_now)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterruptedOperationRecord:
        return cls.model_validate(data)


class ValidationResult(BaseModel):
    """Result from validating checkpoint integrity and safety for restoration."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    is_valid: bool = True
    checkpoint_id: str
    task_id: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RecoveryResult(BaseModel):
    """Result of recovering an interrupted or crashed task."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    success: bool
    task_id: str
    resumed_from_checkpoint_id: str | None = None
    policy_applied: RecoveryPolicy
    status: RecoveryStatus
    resumed_step_id: str | None = None
    actions_taken: list[str] = Field(default_factory=list)
    reusable_artifacts: list[str] = Field(default_factory=list)
    requires_user_action: bool = False
    message: str = ""
    error: str | None = None

