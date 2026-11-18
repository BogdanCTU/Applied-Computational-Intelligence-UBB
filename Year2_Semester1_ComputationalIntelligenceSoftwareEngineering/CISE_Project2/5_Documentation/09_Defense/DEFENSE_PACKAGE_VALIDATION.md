# CISE Project 2 — Defense Package Validation Report

**Master's Programme:** Applied Computational Intelligence  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code (CISE Project 2)  
**Date:** November 2026  

---

## 1. Defense Package Inventory

The table below lists the defense materials in [`5_Documentation/09_Defense/`](./) and [`6_Presentation/`](../../6_Presentation/):

| File | Format | Purpose | Status |
| :--- | :---: | :--- | :---: |
| [`FINAL_DEFENSE_PRESENTATION.pptx`](FINAL_DEFENSE_PRESENTATION.pptx) | PPTX (16:9) | 15-slide widescreen presentation deck | Verified |
| [`FINAL_DEFENSE_SPEAKER_NOTES.docx`](FINAL_DEFENSE_SPEAKER_NOTES.docx) | DOCX | Slide-by-slide speaker script (~14.5 minutes) | Verified |
| [`LIVE_DEMO_SCRIPT.docx`](LIVE_DEMO_SCRIPT.docx) | DOCX | 7-stage live application walkthrough and contingency steps | Verified |
| [`DEFENSE_QUESTIONS_AND_ANSWERS.docx`](DEFENSE_QUESTIONS_AND_ANSWERS.docx) | DOCX | 22 defense questions and technical answers | Verified |
| [`METHODOLOGY_AND_RESULTS_SUMMARY.pdf`](METHODOLOGY_AND_RESULTS_SUMMARY.pdf) | PDF (A4) | Single-page executive summary | Verified (1 page) |
| [`6_Presentation/01`–`07`](../../6_Presentation/) | Markdown | 7 defense presentation decks updated with nested optimization results | Updated |
| [`DEFENSE_PACKAGE_VALIDATION.md`](DEFENSE_PACKAGE_VALIDATION.md) | Markdown | Package inventory and authoritative numerical reference | Current document |

---

## 2. Presentation Slide Structure

| Slide | Title | Core Content | Allocated Time |
| :---: | :--- | :--- | :---: |
| 1 | Title & University Identity | Project title, programme, and institution metadata | 00:45 |
| 2 | Research Problem & Context | Method-level vs. file-level defect prediction; maintenance prioritization | 01:00 |
| 3 | Static Code Analysis Pipeline | .NET 9.0 Roslyn AST analyzer and 26 static code metrics | 01:00 |
| 4 | Empirical Corpus Architecture | Dataset #2 (578 methods, 5 repos) and historical holdout (`Newtonsoft.Json`, 159 methods) | 01:00 |
| 5 | Ground-Truth Attribution & Labeling | SZZ `git blame` tracing, Open-World Assumption (candidate-clean vs. defect-prone), production filtering | 01:00 |
| 6 | Validation: Nested GroupKFold by Repository | 5-Fold outer `GroupKFold` and 4-fold inner `GroupKFold` repository separation | 01:00 |
| 7 | Baseline vs. Optimized Tree Ensembles | Baseline RF (`rf_compact_regularized`), Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`), and Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) | 01:00 |
| 8 | Decision Threshold Selection & Brier Score | Inner-fold threshold selection ($\tau_{\text{inner}}^*$) vs. unnested $\tau^*=0.40$; Brier prediction error vs. `CalibratedClassifierCV` | 01:15 |
| 9 | Nested Cross-Validation & Historical Holdout Results | Nested CV gains (`ROC-AUC 0.7349`, `Pooled F1 0.7653`) and historical baseline holdout on `Newtonsoft.Json` (`F1 0.7845`, `ROC-AUC 0.8209`) | 01:00 |
| 10 | Base-Rate Fallacy in Production | Bayesian precision (~10.9%) at 5% defect prevalence | 01:15 |
| 11 | Feature Analysis & Collinearity | Collinear size cluster ($|\rho| \ge 0.85$), MDI vs. held-out permutation importance, and `max_features='log2'` | 01:00 |
| 12 | Application Architecture & Demo | Streamlit workbench, SQLite persistence, deployed model bundles, and threshold configuration ($\tau=0.50$ binary / `0.30`–`0.60` risk bands) | 00:45 |
| 13 | Software Verification | 123 `pytest` tests passing, .NET 9.0 Roslyn build, and artifact checksum verification | 00:45 |
| 14 | Methodological Limitations | 5-repository sample size, repository size skew, semantic defect boundary (`18/23` FNs have `loc <= 12`), and need for a new unseen holdout repository | 01:00 |
| 15 | Conclusions & Future Work | Summary of empirical findings and future research directions | 00:45 |
| **Total** | **15 Slides** | — | **14:30** |

---

## 3. Live Demonstration Stages

| Stage | Page / Component | Action |
| :---: | :--- | :--- |
| 1 | Application Launch | Run `python -m streamlit run app.py` and verify SQLite (`1_Database/SQLite/bug_detection.db`) and Roslyn (`2_SourceCode/RoslynAnalyzer/bin/Release/net9.0/RoslynAnalyzer.dll`). |
| 2 | Dashboard | Inspect workspace summary counts, observation distribution, lifecycle pipeline, and methodological constraints. |
| 3 | Dataset Management | Inspect Dataset #2 ($N=578$, 279 defect-prone, 299 candidate-clean) and metric distributions. |
| 4 | Model Evaluation | Compare `et_nested_opt_v3_depth6_leaf6_log2`, `rf_nested_opt_v3_depth6_leaf8_log2`, and preserved `exp_final_5fold_v2_best_rf_compact_regularized`. |
| 5 | Defect Prediction (Single Method) | Analyze sample C# methods and inspect predicted risk scores (`predict_proba()`), risk categories (`<=0.30`, `0.31–0.60`, `>0.60`), and binary class ($\tau=0.50$). |
| 6 | Metric Attribution | Review the influential metrics table and full 26 Roslyn metrics for analyzed methods. |
| 7 | Prediction History & Settings | Inspect local SQLite prediction history and privacy settings. |

---

## 4. Authoritative Numerical Reference Table

| Metric / Parameter | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) |
| :--- | :---: | :---: | :---: |
| Dataset #2 Observations / Repositories | 578 (279 pos / 299 clean, 5 repos) | 578 (279 pos / 299 clean, 5 repos) | 578 (279 pos / 299 clean, 5 repos) |
| Estimator / Trees / Max Depth | `RandomForestClassifier` / 100 / 8 | `RandomForestClassifier` / 200 / 6 | `ExtraTreesClassifier` / 200 / 6 |
| Min Split / Min Leaf / Max Features | 5 / 4 / `sqrt` | 10 / 8 / `log2` | 8 / 6 / `log2` |
| Outer 5-Fold ROC-AUC (Mean ± Std) | 0.7037 ± 0.1292 (hist: 0.7025) | 0.7216 ± 0.1156 | 0.7349 ± 0.0703 |
| Outer 5-Fold PR-AUC (Mean ± Std) | 0.6405 ± 0.1135 (hist: 0.6401) | 0.6465 ± 0.1026 | 0.6443 ± 0.0496 |
| Outer 5-Fold Brier (Mean ± Std) | 0.2146 ± 0.0398 (hist: 0.2144) | 0.2055 ± 0.0374 | 0.2062 ± 0.0213 |
| Outer 5-Fold F1 at $\tau=0.50$ | 0.6879 ± 0.0243 (hist: 0.6859) | 0.7517 ± 0.0709 | 0.6867 ± 0.1394 |
| Outer 5-Fold F1 at Nested $\tau_{\text{inner}}^*$ | 0.7408 ± 0.0760 | 0.7539 ± 0.0706 | 0.7667 ± 0.0723 |
| Pooled OOF ROC-AUC / Brier | 0.7034 / 0.2109 | 0.7119 / 0.2043 | 0.7470 / 0.2008 |
| Pooled OOF F1 at Nested $\tau_{\text{inner}}^*$ | 0.7294 (unnested $\tau^*=0.40$: 0.7405) | 0.7406 | 0.7653 |
| Pooled OOF Recall at Nested $\tau_{\text{inner}}^*$ | 88.89% (248/279) | 88.53% (247/279) | 91.76% (256/279) |
| Pooled OOF Precision at Nested $\tau_{\text{inner}}^*$ | 61.85% | 63.66% | 65.64% |
| Pooled OOF Accuracy at Nested $\tau_{\text{inner}}^*$ | 68.17% | 70.07% | 72.84% |
| Historical `Newtonsoft.Json` Holdout ($N=159$) | F1 0.7845, Recall 89.87%, Acc 75.47%, AUC 0.8209 (at $\tau^*=0.40$) | Not evaluated (holdout excluded from optimization) | Not evaluated (holdout excluded from optimization) |

---

## 5. Protected Artifact Checksums

| Artifact Path | SHA-256 Digest |
| :--- | :--- |
| `1_Database/SQLite/bug_detection.db` | `70905a834dac297ac60a7fb91ad7b2909690734447519e8dbd41b29cad029893` |
| `4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib` | `e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f` |
| `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` | `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e` |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` | `32398813679af7715398ab50b15d15741b9aa28426aa581284855b05cb9ab527` |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` | `30b63239417ff2aa0900de6c1566a6919a703d512b48652062fddc05a8b15a56` |
| `3_TestResults/CrossValidation/experiment_results.json` | `8e5e46321fefcdae2aaedb9a8c180ed989cde99edf76636d87cb4dc5c7639d0a` |
| `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json` | `1c8682b75e5b75c3881681ec1bf56b9fe6b4c560d5f4e980fc9a2efeb78bbd22` |
