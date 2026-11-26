"""Versioned model artifact persistence and SQLite model registry integration."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn

from bug_detector.config.settings import AppConfig, load_config, save_config
from bug_detector.db import BugDetectorRepository, DatabaseManager


def get_dependency_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def save_model_bundle(
    model_version: str,
    bundle: dict[str, Any],
    config: AppConfig | None = None,
    activate: bool = False,
) -> tuple[Path, Path]:
    """Save joblib bundle + JSON manifest and register model in SQLite."""
    cfg = config or load_config()
    model_dir = cfg.models_dir / model_version
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / "model.joblib"
    manifest_path = model_dir / "manifest.json"

    joblib.dump(bundle, artifact_path, compress=3)

    manifest = {
        "model_version": model_version,
        "experiment_id": bundle.get("experiment_id"),
        "dataset_version": bundle["dataset_version"],
        "dataset_sha256": bundle.get("dataset_sha256"),
        "algorithm": bundle["algorithm"],
        "experiment_code": bundle["experiment_code"],
        "feature_groups": bundle["feature_groups"],
        "feature_schema": bundle["feature_schema"],
        "hyperparameters": bundle["hyperparameters"],
        "threshold_low": bundle["threshold_low"],
        "threshold_center": bundle["threshold_center"],
        "threshold_high": bundle["threshold_high"],
        "calibration_method": bundle["calibration_method"],
        "cv_metrics": bundle.get("cv_metrics"),
        "independent_test_metrics": bundle.get("independent_test_metrics"),
        "hard_negative_metrics": bundle.get("hard_negative_metrics"),
        "temporal_metrics": bundle.get("temporal_metrics"),
        "dependency_versions": bundle.get("dependency_versions") or get_dependency_versions(),
        "trained_at": bundle.get("trained_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_path": str(artifact_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    repo = BugDetectorRepository(DatabaseManager(cfg.db_path))
    repo.register_model_version(
        {
            "model_version": model_version,
            "experiment_id": manifest["experiment_id"],
            "dataset_version": manifest["dataset_version"],
            "dataset_sha256": manifest["dataset_sha256"],
            "algorithm": manifest["algorithm"],
            "experiment_code": manifest["experiment_code"],
            "feature_groups": manifest["feature_groups"],
            "feature_schema": manifest["feature_schema"],
            "hyperparameters": manifest["hyperparameters"],
            "threshold_low": manifest["threshold_low"],
            "threshold_center": manifest["threshold_center"],
            "threshold_high": manifest["threshold_high"],
            "calibration_method": manifest["calibration_method"],
            "artifact_path": str(artifact_path),
            "manifest_path": str(manifest_path),
            "dependency_versions": manifest["dependency_versions"],
        },
        activate=activate,
    )

    if activate:
        cfg.inference.active_model_version = model_version
        cfg.inference.active_model_path = str(artifact_path)
        cfg.thresholds.threshold_low = float(manifest["threshold_low"])
        cfg.thresholds.threshold_center = float(manifest["threshold_center"])
        cfg.thresholds.threshold_high = float(manifest["threshold_high"])
        save_config(cfg)

    return artifact_path, manifest_path


def load_model_bundle(model_path_or_version: str | Path | None = None, config: AppConfig | None = None) -> dict[str, Any]:
    """Load a persisted model bundle by path, model_version, or active config/DB default."""
    cfg = config or load_config()
    target_path: Path | None = None

    if model_path_or_version is not None:
        p = Path(model_path_or_version)
        if p.exists():
            target_path = p
        else:
            cand = cfg.models_dir / str(model_path_or_version) / "model.joblib"
            if cand.exists():
                target_path = cand
    else:
        if cfg.inference.active_model_path and Path(cfg.inference.active_model_path).exists():
            target_path = Path(cfg.inference.active_model_path)
        else:
            repo = BugDetectorRepository(DatabaseManager(cfg.db_path))
            active = repo.get_active_model()
            if active and Path(active["artifact_path"]).exists():
                target_path = Path(active["artifact_path"])

    if target_path is None or not target_path.exists():
        raise FileNotFoundError(f"Model bundle not found: {model_path_or_version or cfg.inference.active_model_version}")
    return joblib.load(target_path)
