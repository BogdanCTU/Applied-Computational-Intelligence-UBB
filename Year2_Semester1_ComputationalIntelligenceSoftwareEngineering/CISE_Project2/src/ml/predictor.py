"""Real-Time Bug Prediction Engine for C# Methods using Roslyn and Random Forest."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.analyzer.roslyn_client import RoslynClient, RoslynClientError
from src.database.repository import RepositoryDB
from src.ml.model_manager import ModelManager, ModelManagerError
from src.ml.preprocessing import DataPreprocessor
from src.utils.logger import setup_logger

logger = setup_logger("predictor")


class PredictorError(Exception):
    """Base exception for prediction operations."""
    pass


class ModelCompatibilityError(PredictorError):
    """Raised when loaded model artifact has missing or incompatible schemas."""
    pass


class NoMethodsFoundError(PredictorError):
    """Raised when Roslyn AST analysis fails to find eligible methods."""
    pass


@dataclass
class MethodPrediction:
    """Detailed prediction record for an individual C# method."""
    method_name: str
    class_name: str
    method_signature: str
    start_line: int
    end_line: int
    file_name: Optional[str]
    source_code: Optional[str]
    metrics: Dict[str, Any]
    predicted_label: int  # 0 = Clean, 1 = Defect-Prone
    risk_score: float  # Model estimated risk score [0.0 - 1.0]
    risk_category: str  # "Low risk", "Medium risk", "High risk"
    model_name: str
    model_id: Optional[int]
    prediction_timestamp: str
    influential_metrics: List[Dict[str, Any]] = field(default_factory=list)
    global_importances: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction result to standard dictionary."""
        return asdict(self)


class BugPredictor:
    """Predicts defect risk for unseen C# methods using Roslyn AST metrics and Random Forest."""

    def __init__(
        self,
        model_bundle: Dict[str, Any],
        model_id: Optional[int] = None,
        roslyn_client: Optional[RoslynClient] = None,
        db: Optional[RepositoryDB] = None,
        low_threshold: float = 0.30,
        medium_threshold: float = 0.60,
        persist_history: bool = True,
        persist_source_code: bool = False,
    ) -> None:
        self.model_id = model_id
        self.db = db
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.persist_history = persist_history
        self.persist_source_code = persist_source_code

        # Unpack and validate model bundle
        self._validate_and_load_bundle(model_bundle)

        # Initialize Roslyn client
        self.roslyn_client = roslyn_client or RoslynClient()

    @classmethod
    def from_model_identifier(
        cls,
        model_identifier: str | Path,
        models_dir: Path | str,
        model_id: Optional[int] = None,
        roslyn_client: Optional[RoslynClient] = None,
        db: Optional[RepositoryDB] = None,
        low_threshold: float = 0.30,
        medium_threshold: float = 0.60,
        persist_history: bool = True,
        persist_source_code: bool = False,
    ) -> BugPredictor:
        """Instantiate BugPredictor by loading a saved model artifact via ModelManager."""
        mgr = ModelManager(models_dir=models_dir, db=db)
        bundle = mgr.load_model(model_identifier)
        return cls(
            model_bundle=bundle,
            model_id=model_id,
            roslyn_client=roslyn_client,
            db=db,
            low_threshold=low_threshold,
            medium_threshold=medium_threshold,
            persist_history=persist_history,
            persist_source_code=persist_source_code,
        )

    def _validate_and_load_bundle(self, bundle: Dict[str, Any]) -> None:
        """Validate structure, estimators, preprocessors, and feature columns."""
        required_keys = ["model", "preprocessor", "feature_names"]
        for k in required_keys:
            if k not in bundle or bundle[k] is None:
                raise ModelCompatibilityError(f"Model bundle missing essential component: '{k}'")

        self.model = bundle["model"]
        self.preprocessor: DataPreprocessor = bundle["preprocessor"]
        self.feature_names: List[str] = bundle["feature_names"]
        self.model_name: str = bundle.get("model_name", "RandomForest_Classifier")
        self.parameters: Dict[str, Any] = bundle.get("parameters", {})
        self.metrics_summary: Dict[str, Any] = bundle.get("metrics", {})
        self.split_summary: Dict[str, Any] = bundle.get("split_summary", {})

        if not hasattr(self.model, "predict") or not hasattr(self.model, "predict_proba"):
            raise ModelCompatibilityError("Loaded model object does not support predict() and predict_proba().")

        if not isinstance(self.preprocessor, DataPreprocessor):
            raise ModelCompatibilityError("Loaded preprocessor must be an instance of DataPreprocessor.")

        # Cache global MDI feature importances if present
        self.global_importances = self.metrics_summary.get("mdi_feature_importances", [])
        if not self.global_importances and hasattr(self.model, "feature_importances_"):
            for fname, imp in zip(self.feature_names, self.model.feature_importances_):
                self.global_importances.append({"feature": fname, "importance": float(imp)})
            self.global_importances.sort(key=lambda x: x["importance"], reverse=True)

    def predict_code(self, code: str, file_name: Optional[str] = None) -> List[MethodPrediction]:
        """Parse C# source code, extract all eligible methods, and predict defect risk."""
        if not code or not code.strip():
            raise NoMethodsFoundError("Input C# code is empty or contains only whitespace.")

        try:
            extracted_methods = self.roslyn_client.extract_methods(code=code)
        except RoslynClientError as e:
            raise PredictorError(f"Roslyn syntax analysis failed: {e}") from e

        if not extracted_methods:
            raise NoMethodsFoundError(
                "No eligible C# methods could be extracted. "
                "Ensure input contains valid method declarations (e.g., 'public void Foo() { ... }')."
            )

        predictions: List[MethodPrediction] = []
        for m in extracted_methods:
            raw_metrics = m.get("metrics")
            if not raw_metrics or not isinstance(raw_metrics, dict):
                logger.warning(f"Skipping method '{m.get('method_name')}' due to missing metrics.")
                continue

            pred = self.predict_from_metrics(
                metrics=raw_metrics,
                method_name=m.get("method_name", "AnonymousMethod"),
                class_name=m.get("class_name", "UnknownClass"),
                method_signature=m.get("method_signature", ""),
                start_line=m.get("start_line", 1),
                end_line=m.get("end_line", 1),
                file_name=file_name,
                source_code=m.get("source_code") if self.persist_source_code else None,
            )
            predictions.append(pred)

        if not predictions:
            raise NoMethodsFoundError("Roslyn discovered AST structures but no valid method metrics were produced.")

        return predictions

    def predict_file(self, file_path: Path | str) -> List[MethodPrediction]:
        """Analyze a complete .cs file and return predictions for all contained methods."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise PredictorError(f"Source file not found: {file_path}")

        try:
            code = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            code = p.read_text(encoding="latin-1", errors="replace")

        return self.predict_code(code=code, file_name=p.name)

    def predict_from_metrics(
        self,
        metrics: Dict[str, Any],
        method_name: str = "UnknownMethod",
        class_name: str = "UnknownClass",
        method_signature: str = "",
        start_line: int = 1,
        end_line: int = 1,
        file_name: Optional[str] = None,
        source_code: Optional[str] = None,
    ) -> MethodPrediction:
        """Run ML inference on a pre-extracted static code metrics dictionary."""
        # 1. Align features with preprocessor input schema
        # Fill missing features with 0.0 without mutating input
        row_dict = {col: metrics.get(col, 0.0) for col in self.preprocessor.feature_names_in_}
        df_single = pd.DataFrame([row_dict])

        # 2. Transform through model's fitted preprocessor
        try:
            df_proc = self.preprocessor.transform(df_single)
        except Exception as e:
            raise PredictorError(f"Preprocessing transformation failed: {e}") from e

        # Ensure column ordering matches model's feature names
        for col in self.feature_names:
            if col not in df_proc.columns:
                df_proc[col] = 0.0
        df_proc = df_proc[self.feature_names]

        # 3. Model Inference
        pred_label = int(self.model.predict(df_proc)[0])
        probas = self.model.predict_proba(df_proc)[0]

        # Buggy risk score is probability of class 1
        risk_score = float(probas[1]) if len(probas) > 1 else float(pred_label)

        # 4. Categorize risk
        if risk_score <= self.low_threshold:
            risk_cat = "Low risk"
        elif risk_score <= self.medium_threshold:
            risk_cat = "Medium risk"
        else:
            risk_cat = "High risk"

        # 5. Determine influential metrics for explanation
        influential = self._compute_influential_metrics(metrics)

        timestamp = datetime.now(timezone.utc).isoformat()

        # 6. Construct result
        result = MethodPrediction(
            method_name=method_name,
            class_name=class_name,
            method_signature=method_signature or method_name,
            start_line=start_line,
            end_line=end_line,
            file_name=file_name,
            source_code=source_code if self.persist_source_code else None,
            metrics=metrics,
            predicted_label=pred_label,
            risk_score=round(risk_score, 4),
            risk_category=risk_cat,
            model_name=self.model_name,
            model_id=self.model_id,
            prediction_timestamp=timestamp,
            influential_metrics=influential,
            global_importances=self.global_importances[:10],
        )

        # 7. Persist to history if enabled
        if self.persist_history and self.db:
            try:
                self.db.save_prediction(
                    model_id=self.model_id,
                    model_name=self.model_name,
                    method_name=method_name,
                    class_name=class_name,
                    file_name=file_name,
                    source_code=source_code if self.persist_source_code else None,
                    metrics=metrics,
                    predicted_label=pred_label,
                    risk_score=round(risk_score, 4),
                    risk_category=risk_cat,
                )
            except Exception as e:
                logger.warning(f"Could not persist prediction to database: {e}")

        return result

    def _compute_influential_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify key metrics that elevate or suppress defect risk based on model importances and thresholds."""
        influential: List[Dict[str, Any]] = []

        # Heuristic reference baseline thresholds for software engineering metrics
        alert_thresholds = {
            "cyclomatic_complexity": (10, "High cyclomatic complexity elevates execution branching risk."),
            "max_nesting_depth": (4, "Deeply nested control structures impede mental model verification."),
            "loc": (40, "Long method size increases error surface area."),
            "statement_count": (25, "High statement volume increases defect opportunity."),
            "loop_count": (3, "Multiple loops compound control-flow state complexity."),
            "try_catch_count": (2, "Extensive exception handling often indicates defensive patching."),
            "throw_count": (2, "Multiple explicit exception throws indicate complex failure paths."),
            "conditional_expression_count": (2, "Multiple ternary operators reduce readability."),
            "boolean_operator_count": (4, "Complex boolean logic often harbors edge-case defects."),
            "method_call_count": (15, "High external invocation coupling."),
        }

        # Check metric values against thresholds
        for fname, (thresh, note) in alert_thresholds.items():
            val = metrics.get(fname, 0)
            if val is not None and val >= thresh:
                # Find global importance score if known
                global_imp = 0.0
                for item in self.global_importances:
                    if item.get("feature") == fname:
                        global_imp = item.get("importance", 0.0)
                        break

                influential.append({
                    "feature": fname,
                    "value": val,
                    "threshold": thresh,
                    "global_importance": round(global_imp, 4),
                    "interpretation": note,
                })

        # Sort by global importance descending
        influential.sort(key=lambda x: x["global_importance"], reverse=True)
        return influential

