"""Feature Extractor module for calculating and persisting Roslyn static code metrics."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from services.analyzer.roslyn_client import RoslynClient, RoslynClientError
from database.repository import RepositoryDB
from utils.logger import setup_logger

logger = setup_logger("feature_extractor")


class FeatureExtractor:
    """Extracts static code metrics using Roslyn and persists them to SQLite."""

    ANALYZER_VERSION = "2.0.0"
    METHOD_ANALYZER_VERSION = "1.0.0"
    CLASS_SCHEMA_VERSION = "3.0.0"

    def __init__(self, db: RepositoryDB, roslyn_client: Optional[RoslynClient] = None) -> None:
        self.db = db
        self.roslyn = roslyn_client or RoslynClient()

    # ---------------------------------------------------------
    # Class-Level Feature Extraction
    # ---------------------------------------------------------
    def extract_class_features_for_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract 40 static class-level metrics for a single class observation."""
        obs_id = observation["id"]
        source_code = observation.get("source_code")
        target_name = observation.get("class_name")

        if not source_code or not source_code.strip():
            err_data = {
                "class_observation_id": obs_id,
                "status": "failed",
                "error_message": "Missing or empty class source code.",
                "feature_schema_version": self.CLASS_SCHEMA_VERSION,
                "analyzer_version": self.ANALYZER_VERSION,
                "raw_metrics_json": json.dumps({}),
            }
            self.db.upsert_class_features(err_data)
            return err_data

        try:
            classes = self.roslyn.extract_classes(code=source_code)
            selected_cls = None
            for c in classes:
                if target_name and c.get("class_name") == target_name:
                    selected_cls = c
                    break
            if selected_cls is None and classes:
                selected_cls = classes[0]

            metrics = selected_cls.get("metrics") if selected_cls else None
            if not metrics:
                raise RoslynClientError("Roslyn analyzer returned no class metrics.")

            feat_record = {
                "class_observation_id": obs_id,
                "status": "success",
                "error_message": None,
                "feature_schema_version": self.CLASS_SCHEMA_VERSION,
                "analyzer_version": self.ANALYZER_VERSION,
                "raw_metrics_json": json.dumps(metrics),
            }
            feat_record.update(metrics)
            self.db.upsert_class_features(feat_record)
            return feat_record
        except Exception as e:
            logger.warning(f"Class feature extraction failed for class observation #{obs_id}: {e}")
            err_data = {
                "class_observation_id": obs_id,
                "status": "failed",
                "error_message": str(e),
                "feature_schema_version": self.CLASS_SCHEMA_VERSION,
                "analyzer_version": self.ANALYZER_VERSION,
                "raw_metrics_json": json.dumps({}),
            }
            self.db.upsert_class_features(err_data)
            return err_data

    def batch_extract_classes(
        self,
        repository_id: Optional[int] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Extract 40 class-level features for all pending class observations."""
        if force:
            observations = self.db.list_class_observations(repository_id=repository_id)
        else:
            observations = self.db.get_class_observations_needing_features(repository_id=repository_id, include_failed=False)

        total = len(observations)
        if total == 0:
            if progress_callback:
                progress_callback("All class observations already have extracted features.", 1.0)
            return {"total": 0, "success": 0, "failed": 0, "analyzer_version": self.ANALYZER_VERSION}

        batch_items = [
            {"id": str(obs["id"]), "code": obs.get("source_code", "")}
            for obs in observations
            if obs.get("source_code")
        ]
        batch_results = self.roslyn.analyze_batch(batch_items) if batch_items else {}

        success_count = 0
        failed_count = 0

        for idx, obs in enumerate(observations):
            obs_id = obs["id"]
            resp = batch_results.get(str(obs_id))
            metrics = None
            if resp and resp.get("success"):
                classes = resp.get("classes", [])
                for c in classes:
                    if c.get("class_name") == obs.get("class_name"):
                        metrics = c.get("metrics")
                        break
                if metrics is None and classes:
                    metrics = classes[0].get("metrics")

            if metrics:
                feat_record = {
                    "class_observation_id": obs_id,
                    "status": "success",
                    "error_message": None,
                    "feature_schema_version": self.CLASS_SCHEMA_VERSION,
                    "analyzer_version": self.ANALYZER_VERSION,
                    "raw_metrics_json": json.dumps(metrics),
                }
                feat_record.update(metrics)
                self.db.upsert_class_features(feat_record)
                success_count += 1
            else:
                self.db.upsert_class_features({
                    "class_observation_id": obs_id,
                    "status": "failed",
                    "error_message": "No class metrics produced by Roslyn batch analyzer.",
                    "feature_schema_version": self.CLASS_SCHEMA_VERSION,
                    "analyzer_version": self.ANALYZER_VERSION,
                    "raw_metrics_json": json.dumps({}),
                })
                failed_count += 1

            if progress_callback and (idx % 25 == 0 or idx == total - 1):
                pct = (idx + 1) / total
                progress_callback(f"Extracted class metrics {idx + 1}/{total} ({success_count} ok)", pct)

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "analyzer_version": self.ANALYZER_VERSION,
        }

    # ---------------------------------------------------------
    # Historical Method-Level Feature Extraction (Preserved)
    # ---------------------------------------------------------
    def extract_features_for_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract static metrics for a single method observation's source code."""
        obs_id = observation["id"]
        source_code = observation.get("source_code")

        if not source_code or not source_code.strip():
            err_data = {
                "observation_id": obs_id,
                "status": "failed",
                "error_message": "Missing or empty method source code.",
                "analyzer_version": self.METHOD_ANALYZER_VERSION,
                "raw_metrics_json": json.dumps({}),
            }
            self.db.upsert_features(err_data)
            return err_data

        try:
            metrics = self.roslyn.calculate_method_metrics(source_code)
            if not metrics:
                raise RoslynClientError("Roslyn analyzer returned no metrics for method.")

            feat_record = {
                "observation_id": obs_id,
                "status": "success",
                "error_message": None,
                "analyzer_version": self.METHOD_ANALYZER_VERSION,
                "raw_metrics_json": json.dumps(metrics),
            }
            feat_record.update(metrics)
            self.db.upsert_features(feat_record)
            return feat_record

        except Exception as e:
            logger.warning(f"Feature extraction failed for observation #{obs_id}: {e}")
            err_data = {
                "observation_id": obs_id,
                "status": "failed",
                "error_message": str(e),
                "analyzer_version": self.METHOD_ANALYZER_VERSION,
                "raw_metrics_json": json.dumps({}),
            }
            self.db.upsert_features(err_data)
            return err_data

    def batch_extract(
        self,
        repository_id: Optional[int] = None,
        force: bool = False,
        batch_size: int = 50,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Process unextracted (or all, if force=True) method observations in repository."""
        if force:
            observations = self.db.list_observations(repository_id=repository_id)
        else:
            observations = self.db.get_observations_needing_features(repository_id=repository_id, include_failed=False)

        total = len(observations)
        logger.info(f"Starting batch feature extraction: {total} observations to process.")

        if total == 0:
            if progress_callback:
                progress_callback("All observations already have extracted features.", 1.0)
            return {"total": 0, "success": 0, "failed": 0}

        success_count = 0
        failed_count = 0

        for idx, obs in enumerate(observations):
            res = self.extract_features_for_observation(obs)
            if res.get("status") == "success":
                success_count += 1
            else:
                failed_count += 1

            if progress_callback and (idx % 10 == 0 or idx == total - 1):
                pct = (idx + 1) / total
                msg = f"Extracted metrics {idx + 1}/{total} ({success_count} success, {failed_count} failed)"
                progress_callback(msg, pct)

        logger.info(f"Feature extraction complete: {success_count} succeeded, {failed_count} failed out of {total}.")
        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "analyzer_version": self.METHOD_ANALYZER_VERSION,
        }
