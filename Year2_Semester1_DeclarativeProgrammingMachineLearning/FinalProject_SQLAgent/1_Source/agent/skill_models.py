"""Typed data models, token estimation, and safe YAML parser for Domain Skills."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CURRENT_SKILL_SYSTEM_VERSION = 1


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(text: str) -> int:
    """Deterministic token estimation (~3.8 characters per token for English markdown)."""
    if not text:
        return 0
    # Conservative upper bound: at least 1 token per 4 chars + 1 for non-empty text
    return max(1, (len(text) + 3) // 4)


def _parse_yaml_scalar(val_str: str) -> Any:
    """Parse basic scalar types (booleans, numbers, quoted/unquoted strings)."""
    val_str = val_str.strip()
    if (val_str.startswith('"') and val_str.endswith('"')) or (
        val_str.startswith("'") and val_str.endswith("'")
    ):
        return val_str[1:-1]

    # Strip inline comments for unquoted scalar values
    if "#" in val_str:
        val_str = val_str.split("#", 1)[0].strip()

    lower = val_str.lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    if lower in ("null", "none", "~", ""):
        return None

    try:
        return int(val_str)
    except ValueError:
        pass

    try:
        return float(val_str)
    except ValueError:
        pass

    return val_str


def safe_parse_yaml(raw_text: str) -> dict[str, Any]:
    """Parse clean metadata YAML without third-party dependencies.

    Supports comments, key-value mappings, block lists (- item), and inline lists ([a, b]).
    Falls back to standard JSON if valid JSON payload.
    """
    cleaned = raw_text.strip()
    if not cleaned:
        return {}

    # JSON fallback
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned)
        except Exception:
            pass

    result: dict[str, Any] = {}
    lines = cleaned.splitlines()
    current_key: str | None = None
    current_list: list[Any] | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Block list element: e.g. "- item"
        if stripped.startswith("- ") and current_key is not None:
            item_str = stripped[2:].strip()
            item_val = _parse_yaml_scalar(item_str)
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            current_list.append(item_val)
            continue

        # Key-value line: e.g. "key: value"
        if ":" in stripped:
            parts = stripped.split(":", 1)
            k = parts[0].strip()
            v_str = parts[1].strip()

            current_list = None
            if not v_str:
                current_key = k
                current_list = []
                result[k] = current_list
            else:
                current_key = k
                # Inline list: e.g. "[a, b, c]"
                if v_str.startswith("[") and v_str.endswith("]"):
                    inner = v_str[1:-1].strip()
                    items = [
                        _parse_yaml_scalar(x.strip())
                        for x in inner.split(",")
                        if x.strip()
                    ]
                    result[k] = items
                else:
                    result[k] = _parse_yaml_scalar(v_str)

    return result


class SkillCategory(str, Enum):
    """Recognized domain skill classifications."""

    SQL = "sql"
    DATA_ANALYSIS = "data_analysis"
    REPORTING = "reporting"
    DATA_VALIDATION = "data_validation"
    GENERAL = "general"


class SkillMetadata(BaseModel):
    """Validated metadata schema for a Domain Skill."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    skill_id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    supported_task_types: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    is_enabled: bool = Field(default=True)
    min_system_version: int = Field(default=CURRENT_SKILL_SYSTEM_VERSION, ge=1)
    author: str = Field(default="system")
    created_at: str = Field(default_factory=_utc_iso_now)
    updated_at: str = Field(default_factory=_utc_iso_now)

    @field_validator("version")
    @classmethod
    def _validate_semver(cls, v: str) -> str:
        parts = v.strip().split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(
                f"Invalid semver version '{v}': must follow 'MAJOR.MINOR.PATCH' (e.g. '1.0.0')"
            )
        return v.strip()

    @field_validator("min_system_version")
    @classmethod
    def _validate_system_version(cls, v: int) -> int:
        if v > CURRENT_SKILL_SYSTEM_VERSION:
            raise ValueError(
                f"Skill requires system version {v}, but current system version is {CURRENT_SKILL_SYSTEM_VERSION}."
            )
        return v


class LoadedSkill(BaseModel):
    """In-memory representation of an active Markdown domain skill."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    metadata: SkillMetadata
    content: str
    file_path: str
    char_count: int
    estimated_tokens: int
    loaded_at: str = Field(default_factory=_utc_iso_now)

    @property
    def skill_id(self) -> str:
        return self.metadata.skill_id

    @property
    def name(self) -> str:
        return self.metadata.name


class SkillLoadResult(BaseModel):
    """Aggregate result of selectively loading skills under a token budget."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    loaded_skills: list[LoadedSkill] = Field(default_factory=list)
    excluded_skills: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    token_budget: int | None = None
    errors: list[str] = Field(default_factory=list)


class SkillValidationResult(BaseModel):
    """Integrity and security verification report for a discovered skill."""

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    is_valid: bool = True
    skill_id: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

