# Project Completion Baseline & Implementation Plan

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Master's Programme:** Applied Computational Intelligence  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Date:** November 2026  
**Auditor / Lead Engineer:** Autonomous Senior ML4SE Specialist  

---

## 1. Executive Summary

This document establishes the verified, immutable baseline for the completion of the C# Software Defect Prediction project. It formalizes the authoritative historical data counts, resolves historical documentation discrepancies, assesses the project's compliance against the six university assignment criteria, and defines the detailed protocol for executing Phases 2 through 8 to bring the project to a finalized, academically defensible, and reproducible state.

---

## 2. Assessment Against University Assignment Criteria

| Requirement | Description | Current Status | Planned Final State |
| :--- | :--- | :--- | :--- |
| **Req 1** | Identify a real-world software engineering problem suitable for ML | **Fully Satisfied** | Method-level defect prediction for C# codebases using static structural, complexity, and coupling metrics extracted via Microsoft Roslyn. |
| **Req 2** | Collect relevant and representative real-world data | **Partially Satisfied** | Dataset Snapshot #1 (`csharp_empirical_v1`, 483 rows across 3 repos) established. **Phase 2** will expand collection to 5 distinct training repositories (`Humanizer`, `MediatR`, `FluentValidation`, `Serilog`, `Polly`) to form Dataset Snapshot #2 (~466 rows) plus 1 quarantined holdout (`Newtonsoft.Json`). |
| **Req 3** | Select and justify an appropriate ML technique | **Fully Satisfied** | Multi-model evaluation comparing Random Forest, Decision Tree, Logistic Regression, and DummyClassifier baselines with feature importance analysis and complexity justifications. |
| **Req 4** | Implement preprocessing, training, and evaluation | **Substantially Satisfied** | In-fold preprocessing, out-of-fold threshold tuning, Brier scores, ROC-AUC/PR-AUC implemented. Currently evaluated on 2-fold GroupKFold (382 rows). **Phase 3** will execute full 5-fold GroupKFold across the 5 independent training repositories. |
| **Req 5** | Validate model using real-world examples and developer feedback | **Partially Satisfied** | Holdout evaluated on `CommandLineParser` (Dataset 1). **Phase 4** will evaluate the frozen model on a strictly quarantined, independent holdout (`Newtonsoft.Json`) with a qualitative prediction sample audit. **Phase 5** will conduct structured developer feedback evaluation. |
| **Req 6** | Produce a comprehensive report covering problem, data, ML, results, validity threats | **In Progress** | `docs/FINAL_REPORT.md` will be expanded into a 22-section research-grade academic report covering all methodological disclosures, threats to validity, and empirical findings. |

---

## 3. Authoritative Historical Dataset & Experiment Baseline

### 3.1 Dataset Snapshot #1 (`csharp_empirical_v1_v1.0.0.csv`)
- **Dataset Snapshot ID:** 1
- **Total Observations:** 483 methods (226 positive / bug-inducing, 257 candidate-clean)
- **Class Balance:** 46.79% positive, 53.21% candidate-clean
- **Features:** 26 Roslyn-extracted static code metrics
- **Repository Breakdown:**
  - `Humanizer` (Repo #4): 291 observations (139 positive, 152 candidate-clean)
  - `MediatR` (Repo #3): 91 observations (43 positive, 48 candidate-clean)
  - `CommandLineParser` (Repo #1): 101 observations (44 positive, 57 candidate-clean) — Used as development holdout in Dataset 1 experiments.

### 3.2 Authoritative Historical Experiment (`exp_20261113_170914`)
- **Model:** Random Forest (`rf_feature_constrained_log2`: `n_estimators=100`, `max_depth=5`, `max_features='log2'`, `min_samples_split=5`)
- **Cross-Validation Scheme:** 2-Fold GroupKFold ($N_{\text{repos}}=2$, 382 training observations from `MediatR` and `Humanizer`):
  - Fold 1 (Validation: `MediatR`, 91 obs): F1 = 0.6596, Recall = 0.7209, Precision = 0.6078, Brier = 0.2227
  - Fold 2 (Validation: `Humanizer`, 291 obs): F1 = 0.7006, Recall = 0.7914, Precision = 0.6286, Brier = 0.2312
  - Cross-Validation Mean ($\tau=0.50$): F1 = $0.6801 \pm 0.0205$, Recall = $0.7561 \pm 0.0352$, Precision = $0.6182 \pm 0.0104$, Brier = $0.2269 \pm 0.0042$, ROC-AUC = $0.6558$, PR-AUC = $0.6212$
  - Out-of-Fold Threshold Optimized ($\tau=0.30$): F1 = 0.7533, Recall = 0.9396, Precision = 0.6287
- **Dataset 1 Development Holdout (`CommandLineParser`, 101 observations):**
  - Nominal Threshold ($\tau=0.50$): Accuracy = 51.49%, Precision = 46.58%, Recall = 77.27% (34/44), F1 = 0.5812, Brier = 0.2627, ROC-AUC = 0.5186, PR-AUC = 0.4496
  - Tuned Threshold ($\tau=0.30$): Accuracy = 49.50%, Precision = 47.19%, Recall = 95.45% (42/44), F1 = 0.6316, Brier = 0.2627

### 3.3 Reconciled Historical Discrepancies
1. **Humanizer Count (291 vs 178):** Reconciled. 178 was an erroneous documentation artifact caused by doubling True Positives (89); the true empirical observation count in Dataset 1 is **291**.
2. **MediatR Count (91 vs 105):** Reconciled. 105 was an erroneous documentation artifact; the true empirical observation count in Dataset 1 is **91**.
3. **FluentValidation Pilot Count (28 vs 34):** Reconciled. 34 was from the uncorrected v1 pilot where 3 test fixture methods leaked (resulting in 6 observations with 1:1 pairing). The audited v2 pilot with strict production-only filtering contains **28 production observations** (14 positive, 14 clean).
4. **GroupKFold Folds (2 vs 5):** Historically, true 5-fold CV was impossible on Dataset 1 because training only contained 2 repositories (`Humanizer` and `MediatR`). Phase 2 and 3 resolve this fundamentally by adding 3 additional repositories, enabling genuine 5-fold GroupKFold.

---

## 4. Controlled Roadmap for Remaining Phases

### Phase 2: Controlled Dataset Expansion
- **Target Repositories:** `serilog/serilog` and `App-vNext/Polly`.
- **Target Commits:** Up to 350 commits each mined from Git history.
- **Pipeline:**
  1. Clone repositories into `data/repositories/` via `RepositoryManager`.
  2. Mine commits and detect bug-fixing commits via `BugFixDetector` (keyword + pattern regex, threshold 0.50).
  3. Execute SZZ tracing via `SZZAnalyzer` enforcing `src/utils/source_classifier.py` to reject test paths.
  4. Balance positive and candidate-clean methods 1:1 per commit via `LabelManager`.
  5. Extract 26 Roslyn code metrics via `FeatureExtractor`.
  6. Aggregate with `Humanizer` (291), `MediatR` (91), and `FluentValidation` (28) into **Dataset Snapshot #2** (`csharp_empirical_v2_v2.0.0.csv`).
  7. Preserve Dataset Snapshot #1 (`csharp_empirical_v1`) completely unmodified.
  8. **Holdout Quarantine:** Strictly do NOT clone, mine, or inspect `JamesNK/Newtonsoft.Json` during Phase 2.
- **Deliverables:** `docs/DATASET_EXPANSION_FINAL_REPORT.md`, `reports/dataset_expansion/dataset_expansion_summary.json`, Dataset #2 CSV.

### Phase 3: Final Multi-Model 5-Fold GroupKFold Experiment
- **Dataset:** Dataset Snapshot #2 across 5 distinct repository groups.
- **Evaluation Protocol:** 5-fold GroupKFold ($N_{\text{repos}}=5$, $K=5$, each fold leaves out one entire repository).
- **Models Evaluated:**
  - `DummyClassifier(strategy='most_frequent')` & `DummyClassifier(strategy='prior')`
  - `LogisticRegression(class_weight='balanced', max_iter=1000)`
  - `DecisionTreeClassifier(max_depth=5, min_samples_split=10)`
  - `RandomForestClassifier(n_estimators=100, max_depth=5, max_features='log2', min_samples_split=5)`
- **Preprocessing Isolation:** In-fold median imputation, zero-variance feature removal, and robust scaling fit strictly on training splits.
- **Threshold Optimization:** Out-of-fold search across $\tau \in [0.10, 0.90]$ to maximize F1, evaluated alongside nominal $\tau=0.50$.
- **Calibration:** Brier score calculated for all probabilistic models across folds.
- **Deliverables:** `scripts/run_final_experiment.py`, `reports/experiments/final/`, `docs/FINAL_EXPERIMENTAL_RESULTS.md`.

### Phase 4: Independent Quarantined Holdout Evaluation
- **Target:** `JamesNK/Newtonsoft.Json`.
- **Procedure:**
  1. Clone and mine `Newtonsoft.Json` only after Phase 3 models and thresholds are frozen.
  2. Extract production-only methods using identical Roslyn pipeline.
  3. Perform one-shot evaluation using the frozen best model from Phase 3 at both nominal ($\tau=0.50$) and tuned ($\tau^*$) thresholds.
  4. Qualitative Audit: Manually inspect and document a sample of True Positives, False Positives, and False Negatives, cross-referencing SZZ commits and method code.
- **Deliverables:** `docs/INDEPENDENT_VALIDATION_REPORT.md`, `reports/holdout/newtonsoft_holdout_results.json`.

### Phase 5: Developer Feedback Evaluation
- **Methodology:** Use `docs/DEVELOPER_STUDY_TEMPLATE.md` to evaluate utility, interpretability of Roslyn metrics, and trust in predictions.
- **Transparency:** Clearly document participants, roles, code review decisions, and qualitative insights; explicitly disclose any practical limitations without fabrication.
- **Deliverables:** `docs/DEVELOPER_FEEDBACK_REPORT.md`.

### Phase 6: Comprehensive Academic Report
- **Document:** `docs/FINAL_REPORT.md`.
- **Structure:** 22 complete academic sections adhering to ML4SE standards:
  - Abstract & Problem Formulation
  - Data Collection & SZZ Pipeline (with threat disclosures)
  - Static Code Metrics & Roslyn Extraction
  - Dataset Versioning & Characteristics
  - Experimental Setup & 5-Fold Repository-Aware CV
  - Multi-Model Comparative Analysis
  - Calibration & Threshold Tuning Analysis
  - Independent Holdout Evaluation on `Newtonsoft.Json`
  - Qualitative Error Analysis
  - Developer Feedback Study
  - Threats to Construct, Internal, External, and Conclusion Validity
  - Future Work & Conclusions
- **Deliverable:** Fully written, mathematically rigorous academic paper in Markdown.

### Phase 7: README and Documentation Reconciliation
- **Document:** `README.md`.
- **Updates:** Complete synchronization with Dataset #2, 5-fold CV results, `Newtonsoft.Json` holdout metrics, multi-model table, and CLI instructions.

### Phase 8: Final Verification, Smoke Testing & Audit
- **Verification:** Full automated test suite execution, Roslyn analyzer build, end-to-end prediction smoke tests, Streamlit UI verification.
- **Completion Audit:** `docs/PROJECT_COMPLETION_AUDIT.md` verifying compliance against all 6 university requirements.

