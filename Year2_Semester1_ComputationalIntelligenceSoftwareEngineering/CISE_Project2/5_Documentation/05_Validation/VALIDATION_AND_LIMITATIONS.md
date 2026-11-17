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
| Model Deserialization | `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` | SHA-256 verified (`62599235...`); loads via `BugPredictor` |

---

## 2. Empirical Validation

### 2.1 Holdout Generalization (`JamesNK/Newtonsoft.Json`, $N = 159$)

| Evaluation | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | Confusion Matrix [TN, FP, FN, TP] |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| Nominal | 0.50 | 74.21% | 69.79% | 84.81% | 0.7657 | 0.8209 | 0.7917 | 0.1713 | `[51, 29, 12, 67]` |
| CV-Tuned | 0.40 | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.7917 | 0.1713 | `[49, 31, 8, 71]` |

### 2.2 Qualitative Prediction Cases (`Newtonsoft.Json`, $\tau = 0.50$)

| Quadrant | Method | Predicted Risk | Key Metrics | Analysis |
| :--- | :--- | ---: | :--- | :--- |
| True Positive | `CalculatePropertyDetails` | 0.9155 | `loc=78`, `cc=22`, `params=11`, `nesting=2` | High branching and parameter count; SZZ traced null-reference fix (`142f5cb0`). |
| True Positive | `ReadMetadataPropertiesToken` | 0.8870 | `loc=75`, `cc=17`, `statements=59`, `nesting=6` | Deep nesting (6 levels) and high statement density. |
| False Positive | `BsonReader.ReadString` | 0.8514 | `loc=54`, `cc=9`, `statements=35`, `nesting=4` | Complex binary stream parser with no recorded bug fix in the mined window. |
| False Negative | `JContainer.Values` | 0.1944 | `loc=11`, `cc=1`, `statements=1`, `nesting=0` | Single-statement generic wrapper; defect involved LINQ type covariance not captured by AST complexity. |
| False Negative | `JContainer.IsMultiContent` | 0.2279 | `loc=4`, `cc=1`, `statements=1`, `nesting=0` | Four-line method; static structural metrics cannot detect semantic type-contract defects in trivial methods. |

---

## 3. Methodological Limitations

| Limitation | Description and Impact |
| :--- | :--- |
| **Base-Rate Fallacy in Production** | Training and holdout datasets use ~1:1 class balancing (~48%–50% positive). In production codebases with 2%–10% defect prevalence, operational precision decreases substantially. At 5% prevalence, sensitivity $89.87\%$ and false positive rate $38.75\%$ ($1 - 49/80$) yield a Bayesian precision of $\frac{0.8987 \times 0.05}{0.8987 \times 0.05 + 0.3875 \times 0.95} \approx 10.88\%$. |
| **Heuristic SZZ Labels** | Positive labels rely on commit message patterns and `git blame` line tracing, which can misattribute changes from refactorings or tangled commits. |
| **Candidate-Clean Labels (OWA)** | Negative observations (`label = 0`) have no recorded bug fixes in the mined commit window but are not proven defect-free. |
| **Out-of-Fold Threshold Selection** | Threshold $\tau^* = 0.40$ was tuned on pooled out-of-fold CV predictions without nested CV, introducing mild selection optimism on CV metrics; generalization was subsequently checked on `Newtonsoft.Json`. |
| **Temporal Asymmetry** | Defect-prone methods are extracted from historical pre-fix revisions, whereas candidate-clean methods are sampled from `HEAD`. |
| **Absence of Human Study Data** | [DEVELOPER_STUDY_TEMPLATE.md](../07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md) is an unadministered research protocol template; no human participant ratings were collected. |
| **Generalization Scope** | Findings are bounded to the 6 evaluated open-source C# libraries and 26 static AST metrics. |
