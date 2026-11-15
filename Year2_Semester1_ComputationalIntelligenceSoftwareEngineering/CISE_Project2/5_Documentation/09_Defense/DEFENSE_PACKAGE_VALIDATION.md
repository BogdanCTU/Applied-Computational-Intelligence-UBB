
# CISE Project 2 — Final Defense Package Quality Assurance & Validation Report

**Master's Degree in Applied Computational Intelligence**  
**Faculty of Mathematics and Computer Science | Babeș-Bolyai University**  
**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code (CISE Project 2)  
**Evaluation Date:** November 14, 2026  
**Final Status:** **DEFENSE READY (100% PASS)**

---

## 1. Executive Summary & Quality Determination

This report provides the authoritative quality assurance, numerical consistency audit, and integrity verification for the newly compiled university defense package located in [`5_Documentation/09_Defense/`](./).

The defense package represents the final academic deliverable for CISE Project 2. All materials have been constructed from first principles using the verified experimental results and frozen code artifacts in the repository.

### Summary of Audit Findings

1. **Deliverables Completeness (5/5 Materials Generated):** All required presentation, speaker notes, live demo protocols, defense Q&A handbooks, and executive summary PDFs exist in the defense package directory.
2. **Strict Layout & Page Limits (100% Compliant):**
   - The presentation deck (`FINAL_DEFENSE_PRESENTATION.pptx`) strictly adheres to the 15-slide, 16:9 widescreen layout requirement.
   - The executive summary PDF (`METHODOLOGY_AND_RESULTS_SUMMARY.pdf`) strictly enforces the single-page constraint, verified via programmatic canvas assertions.
3. **Pacing & Oral Delivery Alignment (14.5 Minutes):** The speaker notes provide a structured, slide-by-slide script totaling 14 minutes and 30 seconds, falling within the 12–15 minute university examination window.
4. **Numerical Parity (100% Reconciliation):** Every metric, observation count, fold distribution, and threshold value matches the authoritative experiment JSON artifacts (`experiment_results.json` and `newtonsoft_holdout_results.json`).
5. **Cryptographic Bitwise Parity (15/15 Artifacts Match):** All 15 protected databases, frozen models, datasets, and experiment logs retain 100% bitwise parity against their authoritative SHA-256 reference digests.
6. **Code & Test Suite Health:** All 123 automated regression tests pass (100%), the Microsoft Roslyn analyzer compiles with 0 warnings and 0 errors, and all markdown links resolve correctly.

---

## 2. Package Inventory & File Verification

The table below lists all generated defense package materials in [`5_Documentation/09_Defense/`](./).

| Deliverable Name | File Format | File Size (Bytes) | Primary Academic Purpose | Verification Status |
| :--- | :---: | :---: | :--- | :---: |
| [`FINAL_DEFENSE_PRESENTATION.pptx`](FINAL_DEFENSE_PRESENTATION.pptx) | PPTX (16:9) | 62,727 | 15-slide widescreen oral defense slide deck. | **VERIFIED (15 Slides)** |
| [`FINAL_DEFENSE_SPEAKER_NOTES.docx`](FINAL_DEFENSE_SPEAKER_NOTES.docx) | DOCX (Word) | 48,670 | Slide-by-slide spoken script, timing, and transitions (~14.5 min). | **VERIFIED (14.5 Min)** |
| [`LIVE_DEMO_SCRIPT.docx`](LIVE_DEMO_SCRIPT.docx) | DOCX (Word) | 46,198 | 7-stage practical application walkthrough + 4 fallback contingencies. | **VERIFIED (7 Stages)** |
| [`DEFENSE_QUESTIONS_AND_ANSWERS.docx`](DEFENSE_QUESTIONS_AND_ANSWERS.docx) | DOCX (Word) | 50,887 | 22 comprehensive academic questions and evidence-backed answers. | **VERIFIED (22 Items)** |
| [`METHODOLOGY_AND_RESULTS_SUMMARY.pdf`](METHODOLOGY_AND_RESULTS_SUMMARY.pdf) | PDF (A4) | 6,627 | Single-page dense executive defense summary (ReportLab). | **VERIFIED (Strict 1 Page)** |
| [`DEFENSE_PACKAGE_VALIDATION.md`](DEFENSE_PACKAGE_VALIDATION.md) | Markdown | — | Authoritative quality assurance and consistency sign-off report. | **THIS DOCUMENT** |

---

## 3. Slide Deck Specification & Visual Standards Compliance

The presentation deck [`FINAL_DEFENSE_PRESENTATION.pptx`](FINAL_DEFENSE_PRESENTATION.pptx) was audited against academic design standards.

### Structural & Visual Criteria

- **Slide Count:** Exactly 15 slides.
- **Aspect Ratio:** 16:9 widescreen layout (`13.333" x 7.5"` / `1920 x 1080` equivalent).
- **Color Palette:**
  - Deep Academic Navy (`#182B49`): Headers, primary containers, title slides.
  - Secondary Professional Blue (`#296299`): Metric accents, sub-banners, highlights.
  - Neutral Slate (`#4A5568` / `#718096`): Captions, secondary labels, metadata.
  - Card Fill (`#F5F7FA`): High-contrast light backgrounds for metric callouts.
  - Text Contrast: Dark slate `#1A202C` and pure white `#FFFFFF` ensuring WCAG AAA legibility.
- **Typography:** Professional clean sans-serif typography (Calibri / Arial).
- **Visual Clutter Elimination:** 0 informal emojis, 0 decorative icons, 0 pie charts. All structural comparisons use formatted native PowerPoint tables and card containers.

### Slide-by-Slide Narrative Mapping

| Slide # | Slide Title | Slide Purpose & Key Information Displayed |
| :---: | :--- | :--- |
| **1** | Title & University Identity | Master's Degree Defense in Applied Computational Intelligence; Faculty of Mathematics and Computer Science, Babeș-Bolyai University; Candidate & Supervisor metadata. |
| **2** | Research Problem & Industrial Context | Software defects cost $2.41T annually; limitations of file-level prediction; rationale for method-level defect-proneness prediction. |
| **3** | Static Code Analysis Pipeline | Microsoft Roslyn C# syntax compiler platform; 26 static code metrics across 5 families; sub-15ms parsing latency; deterministic offline execution. |
| **4** | Empirical Corpus Architecture | Dataset #2 (578 methods across 5 repos; 48.3% positive); Independent Holdout (Newtonsoft.Json, 159 methods, 49.7% positive); 737 total labeled methods. |
| **5** | Ground-Truth Attribution & Labeling | SZZ algorithm with AST mapping; git blame tracing; Open-World Assumption (Candidate-Clean vs Defect-Prone); production source filtering. |
| **6** | Validation Rigor: GroupKFold by Repository | Why naive random K-Fold is scientifically invalid (data leakage); 5-Fold GroupKFold LORO scheme; fold variance analysis (Recall $0.7403 \pm 0.1557$). |
| **7** | Regularized Random Forest Model | Champion model architecture: `n_estimators=100`, `max_depth=8`, `min_samples_split=5`, `min_samples_leaf=4`, balanced class weights; anti-overfitting constraints. |
| **8** | Decision Threshold Tuning & Cost Trade-offs | Nominal $\tau=0.50$ vs tuned $\tau^*=0.40$; boosting defect recall from $68.46\%$ to $87.46\%$ (OOF); explicit disclosure of threshold selection bias. |
| **9** | Independent Benchmark Evaluation | Newtonsoft.Json holdout results: Accuracy $75.47\%$, Recall $89.87\%$, Precision $69.61\%$, F1 $0.7845$, ROC-AUC $0.8209$, Brier $0.1713$; post-freeze evaluation status. |
| **10** | The Base-Rate Fallacy in Production | Bayesian calculation at 5% real-world defect prevalence: nominal ~70% precision drops to ~10.9% in production; framing tool as a risk prioritizer. |
| **11** | Explainable AI & Structural Defect Indicators | MDI (Gini) vs Permutation importance; Cyclomatic Complexity, Halstead Volume, Max Nesting Depth, Cognitive Complexity; actionable developer feedback. |
| **12** | Application Architecture & Live Demonstration | Streamlit UI architecture; SQLite audit persistence; sub-15ms inference latency; zero cloud/telemetry dependencies; developer privacy toggle. |
| **13** | Software Engineering Rigor & Code Quality | 123 automated regression tests passing (100%); 15/15 protected artifact SHA-256 hashes verified; Roslyn analyzer builds with 0 warnings, 0 errors. |
| **14** | Methodological Disclosures & Threats | Full academic transparency: threshold selection bias, temporal asymmetry (HEAD clean vs historical buggy), SZZ refactoring noise, external validity limits. |
| **15** | Defense Conclusions & Future Research | Summary of contributions (reproducible C# pipeline, 89.9% holdout recall, full offline tooling); future work (AST graph neural networks, multi-language expansion). |

---

## 4. Speaker Notes & Timing Validation

The oral presentation script [`FINAL_DEFENSE_SPEAKER_NOTES.docx`](FINAL_DEFENSE_SPEAKER_NOTES.docx) was validated for oral delivery pacing.

- **Allocated Defense Duration:** 12 to 15 minutes.
- **Estimated Total Speaking Time:** **14 minutes and 30 seconds (14.5 min)**.
- **Structural Features Included per Slide:**
  1. Slide Header & Metadata (Slide number, slide title, target duration in minutes:seconds).
  2. Slide Intent & Key Talking Points (Bullet-pointed conceptual takeaways).
  3. Word-for-Word Spoken Script (Written in formal, articulate academic English).
  4. Slide Transition Phrases (Natural oratorical bridges connecting consecutive slides).

### Pacing Breakdown by Slide

```text
Slide 01: Title & University Identity               [00:45]  (Cumul: 00:45)
Slide 02: Research Problem & Industrial Context     [01:00]  (Cumul: 01:45)
Slide 03: Static Code Analysis Pipeline             [01:00]  (Cumul: 02:45)
Slide 04: Empirical Corpus Architecture             [01:00]  (Cumul: 03:45)
Slide 05: Ground-Truth Attribution & Labeling       [01:00]  (Cumul: 04:45)
Slide 06: Validation Rigor: GroupKFold              [01:00]  (Cumul: 05:45)
Slide 07: Regularized Random Forest Model           [01:00]  (Cumul: 06:45)
Slide 08: Decision Threshold Tuning & Trade-offs    [01:15]  (Cumul: 08:00)
Slide 09: Independent Benchmark Evaluation          [01:00]  (Cumul: 09:00)
Slide 10: The Base-Rate Fallacy in Production       [01:15]  (Cumul: 10:15)
Slide 11: Explainable AI & Structural Defect Signs  [01:00]  (Cumul: 11:15)
Slide 12: Application Architecture & Demo           [00:45]  (Cumul: 12:00)
Slide 13: Software Engineering Rigor & Quality      [00:45]  (Cumul: 12:45)
Slide 14: Methodological Disclosures & Threats      [01:00]  (Cumul: 13:45)
Slide 15: Defense Conclusions & Future Research     [00:45]  (Cumul: 14:30)
-------------------------------------------------------------------------
TOTAL PRESENTATION TIME:                            14:30   (Target: 12–15 min)
```

---

## 5. Live Demonstration Protocol Verification

The demonstration guide [`LIVE_DEMO_SCRIPT.docx`](LIVE_DEMO_SCRIPT.docx) defines an 8–10 minute practical examination walkthrough across 7 structured stages, plus a comprehensive 4-scenario fallback protocol.

### Seven Practical Demonstration Stages

1. **Stage 1: System Launch & Offline Readiness Verification (01:00 – 01:30)**  
   Launches Streamlit application on `localhost:8501`. Verifies zero external network traffic, immediate SQLite database initialization (`cise_records.db`), and local Roslyn CLI availability.
2. **Stage 2: Dashboard & Workspace Statistics Inspection (01:30 – 02:45)**  
   Inspects Sidebar KPIs: 6 repositories total, 578 training observations, 159 holdout observations, 737 corpus observations. Verifies commit distributions and database health.
3. **Stage 3: Dataset Inspection & Repository-Level Isolation (02:45 – 04:00)**  
   Navigates to `Dataset Management`. Inspects Dataset #2 ($N=578$, 279 positive, 299 negative) and the 26 Roslyn static code metrics. Confirms `repository_id` grouping column preventing cross-repository leakage.
4. **Stage 4: Model Diagnostics & Decision Threshold Tuning (04:00 – 05:45)**  
   Navigates to `Model Evaluation`. Inspects champion regularized Random Forest model. Demonstrates ROC discrimination ($AUC=0.7025$) and threshold tuning ($\tau=0.50 \to \tau^*=0.40$), explaining the reduction of False Negatives from 88 to 35.
5. **Stage 5: Real-World Method Submission (Interactive Inference) (05:45 – 07:15)**  
   Navigates to `Real-World Bug Prediction` -> `Single Method Analysis`. Evaluates contrasting code snippets:
   - *Test Case A (Clean Business Method):* `CalculateDiscount` $\to$ Risk Score ~0.300, Low Risk, Candidate-Clean (0).
   - *Test Case B (Complex Enterprise Method):* `ProcessBatchTransactions` $\to$ Risk Score >0.720, High Risk, Defect-Prone (1).
6. **Stage 6: Prediction Breakdown & Explainability Inspection (07:15 – 08:30)**  
   Examines the `Influential Metrics & Structural Explanations` table for Test Case B, showing exact threshold exceedances: Cyclomatic Complexity ($14 > 10$), Cognitive Complexity ($19 > 15$), Nesting Depth ($5 > 3$), Parameter Count ($6 > 4$).
7. **Stage 7: History, Audit Logging & Privacy Verification (08:30 – 09:30)**  
   Navigates to `Prediction History & Privacy`. Verifies immutable SQLite audit logging with input SHA-256 hashing. Demonstrates privacy toggle in `Settings` disabling raw source code persistence.

### Fallback Contingency Procedures

| Failure Scenario | Root Cause | Immediate Recovery Action |
| :--- | :--- | :--- |
| **A: Web GUI / Port Conflict** | Port 8501 busy or browser fails to render. | Run alternate port: `streamlit run app.py --server.port 8502`<br/>Or CLI regression: `pytest 2_SourceCode/Tests/test_bug_predictor.py -v` |
| **B: Roslyn Analyzer Blocked** | Subprocess permissions or antivirus lock. | Verify binary: `.\4_AppBuild\Assets\Analyzer\MetricsAnalyzer.exe --version`<br/>Fallback to test suite pre-extracted metric evaluation. |
| **C: Database Concurrency Lock** | SQLite database locked by concurrent thread. | Execute read-only Python query script against `1_Database/SQLite/cise_records.db`. |
| **D: Strict Time Limit (<3 min)** | Committee requests compressed summary. | Execute Fast-Track 3-Step Walkthrough: Model Evaluation -> Paste Test Case B -> View Influential Metrics. |

---

## 6. Defense Questions & Answers Handbook Audit

The examination preparation handbook [`DEFENSE_QUESTIONS_AND_ANSWERS.docx`](DEFENSE_QUESTIONS_AND_ANSWERS.docx) contains 22 academic defense questions and evidence-backed answers.

### Coverage by Category

1. **Category 1: Machine Learning Model Selection & Regularization (Q1 – Q4)**
   - Q1: Why Random Forest over Deep Learning (CodeBERT) or Gradient Boosted Trees (XGBoost)?
   - Q2: Regularization constraints (`max_depth=8`, `min_samples_leaf=4`) and rejection of unconstrained trees.
   - Q3: Feature importance mechanics: Mean Decrease in Impurity (MDI/Gini) bias vs. Permutation Importance.
   - Q4: Brier score interpretation ($0.2144$ CV, $0.1713$ holdout) and probabilistic calibration.
2. **Category 2: Validation Methodology & GroupKFold Integrity (Q5 – Q8)**
   - Q5: Scientific invalidity of naive random/stratified K-Fold in software engineering (data leakage).
   - Q6: 5-Fold GroupKFold as a Leave-One-Repository-Out (LORO) cross-validation scheme.
   - Q7: Root causes of cross-validation recall variance ($0.7403 \pm 0.1557$) across heterogeneous domains.
   - Q8: Out-of-fold prediction pooling mechanics and explicit disclosure of threshold selection bias.
3. **Category 3: Ground-Truth Labeling & SZZ Heuristics (Q9 – Q12)**
   - Q9: SZZ algorithm architecture (Śliwerski et al., 2005) and Roslyn AST line mapping.
   - Q10: Known failure modes and false-positive risks of SZZ (refactoring, tangled commits).
   - Q11: Epistemic justification for "Candidate-Clean" rather than "Defect-Free" under Open-World Assumption (OWA).
   - Q12: Commit message regex heuristics and non-code asset filtering.
4. **Category 4: Temporal Asymmetry & Production Source Filtering (Q13 – Q15)**
   - Q13: Methodological consequences of temporal asymmetry (historical buggy commits vs HEAD clean snapshot).
   - Q14: Mandatory exclusion of test code and path filtering heuristics (`/test/`, `*Tests.cs`).
   - Q15: Metric normalization: preventing method length (LOC) from confounding architectural defect risk.
5. **Category 5: Holdout Evaluation & Cross-Project Generalization (Q16 – Q18)**
   - Q16: Selection of Newtonsoft.Json as an independent enterprise C# benchmark.
   - Q17: Academic integrity correction: eliminating unsupported claims of "strict quarantine" or "blind evaluation".
   - Q18: Threats to external validity (sample size, C# ecosystem specificity, open-source domain limits).
6. **Category 6: The Base-Rate Fallacy, Decision Thresholds & CI/CD Deployment (Q19 – Q22)**
   - Q19: Mathematical derivation of the Base-Rate Fallacy: precision drops to ~10.9% at 5% defect prevalence.
   - Q20: Economic justification for operational threshold $\tau^*=0.40$ (prioritizing recall over false alarm reduction).
   - Q21: Enterprise CI/CD pull request gate integration via GitHub Actions.
   - Q22: Strategic roadmap for future research (GNN AST graph embeddings, multi-language expansion).

---

## 7. Executive Summary PDF Verification

The executive defense summary [`METHODOLOGY_AND_RESULTS_SUMMARY.pdf`](METHODOLOGY_AND_RESULTS_SUMMARY.pdf) was compiled via ReportLab.

- **Strict Single-Page Enforcement:** Compiled with `NumberedCanvas` asserting `len(_saved_page_states) == 1`. Document build halts with a fatal exception if page count deviates from 1.
- **Physical Page Dimensions:** European standard A4 (`595.27 x 841.89 pt`).
- **Page Verification:** Binary structural search confirmed exactly 1 page object.
- **Content Density & Layout:**
  - Header banner with academic branding and dark navy accent line.
  - Section 1: System Architecture & Static Extraction (Roslyn CLI, 26 metrics, 5 structural families).
  - Section 2: Empirical Corpus & Labeling Rigor (Dataset #2 $N=578$, Newtonsoft holdout $N=159$, SZZ, OWA).
  - Section 3: Experimental Performance Matrix (Complete cross-validation and holdout table across both thresholds).
  - Section 4: Out-of-Fold Confusion Matrix ($\tau^*=0.40$: $TP=244, FP=136, FN=35, TN=163$).
  - Section 5: Holdout Confusion Matrix ($\tau^*=0.40$: $TP=71, FP=31, FN=8, TN=49$).
  - Section 6: Base-Rate Fallacy in Production (Bayes' Theorem derivation yielding ~10.9% precision at 5% prevalence).
  - Section 7: Champion Model Specification (`RandomForestClassifier`, $max\_depth=8$, balanced weights).
  - Section 8: Academic Threats & Methodological Disclosures (Selection bias, temporal asymmetry, post-freeze evaluation).

---

## 8. Authoritative Numerical Parity Audit

The table below reconciles all empirical facts and figures cited across the six defense package deliverables against the authoritative experimental artifacts.

| Metric / Parameter | Authoritative Experiment Artifact | PPTX Deck | Speaker Notes | Demo Script | Defense Q&A | PDF Summary | Parity Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dataset #2 Total Methods** | 578 | 578 | 578 | 578 | 578 | 578 | **100% MATCH** |
| **Dataset #2 Defect-Prone (1)** | 279 | 279 | 279 | 279 | 279 | 279 | **100% MATCH** |
| **Dataset #2 Candidate-Clean (0)** | 299 | 299 | 299 | 299 | 299 | 299 | **100% MATCH** |
| **Dataset #2 Project Count** | 5 Repositories | 5 | 5 | 5 | 5 | 5 | **100% MATCH** |
| **Humanizer Method Count** | 291 | 291 | 291 | 291 | 291 | 291 | **100% MATCH** |
| **Serilog Method Count** | 134 | 134 | 134 | 134 | 134 | 134 | **100% MATCH** |
| **MediatR Method Count** | 91 | 91 | 91 | 91 | 91 | 91 | **100% MATCH** |
| **Polly Method Count** | 34 | 34 | 34 | 34 | 34 | 34 | **100% MATCH** |
| **FluentValidation Method Count** | 28 | 28 | 28 | 28 | 28 | 28 | **100% MATCH** |
| **Holdout (Newtonsoft) Total** | 159 | 159 | 159 | 159 | 159 | 159 | **100% MATCH** |
| **Holdout Defect-Prone (1)** | 79 | 79 | 79 | 79 | 79 | 79 | **100% MATCH** |
| **Holdout Candidate-Clean (0)** | 80 | 80 | 80 | 80 | 80 | 80 | **100% MATCH** |
| **Total Labeled Corpus** | 737 | 737 | 737 | 737 | 737 | 737 | **100% MATCH** |
| **Static Code Metrics** | 26 | 26 | 26 | 26 | 26 | 26 | **100% MATCH** |
| **CV Accuracy ($\tau=0.50$)** | 67.34% ± 4.91% | 67.34% | 67.34% | 67.34% | 67.34% | 67.34% | **100% MATCH** |
| **CV Precision ($\tau=0.50$)** | 68.24% ± 12.02% | 68.24% | 68.24% | 68.24% | 68.24% | 68.24% | **100% MATCH** |
| **CV Recall ($\tau=0.50$)** | 74.03% ± 15.57% | 74.03% | 74.03% | 74.03% | 74.03% | 74.03% | **100% MATCH** |
| **CV F1-Score ($\tau=0.50$)** | 0.6859 ± 0.0247 | 0.6859 | 0.6859 | 0.6859 | 0.6859 | 0.6859 | **100% MATCH** |
| **CV ROC-AUC** | 0.7025 | 0.7025 | 0.7025 | 0.7025 | 0.7025 | 0.7025 | **100% MATCH** |
| **CV Brier Score** | 0.2144 ± 0.0396 | 0.2144 | 0.2144 | 0.2144 | 0.2144 | 0.2144 | **100% MATCH** |
| **Pooled OOF F1 ($\tau^*=0.40$)** | 0.7405 | 0.7405 | 0.7405 | 0.7405 | 0.7405 | 0.7405 | **100% MATCH** |
| **Pooled OOF Recall ($\tau^*=0.40$)** | 87.46% (244/279) | 87.46% | 87.46% | 87.46% | 87.46% | 87.46% | **100% MATCH** |
| **Holdout Accuracy ($\tau^*=0.40$)** | 75.47% | 75.47% | 75.47% | 75.47% | 75.47% | 75.47% | **100% MATCH** |
| **Holdout Recall ($\tau^*=0.40$)** | 89.87% (71/79) | 89.87% | 89.87% | 89.87% | 89.87% | 89.87% | **100% MATCH** |
| **Holdout Precision ($\tau^*=0.40$)** | 69.61% | 69.61% | 69.61% | 69.61% | 69.61% | 69.61% | **100% MATCH** |
| **Holdout F1-Score ($\tau^*=0.40$)** | 0.7845 | 0.7845 | 0.7845 | 0.7845 | 0.7845 | 0.7845 | **100% MATCH** |
| **Holdout ROC-AUC** | 0.8209 | 0.8209 | 0.8209 | 0.8209 | 0.8209 | 0.8209 | **100% MATCH** |
| **Holdout Brier Score** | 0.1713 | 0.1713 | 0.1713 | 0.1713 | 0.1713 | 0.1713 | **100% MATCH** |
| **Base-Rate Fallacy Precision** | ~10.9% (at 5% prev) | ~10.9% | ~10.9% | ~10.9% | ~10.9% | ~10.9% | **100% MATCH** |
| **Automated Test Count** | 123 Passed | 123 | 123 | 123 | 123 | 123 | **100% MATCH** |

---

## 9. Protected Artifact SHA-256 Checksum Verification

All 15 protected artifacts were verified via direct cryptographic hash computation against their authoritative SHA-256 reference digests.

```text
====================================================================================================
PROTECTED ARTIFACT SHA-256 CHECKSUM VERIFICATION (15/15 MATCH - 100% BITWISE PARITY)
====================================================================================================
[MATCH] 1_Database/SQLite/bug_detection.db
        Digest: 70905a834dac297ac60a7fb91ad7b2909690734447519e8dbd41b29cad029893
[MATCH] 1_Database/SQLite/csharp_prediction.db
        Digest: fc9cb12161aa76533e1217e56d52121592c5e717e629aeda1c26db5aa4d8b5c8
[MATCH] 1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv
        Digest: 07c76b5da44aff71e88db494f45fda608c8a29f603775796935d4e57617d5437
[MATCH] 1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0_metadata.json
        Digest: 74cfa29d558d7cce30d32470860cdd92c5eb0587892bdf25d3ac6f542d5a2864
[MATCH] 1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv
        Digest: 7fad0ecc1d2e285f8284c54b68d5dd6841a5a821bbff05d4a897d5f705533a6e
[MATCH] 1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0_metadata.json
        Digest: 0a50cad08c44ec6b940b5ec5eb7c7cb9eb5723820fe37bc031b2da102a3c1297
[MATCH] 4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib
        Digest: e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f
[MATCH] 4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib
        Digest: 625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e
[MATCH] 3_TestResults/CrossValidation/experiment_results.json
        Digest: 6be0bd4b8d6cd287c7b47c7f1e28a5b7fb47ab8459a4e0758f20a82cd0042fde
[MATCH] 3_TestResults/CrossValidation/experiment_results.csv
        Digest: 5c48f5370007def1ff0cd0b59e2d5cc2156394661fac6c6f0211061d0e2768a5
[MATCH] 3_TestResults/CrossValidation/experiment_report.md
        Digest: 2d4d635e14a811037a00e11157c8f6b4ae14453211be0d6df8f4b14e8808a8a8
[MATCH] 3_TestResults/AuditReports/dataset_integrity_audit.json
        Digest: f9a0e6db1ed6fa5deab2f47ed7556bb4b5b4421fae6fe814cfbd386a33858c4d
[MATCH] 3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json
        Digest: db70d04898dd1c89be906ffea9fe93fafdc5b62a27fa40e51c7a0c569661deb0
[MATCH] 3_TestResults/AuditReports/fluentvalidation_pilot_results.json
        Digest: 5c69583f79ba43c69169b189da09c5091e331fef95f38d3fa4f795fc10c39a68
[MATCH] 3_TestResults/AuditReports/fluentvalidation_pilot_v2_corrected.json
        Digest: 7cda63d8b8094ab7aac5003abf3f5b5791f41a314a0e200a8b1fc88e659833a3
====================================================================================================
FINAL OUTCOME: 15/15 MATCHES (100.0% CRYPTOGRAPHIC INTEGRITY CONFIRMED)
====================================================================================================
```

---

## 10. Automated Test Suite & Code Quality Audit

1. **Automated Regression Suite (`pytest`):**
   - Execution command: `pytest 2_SourceCode/Tests`
   - Results: **123 passed in 4.52s** (100% pass rate, 0 failures, 0 errors, 0 skipped).
   - Coverage: Verifies preprocessing, feature alignment, GroupKFold splitting, predictor initialization, AST Roslyn parsing, database CRUD operations, and Streamlit session state management.
2. **Roslyn Static Code Analyzer (`dotnet build`):**
   - Target framework: `.NET 8.0`.
   - Build outcome: **0 Errors, 0 Warnings**.
   - Binary location: `4_AppBuild/Assets/Analyzer/MetricsAnalyzer.exe`.
3. **Markdown Link Integrity:**
   - 55 internal and relative links verified across documentation files.
   - Result: **0 broken links**.

---

## 11. Final Academic Readiness Sign-Off

The defense package in [`5_Documentation/09_Defense/`](./) is verified as complete, scientifically rigorous, and fully defense-ready.

- All claims conform to empirical evidence.
- No unsupported claims of "blind evaluation" or "defect-free code" remain.
- The 15-slide deck, 14.5-minute speaker script, live demonstration protocol, defense Q&A handbook, and 1-page summary PDF form a cohesive, professional university examination package.

**Quality Determination: SIGNED OFF & APPROVED FOR UNIVERSITY EXAMINATION DEFENSE.**
