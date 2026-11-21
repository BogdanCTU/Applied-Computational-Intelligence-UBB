"""Real-Time Static Bug Detection Engine for C# Classes, Source Files, and Methods."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from services.analyzer.roslyn_client import RoslynClient, RoslynClientError
from database.repository import RepositoryDB
from core.settings import register_unpickle_aliases
register_unpickle_aliases()
from ml.model_manager import ModelManager, ModelManagerError
from ml.preprocessing import DataPreprocessor
from utils.logger import setup_logger

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


class NoClassesFoundError(PredictorError):
    """Raised when Roslyn AST analysis fails to find eligible C# classes, structs, or records."""
    pass


@dataclass
class MethodPrediction:
    """Detailed prediction record for an individual C# method (backward-compatible diagnostic mode)."""
    method_name: str
    class_name: str
    method_signature: str
    start_line: int
    end_line: int
    file_name: Optional[str]
    source_code: Optional[str]
    metrics: Dict[str, Any]
    predicted_label: int
    risk_score: float
    risk_category: str
    model_name: str
    model_id: Optional[int]
    prediction_timestamp: str
    decision_threshold: float = 0.50
    dataset_version: Optional[str] = None
    influential_metrics: List[Dict[str, Any]] = field(default_factory=list)
    global_importances: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassPrediction:
    """Detailed static ML prediction record for a single C# class, struct, or record."""
    class_name: str
    qualified_class_name: str
    namespace_name: str
    type_kind: str
    start_line: int
    end_line: int
    is_nested: bool
    method_count: int
    loc: int
    cyclomatic_complexity: int
    file_name: Optional[str]
    source_code: Optional[str]
    metrics: Dict[str, Any]
    predicted_label: int  # 1 = Defect-Prone Class (above threshold), 0 = Candidate-Clean Class
    defect_probability: float  # predict_proba()[:, 1]
    risk_score: float  # alias for defect_probability
    risk_category: str  # "Low risk", "Medium risk", "High risk" (kept distinct from binary threshold)
    decision_threshold: float
    model_name: str
    model_id: Optional[int]
    dataset_version: Optional[str]
    prediction_timestamp: str
    influential_metrics: List[Dict[str, Any]] = field(default_factory=list)
    global_importances: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FilePredictionResult:
    """Aggregated file-level summary derived independently from all classes inside a .cs file."""
    file_name: str
    file_metadata: Dict[str, Any]
    classes_analyzed_count: int
    classes_flagged_count: int
    highest_class_risk_score: float
    mean_class_risk_score: float
    max_defect_probability: float
    file_risk_category: str
    decision_threshold: float
    model_name: str
    model_id: Optional[int]
    dataset_version: Optional[str]
    prediction_timestamp: str
    class_predictions: List[ClassPrediction] = field(default_factory=list)
    extraction_warnings: List[str] = field(default_factory=list)
    parsing_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    disclaimer: str = (
        "ML-based static defect indication supported by historical SZZ defect evidence, "
        "not formal proof of a confirmed defect."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["class_predictions"] = [c.to_dict() for c in self.class_predictions]
        return d


class BugPredictor:
    """Predicts defect propensity for unseen C# classes, full .cs files, and legacy methods."""

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

        self._validate_and_load_bundle(model_bundle)
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
        """Validate structure, estimators, preprocessors, decision threshold, and feature columns."""
        required_keys = ["model", "preprocessor", "feature_names"]
        for k in required_keys:
            if k not in bundle or bundle[k] is None:
                raise ModelCompatibilityError(f"Model bundle missing essential component: '{k}'")

        self.model = bundle["model"]
        self.preprocessor: DataPreprocessor = bundle["preprocessor"]
        self.feature_names: List[str] = bundle["feature_names"]
        self.model_name: str = bundle.get("model_name", "RandomForest_Classifier")
        self.granularity: str = str(bundle.get("granularity", "method"))
        self.dataset_version: Optional[str] = bundle.get("dataset_version")
        self.decision_threshold: float = float(bundle.get("decision_threshold", 0.50))
        self.parameters: Dict[str, Any] = bundle.get("parameters", {})
        self.metrics_summary: Dict[str, Any] = bundle.get("metrics", {})
        self.split_summary: Dict[str, Any] = bundle.get("split_summary", {})

        if not hasattr(self.model, "predict") or not hasattr(self.model, "predict_proba"):
            raise ModelCompatibilityError("Loaded model object does not support predict() and predict_proba().")

        if not isinstance(self.preprocessor, DataPreprocessor):
            raise ModelCompatibilityError("Loaded preprocessor must be an instance of DataPreprocessor.")

        self.global_importances = self.metrics_summary.get("mdi_feature_importances", [])
        if not self.global_importances and hasattr(self.model, "feature_importances_"):
            for fname, imp in zip(self.feature_names, self.model.feature_importances_):
                self.global_importances.append({"feature": fname, "importance": float(imp)})
            self.global_importances.sort(key=lambda x: x["importance"], reverse=True)

    def _categorize_risk(self, probability: float) -> str:
        if probability <= self.low_threshold:
            return "Low risk"
        if probability <= self.medium_threshold:
            return "Medium risk"
        return "High risk"

    def _score_metrics(self, metrics: Dict[str, Any]) -> tuple[float, int, str]:
        """Transform metrics, call predict_proba(), and apply the stored decision_threshold."""
        row_dict = {col: metrics.get(col, 0.0) for col in self.preprocessor.feature_names_in_}
        df_single = pd.DataFrame([row_dict])

        try:
            df_proc = self.preprocessor.transform(df_single)
        except Exception as e:
            raise PredictorError(f"Preprocessing transformation failed: {e}") from e

        for col in self.feature_names:
            if col not in df_proc.columns:
                df_proc[col] = 0.0
        df_proc = df_proc[self.feature_names]

        probas = self.model.predict_proba(df_proc)[0]
        if len(probas) > 1:
            probability = float(probas[1])
        else:
            probability = float(self.model.predict(df_proc)[0])

        pred_label = int(probability >= self.decision_threshold)
        risk_cat = self._categorize_risk(probability)
        return probability, pred_label, risk_cat

    # ---------------------------------------------------------
    # Primary Class & File-Level Prediction API
    # ---------------------------------------------------------
    def predict_class_code(self, code: str, file_name: Optional[str] = None) -> List[ClassPrediction]:
        """Parse C# source code, analyze each class/struct/record independently, and return ClassPredictions."""
        return self.predict_csharp_file(code=code, file_name=file_name).class_predictions

    def predict_csharp_file(
        self,
        code: Optional[str] = None,
        file_path: Optional[Path | str] = None,
        file_name: Optional[str] = None,
    ) -> FilePredictionResult:
        """Analyze a full .cs file (with one or multiple classes) and compute independent class + aggregated file results."""
        if self.granularity != "class" and "class_loc" not in self.preprocessor.feature_names_in_:
            raise ModelCompatibilityError(
                f"Model '{self.model_name}' is trained at '{self.granularity}' granularity and cannot score class-level features. "
                "Select a class-level model (e.g. class_precision_champion_v3)."
            )

        resolved_file_name = file_name
        if file_path is not None:
            p = Path(file_path)
            if not p.exists() or not p.is_file():
                raise PredictorError(f"Source file not found: {file_path}")
            resolved_file_name = resolved_file_name or p.name
            try:
                code = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                code = p.read_text(encoding="latin-1", errors="replace")

        if not code or not code.strip():
            raise NoClassesFoundError("Input C# code is empty or contains only whitespace.")

        try:
            analysis = self.roslyn_client.analyze_source(code=code)
        except RoslynClientError as e:
            raise PredictorError(f"Roslyn syntax analysis failed: {e}") from e

        extracted_classes = analysis.get("classes", [])
        if not extracted_classes:
            raise NoClassesFoundError(
                "No C# class, struct, or record declarations could be extracted. "
                "Ensure input contains valid type declarations (e.g., 'public class OrderService { ... }')."
            )

        class_preds: List[ClassPrediction] = []
        for cls in extracted_classes:
            raw_metrics = cls.get("metrics")
            if not raw_metrics or not isinstance(raw_metrics, dict):
                continue

            pred = self.predict_class_from_metrics(
                metrics=raw_metrics,
                class_name=cls.get("class_name", "UnknownClass"),
                qualified_class_name=cls.get("qualified_class_name", cls.get("class_name", "UnknownClass")),
                namespace_name=cls.get("namespace_name", "Global"),
                type_kind=cls.get("type_kind", "class"),
                start_line=int(cls.get("start_line", 1)),
                end_line=int(cls.get("end_line", 1)),
                is_nested=bool(cls.get("is_nested", False)),
                file_name=resolved_file_name,
                source_code=cls.get("source_code") if self.persist_source_code else None,
                methods=cls.get("methods", []),
                persist_record=False,
            )
            class_preds.append(pred)

        if not class_preds:
            raise NoClassesFoundError("Roslyn discovered type declarations but no valid class metrics were produced.")

        scores = [c.defect_probability for c in class_preds]
        flagged = sum(1 for c in class_preds if c.predicted_label == 1)
        highest_score = round(float(max(scores)), 4)
        mean_score = round(float(np.mean(scores)), 4)
        file_risk_cat = self._categorize_risk(highest_score)
        timestamp = datetime.now(timezone.utc).isoformat()

        file_result = FilePredictionResult(
            file_name=resolved_file_name or "SubmittedCode.cs",
            file_metadata=analysis.get("file_metadata") or {},
            classes_analyzed_count=len(class_preds),
            classes_flagged_count=flagged,
            highest_class_risk_score=highest_score,
            mean_class_risk_score=mean_score,
            max_defect_probability=highest_score,
            file_risk_category=file_risk_cat,
            decision_threshold=self.decision_threshold,
            model_name=self.model_name,
            model_id=self.model_id,
            dataset_version=self.dataset_version,
            prediction_timestamp=timestamp,
            class_predictions=class_preds,
            extraction_warnings=analysis.get("extraction_warnings", []),
            parsing_diagnostics=analysis.get("parsing_diagnostics", []),
        )

        # Persist individual class predictions + file aggregation metadata to SQLite
        if self.persist_history and self.db:
            file_summary_json = json.dumps({
                "classes_analyzed_count": len(class_preds),
                "classes_flagged_count": flagged,
                "highest_class_risk_score": highest_score,
                "mean_class_risk_score": mean_score,
                "file_risk_category": file_risk_cat,
            })
            for cp in class_preds:
                try:
                    self.db.save_prediction(
                        model_id=self.model_id,
                        model_name=self.model_name,
                        granularity="class",
                        dataset_version=self.dataset_version,
                        decision_threshold=self.decision_threshold,
                        method_name=cp.qualified_class_name,
                        class_name=cp.class_name,
                        namespace_name=cp.namespace_name,
                        file_name=resolved_file_name,
                        start_line=cp.start_line,
                        end_line=cp.end_line,
                        method_count=cp.method_count,
                        loc=cp.loc,
                        cyclomatic_complexity=cp.cyclomatic_complexity,
                        source_code=cp.source_code if self.persist_source_code else None,
                        metrics=cp.metrics,
                        file_summary_json=file_summary_json,
                        predicted_label=cp.predicted_label,
                        risk_score=cp.defect_probability,
                        risk_category=cp.risk_category,
                    )
                except Exception as e:
                    logger.warning(f"Could not persist class prediction to database: {e}")

        return file_result

    def predict_class_from_metrics(
        self,
        metrics: Dict[str, Any],
        class_name: str = "UnknownClass",
        qualified_class_name: Optional[str] = None,
        namespace_name: str = "Global",
        type_kind: str = "class",
        start_line: int = 1,
        end_line: int = 1,
        is_nested: bool = False,
        file_name: Optional[str] = None,
        source_code: Optional[str] = None,
        methods: Optional[List[Dict[str, Any]]] = None,
        persist_record: bool = True,
    ) -> ClassPrediction:
        """Run class-level ML inference on pre-extracted static class metrics."""
        probability, pred_label, risk_cat = self._score_metrics(metrics)
        influential = self._compute_influential_metrics(metrics, granularity="class")
        timestamp = datetime.now(timezone.utc).isoformat()
        qname = qualified_class_name or class_name

        method_cnt = int(metrics.get("method_count", 0) or 0)
        class_loc = int(metrics.get("class_loc", 0) or 0)
        total_cc = int(metrics.get("total_cyclomatic_complexity", 0) or 0)

        result = ClassPrediction(
            class_name=class_name,
            qualified_class_name=qname,
            namespace_name=namespace_name,
            type_kind=type_kind,
            start_line=start_line,
            end_line=end_line,
            is_nested=is_nested,
            method_count=method_cnt,
            loc=class_loc,
            cyclomatic_complexity=total_cc,
            file_name=file_name,
            source_code=source_code if self.persist_source_code else None,
            metrics=metrics,
            predicted_label=pred_label,
            defect_probability=round(probability, 4),
            risk_score=round(probability, 4),
            risk_category=risk_cat,
            decision_threshold=self.decision_threshold,
            model_name=self.model_name,
            model_id=self.model_id,
            dataset_version=self.dataset_version,
            prediction_timestamp=timestamp,
            influential_metrics=influential,
            global_importances=self.global_importances[:10],
            methods=methods or [],
        )

        if persist_record and self.persist_history and self.db:
            try:
                self.db.save_prediction(
                    model_id=self.model_id,
                    model_name=self.model_name,
                    granularity="class",
                    dataset_version=self.dataset_version,
                    decision_threshold=self.decision_threshold,
                    method_name=qname,
                    class_name=class_name,
                    namespace_name=namespace_name,
                    file_name=file_name,
                    start_line=start_line,
                    end_line=end_line,
                    method_count=method_cnt,
                    loc=class_loc,
                    cyclomatic_complexity=total_cc,
                    source_code=source_code if self.persist_source_code else None,
                    metrics=metrics,
                    predicted_label=pred_label,
                    risk_score=round(probability, 4),
                    risk_category=risk_cat,
                )
            except Exception as e:
                logger.warning(f"Could not persist class prediction to database: {e}")

        return result

    # ---------------------------------------------------------
    # Historical Method-Level Prediction API (Preserved)
    # ---------------------------------------------------------
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
        """Run ML inference on a pre-extracted method-level static code metrics dictionary."""
        risk_score, pred_label, risk_cat = self._score_metrics(metrics)
        influential = self._compute_influential_metrics(metrics, granularity="method")
        timestamp = datetime.now(timezone.utc).isoformat()

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
            decision_threshold=self.decision_threshold,
            dataset_version=self.dataset_version,
            influential_metrics=influential,
            global_importances=self.global_importances[:10],
        )

        if self.persist_history and self.db:
            try:
                self.db.save_prediction(
                    model_id=self.model_id,
                    model_name=self.model_name,
                    granularity="method",
                    dataset_version=self.dataset_version,
                    decision_threshold=self.decision_threshold,
                    method_name=method_name,
                    class_name=class_name,
                    file_name=file_name,
                    start_line=start_line,
                    end_line=end_line,
                    loc=metrics.get("loc"),
                    cyclomatic_complexity=metrics.get("cyclomatic_complexity"),
                    source_code=source_code if self.persist_source_code else None,
                    metrics=metrics,
                    predicted_label=pred_label,
                    risk_score=round(risk_score, 4),
                    risk_category=risk_cat,
                )
            except Exception as e:
                logger.warning(f"Could not persist prediction to database: {e}")

        return result

    def _compute_influential_metrics(self, metrics: Dict[str, Any], granularity: str = "method") -> List[Dict[str, Any]]:
        """Identify key metrics that elevate defect propensity based on model importances and thresholds."""
        influential: List[Dict[str, Any]] = []

        if granularity == "class":
            alert_thresholds = {
                "total_cyclomatic_complexity": (20, "High aggregate McCabe complexity across class members elevates defect surface."),
                "max_method_complexity": (10, "Contains at least one complex method with heavy control-flow branching."),
                "high_complexity_method_count": (2, "Multiple methods exceed complexity >= 10."),
                "class_loc": (150, "Large class footprint increases cognitive load and maintenance risk."),
                "max_nesting_depth": (4, "Deeply nested control structures impede verification."),
                "method_count": (12, "High member method count indicates broad class responsibility."),
                "total_try_catch_count": (3, "Multiple exception handling blocks indicate complex failure paths."),
                "total_method_call_count": (30, "High external invocation coupling across class members."),
                "total_if_count": (12, "Elevated conditional branching across the class."),
                "wmc_density": (0.30, "High complexity density per physical line of class code."),
            }
        else:
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

        for fname, (thresh, note) in alert_thresholds.items():
            val = metrics.get(fname, 0)
            if val is not None and val >= thresh:
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

        influential.sort(key=lambda x: x["global_importance"], reverse=True)
        return influential
