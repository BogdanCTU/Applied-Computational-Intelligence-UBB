"""Typed dataset record, exclusion, and audit report schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DatasetSampleRecord(BaseModel):
    """Canonical dataset sample enforcing all 18 required provenance columns."""

    sample_id: str
    repository_id: str
    repository_url: str
    commit_sha: str
    parent_commit_sha: str | None = None
    file_path: str
    class_name: str
    method_name: str
    method_signature: str
    source_code: str
    label: Literal[0, 1]
    label_source: str
    verification_status: str
    bug_type: str
    bug_fix_reference: str | None = None
    source_hash: str
    collection_timestamp: str
    dataset_version: str

    # Supporting structural & split provenance
    normalized_source: str = ""
    structural_hash: str = ""
    pair_id: str | None = None
    commit_timestamp: str | None = None
    commit_message: str | None = None
    severity: str | None = None
    type_kind: str = "class"
    start_line: int = 1
    end_line: int = 1
    is_constructor: bool = False
    is_static: bool = False
    is_async: bool = False
    is_generic: bool = False
    is_expression_bodied: bool = False
    extraction_mode: str = "file"
    split_partition: str = "unassigned"
    source_origin: str = "unknown"
    stars: int = 0
    local_path: str | None = None
    features_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sample_id", "repository_id", "file_path", "class_name", "method_name", "source_code", "source_hash")
    @classmethod
    def non_empty_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Required dataset metadata field cannot be empty")
        return v


class ExclusionRecord(BaseModel):
    """Audit record describing why a candidate sample or commit was excluded."""

    source_origin: str
    repository_id: str | None = None
    external_ref: str | None = None
    file_path: str | None = None
    method_name: str | None = None
    exclusion_reason: str
    details: str | None = None


class DatasetAuditReport(BaseModel):
    """Comprehensive dataset quality and provenance audit report."""

    dataset_version: str
    generated_at: str
    total_records_collected: int
    valid_records: int
    invalid_records: int
    bug_count: int
    clean_count: int
    bug_ratio: float
    repository_count: int
    repositories_by_origin: dict[str, int]
    label_source_distribution: dict[str, int]
    defect_category_distribution: dict[str, int]
    verification_status_distribution: dict[str, int]
    duplicate_statistics: dict[str, int]
    missing_metadata_counts: dict[str, int]
    exclusion_statistics: dict[str, int]
    split_partition_distribution: dict[str, int]
    dataset_sha256: str | None = None
