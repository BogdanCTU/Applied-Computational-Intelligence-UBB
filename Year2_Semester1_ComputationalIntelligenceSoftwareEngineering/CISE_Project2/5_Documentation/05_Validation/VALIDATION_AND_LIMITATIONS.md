# Software Verification, Empirical Validation & Methodological Limitations

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Role:** Canonical Verification, Validation & Academic Limitations Reference  

---

## 1. Distinction Between Verification and Validation

In rigorous software engineering and machine learning research, software verification and empirical validation address distinct scientific questions:

- **Software Verification ("Is the software built correctly?"):** Verifies that the implementation executes deterministically according to architectural specifications, passes regression unit/integration suites, builds without compiler errors, preserves data schemas, and handles inference edge-cases.
- **Empirical Validation ("Does the model generalize to real-world software?"):** Evaluates whether learned statistical associations generalize to unseen production codebases, measures out-of-domain discrimination, tests probability calibration, and analyzes failure modes on real code.

---

## 2. Software Verification & Engineering Integrity

### 2.1 Automated Test Suite Execution
The automated test suite (`2_SourceCode/Tests/`) is implemented using `pytest` and verifies every system component:

```
2_SourceCode/Tests/test_bug_fix_detector.py              ... [PASS]
2_SourceCode/Tests/test_bug_predictor.py                 ....... [PASS]
2_SourceCode/Tests/test_commit_collector.py              .. [PASS]
2_SourceCode/Tests/test_config.py                        ... [PASS]
2_SourceCode/Tests/test_database.py                      ... [PASS]
2_SourceCode/Tests/test_dataset_builder_and_exporter.py  ... [PASS]
2_SourceCode/Tests/test_experiment_runner.py             ....... [PASS]
2_SourceCode/Tests/test_fluentvalidation_pilot.py        .. [PASS]
2_SourceCode/Tests/test_github_client.py                 ...... [PASS]
2_SourceCode/Tests/test_label_manager.py                 ... [PASS]
2_SourceCode/Tests/test_ml_pipeline.py                   ...... [PASS]
2_SourceCode/Tests/test_model_baselines.py               ..... [PASS]
2_SourceCode/Tests/test_repository_manager.py            ... [PASS]
2_SourceCode/Tests/test_roslyn_metrics.py                ...... [PASS]
2_SourceCode/Tests/test_source_classifier.py             ............................................................. [PASS]
2_SourceCode/Tests/test_szz_analyzer.py                  ... [PASS]

============================== 123 passed in 31.38s ==============================
```

- **Total Test Cases:** Exactly **123 automated tests**.
- **Exit Code:** `0` (100% passing rate).
- **Execution Mode:** Offline and deterministic; network and external APIs are mocked via `pytest-mock`.

### 2.2 Microsoft Roslyn Compiler Platform Build Verification
The static code metric extraction engine is built on Microsoft Roslyn (`Microsoft.CodeAnalysis.CSharp`, .NET 9.0 SDK):
- **Project Location:** `2_SourceCode/RoslynAnalyzer/`
- **Compiler Platform:** .NET 9.0 (`net9.0`)
- **Compilation Status:** `dotnet build --configuration Release` completes with **0 errors and 0 warnings**.
- **Cross-Platform Compatibility:** Source text is normalized (`\r\n` $\to$ `\n`) before syntax tree generation, ensuring identical character and line metrics across Windows, macOS, and Linux.

### 2.3 Model Loading & Inference Smoke Tests
The serialized winning model bundle was audited via automated runtime assertions:
- **Bundle File:** `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` (SHA-256: `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e`).
- **Deserialization Integrity:** Loads cleanly via `BugPredictor.from_model_identifier()`.
- **Standalone Snippet Ingestion:** Correctly wraps bare method snippets inside `class __DummyContainer__ { ... }` to construct valid syntax trees.
- **Preprocessor Schema Alignment:** Missing input metrics are median-imputed; constant features dropped during training are filtered out before being passed to `model.predict_proba()`.

---

## 3. Empirical Machine Learning Validation

### 3.1 Independent Real-World Holdout (`JamesNK/Newtonsoft.Json`)
To evaluate true generalization to an external codebase, `JamesNK/Newtonsoft.Json` (Repo #17, 11,000 GitHub stars) was maintained as an independent holdout repository evaluated after training models, preprocessing pipelines, and decision thresholds were frozen, as documented by dated artifacts.

Evaluating the frozen model on **159 production methods** (79 SZZ-derived defect-prone, 80 candidate-clean from stable HEAD) yielded:
- **Nominal Threshold ($\tau = 0.50$):**
  - Accuracy: **74.21%** (118/159)
  - Precision: **69.79%** (67/96)
  - Recall: **84.81%** (67/79 defects caught)
  - F1-Score: **0.7657**
  - ROC-AUC: **0.8209** | PR-AUC: **0.7917** | Brier Score: **0.1713**
- **CV-Tuned Threshold ($\tau^* = 0.40$):**
  - Accuracy: **75.47%** (120/159)
  - Precision: **69.61%** (71/102)
  - Recall: **89.87%** (71/79 defects caught)
  - F1-Score: **0.7845**

The holdout results confirm that the 5-fold cross-validation estimates ($F_1 = 0.6859, \text{AUC} = 0.7025$) were conservative. The model successfully generalized to an entirely unseen, industrial-grade library without intra-repository data leakage.

### 3.2 Qualitative Prediction Sample Analysis
To understand model decision boundaries and failure modes, representative cases from `Newtonsoft.Json` were audited:

#### True Positives (High-Complexity Orchestrators)
- **`CalculatePropertyDetails`** ($P(\text{defect-prone}) = 0.9155$): $\text{LOC} = 78, \text{Complexity} = 22, \text{Parameters} = 11, \text{Nesting} = 2$. Coordinates property deserialization across 11 arguments and 22 branching paths. SZZ traced a critical null-reference regression directly to this method (fixed in commit `142f5cb0`).
- **`ReadMetadataPropertiesToken`** ($P(\text{defect-prone}) = 0.8870$): $\text{LOC} = 75, \text{Complexity} = 17, \text{Statements} = 59, \text{Nesting} = 6$. Extreme nesting and high statement density accurately triggered high risk flags.

#### False Positives (Defensively Programmed Parsers)
- **`BsonReader.ReadString`** ($P(\text{defect-prone}) = 0.8514$): $\text{LOC} = 54, \text{Complexity} = 9, \text{Statements} = 35, \text{Nesting} = 4$. Low-level binary buffer parsing with extensive boundary checks. While clean in Git history, its procedural density matches defect-prone profiles; flagging it provides maintainability value.

#### False Negatives (Concise Semantic Flaws)
- **`JContainer.Values`** ($P(\text{defect-prone}) = 0.1944$): $\text{LOC} = 11, \text{Complexity} = 1, \text{Statements} = 1$.
- **`JContainer.IsMultiContent`** ($P(\text{defect-prone}) = 0.2279$): $\text{LOC} = 4, \text{Complexity} = 1, \text{Statements} = 1$.
- **Fundamental Theoretical Insight:** Both methods are 1-statement generic wrappers. The historical defects recorded in Git were subtle LINQ type-covariance mismatches. Because static AST metrics capture syntactic complexity rather than semantic type systems or runtime contracts, the model cannot detect defects in a 4-line method with cyclomatic complexity of 1.

---

## 4. Academic & Methodological Limitations

### 4.1 Balanced Dataset Benchmark vs. Operational Precision (Base-Rate Fallacy)
- **Dataset Context:** Training and holdout datasets were sampled at an approximate **1:1 class ratio** (~48%–50% defect-prone) to prevent machine learning estimators from collapsing into trivial majority predictors.
- **Production Reality:** In industrial production repositories, the natural defect prevalence of C# methods is typically **$2\%\text{--}10\%$** (severe class imbalance).
- **Illustrative Bayesian Scenario:**
  Using the holdout sensitivity ($71/79 \approx 89.87\%$) and specificity ($49/80 = 61.25\%$, giving False Positive Rate $= 1 - 0.6125 = 38.75\%$), we calculate the expected operational precision at a hypothetical **5% defect prevalence** using Bayes' theorem:
  $$P(\text{Bug} \mid \text{Alert}) = \frac{P(\text{Alert} \mid \text{Bug}) \cdot P(\text{Bug})}{P(\text{Alert} \mid \text{Bug}) \cdot P(\text{Bug}) + P(\text{Alert} \mid \text{Clean}) \cdot P(\text{Clean})}$$
  $$P(\text{Bug} \mid \text{Alert}) = \frac{0.8987 \times 0.05}{0.8987 \times 0.05 + 0.3875 \times 0.95} = \frac{0.04494}{0.04494 + 0.36813} = \frac{0.04494}{0.41306} \approx \mathbf{10.88\%}$$
- **Academic Caveat:** Reported precision ($69.61\%\text{--}69.79\%$) represents a balanced evaluation benchmark. In low-prevalence production codebases, operational triage precision will decrease significantly due to the base-rate effect.

### 4.2 SZZ Label Limitations
- Defect labels are derived via SZZ `git blame` tracing. SZZ relies on heuristics (line changes in bug-fixing commits) and may occasionally attribute defects to incidental refactoring or cleanup commits rather than true defect-inducing logic.
- SZZ labels represent heuristic approximations of defect-inducing revisions, not infallible ground truth.

### 4.3 Candidate-Clean Label Limitations (Open-World Assumption)
- Methods sampled from stable repository `HEAD` revisions without recorded bug fixes are classified as *candidate clean*.
- Under the Open-World Assumption of software engineering, the absence of defect reports does not prove that code is permanently defect-free. Latent, unobserved, or yet-unreported bugs may exist.

### 4.4 Out-of-Fold Threshold Tuning Optimism (Absence of Nested CV)
- The decision threshold ($\tau^* = 0.40$) was selected by sweeping across aggregated out-of-fold probability predictions from the same 5-fold cross-validation used for model selection, rather than within a nested cross-validation loop or on an independent validation split.
- Tuning on out-of-fold predictions avoids in-sample training bias but may introduce mild optimistic selection bias into the cross-validation metrics (F1 = 0.7405, Accuracy = 70.42%).
- This optimism was empirically evaluated by freezing the threshold prior to evaluating the independent holdout (`Newtonsoft.Json`), where the 0.40 cutoff confirmed genuine generalizability.

### 4.5 Repository-Level Generalization Scope
- The 6 evaluated repositories (`Humanizer`, `Serilog`, `MediatR`, `Polly`, `FluentValidation`, `Newtonsoft.Json`) represent mature, highly starred open-source libraries.
- Proprietary enterprise systems with monorepo architectures, heavy legacy dependencies, or different engineering cultures may exhibit distinct defect distributions.

### 4.6 Absence of External Human Developer Feedback
- External human practitioner feedback was **not collected** due to academic course constraints.
- [DEVELOPER_STUDY_TEMPLATE.md](../07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md) is published as a formal, reproducible research protocol instrument for future human evaluation, not evidence of a completed human study.
- Qualitative review was conducted via automated AST inspection and Git history analysis by the automated research pipeline, not human software engineers.

### 4.7 Temporal Asymmetry Between Defect-Prone and Candidate-Clean Observations
- Defect-prone observations are extracted from historical pre-fix revisions at the specific commit where the bug was introduced, whereas candidate-clean observations are sampled from the latest stable `HEAD` revision.
- While this sampling strategy ensures that candidate-clean methods survived historical bug fixes across the observed Git history, it creates a temporal asymmetry between historical and contemporary source code snapshots that constitutes an inherent characteristic of version-control mining under the Open-World Assumption.

---

## 5. Future Research Directions

1. **Semantic Embeddings (CodeBERT / Graph Neural Networks):** Augmenting static AST metrics with neural token embeddings and Control Flow Graph (CFG) representations to detect semantic bugs in concise 1-line methods.
2. **Just-In-Time (JIT) Developer Metrics:** Integrating author experience, commit churn, and temporal metrics alongside static code metrics.
3. **Automated Refactoring Guidance:** Coupling defect alerts with Roslyn code refactoring providers to automatically suggest extract-method refactorings for methods with high cyclomatic complexity and deep nesting.

