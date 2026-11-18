# Software Verification, Empirical Validation, and Methodological Limitations

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  

---

## 1. Software Verification

### 1.1 Automated Regression Test Suite

The test suite (`2_SourceCode/Tests/`) comprises 16 modules (123 tests) executed via `pytest`:

| Test Module | Tests | Scope |
| :--- | ---: | :--- |
| `test_bug_fix_detector.py` | 3 | Regex bug-fix scoring and manual overrides |
| `test_bug_predictor.py` | 7 | Method/file inference, risk categorization, and feature attribution |
| `test_commit_collector.py` | 2 | Git commit traversal and incremental persistence |
| `test_config.py` | 3 | Settings initialization and unpickle module aliases |
| `test_database.py` | 3 | SQLite schema, foreign keys, and CRUD transactions |
| `test_dataset_builder_and_exporter.py` | 3 | Feature matrix construction and CSV/JSON export |
| `test_experiment_runner.py` | 7 | 5-Fold `GroupKFold` partitioning and metric aggregation |
| `test_fluentvalidation_pilot.py` | 2 | Production source filtering on pilot repository |
| `test_github_client.py` | 6 | GitHub REST API search and rate-limit handling |
| `test_label_manager.py` | 3 | SZZ observation creation and candidate-clean sampling |
| `test_ml_pipeline.py` | 6 | Preprocessing, model training, and bundle serialization |
| `test_model_baselines.py` | 5 | Multi-model baseline comparisons |
| `test_repository_manager.py` | 3 | Git clone and update lifecycle |
| `test_roslyn_metrics.py` | 6 | .NET Roslyn AST metric calculation |
| `test_source_classifier.py` | 61 | Production vs. test C# file path filtering |
| `test_szz_analyzer.py` | 3 | `git blame` line attribution and BIC extraction |
| **Total** | **123** | **100% Pass Rate (offline execution with mocked network calls)** |

### 1.2 Roslyn Analyzer and Model Bundle Verification

| Check | Target | Result |
| :--- | :--- | :--- |
| .NET Build | `2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj` (`Release`) | 0 warnings, 0 errors |
| Line-Ending Normalization | `RoslynClient.extract_methods` (`\r\n` $\to$ `\n`) | Consistent spans across Windows, macOS, and Linux |
| Preserved Baseline Models | `exp_final_5fold_v2_best_rf_compact_regularized.joblib`, `rf_csharp_empirical_model.joblib` | SHA-256 checksums unchanged; loadable via `BugPredictor` |
| Optimized Versioned Models | `et_nested_opt_v3_depth6_leaf6_log2.joblib`, `rf_nested_opt_v3_depth6_leaf8_log2.joblib` | Verified in `ModelManager`, `BugPredictor`, and Streamlit UI |

---

## 2. Empirical Validation and Error Analysis

### 2.1 Nested Cross-Validation on Dataset #2 ($N = 578$, 5 Repositories)

| Model | Outer ROC-AUC | Outer PR-AUC | Outer Brier | Nested $\tau_{\text{inner}}^*$ F1 | Pooled OOF F1 ($\tau_{\text{inner}}^*$) | Pooled OOF Recall ($\tau_{\text{inner}}^*$) | Pooled OOF Precision ($\tau_{\text{inner}}^*$) | Pooled Confusion Matrix [TN, FP, FN, TP] |
| :--- | :---: | :---: | :---: | :---: | ---: | ---: | ---: | :---: |
| Baseline RF (`rf_compact_regularized`) | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 | 0.7408 ± 0.0760 | 0.7294 | 88.89% | 61.85% | `[146, 153, 31, 248]` |
| Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | 0.7216 ± 0.1156 | 0.6465 ± 0.1026 | 0.2055 ± 0.0374 | 0.7539 ± 0.0706 | 0.7406 | 88.53% | 63.66% | `[158, 141, 32, 247]` |
| Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) | 0.7349 ± 0.0703 | 0.6443 ± 0.0496 | 0.2062 ± 0.0213 | 0.7667 ± 0.0723 | 0.7653 | 91.76% | 65.64% | `[165, 134, 23, 256]` |

### 2.2 Error Analysis on Dataset #2 (`3_TestResults/ModelOptimization/error_analysis.csv`)

For `et_nested_opt_v3_depth6_leaf6_log2` under nested threshold evaluation ($N = 578$):

| Quadrant | Count | Median `loc` (Mean) | Median `logical_loc` (Mean) | Median `cc` (Mean) | Median `nesting` (Mean) | Structural Interpretation |
| :--- | ---: | :---: | :---: | :---: | :---: | :--- |
| True Positive (TP) | 256 | 18.5 (30.33) | 7.0 (12.67) | 2.0 (4.74) | 1.0 (1.17) | Multi-statement methods with elevated branching and call density |
| True Negative (TN) | 165 | 3.0 (4.06) | 1.0 (1.12) | 1.0 (1.02) | 0.0 (0.02) | Short 1-statement methods and property helpers |
| False Positive (FP) | 134 | 15.0 (18.26) | 5.0 (8.07) | 2.0 (3.43) | 1.0 (0.87) | Candidate-clean methods with elevated structural complexity (27 have `cc >= 6` or `loc >= 35`) |
| False Negative (FN) | 23 | 5.0 (6.74) | 1.0 (1.13) | 1.0 (1.17) | 0.0 (0.04) | Short methods (18/23 have `loc <= 12` and `cc <= 2`) where defects are semantic rather than structural |

### 2.3 Historical Baseline Holdout (`JamesNK/Newtonsoft.Json`, $N = 159$)

The historical holdout evaluation was executed once for the original baseline RF (`rf_compact_regularized`) prior to the optimization experiment:

| Evaluation | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | Confusion Matrix [TN, FP, FN, TP] |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| Baseline RF Nominal | 0.50 | 74.21% | 69.79% | 84.81% | 0.7657 | 0.8209 | 0.7917 | 0.1713 | `[51, 29, 12, 67]` |
| Baseline RF Unnested CV-Tuned | 0.40 | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.7917 | 0.1713 | `[49, 31, 8, 71]` |

`Newtonsoft.Json` was not used during the nested optimization experiment. These holdout metrics apply only to the historical baseline model, not to the newly optimized models.

---

## 3. Methodological Limitations

| Limitation | Description and Impact |
| :--- | :--- |
| **Small Repository Count and Size Imbalance** | Only 5 repositories were used for training and nested cross-validation (`N = 578`). `Humanizer` accounts for 50.35% of observations (291/578), whereas `Polly` (34) and `FluentValidation` (28) represent 10.73% combined. |
| **No New External Holdout for Optimized Models** | Because `Newtonsoft.Json` was previously examined for the baseline model, it was excluded from optimization. Evaluating external generalization of `et_nested_opt_v3_depth6_leaf6_log2` and `rf_nested_opt_v3_depth6_leaf8_log2` requires mining a new unseen repository. |
| **Static Metric Boundary on Semantic Defects** | Static AST metrics measure syntactic structure and cannot detect single-line semantic, literal, or type-contract bugs (`18/23` false negatives in Dataset #2 have `loc <= 12` and `cc <= 2`). |
| **Candidate-Clean Labels (Open-World Assumption)** | Negative observations (`label = 0`) have no recorded bug fixes in the mined commit window but are not confirmed defect-free. Complex candidate-clean methods flagged as false positives may harbor latent defects or maintenance risk. |
| **Heuristic SZZ Labels and Temporal Difference** | Positive labels (`label = 1`) rely on commit message patterns and `git blame` tracing on historical pre-fix commits, whereas candidate-clean observations (`label = 0`) are sampled from contemporary `HEAD` revisions. |
| **Base-Rate Fallacy in Production** | Training and holdout sets use ~1:1 class balancing (~48%–50% positive). In production repositories with 2%–10% defect prevalence, operational precision decreases substantially (e.g., at 5% prevalence, sensitivity $89.87\%$ and false positive rate $38.75\%$ yield a Bayesian precision of $\approx 10.88\%$). |
| **Deployment Threshold Alignment** | Nested cross-validation selects fold-specific inner thresholds ($\tau_{\text{inner}}^* \in \{0.35, 0.40\}$ for Extra Trees), whereas `BugPredictor.predict_from_metrics()` computes binary `predicted_label` via `model.predict()` ($\tau = 0.50$) and maps probabilities to Low ($\le 0.30$), Medium ($0.31\text{--}0.60$), and High ($> 0.60$) risk bands. |
| **Absence of Human Study Data** | [DEVELOPER_STUDY_TEMPLATE.md](../07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md) is an unadministered research protocol template; no human participant ratings were collected. |
| **Generalization Scope** | Nested cross-validation metrics are empirical estimates on the 5 C# repositories in Dataset #2 and do not establish universal generalization across all C# codebases. |
