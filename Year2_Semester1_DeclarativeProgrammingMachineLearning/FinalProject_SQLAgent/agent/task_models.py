"""Typed data models and lifecycle states for Agent Task Planning and Execution.

Utilizes Pydantic v2 to enforce validation, explicit lifecycle transitions,
and serializable state representations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskStatus(str, Enum):
    """Explicit lifecycle states for an AgentTask."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    """Explicit lifecycle states for an individual TaskStep."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal task or step lifecycle transition is attempted."""


# Valid transition maps
VALID_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.PLANNING, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.WAITING_FOR_APPROVAL,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_FOR_APPROVAL: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}

VALID_STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
    StepStatus.PENDING: {StepStatus.READY, StepStatus.SKIPPED, StepStatus.CANCELLED},
    StepStatus.READY: {
        StepStatus.RUNNING,
        StepStatus.WAITING_FOR_APPROVAL,
        StepStatus.SKIPPED,
        StepStatus.CANCELLED,
    },
    StepStatus.RUNNING: {
        StepStatus.WAITING_FOR_APPROVAL,
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.CANCELLED,
    },
    StepStatus.WAITING_FOR_APPROVAL: {
        StepStatus.RUNNING,
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.CANCELLED,
    },
    StepStatus.COMPLETED: set(),
    StepStatus.FAILED: set(),
    StepStatus.SKIPPED: set(),
    StepStatus.CANCELLED: set(),
}


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStep(BaseModel):
    """Granular execution unit within a planned AgentTask."""

    model_config = ConfigDict(
        use_enum_values=False,
        extra="ignore",
        validate_assignment=True,
    )

    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., min_length=1, description="Concise title of the step")
    description: str = Field(default="", description="Detailed step instructions and objective")
    required_skill: str | None = Field(default=None, description="Identifier of relevant skill")
    required_tools: list[str] = Field(default_factory=list, description="List of MCP tool names")
    dependencies: list[str] = Field(
        default_factory=list, description="IDs of mandatory steps that must be COMPLETED before this step"
    )
    optional_dependencies: list[str] = Field(
        default_factory=list, description="IDs of optional steps that can be COMPLETED or SKIPPED before this step"
    )
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current lifecycle state")
    output_reference: str | None = Field(
        default=None, description="Pointer to result artifact, dataset, or cache key"
    )
    error: str | None = Field(default=None, description="Error explanation if step failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary step metadata")
    created_at: str = Field(default_factory=_utc_iso_now)
    updated_at: str = Field(default_factory=_utc_iso_now)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, val: Any) -> StepStatus:
        if isinstance(val, StepStatus):
            return val
        if isinstance(val, str):
            try:
                return StepStatus[val.upper()]
            except KeyError:
                return StepStatus(val.upper())
        raise ValueError(f"Invalid StepStatus: {val}")

    def transition_to(
        self,
        new_status: StepStatus | str,
        *,
        error: str | None = None,
        output_reference: str | None = None,
    ) -> None:
        """Safely transition this step to a new lifecycle state."""
        target = (
            new_status
            if isinstance(new_status, StepStatus)
            else StepStatus(str(new_status).upper())
        )
        if target == self.status:
            if error is not None:
                self.error = error
            if output_reference is not None:
                self.output_reference = output_reference
            return

        valid_targets = VALID_STEP_TRANSITIONS.get(self.status, set())
        if target not in valid_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition step '{self.step_id}' from {self.status.value} to {target.value}. "
                f"Allowed transitions from {self.status.value}: "
                f"{[s.value for s in valid_targets] or 'None (terminal state)'}"
            )

        self.status = target
        self.updated_at = _utc_iso_now()
        if error is not None:
            self.error = error
        if output_reference is not None:
            self.output_reference = output_reference

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
            StepStatus.CANCELLED,
        }

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskStep:
        return cls.model_validate(data)


class TaskPlan(BaseModel):
    """Structured plan composed of ordered/DAG steps generated for an AgentTask."""

    model_config = ConfigDict(
        use_enum_values=False,
        extra="ignore",
        validate_assignment=True,
    )

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Associated AgentTask identifier")
    steps: list[TaskStep] = Field(default_factory=list, description="Ordered steps for execution")
    rationale: str = Field(default="", description="High-level explanation of the plan")
    created_at: str = Field(default_factory=_utc_iso_now)

    @field_validator("steps")
    @classmethod
    def _validate_unique_step_ids(cls, steps: list[TaskStep]) -> list[TaskStep]:
        ids: set[str] = set()
        for step in steps:
            if step.step_id in ids:
                raise ValueError(f"Duplicate step_id detected in plan: '{step.step_id}'")
            ids.add(step.step_id)
        return steps

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskPlan:
        return cls.model_validate(data)


class AgentTask(BaseModel):
    """Primary task entity representing a natural-language reporting workflow."""

    model_config = ConfigDict(
        use_enum_values=False,
        extra="ignore",
        validate_assignment=True,
    )

    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    user_request: str = Field(..., min_length=1, description="Original user prompt")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current lifecycle state")
    current_step: str | None = Field(default=None, description="ID of currently executing step")
    steps: list[TaskStep] = Field(default_factory=list, description="Active execution steps")
    plan: TaskPlan | None = Field(default=None, description="Associated task plan")
    created_at: str = Field(default_factory=_utc_iso_now)
    updated_at: str = Field(default_factory=_utc_iso_now)
    error: str | None = Field(default=None, description="Terminal error description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary task metadata")

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, val: Any) -> TaskStatus:
        if isinstance(val, TaskStatus):
            return val
        if isinstance(val, str):
            try:
                return TaskStatus[val.upper()]
            except KeyError:
                return TaskStatus(val.upper())
        raise ValueError(f"Invalid TaskStatus: {val}")

    def transition_to(
        self,
        new_status: TaskStatus | str,
        *,
        error: str | None = None,
    ) -> None:
        """Safely transition this task to a new lifecycle state."""
        target = (
            new_status
            if isinstance(new_status, TaskStatus)
            else TaskStatus(str(new_status).upper())
        )
        if target == self.status:
            if error is not None:
                self.error = error
            return

        valid_targets = VALID_TASK_TRANSITIONS.get(self.status, set())
        if target not in valid_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition task '{self.task_id}' from {self.status.value} to {target.value}. "
                f"Allowed transitions from {self.status.value}: "
                f"{[s.value for s in valid_targets] or 'None (terminal state)'}"
            )

        self.status = target
        self.updated_at = _utc_iso_now()
        if error is not None:
            self.error = error

    def get_step(self, step_id: str) -> TaskStep | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def add_step(self, step: TaskStep) -> None:
        if any(s.step_id == step.step_id for s in self.steps):
            raise ValueError(f"Step with id '{step.step_id}' already exists in task '{self.task_id}'")
        self.steps.append(step)
        self.updated_at = _utc_iso_now()

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["status"] = self.status.value
        d["steps"] = [s.to_dict() for s in self.steps]
        if self.plan:
            d["plan"] = self.plan.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentTask:
        return cls.model_validate(data)
