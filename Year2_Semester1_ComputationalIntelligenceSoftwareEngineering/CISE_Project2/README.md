# Machine Learning-Based C# Bug Detection Classifier (v4.0.0)

**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Programme:** Applied Computational Intelligence, Master's Degree  
**Course:** Computational Intelligence in Software Engineering (CISE), Project 2  

> **Scope Disclaimer:** This system is a **static Machine Learning-Based C# Bug Detection Classifier** trained on historical Git bug-fix commits and SZZ blame mappings across public C# repositories. It is **not** a formally verified bug prover; **`BUG`** (`BUG DETECTED`) verdicts indicate statistical similarity to historically defective classes supported by static AST evidence, while **`CLEAN`** verdicts indicate no defect was detected by the classifier under the Open-World Assumption.

---

## Executive Summary

Version `4.0.0` transforms the project into a **Top-200 star-ranked public C# repository static bug detection classifier** with explicit **`BUG` / `CLEAN`** verdicts, multi-class `.cs` file aggregation (refusing to classify syntax-broken or incomplete files as `CLEAN`), and strictly provenance-separated bug localization:

- **Top-200 Empirical Corpus (`csharp_class_top200_v4` v4.0.0):** `9,588` production C# class/struct/record observations (**`4,425` BUG** / `46.15%`, **`5,163` CLEAN** / `53.85%`) mined across **`200` distinct public C# GitHub repositories** ranked by GitHub stars descending (`4,409` to `121,429` stars; `500` discovered, `367` eligible candidates, `179` documented exclusions, `0` collection failures; SHA-256: `c7ff8436b3d9beae096df413985bf128095fc6b25cad0239cb27b452f07226c2`).
- **Provenance-Aware SZZ & ML Method Localization:**
  - SZZ history (`git blame -w -M -C`) maps pre-fix bug-fix diffs to enclosing classes, enclosing methods, source revisions, and contiguous line ranges (`7,361` verified historical localization records in `class_bug_localizations`).
  - A separately validated **ML Method Localizer** (`method_localizer_top200_v4.joblib`, 26 method Roslyn features, `67,556` method observations across SZZ-localized BUG classes) ranks suspicious methods on unseen `BUG` classes (`Top-1 = 44.99%`, `Top-3 = 68.64%`, `ROC-AUC = 0.6611` on independent holdout), while **exact buggy line localization on unseen code is explicitly marked `unavailable`**.
- **Strict Zero-Leakage Validation Protocol:** Partitioned strictly by repository into **`160` Development repositories** (`7,546` classes: `3,414` BUG, `4,132` CLEAN) and **`40` untouched Independent Holdout repositories** (`2,042` classes: `1,011` BUG, `1,031` CLEAN). Evaluated 12 configurations across all 7 ML families (`DummyClassifier`, `LogisticRegression`, `DecisionTreeClassifier`, `RandomForestClassifier`, `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, `CalibratedClassifierCV`) using **5×4 Nested GroupKFold** with threshold selection strictly inside inner CV folds (`select_classifier_threshold`).
- **Headline Champion Result (`class_bug_classifier_top200_v4` = `rf_depth12_leaf4_log2_all40`, inner-CV threshold $\tau = 0.520$):**
  - **Nested CV OOF (160 dev repos, 7,546 classes):** Precision = **`77.66%`** (outer mean `77.58% ± 2.49%`), Recall = `66.99%`, F1 = `71.93%`, ROC-AUC = `0.8330`, PR-AUC = `0.8102`, FPR = `15.92%`, FNR = `33.01%`.
  - **Untouched 40-Repo Holdout (2,042 classes):** **Precision = `79.47%`**, **Recall = `62.02%`** (`627 / 1,011`), **F1 = `69.67%`**, **ROC-AUC = `0.8180`**, **PR-AUC = `0.8104`**, **FPR = `15.71%`**, **FNR = `37.98%`** (`CM = [[869, 162], [384, 627]]`).
  - Exceeds the **`>= 75%` independent holdout precision target** while maintaining balanced recall (`62.02%`) and strictly beating the `DummyClassifier` baseline (`51.93%` precision, `0.5221` ROC-AUC).

---

## Independent Holdout Model Comparison (`3_TestResults/Top200ClassifierOptimization/`)

| Model Family | Config ID | Threshold ($\tau$, Inner CV) | Nested OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | Holdout ROC-AUC | Holdout FPR / FNR |
|---|---|---:|---|---:|---:|---:|---:|---|
| **Random Forest (Champion)** | `rf_depth12_leaf4_log2_all40` | `0.52` | **77.66%** / **66.99%** / **71.93%** | **79.47%** | **62.02%** | **69.67%** | 0.8180 | 15.71% / **37.98%** |
| Random Forest (Pruned 30) | `rf_depth12_leaf4_corr_pruned` | `0.54` | 77.96% / 66.20% / 71.60% | 80.83% | 60.04% | 68.90% | 0.8186 | 13.97% / 39.96% |
| Calibrated Ensemble (Sigmoid) | `calibrated_rf_sigmoid` | `0.54` | 77.77% / 66.49% / 71.69% | 81.05% | 59.64% | 68.72% | 0.8182 | 13.68% / 40.36% |
| HistGradientBoosting (Balanced) | `hgb_depth5_leaf20_l2_2` | `0.58` | 77.90% / 64.41% / 70.51% | 81.84% | 58.85% | 68.47% | 0.8202 | 12.80% / 41.15% |
| Random Forest (Unweighted) | `rf_depth14_leaf3_sqrt_unweighted` | `0.52` | 78.05% / 66.05% / 71.55% | 81.32% | 58.56% | 68.09% | 0.8168 | 13.19% / 41.44% |
| HistGradientBoosting (Unweighted) | `hgb_depth4_leaf15_unweighted` | `0.54` | 77.87% / 65.23% / 70.99% | 81.84% | 57.07% | 67.25% | **0.8215** | 12.42% / 42.93% |
| Decision Tree | `dt_depth6_leaf12_bal` | `0.64` | 78.23% / 60.31% / 68.11% | 81.56% | 56.87% | 67.02% | 0.7951 | 12.61% / 43.13% |
| Extra Trees (Balanced) | `et_depth12_leaf4_log2_bal` | `0.54` | 78.24% / 64.24% / 70.55% | 79.17% | 56.78% | 66.13% | 0.8103 | 14.65% / 43.22% |
| Logistic Regression (Robust L2) | `lr_robust_l2_c02` | `0.50` | 77.91% / 63.21% / 69.79% | 81.82% | 55.19% | 65.92% | 0.8051 | 12.03% / 44.81% |
| Extra Trees (Depth 14) | `et_depth14_leaf5_sqrt` | `0.52` | 77.82% / 64.44% / 70.50% | 80.49% | 55.09% | 65.41% | 0.8115 | 13.09% / 44.91% |
| Logistic Regression (Std L2) | `lr_std_l2_c01_bal` | `0.56` | 78.24% / 62.57% / 69.53% | **81.89%** | 54.10% | 65.16% | 0.8041 | **11.74%** / 45.90% |
| DummyClassifier (Stratified) | `dummy_stratified` | `0.30` | 45.57% / 46.10% / 45.84% | 51.93% | 47.97% | 49.87% | 0.5221 | 43.55% / 52.03% |

---

## System Quick Start

### 1. Build the Roslyn Static Analyzer (.NET 9.0)
```bash
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release
```

### 2. Launch the C# Bug Detection Classifier Web Application
```bash
.venv/bin/streamlit run 2_SourceCode/Python/app.py
```
Supports **Paste C# Class/Struct/Record**, **Upload Complete `.cs` File** (multi-class analysis reporting per-class `BUG DETECTED` / `CLEAN` verdicts, file summary counts, and `ANALYSIS INCOMPLETE` when syntax/parse failures occur), **Verified Historical SZZ vs. ML Suspicious Method Localization**, and **Legacy Method Diagnostic Mode**.

### 3. Re-Run Top-200 Collection or Classifier Optimization
```bash
.venv/bin/python 2_SourceCode/Scripts/run_top200_csharp_pipeline.py --target-repos 200 --max-discover 500 --max-commits 250
.venv/bin/python 2_SourceCode/Scripts/run_top200_classifier_optimization.py
```

### 4. Run Automated Tests
```bash
.venv/bin/pytest 2_SourceCode/Tests/ -v
```

---

## Project Documentation Map

- [Executive Summary](SUMMARY_DOC.md)
- [System Architecture](5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md)
- [Database Schema](1_Database/Schema/database_schema.md) & [Database Architecture](5_Documentation/02_Database/DATABASE_ARCHITECTURE.md)
- [Dataset Schema](1_Database/Schema/dataset_schema.md)
- [Source Code Guide](5_Documentation/03_SourceCode/SOURCE_CODE_GUIDE.md)
- [ML Methodology](5_Documentation/04_MachineLearning/PROJECT_METHODOLOGY.md) & [Experimental Results](5_Documentation/04_MachineLearning/EXPERIMENTAL_RESULTS.md)
- [Validation & Limitations](5_Documentation/05_Validation/VALIDATION_AND_LIMITATIONS.md)
- [User Guide](5_Documentation/06_UserGuide/USER_GUIDE.md)
- [Academic Final Report](5_Documentation/07_AcademicReport/FINAL_REPORT.md)
- [Presentation Slides (`6_Presentation/`)](6_Presentation/01_ProjectOverview.md)
- [Archived Method-Level Artifacts](5_Documentation/08_Archive/README.md) & [Defense Validation](5_Documentation/09_Defense/DEFENSE_PACKAGE_VALIDATION.md)
