"""Phase 3: Final Multi-Model 5-Fold GroupKFold Cross-Validation Experiment.

Executes strict 5-fold repository-aware cross-validation across the 5 independent
training repositories in Dataset Snapshot #2 (csharp_empirical_v2_v2.0.0.csv):
1. Humanizr/Humanizer (291 obs)
2. serilog/serilog (134 obs)
3. LuckyPennySoftware/MediatR (91 obs)
4. App-vNext/Polly (34 obs)
5. FluentValidation/FluentValidation (28 obs)
Total: 578 production method observations.

Evaluates 11 configurations across 4 model families:
- DummyClassifier (most_frequent, stratified)
- LogisticRegression (standard, balanced)
- DecisionTreeClassifier (shallow_depth4, depth8)
- RandomForestClassifier (baseline, deep_capacity, compact_regularized, heavy_bagging, feature_constrained_log2)

Guarantees:
- Zero intra-repository leakage (GroupKFold with N_repos=5, K=5)
- Independent in-fold preprocessing and scaling
- Out-of-fold decision threshold tuning on CV predictions
- Probabilistic calibration evaluation (Brier score)
- Freezes best model and threshold for Phase 4 independent holdout evaluation.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES
from src.ml.experiment_runner import (
    DEFAULT_EXPERIMENT_GRID,
    ExperimentConfig,
    ExperimentRunner,
)
from src.utils.logger import setup_logger

logger = setup_logger("final_experiment")


def run_final_experiment() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 3: FINAL MULTI-MODEL 5-FOLD GROUPKFOLD EXPERIMENT")
    print("=" * 80)
    start_time = time.time()

    # 1. Load Dataset Snapshot #2
    csv_path = PROJECT_ROOT / "data" / "processed" / "csharp_empirical_v2_v2.0.0.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset Snapshot #2 not found at {csv_path}. Run Phase 2 first!")

    df = pd.read_csv(csv_path)
    print(f"Loaded Dataset Snapshot #2 from {csv_path}")
    print(f"  Shape: {df.shape[0]} rows, {df.shape[1]} columns")

    # 2. Extract Features, Target, and Group Metadata
    feature_cols = [c for c in DEFAULT_NUMERICAL_FEATURES if c in df.columns]
    assert len(feature_cols) == 26, f"Expected 26 Roslyn features, found {len(feature_cols)}"

    X = df[feature_cols].copy()
    y = df["label"].astype(int).copy()
    meta = df[["observation_id", "repository_id", "repository_name", "commit_sha", "file_path", "method_signature"]].copy()

    # Validate Repository Grouping
    repo_counts = meta["repository_name"].value_counts().to_dict()
    unique_repo_ids = meta["repository_id"].unique()
    n_repos = len(unique_repo_ids)
    print(f"\nTraining Repositories ({n_repos} distinct groups):")
    for rname, cnt in repo_counts.items():
        buggy_cnt = int(df[df["repository_name"] == rname]["label"].sum())
        clean_cnt = cnt - buggy_cnt
        print(f"  - {rname}: {cnt} obs (Buggy: {buggy_cnt}, Clean: {clean_cnt})")

    assert n_repos == 5, f"Expected exactly 5 repositories for 5-fold GroupKFold, found {n_repos}"

    # 3. Configure Experiment
    experiment_id = "exp_final_5fold_v2"
    exp_dir = PROJECT_ROOT / "reports" / "experiments" / experiment_id
    if exp_dir.exists():
        shutil.rmtree(exp_dir)

    exp_config = ExperimentConfig(
        experiment_id=experiment_id,
        description="Final 5-Fold GroupKFold Cross-Validation on Dataset Snapshot #2 (5 Repositories)",
        random_state=42,
        n_splits=5,
        strict_groups=True,
        group_col="repository_id",
        selection_metric="f1",
        param_grid=list(DEFAULT_EXPERIMENT_GRID),
        output_dir=PROJECT_ROOT / "reports" / "experiments",
        impute_missing=True,
        remove_constant=True,
    )

    runner = ExperimentRunner(exp_config)

    # 4. Execute Multi-Model Cross-Validation
    print(f"\nExecuting 5-Fold GroupKFold across {len(exp_config.param_grid)} configurations...")
    exp_summary = runner.run_experiment(
        X_train=X,
        y_train=y,
        meta_train=meta,
        X_holdout=None,  # Quarantined until Phase 4!
        y_holdout=None,
        meta_holdout=None,
        dataset_name="csharp_empirical_v2_v2.0.0",
    )

    # 5. Extract and Analyze Results
    print("\n" + "=" * 80)
    print("5-FOLD GROUPKFOLD CROSS-VALIDATION RESULTS")
    print("=" * 80)

    # Load generated JSON results for detailed inspection
    results_json_path = exp_dir / "experiment_results.json"
    with open(results_json_path, "r", encoding="utf-8") as f:
        results_data = json.load(f)

    ranked_configs = results_data["configurations"]
    print(f"\nConfiguration Rankings (Sorted by Mean CV F1):")
    print(f"{'Rank':<5} {'Config ID':<30} {'Algorithm':<20} {'F1 (mean±std)':<18} {'Recall':<12} {'Precision':<12} {'Brier':<10}")
    print("-" * 110)

    best_f1_cfg = ranked_configs[0]
    lowest_brier_cfg = min(
        [c for c in ranked_configs if "brier_score" in c["cv_results"].get("aggregate_metrics", {})],
        key=lambda c: c["cv_results"]["aggregate_metrics"]["brier_score"]["mean"],
    )

    for c in ranked_configs:
        m = c["cv_results"]["aggregate_metrics"]
        f1_str = f"{m['f1']['mean']:.4f} ± {m['f1']['std']:.4f}"
        rec_str = f"{m['recall']['mean']:.4f}"
        prec_str = f"{m['precision']['mean']:.4f}"
        brier_str = f"{m['brier_score']['mean']:.4f}" if "brier_score" in m else "N/A"
        print(f"{c['rank']:<5} {c['config_id']:<30} {c['algorithm']:<20} {f1_str:<18} {rec_str:<12} {prec_str:<12} {brier_str:<10}")

    print("\n" + "=" * 80)
    print("MODEL SELECTION & CALIBRATION ANALYSIS")
    print("=" * 80)
    best_m = best_f1_cfg["cv_results"]["aggregate_metrics"]
    lowest_b_m = lowest_brier_cfg["cv_results"]["aggregate_metrics"]
    print(f"Best F1 Model: '{best_f1_cfg['config_id']}' ({best_f1_cfg['algorithm']})")
    print(f"  CV F1: {best_m['f1']['mean']:.4f} ± {best_m['f1']['std']:.4f}")
    print(f"  CV Recall: {best_m['recall']['mean']:.4f} ± {best_m['recall']['std']:.4f}")
    print(f"  CV Precision: {best_m['precision']['mean']:.4f} ± {best_m['precision']['std']:.4f}")
    print(f"  CV Accuracy: {best_m['accuracy']['mean']:.4f} ± {best_m['accuracy']['std']:.4f}")
    print(f"  CV ROC-AUC: {best_m.get('roc_auc', {}).get('mean', 'N/A')}")
    print(f"  CV PR-AUC: {best_m.get('average_precision', {}).get('mean', 'N/A')}")
    print(f"  CV Brier Score: {best_m.get('brier_score', {}).get('mean', 'N/A')}")
    print(f"\nLowest Brier Score (Best Calibrated) Model: '{lowest_brier_cfg['config_id']}' ({lowest_brier_cfg['algorithm']})")
    print(f"  CV Brier Score: {lowest_b_m['brier_score']['mean']:.4f} ± {lowest_b_m['brier_score']['std']:.4f}")
    print(f"  CV F1: {lowest_b_m['f1']['mean']:.4f}")

    # Threshold Curve for Best Model
    print("\n" + "=" * 80)
    print(f"OUT-OF-FOLD THRESHOLD OPTIMIZATION (Model: {best_f1_cfg['config_id']})")
    print("=" * 80)
    th_info = results_data.get("threshold_optimization", {})
    opt_t = th_info.get("optimal_threshold", 0.50)
    curve = th_info.get("threshold_curve", [])

    print(f"Nominal Threshold (0.50):")
    nom_entry = next((e for e in curve if abs(e["threshold"] - 0.50) < 1e-4), None)
    if nom_entry:
        print(f"  Accuracy: {nom_entry['accuracy']:.4f}, Precision: {nom_entry['precision']:.4f}, Recall: {nom_entry['recall']:.4f}, F1: {nom_entry['f1']:.4f}")
        print(f"  Confusion Matrix: TN={nom_entry['true_negatives']}, FP={nom_entry['false_positives']}, FN={nom_entry['false_negatives']}, TP={nom_entry['true_positives']}")

    opt_entry = next((e for e in curve if abs(e["threshold"] - opt_t) < 1e-4), None)
    print(f"\nOptimized Out-of-Fold Threshold ({opt_t:.2f}):")
    if opt_entry:
        print(f"  Accuracy: {opt_entry['accuracy']:.4f}, Precision: {opt_entry['precision']:.4f}, Recall: {opt_entry['recall']:.4f}, F1: {opt_entry['f1']:.4f}")
        print(f"  Confusion Matrix: TN={opt_entry['true_negatives']}, FP={opt_entry['false_positives']}, FN={opt_entry['false_negatives']}, TP={opt_entry['true_positives']}")

    # 6. Copy Model to reports/experiments/final/model/
    final_dir = PROJECT_ROOT / "reports" / "experiments" / "final"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    shutil.copytree(exp_dir, final_dir)
    print(f"\nFinal experiment artifacts synced to: {final_dir}")

    total_time = round(time.time() - start_time, 2)
    print(f"Phase 3 completed in {total_time}s.")
    return results_data


if __name__ == "__main__":
    run_final_experiment()
