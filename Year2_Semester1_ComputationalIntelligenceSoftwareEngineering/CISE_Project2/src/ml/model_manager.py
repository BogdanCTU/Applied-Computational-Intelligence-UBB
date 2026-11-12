"""Model Manager module for persisting, versioning, and reloading trained ML models with joblib."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import sklearn

from src.database.repository import RepositoryDB
from src.ml.preprocessing import DataPreprocessor
from src.utils.logger import setup_logger

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
        path = Path(model_identifier)
        if not path.is_absolute():
            path = self.models_dir / (f"{path}.joblib" if not str(path).endswith(".joblib") else path)

        if not path.exists():
            raise ModelManagerError(f"Model artifact not found at {path}")

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
        """List all valid models available in database or directory."""
        if self.db:
            db_models = self.db.list_models()
            if db_models:
                return db_models

        # Fallback: scan models directory
        models = []
        for p in self.models_dir.glob("*.joblib"):
            try:
                bundle = joblib.load(p)
                models.append({
                    "id": p.stem,
                    "name": bundle.get("model_name", p.stem),
                    "algorithm": "RandomForestClassifier",
                    "dataset_id": bundle.get("dataset_id"),
                    "model_file_path": str(p),
                    "metrics": bundle.get("metrics", {}),
                    "parameters": bundle.get("parameters", {}),
                })
            except Exception:
                pass
        return models

