"""Automated Machine Learning Experimentation Pipeline for Defect Prediction.
Supports multi-model baseline evaluation (Dummy, Logistic Regression, Decision Tree, Random Forest),
strict GroupKFold validation, probability calibration (Brier score), decision threshold tuning,
reproducible artifact persistence (CSV, JSON, Markdown), and independent holdout testing.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    confusion_matrix,
)

from config.settings import PROJECT_ROOT
from src.ml.cross_validation import (
    CrossValidationResults,
    InsufficientRepositoriesError,
    RepositoryGroupKFoldValidator,
    check_repository_readiness,
    compute_threshold_curve,
)
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager
from src.ml.preprocessing import DataPreprocessor
from src.utils.logger import setup_logger

logger = setup_logger("experiment_runner")


def build_estimator(
    algorithm: str,
    params: Dict[str, Any],
    random_state: int = 42,
) -> Tuple[Any, bool]:
    """Instantiate model estimator and determine whether in-fold feature scaling is required.
    
    Returns:
        (estimator, needs_scaling)
    """
    algo = algorithm.lower().replace("-", "_")
    p = {k: v for k, v in params.items() if k not in ("config_id", "algorithm", "needs_scaling")}

    if algo in ("dummy", "dummy_classifier"):
        strat = p.get("strategy", "most_frequent")
        kwargs: Dict[str, Any] = {"strategy": strat}
        if strat != "most_frequent":
            kwargs["random_state"] = p.get("random_state", random_state)
        return DummyClassifier(**kwargs), False

    elif algo in ("logistic_regression", "lr", "logistic"):
        kwargs = {
            "C": p.get("C", 1.0),
            "max_iter": p.get("max_iter", 1000),
            "solver": p.get("solver", "lbfgs"),
            "class_weight": p.get("class_weight", None),
            "random_state": p.get("random_state", random_state),
        }
        if "penalty" in p:
            kwargs["penalty"] = p["penalty"]
        return LogisticRegression(**kwargs), True

    elif algo in ("decision_tree", "dt", "tree"):
        kwargs = {
            "criterion": p.get("criterion", "gini"),
            "max_depth": p.get("max_depth", None),
            "min_samples_split": p.get("min_samples_split", 2),
            "min_samples_leaf": p.get("min_samples_leaf", 1),
            "class_weight": p.get("class_weight", None),
            "random_state": p.get("random_state", random_state),
        }
        return DecisionTreeClassifier(**kwargs), False

    elif algo in ("random_forest", "rf", "random_forest_classifier"):
        kwargs = {
            "n_estimators": p.get("n_estimators", 100),
            "max_depth": p.get("max_depth", None),
            "min_samples_split": p.get("min_samples_split", 2),
            "min_samples_leaf": p.get("min_samples_leaf", 1),
            "max_features": p.get("max_features", "sqrt"),
            "class_weight": p.get("class_weight", None),
            "random_state": p.get("random_state", random_state),
            "n_jobs": p.get("n_jobs", -1),
        }
        return RandomForestClassifier(**kwargs), False

    else:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. Supported: dummy, logistic_regression, decision_tree, random_forest."
        )


# Default curated configuration matrix covering multiple baseline families and Random Forest
DEFAULT_EXPERIMENT_GRID: List[Dict[str, Any]] = [
    # 1. Baseline Classifiers
    {
        "config_id": "dummy_most_frequent",
        "algorithm": "dummy",
        "strategy": "most_frequent",
    },
    {
        "config_id": "dummy_stratified",
        "algorithm": "dummy",
        "strategy": "stratified",
    },
    # 2. Linear Baseline: Logistic Regression
    {
        "config_id": "lr_standard_c1",
        "algorithm": "logistic_regression",
        "C": 1.0,
        "max_iter": 1000,
        "class_weight": None,
    },
    {
        "config_id": "lr_balanced_c1",
        "algorithm": "logistic_regression",
        "C": 1.0,
        "max_iter": 1000,
        "class_weight": "balanced",
    },
    # 3. Interpretable Tree Baseline: Decision Tree
    {
        "config_id": "dt_shallow_depth4",
        "algorithm": "decision_tree",
        "max_depth": 4,
        "min_samples_split": 5,
        "min_samples_leaf": 4,
        "class_weight": "balanced",
    },
    {
        "config_id": "dt_depth8",
        "algorithm": "decision_tree",
        "max_depth": 8,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "class_weight": "balanced",
    },
    # 4. Complex Ensembles: Random Forest
    {
        "config_id": "rf_baseline_balanced",
        "algorithm": "random_forest",
        "n_estimators": 100,
        "max_depth": 10,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "class_weight": "balanced",
    },
    {
        "config_id": "rf_deep_capacity",
        "algorithm": "random_forest",
        "n_estimators": 200,
        "max_depth": 15,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "max_features": "sqrt",
        "class_weight": "balanced",
    },
    {
        "config_id": "rf_compact_regularized",
        "algorithm": "random_forest",
        "n_estimators": 100,
        "max_depth": 8,
        "min_samples_split": 5,
        "min_samples_leaf": 4,
        "max_features": "sqrt",
        "class_weight": "balanced",
    },
    {
        "config_id": "rf_heavy_bagging_300",
        "algorithm": "random_forest",
        "n_estimators": 300,
        "max_depth": 15,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "class_weight": "balanced",
    },
    {
        "config_id": "rf_feature_constrained_log2",
        "algorithm": "random_forest",
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_split": 4,
        "min_samples_leaf": 2,
        "max_features": "log2",
        "class_weight": "balanced",
    },
]


@dataclass
class ExperimentConfig:
    """Configuration specification for an automated ML experiment run."""
    experiment_id: str = field(default_factory=lambda: f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    description: str = "Automated Multi-Model Baseline & Random Forest Experimentation with GroupKFold"
    random_state: int = 42
    n_splits: int = 5
    strict_groups: bool = True
    selection_metric: str = "f1"  # Metric used to pick the best model from CV
    param_grid: List[Dict[str, Any]] = field(default_factory=lambda: list(DEFAULT_EXPERIMENT_GRID))
    impute_missing: bool = True
    remove_constant: bool = True
    group_col: str = "repository_id"
    output_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "description": self.description,
            "random_state": self.random_state,
            "n_splits": self.n_splits,
            "strict_groups": self.strict_groups,
            "selection_metric": self.selection_metric,
            "param_grid": self.param_grid,
            "impute_missing": self.impute_missing,
            "remove_constant": self.remove_constant,
            "group_col": self.group_col,
            "output_dir": str(self.output_dir) if self.output_dir else None,
        }


@dataclass
class ConfigurationResult:
    """Summary of cross-validation results for a single model configuration."""
    config_id: str
    parameters: Dict[str, Any]
    cv_results: CrossValidationResults
    selection_score: float
    rank: int = 0

    def _format_param_details(self) -> str:
        algo = self.parameters.get("algorithm", "random_forest")
        if algo == "dummy":
            return f"strategy={self.parameters.get('strategy')}"
        elif algo == "logistic_regression":
            return f"C={self.parameters.get('C')}, weight={self.parameters.get('class_weight')}"
        elif algo == "decision_tree":
            return f"depth={self.parameters.get('max_depth')}, leaf={self.parameters.get('min_samples_leaf')}, weight={self.parameters.get('class_weight')}"
        else:
            return (
                f"trees={self.parameters.get('n_estimators')}, depth={self.parameters.get('max_depth')}, "
                f"leaf={self.parameters.get('min_samples_leaf')}, feat={self.parameters.get('max_features')}"
            )

    def to_summary_dict(self) -> Dict[str, Any]:
        agg = self.cv_results.aggregate_metrics
        algo = self.parameters.get("algorithm", "random_forest")
        return {
            "config_id": self.config_id,
            "rank": self.rank,
            "algorithm": algo,
            "selection_score": round(self.selection_score, 4),
            "n_estimators": self.parameters.get("n_estimators"),
            "max_depth": str(self.parameters.get("max_depth")),
            "min_samples_split": self.parameters.get("min_samples_split"),
            "min_samples_leaf": self.parameters.get("min_samples_leaf"),
            "max_features": str(self.parameters.get("max_features")),
            "class_weight": str(self.parameters.get("class_weight")),
            "cv_f1_mean": agg.get("f1", {}).get("mean", 0.0),
            "cv_f1_std": agg.get("f1", {}).get("std", 0.0),
            "cv_roc_auc_mean": agg.get("roc_auc", {}).get("mean", 0.0),
            "cv_roc_auc_std": agg.get("roc_auc", {}).get("std", 0.0),
            "cv_accuracy_mean": agg.get("accuracy", {}).get("mean", 0.0),
            "cv_accuracy_std": agg.get("accuracy", {}).get("std", 0.0),
            "cv_precision_mean": agg.get("precision", {}).get("mean", 0.0),
            "cv_precision_std": agg.get("precision", {}).get("std", 0.0),
            "cv_recall_mean": agg.get("recall", {}).get("mean", 0.0),
            "cv_recall_std": agg.get("recall", {}).get("std", 0.0),
            "cv_average_precision_mean": agg.get("average_precision", {}).get("mean", 0.0),
            "cv_average_precision_std": agg.get("average_precision", {}).get("std", 0.0),
            "cv_brier_score_mean": agg.get("brier_score", {}).get("mean", 0.0),
            "cv_brier_score_std": agg.get("brier_score", {}).get("std", 0.0),
            "mean_train_duration_s": agg.get("train_duration_s", {}).get("mean", 0.0),
            "mean_val_duration_s": agg.get("val_duration_s", {}).get("mean", 0.0),
        }


class ExperimentRunner:
    """Orchestrates end-to-end automated machine learning experiments."""

    def __init__(self, config: Optional[ExperimentConfig] = None) -> None:
        self.config = config or ExperimentConfig()
        base_dir = self.config.output_dir or (PROJECT_ROOT / "reports" / "experiments")
        self.run_dir = base_dir / self.config.experiment_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_dataset_fingerprint(X: pd.DataFrame, y: pd.Series) -> str:
        """Compute SHA256 digest of feature matrix and target labels for provenance."""
        hasher = hashlib.sha256()
        hasher.update(X.to_csv(index=False).encode("utf-8"))
        hasher.update(y.to_csv(index=False).encode("utf-8"))
        return hasher.hexdigest()

    def run_experiment(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        meta_train: pd.DataFrame,
        X_holdout: Optional[pd.DataFrame] = None,
        y_holdout: Optional[pd.Series] = None,
        meta_holdout: Optional[pd.DataFrame] = None,
        dataset_name: str = "csharp_empirical_v1",
    ) -> Dict[str, Any]:
        """Execute cross-validation over the parameter grid, select the best model,
        and evaluate against holdout test data if provided.
        """
        logger.info(f"Starting experiment '{self.config.experiment_id}' ({len(self.config.param_grid)} configurations)")
        start_time = time.time()

        # 1. Inspect repository readiness
        readiness = check_repository_readiness(
            meta_train,
            n_splits=self.config.n_splits,
            group_col=self.config.group_col,
        )

        validator = RepositoryGroupKFoldValidator(
            n_splits=self.config.n_splits,
            strict_repo_count=self.config.strict_groups,
            impute_missing=self.config.impute_missing,
            remove_constant=self.config.remove_constant,
            group_col=self.config.group_col,
        )

        dataset_fp = self.compute_dataset_fingerprint(X_train, y_train)

        # 2. Iterate across all configurations in grid
        config_results: List[ConfigurationResult] = []

        for idx, p in enumerate(self.config.param_grid, 1):
            cfg_id = p.get("config_id", f"config_{idx}")
            algo = p.get("algorithm", "random_forest")

            cfg_params = {k: v for k, v in p.items() if k != "config_id"}
            cfg_params.setdefault("algorithm", algo)
            if algo == "random_forest":
                cfg_params.setdefault("random_state", self.config.random_state)
                cfg_params.setdefault("n_jobs", -1)

            # Build estimator and check scaling requirements
            sample_estimator, needs_scaling = build_estimator(algo, cfg_params, self.config.random_state)

            logger.info(
                f"Evaluating config {idx}/{len(self.config.param_grid)}: '{cfg_id}' (algo={algo}, scaling={needs_scaling})"
            )

            def model_factory() -> Any:
                est, _ = build_estimator(algo, cfg_params, self.config.random_state)
                return est

            cv_res = validator.evaluate_model(
                model_factory=model_factory,
                X_train_raw=X_train,
                y_train=y_train,
                meta_train=meta_train,
                needs_scaling=needs_scaling,
            )

            # Determine score on selection metric
            sel_metric = self.config.selection_metric
            score = cv_res.aggregate_metrics.get(sel_metric, {}).get("mean", 0.0)

            config_results.append(
                ConfigurationResult(
                    config_id=cfg_id,
                    parameters=cfg_params,
                    cv_results=cv_res,
                    selection_score=score,
                )
            )

        # 3. Rank configurations by selection metric descending
        config_results.sort(key=lambda r: r.selection_score, reverse=True)
        for rank, r in enumerate(config_results, 1):
            r.rank = rank

        best_config_result = config_results[0]
        logger.info(
            f"Best configuration: '{best_config_result.config_id}' ({best_config_result.parameters.get('algorithm')}) "
            f"with CV {self.config.selection_metric}={best_config_result.selection_score:.4f}"
        )

        # 4. Decision Threshold Tuning on Best Model's Out-Of-Fold CV Predictions
        threshold_curve: List[Dict[str, Any]] = []
        optimal_cv_threshold: float = 0.50
        optimal_threshold_info: Dict[str, Any] = {}

        if best_config_result.cv_results.oof_predictions:
            oof_y_true = np.array(best_config_result.cv_results.oof_predictions["y_true"])
            oof_y_prob = np.array(best_config_result.cv_results.oof_predictions["y_prob"])
            threshold_curve = compute_threshold_curve(oof_y_true, oof_y_prob)

            if threshold_curve:
                best_t_entry = max(threshold_curve, key=lambda x: x["f1"])
                optimal_cv_threshold = float(best_t_entry["threshold"])
                optimal_threshold_info = {
                    "optimal_threshold": optimal_cv_threshold,
                    "cv_f1_at_optimal": best_t_entry["f1"],
                    "cv_precision_at_optimal": best_t_entry["precision"],
                    "cv_recall_at_optimal": best_t_entry["recall"],
                    "cv_accuracy_at_optimal": best_t_entry["accuracy"],
                }

        # 5. Final Model Training on complete training partition
        logger.info(f"Training final model on full training set using best configuration '{best_config_result.config_id}'...")
        final_preproc = DataPreprocessor(
            impute_missing=self.config.impute_missing,
            remove_constant=self.config.remove_constant,
        )
        X_train_proc = final_preproc.fit_transform(X_train)

        best_algo = best_config_result.parameters.get("algorithm", "random_forest")
        raw_estimator, best_needs_scaling = build_estimator(
            best_algo,
            best_config_result.parameters,
            self.config.random_state,
        )

        if best_needs_scaling:
            final_model = Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", raw_estimator),
            ])
        else:
            final_model = raw_estimator

        final_model.fit(X_train_proc, y_train)

        # 6. One-Shot Holdout Evaluation (if holdout partition provided)
        holdout_results: Optional[Dict[str, Any]] = None
        if X_holdout is not None and y_holdout is not None and not X_holdout.empty:
            logger.info("Evaluating selected model on independent holdout test set...")
            X_holdout_proc = final_preproc.transform(X_holdout)
            holdout_results = ModelEvaluator.evaluate(final_model, X_holdout_proc, y_holdout)
            holdout_results["holdout_samples"] = len(y_holdout)
            if meta_holdout is not None and self.config.group_col in meta_holdout.columns:
                holdout_results["holdout_repositories"] = [str(r) for r in meta_holdout[self.config.group_col].unique()]

            # Compute holdout Brier score
            if hasattr(final_model, "predict_proba"):
                y_prob_holdout = final_model.predict_proba(X_holdout_proc)[:, 1]
                holdout_results["brier_score"] = round(float(brier_score_loss(y_holdout, y_prob_holdout)), 4)

                # Evaluate holdout at CV-optimized threshold to test out-of-domain transfer
                y_pred_opt = (y_prob_holdout >= optimal_cv_threshold).astype(int)
                holdout_results["optimal_cv_threshold_used"] = optimal_cv_threshold
                holdout_results["holdout_at_optimal_cv_threshold"] = {
                    "accuracy": round(float(accuracy_score(y_holdout, y_pred_opt)), 4),
                    "precision": round(float(precision_score(y_holdout, y_pred_opt, zero_division=0)), 4),
                    "recall": round(float(recall_score(y_holdout, y_pred_opt, zero_division=0)), 4),
                    "f1": round(float(f1_score(y_holdout, y_pred_opt, zero_division=0)), 4),
                    "confusion_matrix": confusion_matrix(y_holdout, y_pred_opt, labels=[0, 1]).tolist(),
                }

        total_exec_duration = round(time.time() - start_time, 2)

        # 7. Persist Model Bundle
        models_dir = self.run_dir / "model"
        models_dir.mkdir(parents=True, exist_ok=True)
        model_mgr = ModelManager(models_dir)
        saved_model_path = model_mgr.save_model(
            model_name=f"{self.config.experiment_id}_best_{best_config_result.config_id}",
            model=final_model,
            preprocessor=final_preproc,
            feature_names=final_preproc.feature_names_out_,
            parameters=best_config_result.parameters,
            metrics=holdout_results or best_config_result.cv_results.aggregate_metrics,
            split_summary={
                "train_samples": len(X_train),
                "cv_folds": validator.n_splits,
                "holdout_samples": len(X_holdout) if X_holdout is not None else 0,
            },
            overwrite=True,
        )

        # 8. Generate Output Files (CSV, JSON, Markdown)
        csv_path = self.save_csv_results(config_results)
        json_path = self.save_json_results(
            config_results=config_results,
            best_config_result=best_config_result,
            holdout_results=holdout_results,
            dataset_name=dataset_name,
            dataset_fingerprint=dataset_fp,
            readiness=readiness,
            total_duration_s=total_exec_duration,
            threshold_curve=threshold_curve,
            optimal_threshold_info=optimal_threshold_info,
        )
        report_path = self.generate_markdown_report(
            config_results=config_results,
            best_config_result=best_config_result,
            holdout_results=holdout_results,
            dataset_name=dataset_name,
            readiness=readiness,
            total_duration_s=total_exec_duration,
            saved_model_path=saved_model_path,
            threshold_curve=threshold_curve,
            optimal_threshold_info=optimal_threshold_info,
        )

        return {
            "experiment_id": self.config.experiment_id,
            "run_dir": str(self.run_dir),
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "report_path": str(report_path),
            "saved_model_path": str(saved_model_path),
            "best_config_id": best_config_result.config_id,
            "best_parameters": best_config_result.parameters,
            "best_cv_score": best_config_result.selection_score,
            "holdout_results": holdout_results,
            "optimal_threshold_info": optimal_threshold_info,
            "total_duration_s": total_exec_duration,
        }

    def save_csv_results(self, results: List[ConfigurationResult]) -> Path:
        """Persist configuration metrics table to experiment_results.csv."""
        csv_path = self.run_dir / "experiment_results.csv"
        rows = [r.to_summary_dict() for r in results]
        if not rows:
            return csv_path

        fieldnames = list(rows[0].keys())
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Saved CSV results to {csv_path}")
        return csv_path

    def save_json_results(
        self,
        config_results: List[ConfigurationResult],
        best_config_result: ConfigurationResult,
        holdout_results: Optional[Dict[str, Any]],
        dataset_name: str,
        dataset_fingerprint: str,
        readiness: Any,
        total_duration_s: float,
        threshold_curve: List[Dict[str, Any]],
        optimal_threshold_info: Dict[str, Any],
    ) -> Path:
        """Persist complete experiment metadata and fold-level metrics to experiment_results.json."""
        json_path = self.run_dir / "experiment_results.json"

        data = {
            "experiment_id": self.config.experiment_id,
            "description": self.config.description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_state": self.config.random_state,
            "dataset": {
                "name": dataset_name,
                "fingerprint_sha256": dataset_fingerprint,
                "readiness": readiness.to_dict() if hasattr(readiness, "to_dict") else str(readiness),
            },
            "selection_metric": self.config.selection_metric,
            "total_duration_s": total_duration_s,
            "best_configuration": {
                "config_id": best_config_result.config_id,
                "algorithm": best_config_result.parameters.get("algorithm", "random_forest"),
                "parameters": best_config_result.parameters,
                "cv_score": best_config_result.selection_score,
            },
            "threshold_optimization": {
                "optimal_threshold": optimal_threshold_info.get("optimal_threshold", 0.50),
                "cv_performance": optimal_threshold_info,
                "threshold_curve": threshold_curve,
            },
            "holdout_evaluation": holdout_results,
            "configurations": [
                {
                    "config_id": r.config_id,
                    "rank": r.rank,
                    "algorithm": r.parameters.get("algorithm", "random_forest"),
                    "parameters": r.parameters,
                    "selection_score": round(r.selection_score, 4),
                    "cv_results": r.cv_results.to_dict(),
                }
                for r in config_results
            ],
        }

        with open(json_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved JSON results to {json_path}")
        return json_path

    def generate_markdown_report(
        self,
        config_results: List[ConfigurationResult],
        best_config_result: ConfigurationResult,
        holdout_results: Optional[Dict[str, Any]],
        dataset_name: str,
        readiness: Any,
        total_duration_s: float,
        saved_model_path: Path,
        threshold_curve: List[Dict[str, Any]],
        optimal_threshold_info: Dict[str, Any],
    ) -> Path:
        """Generate comprehensive academic experiment report in Markdown format."""
        report_path = self.run_dir / "experiment_report.md"

        lines: List[str] = [
            f"# Multi-Model Defect Prediction Experiment Report: {self.config.experiment_id}",
            "",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Dataset Snapshot:** `{dataset_name}`  ",
            f"**Execution Duration:** {total_duration_s}s  ",
            f"**Selection Metric:** `{self.config.selection_metric}`  ",
            f"**Cross-Validation Strategy:** {self.config.n_splits}-fold GroupKFold by `{self.config.group_col}`  ",
            "",
            "---",
            "",
            "## 1. Experiment Objective & Protocol",
            "",
            "This experiment evaluates multiple classification model families on method-level software defect prediction "
            "using static code metrics. Evaluated model families include **Dummy baselines** (most frequent and stratified), "
            "**Logistic Regression** (linear baseline with in-fold standard scaling), **Decision Tree** (interpretable tree baseline), "
            "and **Random Forest** (non-linear ensemble).",
            "",
            "### Leakage Prevention Guarantees",
            "1. **Repository-Aware Partitioning:** Zero overlap between training and validation repositories within any fold.",
            "2. **Independent Preprocessing:** Median imputation, zero-variance pruning, and feature scaling (`StandardScaler`) "
            "are fitted strictly on the training partition of each fold and applied to the validation partition without leakage.",
            "3. **Holdout Isolation:** The holdout repository was strictly isolated from training, preprocessing, hyperparameter "
            "search, and decision threshold selection.",
            "",
            "### Repository Grouping Feasibility",
            f"- **Available Training Repositories:** {readiness.available_repo_count}",
            f"- **Required Repositories for {self.config.n_splits}-fold GroupKFold:** {readiness.required_repo_count}",
            f"- **Readiness Status:** {'[PASS] Sufficient Repositories' if readiness.is_ready else '[PARTIAL] Limited Repository Corpus'}",
            f"- **Diagnostic Note:** {readiness.recommendation}",
            "",
            "---",
            "",
            "## 2. Multi-Model Benchmark & Cross-Validation Results",
            "",
            "| Rank | Configuration ID | Algorithm | Hyperparameters | Mean F1 | F1 Std | Mean ROC-AUC | Mean AP | Mean Brier |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for r in config_results:
            agg = r.cv_results.aggregate_metrics
            algo = r.parameters.get("algorithm", "rf")
            f1_m = agg.get("f1", {}).get("mean", 0.0)
            f1_s = agg.get("f1", {}).get("std", 0.0)
            auc_m = agg.get("roc_auc", {}).get("mean", 0.0)
            ap_m = agg.get("average_precision", {}).get("mean", 0.0)
            brier_m = agg.get("brier_score", {}).get("mean", 0.0)
            details = r._format_param_details()

            lines.append(
                f"| **#{r.rank}** | `{r.config_id}` | `{algo}` | {details} | "
                f"**{f1_m:.4f}** | $\\pm {f1_s:.4f}$ | {auc_m:.4f} | {ap_m:.4f} | {brier_m:.4f} |"
            )

        dummy_f1 = best_config_result.cv_results.baseline_metrics.get("dummy_most_frequent_f1", {}).get("mean", 0.0)
        lift = best_config_result.selection_score - dummy_f1

        lines.extend([
            "",
            "---",
            "",
            "## 3. Best Model Selection & Baseline Lift",
            "",
            f"- **Selected Model:** `{best_config_result.config_id}` (Rank #1)",
            f"- **Algorithm:** `{best_config_result.parameters.get('algorithm')}`",
            f"- **Cross-Validation {self.config.selection_metric.upper()}:** **{best_config_result.selection_score:.4f}**",
            f"- **Saved Model Artifact:** `{saved_model_path.name}`",
            "",
            "### Baseline Comparison (DummyClassifier)",
            f"- **Dummy (Most Frequent) Cross-Validation F1:** `{dummy_f1:.4f}`",
            f"- **Lift over Majority Guessing:** The selected model achieves **+{lift:.4f}** F1 points over `DummyClassifier(strategy='most_frequent')`.",
            "",
            "### Comparative Model Family Breakdown",
        ])

        # Summarize best per algorithm family
        algos_present = sorted(list({r.parameters.get("algorithm", "rf") for r in config_results}))
        for a in algos_present:
            family_results = [r for r in config_results if r.parameters.get("algorithm") == a]
            best_in_family = min(family_results, key=lambda x: x.rank)
            agg = best_in_family.cv_results.aggregate_metrics
            lines.append(
                f"- **Best {a.upper()}:** `{best_in_family.config_id}` — F1: `{agg.get('f1', {}).get('mean', 0.0):.4f}`, "
                f"ROC-AUC: `{agg.get('roc_auc', {}).get('mean', 0.0):.4f}`, Brier: `{agg.get('brier_score', {}).get('mean', 0.0):.4f}`"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Fold-Level Performance & Stability Analysis",
            "",
            "| Fold | Train Repos | Val Repos | Train (Buggy / Clean) | Val (Buggy / Clean) | Confusion Matrix [TN, FP, FN, TP] | F1 | ROC-AUC | Brier Score |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for fm in best_config_result.cv_results.fold_metrics:
            cm_flat = [fm.confusion_matrix[0][0], fm.confusion_matrix[0][1], fm.confusion_matrix[1][0], fm.confusion_matrix[1][1]]
            lines.append(
                f"| Fold {fm.fold_index} | {fm.train_repo_count} | {fm.val_repo_count} | "
                f"{fm.train_buggy_count} / {fm.train_clean_count} | {fm.val_buggy_count} / {fm.val_clean_count} | "
                f"`{cm_flat}` | **{fm.f1:.4f}** | {fm.roc_auc:.4f} | {fm.brier_score:.4f} |"
            )

        if threshold_curve:
            lines.extend([
                "",
                "---",
                "",
                "## 5. Decision Threshold Optimization (Out-of-Fold Cross-Validation)",
                "",
                "Decision threshold was swept strictly across out-of-fold validation predictions to analyze precision-recall "
                "trade-offs without holdout data leakage:",
                "",
                "| Threshold | Accuracy | Precision | Recall | F1-Score | True Negatives | False Positives | False Negatives | True Positives |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for tc in threshold_curve:
                is_opt = tc["threshold"] == optimal_threshold_info.get("optimal_threshold")
                mark = "**" if is_opt else ""
                lines.append(
                    f"| {mark}{tc['threshold']:.2f}{mark} | {tc['accuracy']:.4f} | {tc['precision']:.4f} | "
                    f"{tc['recall']:.4f} | {mark}{tc['f1']:.4f}{mark} | {tc.get('true_negatives', '-')} | "
                    f"{tc['false_positives']} | {tc.get('false_negatives', '-')} | {tc['true_positives']} |"
                )
            lines.append(f"\n> **Optimal CV Decision Threshold:** `{optimal_threshold_info.get('optimal_threshold', 0.50):.2f}` "
                         f"(F1 = {optimal_threshold_info.get('cv_f1_at_optimal', 0.0):.4f})")

        if holdout_results is not None:
            lines.extend([
                "",
                "---",
                "",
                "## 6. Independent Repository Holdout Evaluation",
                "",
                "> [!IMPORTANT]",
                "> The holdout repository (`commandlineparser/commandline`) was strictly isolated from hyperparameter exploration, "
                "> model selection, and threshold tuning. These metrics evaluate true out-of-domain transferability.",
                "",
                f"- **Holdout Repositories:** `{holdout_results.get('holdout_repositories', ['Holdout'])}`",
                f"- **Holdout Methods Evaluated:** {holdout_results.get('holdout_samples', holdout_results.get('test_sample_count', 0))}",
                "",
                "### Performance at Standard Decision Threshold (0.50)",
                f"- **Accuracy:** **{holdout_results.get('accuracy', 0.0):.4f}**",
                f"- **Precision:** **{holdout_results.get('precision', 0.0):.4f}**",
                f"- **Recall:** **{holdout_results.get('recall', 0.0):.4f}**",
                f"- **F1-Score:** **{holdout_results.get('f1', 0.0):.4f}**",
                f"- **ROC-AUC:** **{holdout_results.get('roc_auc', 0.0):.4f}**",
                f"- **Average Precision (PR-AUC):** **{holdout_results.get('average_precision', 0.0):.4f}**",
                f"- **Brier Score (Probability Calibration):** **{holdout_results.get('brier_score', 0.0)}**",
                f"- **Confusion Matrix [TN, FP, FN, TP]:** `{holdout_results.get('confusion_matrix')}`",
            ])

            if "holdout_at_optimal_cv_threshold" in holdout_results:
                opt_ho = holdout_results["holdout_at_optimal_cv_threshold"]
                lines.extend([
                    "",
                    f"### Transfer of CV-Optimized Threshold ({holdout_results.get('optimal_cv_threshold_used', 0.50):.2f})",
                    f"- **Holdout Accuracy:** `{opt_ho.get('accuracy', 0.0):.4f}`",
                    f"- **Holdout Precision:** `{opt_ho.get('precision', 0.0):.4f}`",
                    f"- **Holdout Recall:** `{opt_ho.get('recall', 0.0):.4f}`",
                    f"- **Holdout F1-Score:** `{opt_ho.get('f1', 0.0):.4f}`",
                    f"- **Confusion Matrix:** `{opt_ho.get('confusion_matrix')}`",
                ])

        lines.extend([
            "",
            "---",
            "",
            "## 7. Methodological Limitations & Future Work",
            "",
            "1. **Corpus Size for 5-Fold GroupKFold:** Running full 5-fold cross-validation requires at least 5 distinct training "
            "repositories. With the current dataset of 2 training repositories, cross-validation evaluates across $K=2$ folds.",
            "2. **Open-World Assumption on Candidate Clean Labels:** Methods without bug-fix blame traces are candidate clean; "
            "unreported latent bugs may introduce label noise.",
            "3. **Artificial Balance:** Experimental balance (~47% buggy) improves tree split stability but does not reflect "
            "industrial defect prevalence (5%–15%).",
            "4. **Threshold Generalization:** While threshold tuning on CV optimizes within-domain F1, domain shifts across "
            "unseen repositories may affect optimal operating points.",
        ])

        with open(report_path, mode="w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Standalone holdout report
        if holdout_results is not None:
            holdout_report_path = self.run_dir / "holdout_evaluation_report.md"
            holdout_lines = [
                f"# Independent Holdout Evaluation Report: {self.config.experiment_id}",
                "",
                f"**Selected Model:** `{best_config_result.config_id}` ({best_config_result.parameters.get('algorithm')})  ",
                f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
                "",
                "## Performance on Unseen Holdout Repository (`commandlineparser/commandline`)",
                "",
                f"| Metric | Standard Threshold (0.50) | CV-Optimized Threshold ({holdout_results.get('optimal_cv_threshold_used', 0.50):.2f}) |",
                f"| :--- | :--- | :--- |",
                f"| Accuracy | {holdout_results.get('accuracy', 0.0):.4f} | {holdout_results.get('holdout_at_optimal_cv_threshold', {}).get('accuracy', 0.0):.4f} |",
                f"| Precision | {holdout_results.get('precision', 0.0):.4f} | {holdout_results.get('holdout_at_optimal_cv_threshold', {}).get('precision', 0.0):.4f} |",
                f"| Recall | {holdout_results.get('recall', 0.0):.4f} | {holdout_results.get('holdout_at_optimal_cv_threshold', {}).get('recall', 0.0):.4f} |",
                f"| F1-Score | {holdout_results.get('f1', 0.0):.4f} | {holdout_results.get('holdout_at_optimal_cv_threshold', {}).get('f1', 0.0):.4f} |",
                f"| ROC-AUC | {holdout_results.get('roc_auc', 0.0):.4f} | N/A |",
                f"| PR-AUC | {holdout_results.get('average_precision', 0.0):.4f} | N/A |",
                f"| Brier Score | {holdout_results.get('brier_score', 0.0)} | N/A |",
                f"| Confusion Matrix | `{holdout_results.get('confusion_matrix')}` | `{holdout_results.get('holdout_at_optimal_cv_threshold', {}).get('confusion_matrix')}` |",
                "",
                "## Methodological Distinction Between Cross-Validation and Holdout Evaluation",
                "Cross-validation was conducted exclusively within the training partition to select the optimal model ",
                "family, hyperparameters, and decision threshold. The holdout dataset was never observed during training, ",
                "feature pruning, imputation fitting, or threshold selection, confirming true out-of-domain generalization capacity.",
            ]
            with open(holdout_report_path, mode="w", encoding="utf-8") as f:
                f.write("\n".join(holdout_lines) + "\n")

        logger.info(f"Generated experiment report at {report_path}")
        return report_path
