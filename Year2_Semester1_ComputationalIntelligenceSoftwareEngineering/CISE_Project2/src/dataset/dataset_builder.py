"""Dataset Builder for generating reproducible, leakage-free ML datasets."""
from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional, Set, Tuple

from src.database.repository import RepositoryDB
from src.utils.logger import setup_logger

logger = setup_logger("dataset_builder")

DEFAULT_NUMERICAL_FEATURES = [
    "loc",
    "logical_loc",
    "method_length",
    "parameter_count",
    "local_variable_count",
    "statement_count",
    "return_count",
    "cyclomatic_complexity",
    "max_nesting_depth",
    "boolean_operator_count",
    "logical_operator_count",
    "conditional_expression_count",
    "if_count",
    "switch_count",
    "loop_count",
    "try_catch_count",
    "throw_count",
    "break_continue_count",
    "method_call_count",
    "field_access_count",
    "property_access_count",
    "assignment_count",
    "object_creation_count",
    "is_static",
    "is_async",
    "is_generic",
]

IDENTIFIER_COLUMNS = [
    "observation_id",
    "repository_id",
    "repository_name",
    "commit_sha",
    "file_path",
    "class_name",
    "method_name",
    "method_signature",
    "label",
    "label_confidence",
    "evidence_category",
]


class DatasetBuilder:
    """Builds, validates, and snapshots machine learning datasets from observations and features."""

    def __init__(self, db: RepositoryDB) -> None:
        self.db = db

    def generate_dataset_snapshot(
        self,
        name: str,
        version: str,
        description: str = "",
        exclude_uncertain: bool = True,
        feature_names: Optional[List[str]] = None,
        repository_id: Optional[int] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """Create a versioned dataset snapshot and return (dataset_id, stats)."""
        selected_features = feature_names or DEFAULT_NUMERICAL_FEATURES

        # 1. Fetch observations
        all_obs = self.db.list_observations(repository_id=repository_id)
        if not all_obs:
            raise ValueError("No observations available in database to build dataset.")

        valid_observation_ids: List[int] = []
        uncertain_excluded = 0
        missing_features = 0
        seen_fingerprints: Set[str] = set()
        duplicates_count = 0

        for obs in all_obs:
            # Filter uncertain labels
            if exclude_uncertain and obs["label"] == -1:
                uncertain_excluded += 1
                continue

            # Check if features exist and were extracted successfully
            feat = self.db.get_features_by_observation_id(obs["id"])
            if not feat or feat.get("status") == "failed":
                missing_features += 1
                continue

            # Duplicate check based on repository + method signature + source hash
            fingerprint = f"{obs['repository_id']}:{obs['file_path']}:{obs['method_signature']}:{obs['source_code']}"
            if fingerprint in seen_fingerprints:
                duplicates_count += 1
                continue
            seen_fingerprints.add(fingerprint)

            valid_observation_ids.append(obs["id"])

        if not valid_observation_ids:
            raise ValueError("No valid observations with extracted features remained after filtering.")

        # 2. Persist snapshot in database
        dataset_id = self.db.create_dataset(
            name=name,
            version=version,
            description=description,
            observation_ids=valid_observation_ids,
            feature_names=selected_features,
        )

        stats = self.compute_dataset_statistics(dataset_id, selected_features)
        stats.update({
            "uncertain_excluded": uncertain_excluded,
            "missing_features_excluded": missing_features,
            "duplicates_excluded": duplicates_count,
        })

        logger.info(f"Generated dataset snapshot '{name}' v{version} (ID: {dataset_id}) with {len(valid_observation_ids)} observations.")
        return dataset_id, stats

    def compute_dataset_statistics(self, dataset_id: int, feature_names: List[str]) -> Dict[str, Any]:
        """Compute summary statistics for a dataset snapshot."""
        records = self.db.get_dataset_dataframe_records(dataset_id)
        if not records:
            return {"total": 0, "buggy": 0, "clean": 0, "class_ratio": 0.0}

        df = pd.DataFrame(records)
        total = len(df)
        buggy = int((df["label"] == 1).sum())
        clean = int((df["label"] == 0).sum())
        uncertain = int((df["label"] == -1).sum())

        repo_dist = df["repository_name"].value_counts().to_dict() if "repository_name" in df else {}

        # Check for missing values in features
        missing_vals: Dict[str, int] = {}
        for f in feature_names:
            if f in df:
                missing_vals[f] = int(df[f].isna().sum())

        return {
            "total_observations": total,
            "buggy_count": buggy,
            "clean_count": clean,
            "uncertain_count": uncertain,
            "buggy_ratio": round(buggy / total, 4) if total > 0 else 0.0,
            "clean_ratio": round(clean / total, 4) if total > 0 else 0.0,
            "repository_distribution": repo_dist,
            "missing_values_per_feature": missing_vals,
        }

    def get_features_and_labels(
        self,
        dataset_id: int,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """Extract feature matrix X, target series y, and metadata dataframe for ML pipeline."""
        records = self.db.get_dataset_dataframe_records(dataset_id)
        if not records:
            raise ValueError(f"No records found for dataset ID #{dataset_id}")

        df = pd.DataFrame(records)
        target_features = feature_names or DEFAULT_NUMERICAL_FEATURES

        # Ensure all requested feature columns exist and are numeric
        for col in target_features:
            if col not in df.columns:
                df[col] = 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        X = df[target_features].copy()
        y = df["label"].astype(int)

        # Metadata columns strictly separated from features to prevent leakage
        meta_cols = [c for c in IDENTIFIER_COLUMNS if c in df.columns]
        metadata = df[meta_cols].copy()

        return X, y, metadata

