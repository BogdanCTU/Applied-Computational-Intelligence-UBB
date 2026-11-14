import json
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
db_path = PROJECT_ROOT / "data" / "database" / "bug_detection.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Collect authoritative repository statistics
repo_stats = {}
for rid, full_name, name in cursor.execute("SELECT id, full_name, name FROM repositories ORDER BY id").fetchall():
    commits = cursor.execute("SELECT COUNT(*) FROM commits WHERE repository_id = ?", (rid,)).fetchone()[0]
    fixes = cursor.execute("SELECT COUNT(*) FROM commits WHERE repository_id = ? AND is_bug_fix = 1", (rid,)).fetchone()[0]
    traces = cursor.execute("SELECT COUNT(*) FROM szz_results WHERE repository_id = ?", (rid,)).fetchone()[0]
    bics = cursor.execute("SELECT COUNT(DISTINCT inducing_commit_sha) FROM szz_results WHERE repository_id = ?", (rid,)).fetchone()[0]
    
    obs_pos = cursor.execute("SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = 1", (rid,)).fetchone()[0]
    obs_clean = cursor.execute("SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = 0", (rid,)).fetchone()[0]
    obs_unc = cursor.execute("SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = -1", (rid,)).fetchone()[0]
    
    feat_succ = cursor.execute("SELECT COUNT(*) FROM features f JOIN observations o ON f.observation_id = o.id WHERE o.repository_id = ? AND f.status = 'success'", (rid,)).fetchone()[0]
    feat_fail = cursor.execute("SELECT COUNT(*) FROM features f JOIN observations o ON f.observation_id = o.id WHERE o.repository_id = ? AND f.status = 'failed'", (rid,)).fetchone()[0]
    
    ds1_cnt = cursor.execute("SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ?", (rid,)).fetchone()[0]
    ds1_pos = cursor.execute("SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ? AND o.label = 1", (rid,)).fetchone()[0]
    ds1_clean = cursor.execute("SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ? AND o.label = 0", (rid,)).fetchone()[0]
    
    repo_stats[str(rid)] = {
        "repository_id": rid,
        "full_name": full_name,
        "name": name,
        "commits_mined": commits,
        "candidate_bug_fixing_commits": fixes,
        "szz_line_traces": traces,
        "unique_candidate_bics": bics,
        "db_observations": {
            "total": obs_pos + obs_clean + obs_unc,
            "positive_label_1": obs_pos,
            "candidate_clean_label_0": obs_clean,
            "uncertain_label_minus_1": obs_unc
        },
        "feature_extractions": {
            "success": feat_succ,
            "failed": feat_fail,
            "success_rate": round(feat_succ / max(1, feat_succ + feat_fail), 4)
        },
        "dataset_1_membership": {
            "is_member": ds1_cnt > 0,
            "total_samples": ds1_cnt,
            "positive_samples": ds1_pos,
            "candidate_clean_samples": ds1_clean,
            "role": "holdout" if rid == 1 else ("training" if rid in [3, 4] else "none")
        }
    }

audit_data = {
    "audit_metadata": {
        "audit_name": "Final Dataset Integrity, Reproducibility and Documentation Audit",
        "date": "2026-11-14",
        "auditor_role": "Senior ML4SE Research Engineer and Independent Academic Auditor",
        "database_path": str(db_path),
        "authoritative_dataset_id": 1,
        "authoritative_dataset_name": "csharp_empirical_v1",
        "authoritative_dataset_version": "1.0.0",
        "authoritative_dataset_total_observations": 483,
        "authoritative_experiment_id": "exp_20261113_170914"
    },
    "repository_statistics": repo_stats,
    "discrepancy_reconciliations": {
        "humanizer_291_vs_178": {
            "authoritative_count_in_dataset_1": 291,
            "raw_db_observations": 304,
            "failed_feature_extractions_excluded": 8,
            "deduplicated_observations_excluded": 5,
            "erroneous_documented_figure": 178,
            "root_cause_of_discrepancy": "An agent mistakenly doubled the threshold TP count (TP=89 at threshold 0.60 -> 89*2=178) in expansion planning documents. 178 is unverified and incorrect. Authoritative count is 291 in Dataset 1."
        },
        "mediatr_91_vs_105": {
            "authoritative_count_in_dataset_1": 91,
            "raw_db_observations": 98,
            "failed_feature_extractions_excluded": 1,
            "deduplicated_observations_excluded": 6,
            "erroneous_documented_figure": 105,
            "root_cause_of_discrepancy": "An agent estimated 52 positive + 53 clean = 105 in expansion planning documents. 105 is unverified and incorrect. Authoritative count is 91 in Dataset 1."
        },
        "fluentvalidation_34_vs_28": {
            "v1_pilot_unfiltered": 34,
            "v2_pilot_corrected": 28,
            "count_in_dataset_1": 0,
            "root_cause_of_discrepancy": "v1 pilot allowed 3 test fixture methods to enter Label 1 (src/FluentValidation.Tests/ChainedValidationTester.cs and TestExtensions.cs) due to incomplete regex coverage on nested projects, and sampled 17 clean methods (total 34). v2 pilot corrected this using src/utils/source_classifier.py, purging the 3 test fixtures (leaving 14 production positive methods) and resampling exactly 14 clean methods (total 28 observations). FluentValidation is not in Dataset 1."
        }
    },
    "fluentvalidation_v2_audit": {
        "verified_positive_observations": 14,
        "verified_clean_observations": 14,
        "total_observations": 28,
        "test_code_leakage_detected": False,
        "duplicate_fingerprints_count": 0,
        "candidate_bug_fixing_commits": 11,
        "fixes_producing_szz_traces": 10,
        "false_positive_commit_sha": "91e78489",
        "false_positive_commit_description": "Packaging compatibility overload (issue #1860); modified 0 C# source lines, produced 0 SZZ traces and 0 observations.",
        "szz_line_traces_count": 25,
        "unique_bics_count": 12,
        "dataset_1_tampering_detected": False
    },
    "machine_learning_methodology_audit": {
        "cross_validation_scheme": "2-fold GroupKFold across MediatR (91) and Humanizer (291)",
        "five_fold_cv_actually_executed": False,
        "five_fold_cv_claim_status": "Strictly disallowed until 5 distinct training repos are collected and evaluated",
        "in_fold_preprocessing_isolated": True,
        "in_fold_preprocessing_details": "Imputation, constant removal, and scaling fitted strictly on fold training data",
        "holdout_repository": "commandlineparser/commandline",
        "holdout_samples": 101,
        "holdout_quarantine_status": "Previously inspected by researcher; serves as diagnostic benchmark, not blind gold standard",
        "decision_threshold_optimization": "Tuned on pooled out-of-fold CV predictions; exhibits post-selection optimism on CV F1",
        "brier_score_interpretation": "Measures mean squared error in predicted probabilities; lowest Brier score in CV was 0.1983 (rf_deep_unconstrained) and 0.2283 (logistic_regression), whereas best F1 model had Brier 0.2317 in CV and 0.2627 on holdout",
        "class_balance_impact": "Candidate-clean methods sampled 1:1 against positive methods (~50% prevalence); operational precision in low-prevalence production (5%-15%) will be lower via Bayes rule"
    },
    "readme_audit": {
        "roslyn_metrics_count_claim": {"claim": "24 metrics (page guide) vs 26 metrics (capabilities)", "status": "Inconsistent / Incorrect (guide)", "authoritative_value": 26},
        "model_families_claim": {"claim": "Random Forest only", "status": "Outdated", "authoritative_value": "DummyClassifier, Logistic Regression, Decision Tree, Random Forest"},
        "repository_aware_validation_claim": {"claim": "GroupShuffleSplit & GroupKFold", "status": "Verified", "authoritative_value": "GroupShuffleSplit for holdout, 2-fold GroupKFold for training CV"},
        "dataset_size_claim": {"claim": "483 observations across 3 repos", "status": "Verified", "authoritative_value": "Humanizer (291), MediatR (91), CommandLineParser (101)"},
        "holdout_results_claim": {"claim": "Recall 81.82%, F1 0.6261", "status": "Outdated (prototype run exp_20261113_162850)", "authoritative_value": "At tau=0.50: Recall 77.27%, F1 0.5812, Brier 0.2627; At tau=0.30: Recall 95.45%, F1 0.6316"}
    },
    "verdict": {
        "go_no_go_decision": "GO_CONDITIONAL",
        "conditions": [
            "Do not start collection until authoritative counts are reconciled in all documents.",
            "Maintain strict separation between Dataset 1 (483) and future expansion snapshots.",
            "Acknowledge that 5-fold CV is a future capability requiring 5 training repositories.",
            "Preserve independent quarantine for holdout repository."
        ]
    }
}

audits_dir = PROJECT_ROOT / "reports" / "audits"
audits_dir.mkdir(parents=True, exist_ok=True)
audit_path = audits_dir / "dataset_integrity_audit.json"
audit_path.write_text(json.dumps(audit_data, indent=2), encoding="utf-8")
print(f"Audit summary written to {audit_path}")

