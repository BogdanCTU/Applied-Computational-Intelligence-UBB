"""Typed data models for Working, Episodic, and Semantic Memory subsystems."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskDecision(BaseModel):
    """A strategic or analytical choice made during task execution."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Target task ID")
    step_id: str | None = Field(default=None, description="Optional step ID during which decision occurred")
    decision_type: str = Field(..., description="Category, e.g. 'sql_strategy', 'chart_choice', 'error_recovery'")
    summary: str = Field(..., min_length=1, description="Concise statement of what was decided")
    rationale: str = Field(default="", description="Why this decision was chosen over alternatives")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_iso_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskDecision:
        return cls.model_validate(data)


class TaskToolCallRecord(BaseModel):
    """Audit record of an MCP tool invocation during task execution."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Target task ID")
    step_id: str | None = Field(default=None)
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = Field(default="")
    duration_ms: float = Field(default=0.0)
    status: str = Field(default="success")  # "success", "failed", "rejected", "timeout"
    error: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_iso_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskToolCallRecord:
        return cls.model_validate(data)


class TaskArtifactRecord(BaseModel):
    """Pointer to a generated document, exported file, or dataset reference."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    artifact_id: str = Field(default_factory=lambda: f"art_{uuid.uuid4().hex[:8]}")
    task_id: str = Field(..., description="Target task ID")
    step_id: str | None = Field(default=None)
    artifact_type: str = Field(..., description="'pdf_report', 'csv_report', 'sql_dataset_ref', 'chart_spec'")
    file_path: str = Field(..., description="Absolute or relative file path to artifact")
    file_size_bytes: int = Field(default=0)
    checksum: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_iso_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskArtifactRecord:
        return cls.model_validate(data)


class SemanticFact(BaseModel):
    """Validated database, business, or reporting domain knowledge."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    fact_id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:8]}")
    category: str = Field(
        ...,
        description="'table_description', 'table_relationship', 'business_metric', 'aggregation_constraint', 'data_quality'",
    )
    subject: str = Field(..., min_length=1, description="Primary subject entity (e.g. 'orders', 'revenue')")
    fact: str = Field(..., min_length=1, description="The validated truth or rule statement")
    provenance: str = Field(default="system", description="Origin of fact: 'schema_inspection', 'user_verified', etc.")
    is_validated: bool = Field(default=True, description="Whether this fact has been verified as true domain knowledge")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_iso_now)
    updated_at: str = Field(default_factory=_utc_iso_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticFact:
        return cls.model_validate(data)


class TaskHistoryItem(BaseModel):
    """Episodic historical summary representation of a past task."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    task_id: str
    user_request: str
    status: str
    current_step: str | None = None
    created_at: str
    updated_at: str
    error: str | None = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    execution_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskHistoryItem:
        return cls.model_validate(data)

