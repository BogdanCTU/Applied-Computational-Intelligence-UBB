"""Static C# Bug Detection Classifier and Bug Localization Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
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


def _compute_normalized_fingerprint(code: str) -> str:
    norm_lines = [ln.rstrip() for ln in code.replace("\r\n", "\n").replace("\r", "\n").splitlines()]
    return hashlib.sha256("\n".join(norm_lines).strip().encode("utf-8", errors="replace")).hexdigest()


@dataclass
class HistoricalBugLocation:
    """Verified historical defect location derived directly from SZZ blame evidence."""
    repository_name: str
    file_path: str
    commit_sha: str
    bug_fix_commit_sha: Optional[str]
    bug_inducing_commit_sha: Optional[str]
    method_name: Optional[str]
    method_signature: Optional[str]
    method_start_line: Optional[int]
    method_end_line: Optional[int]
    affected_lines: List[int] = field(default_factory=list)
    affected_line_ranges: List[Dict[str, int]] = field(default_factory=list)
    szz_confidence: float = 0.85
    source: str = "verified_historical_szz"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SuspiciousMethodLocation:
    """ML-estimated suspicious method ranked by a separately validated method localizer."""
    method_name: str
    method_signature: str
    start_line: int
    end_line: int
    probability: float
    is_suspicious: bool
    threshold: float
    cyclomatic_complexity: int = 1
    loc: int = 0
    source: str = "ml_suspicious_method_localizer"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugLocalizationResult:
    """Transparent bug localization report separating verified SZZ evidence from ML estimates."""
    status: str  # "verified_historical", "ml_method_only", "unavailable", "not_applicable"
    exact_line_localization_status: str  # "verified_historical", "unavailable", "not_applicable"
    verified_historical_locations: List[HistoricalBugLocation] = field(default_factory=list)
    ml_suspicious_methods: List[SuspiciousMethodLocation] = field(default_factory=list)
    summary_note: str = ""
    limitation_note: str = (
        "Class-level static features classify whether a class is BUG or CLEAN and do not prove exact buggy lines. "
        "Exact line ranges are shown only when supported by verified historical SZZ evidence; "
        "ML-suspicious methods reflect a separately validated method model."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["verified_historical_locations"] = [x.to_dict() for x in self.verified_historical_locations]
        d["ml_suspicious_methods"] = [x.to_dict() for x in self.ml_suspicious_methods]
        return d


@dataclass
class FailedClassAnalysis:
    """Explicit failure record when a discovered class cannot be scored reliably."""
    class_name: str
    qualified_class_name: str
    start_line: int
    end_line: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    classification: str = "CLEAN"
    confidence: float = 0.50
    decision_threshold: float = 0.50
    dataset_version: Optional[str] = None
    influential_metrics: List[Dict[str, Any]] = field(default_factory=list)
    global_importances: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassPrediction:
    """Binary BUG / CLEAN classification record and localization details for a single C# class."""
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
    predicted_label: int  # 1 = BUG, 0 = CLEAN
    defect_probability: float  # predict_proba()[:, 1]
    risk_score: float  # backward-compatible alias for defect_probability
    risk_category: str  # secondary label retained for API backward compatibility
    decision_threshold: float
    model_name: str
    model_id: Optional[int]
    dataset_version: Optional[str]
    prediction_timestamp: str
    classification: str = "CLEAN"  # Explicit "BUG" or "CLEAN"
    confidence: float = 0.50  # Probability of assigned class (prob if BUG, 1-prob if CLEAN)
    localization: Optional[BugLocalizationResult] = None
    explanation_summary: str = ""
    limitation_note: str = (
        "Static ML classification indicates historical defect similarity using 40 Roslyn class features, "
        "not formal bug verification or line-level proof."
    )
    influential_metrics: List[Dict[str, Any]] = field(default_factory=list)
    global_importances: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.localization is not None:
            d["localization"] = self.localization.to_dict()
        return d


@dataclass
class FilePredictionResult:
    """Aggregated file-level classification summary derived independently across classes inside a .cs file."""
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
    file_classification: str = "CLEAN"  # "BUG", "BUG (PARTIAL ANALYSIS)", "CLEAN", "ANALYSIS INCOMPLETE"
    classes_bug_count: int = 0
    classes_clean_count: int = 0
    classes_failed_count: int = 0
    syntax_error_count: int = 0
    analysis_complete: bool = True
    failed_classes: List[FailedClassAnalysis] = field(default_factory=list)
    class_predictions: List[ClassPrediction] = field(default_factory=list)
    extraction_warnings: List[str] = field(default_factory=list)
    parsing_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    disclaimer: str = (
        "ML-based static C# bug detection classifier trained on historical SZZ defect evidence, "
        "not formal proof of defects or defect absence."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["class_predictions"] = [c.to_dict() for c in self.class_predictions]
        d["failed_classes"] = [f.to_dict() for f in self.failed_classes]
        return d


class BugPredictor:
    """Classifies C# classes and full .cs files as BUG or CLEAN and attaches available localization evidence."""

    def __init__(
        self,
        model_bundle: Dict[str, Any],
        model_id: Optional[int] = None,
        roslyn_client: Optional[RoslynClient] = None,
        db: Optional[RepositoryDB] = None,
        method_localizer_bundle: Optional[Dict[str, Any]] = None,
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
        self.method_localizer_bundle = method_localizer_bundle
        self.roslyn_client = roslyn_client or RoslynClient()

    @classmethod
    def from_model_identifier(
        cls,
        model_identifier: str | Path,
        models_dir: Path | str,
        model_id: Optional[int] = None,
        roslyn_client: Optional[RoslynClient] = None,
        db: Optional[RepositoryDB] = None,
        method_localizer_identifier: str | Path | None = "method_localizer_top200_v4",
        low_threshold: float = 0.30,
        medium_threshold: float = 0.60,
        persist_history: bool = True,
        persist_source_code: bool = False,
    ) -> BugPredictor:
        """Instantiate BugPredictor from a saved model bundle and optional method localizer."""
        mgr = ModelManager(models_dir=models_dir, db=db)
        bundle = mgr.load_model(model_identifier)
        method_loc_bundle: Optional[Dict[str, Any]] = None
        if method_localizer_identifier:
            try:
                method_loc_bundle = mgr.load_model(method_localizer_identifier)
            except ModelManagerError:
                method_loc_bundle = None
        return cls(
            model_bundle=bundle,
            model_id=model_id,
            roslyn_client=roslyn_client,
            db=db,
            method_localizer_bundle=method_loc_bundle,
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

    def _localize_bug_class(
        self,
        class_source: Optional[str],
        methods: List[Dict[str, Any]],
        predicted_label: int,
    ) -> BugLocalizationResult:
        """Build transparent localization info distinguishing verified SZZ evidence vs validated ML methods."""
        if predicted_label == 0:
            return BugLocalizationResult(
                status="not_applicable",
                exact_line_localization_status="not_applicable",
                summary_note="Class classified as CLEAN; no bug localization triggered.",
            )

        historical_locs: List[HistoricalBugLocation] = []
        if self.db and class_source:
            fp = _compute_normalized_fingerprint(class_source)
            matched = self.db.find_verified_historical_localizations(source_fingerprint=fp)
            for row in matched:
                historical_locs.append(
                    HistoricalBugLocation(
                        repository_name=row.get("repository_name", ""),
                        file_path=row.get("file_path", ""),
                        commit_sha=row.get("commit_sha", ""),
                        bug_fix_commit_sha=row.get("bug_fix_commit_sha"),
                        bug_inducing_commit_sha=row.get("bug_inducing_commit_sha"),
                        method_name=row.get("method_name"),
                        method_signature=row.get("method_signature"),
                        method_start_line=row.get("method_start_line"),
                        method_end_line=row.get("method_end_line"),
                        affected_lines=json.loads(row.get("affected_lines_json") or "[]"),
                        affected_line_ranges=json.loads(row.get("affected_line_ranges_json") or "[]"),
                        szz_confidence=float(row.get("szz_confidence", 0.85)),
                    )
                )

        ml_methods: List[SuspiciousMethodLocation] = []
        if self.method_localizer_bundle and methods:
            m_model = self.method_localizer_bundle.get("model")
            m_prep = self.method_localizer_bundle.get("preprocessor")
            m_feats = self.method_localizer_bundle.get("feature_names", [])
            m_thresh = float(self.method_localizer_bundle.get("decision_threshold", 0.50))
            if m_model is not None and m_prep is not None:
                valid_ms = [m for m in methods if isinstance(m.get("metrics"), dict) and m["metrics"]]
                if valid_ms:
                    rows = [
                        {col: m["metrics"].get(col, 0.0) for col in m_prep.feature_names_in_}
                        for m in valid_ms
                    ]
                    df_m = m_prep.transform(pd.DataFrame(rows))
                    for col in m_feats:
                        if col not in df_m.columns:
                            df_m[col] = 0.0
                    df_m = df_m[m_feats]
                    probs = m_model.predict_proba(df_m)[:, 1]
                    for m, p_val in zip(valid_ms, probs):
                        p_float = float(p_val)
                        ml_methods.append(
                            SuspiciousMethodLocation(
                                method_name=m.get("method_name", "UnknownMethod"),
                                method_signature=m.get("method_signature", m.get("method_name", "")),
                                start_line=int(m.get("start_line", 1)),
                                end_line=int(m.get("end_line", 1)),
                                probability=round(p_float, 4),
                                is_suspicious=bool(p_float >= m_thresh),
                                threshold=m_thresh,
                                cyclomatic_complexity=int(m["metrics"].get("cyclomatic_complexity", 1) or 1),
                                loc=int(m["metrics"].get("loc", 0) or 0),
                            )
                        )
                    ml_methods.sort(key=lambda x: x.probability, reverse=True)

        if historical_locs:
            status = "verified_historical"
            line_status = "verified_historical"
            note = (
                f"Matched {len(historical_locs)} verified historical SZZ defect trace(s) with exact line evidence."
            )
        elif ml_methods:
            flagged_m = [m for m in ml_methods if m.is_suspicious]
            status = "ml_method_only"
            line_status = "unavailable"
            if flagged_m:
                note = (
                    f"Exact line-level localization is unavailable without historical SZZ evidence. "
                    f"Separately validated method localizer identified {len(flagged_m)} suspicious method(s)."
                )
            else:
                note = (
                    "Exact line-level localization is unavailable without historical SZZ evidence. "
                    "Ranked member methods by separately validated method-localizer probability."
                )
        else:
            status = "unavailable"
            line_status = "unavailable"
            note = (
                "Method and exact line localization are unavailable for this unseen BUG class "
                "(no matching historical SZZ evidence or analyzable multi-method body)."
            )

        return BugLocalizationResult(
            status=status,
            exact_line_localization_status=line_status,
            verified_historical_locations=historical_locs,
            ml_suspicious_methods=ml_methods,
            summary_note=note,
        )

    @staticmethod
    def _build_explanation(
        class_name: str,
        classification: str,
        probability: float,
        threshold: float,
        influential: List[Dict[str, Any]],
    ) -> str:
        if classification == "BUG":
            if influential:
                top_names = ", ".join(item["feature"] for item in influential[:3])
                return (
                    f"Classified as BUG because P(BUG) = {probability:.3f} >= threshold {threshold:.2f}, "
                    f"driven by elevated structural metrics ({top_names})."
                )
            return f"Classified as BUG because P(BUG) = {probability:.3f} >= threshold {threshold:.2f}."
        return (
            f"Classified as CLEAN because P(BUG) = {probability:.3f} < threshold {threshold:.2f} "
            f"(no defect pattern detected above decision threshold)."
        )

    # ---------------------------------------------------------
    # Primary Class & File-Level Classification API
    # ---------------------------------------------------------
    def predict_class_code(self, code: str, file_name: Optional[str] = None) -> List[ClassPrediction]:
        """Parse C# source code, classify each class/struct/record independently as BUG or CLEAN."""
        return self.predict_csharp_file(code=code, file_name=file_name).class_predictions

    def predict_csharp_file(
        self,
        code: Optional[str] = None,
        file_path: Optional[Path | str] = None,
        file_name: Optional[str] = None,
    ) -> FilePredictionResult:
        """Analyze a full .cs file (one or multiple classes) returning independent verdicts and a safe file summary."""
        if self.granularity != "class" and "class_loc" not in self.preprocessor.feature_names_in_:
            raise ModelCompatibilityError(
                f"Model '{self.model_name}' is trained at '{self.granularity}' granularity and cannot classify classes. "
                "Select a class-level classifier (e.g. class_bug_classifier_top200_v4)."
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

        diagnostics = analysis.get("parsing_diagnostics", []) or []
        syntax_errors = [d for d in diagnostics if str(d.get("severity", "")).lower() == "error"]
        raw_classes = analysis.get("classes", []) or []
        extracted_classes = [
            c for c in raw_classes
            if (c.get("class_name") or "").strip() and c.get("class_name") != "__DummyContainer__"
        ]

        if not extracted_classes:
            err_hint = f" Syntax errors: {syntax_errors[0].get('message')}" if syntax_errors else ""
            raise NoClassesFoundError(
                "No C# class, struct, or record declarations could be extracted." + err_hint
            )

        class_preds: List[ClassPrediction] = []
        failed_classes: List[FailedClassAnalysis] = []

        for cls in extracted_classes:
            cname = cls.get("class_name", "UnknownClass")
            qname = cls.get("qualified_class_name", cname)
            sline = int(cls.get("start_line", 1))
            eline = int(cls.get("end_line", 1))
            raw_metrics = cls.get("metrics")

            if not raw_metrics or not isinstance(raw_metrics, dict):
                failed_classes.append(
                    FailedClassAnalysis(
                        class_name=cname,
                        qualified_class_name=qname,
                        start_line=sline,
                        end_line=eline,
                        reason="Roslyn did not produce class metrics (incomplete or invalid syntax inside class).",
                    )
                )
                continue

            try:
                pred = self.predict_class_from_metrics(
                    metrics=raw_metrics,
                    class_name=cname,
                    qualified_class_name=qname,
                    namespace_name=cls.get("namespace_name", "Global"),
                    type_kind=cls.get("type_kind", "class"),
                    start_line=sline,
                    end_line=eline,
                    is_nested=bool(cls.get("is_nested", False)),
                    file_name=resolved_file_name,
                    source_code=cls.get("source_code"),
                    methods=cls.get("methods", []),
                    persist_record=False,
                )
                class_preds.append(pred)
            except Exception as exc:
                failed_classes.append(
                    FailedClassAnalysis(
                        class_name=cname,
                        qualified_class_name=qname,
                        start_line=sline,
                        end_line=eline,
                        reason=f"Classifier evaluation failed: {exc}",
                    )
                )

        if not class_preds:
            raise NoClassesFoundError(
                f"Found {len(extracted_classes)} class declaration(s), but none could be classified reliably."
            )

        scores = [c.defect_probability for c in class_preds]
        bug_count = sum(1 for c in class_preds if c.predicted_label == 1)
        clean_count = sum(1 for c in class_preds if c.predicted_label == 0)
        failed_count = len(failed_classes)
        syntax_error_count = len(syntax_errors)
        analysis_complete = (failed_count == 0) and (syntax_error_count == 0)

        if bug_count > 0:
            file_classification = "BUG" if analysis_complete else "BUG (PARTIAL ANALYSIS)"
        elif analysis_complete:
            file_classification = "CLEAN"
        else:
            file_classification = "ANALYSIS INCOMPLETE"

        highest_score = round(float(max(scores)), 4)
        mean_score = round(float(np.mean(scores)), 4)
        file_risk_cat = self._categorize_risk(highest_score)
        timestamp = datetime.now(timezone.utc).isoformat()

        file_result = FilePredictionResult(
            file_name=resolved_file_name or "SubmittedCode.cs",
            file_metadata=analysis.get("file_metadata") or {},
            classes_analyzed_count=len(class_preds),
            classes_flagged_count=bug_count,
            highest_class_risk_score=highest_score,
            mean_class_risk_score=mean_score,
            max_defect_probability=highest_score,
            file_risk_category=file_risk_cat,
            decision_threshold=self.decision_threshold,
            model_name=self.model_name,
            model_id=self.model_id,
            dataset_version=self.dataset_version,
            prediction_timestamp=timestamp,
            file_classification=file_classification,
            classes_bug_count=bug_count,
            classes_clean_count=clean_count,
            classes_failed_count=failed_count,
            syntax_error_count=syntax_error_count,
            analysis_complete=analysis_complete,
            failed_classes=failed_classes,
            class_predictions=class_preds,
            extraction_warnings=analysis.get("extraction_warnings", []) or [],
            parsing_diagnostics=diagnostics,
        )

        if self.persist_history and self.db:
            file_summary_json = json.dumps({
                "file_classification": file_classification,
                "classes_analyzed_count": len(class_preds),
                "classes_bug_count": bug_count,
                "classes_clean_count": clean_count,
                "classes_failed_count": failed_count,
                "syntax_error_count": syntax_error_count,
                "analysis_complete": analysis_complete,
                "highest_class_risk_score": highest_score,
                "mean_class_risk_score": mean_score,
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
                        classification_label=cp.classification,
                        risk_score=cp.defect_probability,
                        risk_category=cp.risk_category,
                        localization_json=json.dumps(cp.localization.to_dict()) if cp.localization else None,
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
        """Run binary BUG / CLEAN classification on pre-extracted static class metrics."""
        probability, pred_label, risk_cat = self._score_metrics(metrics)
        classification = "BUG" if pred_label == 1 else "CLEAN"
        confidence = round(probability if pred_label == 1 else (1.0 - probability), 4)
        influential = self._compute_influential_metrics(metrics, granularity="class")
        localization = self._localize_bug_class(source_code, methods or [], pred_label)
        explanation = self._build_explanation(
            class_name=class_name,
            classification=classification,
            probability=probability,
            threshold=self.decision_threshold,
            influential=influential,
        )
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
            classification=classification,
            confidence=confidence,
            localization=localization,
            explanation_summary=explanation,
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
                    classification_label=classification,
                    risk_score=round(probability, 4),
                    risk_category=risk_cat,
                    localization_json=json.dumps(localization.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Could not persist class prediction to database: {e}")

        return result

    # ---------------------------------------------------------
    # Historical Method-Level Prediction API (Preserved)
    # ---------------------------------------------------------
    def predict_code(self, code: str, file_name: Optional[str] = None) -> List[MethodPrediction]:
        """Parse C# source code, extract all eligible methods, and classify each."""
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
        classification = "BUG" if pred_label == 1 else "CLEAN"
        confidence = round(risk_score if pred_label == 1 else (1.0 - risk_score), 4)
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
            classification=classification,
            confidence=confidence,
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
                    classification_label=classification,
                    risk_score=round(risk_score, 4),
                    risk_category=risk_cat,
                )
            except Exception as e:
                logger.warning(f"Could not persist prediction to database: {e}")

        return result

    def _compute_influential_metrics(self, metrics: Dict[str, Any], granularity: str = "method") -> List[Dict[str, Any]]:
        """Identify key structural metrics exceeding reference thresholds."""
        influential: List[Dict[str, Any]] = []

        if granularity == "class":
            alert_thresholds = {
                "total_cyclomatic_complexity": (20, "High aggregate McCabe complexity across class members."),
                "max_method_complexity": (10, "Contains at least one method with elevated branching."),
                "high_complexity_method_count": (2, "Multiple methods exceed cyclomatic complexity >= 10."),
                "class_loc": (150, "Large class code footprint."),
                "max_nesting_depth": (4, "Deep lexical control-flow nesting depth."),
                "method_count": (12, "High member method count."),
                "total_try_catch_count": (3, "Multiple exception handling blocks."),
                "total_method_call_count": (30, "High method invocation coupling."),
                "total_if_count": (12, "Elevated conditional branching count."),
                "wmc_density": (0.30, "High cyclomatic complexity density per line."),
            }
        else:
            alert_thresholds = {
                "cyclomatic_complexity": (10, "High cyclomatic complexity."),
                "max_nesting_depth": (4, "Deep control-flow nesting."),
                "loc": (40, "Elevated method length."),
                "statement_count": (25, "High statement count."),
                "loop_count": (3, "Multiple loops."),
                "try_catch_count": (2, "Multiple try/catch blocks."),
                "throw_count": (2, "Multiple throw statements."),
                "conditional_expression_count": (2, "Multiple conditional expressions."),
                "boolean_operator_count": (4, "Complex boolean logic."),
                "method_call_count": (15, "High external method call count."),
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
