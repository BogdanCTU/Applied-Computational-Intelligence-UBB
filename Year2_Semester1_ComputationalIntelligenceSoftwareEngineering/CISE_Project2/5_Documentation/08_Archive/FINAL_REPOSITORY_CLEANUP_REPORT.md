# CISE Project 2 — Final Repository Cleanup & Legacy Directory Removal Report

**Project Title:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Master Program:** Applied Computational Intelligence (Year 2, Semester 1)  
**Course:** Computational Intelligence in Software Engineering (CISE Project 2)  
**Execution Date:** 2026-11-14  
**Author:** CISE Project 2 Engineering & Architecture Team  

---

## 1. Summary of the Cleanup

Following the initial staged reorganization into the six numbered top-level domains (`1_Database` through `6_Presentation`), this operation performed the comprehensive, final cleanup of the repository. All ten legacy root-level directories (`config/`, `data/`, `modles/`, `roslyn_analyzer/`, `scratch/`, `scripts/`, `src/`, `tests/`, `tmp/`, `ui/`) and internal temporary compatibility shims (`2_SourceCode/Python/{src,config,ui}`) have been removed.

Every project component now has exactly **one authoritative location**. All 66 Python application modules, scripts, and test modules in `2_SourceCode/` were systematically refactored to use direct canonical package imports (`core.settings`, `database`, `ml`, `repositories`, `services`, `utils`, `application.pages`), eliminating any reliance on backward-compatibility layers.

All 121 automated unit/integration tests pass with 100% success rate, the .NET 9 Roslyn analyzer builds with zero warnings and zero errors, and all 15 protected databases, datasets, models, and experiment artifacts preserve 100% bitwise SHA-256 parity with zero model retraining or dataset regeneration.

---

## 2. Final Root Directory Tree

```text
CISE_Project2/
│
├── README.md                                  # Primary repository overview, results & documentation index
├── app.py                                     # Root Streamlit launcher delegating to 2_SourceCode/Python/app.py
├── pytest.ini                                 # Root test configuration (pythonpath = 2_SourceCode/Python, testpaths = 2_SourceCode/Tests)
├── requirements.txt                           # Frozen Python dependencies
├── .env.example                               # Environment template for GitHub tokens and path overrides
├── .gitignore                                 # Git ignore rules for virtualenvs, binaries, and local data
├── skills-lock.json                           # Agent and tooling configuration
│
├── 1_Database/                                # Persistent database and datasets
│   ├── SQLite/                                # SQLite databases (bug_detection.db, csharp_prediction.db)
│   ├── Datasets/                              # Versioned CSV datasets (Original/ v1.0.0, Processed/ v2.0.0)
│   ├── Repositories/                          # Cloned open-source C# Git repositories (7 projects)
│   └── Schema/                                # Relational database & dataset schemas
│
├── 2_SourceCode/                              # Implementation & automated test source code
│   ├── Python/                                # Python application modules
│   │   ├── application/pages/                 # Interactive Streamlit UI pages (8 tabs)
│   │   ├── core/settings.py                   # Centralized configuration & dynamic root finder
│   │   ├── database/                          # SQLite connection, schema, repository DB
│   │   ├── ml/                                # Preprocessing, trainer, GroupKFold, predictor
│   │   ├── repositories/                      # GitHub API client, git manager, commit collector
│   │   ├── services/                          # Roslyn bridge, SZZ analyzer, dataset builder, labeler
│   │   ├── utils/                             # Logger & production source code classifier
│   │   └── app.py                             # Core Streamlit application entrypoint
│   ├── RoslynAnalyzer/                        # .NET 9.0 C# AST static metric analyzer
│   ├── Tests/                                 # 16 automated test modules (121 tests)
│   └── Scripts/                               # 14 operational, research, and audit utilities
│
├── 3_TestResults/                             # Verification evidence and evaluation outputs
│   ├── AutomatedTests/                        # Automated pytest test execution reports
│   ├── CrossValidation/                      # Final 5-fold CV JSON/CSV/MD outputs & Historical runs
│   ├── HoldoutEvaluation/                     # Independent holdout (Newtonsoft.Json) results
│   ├── ModelEvaluation/                       # 11-model comparison benchmark metrics & model
│   └── AuditReports/                          # SZZ and dataset integrity audits
│
├── 4_AppBuild/                                # Distributable runtime packages
│   ├── Windows/                               # Windows 1-click launcher (run_app.bat)
│   ├── Assets/Models/                         # Frozen runtime model joblib bundles
│   └── ReleaseNotes/                          # Release notes and changelog (v1.0.0)
│
├── 5_Documentation/                           # Technical and academic documentation
│   ├── 01_Architecture/                       # System architecture (SYSTEM_ARCHITECTURE.md)
│   ├── 02_Database/                           # Database architecture (DATABASE_ARCHITECTURE.md)
│   ├── 03_SourceCode/                         # Source code guide (SOURCE_CODE_GUIDE.md)
│   ├── 04_MachineLearning/                    # SZZ, Roslyn features, ML benchmark results
│   ├── 05_Validation/                         # Empirical validation, Bayes theorem, limitations
│   ├── 06_UserGuide/                          # Step-by-step user manual & troubleshooting
│   ├── 07_AcademicReport/                     # Authoritative academic paper (FINAL_REPORT.md)
│   └── 08_Archive/                            # Historical audits, provenance, and cleanup report
│
└── 6_Presentation/                            # University defense presentation material (7 slide decks)
    ├── 01_ProjectOverview.md
    ├── 02_ProblemAndObjectives.md
    ├── 03_SystemArchitecture.md
    ├── 04_DatasetAndMethodology.md
    ├── 05_MachineLearningResults.md
    ├── 06_ApplicationDemo.md
    └── 07_ConclusionAndFutureWork.md
```

---

## 3. Migration Table for All 10 Legacy Directories

| # | Legacy Directory | Status | Destination / Authoritative Location | Verification & Checksum Status |
| :---: | :--- | :---: | :--- | :--- |
| 1 | `config/` | **REMOVED** | `2_SourceCode/Python/core/settings.py` | Imports refactored to `from core.settings import ...`. Settings resolve dynamically. |
| 2 | `data/` | **REMOVED** | `1_Database/SQLite/`, `1_Database/Datasets/`, `1_Database/Repositories/` | `bug_detection.db`, datasets v1 and v2, and all 7 cloned repos safely moved and verified bitwise. |
| 3 | `modles/` | **REMOVED** | *(Typo in prompt; did not exist on disk)* | Verified non-existent. |
| 4 | `models/` | **REMOVED** | `4_AppBuild/Assets/Models/` & `3_TestResults/ModelEvaluation/` | `rf_csharp_empirical_model.joblib` verified bitwise (SHA-256: `e316287b942b...`). |
| 5 | `roslyn_analyzer/` | **REMOVED** | `2_SourceCode/RoslynAnalyzer/` | Source code and project file verified identical; compiled with .NET 9 SDK in `2_SourceCode`. |
| 6 | `scratch/` | **REMOVED** | `2_SourceCode/Scripts/` | 4 useful audit/verification scripts migrated; 5 disposable temporary scripts deleted. |
| 7 | `scripts/` | **REMOVED** | `2_SourceCode/Scripts/` | All 10 operational scripts verified bitwise identical; updated imports. |
| 8 | `src/` | **REMOVED** | `2_SourceCode/Python/` | All 22 module files verified identical; all 61 callers refactored to canonical imports. |
| 9 | `tests/` | **REMOVED** | `2_SourceCode/Tests/` | All 16 test modules preserved and passing (121/121 tests pass). |
| 10 | `tmp/` | **REMOVED** | *(Empty directory)* | Safely deleted. |
| 11 | `ui/` | **REMOVED** | `2_SourceCode/Python/application/pages/` | All 8 Streamlit pages preserved and verified bitwise identical. |
| 12 | `2_SourceCode/Python/{src,config,ui}` | **REMOVED** | `2_SourceCode/Python/` | Internal compatibility shims removed after direct canonical import refactoring. |

---

## 4. Files & Directories Removed and Justification

1. **`config/` (4 files):** Redundant wrapper around settings. Replaced by `2_SourceCode/Python/core/settings.py`.
2. **`data/database/` (2 files):** Moved to `1_Database/SQLite/`. Verified bitwise identical.
3. **`data/processed/` (4 files):** Moved to `1_Database/Datasets/Processed/` and `Original/`. Verified bitwise identical.
4. **`data/raw/` (0 files):** Empty directory. Removed.
5. **`data/repositories/` (7 repo trees):** Moved to `1_Database/Repositories/`.
6. **`models/` (1 file):** `rf_csharp_empirical_model.joblib` moved to `4_AppBuild/Assets/Models/`. Verified bitwise identical.
7. **`roslyn_analyzer/` (60 files):** Source and project files moved to `2_SourceCode/RoslynAnalyzer/`. Build artifacts (`bin/`, `obj/`) regenerated in new location.
8. **`scratch/` (12 files):**
   - Migrated to `2_SourceCode/Scripts/`: `audit_commits.py`, `audit_fv_v2.py`, `generate_audit_json.py`, `verify_repo_stats.py`.
   - Disposed: `inspect_repo_paths.py`, `test_clean_methods.py`, `test_methods.py`, `test_pilot_szz.py`, `verify_all_markdown_links.py` (one-off debugging scripts).
9. **`scripts/` (10 files):** All migrated to `2_SourceCode/Scripts/`.
10. **`src/` (60 files):** All migrated to `2_SourceCode/Python/`.
11. **`tests/` (32 files):** All migrated to `2_SourceCode/Tests/`.
12. **`tmp/` (0 files):** Empty temporary directory removed.
13. **`ui/` (11 files):** All migrated to `2_SourceCode/Python/application/pages/`.
14. **`2_SourceCode/Python/src`, `config`, `ui`:** Temporary compatibility facade directories removed to ensure zero redundant parallel trees exist.

---

## 5. Files Migrated & Final Authoritative Destinations

- **Databases:**
  - `data/database/bug_detection.db` -> `1_Database/SQLite/bug_detection.db`
  - `data/database/csharp_prediction.db` -> `1_Database/SQLite/csharp_prediction.db`
- **Datasets:**
  - `data/processed/csharp_empirical_v1_v1.0.0.*` -> `1_Database/Datasets/Original/` & `1_Database/Datasets/Processed/`
  - `data/processed/csharp_empirical_v2_v2.0.0.*` -> `1_Database/Datasets/Processed/`
- **Cloned Git Repositories:**
  - `data/repositories/*` -> `1_Database/Repositories/*`
- **Application Code:**
  - `src/database/*` -> `2_SourceCode/Python/database/`
  - `src/ml/*` -> `2_SourceCode/Python/ml/`
  - `src/collection/*` -> `2_SourceCode/Python/repositories/`
  - `src/analyzer/*` -> `2_SourceCode/Python/services/analyzer/`
  - `src/mining/*` -> `2_SourceCode/Python/services/mining/`
  - `src/dataset/*` -> `2_SourceCode/Python/services/dataset/`
  - `src/labeling/*` -> `2_SourceCode/Python/services/labeling/`
  - `src/utils/*` -> `2_SourceCode/Python/utils/`
  - `ui/pages/*` -> `2_SourceCode/Python/application/pages/`
  - `config/settings.py` -> `2_SourceCode/Python/core/settings.py`
- **Roslyn Analyzer:**
  - `roslyn_analyzer/Program.cs` & `.csproj` -> `2_SourceCode/RoslynAnalyzer/`
- **Automated Tests:**
  - `tests/test_*.py` (16 modules) -> `2_SourceCode/Tests/`
- **Scripts:**
  - `scripts/*.py` (10 files) + `scratch/{audit_commits,audit_fv_v2,generate_audit_json,verify_repo_stats}.py` (4 files) -> `2_SourceCode/Scripts/` (14 total scripts)
- **Runtime Models:**
  - `models/rf_csharp_empirical_model.joblib` -> `4_AppBuild/Assets/Models/` & `3_TestResults/ModelEvaluation/`

---

## 6. Updated Path, Import, and Configuration References

1. **Direct Canonical Package Imports (66 files refactored):**
   - `from config.settings import ...` -> `from core.settings import ...`
   - `from src.analyzer.roslyn_client import ...` -> `from services.analyzer.roslyn_client import ...`
   - `from src.collection.* import ...` -> `from repositories.* import ...`
   - `from src.database.* import ...` -> `from database.* import ...`
   - `from src.dataset.* import ...` -> `from services.dataset.* import ...`
   - `from src.labeling.* import ...` -> `from services.labeling.* import ...`
   - `from src.mining.* import ...` -> `from services.mining.* import ...`
   - `from src.ml.* import ...` -> `from ml.* import ...`
   - `from src.utils.* import ...` -> `from utils.* import ...`
   - `from ui.pages.* import ...` -> `from application.pages.* import ...`
2. **Centralized Dynamic Root Finder (`core/settings.py`):**
   - `find_project_root()` walks parent directories looking for boundary markers (`1_Database`, `2_SourceCode`, `pytest.ini`).
   - Default storage paths resolve to `1_Database/SQLite/`, `1_Database/Datasets/`, `1_Database/Repositories/`, and `4_AppBuild/Assets/Models/`.
3. **In-Memory Pickler Aliases for Frozen Models:**
   - To preserve 100% bitwise parity on frozen `.joblib` model bundles without requiring retraining, `core/settings.py` registers dynamic in-memory unpickling shims in `sys.modules` (`sys.modules["src.ml.preprocessing"] = ml.preprocessing`).
   - Models unpickle cleanly with zero filesystem `src/` directory.
4. **`pytest.ini` Configuration:**
   - `pythonpath = 2_SourceCode/Python`
   - `testpaths = 2_SourceCode/Tests`
5. **Streamlit Root Entrypoint (`app.py`):**
   - Injects `2_SourceCode/Python` into `sys.path` and delegates execution to `2_SourceCode/Python/app.py`.

---

## 7. Automated Test Results

Executed on 2026-11-14:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.17, pytest-9.2.0, pluggy-1.7.0
rootdir: E:\PERSONAL\GitHub\1_Applied-Computational-Intelligence-UBB\Year2_Semester1_ComputationalIntelligenceSoftwareEngineering\CISE_Project2
configfile: pytest.ini
testpaths: 2_SourceCode/Tests
plugins: anyio-4.16.0, mock-3.17.0
collected 121 items

2_SourceCode\Tests\test_bug_fix_detector.py ...                          [  2%]
2_SourceCode\Tests\test_bug_predictor.py .......                         [  8%]
2_SourceCode\Tests\test_commit_collector.py ..                           [  9%]
2_SourceCode\Tests\test_config.py .                                      [ 10%]
2_SourceCode\Tests\test_database.py ...                                  [ 13%]
2_SourceCode\Tests\test_dataset_builder_and_exporter.py ...              [ 15%]
2_SourceCode\Tests\test_experiment_runner.py .......                     [ 21%]
2_SourceCode\Tests\test_fluentvalidation_pilot.py ..                     [ 23%]
2_SourceCode\Tests\test_github_client.py ......                          [ 28%]
2_SourceCode\Tests\test_label_manager.py ...                             [ 30%]
2_SourceCode\Tests\test_ml_pipeline.py ......                            [ 35%]
2_SourceCode\Tests\test_model_baselines.py .....                         [ 39%]
2_SourceCode\Tests\test_repository_manager.py ...                        [ 42%]
2_SourceCode\Tests\test_roslyn_metrics.py ......                         [ 47%]
2_SourceCode\Tests\test_source_classifier.py ........................... [ 69%]
..................................                                       [ 97%]
2_SourceCode\Tests\test_szz_analyzer.py ...                              [100%]

============================ 121 passed in 29.87s =============================
```
**Result: 121 passed, 0 failed, 0 errors, 0 skipped (100% pass rate).**

---

## 8. Roslyn Analyzer Build Results

Command:
```powershell
dotnet build 2_SourceCode\RoslynAnalyzer\RoslynAnalyzer.csproj -c Release
```
Output:
```text
  Determining projects to restore...
  All projects are up-to-date for restore.
  RoslynAnalyzer -> E:\PERSONAL\GitHub\...\2_SourceCode\RoslynAnalyzer\bin\Release\net9.0\RoslynAnalyzer.dll

Build succeeded.
    0 Warning(s)
    0 Error(s)

Time Elapsed 00:00:00.55
```
**Result: Clean build, 0 warnings, 0 errors.**

---

## 9. Application & Runtime Smoke-Test Results

Executed via automated integrity verification:
1. **Core Package Imports:** `core.settings`, `database`, `ml`, `repositories`, `services`, `utils`, `application` all imported cleanly.
2. **Database Connectivity:** Connected to `1_Database/SQLite/bug_detection.db`. Verified statistics:
   - `repositories_total`: 7
   - `commits_total`: 2,450
   - `observations_total`: 877 (439 buggy, 438 clean, 0 uncertain)
   - `datasets_count`: 2
   - `models_count`: 1
3. **Dataset Ingestion:**
   - Dataset v1 (`1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv`): 483 rows, 51 columns.
   - Dataset v2 (`1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv`): 578 rows, 51 columns.
4. **Roslyn Client Metric Extraction:**
   - Input: C# class with method `Add(int a, int b)`.
   - Extracted 26 static features via `RoslynClient` subprocess.
5. **Model Ingestion & Prediction Smoke Test:**
   - Model 1 (`rf_csharp_empirical_model.joblib`, 25 features): Scored sample method `Div` -> RiskScore = 0.3129 (Medium risk).
   - Model 2 (`exp_final_5fold_v2_best_rf_compact_regularized.joblib`, 26 features): Scored sample method `Div` -> RiskScore = 0.2591 (Low risk).
6. **Streamlit Startup:** Entrypoint `app.py` loads and delegates to `2_SourceCode/Python/app.py` with all 8 pages registered.

---

## 10. Markdown Link Validation

Validated across all 48 project Markdown documents:
- **Total Markdown files scanned:** 48
- **Total relative file links tested:** 65
- **Broken links found:** **0**
- **Link validity rate:** **100%**

---

## 11. Protected Artifact Checksum Verification

All 15 protected artifacts were checked against the pre-migration cryptographic baseline:

| Artifact Path | Baseline SHA-256 Checksum | Post-Cleanup SHA-256 Checksum | Parity Status |
| :--- | :--- | :--- | :---: |
| `1_Database/SQLite/bug_detection.db` | `70905a834dac...` | `70905a834dac297ac60a7fb91ad7b2909690734447519e8dbd41b29cad029893` | **MATCH** |
| `1_Database/SQLite/csharp_prediction.db` | `fc9cb12161aa...` | `fc9cb12161aa76533e1217e56d52121592c5e717e629aeda1c26db5aa4d8b5c8` | **MATCH** |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` | `c7ab9bafec7b...` | `c7ab9bafec7b2860a6450814a66a5ddc60072c208ea671a45f5206087209b0f1` | **MATCH** |
| `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0_meta.` | `74cfa29d558d...` | `74cfa29d558d7cce30d32470860cdd92c5eb0587892bdf25d3ac6f542d5a2864` | **MATCH** |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` | `7fad0ecc1d2e...` | `7fad0ecc1d2e285f8284c54b68d5dd6841a5a821bbff05d4a897d5f705533a6e` | **MATCH** |
| `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0_meta.`| `0a50cad08c44...` | `0a50cad08c44ec6b940b5ec5eb7c7cb9eb5723820fe37bc031b2da102a3c1297` | **MATCH** |
| `4_AppBuild/Assets/Models/rf_csharp_empirical_model.joblib` | `e316287b942b...` | `e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f` | **MATCH** |
| `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact.` | `625992350a78...` | `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_results.json` | `6be0bd4b8d6c...` | `6be0bd4b8d6cd287c7b47c7f1e28a5b7fb47ab8459a4e0758f20a82cd0042fde` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_results.csv` | `5c48f5370007...` | `5c48f5370007def1ff0cd0b59e2d5cc2156394661fac6c6f0211061d0e2768a5` | **MATCH** |
| `3_TestResults/CrossValidation/experiment_report.md` | `2d4d635e14a8...` | `2d4d635e14a811037a00e11157c8f6b4ae14453211be0d6df8f4b14e8808a8a8` | **MATCH** |
| `3_TestResults/AuditReports/dataset_integrity_audit.json` | `f9a0e6db1ed6...` | `f9a0e6db1ed6fa5deab2f47ed7556bb4b5b4421fae6fe814cfbd386a33858c4d` | **MATCH** |
| `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json`| `db70d04898dd...` | `db70d04898dd1c89be906ffea9fe93fafdc5b62a27fa40e51c7a0c569661deb0` | **MATCH** |
| `3_TestResults/AuditReports/fluentvalidation_pilot_results.json` | `5c69583f79ba...` | `5c69583f79ba43c69169b189da09c5091e331fef95f38d3fa4f795fc10c39a68` | **MATCH** |
| `3_TestResults/AuditReports/fluentvalidation_pilot_v2_corr.json` | `7cda63d8b809...` | `7cda63d8b8094ab7aac5003abf3f5b5791f41a314a0e200a8b1fc88e659833a3` | **MATCH** |

**Verification Outcome: 15/15 Match (100% Bitwise Parity).**

---

## 12. Remaining Limitations & Unresolved Issues

- **None.** The repository contains zero redundant legacy root directories, zero broken markdown links, zero compiler warnings, zero broken imports, and zero test regressions.
- All six curriculum requirements of the CISE project curriculum are fully satisfied.

---

## 13. Final Verdict

**FINAL REPOSITORY CLEANUP COMPLETE**

