"""Phase 4: Independent Real-World Holdout Validation Script.

Ingests, mines, and extracts production methods from JamesNK/Newtonsoft.Json
strictly AFTER the training models, hyperparameter configurations, and decision
thresholds from Phase 3 are frozen.

Performs:
1. Cloning and commit history extraction (up to 350 commits).
2. Bug-fixing commit detection (threshold 0.50).
3. SZZ line blame tracing with strict production-only filtering.
4. Method-level labeling and 1:1 balanced clean sampling.
5. Roslyn 26-metric extraction.
6. One-shot evaluation against the frozen rf_compact_regularized model at:
   - Nominal threshold tau = 0.50
   - In-training tuned threshold tau* = 0.40
7. Extraction of qualitative audit cases (TP, FP, FN, TN).
8. JSON artifact persistence to reports/holdout/newtonsoft_holdout_results.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.settings import get_settings
from repositories.commit_collector import CommitCollector
from repositories.repository_manager import RepositoryManager
from database.connection import Database
from database.repository import RepositoryDB
from services.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES
from services.dataset.feature_extractor import FeatureExtractor
from services.labeling.label_manager import LabelManager
from services.mining.bug_fix_detector import BugFixDetector
from services.mining.szz_analyzer import SZZAnalyzer
from ml.model_manager import ModelManager
from utils.logger import setup_logger
from utils.source_classifier import is_production_csharp_file

logger = setup_logger("holdout_validation")


def main() -> None:
    print("=" * 80)
    print("PHASE 4: INDEPENDENT HOLDOUT VALIDATION (JamesNK/Newtonsoft.Json)")
    print("=" * 80)
    start_time = time.time()
    settings = get_settings()
    settings.ensure_directories()
    db = Database(settings.storage.database_path)
    repo_db = RepositoryDB(db)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=repo_db)

    # -----------------------------------------------------------------
    # Step 1: Verify Frozen Model from Phase 3 Exists
    # -----------------------------------------------------------------
    model_dir = PROJECT_ROOT / "reports" / "experiments" / "final" / "model"
    model_files = list(model_dir.glob("*.joblib"))
    if not model_files:
        raise FileNotFoundError(f"No frozen model bundle found in {model_dir}. Run Phase 3 first!")

    model_path = model_files[0]
    print(f"Loading frozen Phase 3 model bundle: {model_path.name}")
    model_mgr = ModelManager(model_dir)
    bundle = model_mgr.load_model(model_path.stem)
    frozen_model = bundle["model"]
    frozen_preproc = bundle["preprocessor"]
    feature_names = bundle["feature_names"]
    frozen_params = bundle["parameters"]
    model_name = bundle.get("model_name", model_path.stem)
    print(f"Frozen Model Architecture: {model_name}")
    print(f"  Parameters: {frozen_params}")
    print(f"  Expected Features ({len(feature_names)}): {feature_names[:5]}...")

    # Load frozen threshold from Phase 3 results
    exp_results_path = PROJECT_ROOT / "reports" / "experiments" / "final" / "experiment_results.json"
    with open(exp_results_path, "r", encoding="utf-8") as f:
        exp_results = json.load(f)
    optimal_tau = float(exp_results.get("threshold_optimization", {}).get("optimal_threshold", 0.40))
    print(f"Frozen Thresholds: Nominal tau = 0.50, Tuned tau* = {optimal_tau:.2f}")

    # -----------------------------------------------------------------
    # Step 2: Ingest and Mine JamesNK/Newtonsoft.Json
    # -----------------------------------------------------------------
    repo_meta = {
        "full_name": "JamesNK/Newtonsoft.Json",
        "name": "Newtonsoft.Json",
        "owner": "JamesNK",
        "url": "https://github.com/JamesNK/Newtonsoft.Json.git",
        "description": "Json.NET is a popular high-performance JSON framework for .NET",
        "license": "MIT",
        "default_branch": "master",
        "stars": 11000,
        "status": "registered",
    }

    repo_id = repo_db.upsert_repository(repo_meta)
    print(f"\nRegistered Holdout Repository: ID #{repo_id} ({repo_meta['full_name']})")

    print(f"Cloning/updating repository from {repo_meta['url']} (branch: {repo_meta['default_branch']})...")
    clone_res = repo_mgr.clone_or_update(
        url=repo_meta["url"],
        owner=repo_meta["owner"],
        name=repo_meta["name"],
        default_branch=repo_meta["default_branch"],
    )
    local_path = Path(clone_res["local_path"])
    print(f"Local clone path: {local_path} (Status: {clone_res['status']})")

    # Mine commits
    max_commits = 350
    print(f"\nMining up to {max_commits} commits from history...")
    collector = CommitCollector(repo_db)
    commit_res = collector.extract_and_persist(repo_id, local_path, max_commits=max_commits)
    print(f"  -> Mined {commit_res['new_extracted']} new commits (total in repo: {commit_res['total_in_repo']})")

    # Detect bug-fixing commits
    print("\nRunning heuristic bug-fixing commit detection (threshold = 0.50)...")
    detector = BugFixDetector(repo_db, default_threshold=0.50)
    fix_res = detector.detect_in_repository(repo_id, threshold=0.50)
    print(f"  -> Detected {fix_res['classified_bug_fixes']} bug-fixing commits out of {fix_res['total_commits']} commits")

    # Run SZZ tracing
    print("\nRunning SZZ line blame tracing with production-only filtering...")
    szz_analyzer = SZZAnalyzer(repo_db)
    szz_res = szz_analyzer.run_repository_szz(repo_id, local_path)
    print(f"  -> Traced {szz_res['total_bic_traces']} BIC lines across {szz_res['unique_bug_inducing_commits']} unique BICs")

    # Method-level labeling
    print("\nExtracting SZZ-derived buggy methods (Label 1)...")
    label_mgr = LabelManager(repo_db)
    buggy_obs = label_mgr.create_observations_from_szz(repo_id, local_path)
    print(f"  -> Extracted {len(buggy_obs)} buggy method observations")

    # Sample matching candidate-clean methods from HEAD
    target_clean = len(buggy_obs)
    print(f"Sampling {target_clean} candidate-clean methods (Label 0) from stable HEAD...")
    clean_obs = label_mgr.sample_candidate_clean_methods(repo_id, local_path, target_count=target_clean)
    print(f"  -> Sampled {len(clean_obs)} clean method observations")

    # Extract Roslyn metrics
    print("\nExtracting Roslyn static metrics for holdout observations...")
    feat_extractor = FeatureExtractor(repo_db)
    feat_res = feat_extractor.batch_extract(repository_id=repo_id)
    print(f"  -> Features extracted: {feat_res['success']} succeeded, {feat_res['failed']} failed")

    # -----------------------------------------------------------------
    # Step 3: Fetch Extracted Observations & Assemble Feature Matrix
    # -----------------------------------------------------------------
    with db.session() as conn:
        obs_rows = conn.execute(
            """
            SELECT o.id as observation_id, o.commit_sha, o.file_path, o.class_name, o.method_name,
                   o.method_signature, o.label, o.evidence_category, o.source_code,
                   f.raw_metrics_json, f.loc, f.logical_loc, f.method_length, f.parameter_count,
                   f.local_variable_count, f.statement_count, f.return_count, f.cyclomatic_complexity,
                   f.max_nesting_depth, f.boolean_operator_count, f.logical_operator_count,
                   f.conditional_expression_count, f.if_count, f.switch_count, f.loop_count,
                   f.try_catch_count, f.throw_count, f.break_continue_count, f.method_call_count,
                   f.field_access_count, f.property_access_count, f.assignment_count,
                   f.object_creation_count, f.is_static, f.is_async, f.is_generic
            FROM observations o
            JOIN features f ON o.id = f.observation_id
            WHERE o.repository_id = :rid AND o.label IN (0, 1) AND f.status = 'success'
            ORDER BY o.id
            """,
            {"rid": repo_id}
        ).fetchall()

    holdout_df = pd.DataFrame([dict(r) for r in obs_rows])
    # Filter non-production just in case
    holdout_df = holdout_df[holdout_df["file_path"].apply(is_production_csharp_file)].reset_index(drop=True)
    # Deduplicate
    holdout_df = holdout_df.drop_duplicates(subset=["file_path", "method_signature", "source_code"]).reset_index(drop=True)

    n_holdout = len(holdout_df)
    n_buggy = int((holdout_df["label"] == 1).sum())
    n_clean = int((holdout_df["label"] == 0).sum())
    print(f"\nFinal Audited Holdout Dataset: {n_holdout} production observations")
    print(f"  Buggy (Label 1): {n_buggy} ({n_buggy/n_holdout*100:.2f}%)")
    print(f"  Clean (Label 0): {n_clean} ({n_clean/n_holdout*100:.2f}%)")

    # -----------------------------------------------------------------
    # Step 4: One-Shot Model Evaluation
    # -----------------------------------------------------------------
    X_holdout = holdout_df[DEFAULT_NUMERICAL_FEATURES].copy()
    y_holdout = holdout_df["label"].astype(int).values

    # Preprocess holdout features using frozen preprocessor
    X_holdout_proc = frozen_preproc.transform(X_holdout)

    # Predict probabilities using frozen model
    y_prob = frozen_model.predict_proba(X_holdout_proc)[:, 1]
    holdout_df["predicted_probability"] = y_prob

    # Evaluate at Nominal Threshold (tau = 0.50)
    y_pred_50 = (y_prob >= 0.50).astype(int)
    cm_50 = confusion_matrix(y_holdout, y_pred_50, labels=[0, 1]).tolist()
    acc_50 = float(accuracy_score(y_holdout, y_pred_50))
    prec_50 = float(precision_score(y_holdout, y_pred_50, zero_division=0))
    rec_50 = float(recall_score(y_holdout, y_pred_50, zero_division=0))
    f1_50 = float(f1_score(y_holdout, y_pred_50, zero_division=0))
    brier_50 = float(brier_score_loss(y_holdout, y_prob))
    auc_50 = float(roc_auc_score(y_holdout, y_prob))
    ap_50 = float(average_precision_score(y_holdout, y_prob))

    # Evaluate at Tuned Threshold (tau* = optimal_tau)
    y_pred_opt = (y_prob >= optimal_tau).astype(int)
    cm_opt = confusion_matrix(y_holdout, y_pred_opt, labels=[0, 1]).tolist()
    acc_opt = float(accuracy_score(y_holdout, y_pred_opt))
    prec_opt = float(precision_score(y_holdout, y_pred_opt, zero_division=0))
    rec_opt = float(recall_score(y_holdout, y_pred_opt, zero_division=0))
    f1_opt = float(f1_score(y_holdout, y_pred_opt, zero_division=0))

    holdout_df["pred_label_nominal"] = y_pred_50
    holdout_df["pred_label_tuned"] = y_pred_opt

    print("\n" + "=" * 80)
    print("INDEPENDENT HOLDOUT EVALUATION RESULTS")
    print("=" * 80)
    print(f"Nominal Threshold (tau = 0.50):")
    print(f"  Accuracy:  {acc_50:.4f}")
    print(f"  Precision: {prec_50:.4f}")
    print(f"  Recall:    {rec_50:.4f} ({cm_50[1][1]}/{n_buggy})")
    print(f"  F1-Score:  {f1_50:.4f}")
    print(f"  ROC-AUC:   {auc_50:.4f}")
    print(f"  PR-AUC:    {ap_50:.4f}")
    print(f"  Brier:     {brier_50:.4f}")
    print(f"  Confusion Matrix: TN={cm_50[0][0]}, FP={cm_50[0][1]}, FN={cm_50[1][0]}, TP={cm_50[1][1]}")

    print(f"\nCV-Tuned Threshold (tau* = {optimal_tau:.2f}):")
    print(f"  Accuracy:  {acc_opt:.4f}")
    print(f"  Precision: {prec_opt:.4f}")
    print(f"  Recall:    {rec_opt:.4f} ({cm_opt[1][1]}/{n_buggy})")
    print(f"  F1-Score:  {f1_opt:.4f}")
    print(f"  Confusion Matrix: TN={cm_opt[0][0]}, FP={cm_opt[0][1]}, FN={cm_opt[1][0]}, TP={cm_opt[1][1]}")

    # -----------------------------------------------------------------
    # Step 5: Qualitative Sample Audit
    # -----------------------------------------------------------------
    print("\n" + "=" * 80)
    print("QUALITATIVE PREDICTION SAMPLE AUDIT")
    print("=" * 80)

    # Classify cases at nominal threshold
    tp_cases = holdout_df[(holdout_df["label"] == 1) & (holdout_df["pred_label_nominal"] == 1)].sort_values(by="predicted_probability", ascending=False)
    fp_cases = holdout_df[(holdout_df["label"] == 0) & (holdout_df["pred_label_nominal"] == 1)].sort_values(by="predicted_probability", ascending=False)
    fn_cases = holdout_df[(holdout_df["label"] == 1) & (holdout_df["pred_label_nominal"] == 0)].sort_values(by="predicted_probability", ascending=True)
    tn_cases = holdout_df[(holdout_df["label"] == 0) & (holdout_df["pred_label_nominal"] == 0)].sort_values(by="predicted_probability", ascending=True)

    def extract_case_details(row: pd.Series) -> Dict[str, Any]:
        return {
            "observation_id": int(row["observation_id"]),
            "file_path": str(row["file_path"]),
            "class_name": str(row["class_name"]),
            "method_name": str(row["method_name"]),
            "method_signature": str(row["method_signature"]),
            "ground_truth_label": int(row["label"]),
            "predicted_probability": round(float(row["predicted_probability"]), 4),
            "evidence_category": str(row["evidence_category"]),
            "key_metrics": {
                "loc": int(row["loc"]),
                "logical_loc": int(row["logical_loc"]),
                "cyclomatic_complexity": int(row["cyclomatic_complexity"]),
                "max_nesting_depth": int(row["max_nesting_depth"]),
                "statement_count": int(row["statement_count"]),
                "parameter_count": int(row["parameter_count"]),
                "method_call_count": int(row["method_call_count"]),
                "try_catch_count": int(row["try_catch_count"]),
            },
        }

    audit_tp = [extract_case_details(r) for _, r in tp_cases.head(3).iterrows()]
    audit_fp = [extract_case_details(r) for _, r in fp_cases.head(3).iterrows()]
    audit_fn = [extract_case_details(r) for _, r in fn_cases.head(3).iterrows()]
    audit_tn = [extract_case_details(r) for _, r in tn_cases.head(3).iterrows()]

    print(f"Extracted {len(audit_tp)} True Positives, {len(audit_fp)} False Positives, {len(audit_fn)} False Negatives, {len(audit_tn)} True Negatives for manual audit.")

    # -----------------------------------------------------------------
    # Step 6: Save Results Artifact
    # -----------------------------------------------------------------
    total_elapsed = round(time.time() - start_time, 2)
    holdout_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "holdout_repository": {
            "id": repo_id,
            "full_name": repo_meta["full_name"],
            "url": repo_meta["url"],
            "license": repo_meta["license"],
            "default_branch": repo_meta["default_branch"],
            "local_path": str(local_path),
        },
        "mining_statistics": {
            "commits_requested": max_commits,
            "commits_mined": commit_res["new_extracted"] + commit_res["already_present"],
            "total_repo_commits": commit_res["total_in_repo"],
            "bug_fixing_commits": fix_res["classified_bug_fixes"],
            "szz_line_traces": szz_res["total_bic_traces"],
            "unique_bug_inducing_commits": szz_res["unique_bug_inducing_commits"],
            "total_production_observations": n_holdout,
            "buggy_methods": n_buggy,
            "clean_methods": n_clean,
        },
        "frozen_model": {
            "model_name": model_name,
            "algorithm": frozen_params.get("algorithm", "random_forest"),
            "parameters": frozen_params,
            "features_used": feature_names,
        },
        "metrics_at_nominal_threshold_0_50": {
            "threshold": 0.50,
            "accuracy": acc_50,
            "precision": prec_50,
            "recall": rec_50,
            "f1_score": f1_50,
            "roc_auc": auc_50,
            "pr_auc": ap_50,
            "brier_score": brier_50,
            "confusion_matrix": {
                "true_negatives": cm_50[0][0],
                "false_positives": cm_50[0][1],
                "false_negatives": cm_50[1][0],
                "true_positives": cm_50[1][1],
            },
        },
        "metrics_at_tuned_threshold": {
            "threshold": optimal_tau,
            "accuracy": acc_opt,
            "precision": prec_opt,
            "recall": rec_opt,
            "f1_score": f1_opt,
            "confusion_matrix": {
                "true_negatives": cm_opt[0][0],
                "false_positives": cm_opt[0][1],
                "false_negatives": cm_opt[1][0],
                "true_positives": cm_opt[1][1],
            },
        },
        "qualitative_audit_sample": {
            "true_positives": audit_tp,
            "false_positives": audit_fp,
            "false_negatives": audit_fn,
            "true_negatives": audit_tn,
        },
        "execution_duration_s": total_elapsed,
    }

    reports_dir = PROJECT_ROOT / "reports" / "holdout"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_file = reports_dir / "newtonsoft_holdout_results.json"
    out_file.write_text(json.dumps(holdout_payload, indent=2), encoding="utf-8")
    print(f"\nHoldout validation summary saved to: {out_file}")
    print(f"Phase 4 completed in {total_elapsed}s.")


if __name__ == "__main__":
    main()
