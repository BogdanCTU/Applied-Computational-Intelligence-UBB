# Machine Learning-Based Bug Detection in C# Source Code (v3.0.0)

**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Programme:** Applied Computational Intelligence, Master's Degree  
**Course:** Computational Intelligence in Software Engineering (CISE), Project 2  

> **Scope Disclaimer:** This system is a **static machine learning defect indicator** trained on historical Git bug-fix commits and SZZ blame mappings across public C# repositories. It is **not** a formally verified bug prover; flagged classes indicate elevated statistical propensity for defects under historical SZZ evidence, while unflagged code represents candidate-clean code under the Open-World Assumption.

---

## Executive Summary

Version `3.0.0` transforms the project from a 5-repository method-level prototype into a **106-repository class- and file-level C# static bug detection platform** optimized for **high precision**:

- **Empirical Corpus (`csharp_class_empirical_v3` v3.0.0):** `5,711` production C# class/struct/record observations (`2,829` defect-prone / `49.54%`, `2,882` candidate-clean / `50.46%`) mined across **`106` distinct public GitHub C# repositories** (`300` discovered, `304` candidates evaluated, `15` documented exclusions, `0` collection failures; SHA-256: `7087edb539cf44690a3b97fbd66f6cf0cd6853b320c328f4f58522561a07e70c`).
- **Granularity & Roslyn `v3.0.0` Feature Extractor:** Dedicated .NET 9.0 Roslyn CLI analyzing classes, structs, records, and multi-class `.cs` files via `--batch-stdin` NDJSON streaming. Extracts **40 isolated class-level static metrics** (strictly excluding nested types from parent metrics and enclosing line counts) while retaining full backward compatibility for the legacy **26 method-level metrics**.
- **Precision Optimization & Validation Protocol:** Partitioned strictly by repository into **`84` Development repositories** (`4,730` classes) and **`22` untouched Independent Holdout repositories** (`981` classes). All 7 required ML families (`DummyClassifier`, `LogisticRegression`, `DecisionTreeClassifier`, `RandomForestClassifier`, `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, `CalibratedClassifierCV`) were evaluated under **5x4 Nested GroupKFold** with **inner-fold precision threshold selection**.
- **Headline Champion Result (`class_precision_champion_v3` = `rf_opt_depth12_leaf4_log2`, threshold $\tau = 0.600$):**
  - **Nested CV OOF (84 dev repos):** **Precision = 82.30%** (outer mean `82.45% +/- 2.70%`), Recall = `61.71%`, F1 = `70.53%`, ROC-AUC = `0.8260`, PR-AUC = `0.8280`.
  - **Untouched 22-Repo Holdout (981 classes):** **Precision = 83.43%**, **Recall = 61.99%**, **F1 = 71.13%**, **ROC-AUC = 0.8449**, **PR-AUC = 0.8327**, **FPR = 11.00%** (`TP=287, FP=57, FN=176, TN=461`).
  - Surpasses both the **>= 75%** minimum acceptable target and the **>= 80%** preferred precision target while maintaining recall above the **>= 50%** floor.

---

## Model Benchmark Comparison (`3_TestResults/ClassModelOptimization/`)

| Rank / Model Family | Config ID | Threshold ($\tau$, Inner CV) | Nested OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | Holdout ROC-AUC |
|---|---|---:|---|---:|---:|---:|---:|
| **Random Forest (Champion)** | `rf_opt_depth12_leaf4_log2` | `0.60` | **82.30%** / 61.71% / **70.53%** | **83.43%** | **61.99%** | **71.13%** | 0.8449 |
| Random Forest (Unweighted) | `rf_opt_depth10_leaf6_unweighted` | `0.60` | 81.69% / 61.83% / 70.39% | 82.66% | 61.77% | 70.70% | 0.8460 |
| Calibrated Ensemble (Sigmoid RF) | `calibrated_rf_sigmoid` | `0.64` | 81.56% / 61.71% / 70.26% | 83.09% | 61.56% | 70.72% | **0.8478** |
| Extra Trees | `et_opt_depth10_leaf4_log2_bal` | `0.60` | 82.63% / 61.12% / 70.26% | 83.33% | 58.32% | 68.61% | 0.8368 |
| Calibrated Ensemble (Isotonic ET) | `calibrated_et_isotonic` | `0.64` | 82.11% / 60.74% / 69.83% | 83.28% | 58.10% | 68.45% | 0.8365 |
| Random Forest (Baseline) | `rf_baseline_compact` | `0.62` | 82.27% / 60.40% / 69.66% | 82.88% | 59.61% | 69.35% | 0.8428 |
| HistGradientBoosting (Unweighted) | `hgb_depth4_leaf25_unweighted` | `0.64` | 81.40% / 60.86% / 69.65% | 81.85% | 57.45% | 67.51% | **0.8502** |
| HistGradientBoosting (Balanced) | `hgb_depth5_leaf20_l2_2` | `0.66` | 82.01% / 58.20% / 68.08% | 83.06% | 54.00% | 65.45% | 0.8433 |
| Logistic Regression (Balanced L2) | `lr_std_l2_c01_bal` | `0.58` | 80.82% / 60.57% / 69.24% | 80.18% | 56.80% | 66.50% | 0.8184 |
| Decision Tree (Depth 6 Balanced) | `dt_depth6_leaf10_bal` | `0.70` | 81.61% / 53.25% / 64.45% | 84.23% | 50.76% | 63.34% | 0.7953 |
| DummyClassifier (Stratified) | `dummy_stratified` | `0.30` | 49.43% / 49.49% / 49.46% | 44.83% | 47.73% | 46.23% | 0.4761 |

---

## System Quick Start

### 1. Build the Roslyn Static Analyzer (.NET 9.0)
```bash
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release
```

### 2. Launch the Class & File Bug Detection Web Application
```bash
.venv/bin/streamlit run 2_SourceCode/Python/app.py
```
Supports **Paste C# Class/Struct/Record**, **Upload Complete `.cs` File** (multi-class analysis with file-level max/mean/flagged risk aggregation + per-class drill-down), and **Legacy Method Diagnostic Mode**.

### 3. Re-Run Class ML Optimization or Data Collection
```bash
.venv/bin/python 2_SourceCode/Scripts/run_100_repo_class_pipeline.py --target-repos 106 --max-discover 300 --max-commits 250
.venv/bin/python 2_SourceCode/Scripts/run_class_model_optimization.py
```

### 4. Run Automated Tests
```bash
.venv/bin/pytest -v
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
