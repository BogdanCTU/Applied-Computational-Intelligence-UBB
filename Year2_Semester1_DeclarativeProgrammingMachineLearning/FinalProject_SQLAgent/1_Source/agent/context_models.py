"""Data models, execution stages, and build reports for ContextBuilder."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExecutionStage(str, Enum):
    """Recognized execution stages in the agent lifecycle."""

    REQUEST_PLANNING = "REQUEST_PLANNING"
    SCHEMA_DISCOVERY = "SCHEMA_DISCOVERY"
    SQL_GENERATION = "SQL_GENERATION"
    SQL_VALIDATION = "SQL_VALIDATION"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    CHART_PLANNING = "CHART_PLANNING"
    REPORT_GENERATION = "REPORT_GENERATION"
    FINAL_RESPONSE = "FINAL_RESPONSE"


class SectionPriority(int, Enum):
    """Relative importance for context budget allocation (higher values win)."""

    MANDATORY = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ContextError(Exception):
    """Base exception for ContextBuilder errors."""


class ContextBudgetExceededError(ContextError):
    """Raised when mandatory context sections exceed the available input token budget."""


class InvalidStageError(ContextError):
    """Raised when an unrecognized execution stage is provided."""


# ---------------------------------------------------------------------------
# Section & Report Models
# ---------------------------------------------------------------------------


class ContextSection(BaseModel):
    """An individual block of context evaluated for inclusion."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str = Field(..., min_length=1)
    content: str
    priority: SectionPriority = SectionPriority.MEDIUM
    is_mandatory: bool = False
    category: str = Field(
        default="other",
        description="Categorical bucket: system_instructions, skills, database_schema, "
        "task_and_checkpoint, working_memory, episodic_memory, semantic_memory, "
        "tool_results, user_request, other",
    )
    estimated_tokens: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExcludedSection(BaseModel):
    """Details on a context section that was omitted due to budget constraints."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    name: str
    category: str
    priority: SectionPriority
    estimated_tokens: int
    reason: str


class ContextComponentBreakdown(BaseModel):
    """Estimated token distribution across context categories."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    system_instructions: int = 0
    skills: int = 0
    database_schema: int = 0
    task_and_checkpoint: int = 0
    working_memory: int = 0
    episodic_memory: int = 0
    semantic_memory: int = 0
    tool_results: int = 0
    conversation_history: int = 0
    user_request: int = 0
    other: int = 0

    def total(self) -> int:
        return sum(
            getattr(self, f)
            for f in type(self).model_fields.keys()
            if isinstance(getattr(self, f), int)
        )

    def to_dict(self) -> dict[str, int]:
        return {
            k: getattr(self, k)
            for k in type(self).model_fields.keys()
            if getattr(self, k) > 0
        }


class ContextBuildReport(BaseModel):
    """Audit report detailing token allocation and context composition."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    @model_validator(mode="before")
    @classmethod
    def _sync_context_windows(cls, data: Any) -> Any:
        if isinstance(data, dict):
            num = data.get("num_ctx")
            if num is not None:
                if "effective_context_window" not in data:
                    data["effective_context_window"] = num
                if "configured_context_window" not in data:
                    data["configured_context_window"] = num
        return data

    stage: ExecutionStage
    num_ctx: int = 131072
    configured_context_window: int = 131072
    effective_context_window: int = 131072
    reserved_output_tokens: int = 1024
    safety_margin_tokens: int = 256
    available_input_tokens: int = 0
    estimated_input_tokens: int = 0
    remaining_tokens: int = 0
    component_breakdown: dict[str, int] = Field(default_factory=dict)
    included_sections: list[str] = Field(default_factory=list)
    included_categories: list[str] = Field(default_factory=list)
    excluded_sections: list[ExcludedSection] = Field(default_factory=list)
    excluded_categories: list[str] = Field(default_factory=list)
    exclusion_reasons: list[str] = Field(default_factory=list)
    model_validation_status: str = "compatible"
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utc_iso_now)

    def summary_text(self) -> str:
        """Render a formatted summary suitable for the Activity Inspector."""
        lines = [
            "Context Assembly Report",
            f"Execution Stage: {self.stage.value}",
            f"Configured Context Window: {self.configured_context_window:,} tokens",
            f"Effective Context Window: {self.effective_context_window:,} tokens",
            f"Model Capability Validation: {self.model_validation_status.upper()}",
            f"Reserved Output: {self.reserved_output_tokens:,} tokens | Safety Margin: {self.safety_margin_tokens:,} tokens",
            f"Available Input Budget: {self.available_input_tokens:,} tokens",
            f"Estimated Input Tokens: {self.estimated_input_tokens:,} tokens (Remaining: {self.remaining_tokens:,})",
            "",
            "Component Breakdown:",
        ]

        if self.component_breakdown:
            for k, v in sorted(self.component_breakdown.items(), key=lambda x: -x[1]):
                lines.append(f"- {k}: {v:,}")
        else:
            lines.append("- (none)")

        lines.append("")
        lines.append(
            f"Included Sections: {', '.join(self.included_sections) if self.included_sections else 'none'}"
        )
        if self.included_categories:
            lines.append(f"Included Categories: {', '.join(self.included_categories)}")

        if self.excluded_sections:
            lines.append("Excluded Sections:")
            for exc in self.excluded_sections:
                lines.append(
                    f"- {exc.name} ({exc.estimated_tokens:,} tokens, priority={exc.priority.name}): {exc.reason}"
                )
        else:
            lines.append("Excluded Sections: None")

        if self.excluded_categories:
            lines.append(f"Excluded Categories: {', '.join(self.excluded_categories)}")
        if self.exclusion_reasons:
            lines.append("Exclusion Reasons:")
            for r in self.exclusion_reasons:
                lines.append(f"- {r}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)


class AssembledContext(BaseModel):
    """Final assembled context payload ready for Ollama."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    stage: ExecutionStage
    system_prompt: str
    user_prompt: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    report: ContextBuildReport

    @property
    def estimated_input_tokens(self) -> int:
        return self.report.estimated_input_tokens
