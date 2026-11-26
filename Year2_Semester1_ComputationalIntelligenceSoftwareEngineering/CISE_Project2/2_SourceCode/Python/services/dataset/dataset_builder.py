"""Dataset Builder for generating reproducible, leakage-free class-level and legacy method-level ML datasets."""
from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional, Set, Tuple

from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from utils.logger import setup_logger
from utils.source_classifier import is_production_csharp_file

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

CLASS_IDENTIFIER_COLUMNS = [
    "class_observation_id",
    "observation_id",
    "repository_id",
    "repository_name",
    "commit_sha",
    "parent_sha",
    "bug_fix_commit_sha",
    "bug_inducing_commit_sha",
    "file_path",
    "namespace_name",
    "class_name",
    "qualified_class_name",
    "type_kind",
    "start_line",
    "end_line",
    "is_nested",
    "source_fingerprint",
    "structural_fingerprint",
    "label",
    "label_confidence",
    "szz_trace_count",
    "localization_status",
    "affected_methods_json",
    "affected_line_ranges_json",
    "evidence_category",
]

CLASS_FEATURE_DEFINITIONS: Dict[str, str] = {
    "class_loc": "Non-empty physical lines in class/struct/record excluding nested types.",
    "class_logical_loc": "Total executable statements and expression bodies across owned class members.",
    "method_count": "Number of direct method declarations in the type.",
    "constructor_count": "Number of direct constructors (including primary constructors).",
    "property_count": "Number of direct property declarations in the type.",
    "field_count": "Number of direct field variable declarators in the type.",
    "nested_type_count": "Number of direct nested class/struct/record/interface declarations.",
    "total_parameter_count": "Sum of formal parameters across direct callable members.",
    "max_parameter_count": "Maximum parameter count among direct callable members.",
    "total_local_variable_count": "Sum of local variable declarations across direct members.",
    "total_statement_count": "Sum of statement AST nodes across direct members.",
    "total_return_count": "Sum of return statements and expression bodies across direct members.",
    "total_cyclomatic_complexity": "Weighted Methods per Class (sum of McCabe complexities, minimum 1).",
    "mean_method_complexity": "Mean McCabe cyclomatic complexity across direct callable members.",
    "max_method_complexity": "Maximum McCabe cyclomatic complexity among direct callable members.",
    "std_method_complexity": "Population standard deviation of McCabe complexity across callable members.",
    "max_nesting_depth": "Maximum lexical control-flow nesting depth across direct members.",
    "mean_nesting_depth": "Mean maximum nesting depth across direct callable members.",
    "total_boolean_operator_count": "Sum of !, &, |, ^ operators across direct members.",
    "total_logical_operator_count": "Sum of &&, ||, ?? short-circuit operators across direct members.",
    "total_conditional_expression_count": "Sum of ternary (? :) conditional expressions.",
    "total_if_count": "Total if statements across direct members.",
    "total_switch_count": "Total switch statements and switch expressions across direct members.",
    "total_loop_count": "Total for/foreach/while/do-while loops across direct members.",
    "total_try_catch_count": "Total try-catch-finally blocks across direct members.",
    "total_throw_count": "Total throw statements and expressions across direct members.",
    "total_break_continue_count": "Total break and continue jump statements across direct members.",
    "total_method_call_count": "Total method invocation expressions across direct members.",
    "total_field_access_count": "Total lowercase/underscore member field accesses.",
    "total_property_access_count": "Total PascalCase member property accesses.",
    "total_assignment_count": "Total assignment expressions across direct members.",
    "total_object_creation_count": "Total explicit and implicit 'new' object creations.",
    "static_method_count": "Count of static methods declared in the type.",
    "async_method_count": "Count of async methods declared in the type.",
    "generic_method_count": "Count of generic methods declared in the type.",
    "high_complexity_method_count": "Count of callable members with cyclomatic complexity >= 10.",
    "large_method_count": "Count of callable members with loc >= 40 or statements >= 25.",
    "complexity_concentration": "Ratio of max_method_complexity to total_cyclomatic_complexity.",
    "structural_density": "Ratio of total_statement_count to class_loc.",
    "wmc_density": "Ratio of total_cyclomatic_complexity to class_loc.",
}


class DatasetBuilder:
    """Builds, validates, deduplicates, and snapshots ML datasets from observations and features."""

    def __init__(self, db: RepositoryDB) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Class-Level Dataset Construction (v3.0.0+)
    # ---------------------------------------------------------
    def generate_class_dataset_snapshot(
        self,
        name: str,
        version: str,
        description: str = "",
        exclude_uncertain: bool = True,
        feature_names: Optional[List[str]] = None,
        repository_ids: Optional[List[int]] = None,
        deduplicate_exact_source: bool = True,
        deduplicate_repeated_revisions: bool = True,
        overwrite: bool = False,
    ) -> Tuple[int, Dict[str, Any]]:
        """Build a deduplicated, leakage-free class-level dataset snapshot and return (dataset_id, stats)."""
        selected_features = feature_names or list(CLASS_FEATURE_NAMES)
        records = self.db.list_class_observations_with_features(
            repository_ids=repository_ids,
            exclude_uncertain=exclude_uncertain,
        )
        if not records:
            raise ValueError("No class observations with extracted features available to build dataset.")

        # Track conflicting buggy class fingerprints/identities so Label 0 never duplicates Label 1
        buggy_source_fps: Set[str] = {
            r["source_fingerprint"] for r in records if r["label"] == 1 and r.get("source_fingerprint")
        }
        buggy_class_keys: Set[Tuple[int, str, str]] = {
            (r["repository_id"], r["file_path"], r["qualified_class_name"])
            for r in records if r["label"] == 1
        }

        valid_ids: List[int] = []
        test_files_excluded = 0
        conflicting_clean_excluded = 0
        intra_repo_exact_dups = 0
        cross_repo_exact_dups = 0
        repeated_revision_dups = 0
        historical_revisions_retained = 0

        seen_source_fps: Dict[str, int] = {}
        seen_revision_structs: Set[Tuple[int, str, str, str]] = set()
        seen_class_identities: Set[Tuple[int, str, str]] = set()

        # Process positive (1) records before candidate-clean (0) so Label 1 wins any collision
        sorted_records = sorted(records, key=lambda r: (0 if r["label"] == 1 else 1, r["class_observation_id"]))

        for rec in sorted_records:
            if not is_production_csharp_file(rec["file_path"]):
                test_files_excluded += 1
                continue

            repo_id = int(rec["repository_id"])
            src_fp = rec.get("source_fingerprint") or ""
            struct_fp = rec.get("structural_fingerprint") or ""
            cls_key = (repo_id, rec["file_path"], rec["qualified_class_name"])

            if rec["label"] == 0:
                if src_fp in buggy_source_fps or cls_key in buggy_class_keys:
                    conflicting_clean_excluded += 1
                    continue

            # Exact source code deduplication
            if src_fp and src_fp in seen_source_fps:
                prev_repo = seen_source_fps[src_fp]
                if prev_repo == repo_id:
                    intra_repo_exact_dups += 1
                else:
                    cross_repo_exact_dups += 1
                if deduplicate_exact_source:
                    continue

            # Near-duplicate / repeated class revision with identical structural fingerprint
            rev_key = (repo_id, rec["file_path"], rec["qualified_class_name"], struct_fp)
            if rev_key in seen_revision_structs:
                repeated_revision_dups += 1
                if deduplicate_repeated_revisions:
                    continue

            if cls_key in seen_class_identities:
                historical_revisions_retained += 1

            seen_source_fps.setdefault(src_fp, repo_id)
            seen_revision_structs.add(rev_key)
            seen_class_identities.add(cls_key)
            valid_ids.append(int(rec["class_observation_id"]))

        if not valid_ids:
            raise ValueError("No valid class observations remained after filtering and deduplication.")

        dataset_id = self.db.create_class_dataset(
            name=name,
            version=version,
            description=description,
            class_observation_ids=valid_ids,
            feature_names=selected_features,
            feature_schema_version="3.0.0",
            overwrite=overwrite,
        )

        duplicate_analysis = {
            "total_candidate_records": len(records),
            "retained_records": len(valid_ids),
            "test_files_excluded": test_files_excluded,
            "conflicting_clean_excluded": conflicting_clean_excluded,
            "intra_repo_exact_duplicates_removed": intra_repo_exact_dups if deduplicate_exact_source else 0,
            "cross_repo_exact_duplicates_removed": cross_repo_exact_dups if deduplicate_exact_source else 0,
            "intra_repo_exact_duplicates_detected": intra_repo_exact_dups,
            "cross_repo_exact_duplicates_detected": cross_repo_exact_dups,
            "repeated_structural_revision_duplicates": repeated_revision_dups,
            "legitimate_historical_revisions_retained": historical_revisions_retained,
        }

        stats = self.compute_class_dataset_statistics(dataset_id, selected_features)
        stats["duplicate_analysis"] = duplicate_analysis
        logger.info(
            f"Generated class dataset '{name}' v{version} (ID: {dataset_id}): "
            f"{stats['total_observations']} classes across {stats['repository_count']} repos."
        )
        return dataset_id, stats

    def compute_class_dataset_statistics(self, dataset_id: int, feature_names: List[str]) -> Dict[str, Any]:
        records = self.db.get_class_dataset_dataframe_records(dataset_id)
        if not records:
            return {"total_observations": 0, "buggy_count": 0, "clean_count": 0, "repository_count": 0}

        df = pd.DataFrame(records)
        total = len(df)
        buggy = int((df["label"] == 1).sum())
        clean = int((df["label"] == 0).sum())
        uncertain = int((df["label"] == -1).sum())
        repo_dist = df["repository_name"].value_counts().to_dict() if "repository_name" in df else {}

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
            "repository_count": len(repo_dist),
            "repository_distribution": repo_dist,
            "missing_values_per_feature": missing_vals,
        }

    def get_class_features_and_labels(
        self,
        dataset_id: int,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        records = self.db.get_class_dataset_dataframe_records(dataset_id)
        if not records:
            raise ValueError(f"No records found for class dataset ID #{dataset_id}")

        df = pd.DataFrame(records)
        target_features = feature_names or list(CLASS_FEATURE_NAMES)

        for col in target_features:
            if col not in df.columns:
                df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        X = df[target_features].copy()
        y = df["label"].astype(int)
        meta_cols = [c for c in CLASS_IDENTIFIER_COLUMNS if c in df.columns]
        metadata = df[meta_cols].copy()
        return X, y, metadata

    # ---------------------------------------------------------
    # Historical Method-Level Dataset Construction (Preserved)
    # ---------------------------------------------------------
    def generate_dataset_snapshot(
        self,
        name: str,
        version: str,
        description: str = "",
        exclude_uncertain: bool = True,
        feature_names: Optional[List[str]] = None,
        repository_id: Optional[int] = None,
        repository_ids: Optional[List[int]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """Create a versioned method dataset snapshot and return (dataset_id, stats)."""
        selected_features = feature_names or DEFAULT_NUMERICAL_FEATURES

        if repository_ids is not None:
            all_obs = [obs for rid in repository_ids for obs in self.db.list_observations(repository_id=rid)]
        else:
            all_obs = self.db.list_observations(repository_id=repository_id)
        if not all_obs:
            raise ValueError("No observations available in database to build dataset.")

        valid_observation_ids: List[int] = []
        uncertain_excluded = 0
        missing_features = 0
        test_files_excluded = 0
        seen_fingerprints: Set[str] = set()
        duplicates_count = 0

        for obs in all_obs:
            if not is_production_csharp_file(obs["file_path"]):
                test_files_excluded += 1
                continue

            if exclude_uncertain and obs["label"] == -1:
                uncertain_excluded += 1
                continue

            feat = self.db.get_features_by_observation_id(obs["id"])
            if not feat or feat.get("status") == "failed":
                missing_features += 1
                continue

            fingerprint = f"{obs['repository_id']}:{obs['file_path']}:{obs['method_signature']}:{obs['source_code']}"
            if fingerprint in seen_fingerprints:
                duplicates_count += 1
                continue
            seen_fingerprints.add(fingerprint)

            valid_observation_ids.append(obs["id"])

        if not valid_observation_ids:
            raise ValueError("No valid observations with extracted features remained after filtering.")

        dataset_id = self.db.create_dataset(
            name=name,
            version=version,
            description=description,
            observation_ids=valid_observation_ids,
            feature_names=selected_features,
        )

        stats = self.compute_dataset_statistics(dataset_id, selected_features)
        stats.update({
            "test_files_excluded": test_files_excluded,
            "uncertain_excluded": uncertain_excluded,
            "missing_features_excluded": missing_features,
            "duplicates_excluded": duplicates_count,
        })

        logger.info(f"Generated dataset snapshot '{name}' v{version} (ID: {dataset_id}) with {len(valid_observation_ids)} observations.")
        return dataset_id, stats

    def compute_dataset_statistics(self, dataset_id: int, feature_names: List[str]) -> Dict[str, Any]:
        """Compute summary statistics for a method or class dataset snapshot."""
        ds = self.db.get_dataset(dataset_id)
        if ds and ds.get("granularity") == "class":
            return self.compute_class_dataset_statistics(dataset_id, feature_names)

        records = self.db.get_dataset_dataframe_records(dataset_id)
        if not records:
            return {"total": 0, "buggy": 0, "clean": 0, "class_ratio": 0.0}

        df = pd.DataFrame(records)
        total = len(df)
        buggy = int((df["label"] == 1).sum())
        clean = int((df["label"] == 0).sum())
        uncertain = int((df["label"] == -1).sum())

        repo_dist = df["repository_name"].value_counts().to_dict() if "repository_name" in df else {}

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
            "repository_count": len(repo_dist),
            "repository_distribution": repo_dist,
            "missing_values_per_feature": missing_vals,
        }

    def get_features_and_labels(
        self,
        dataset_id: int,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """Extract feature matrix X, target series y, and metadata dataframe for ML pipeline."""
        ds = self.db.get_dataset(dataset_id)
        if ds and ds.get("granularity") == "class":
            return self.get_class_features_and_labels(dataset_id, feature_names)

        records = self.db.get_dataset_dataframe_records(dataset_id)
        if not records:
            raise ValueError(f"No records found for dataset ID #{dataset_id}")

        df = pd.DataFrame(records)
        target_features = feature_names or DEFAULT_NUMERICAL_FEATURES

        for col in target_features:
            if col not in df.columns:
                df[col] = 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        X = df[target_features].copy()
        y = df["label"].astype(int)

        meta_cols = [c for c in IDENTIFIER_COLUMNS if c in df.columns]
        metadata = df[meta_cols].copy()

        return X, y, metadata
