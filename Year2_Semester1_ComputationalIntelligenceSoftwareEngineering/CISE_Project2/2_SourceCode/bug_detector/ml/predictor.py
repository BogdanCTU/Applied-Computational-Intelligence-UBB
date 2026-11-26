"""Inference predictor combining Roslyn method extraction, FeaturePipeline, RF, and local evidence."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from bug_detector.config.settings import AppConfig, load_config
from bug_detector.db import BugDetectorRepository, DatabaseManager
from bug_detector.db.repository import sha256_text
from bug_detector.explainability.local_evidence import (
    compute_tree_path_contributions,
    rank_suspicious_methods,
)
from bug_detector.ml.calibration import apply_three_way_decision
from bug_detector.ml.registry import load_model_bundle
from bug_detector.preprocessing.models import FileAnalysisResult, MethodAnalysis
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient


def _method_to_feature_record(m: MethodAnalysis) -> dict[str, Any]:
    return {
        "extraction_failed": bool(m.has_syntax_errors),
        "semantic_model_available": bool(m.dfg_metrics.get("semantic_model_available", 0.0) > 0.5),
        "tokens_normalized": m.tokens_normalized,
        "api_calls": m.api_calls,
        "lexical_metrics": m.lexical_metrics,
        "ast_metrics": m.ast_metrics,
        "cfg_metrics": m.cfg_metrics,
        "dfg_metrics": m.dfg_metrics,
        "structural_metrics": m.structural_metrics,
    }


class BugDetectorPredictor:
    """End-to-end method-level C# bug detection predictor."""

    def __init__(
        self,
        model_path_or_version: str | Path | None = None,
        config: AppConfig | None = None,
    ) -> None:
        self.config = config or load_config()
        self.bundle = load_model_bundle(model_path_or_version, config=self.config)
        self.model_version: str = self.bundle.get("model_version") or (
            self.config.inference.active_model_version or "v5-unknown"
        )
        self.pipeline = self.bundle["feature_pipeline"]
        self.estimator = self.bundle["estimator"]
        self.threshold_low = float(self.config.thresholds.threshold_low if model_path_or_version is None and self.config.inference.active_model_version == self.model_version else self.bundle["threshold_low"])
        self.threshold_center = float(self.config.thresholds.threshold_center if model_path_or_version is None and self.config.inference.active_model_version == self.model_version else self.bundle["threshold_center"])
        self.threshold_high = float(self.config.thresholds.threshold_high if model_path_or_version is None and self.config.inference.active_model_version == self.model_version else self.bundle["threshold_high"])
        self.repo = BugDetectorRepository(DatabaseManager(self.config.db_path))

    def predict_source(
        self,
        source_code: str,
        file_name: str = "Input.cs",
        input_mode: str = "paste",
        persist_run: bool = True,
        roslyn_client: RoslynPreprocessorClient | None = None,
    ) -> dict[str, Any]:
        """Analyze C# source code and classify every extracted method into BUG / CLEAN / UNCERTAIN."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        own_client = roslyn_client is None
        client = roslyn_client or RoslynPreprocessorClient(self.config)
        try:
            analysis: FileAnalysisResult = client.analyze_source(
                source_code=source_code,
                file_path=file_name,
                mode="file",
                normalization=self.config.normalization,
            )
        finally:
            if own_client:
                client.close()

        # Refuse to output CLEAN on syntax-broken or unparseable source
        if not analysis.success or analysis.has_syntax_errors:
            err_msg = analysis.error_message or f"Source contains {analysis.syntax_error_count} C# syntax error(s)."
            error_preds = [
                {
                    "file_name": file_name,
                    "class_name": m.class_name,
                    "method_name": m.method_name,
                    "method_signature": m.method_signature,
                    "start_line": m.start_line,
                    "end_line": m.end_line,
                    "classification": "ANALYSIS_ERROR",
                    "probability": None,
                    "threshold_low": self.threshold_low,
                    "threshold_center": self.threshold_center,
                    "threshold_high": self.threshold_high,
                    "uncertainty_status": "syntax_error_blocks_classification",
                    "model_version": self.model_version,
                    "feature_extraction_status": "failed_syntax_errors",
                    "suspicious_rank": None,
                    "historical_match_sample_id": None,
                    "historical_provenance": None,
                    "local_evidence": {"method": "unavailable", "reason": err_msg},
                    "method_source_hash": sha256_text(m.normalized_source or m.raw_source),
                    "extraction_warnings": m.extraction_warnings,
                }
                for m in analysis.methods
            ]
            if persist_run:
                self.repo.save_detection_run(
                    run_id=run_id,
                    model_version=self.model_version,
                    input_mode=input_mode,
                    file_name=file_name,
                    source_code=source_code,
                    analysis_status="ANALYSIS_ERROR",
                    syntax_error_count=analysis.syntax_error_count,
                    predictions=error_preds,
                    error_message=err_msg,
                )
            return {
                "run_id": run_id,
                "file_name": file_name,
                "model_version": self.model_version,
                "analysis_status": "ANALYSIS_ERROR",
                "has_syntax_errors": True,
                "syntax_error_count": analysis.syntax_error_count,
                "syntax_errors": [e.model_dump() for e in analysis.syntax_errors],
                "error_message": err_msg,
                "methods": error_preds,
            }

        if not analysis.methods:
            msg = "No supported C# methods or constructors were found in source."
            if persist_run:
                self.repo.save_detection_run(
                    run_id=run_id,
                    model_version=self.model_version,
                    input_mode=input_mode,
                    file_name=file_name,
                    source_code=source_code,
                    analysis_status="NO_METHODS",
                    syntax_error_count=0,
                    predictions=[],
                    error_message=msg,
                )
            return {
                "run_id": run_id,
                "file_name": file_name,
                "model_version": self.model_version,
                "analysis_status": "NO_METHODS",
                "has_syntax_errors": False,
                "syntax_error_count": 0,
                "syntax_errors": [],
                "error_message": msg,
                "methods": [],
            }

        records = [_method_to_feature_record(m) for m in analysis.methods]
        X_mat, stats_by_group = self.pipeline.transform(records)
        probs = self.estimator.predict_proba(X_mat)[:, 1]
        feature_names = self.pipeline.get_feature_names()
        group_map = self.pipeline.get_feature_group_map()

        predictions: list[dict[str, Any]] = []
        for idx, (m, prob) in enumerate(zip(analysis.methods, probs)):
            prob_f = float(prob)
            verdict, unc_status = apply_three_way_decision(prob_f, self.threshold_low, self.threshold_high)
            m_hash = sha256_text(m.normalized_source or m.raw_source)
            hist_matches = self.repo.lookup_historical_provenance(m_hash)
            local_ev = compute_tree_path_contributions(
                estimator=self.estimator,
                X_row=X_mat[idx],
                feature_names=feature_names,
                group_map=group_map,
                top_k=self.config.inference.top_local_evidence_count,
            )
            sem_ok = bool(m.dfg_metrics.get("semantic_model_available", 0.0) > 0.5)
            fe_status = "complete" if sem_ok else "syntactic_only_no_semantic_context"
            predictions.append(
                {
                    "file_name": file_name,
                    "class_name": m.class_name,
                    "type_kind": m.type_kind,
                    "method_name": m.method_name,
                    "method_signature": m.method_signature,
                    "start_line": m.start_line,
                    "end_line": m.end_line,
                    "classification": verdict,
                    "probability": round(prob_f, 4),
                    "threshold_low": round(self.threshold_low, 4),
                    "threshold_center": round(self.threshold_center, 4),
                    "threshold_high": round(self.threshold_high, 4),
                    "uncertainty_status": unc_status,
                    "model_version": self.model_version,
                    "feature_extraction_status": fe_status,
                    "suspicious_rank": None,
                    "historical_match_sample_id": hist_matches[0]["sample_id"] if hist_matches else None,
                    "historical_provenance": hist_matches if hist_matches else None,
                    "local_evidence": local_ev,
                    "method_source_hash": m_hash,
                    "extraction_warnings": m.extraction_warnings,
                    "clean_disclaimer": (
                        "CLEAN indicates the model did not detect a defect pattern above threshold; it does not prove correctness."
                        if verdict == "CLEAN"
                        else None
                    ),
                }
            )

        rank_suspicious_methods(predictions)
        if persist_run:
            self.repo.save_detection_run(
                run_id=run_id,
                model_version=self.model_version,
                input_mode=input_mode,
                file_name=file_name,
                source_code=source_code,
                analysis_status="OK",
                syntax_error_count=0,
                predictions=predictions,
            )

        return {
            "run_id": run_id,
            "file_name": file_name,
            "model_version": self.model_version,
            "analysis_status": "OK",
            "has_syntax_errors": False,
            "syntax_error_count": 0,
            "syntax_errors": [],
            "semantic_model_available": analysis.semantic_model_available,
            "error_message": None,
            "methods": predictions,
            "feature_extraction_stats": {g: s.failed_items for g, s in stats_by_group.items()},
        }
