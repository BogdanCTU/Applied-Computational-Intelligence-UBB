"""Base interfaces and deterministic extraction helpers for feature groups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import sparse


@dataclass
class ExtractionStats:
    """Tracks extraction success/failure statistics across a batch of methods."""

    group_name: str
    extractor_version: str
    total_items: int = 0
    failed_items: int = 0
    missing_semantic_items: int = 0
    notes: list[str] = field(default_factory=list)


class BaseFeatureExtractor(ABC):
    """Contract for every independent, testable feature group extractor."""

    group_name: str = "base"
    version: str = "1.0.0"

    def fit(self, records: list[dict[str, Any]]) -> "BaseFeatureExtractor":
        """Fit any vocabulary or normalization strictly on training records."""
        return self

    @abstractmethod
    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        """Deterministically transform method feature records into a CSR feature matrix."""

    def fit_transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        return self.fit(records).transform(records)

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """Return ordered feature names matching columns of transform()."""

    def schema_dict(self) -> dict[str, Any]:
        names = self.get_feature_names()
        return {
            "group_name": self.group_name,
            "version": self.version,
            "num_features": len(names),
            "feature_names": names,
        }


def extract_fixed_dense_matrix(
    records: list[dict[str, Any]],
    payload_key: str,
    columns: list[str],
    group_name: str,
    version: str,
) -> tuple[sparse.csr_matrix, ExtractionStats]:
    """Extract a deterministic CSR matrix from a fixed schema of numeric metric keys."""
    stats = ExtractionStats(group_name=group_name, extractor_version=version, total_items=len(records))
    if not records:
        return sparse.csr_matrix((0, len(columns)), dtype=np.float64), stats

    mat = np.zeros((len(records), len(columns)), dtype=np.float64)
    for i, rec in enumerate(records):
        if rec.get("extraction_failed"):
            stats.failed_items += 1
        if not rec.get("semantic_model_available", False):
            stats.missing_semantic_items += 1
        sub = rec.get(payload_key) or {}
        if not isinstance(sub, dict):
            stats.failed_items += 1
            continue
        for j, col in enumerate(columns):
            val = sub.get(col, 0.0)
            try:
                fval = float(val)
                mat[i, j] = 0.0 if (np.isnan(fval) or np.isinf(fval)) else fval
            except (TypeError, ValueError):
                mat[i, j] = 0.0
    return sparse.csr_matrix(mat), stats
