"""Model Manager module for persisting, versioning, and reloading trained ML models with joblib."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import sklearn

from database.repository import RepositoryDB
from core.settings import register_unpickle_aliases
register_unpickle_aliases()
from ml.preprocessing import DataPreprocessor
from utils.logger import setup_logger

logger = setup_logger("model_manager")


class ModelManagerError(Exception):
    """Base exception for model management operations."""
    pass


class ModelManager:
    """Handles serialization, versioning, and validation of trained models and preprocessors."""

    def __init__(self, models_dir: Path | str, db: Optional[RepositoryDB] = None) -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def save_model(
        self,
        model_name: str,
        model: Any,
        preprocessor: DataPreprocessor,
        feature_names: List[str],
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        dataset_id: Optional[int] = None,
        split_summary: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> Path:
        """Serialize model, fitted preprocessor, and metadata bundle to disk and database."""
        safe_name = "".join(c for c in model_name if c.isalnum() or c in ("-", "_")).strip()
        if not safe_name:
            raise ModelManagerError(f"Invalid model name: '{model_name}'")

        file_path = self.models_dir / f"{safe_name}.joblib"
        if file_path.exists() and not overwrite:
            raise ModelManagerError(f"Model file '{file_path}' already exists. Specify a unique name or overwrite=True.")

        payload = {
            "model_name": safe_name,
            "model": model,
            "preprocessor": preprocessor,
            "feature_names": feature_names,
            "parameters": parameters,
            "metrics": metrics,
            "dataset_id": dataset_id,
            "split_summary": split_summary or {},
            "python_version": sys.version,
            "sklearn_version": sklearn.__version__,
        }

        joblib.dump(payload, file_path, compress=3)
        logger.info(f"Model artifact saved successfully to {file_path}")

        # Record in SQLite database if db is available
        if self.db:
            try:
                self.db.save_model_record(
                    name=safe_name,
                    algorithm="RandomForestClassifier",
                    dataset_id=dataset_id,
                    parameters=parameters,
                    metrics=metrics,
                    feature_names=feature_names,
                    model_file_path=str(file_path),
                )
            except Exception as e:
                logger.warning(f"Could not write model metadata to database: {e}")

        return file_path

    def load_model(self, model_identifier: str | Path) -> Dict[str, Any]:
        """Load and validate model artifact bundle from disk."""
        raw_str = str(model_identifier)
        path = Path(raw_str)
        if not path.is_absolute():
            path = self.models_dir / (f"{path}.joblib" if not raw_str.endswith(".joblib") else path)

        if not path.exists():
            fallback_name = Path(raw_str.replace("\\", "/")).name
            if not fallback_name.endswith(".joblib"):
                fallback_name = f"{fallback_name}.joblib"
            fallback_path = self.models_dir / fallback_name
            if fallback_path.exists():
                path = fallback_path
            else:
                raise ModelManagerError(f"Model artifact not found at {path}")

        register_unpickle_aliases()
        try:
            bundle = joblib.load(path)
        except Exception as e:
            raise ModelManagerError(f"Failed to deserialized model bundle: {e}") from e

        # Validate structure
        required_keys = ["model", "preprocessor", "feature_names", "parameters", "metrics"]
        for k in required_keys:
            if k not in bundle:
                raise ModelManagerError(f"Corrupted model bundle: missing key '{k}'")

        logger.info(f"Loaded model '{bundle.get('model_name')}' from {path}")
        return bundle

    def list_saved_models(self) -> List[Dict[str, Any]]:
        """List all valid models available in directory and database."""
        register_unpickle_aliases()
        models: List[Dict[str, Any]] = []
        seen_names: set[str] = set()

        # Scan models directory for serialized bundles
        preferred_order = [
            "et_nested_opt_v3_depth6_leaf6_log2",
            "rf_nested_opt_v3_depth6_leaf8_log2",
            "exp_final_5fold_v2_best_rf_compact_regularized",
            "rf_csharp_empirical_model",
        ]
        joblib_files = sorted(
            self.models_dir.glob("*.joblib"),
            key=lambda p: (preferred_order.index(p.stem) if p.stem in preferred_order else 999, p.stem),
        )

        db_by_name: Dict[str, Dict[str, Any]] = {}
        if self.db:
            for m in self.db.list_models():
                db_by_name[str(m.get("name", ""))] = m

        for p in joblib_files:
            try:
                bundle = joblib.load(p)
                m_name = str(bundle.get("model_name", p.stem))
                est = bundle.get("model")
                algo_name = type(est).__name__ if est is not None else "RandomForestClassifier"
                db_rec = db_by_name.get(m_name) or db_by_name.get(p.stem)
                models.append({
                    "id": db_rec["id"] if db_rec else None,
                    "name": m_name,
                    "algorithm": algo_name,
                    "dataset_id": bundle.get("dataset_id", db_rec.get("dataset_id") if db_rec else None),
                    "model_file_path": str(p),
                    "metrics": bundle.get("metrics", {}),
                    "parameters": bundle.get("parameters", {}),
                    "created_at": db_rec.get("created_at", "bundled") if db_rec else "bundled",
                })
                seen_names.add(m_name)
                seen_names.add(p.stem)
            except Exception:
                pass

        if self.db:
            for m in self.db.list_models():
                m_name = str(m.get("name", ""))
                if m_name not in seen_names:
                    models.append(m)

        return models

