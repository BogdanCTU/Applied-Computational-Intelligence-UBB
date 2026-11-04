"""Structured event models and security sanitizers for agent execution transparency."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Keys to sanitize from argument and result logs
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(?:password|passwd|token|secret|api[_-]?key|auth|bearer|credentials|private[_-]?key)",
    re.IGNORECASE,
)


def mask_sensitive_data(value: Any, *, max_depth: int = 5) -> Any:
    """Recursively scrub sensitive keys and credentials from data payloads."""
    if max_depth <= 0:
        return "<depth-limit>"

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for k, v in value.items():
            if _SENSITIVE_KEY_PATTERNS.search(str(k)):
                cleaned[k] = "[REDACTED_CREDENTIAL]"
            else:
                cleaned[k] = mask_sensitive_data(v, max_depth=max_depth - 1)
        return cleaned

    if isinstance(value, (list, tuple)):
        # Limit preview size of large arrays
        if len(value) > 30:
            preview = [mask_sensitive_data(x, max_depth=max_depth - 1) for x in value[:20]]
            preview.append(f"... [+{len(value) - 20} more items]")
            return preview
        return [mask_sensitive_data(x, max_depth=max_depth - 1) for x in value]

    if isinstance(value, str):
        # Mask obvious inline JWT / bearer patterns if present
        if len(value) > 200 and "eyJ" in value:
            return "[REDACTED_TOKEN_PATTERN]"
        return value

    return value


class ActivityCategory(str, Enum):
    USER_REQUEST = "User Request"
    AGENT_STATUS = "Agent Status"
    REASONING_SUMMARY = "Reasoning Summary"
    PLANNING = "Planning"
    TOOL_CALL = "Tool Call"
    TOOL_ARGUMENTS = "Tool Arguments"
    TOOL_RESULT = "Tool Result"
    SQL_GENERATION = "SQL Generation"
    SQL_VALIDATION = "SQL Validation"
    APPROVAL_REQUIRED = "Approval Required"
    APPROVAL_RESULT = "Approval Result"
    SQL_EXECUTION = "SQL Execution"
    SQL_RESULT = "SQL Result"
    REPORT_PLANNING = "Report Planning"
    REPORT_GENERATION = "Report Generation"
    COMPLETION = "Completion"
    ERROR = "Error"


@dataclass
class ActivityEvent:
    """Chronological event card representing an observable agent action or decision."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    category: str = ActivityCategory.AGENT_STATUS.value
    title: str = ""
    description: str = ""
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result_summary: str | None = None
    duration_ms: float | None = None
    status: str = "success"  # "in_progress", "success", "waiting_approval", "rejected", "failed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.arguments:
            d["arguments"] = mask_sensitive_data(self.arguments)
        return d

    @classmethod
    def create(
        cls,
        category: ActivityCategory | str,
        title: str,
        description: str = "",
        *,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        result_summary: str | None = None,
        duration_ms: float | None = None,
        status: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> "ActivityEvent":
        cat_val = category.value if isinstance(category, ActivityCategory) else str(category)
        clean_args = mask_sensitive_data(arguments) if arguments else None
        return cls(
            category=cat_val,
            title=title,
            description=description,
            tool_name=tool_name,
            arguments=clean_args,
            result_summary=result_summary,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
        )

