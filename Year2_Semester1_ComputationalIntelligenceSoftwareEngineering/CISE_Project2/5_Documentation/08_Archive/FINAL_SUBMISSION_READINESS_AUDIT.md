# Final Submission Readiness Audit: Independent Academic & Research Assessment

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Master's Programme:** Applied Computational Intelligence  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Role:** Independent Academic Examiner & Senior ML4SE Research Auditor  
**Date:** November 2026  
**Audit Scope:** Read-Only Verification of Implementation, Datasets, Experiments, Models, Reports, and University Criteria  

---

## 1. Executive Summary

This independent audit conducts a comprehensive, read-only examination of the final project repository (`CISE_Project2`). The audit evaluates the codebase, versioned datasets, experimental artifacts, frozen models, independent holdout results, and documentation against the six core evaluation requirements established by the university curriculum.

The project demonstrates exceptional technical depth, architectural modularity, and experimental rigor. The transition from preliminary exploratory work on Dataset #1 (483 observations, 2-fold CV) to an expanded multi-repository corpus on Dataset #2 (578 production observations across 5 training repositories) enabled a genuine **5-fold repository-aware cross-validation** ($N_{\text{repos}}=5$, $K=5$) with zero intra-repository leakage. The regularized Random Forest model (`rf_compact_regularized`) was appropriately selected as the winning architecture (CV F1 = $0.6859 \pm 0.0247$, Brier = $0.2144$), and an out-of-fold tuned threshold ($\tau^* = 0.40$) was derived purely from training predictions. An independent sixth repository, `JamesNK/Newtonsoft.Json` (159 observations), was maintained under strict quarantine and evaluated only after models and thresholds were frozen, achieving an out-of-domain F1 of **0.7845** and Recall of **89.87%** (71/79 defects caught).

All 121 unit and integration tests pass deterministically, and the .NET 9.0 Roslyn analyzer builds with zero errors or warnings. However, the audit identifies specific methodological limitations—most notably that user feedback from external human practitioners was **not collected**, that qualitative case audits were performed algorithmically by the AI agent rather than through human user studies, and that precision metrics reported from artificially balanced datasets must be interpreted in light of the base-rate fallacy in low-prevalence production environments.

**Final Audit Verdict:** **READY WITH DOCUMENTED LIMITATIONS**.

---

## 2. Assessment of University Assignment Requirements

| Requirement | Prescribed University Objective | Assigned Rating | Concrete Verification Evidence |
| :--- | :--- | :---: | :--- |
| **Requirement 1** | Identify a real-world software engineering problem suitable for ML | **COMPLETE** | Method-level software defect prediction in C#. Problem formulation clearly articulated in [FINAL_REPORT.md](../) Section 2. Method-level granularity directly addresses practical code review needs. |
| **Requirement 2** | Collect relevant and representative real-world data | **COMPLETE** | Automated pipeline mines public GitHub C# repositories. Two versioned dataset snapshots exist in SQLite and CSV ([csharp_empirical_v1](../): 483 obs; [csharp_empirical_v2](../): 578 obs across 5 repos). Strict production filtering eliminates test fixtures (0% test leakage). |
| **Requirement 3** | Select and justify an appropriate machine learning technique | **COMPLETE** | Multi-model benchmark evaluates 11 configurations across 4 algorithm families (Dummy, Logistic Regression, Decision Trees, Random Forest). Selection of `rf_compact_regularized` is empirically and theoretically justified in [FINAL_EXPERIMENTAL_RESULTS.md](../) by depth constraints preventing project-specific memorization. |
| **Requirement 4** | Implement preprocessing, training and evaluation | **COMPLETE** | Genuine 5-Fold GroupKFold CV ($N=5, K=5$). Preprocessing (median imputation, constant feature pruning, scaling) fitted strictly in-fold. Probability calibration measured via Brier score (0.2144). Out-of-fold threshold tuning ($\tau^*=0.40$) executed without test-set leakage. |
| **Requirement 5** | Validate model using real-world examples and gather user feedback where feasible | **COMPLETE WITH LIMITATIONS** | Real-world validation is extensive: independent holdout on quarantined `Newtonsoft.Json` (159 methods, Recall=89.87%, F1=0.7845) and 12-case qualitative audit. **Limitation:** User feedback from external human developers was **not collected** due to academic course constraints. The formal study protocol was published ([DEVELOPER_STUDY_TEMPLATE.md](../)) and evaluated qualitatively without data fabrication ([DEVELOPER_FEEDBACK_REPORT.md](../)). |
| **Requirement 6** | Produce a comprehensive report covering problem, data, ML methodology, results, threats | **COMPLETE** | [FINAL_REPORT.md](../) contains all 22 required academic sections, including formal mathematical formulations, architecture flowcharts, empirical benchmark tables, and detailed threats to validity. |

---

## 3. Dataset #2 Integrity & Reconciled Verification

We independently verified the physical CSV export ([csharp_empirical_v2_v2.0.0.csv](../)), SQLite database (`data/database/bug_detection.db`), metadata file, and summary reports.

### 3.1 Empirical Observation Counts

| Repository ID | Full Name | Buggy (Label 1) | Clean (Label 0) | Total Verified in CSV | Total Verified in SQLite | % of Dataset |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Repo #4** | `Humanizr/Humanizer` | 139 | 152 | 291 | 291 | 50.35% |
| **Repo #15** | `serilog/serilog` | 66 | 68 | 134 | 134 | 23.18% |
| **Repo #3** | `LuckyPennySoftware/MediatR` | 43 | 48 | 91 | 91 | 15.74% |
| **Repo #16** | `App-vNext/Polly` | 17 | 17 | 34 | 34 | 5.88% |
| **Repo #14** | `FluentValidation/FluentValidation` | 14 | 14 | 28 | 28 | 4.84% |
| **Total** | **5 Repositories** | **279 (48.27%)** | **299 (51.73%)** | **578** | **578** | **100.0%** |

- **Total Observations:** Exactly **578 rows**, matching the reported count in [DATASET_EXPANSION_FINAL_REPORT.md](../).
- **Class Balance:** 279 positive (48.27%) and 299 candidate-clean (51.73%).
- **Feature Schema:** Exactly **26 Roslyn numerical features** are present.
- **Missing Values:** Exactly **0 missing values** across all 26 features across all 578 observations.
- **Test File Exclusion:** Re-evaluating all 578 `file_path` values through `src/utils/source_classifier.py` confirmed **0 test files leaked** (100% production verified).

### 3.2 Audit Findings on Method Duplication & File Paths
1. **Method Signatures Across Different Commits (46 rows / 23 unique signatures):**
   - In 23 instances, the same method signature appears twice or three times in the dataset (e.g. `Humanizer.BuildDefault`, `MediatR.BuildMediator`, `Serilog.MessageTemplateParser.ParseTextToken`).
   - **Verification:** Inspection of underlying commit hashes confirmed that these represent *different historical revisions* of the method over time with distinct LOC, different cyclomatic complexities, and different bug-fixing commits. Because SZZ traces defects to specific historical commits, methods that underwent multiple refactorings/bug-fixes across years appear in their respective pre-fix states.
2. **`FluentValidation/TestHelper/ValidatorTestExtensions.cs` (4 observations):**
   - Auditing identified 4 observations from `src/FluentValidation/TestHelper/ValidatorTestExtensions.cs`.
   - **Verification:** This file is not a test project or test suite; it is a public component of the `FluentValidation` core NuGet library providing assertion extension methods for consuming developers. Its classification as production source code is structurally defensible.
3. **`MediatR.Examples` (7 observations):**
   - 7 observations originate from `samples/MediatR.Examples/`. These observations were inherited directly from historical Dataset Snapshot #1 (`csharp_empirical_v1`), which was preserved unmodified as required by the experimental protocol.

---

## 4. Five-Fold Cross-Validation Verification

We independently inspected [experiment_results.json](../), recalculating all fold statistics and checking group assignments:

### 4.1 Fold Assignment & Zero-Leakage Audit

| Fold Index | Held-Out Validation Repository | Validation Samples | Training Repositories | Training Samples | Intra-Repo Overlap |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Fold 1** | Repo 4 (`Humanizr/Humanizer`) | 291 | Repos 15, 3, 16, 14 | 287 | **0 (Zero Leakage)** |
| **Fold 2** | Repo 15 (`serilog/serilog`) | 134 | Repos 4, 3, 16, 14 | 444 | **0 (Zero Leakage)** |
| **Fold 3** | Repo 3 (`LuckyPennySoftware/MediatR`) | 91 | Repos 4, 15, 16, 14 | 487 | **0 (Zero Leakage)** |
| **Fold 4** | Repo 16 (`App-vNext/Polly`) | 34 | Repos 4, 15, 3, 14 | 544 | **0 (Zero Leakage)** |
| **Fold 5** | Repo 14 (`FluentValidation/FluentValidation`) | 28 | Repos 4, 15, 3, 16 | 550 | **0 (Zero Leakage)** |

- **Total Evaluated Across Folds:** $291 + 134 + 91 + 34 + 28 = 578$. Every repository appears in the validation set of **exactly one fold**.
- **Leakage Check:** $\text{Train\_Repos} \cap \text{Val\_Repos} = \emptyset$ for all 5 folds.

### 4.2 Mathematical Recalculation of Cross-Validation Metrics

For the winning model `rf_compact_regularized`:
- Individual fold F1 scores: $[0.6767, 0.6995, 0.6593, 0.6667, 0.7273]$.
- **Mean F1:**
  $$\bar{F}_1 = \frac{0.6767 + 0.6995 + 0.6593 + 0.6667 + 0.7273}{5} = \frac{3.4295}{5} = \mathbf{0.6859}$$
- **Standard Deviation:**
  - Population standard deviation ($\text{ddof}=0$): **$0.0247$**.
  - Sample standard deviation ($\text{ddof}=1$): **$0.0277$**.
  - **Audit Note:** The reported standard deviation in the final reports ($0.0247$) corresponds exactly to the population standard deviation ($\text{ddof}=0$) across the five folds. Both representations confirm low cross-fold variance.
- Individual fold accuracy scores: $[0.7045, 0.5896, 0.6593, 0.7353, 0.6786]$ (corresponding to Fold 1 `Humanizer` [205/291], Fold 2 `Serilog` [79/134], Fold 3 `MediatR` [60/91], Fold 4 `Polly` [25/34], Fold 5 `FluentValidation` [19/28]).
- **Mean Accuracy:**
  $$\bar{\text{Acc}} = \frac{0.704467 + 0.589552 + 0.659341 + 0.735294 + 0.678571}{5} = \frac{3.367225}{5} = \mathbf{0.6734} \quad (67.34\%)$$
- **Standard Deviation:**
  - Population standard deviation ($\text{ddof}=0$): **$0.0491$** ($4.91\%$).
  - Sample standard deviation ($\text{ddof}=1$): **$0.0549$** ($5.49\%$).

### 4.3 Recalculation of Out-of-Fold Threshold Optimization
Threshold optimization was conducted on pooled out-of-fold probabilities ($N=578$):
- **Nominal Threshold ($\tau = 0.50$):**
  $$TN=183, \quad FP=116, \quad FN=74, \quad TP=205$$
  - $\text{Accuracy} = \frac{183 + 205}{578} = \frac{388}{578} = \mathbf{0.6713}$ ($67.13\%$)
  - $\text{Precision} = \frac{205}{205 + 116} = \frac{205}{321} = \mathbf{0.6386}$ ($63.86\%$)
  - $\text{Recall} = \frac{205}{205 + 74} = \frac{205}{279} = \mathbf{0.7348}$ ($73.48\%$)
  - $\text{F1} = \frac{2 \times 0.638629 \times 0.734767}{0.638629 + 0.734767} = \mathbf{0.6833}$
- **Optimized Threshold ($\tau^* = 0.40$):**
  $$TN=163, \quad FP=136, \quad FN=35, \quad TP=244$$
  - $\text{Accuracy} = \frac{163 + 244}{578} = \frac{407}{578} = \mathbf{0.7042}$ ($70.42\%$)
  - $\text{Precision} = \frac{244}{244 + 136} = \frac{244}{380} = \mathbf{0.6421}$ ($64.21\%$)
  - $\text{Recall} = \frac{244}{244 + 35} = \frac{244}{279} = \mathbf{0.8746}$ ($87.46\%$)
  - $\text{F1} = \frac{2 \times 0.642105 \times 0.874551}{0.642105 + 0.874551} = \mathbf{0.7405}$
- **Verification:** All reported threshold optimization values are mathematically exact. The reports correctly distinguish nominal performance from threshold-optimized performance.

### 4.4 Discrepancy Resolution & Reconciliation of Accuracy Figures ($67.34\%$ vs. $67.13\%$ vs. $70.42\%$)

An independent audit query flagged an apparent discrepancy between an earlier summary reporting out-of-fold accuracy as $67.34\%$ alongside threshold-tuned metrics ($\tau^* = 0.40$), while the final confusion matrix mathematically yields $70.42\%$. We audited the underlying experiment artifacts (`reports/experiments/final/experiment_results.json`) and reconciled the three related accuracy figures:

| Metric Identifier | Evaluation Protocol | Operating Threshold | Underlying Formula | Reported Value | Mathematical Verification |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **5-Fold CV Mean Accuracy** | Unweighted fold-level cross-validation average across 5 held-out repos | Nominal $\tau = 0.50$ | $\frac{1}{K}\sum_{k=1}^5 \text{Acc}_k$ | **$0.6734 \pm 0.0491$** | $\frac{0.7045 + 0.5896 + 0.6593 + 0.7353 + 0.6786}{5} = 0.673445$ |
| **Pooled OOF Nominal Accuracy** | Global pooled out-of-fold prediction across all 578 observations | Nominal $\tau = 0.50$ | $\frac{TN + TP}{N} = \frac{183 + 205}{578}$ | **$0.6713$** ($67.13\%$) | Exact match with pooled confusion matrix at default threshold $\tau=0.50$. |
| **Pooled OOF Tuned Accuracy** | Global pooled out-of-fold prediction across all 578 observations | Tuned $\tau^* = 0.40$ | $\frac{TN + TP}{N} = \frac{163 + 244}{578}$ | **$0.7042$** ($70.42\%$) | Exact match with pooled confusion matrix at optimal threshold $\tau^*=0.40$. |

#### Root Cause of the Earlier Summary Discrepancy
The earlier summary conflated two distinct evaluation dimensions:
1. **The Nominal CV Fold Mean ($67.34\%$):** The benchmark comparison table in Section 14 evaluates all 11 model configurations at the standard threshold $\tau = 0.50$ using unweighted fold-mean accuracy ($0.6734 \pm 0.0491$).
2. **The Tuned OOF Metrics ($\tau^* = 0.40$):** Threshold optimization aggregates out-of-fold probability predictions globally across all 578 instances. At $\tau^* = 0.40$, the confusion matrix yields $TN=163, FP=136, FN=35, TP=244$, which mathematically produces $\text{Accuracy} = \frac{407}{578} = \mathbf{70.42\%}$, $\text{Precision} = \mathbf{64.21\%}$, $\text{Recall} = \mathbf{87.46\%}$, and $\text{F1} = \mathbf{0.7405}$.
3. In an earlier intermediate summary note, the nominal fold-mean accuracy ($67.34\%$) was mistakenly transcribed alongside the tuned-threshold precision, recall, and F1 values.
4. **Audit Conclusion:** The underlying experimental JSON artifacts and physical models are completely consistent and uncorrupted. The authoritative tuned-threshold out-of-fold accuracy is **$70.42\%$**, while **$67.34\%$** is the nominal default-threshold cross-validation fold mean.

---

## 5. Frozen Model Artifact Verification

We audited the serialized model bundle on disk:
- **File Location:** `reports/experiments/final/model/exp_final_5fold_v2_best_rf_compact_regularized.joblib`
- **File Size:** 145,504 bytes
- **SHA-256 Digest:** `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e`
- **Model Architecture:** `RandomForestClassifier` (`n_estimators=100`, `max_depth=8`, `min_samples_split=5`, `min_samples_leaf=4`, `max_features='sqrt'`, `class_weight='balanced'`).
- **Preprocessor:** `DataPreprocessor` (impute_missing=True, remove_constant=True) fitted on all 578 training observations with 26 feature inputs.
- **Verification:** The saved model matches the winning `rf_compact_regularized` configuration.

---

## 6. Independent Holdout Verification (`JamesNK/Newtonsoft.Json`)

We audited the holdout evaluation records in `reports/holdout/newtonsoft_holdout_results.json` and [INDEPENDENT_VALIDATION_REPORT.md](../):

### 6.1 Independence & Anti-Snooping Verification
1. **Quarantine Audit:** `JamesNK/Newtonsoft.Json` (Repo #17) is completely absent from all training folds and from Dataset Snapshots #1 and #2.
2. **Pre-Freeze Protocol:** The model architecture (`rf_compact_regularized`) and decision thresholds ($\tau=0.50, \tau^*=0.40$) were frozen in Phase 3 before `Newtonsoft.Json` was cloned and mined in Phase 4.
3. **Cross-Repository Code Overlap:** An exhaustive cross-query between the training set (578 observations) and `Newtonsoft.Json` (159 observations) revealed:
   - Shared Method Signatures: **0**.
   - Identical Source Code Strings: **0**.
   - Zero code leakage between training codebases and `Newtonsoft.Json`.

### 6.2 Holdout Metrics Recalculation
- **Holdout Dataset:** Exactly **159 production observations** (79 Buggy, 80 Clean).
- **Nominal Threshold ($\tau = 0.50$):**
  $$TN=51, \quad FP=29, \quad FN=12, \quad TP=67$$
  - $\text{Accuracy} = \frac{51 + 67}{159} = \mathbf{74.21\%}$
  - $\text{Precision} = \frac{67}{67 + 29} = \frac{67}{96} = \mathbf{69.79\%}$
  - $\text{Recall} = \frac{67}{67 + 12} = \frac{67}{79} = \mathbf{84.81\%}$
  - $\text{F1} = \mathbf{0.7657}$
  - $\text{ROC-AUC} = \mathbf{0.8209}$ | $\text{PR-AUC} = \mathbf{0.7917}$ | $\text{Brier} = \mathbf{0.1713}$
- **CV-Tuned Threshold ($\tau^* = 0.40$):**
  $$TN=49, \quad FP=31, \quad FN=8, \quad TP=71$$
  - $\text{Accuracy} = \frac{49 + 71}{159} = \mathbf{75.47\%}$
  - $\text{Precision} = \frac{71}{71 + 31} = \frac{71}{102} = \mathbf{69.61\%}$
  - $\text{Recall} = \frac{71}{71 + 8} = \frac{71}{79} = \mathbf{89.87\%}$
  - $\text{F1} = \mathbf{0.7845}$
- **Verification:** All reported holdout metrics match the underlying prediction records without discrepancy.

---

## 7. Qualitative Prediction Sample Audit

We audited the qualitative cases documented in [INDEPENDENT_VALIDATION_REPORT.md](../) and `reports/holdout/newtonsoft_holdout_results.json`:
- **Cases Inspected:** 12 structured cases (3 True Positives, 3 False Positives, 3 False Negatives, 3 True Negatives).
- **Evidence Backing:** Each case includes method signatures, source file paths, ground-truth SZZ labels, predicted probabilities, and detailed Roslyn metrics (LOC, cyclomatic complexity, nesting depth, parameter counts, method call counts).
- **Critical Findings:**
  - **True Positives** (`CalculatePropertyDetails`, `ReadMetadataPropertiesToken`): Methods exhibit extreme cyclomatic complexity (17–22), high parameter counts (9–11), and deep nesting (up to 6 levels). The model assigned $88\%\text{--}91\%$ defect risk, corroborating historical null-reference regressions fixed in Git.
  - **False Positives** (`BsonReader.ReadString`, `BsonBinaryWriter.CalculateSize`): Low-level binary buffer parsing routines. Structurally complex (LOC 54–78, complexity 8–17) but defensively written.
  - **False Negatives** (`JContainer.Values`, `JContainer.IsMultiContent`): Concise 1-statement generic wrappers (LOC 4–11, complexity 1). SZZ traced subtle type-covariance bugs to them. Static syntactic metrics have no signal to detect semantic type bugs in 1-line methods.
- **Audit Qualification:** The qualitative case review was performed through automated AST inspection and git-log analysis by the autonomous agent, rather than by human software engineers in a controlled lab session.

---

## 8. Developer Feedback Assessment

We inspected [DEVELOPER_FEEDBACK_REPORT.md](../) and [DEVELOPER_STUDY_TEMPLATE.md](../):

- **External Human Participant Feedback:** **NOT COLLECTED**.
- **Transparent Disclosure:** [DEVELOPER_FEEDBACK_REPORT.md](../) Section 2 and [FINAL_REPORT.md](../) Section 19 explicitly disclose that:
  > *"In strict accordance with academic ethics and research reproducibility guidelines, no external participant responses or fabricated survey cohorts are simulated. ... the study protocol is formally documented as a reproducible research instrument accompanied by expert qualitative analysis."*
- **Curriculum Requirement Evaluation:** University Requirement 5 states: *"Validate the model using real-world examples and gather user feedback where feasible."* The project satisfies the primary clause through extensive real-world holdout evaluation (`Newtonsoft.Json`), and ethically discloses the absence of external user survey responses. Rating assigned: **COMPLETE WITH LIMITATIONS**.

---

## 9. Academic Consistency & Critical Methodological Considerations

### 9.1 Artificial Class Balancing vs. Operational Precision (Base-Rate Fallacy)
- **Dataset Context:** In both Dataset #2 (48.27% positive) and the holdout dataset (49.69% positive), methods were sampled at an approximate **1:1 class ratio** to prevent machine learning estimators from collapsing into trivial majority predictors.
- **Operational Reality:** In industrial production repositories, the natural defect prevalence of C# methods is typically **$2\%\text{--}10\%$** (severe class imbalance).
- **Audit Caveat:** While the model achieves a precision of **$69.61\%\text{--}69.79\%$** on the 1:1 balanced holdout, this precision will decline in production environments where the base rate is 5%. For example, with $90\%$ recall and $60\%$ specificity on 1,000 production methods (50 buggy, 950 clean):
  - True Positives: $50 \times 0.90 = 45$
  - False Positives: $950 \times (1 - 0.60) = 380$
  - Operational Precision: $\frac{45}{45 + 380} = \mathbf{10.6\%}$
- **Assessment:** [FINAL_REPORT.md](../) must be read with the explicit understanding that reported precision reflects a balanced evaluation benchmark rather than operational triage precision in low-prevalence production codebases.

### 9.2 SZZ Label Limitations
- [FINAL_REPORT.md](../) Section 20.1 appropriately discusses SZZ construct validity threats (e.g. `git blame` noise, refactoring attribution). SZZ labels are heuristic approximations of defect-inducing revisions, not infallible ground truth.

### 9.3 Probability Calibration (Brier Score)
- The report notes that `rf_compact_regularized` achieved a low Brier score ($0.2144$ on CV, $0.1713$ on holdout). While lower than uninformative baselines ($0.50$), Brier score measures mean squared probability error; it is an aggregate proper scoring metric rather than proof of decile-by-decile calibration (which requires reliability diagrams).

### 9.4 Potential Optimism in Out-of-Fold Threshold Tuning (Absence of Nested Tuning)
- **Methodological Vulnerability:** Decision threshold optimization was conducted by sweeping $\tau \in [0.10, 0.90]$ across the pooled out-of-fold validation probabilities generated from the 5-fold cross-validation of `rf_compact_regularized`. Because the same out-of-fold predictions used to evaluate model configurations were also reused to select $\tau^* = 0.40$ without a nested cross-validation loop or an independent validation split for threshold tuning, the resulting cross-validation metrics (F1 = 0.7405, Accuracy = 70.42%) may incorporate mild optimistic selection bias.
- **Empirical Mitigating Control:** The project rigorously controls for this potential optimism via **Phase 4: Independent Quarantined Holdout Testing**. Both the model configuration and the decision threshold ($\tau^* = 0.40$) were strictly frozen prior to mining `JamesNK/Newtonsoft.Json`. When evaluated on this independent repository, the tuned threshold demonstrated genuine generalization (Holdout F1 = 0.7845, Recall = 89.87%, Accuracy = 75.47%), confirming that the performance gains were not artifacts of threshold overfitting.

---

## 10. Critical Issues & Recommended Disclosures

### Critical Issues
- **None.** There are no data leaks, no broken pipelines, no failing tests, and no fabricated results.

### Recommended Academic Disclosures (for viva/presentation)
1. **Base-Rate Precision Disclosure:** When presenting the holdout precision (69.61%), explicitly clarify that this metric was evaluated on a 1:1 balanced test corpus; in an industrial repo with 5% defect prevalence, operational precision will be lower due to the base-rate effect.
2. **Developer Study Status:** State transparently that the double-blind 24-method review protocol is published as a research instrument, and that qualitative insights reflect expert static metric analysis rather than external survey cohorts.
3. **Semantic Defect Boundary:** Highlight the qualitative finding from the False Negative analysis: static AST metrics reliably detect procedural complexity bottlenecks but cannot detect semantic defects in 1-line wrapper methods.
4. **Threshold Selection Disclosure:** Disclose that threshold tuning was conducted across pooled out-of-fold cross-validation predictions rather than within a nested cross-validation loop, but emphasize that the quarantined holdout on `Newtonsoft.Json` confirmed out-of-domain transferability without degradation.

---

## 11. Final Submission Verdict

```
================================================================================
FINAL SUBMISSION VERDICT: READY WITH DOCUMENTED LIMITATIONS
================================================================================
```

### Justification
1. **Academic Rigor:** Genuine 5-fold GroupKFold cross-validation across 5 distinct open-source projects ($N=5, K=5$) with zero repository leakage.
2. **Quarantined Generalization:** One-shot holdout testing on `JamesNK/Newtonsoft.Json` (159 methods, F1=0.7845, Recall=89.87%, ROC-AUC=0.8209) confirms genuine out-of-domain transfer without data snooping.
3. **Engineering Standards:** 121 passing automated tests, .NET 9.0 Roslyn compiler analyzer, SQLite persistence, and interactive Streamlit UI.
4. **Academic Honesty:** Methodological limitations (absence of external human survey participants, SZZ heuristic approximations, balanced precision vs production base rates) are disclosed rather than obscured.

The project fulfills the academic requirements of the Computational Intelligence in Software Engineering curriculum at Babeș-Bolyai University and is recommended for submission.

