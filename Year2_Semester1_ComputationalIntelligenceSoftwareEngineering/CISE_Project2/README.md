# C# Defect Predictor: Machine Learning-Based Software Defect Prediction

Method-level software defect prediction for C# source code using Microsoft Roslyn static code metrics, SZZ git blame localization, repository-level cross-validation, and an interactive Streamlit workbench.

Developed for the Computational Intelligence in Software Engineering course at Babeș-Bolyai University (Master in Applied Computational Intelligence).

---

## 1. Project Purpose

Software defect prediction estimates the defect-proneness of source code components to help prioritize code review and testing. This system extracts 26 static Abstract Syntax Tree (AST) metrics from individual C# methods using Microsoft Roslyn, assigns heuristic labels from version-control history via the SZZ algorithm, and trains supervised classifiers evaluated across repository boundaries.

---

## 2. Main Capabilities

- **Repository Collection and Git Mining:** Search public C# repositories via the GitHub REST API, clone commit histories, and detect candidate bug-fixing commits using regex heuristics. (Requires network access; source analysis and inference run locally.)
- **SZZ Defect Localization:** Trace lines modified or deleted in bug-fixing commits to candidate bug-inducing commits using `git blame -w -M -C`.
- **Production Source Filtering:** Exclude test projects, test fixtures, build directories, and generated files prior to dataset construction.
- **Roslyn Static Metric Extraction:** Compute 26 size, complexity, control-flow, and object-oriented metrics at the method level via `.NET 9.0` and `Microsoft.CodeAnalysis.CSharp`.
- **Repository-Aware Validation:** Partition training and validation folds by repository (`GroupKFold`, $K=5$) so methods from the same repository do not appear in both partitions simultaneously.
- **Method-Level Inference:** Evaluate standalone C# methods or complete `.cs` files locally in the Streamlit workbench.

---

## 3. Architecture Overview

```text
CISE_Project2/
├── README.md                                  # Project overview and quickstart
├── app.py                                     # Root Streamlit entrypoint
├── pytest.ini                                 # Automated test configuration
├── requirements.txt                           # Python dependencies
├── 1_Database/                                # SQLite database, schemas, and CSV datasets
├── 2_SourceCode/                              # Python modules, .NET 9.0 Roslyn analyzer, and tests
├── 3_TestResults/                             # Cross-validation, holdout, and audit artifacts
├── 4_AppBuild/                                # Serialized model bundles and Windows launcher
├── 5_Documentation/                           # Technical specifications and academic reports
└── 6_Presentation/                            # Academic defense presentation decks
```

| Component | Technology | Version | Role |
| :--- | :--- | :--- | :--- |
| Runtime | Python | >= 3.11 | Data pipeline, machine learning, and UI |
| Compiler Platform | .NET SDK / `Microsoft.CodeAnalysis.CSharp` | 9.0 / 4.12.0 | C# AST parsing and 26 static code metrics |
| Machine Learning | `scikit-learn`, `pandas`, `numpy`, `joblib` | >= 1.5.0 | Preprocessing, GroupKFold validation, and Random Forest inference |
| Storage | SQLite3 | 3.x | Local relational persistence (`1_Database/SQLite/bug_detection.db`) |
| Interface | Streamlit, Plotly | >= 1.40.0 | Local multi-page workbench |
| Testing | `pytest`, `pytest-mock` | >= 8.3.0 | Offline unit and integration test suite (123 tests) |

---

## 4. Installation and Execution

### System Requirements

| Requirement | Specification |
| :--- | :--- |
| Python | 3.11 or higher |
| .NET SDK | 9.0 or higher (`dotnet --version`) |
| Git | Command-line client in system `PATH` |
| Network | Required only for GitHub repository search and cloning |

### Setup and Launch (Linux / macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release
python -m streamlit run app.py
```

### Setup and Launch (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
dotnet build 2_SourceCode\RoslynAnalyzer\RoslynAnalyzer.csproj -c Release
python -m streamlit run app.py
```

On Windows, `4_AppBuild\Windows\run_app.bat` initializes the environment, checks the Roslyn binary, and starts Streamlit.

### Automated Tests

```bash
pytest
```

Test execution results are recorded in [3_TestResults/AutomatedTests/TEST_EXECUTION_REPORT.md](3_TestResults/AutomatedTests/TEST_EXECUTION_REPORT.md).

---

## 5. Dataset and Model Summary

### Datasets

| Dataset | Observations | Defect-Prone (1) | Candidate-Clean (0) | Repositories | Purpose |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `csharp_empirical_v1` (v1.0.0) | 483 | 226 (46.79%) | 257 (53.21%) | `Humanizer` (291), `CommandLineParser` (101), `MediatR` (91) | Initial exploratory corpus |
| `csharp_empirical_v2` (v2.0.0) | 578 | 279 (48.27%) | 299 (51.73%) | `Humanizer` (291), `Serilog` (134), `MediatR` (91), `Polly` (34), `FluentValidation` (28) | 5-fold `GroupKFold` cross-validation |
| Independent holdout | 159 | 79 (49.69%) | 80 (50.31%) | `JamesNK/Newtonsoft.Json` (159) | External holdout evaluation |

Positive labels (1) are heuristic SZZ attributions from bug-fixing commits. Negative labels (0) are candidate-clean methods sampled from `HEAD` with no recorded bug fixes in the mined commit window.

### Selected Model (`rf_compact_regularized`)

| Parameter | Value |
| :--- | ---: |
| Model | Random Forest |
| Estimators | 100 |
| Maximum depth | 8 |
| Minimum split | 5 |
| Minimum leaf | 4 |
| Class weights | Balanced |
| Decision threshold ($\tau^*$) | 0.40 |

### Evaluation Summary

| Evaluation | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5-Fold GroupKFold mean | 0.50 | 67.34% ± 4.91% | 68.24% ± 12.02% | 74.03% ± 15.57% | 0.6859 ± 0.0247 | 0.7025 | 0.2144 |
| GroupKFold pooled OOF | 0.50 | 67.13% | 63.86% | 73.48% | 0.6833 | 0.7025 | 0.2144 |
| GroupKFold pooled OOF | 0.40 | 70.42% | 64.21% | 87.46% | 0.7405 | 0.7025 | 0.2144 |
| Newtonsoft.Json holdout | 0.50 | 74.21% | 69.79% | 84.81% | 0.7657 | 0.8209 | 0.1713 |
| Newtonsoft.Json holdout | 0.40 | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.1713 |

---

## 6. Documentation References

| Document | Path | Scope |
| :--- | :--- | :--- |
| System Architecture | [5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md](5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md) | Component structure and processing flow |
| Database Architecture | [5_Documentation/02_Database/DATABASE_ARCHITECTURE.md](5_Documentation/02_Database/DATABASE_ARCHITECTURE.md) | SQLite schema, tables, and SZZ provenance |
| Source Code Guide | [5_Documentation/03_SourceCode/SOURCE_CODE_GUIDE.md](5_Documentation/03_SourceCode/SOURCE_CODE_GUIDE.md) | Python packages, Roslyn AST analyzer, and build commands |
| Project Methodology | [5_Documentation/04_MachineLearning/PROJECT_METHODOLOGY.md](5_Documentation/04_MachineLearning/PROJECT_METHODOLOGY.md) | Repository selection, SZZ rules, source filtering, and 26 Roslyn metrics |
| Experimental Results | [5_Documentation/04_MachineLearning/EXPERIMENTAL_RESULTS.md](5_Documentation/04_MachineLearning/EXPERIMENTAL_RESULTS.md) | Cross-validation benchmarks, threshold tuning, and holdout results |
| Validation & Limitations | [5_Documentation/05_Validation/VALIDATION_AND_LIMITATIONS.md](5_Documentation/05_Validation/VALIDATION_AND_LIMITATIONS.md) | Verification suite, qualitative cases, Bayesian base-rate analysis, and threats to validity |
| User Guide | [5_Documentation/06_UserGuide/USER_GUIDE.md](5_Documentation/06_UserGuide/USER_GUIDE.md) | Application pages, controls, and troubleshooting |
| Academic Report | [5_Documentation/07_AcademicReport/FINAL_REPORT.md](5_Documentation/07_AcademicReport/FINAL_REPORT.md) | Full academic report |
| Developer Study Protocol | [5_Documentation/07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md](5_Documentation/07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md) | Double-blind review protocol template (24 methods) |
| Defense Package | [5_Documentation/09_Defense/DEFENSE_PACKAGE_VALIDATION.md](5_Documentation/09_Defense/DEFENSE_PACKAGE_VALIDATION.md) | Defense slides, scripts, and artifact validation summary |
| Presentation Decks | [6_Presentation/](6_Presentation/) | Markdown slide decks |
