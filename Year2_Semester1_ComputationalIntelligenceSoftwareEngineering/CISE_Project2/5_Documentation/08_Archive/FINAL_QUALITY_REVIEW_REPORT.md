# Final Quality Review & Repository Refinement Report

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Babeș-Bolyai University — Faculty of Mathematics and Computer Science  
**Master:** Applied Computational Intelligence (Year 2, Semester 1)  
**Course:** Computational Intelligence in Software Engineering (CISE)  
**Date:** November 2026  
**Status:** Completed & Empirically Verified  

---

## 1. Executive Summary

This report documents the controlled quality, application UI, and documentation refinement executed across the `CISE_Project2` repository. The refinement adhered strictly to non-negotiable academic and architectural constraints: zero modifications to experimental results, frozen machine learning models, database schemas, feature definitions, or training datasets.

All system modifications were non-destructive, focused on code readability, interface usability, test isolation, and academic documentation rigor.

### Key Quality Verification Results

| Dimension | Target Standard | Verification Outcome | Status |
| :--- | :--- | :--- | :---: |
| **Cryptographic Integrity** | 100% Bitwise Parity across 15 Protected Artifacts | 15/15 SHA-256 Checksums Matched | **PASS** |
| **Automated Test Suite** | 100% Passing in Fresh Process | 123/123 Tests Passed (0 Failed, 0 Skipped) | **PASS** |
| **Static Code Analyzer** | .NET 9 Release Compilation with Roslyn API | 0 Warnings, 0 Errors | **PASS** |
| **Streamlit Interface** | Clean Academic Workbench, Zero Emojis, No Pie Charts | All 8 Pages Validated; 0 Emojis, 0 Pie Charts | **PASS** |
| **Documentation Links** | Complete Internal Link Consistency | 53/53 Relative Markdown Links Valid | **PASS** |
| **Visual / Writing Standards** | Formal Academic English, Standardized Terminology | Fully Standardized Across All Active Documents | **PASS** |

---

## 2. Summary of Changes by Refinement Stage

### Stage 1 — Repository Audit & Baseline Verification
- Audited the entire repository structure (`1_Database` through `6_Presentation`).
- Calculated and recorded the cryptographic SHA-256 baseline for all 15 protected empirical artifacts.
- Identified test suite import issues and documentation discrepancies prior to modifying any source code.

### Stage 2 — Source Code & Test Suite Resolution
- **Circular Import Elimination:** Removed the eager module-level execution of `register_unpickle_aliases()` in `2_SourceCode/Python/core/settings.py`. Decoupled settings resolution from the machine learning package lifecycle.
- **Model Deserialization Hardening:** Integrated lazy unpickling alias registration inside `load_model` and `list_saved_models` in `2_SourceCode/Python/ml/model_manager.py` immediately prior to `joblib.load()`.
- **Test Isolation & Regressions:** Added two regression tests in `2_SourceCode/Tests/test_config.py` verifying alias registration idempotency and isolated import-order resilience. The test suite expanded from 121 to 123 tests, all passing in a single invocation without preloaded harnesses.
- **Roslyn Analyzer Documentation:** Added comprehensive XML documentation comments (`/// <summary>`) to public metric classes and methods in `2_SourceCode/RoslynAnalyzer/Program.cs` without altering AST extraction semantics.

### Stage 3 — Streamlit Workbench Refinement
- **Zero Emojis Policy:** Eliminated all emojis and decorative symbols from `app.py` and all 8 page modules under `2_SourceCode/Python/application/pages/` (titles, sidebar navigation, buttons, alerts, tabs, and status badges).
- **Visualization Standardization:** Replaced decorative Plotly donut charts in `dashboard.py` and `dataset_management.py` with structured tables and neutral horizontal bar charts.
- **Terminology Normalization:** Standardized prediction outputs and class labels across all UI views:
  - Binary classification: **Defect-Prone (1)** and **Candidate-Clean (0)**.
  - Risk categorization: Plain text **Low Risk**, **Medium Risk**, and **High Risk**.

### Stage 4 — Documentation & Presentation Refinement
- **Root README Rewrite:** Rewrote `README.md` to conform to a 10-section academic standard featuring clean Mermaid flowcharts, verified relative links, and zero emojis.
- **Dataset #1 Empirical Count Reconciliation:** Reconciled documentation discrepancy regarding Dataset #1: corrected conflicting historical figures to the authoritative empirical count of **226 positive (defect-prone)** and **257 candidate-clean** observations ($N = 483$).
- **Academic Rigor & Limitations:** Integrated explicit discussion across technical and presentation documents regarding:
  - The Open-World Assumption (OWA) for candidate-clean methods.
  - The Base-Rate Fallacy under Bayes' theorem (demonstrating expected operational precision of $\approx 10.9\%$ at 5% defect prevalence).
  - Out-of-fold threshold tuning ($\tau^* = 0.40$) without nested cross-validation.
  - Classification of the 24-method double-blind review protocol as a formal research instrument rather than an executed human study.
- **Presentation Decks:** Refined all seven presentation decks (`6_Presentation/01_*.md` through `07_*.md`), replacing pie charts with confusion matrices, eliminating emojis, and updating test counts.

### Stage 5 — Comprehensive Verification Suite
- Verified all 123 unit and integration tests passing via `pytest`.
- Verified clean compilation of `RoslynAnalyzer.csproj` in Release mode using .NET 9.0 SDK.
- Performed runtime smoke testing of Streamlit entrypoints and page modules.
- Verified cryptographic bitwise parity across all 15 protected artifacts.
- Executed automated link and emoji scanners across the entire active codebase.

---

## 3. Confirmed Defects and Resolutions

### Defect 1: Circular Import Between Settings and ML Packages
- **Symptom:** Running `pytest` in a fresh terminal session produced `AttributeError: partially initialized module 'ml' ... has no attribute 'preprocessing'` during test collection.
- **Root Cause:** `core/settings.py` eagerly executed `register_unpickle_aliases()` at module import time, importing `ml.preprocessing` while `ml` was still mid-initialization.
- **Resolution:** Removed the eager top-level call in `settings.py`. Made `register_unpickle_aliases()` robust against partial initialization and invoked it lazily in `ml/model_manager.py` only when unpickling legacy model bundles. Added two automated regression tests in `test_config.py`.

### Defect 2: Dataset Snapshot #1 Label Discrepancy
- **Symptom:** Historical documentation inconsistently cited Dataset #1 as containing 242 positive / 241 negative observations or 231 / 252 observations.
- **Root Cause:** Early development drafts had duplicated positive observations before production filtering was stabilized.
- **Resolution:** Inspected the authoritative CSV (`csharp_empirical_v1_v1.0.0.csv`) and database records: confirmed exactly **226 positive (defect-prone)** and **257 negative (candidate-clean)** observations ($N = 483$). Synchronized all technical documentation, academic reports, and presentation slides to reflect the authoritative numbers.

### Defect 3: Emojis and Non-Academic Visualizations
- **Symptom:** The user interface and markdown documentation utilized informal emojis and decorative pie charts.
- **Resolution:** Replaced all pie/donut charts with markdown data tables and horizontal bar charts. Removed all decorative emojis from Python code docstrings, Streamlit UI components, documentation files, and presentation materials.

### Defect 4: Outdated Directory Path References
- **Symptom:** Documentation referenced legacy pre-migration paths (such as `src/`, `data/processed/`, and `reports/experiments/`).
- **Resolution:** Updated all paths across active guides and presentation decks to canonical repository locations (`1_Database/`, `2_SourceCode/`, `3_TestResults/`, `4_AppBuild/`, `5_Documentation/`, `6_Presentation/`).

---

## 4. Protected Artifact Checksum Verification

All 15 protected artifacts retain 100% cryptographic SHA-256 bitwise parity against their pre-refinement baseline:

| Protected Artifact Path | Baseline SHA-256 Checksum | Current SHA-256 Digest | Status |
| :--- | :--- | :--- | :---: |
| `1_Database/SQLite/bug_detection.db` | `70905a834dac...` | `70905a834dac297ac60a7fb91ad7b2909690734447519e8dbd41b29cad029893` | **MATCH** |
| `1_Database/SQLite/csharp_prediction.db` | `fc9cb12161aa...` | `fc9cb12161aa76533e1217e56d52121592c5e717e629aeda1c26db5aa4d8b5c8` | **MATCH** |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` | `c7ab9bafec7b...` | `c7ab9bafec7b2860a6450814a66a5ddc60072c208ea671a45f5206087209b0f1` | **MATCH** |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0_metadata.json` | `74cfa29d558d...` | `74cfa29d558d7cce30d32470860cdd92c5eb0587892bdf25d3ac6f542d5a2864` | **MATCH** |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` | `7fad0ecc1d2e...` | `7fad0ecc1d2e285f8284c54b68d5dd6841a5a821bbff05d4a897d5f705533a6e` | **MATCH** |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0_metadata.json` | `0a50cad08c44...` | `0a50cad08c44ec6b940b5ec5eb7c7cb9eb5723820fe37bc031b2da102a3c1297` | **MATCH** |
| `4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib` | `e316287b942b...` | `e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f` | **MATCH** |
| `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` | `625992350a78...` | `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_results.json` | `6be0bd4b8d6c...` | `6be0bd4b8d6cd287c7b47c7f1e28a5b7fb47ab8459a4e0758f20a82cd0042fde` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_results.csv` | `5c48f5370007...` | `5c48f5370007def1ff0cd0b59e2d5cc2156394661fac6c6f0211061d0e2768a5` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_report.md` | `2d4d635e14a8...` | `2d4d635e14a811037a00e11157c8f6b4ae14453211be0d6df8f4b14e8808a8a8` | **MATCH** |
| `3_TestResults/AuditReports/dataset_integrity_audit.json` | `f9a0e6db1ed6...` | `f9a0e6db1ed6fa5deab2f47ed7556bb4b5b4421fae6fe814cfbd386a33858c4d` | **MATCH** |
| `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json` | `db70d04898dd...` | `db70d04898dd1c89be906ffea9fe93fafdc5b62a27fa40e51c7a0c569661deb0` | **MATCH** |
| `3_TestResults/AuditReports/fluentvalidation_pilot_results.json` | `5c69583f79ba...` | `5c69583f79ba43c69169b189da09c5091e331fef95f38d3fa4f795fc10c39a68` | **MATCH** |
| `3_TestResults/AuditReports/fluentvalidation_pilot_v2_corrected.json` | `7cda63d8b809...` | `7cda63d8b8094ab7aac5003abf3f5b5791f41a314a0e200a8b1fc88e659833a3` | **MATCH** |

**Verification Outcome: 15/15 Match (100.0% Bitwise Parity).**

---

## 5. Architectural Invariants Sign-Off

The repository quality refinement has achieved all stated goals while maintaining complete fidelity to the original research:

1. **Repository Structure:** The canonical 6-domain architecture (`1_Database/` through `6_Presentation/`) remains strictly intact.
2. **Empirical Ground Truth:** Datasets, SZZ traces, model weights, and experimental metrics are identical to historical records.
3. **Reproducibility:** The software system builds, passes tests, and runs offline without external cloud or database dependencies.
4. **Academic Presentation:** Documentation, user interface, and presentation slides are now presented in formal academic English suitable for high-standard scholarly evaluation.

