"""Composable feature pipeline combining independent extractors with strict train/test separation."""

from __future__ import annotations

from typing import Any

from scipy import sparse

from bug_detector.config.settings import EXPERIMENT_DEFINITIONS, FeatureConfig
from bug_detector.features.ast_features import AstFeatureExtractor
from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats
from bug_detector.features.control_flow import ControlFlowFeatureExtractor
from bug_detector.features.data_flow import DataFlowFeatureExtractor
from bug_detector.features.lexical import LexicalFeatureExtractor
from bug_detector.features.structural import StructuralFeatureExtractor


class FeaturePipeline:
    """Composes ordered feature group extractors and enforces train-only fitting."""

    version = "1.0.0"

    def __init__(
        self,
        groups: list[str] | None = None,
        feature_config: FeatureConfig | None = None,
    ) -> None:
        self.feature_config = feature_config or FeatureConfig()
        if groups is not None:
            self.groups = list(groups)
        else:
            self.groups = list(
                EXPERIMENT_DEFINITIONS.get(
                    self.feature_config.experiment_code,
                    self.feature_config.enabled_groups,
                )
            )
        self.extractors: list[BaseFeatureExtractor] = [self._build_extractor(g) for g in self.groups]
        self._is_fitted = False

    def _build_extractor(self, group_name: str) -> BaseFeatureExtractor:
        if group_name == "lexical":
            return LexicalFeatureExtractor(
                max_token_features=self.feature_config.tfidf_max_token_features,
                max_api_features=self.feature_config.tfidf_max_api_features,
                ngram_range=(self.feature_config.tfidf_ngram_min, self.feature_config.tfidf_ngram_max),
                min_df=self.feature_config.tfidf_min_df,
            )
        if group_name == "ast":
            return AstFeatureExtractor()
        if group_name == "control_flow":
            return ControlFlowFeatureExtractor()
        if group_name == "data_flow":
            return DataFlowFeatureExtractor()
        if group_name == "structural":
            return StructuralFeatureExtractor()
        raise ValueError(f"Unknown feature group: {group_name}")

    def fit(self, train_records: list[dict[str, Any]]) -> "FeaturePipeline":
        for ext in self.extractors:
            ext.fit(train_records)
        self._is_fitted = True
        return self

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, dict[str, ExtractionStats]]:
        if not self._is_fitted:
            raise RuntimeError("FeaturePipeline must be fitted on training data before calling transform().")
        blocks: list[sparse.csr_matrix] = []
        stats_by_group: dict[str, ExtractionStats] = {}
        for ext in self.extractors:
            mat, stats = ext.transform(records)
            blocks.append(mat)
            stats_by_group[ext.group_name] = stats
        combined = sparse.hstack(blocks, format="csr") if len(blocks) > 1 else blocks[0]
        return combined, stats_by_group

    def fit_transform(
        self, train_records: list[dict[str, Any]]
    ) -> tuple[sparse.csr_matrix, dict[str, ExtractionStats]]:
        return self.fit(train_records).transform(train_records)

    def get_feature_names(self) -> list[str]:
        names: list[str] = []
        for ext in self.extractors:
            names.extend(ext.get_feature_names())
        return names

    def get_feature_group_map(self) -> dict[str, list[int]]:
        """Map each group name to its column indices in the combined matrix."""
        mapping: dict[str, list[int]] = {}
        cursor = 0
        for ext in self.extractors:
            n = len(ext.get_feature_names())
            mapping[ext.group_name] = list(range(cursor, cursor + n))
            cursor += n
        return mapping

    def schema_dict(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.version,
            "groups": self.groups,
            "total_features": len(self.get_feature_names()),
            "group_schemas": [ext.schema_dict() for ext in self.extractors],
        }
