"""CLI script for running automated ML experiments on C# defect datasets."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config.settings import get_settings
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.ml.cross_validation import check_repository_readiness, InsufficientRepositoriesError
from src.ml.experiment_runner import ExperimentConfig, ExperimentRunner, DEFAULT_EXPERIMENT_GRID
from src.ml.preprocessing import split_by_repository
from src.utils.logger import setup_logger

logger = setup_logger("run_experiments")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated ML Experimentation Pipeline for C# Defect Prediction")
    parser.add_argument("--dataset-id", type=int, default=1, help="Database dataset ID to load (default: 1)")
    parser.add_argument("--csv-path", type=str, default=None, help="Direct CSV snapshot path (optional)")
    parser.add_argument("--n-splits", type=int, default=5, help="Number of GroupKFold splits (default: 5)")
    parser.add_argument("--strict-groups", action="store_true", help="Fail if repository count < n-splits")
    parser.add_argument("--metric", type=str, default="f1", help="Model selection metric (default: f1)")
    parser.add_argument("--test-size", type=float, default=0.25, help="Repository holdout ratio (default: 0.25)")
    parser.add_argument("--random-state", type=int, default=42, help="Random state seed (default: 42)")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_directories()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    builder = DatasetBuilder(repo_db)

    print("=" * 80)
    print("AUTOMATED MACHINE LEARNING EXPERIMENTATION PIPELINE")
    print("=" * 80)

    # 1. Load data
    csv_to_use = args.csv_path
    default_csv = PROJECT_ROOT / "exports" / "csharp_empirical_v1_v1.0.0.csv"
    if not csv_to_use and default_csv.exists():
        csv_to_use = str(default_csv)

    if csv_to_use and Path(csv_to_use).exists():
        print(f"Loading dataset from CSV: {csv_to_use}")
        df = pd.read_csv(csv_to_use)
        feature_cols = [c for c in df.columns if c not in [
            "observation_id", "repository_id", "repository_name", "commit_sha",
            "file_path", "class_name", "method_name", "method_signature", "label",
            "label_confidence", "evidence_category"
        ]]
        X = df[feature_cols]
        y = df["label"]
        metadata = df[["observation_id", "repository_id", "repository_name", "file_path", "method_name"]]
        dataset_name = Path(csv_to_use).stem
    else:
        print(f"Loading dataset ID #{args.dataset_id} from database...")
        X, y, metadata = builder.get_features_and_labels(args.dataset_id)
        dataset_meta = repo_db.get_dataset(args.dataset_id)
        dataset_name = dataset_meta.get("name", f"dataset_{args.dataset_id}") if dataset_meta else f"dataset_{args.dataset_id}"

    print(f"Loaded {len(X)} observations across {metadata['repository_id'].nunique()} repositories.")

    # 2. Split into Train and Independent Holdout
    X_train, X_holdout, y_train, y_holdout, meta_train, meta_holdout, split_sum = split_by_repository(
        X, y, metadata, test_size=args.test_size, random_state=args.random_state
    )

    print(f"\nRepository Partitioning (Zero-Leakage):")
    print(f"  Training Repositories: {split_sum['train_repo_count']} ({split_sum['train_samples']} methods)")
    print(f"  Holdout Repositories:  {split_sum['test_repo_count']} ({split_sum['test_samples']} methods)")

    # 3. Check Repository Readiness for requested n_splits
    readiness = check_repository_readiness(meta_train, n_splits=args.n_splits)
    print(f"\nCross-Validation Readiness Assessment:")
    print(f"  Available Training Repositories: {readiness.available_repo_count}")
    print(f"  Required Repositories for {args.n_splits}-fold: {readiness.required_repo_count}")
    print(f"  Missing Repositories:            {readiness.missing_repo_count}")
    print(f"  Diagnosis: {readiness.recommendation}")

    effective_splits = args.n_splits
    if not readiness.is_ready:
        if args.strict_groups:
            print("\n[ERROR] Aborting experiment: strict_groups flag is enabled and repository count is insufficient.")
            raise InsufficientRepositoriesError(readiness.recommendation)
        else:
            effective_splits = readiness.available_repo_count
            print(f"\n[NOTE] Automatically adapting cross-validation to {effective_splits}-fold GroupKFold based on available training repositories.")

    # 4. Configure Experiment
    exp_config = ExperimentConfig(
        description=f"Random Forest hyperparameter exploration ({len(DEFAULT_EXPERIMENT_GRID)} configs)",
        random_state=args.random_state,
        n_splits=effective_splits,
        strict_groups=args.strict_groups,
        selection_metric=args.metric,
        param_grid=DEFAULT_EXPERIMENT_GRID,
        output_dir=settings.storage.reports_dir / "experiments",
    )

    runner = ExperimentRunner(exp_config)
    results = runner.run_experiment(
        X_train=X_train,
        y_train=y_train,
        meta_train=meta_train,
        X_holdout=X_holdout,
        y_holdout=y_holdout,
        meta_holdout=meta_holdout,
        dataset_name=dataset_name,
    )

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Best Configuration:    {results['best_config_id']}")
    print(f"Best CV {args.metric.upper()}:          {results['best_cv_score']:.4f}")
    if results.get("optimal_threshold_info"):
        opt = results["optimal_threshold_info"]
        print(f"Optimal CV Threshold:  {opt.get('optimal_threshold', 0.50):.2f} (CV F1: {opt.get('cv_f1_at_optimal', 0.0):.4f})")
    if results["holdout_results"]:
        ho = results["holdout_results"]
        print(f"Holdout F1-Score:      {ho.get('f1', 0.0):.4f}")
        print(f"Holdout Recall:        {ho.get('recall', 0.0):.4f}")
        print(f"Holdout Precision:     {ho.get('precision', 0.0):.4f}")
        print(f"Holdout ROC-AUC:       {ho.get('roc_auc', 0.0):.4f}")
        print(f"Holdout Brier Score:   {ho.get('brier_score', 'N/A')}")
        if "holdout_at_optimal_cv_threshold" in ho:
            opt_ho = ho["holdout_at_optimal_cv_threshold"]
            print(f"Holdout F1 (at Opt T): {opt_ho.get('f1', 0.0):.4f}")
    print(f"Execution Duration:    {results['total_duration_s']}s")
    print(f"\nArtifacts Persisted:")
    print(f"  CSV Results:         {results['csv_path']}")
    print(f"  JSON Artifact:       {results['json_path']}")
    print(f"  Experiment Report:   {results['report_path']}")
    print(f"  Saved Model:         {results['saved_model_path']}")


if __name__ == "__main__":
    main()

