# CISE Project 2 — Defense Package Validation Report

**Master's Programme:** Applied Computational Intelligence  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code (CISE Project 2)  
**Date:** November 2026  

---

## 1. Defense Package Inventory

The table below lists the defense materials in [`5_Documentation/09_Defense/`](./):

| File | Format | Purpose | Status |
| :--- | :---: | :--- | :---: |
| [`FINAL_DEFENSE_PRESENTATION.pptx`](FINAL_DEFENSE_PRESENTATION.pptx) | PPTX (16:9) | 15-slide widescreen presentation deck | Verified (15 slides) |
| [`FINAL_DEFENSE_SPEAKER_NOTES.docx`](FINAL_DEFENSE_SPEAKER_NOTES.docx) | DOCX | Slide-by-slide speaker script (~14.5 minutes) | Verified |
| [`LIVE_DEMO_SCRIPT.docx`](LIVE_DEMO_SCRIPT.docx) | DOCX | 7-stage live application walkthrough and contingency steps | Verified |
| [`DEFENSE_QUESTIONS_AND_ANSWERS.docx`](DEFENSE_QUESTIONS_AND_ANSWERS.docx) | DOCX | 22 defense questions and technical answers | Verified |
| [`METHODOLOGY_AND_RESULTS_SUMMARY.pdf`](METHODOLOGY_AND_RESULTS_SUMMARY.pdf) | PDF (A4) | Single-page executive summary | Verified (1 page) |
| [`DEFENSE_PACKAGE_VALIDATION.md`](DEFENSE_PACKAGE_VALIDATION.md) | Markdown | Package inventory and numerical parity verification | Current document |

---

## 2. Presentation Slide Structure (`FINAL_DEFENSE_PRESENTATION.pptx`)

| Slide | Title | Core Content | Allocated Time |
| :---: | :--- | :--- | :---: |
| 1 | Title & University Identity | Project title, programme, and institution metadata | 00:45 |
| 2 | Research Problem & Context | Method-level vs. file-level defect prediction; maintenance prioritization | 01:00 |
| 3 | Static Code Analysis Pipeline | .NET 9.0 Roslyn AST analyzer and 26 static code metrics | 01:00 |
| 4 | Empirical Corpus Architecture | Dataset #2 (578 methods, 5 repos) and independent holdout (`Newtonsoft.Json`, 159 methods) | 01:00 |
| 5 | Ground-Truth Attribution & Labeling | SZZ `git blame` tracing, Open-World Assumption (candidate-clean vs. defect-prone), production filtering | 01:00 |
| 6 | Validation: GroupKFold by Repository | 5-Fold `GroupKFold` repository separation and fold variance | 01:00 |
| 7 | Regularized Random Forest Model | `rf_compact_regularized` (`n_estimators=100`, `max_depth=8`, `min_samples_leaf=4`, balanced weights) | 01:00 |
| 8 | Decision Threshold Tuning | Nominal $\tau=0.50$ vs. tuned $\tau^*=0.40$ on pooled out-of-fold predictions; threshold selection bias | 01:15 |
| 9 | Independent Holdout Evaluation | `Newtonsoft.Json` results: Accuracy 75.47%, Recall 89.87%, Precision 69.61%, F1 0.7845, ROC-AUC 0.8209 | 01:00 |
| 10 | Base-Rate Fallacy in Production | Bayesian precision (~10.9%) at 5% defect prevalence | 01:15 |
| 11 | Feature Importance & Metric Attribution | MDI (Gini) and permutation importance rankings | 01:00 |
| 12 | Application Architecture & Demo | Streamlit workbench, SQLite persistence, local analysis/inference (network used only for repository collection) | 00:45 |
| 13 | Software Verification | 123 `pytest` tests passing, .NET 9.0 Roslyn build, and artifact checksum verification | 00:45 |
| 14 | Methodological Limitations | Threshold selection bias, temporal asymmetry, SZZ heuristics, and external validity scope | 01:00 |
| 15 | Conclusions & Future Work | Summary of empirical findings and future research directions | 00:45 |
| **Total** | **15 Slides** | — | **14:30** |

---

## 3. Live Demonstration Stages (`LIVE_DEMO_SCRIPT.docx`)

| Stage | Page / Component | Action |
| :---: | :--- | :--- |
| 1 | Application Launch | Run `python -m streamlit run app.py` and verify SQLite (`1_Database/SQLite/bug_detection.db`) and Roslyn (`2_SourceCode/RoslynAnalyzer/bin/Release/net9.0/RoslynAnalyzer.dll`). |
| 2 | Dashboard | Inspect workspace summary counts, observation distribution, lifecycle pipeline, and methodological constraints. |
| 3 | Dataset Management | Inspect Dataset #2 ($N=578$, 279 defect-prone, 299 candidate-clean) and metric distributions. |
| 4 | Model Evaluation | Inspect holdout metrics, confusion matrix, ROC/PR curves, and feature importance rankings. |
| 5 | Defect Prediction (Single Method) | Analyze sample C# methods and inspect predicted risk scores and risk categories. |
| 6 | Metric Attribution | Review the influential metrics table and full 26 Roslyn metrics for analyzed methods. |
| 7 | Prediction History & Settings | Inspect local SQLite prediction history and privacy settings. |

---

## 4. Numerical Parity Across Deliverables

| Metric / Parameter | Reference Value | PPTX | Speaker Notes | Demo Script | Defense Q&A | Summary PDF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Dataset #2 Total Methods | 578 | 578 | 578 | 578 | 578 | 578 |
| Dataset #2 Defect-Prone (`1`) | 279 | 279 | 279 | 279 | 279 | 279 |
| Dataset #2 Candidate-Clean (`0`) | 299 | 299 | 299 | 299 | 299 | 299 |
| Dataset #2 Repositories | 5 | 5 | 5 | 5 | 5 | 5 |
| `Humanizer` / `Serilog` / `MediatR` / `Polly` / `FluentValidation` | 291 / 134 / 91 / 34 / 28 | Match | Match | Match | Match | Match |
| Holdout (`Newtonsoft.Json`) Total | 159 (79 / 80) | Match | Match | Match | Match | Match |
| Total Evaluated Corpus | 737 | 737 | 737 | 737 | 737 | 737 |
| Roslyn Static Metrics | 26 | 26 | 26 | 26 | 26 | 26 |
| CV Fold Mean Accuracy ($\tau=0.50$) | 67.34% ± 4.91% | 67.34% | 67.34% | 67.34% | 67.34% | 67.34% |
| CV Fold Mean Precision ($\tau=0.50$) | 68.24% ± 12.02% | 68.24% | 68.24% | 68.24% | 68.24% | 68.24% |
| CV Fold Mean Recall ($\tau=0.50$) | 74.03% ± 15.57% | 74.03% | 74.03% | 74.03% | 74.03% | 74.03% |
| CV Fold Mean F1 ($\tau=0.50$) | 0.6859 ± 0.0247 | 0.6859 | 0.6859 | 0.6859 | 0.6859 | 0.6859 |
| CV ROC-AUC | 0.7025 | 0.7025 | 0.7025 | 0.7025 | 0.7025 | 0.7025 |
| CV Brier Score | 0.2144 ± 0.0396 | 0.2144 | 0.2144 | 0.2144 | 0.2144 | 0.2144 |
| Pooled OOF Accuracy / Recall / F1 ($\tau^*=0.40$) | 70.42% / 87.46% / 0.7405 | Match | Match | Match | Match | Match |
| Holdout Accuracy ($\tau^*=0.40$) | 75.47% | 75.47% | 75.47% | 75.47% | 75.47% | 75.47% |
| Holdout Precision ($\tau^*=0.40$) | 69.61% | 69.61% | 69.61% | 69.61% | 69.61% | 69.61% |
| Holdout Recall ($\tau^*=0.40$) | 89.87% (71/79) | 89.87% | 89.87% | 89.87% | 89.87% | 89.87% |
| Holdout F1 ($\tau^*=0.40$) | 0.7845 | 0.7845 | 0.7845 | 0.7845 | 0.7845 | 0.7845 |
| Holdout ROC-AUC / Brier | 0.8209 / 0.1713 | Match | Match | Match | Match | Match |
| Bayesian Precision at 5% Prevalence | ~10.9% | ~10.9% | ~10.9% | ~10.9% | ~10.9% | ~10.9% |
| Automated Tests | 123 Passed | 123 | 123 | 123 | 123 | 123 |

---

## 5. Protected Artifact Checksums

| Artifact Path | SHA-256 Digest (Binary / Platform-Consistent) |
| :--- | :--- |
| `1_Database/SQLite/bug_detection.db` | `70905a834dac297ac60a7fb91ad7b2909690734447519e8dbd41b29cad029893` |
| `4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib` | `e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f` |
| `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` | `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e` |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` | `32398813679af7715398ab50b15d15741b9aa28426aa581284855b05cb9ab527` |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` | `30b63239417ff2aa0900de6c1566a6919a703d512b48652062fddc05a8b15a56` |
| `3_TestResults/CrossValidation/experiment_results.json` | `8e5e46321fefcdae2aaedb9a8c180ed989cde99edf76636d87cb4dc5c7639d0a` |
| `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json` | `1c8682b75e5b75c3881681ec1bf56b9fe6b4c560d5f4e980fc9a2efeb78bbd22` |
