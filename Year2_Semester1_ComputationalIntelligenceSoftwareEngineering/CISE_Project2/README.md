# CISE Project — Machine Learning-Based C# Source-Code Bug Detection System (`v5.0.0`)

A modular, Roslyn-backed **C# Source-Code Bug Detection System** that analyzes `.cs` source files at the method level and uses a trained `scikit-learn` **`RandomForestClassifier`** to classify individual methods as **`BUG`**, **`CLEAN`**, or **`UNCERTAIN`** (and explicitly **`ANALYSIS_ERROR`** on syntax-broken input).

> **Note on Legacy Artifacts:** Prior `v1`–`v4` defect-proneness / SZZ files are isolated in `0_LegacyArchive_v1_v4/` and never mixed with `v5.0.0`.

## Key Measured Results (`v5.0.0`)

- **Validated Dataset (`csharp_bug_detection_v5.0.0`):** `5,275` methods (`2,264` `BUG` / `3,011` `CLEAN`) across `637` repositories (`536` Microsoft InferredBugs, `56` GitHub bug-fix repos, `45` hard-negative repos), after rejecting `6,755` noisy, refactoring, duplicate, or cross-label conflicting records.
- **Champion Model (`rf_I_v5.0.0_20261126_150933`):** Experiment `I` (`536` features across Lexical, AST, Control-Flow, Data-Flow, and Supplementary Structural groups; thresholds `0.440 / 0.470 / 0.541`):
  - **Independent Test (`1,132` methods, `137` unseen repos):** Accuracy `0.5433`, Precision `0.5028`, Recall `0.6833`, F1 `0.5793`, ROC-AUC `0.5848`, PR-AUC `0.5586` (vs. `0.5012` PR-AUC for structural metrics alone).
  - **Hard-Negative Holdout (`233` complex verified-correct methods, `12` unseen repos):** Binary Specificity `85.41%` (`14.59%` FPR), 3-way Selective FPR **`0.00%`** (`143` `CLEAN`, `90` `UNCERTAIN`, `0` confident `BUG` false positives).
  - **Verification:** `.NET 9.0` Roslyn Release build (`0` warnings/errors) + `19/19` automated `pytest` tests passed (including headless Streamlit `AppTest` across all 6 pages).

## Quick Start

```bash
# 1. Build C# Roslyn Preprocessor
dotnet build 2_SourceCode/RoslynPreprocessor/RoslynPreprocessor.csproj -c Release

# 2. Run automated tests
.venv/bin/pytest 2_SourceCode/Tests/ -v

# 3. Detect bugs in a C# file from CLI
PYTHONPATH=2_SourceCode .venv/bin/python -m bug_detector detect 2_SourceCode/Tests/fixtures/verified_buggy.cs

# 4. Launch minimal 6-page Streamlit GUI
.venv/bin/streamlit run app.py
```

## Documentation Index

- [Executive Summary](SUMMARY_DOC.md)
- [Final Implementation & Validation Report](FINAL_IMPLEMENTATION_REPORT.md)
- [System Architecture](5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md)
- [Dataset Methodology](5_Documentation/02_Dataset/DATASET_METHODOLOGY.md) & [Data Collection Guide](5_Documentation/02_Dataset/DATA_COLLECTION_GUIDE.md)
- [Preprocessing & Feature Engineering](5_Documentation/03_PreprocessingAndFeatures/PREPROCESSING_AND_FEATURES.md)
- [ML Methodology & Training Guide](5_Documentation/04_MachineLearning/ML_METHODOLOGY_AND_TRAINING_GUIDE.md)
- [Experimental Results & Limitations](5_Documentation/05_Evaluation/EXPERIMENTAL_RESULTS_AND_LIMITATIONS.md)
- [Database Architecture](5_Documentation/06_Database/DATABASE_ARCHITECTURE.md), [DB Schema](1_Database/Schema/database_schema_v5.md), & [Dataset Schema](1_Database/Schema/dataset_schema_v5.md)
- [Installation & Config](5_Documentation/07_UserAndDeveloperGuide/INSTALLATION_AND_CONFIG.md), [User Guide](5_Documentation/07_UserAndDeveloperGuide/USER_GUIDE.md), & [Testing Guide](5_Documentation/07_UserAndDeveloperGuide/TESTING_GUIDE.md)
- [Academic Research Report](5_Documentation/08_AcademicReport/ACADEMIC_RESEARCH_REPORT.md)
- [Presentation Slides (`6_Presentation/`)](6_Presentation/01_ProjectOverview.md)
