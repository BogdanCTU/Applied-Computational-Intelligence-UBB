"""Controlled ML experiments A-I, leave-one-group-out ablation, independent & temporal eval."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bug_detector.config.settings import EXPERIMENT_DEFINITIONS, AppConfig, load_config
from bug_detector.db import BugDetectorRepository, DatabaseManager
from bug_detector.explainability.global_importance import compute_global_importances
from bug_detector.logging_utils import get_logger
from bug_detector.ml.evaluator import analyze_false_positives_and_negatives, compute_classification_metrics
from bug_detector.ml.registry import save_model_bundle
from bug_detector.ml.splitting import build_repository_splits, verify_zero_leakage
from bug_detector.ml.trainer import (
    load_dataset_records_from_db,
    train_random_forest_with_cv,
    train_secondary_baseline,
)

logger = get_logger(__name__)


class ExperimentSuiteRunner:
    """Runs Experiments A-I, feature ablation, baselines, and independent evaluation."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.repo = BugDetectorRepository(DatabaseManager(self.config.db_path))

    def _evaluate_bundle_on_split(
        self, bundle: dict[str, Any], records: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
        if not records:
            return {"sample_count": 0, "bug_count": 0, "clean_count": 0, "repository_count": 0}, np.array([]), np.array([])
        X, _ = bundle["feature_pipeline"].transform(records)
        y = np.array([int(r["label"]) for r in records], dtype=int)
        probs = bundle["estimator"].predict_proba(X)[:, 1]
        metrics = compute_classification_metrics(
            y_true=y,
            y_prob=probs,
            threshold_low=bundle["threshold_low"],
            threshold_center=bundle["threshold_center"],
            threshold_high=bundle["threshold_high"],
            repository_ids=[str(r["repository_id"]) for r in records],
        )
        return metrics, y, probs

    def _generate_plots(
        self,
        exp_df: pd.DataFrame,
        champion_bundle: dict[str, Any],
        test_metrics: dict[str, Any],
        test_global_imp: dict[str, Any],
        out_dir: Path,
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        # 1. Experiment comparison bar chart (Independent Test F1, PR-AUC, ROC-AUC)
        fig, ax = plt.subplots(figsize=(10, 4.8))
        x = np.arange(len(exp_df))
        w = 0.26
        ax.bar(x - w, exp_df["test_f1"].fillna(0), width=w, label="F1-Score")
        ax.bar(x, exp_df["test_pr_auc"].fillna(0), width=w, label="PR-AUC")
        ax.bar(x + w, exp_df["test_roc_auc"].fillna(0), width=w, label="ROC-AUC")
        ax.set_xticks(x)
        ax.set_xticklabels(exp_df["experiment_code"])
        ax.set_ylim(0, 1.0)
        ax.set_ylabel("Score")
        ax.set_title("Random Forest Feature Experiments (A-I) — Independent Test Set")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "experiments_a_to_i_comparison.png", dpi=150)
        plt.close(fig)

        # 2. Champion Confusion Matrix
        cm = np.array(test_metrics.get("confusion_matrix", [[0, 0], [0, 0]]))
        fig, ax = plt.subplots(figsize=(4.5, 4.0))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["CLEAN (0)", "BUG (1)"])
        ax.set_yticklabels(["CLEAN (0)", "BUG (1)"])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"Independent Test Confusion Matrix ({champion_bundle['experiment_code']})")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black", fontsize=12)
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(out_dir / "champion_confusion_matrix.png", dpi=150)
        plt.close(fig)

        # 3. Calibration curve
        bins = test_metrics.get("calibration_bins") or []
        if bins:
            fig, ax = plt.subplots(figsize=(5.0, 4.2))
            mp = [b["mean_predicted"] for b in bins]
            fp = [b["fraction_positive"] for b in bins]
            ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
            ax.plot(mp, fp, "o-", label="Random Forest")
            ax.set_xlabel("Mean Predicted Probability")
            ax.set_ylabel("Observed BUG Fraction")
            ax.set_title(f"Calibration Curve (Brier = {test_metrics.get('brier_score')})")
            ax.legend()
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "champion_calibration_curve.png", dpi=150)
            plt.close(fig)

        # 4. Feature-group permutation importance
        g_imp = test_global_imp.get("group_importance") or {}
        if g_imp:
            groups = list(g_imp.keys())
            vals = [g_imp[g]["permutation_importance_sum"] for g in groups]
            fig, ax = plt.subplots(figsize=(7.0, 4.0))
            ax.barh(groups, vals)
            ax.set_xlabel("Summed Held-Out Permutation Importance (PR-AUC drop)")
            ax.set_title("Feature-Group Importance on Independent Test Set")
            ax.grid(axis="x", alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "feature_group_importance.png", dpi=150)
            plt.close(fig)

    def run_all(self, dataset_version: str | None = None) -> dict[str, Any]:
        """Execute Experiments A-I, leave-one-group-out ablation, baselines, and full evaluation."""
        dver = dataset_version or self.config.dataset_version
        records, ds_meta = load_dataset_records_from_db(dver, self.config)
        ds_sha = ds_meta.get("dataset_sha256")

        splits = build_repository_splits(
            records,
            independent_test_fraction=self.config.validation.independent_test_repo_fraction,
            temporal_test_fraction=self.config.validation.temporal_test_fraction,
            random_state=self.config.validation.random_state,
        )
        dev_recs = splits["dev"]
        test_recs = splits["independent_test"]
        hn_recs = splits["hard_negative_test"]
        t_train = splits["temporal_train"]
        t_test = splits["temporal_test"]

        verify_zero_leakage(dev_recs, test_recs, hn_recs)
        part_map = {r["sample_id"]: r["split_partition"] for r in dev_recs + test_recs + hn_recs}
        self.repo.update_sample_partitions(dver, part_map)

        out_dir = self.config.results_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        exp_rows: list[dict[str, Any]] = []
        bundles_by_code: dict[str, dict[str, Any]] = {}

        # Run Experiments A-I
        for code, groups in EXPERIMENT_DEFINITIONS.items():
            logger.info("Running Experiment %s with groups=%s...", code, groups)
            bundle = train_random_forest_with_cv(
                dev_records=dev_recs,
                dataset_version=dver,
                dataset_sha256=ds_sha,
                experiment_code=code,
                feature_groups=groups,
                config=self.config,
                tune_hyperparameters=(code in {"H", "I"}),
                tune_calibration=(code in {"H", "I"}),
            )
            test_m, _, _ = self._evaluate_bundle_on_split(bundle, test_recs)
            hn_m, _, _ = self._evaluate_bundle_on_split(bundle, hn_recs)

            temporal_m = None
            if len(t_train) >= 40 and len(t_test) >= 20:
                t_bundle = train_random_forest_with_cv(
                    dev_records=t_train,
                    dataset_version=dver,
                    dataset_sha256=ds_sha,
                    experiment_code=code,
                    feature_groups=groups,
                    config=self.config,
                    tune_hyperparameters=False,
                    tune_calibration=False,
                )
                temporal_m, _, _ = self._evaluate_bundle_on_split(t_bundle, t_test)

            exp_id = f"exp_{code}_{uuid.uuid4().hex[:8]}"
            bundle["experiment_id"] = exp_id
            bundle["independent_test_metrics"] = test_m
            bundle["hard_negative_metrics"] = hn_m
            bundle["temporal_metrics"] = temporal_m

            self.repo.save_experiment(
                {
                    "experiment_id": exp_id,
                    "dataset_version": dver,
                    "experiment_code": code,
                    "algorithm": "RandomForestClassifier",
                    "feature_groups": groups,
                    "hyperparameters": bundle["hyperparameters"],
                    "cv_metrics": bundle["cv_metrics"],
                    "test_metrics": test_m,
                    "hard_negative_metrics": hn_m,
                    "temporal_metrics": temporal_m,
                    "duration_seconds": bundle["duration_seconds"],
                    "status": "COMPLETED",
                }
            )
            bundles_by_code[code] = bundle

            exp_rows.append(
                {
                    "experiment_id": exp_id,
                    "experiment_code": code,
                    "feature_groups": "+".join(groups),
                    "num_features": bundle["feature_schema"]["total_features"],
                    "cv_f1": bundle["cv_metrics"].get("f1"),
                    "cv_pr_auc": bundle["cv_metrics"].get("pr_auc"),
                    "cv_roc_auc": bundle["cv_metrics"].get("roc_auc"),
                    "test_accuracy": test_m.get("accuracy"),
                    "test_precision": test_m.get("precision"),
                    "test_recall": test_m.get("recall"),
                    "test_f1": test_m.get("f1"),
                    "test_specificity": test_m.get("specificity"),
                    "test_fpr": test_m.get("fpr"),
                    "test_fnr": test_m.get("fnr"),
                    "test_roc_auc": test_m.get("roc_auc"),
                    "test_pr_auc": test_m.get("pr_auc"),
                    "test_brier": test_m.get("brier_score"),
                    "test_uncertain_rate": test_m.get("uncertain_rate"),
                    "test_selective_f1": test_m.get("selective_f1"),
                    "hn_fpr": hn_m.get("fpr"),
                    "hn_uncertain_rate": hn_m.get("uncertain_rate"),
                    "hn_selective_fpr": hn_m.get("selective_fpr"),
                    "duration_s": bundle["duration_seconds"],
                }
            )

        # Select champion strictly by Development Nested CV PR-AUC/F1 among source-code configurations (F-I, preferring richer code models)
        source_codes = ["B", "C", "D", "E", "F", "G", "H", "I"]
        best_code = max(
            source_codes,
            key=lambda c: (
                bundles_by_code[c]["cv_metrics"].get("pr_auc") or 0.0,
                bundles_by_code[c]["cv_metrics"].get("f1") or 0.0,
            ),
        )
        champion_bundle = bundles_by_code[best_code]
        champ_version = f"rf_{best_code}_{dver}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        champion_bundle["model_version"] = champ_version

        # Leave-One-Group-Out Ablation from Full I
        all_groups = list(EXPERIMENT_DEFINITIONS["I"])
        ablation_rows: list[dict[str, Any]] = []
        full_i_test = bundles_by_code["I"]["independent_test_metrics"]
        for drop_g in all_groups:
            kept_g = [g for g in all_groups if g != drop_g]
            ab_bundle = train_random_forest_with_cv(
                dev_records=dev_recs,
                dataset_version=dver,
                dataset_sha256=ds_sha,
                experiment_code=f"I_minus_{drop_g}",
                feature_groups=kept_g,
                config=self.config,
                tune_hyperparameters=False,
                tune_calibration=False,
            )
            ab_test, _, _ = self._evaluate_bundle_on_split(ab_bundle, test_recs)
            ablation_rows.append(
                {
                    "ablated_group": drop_g,
                    "remaining_groups": "+".join(kept_g),
                    "cv_f1": ab_bundle["cv_metrics"].get("f1"),
                    "cv_pr_auc": ab_bundle["cv_metrics"].get("pr_auc"),
                    "test_f1": ab_test.get("f1"),
                    "test_pr_auc": ab_test.get("pr_auc"),
                    "test_roc_auc": ab_test.get("roc_auc"),
                    "delta_test_f1_vs_I": round((ab_test.get("f1") or 0.0) - (full_i_test.get("f1") or 0.0), 4),
                    "delta_test_pr_auc_vs_I": round((ab_test.get("pr_auc") or 0.0) - (full_i_test.get("pr_auc") or 0.0), 4),
                }
            )

        # Secondary baselines on champion feature groups
        baseline_rows: list[dict[str, Any]] = [
            {
                "algorithm": "RandomForestClassifier (Primary)",
                **champion_bundle["independent_test_metrics"],
                "duration_seconds": champion_bundle["duration_seconds"],
            }
        ]
        for alg in ["ExtraTreesClassifier", "HistGradientBoostingClassifier", "LogisticRegression"]:
            b_m = train_secondary_baseline(
                algorithm_name=alg,
                dev_records=dev_recs,
                test_records=test_recs,
                feature_groups=champion_bundle["feature_groups"],
                feature_cfg=self.config.features,
                random_state=self.config.validation.random_state,
            )
            baseline_rows.append(b_m)

        # Persist & activate champion model bundle
        artifact_path, manifest_path = save_model_bundle(
            model_version=champ_version,
            bundle=champion_bundle,
            config=self.config,
            activate=True,
        )

        # Detailed independent evaluation + source/bug-type breakdowns + FP/FN error analysis
        test_m, y_test, probs_test = self._evaluate_bundle_on_split(champion_bundle, test_recs)
        hn_m, y_hn, probs_hn = self._evaluate_bundle_on_split(champion_bundle, hn_recs)
        self.repo.save_evaluation_result(champ_version, "dev_nested_cv_oof", champion_bundle["cv_metrics"])
        self.repo.save_evaluation_result(champ_version, "independent_test", test_m)
        if hn_recs:
            self.repo.save_evaluation_result(champ_version, "hard_negative_test", hn_m)
        if champion_bundle.get("temporal_metrics"):
            self.repo.save_evaluation_result(champ_version, "temporal_test", champion_bundle["temporal_metrics"])

        # Breakdown by label_source on independent test set
        source_breakdown: dict[str, Any] = {}
        for lsrc in sorted({r["label_source"] for r in test_recs}):
            idx = [i for i, r in enumerate(test_recs) if r["label_source"] == lsrc]
            source_breakdown[lsrc] = compute_classification_metrics(
                y_true=y_test[idx],
                y_prob=probs_test[idx],
                threshold_low=champion_bundle["threshold_low"],
                threshold_center=champion_bundle["threshold_center"],
                threshold_high=champion_bundle["threshold_high"],
                repository_ids=[test_recs[i]["repository_id"] for i in idx],
            )

        # Independent test permutation importance & error analysis
        X_test_mat, _ = champion_bundle["feature_pipeline"].transform(test_recs)
        test_global_imp = compute_global_importances(
            estimator=champion_bundle["estimator"],
            X_eval=X_test_mat,
            y_eval=y_test,
            feature_names=champion_bundle["feature_pipeline"].get_feature_names(),
            group_map=champion_bundle["feature_pipeline"].get_feature_group_map(),
            n_repeats=5,
            random_state=self.config.validation.random_state,
        )
        error_analysis = analyze_false_positives_and_negatives(
            records=test_recs,
            y_true=y_test,
            y_prob=probs_test,
            threshold_center=champion_bundle["threshold_center"],
            limit=15,
        )

        exp_df = pd.DataFrame(exp_rows)
        ab_df = pd.DataFrame(ablation_rows)
        base_df = pd.DataFrame(
            [
                {
                    "algorithm": r["algorithm"],
                    "accuracy": r.get("accuracy"),
                    "precision": r.get("precision"),
                    "recall": r.get("recall"),
                    "f1": r.get("f1"),
                    "specificity": r.get("specificity"),
                    "fpr": r.get("fpr"),
                    "roc_auc": r.get("roc_auc"),
                    "pr_auc": r.get("pr_auc"),
                    "brier_score": r.get("brier_score"),
                    "duration_seconds": r.get("duration_seconds"),
                }
                for r in baseline_rows
            ]
        )

        exp_df.to_csv(out_dir / "experiments_a_to_i.csv", index=False)
        ab_df.to_csv(out_dir / "feature_ablation.csv", index=False)
        base_df.to_csv(out_dir / "baseline_comparison.csv", index=False)
        (out_dir / "error_analysis.json").write_text(json.dumps(error_analysis, indent=2) + "\n", encoding="utf-8")
        (out_dir / "global_importance_test.json").write_text(json.dumps(test_global_imp, indent=2) + "\n", encoding="utf-8")

        self._generate_plots(exp_df, champion_bundle, test_m, test_global_imp, out_dir)

        summary = {
            "dataset_version": dver,
            "dataset_sha256": ds_sha,
            "partition_counts": {
                "dev": {"samples": len(dev_recs), "repos": len({r["repository_id"] for r in dev_recs}), "bugs": sum(1 for r in dev_recs if r["label"] == 1)},
                "independent_test": {"samples": len(test_recs), "repos": len({r["repository_id"] for r in test_recs}), "bugs": sum(1 for r in test_recs if r["label"] == 1)},
                "hard_negative_test": {"samples": len(hn_recs), "repos": len({r["repository_id"] for r in hn_recs}), "bugs": sum(1 for r in hn_recs if r["label"] == 1)},
                "temporal_train": {"samples": len(t_train), "repos": len({r["repository_id"] for r in t_train})},
                "temporal_test": {"samples": len(t_test), "repos": len({r["repository_id"] for r in t_test})},
            },
            "selected_champion_experiment": best_code,
            "champion_model_version": champ_version,
            "artifact_path": str(artifact_path),
            "manifest_path": str(manifest_path),
            "champion_cv_metrics": champion_bundle["cv_metrics"],
            "champion_independent_test_metrics": test_m,
            "champion_hard_negative_metrics": hn_m,
            "champion_temporal_metrics": champion_bundle.get("temporal_metrics"),
            "independent_test_source_breakdown": source_breakdown,
            "experiments_a_to_i": exp_rows,
            "feature_ablation": ablation_rows,
            "baseline_comparison": base_df.to_dict(orient="records"),
        }
        (out_dir / "evaluation_summary_v5.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        logger.info(
            "Experiment suite complete. Champion=%s (%s) | Independent Test F1=%.4f, PR-AUC=%.4f, ROC-AUC=%.4f | Hard-Neg FPR=%s",
            champ_version,
            best_code,
            test_m.get("f1") or 0.0,
            test_m.get("pr_auc") or 0.0,
            test_m.get("roc_auc") or 0.0,
            hn_m.get("fpr"),
        )
        return summary
