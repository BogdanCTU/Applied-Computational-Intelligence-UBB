# Project Summary — CISE Bug Detector (`v5.0.0`)

## Objective
Redesign the CISE project from scratch into a method-level **Machine Learning-Based C# Source-Code Bug Detection System** classifying methods into `BUG`, `CLEAN`, or `UNCERTAIN` using a `RandomForestClassifier` trained on real defective and fixed source code.

## Implemented System
1. **Roslyn C# Preprocessor (`2_SourceCode/RoslynPreprocessor/`):** `.NET 9.0` analyzer supporting classes, structs, records, nested types, constructors, static/generic/async/expression-bodied/overloaded methods, controlled normalization, tokenization, AST, `AnalyzeControlFlow`, `AnalyzeDataFlow`, and supplementary structural metrics over a persistent batch JSONL bridge.
2. **Validated Multi-Source Dataset (`v5.0.0`):** `5,275` valid methods (`2,264` `BUG`, `3,011` `CLEAN`) across `637` repositories combining Microsoft `InferredBugs` (`2,751` retained), verified GitHub bug-fix commits (`1,768` retained), and unit-test-backed complex hard negatives (`756` retained), with `6,755` exclusions logged in SQLite (`1_Database/SQLite/bug_detector_v5.db`) and `dataset_audit_report_v5.0.0.json`.
3. **ML Pipeline & Evaluation (`2_SourceCode/bug_detector/ml/`):** Zero-leakage repository-grouped `5×3` nested CV, Experiments `A`–`I`, leave-one-group-out ablation, secondary baselines (`ExtraTrees`, `HistGradientBoosting`, `LogisticRegression`), OOF-calibrated 3-way thresholding (`0.440 / 0.470 / 0.541`), held-out permutation importance, and Saabas tree-path local evidence.
4. **CLI & Minimal 6-Page Streamlit GUI (`app.py`, `2_SourceCode/gui/`):** Full command-line and interactive interfaces for Dashboard, Manual Detection, Results, Dataset Explorer, Model Training, and Model Configuration.
5. **Verification:** `dotnet build -c Release` (`0` warnings/errors), `19/19` `pytest` tests passing (including headless Streamlit `AppTest`), and verified CLI predictions on buggy, fixed, hard-negative, and syntax-broken C# fixtures.

See [FINAL_IMPLEMENTATION_REPORT.md](FINAL_IMPLEMENTATION_REPORT.md) for full experimental answers and acceptance verification.
