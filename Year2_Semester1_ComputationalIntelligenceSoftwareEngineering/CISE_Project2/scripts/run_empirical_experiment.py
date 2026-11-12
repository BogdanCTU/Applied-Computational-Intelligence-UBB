"""End-to-End Empirical Validation and Model Assessment Script for Phase 7.
Collects real C# repositories, mines commits, runs SZZ, extracts Roslyn metrics,
builds dataset snapshot, trains Random Forest model with zero repository leakage,
evaluates on holdout repositories, and performs error analysis.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from src.collection.github_client import GitHubClient
from src.collection.repository_manager import RepositoryManager
from src.collection.commit_collector import CommitCollector
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.dataset.exporter import DatasetExporter
from src.dataset.feature_extractor import FeatureExtractor
from src.labeling.label_manager import LabelManager
from src.mining.bug_fix_detector import BugFixDetector
from src.mining.szz_analyzer import SZZAnalyzer
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager
from src.ml.predictor import BugPredictor
from src.ml.preprocessing import DataPreprocessor, split_by_repository
from src.ml.trainer import ModelTrainer
from src.utils.logger import setup_logger

logger = setup_logger("empirical_experiment")


def main() -> None:
    print("=" * 80)
    print("PHASE 7: EMPIRICAL VALIDATION & MODEL ASSESSMENT")
    print("=" * 80)

    settings = get_settings()
    settings.ensure_directories()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)

    github_client = GitHubClient(token=settings.github.token)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=repo_db)
    commit_collector = CommitCollector(repo_db)
    fix_detector = BugFixDetector(repo_db)
    szz_analyzer = SZZAnalyzer(repo_db)
    label_mgr = LabelManager(repo_db)
    feat_extractor = FeatureExtractor(repo_db)
    dataset_builder = DatasetBuilder(repo_db)
    exporter = DatasetExporter(repo_db, settings.storage.exports_dir)
    model_mgr = ModelManager(settings.storage.models_dir, db=repo_db)

    target_repos = [
        ("commandlineparser", "commandline"),
        ("LuckyPennySoftware", "MediatR"),
        ("Humanizr", "Humanizer"),
    ]

    # -------------------------------------------------------------
    # Step 1: Repository Discovery & Full Git History Cloning
    # -------------------------------------------------------------
    print("\n--- STEP 1: Repository Discovery & Local Git Cloning ---")
    registered_repos = []
    for owner, name in target_repos:
        full_name = f"{owner}/{name}"
        print(f"Fetching metadata for '{full_name}'...")
        try:
            meta = github_client.get_repository(owner, name)
            repo_id = repo_db.upsert_repository(meta)
        except Exception as e:
            print(f"Warning: GitHub API error for {full_name}: {e}. Creating fallback registration.")
            repo_id = repo_db.upsert_repository({
                "full_name": full_name,
                "name": name,
                "owner": owner,
                "url": f"https://github.com/{full_name}.git",
                "default_branch": "master" if name == "commandline" else "main",
                "stars": 5000,
            })

        print(f"Cloning full history for '{full_name}' (ID #{repo_id})...")
        res = repo_mgr.clone_or_update(
            url=f"https://github.com/{full_name}.git",
            owner=owner,
            name=name,
            default_branch=meta.get("default_branch", "main"),
        )
        local_path = res["local_path"]
        print(f"  -> Path: {local_path} (Status: {res['status']})")
        registered_repos.append((repo_id, full_name, local_path))

    # -------------------------------------------------------------
    # Step 2: Commit History & Diff Extraction
    # -------------------------------------------------------------
    print("\n--- STEP 2: Commit History & File Diff Extraction ---")
    for repo_id, full_name, local_path in registered_repos:
        print(f"Collecting commits for '{full_name}'...")
        res = commit_collector.extract_and_persist(repo_id, local_path, max_commits=150)
        print(f"  -> Extracted {res['new_extracted']} new commits (already present: {res['already_present']}, total in repo: {res['total_in_repo']})")

    # -------------------------------------------------------------
    # Step 3: Bug-Fixing Commit Detection
    # -------------------------------------------------------------
    print("\n--- STEP 3: Bug-Fixing Commit Detection ---")
    all_bug_commits = []
    for repo_id, full_name, _ in registered_repos:
        print(f"Detecting bug fixes in '{full_name}'...")
        res = fix_detector.detect_in_repository(repo_id, threshold=0.50)
        print(f"  -> Analyzed {res['total_commits']} commits | Found {res['classified_bug_fixes']} bug-fixing commits")
        bug_commits = repo_db.list_commits(repository_id=repo_id, bug_fix_only=True)
        all_bug_commits.extend(bug_commits)

    print(f"Total candidate bug-fixing commits discovered across all repos: {len(all_bug_commits)}")

    # -------------------------------------------------------------
    # Step 4: SZZ Algorithm & Bug-Inducing Commit (BIC) Tracing
    # -------------------------------------------------------------
    print("\n--- STEP 4: SZZ Bug-Inducing Commit Analysis ---")
    total_szz_traces = 0
    for repo_id, full_name, local_path in registered_repos:
        print(f"Running SZZ analysis on '{full_name}'...")
        res = szz_analyzer.run_repository_szz(repo_id, local_path)
        print(f"  -> Analyzed {res['total_fixing_commits']} fixes | Found {res['unique_bug_inducing_commits']} BICs ({res['total_bic_traces']} traces)")
        total_szz_traces += res["total_bic_traces"]

    # -------------------------------------------------------------
    # Step 5: Method-Level Labeling (Pre-Fix Buggy vs Candidate Clean)
    # -------------------------------------------------------------
    print("\n--- STEP 5: Method-Level Observation Labeling ---")
    total_buggy_obs = 0
    total_clean_obs = 0
    for repo_id, full_name, local_path in registered_repos:
        print(f"Creating Label 1 (Buggy) observations for '{full_name}' from SZZ traces...")
        buggy_obs = label_mgr.create_observations_from_szz(repo_id, local_path)
        print(f"  -> Created {len(buggy_obs)} Label 1 observations")
        total_buggy_obs += len(buggy_obs)

        # Sample candidate clean methods to maintain balanced/realistic ratio
        target_clean = max(len(buggy_obs), 15)
        print(f"Sampling candidate clean methods (Label 0) for '{full_name}' (target: {target_clean})...")
        clean_obs = label_mgr.sample_candidate_clean_methods(repo_id, local_path, target_count=target_clean)
        print(f"  -> Sampled {len(clean_obs)} Label 0 candidate clean observations")
        total_clean_obs += len(clean_obs)

    print(f"\nLabeling Complete: {total_buggy_obs} Buggy (Label 1) vs {total_clean_obs} Candidate Clean (Label 0)")

    # -------------------------------------------------------------
    # Step 6: Roslyn Static Code Metric Extraction
    # -------------------------------------------------------------
    print("\n--- STEP 6: Roslyn Static Code Feature Extraction (24 Metrics) ---")
    needing = repo_db.get_observations_needing_features()
    print(f"Extracting Roslyn metrics for {len(needing)} observations...")
    extract_res = feat_extractor.batch_extract()
    print(f"  -> Extracted: {extract_res['success']} succeeded, {extract_res['failed']} failed.")

    # -------------------------------------------------------------
    # Step 7: Dataset Snapshot Generation & CSV Export
    # -------------------------------------------------------------
    print("\n--- STEP 7: Dataset Snapshot Generation & Serialization ---")
    ds_name = "csharp_empirical_v1"
    ds_version = "1.0.0"
    ds_id, ds_stats = dataset_builder.generate_dataset_snapshot(
        name=ds_name,
        version=ds_version,
        description="Empirical C# bug detection dataset across CommandLineParser, MediatR, and Humanizer.",
        exclude_uncertain=True,
    )
    print(f"Dataset snapshot #{ds_id} generated successfully!")
    print(f"  Total observations: {ds_stats['total_observations']}")
    print(f"  Buggy (1): {ds_stats['buggy_count']} | Clean (0): {ds_stats['clean_count']} | Uncertain: {ds_stats['uncertain_count']}")
    print(f"  Repository Distribution: {ds_stats['repository_distribution']}")

    exp_res = exporter.export_to_csv(ds_id, overwrite=True)
    csv_path = exp_res["csv_path"]
    json_path = exp_res["metadata_path"]
    print(f"Exported CSV: {csv_path}")
    print(f"Exported Metadata JSON: {json_path}")

    # -------------------------------------------------------------
    # Step 8: Machine Learning Pipeline - Zero-Leakage Split & Training
    # -------------------------------------------------------------
    print("\n--- STEP 8: ML Pipeline - Repository-Aware Partitioning & Training ---")
    X, y, metadata = dataset_builder.get_features_and_labels(ds_id)

    # Repository-aware split: strictly separates entire repositories
    X_train, X_test, y_train, y_test, meta_train, meta_test, split_summary = split_by_repository(
        X, y, metadata, test_size=0.33, random_state=42
    )

    print(f"Train Repositories: {split_summary['train_repositories']} ({split_summary['train_samples']} methods)")
    print(f"Holdout Test Repositories: {split_summary['test_repositories']} ({split_summary['test_samples']} methods)")
    print(f"Train Buggy: {split_summary['train_buggy_count']} | Clean: {split_summary['train_clean_count']}")
    print(f"Test Buggy: {split_summary['test_buggy_count']} | Clean: {split_summary['test_clean_count']}")

    # Fit preprocessor strictly on training data
    preprocessor = DataPreprocessor(impute_missing=True, remove_constant=True)
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc = preprocessor.transform(X_test)

    # Train Random Forest with GroupKFold CV on training repositories
    n_splits = min(len(split_summary["train_repositories"]), 5)
    trainer = ModelTrainer(
        n_estimators=100,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
    )
    model, cv_results, baseline_results, train_duration = trainer.train_with_cv(
        X_train=X_train_proc,
        y_train=y_train,
        meta_train=meta_train,
        n_splits=n_splits,
    )

    print(f"Model trained in {train_duration}s.")
    print(f"Cross-Validation Mean F1: {cv_results['f1']['mean']:.4f} +/- {cv_results['f1']['std']:.4f}")
    print(f"Cross-Validation Mean Accuracy: {cv_results['accuracy']['mean']:.4f} +/- {cv_results['accuracy']['std']:.4f}")
    print(f"Baseline Dummy Mean F1: {baseline_results['f1']['mean']:.4f}")
    print(f"Baseline Dummy Mean Accuracy: {baseline_results['accuracy']['mean']:.4f}")

    # -------------------------------------------------------------
    # Step 9: Final Evaluation on Untouched Holdout Test Set
    # -------------------------------------------------------------
    print("\n--- STEP 9: Holdout Test Set Evaluation & Feature Importance ---")
    eval_results = ModelEvaluator.evaluate(model, X_test_proc, y_test)

    print(f"Holdout Accuracy: {eval_results['accuracy']}")
    print(f"Holdout Precision: {eval_results['precision']}")
    print(f"Holdout Recall: {eval_results['recall']}")
    print(f"Holdout F1-Score: {eval_results['f1']}")
    print(f"Holdout ROC-AUC: {eval_results['roc_auc']}")
    print(f"Holdout Average Precision (PR-AUC): {eval_results['average_precision']}")
    print(f"Confusion Matrix [ [TN, FP], [FN, TP] ]: {eval_results['confusion_matrix']}")

    print("\nTop 5 Gini (MDI) Features:")
    for feat in eval_results["mdi_feature_importances"][:5]:
        print(f"  - {feat['feature']}: {feat['importance']:.4f}")

    print("\nTop 5 Permutation Features (Holdout Set):")
    for feat in eval_results["permutation_feature_importances"][:5]:
        print(f"  - {feat['feature']}: mean={feat['importance_mean']:.4f} (std={feat['importance_std']:.4f})")

    # Save model artifact
    saved_model_path = model_mgr.save_model(
        model_name="rf_csharp_empirical_model",
        model=model,
        preprocessor=preprocessor,
        feature_names=preprocessor.feature_names_out_,
        parameters=trainer.params,
        metrics=eval_results,
        dataset_id=ds_id,
        split_summary=split_summary,
        overwrite=True,
    )
    print(f"\nModel artifact saved to: {saved_model_path}")

    # -------------------------------------------------------------
    # Step 10: Error Analysis on Holdout Observations
    # -------------------------------------------------------------
    print("\n--- STEP 10: Error Analysis (False Positives & False Negatives) ---")
    y_test_pred = model.predict(X_test_proc)
    y_test_prob = model.predict_proba(X_test_proc)[:, 1]

    holdout_meta = meta_test.reset_index(drop=True)
    holdout_proc = X_test_proc.reset_index(drop=True)

    errors = []
    for i in range(len(y_test)):
        act = int(y_test.iloc[i])
        pred = int(y_test_pred[i])
        prob = float(y_test_prob[i])
        m_row = holdout_meta.iloc[i]
        f_row = holdout_proc.iloc[i]

        if act != pred:
            err_type = "False Positive" if (act == 0 and pred == 1) else "False Negative"
            errors.append({
                "type": err_type,
                "observation_id": int(m_row.get("observation_id", 0)),
                "repository": m_row.get("repository_name", "unknown"),
                "method_name": m_row.get("method_name", "unknown"),
                "actual": act,
                "predicted": pred,
                "risk_score": round(prob, 4),
                "loc": int(f_row.get("loc", 0)),
                "cyclomatic_complexity": int(f_row.get("cyclomatic_complexity", 0)),
                "max_nesting_depth": int(f_row.get("max_nesting_depth", 0)),
            })

    print(f"Total misclassifications on holdout test set: {len(errors)} / {len(y_test)}")
    for err in errors[:5]:
        print(f"  [{err['type']}] Method: {err['method_name']} | Repo: {err['repository']} | Actual: {err['actual']} | Pred: {err['predicted']} | Risk: {err['risk_score']} | CC: {err['cyclomatic_complexity']} | LOC: {err['loc']}")

    # -------------------------------------------------------------
    # Step 11: Real-Time Prediction Workflow Validation
    # -------------------------------------------------------------
    print("\n--- STEP 11: Real-Time Bug Prediction Validation on Unseen Code ---")
    predictor = BugPredictor(
        model_bundle=model_mgr.load_model("rf_csharp_empirical_model"),
        db=repo_db,
    )

    sample_test_csharp = """
    public bool ValidateConfiguration(string connectionString, int timeoutSeconds)
    {
        if (string.IsNullOrEmpty(connectionString))
        {
            throw new ArgumentNullException(nameof(connectionString));
        }
        if (timeoutSeconds <= 0)
        {
            return false;
        }
        for (int i = 0; i < 3; i++)
        {
            try
            {
                if (connectionString.Contains("Server=") && timeoutSeconds > 5)
                {
                    return true;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }
        }
        return false;
    }
    """
    preds = predictor.predict_code(sample_test_csharp, file_name="TestConfigValidator.cs")
    print(f"Predicted {len(preds)} methods:")
    for p in preds:
        print(f"  Method: {p.method_name} | Predicted: {p.predicted_label} | Risk: {p.risk_score} ({p.risk_category})")
        print(f"  Influential Metrics: {[m['feature'] for m in p.influential_metrics]}")

    print("\n" + "=" * 80)
    print("EMPIRICAL VALIDATION EXECUTION COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
