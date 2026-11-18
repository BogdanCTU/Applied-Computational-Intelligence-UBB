# C# Defect Predictor: Machine Learning-Based Software Defect Prediction

Method-level software defect prediction for C# source code using Microsoft Roslyn static code metrics, SZZ git blame localization, nested repository-level cross-validation, and a local Streamlit workbench.

Developed for the Computational Intelligence in Software Engineering course at Babeș-Bolyai University (Master in Applied Computational Intelligence).

---

## 1. Project Purpose

This system extracts 26 static Abstract Syntax Tree (AST) metrics from individual C# methods using Microsoft Roslyn, assigns heuristic defect labels from version-control history via the SZZ algorithm, and evaluates supervised classifiers across repository boundaries using nested `GroupKFold` cross-validation.

---

## 2. Main Capabilities

- **Repository Collection and Git Mining:** Search public C# repositories via the GitHub REST API, clone commit histories, and detect candidate bug-fixing commits using regex heuristics. (Requires network access; source analysis and inference run locally.)
- **SZZ Defect Localization:** Trace lines modified or deleted in bug-fixing commits to candidate bug-inducing commits using `git blame -w -M -C`.
- **Production Source Filtering:** Exclude test projects, test fixtures, build directories, and generated files prior to dataset construction.
- **Roslyn Static Metric Extraction:** Compute 26 size, complexity, control-flow, and object-oriented metrics at the method level via `.NET 9.0` and `Microsoft.CodeAnalysis.CSharp`.
- **Nested Repository-Level Validation:** Evaluate models using 5-fold outer `GroupKFold` and 4-fold inner `GroupKFold` so model selection, feature selection, and threshold tuning occur strictly inside training partitions.
- **Method-Level Inference:** Score standalone C# methods or `.cs` files locally in the Streamlit workbench.

---

## 3. Architecture Overview

```text
CISE_Project2/
├── README.md                                  # Project overview and quickstart
├── app.py                                     # Root Streamlit entrypoint
├── pytest.ini                                 # Automated test configuration
├── requirements.txt                           # Python dependencies
├── 1_Database/                                # SQLite database, schemas, and CSV datasets
├── 2_SourceCode/                              # Python modules, .NET 9.0 Roslyn analyzer, scripts, tests
├── 3_TestResults/                             # Baseline CV, holdout, audit, and nested optimization results
├── 4_AppBuild/                                # Serialized model bundles and Windows launcher
├── 5_Documentation/                           # Technical specifications and academic reports
└── 6_Presentation/                            # Academic defense presentation decks
```

| Component | Technology | Version | Role |
| :--- | :--- | :--- | :--- |
| Runtime | Python | >= 3.11 | Data pipeline, machine learning, and UI |
| Compiler Platform | .NET SDK / `Microsoft.CodeAnalysis.CSharp` | 9.0 / 4.12.0 | C# AST parsing and 26 static code metrics |
| Machine Learning | `scikit-learn`, `pandas`, `numpy`, `joblib` | >= 1.5.0 | Preprocessing, nested `GroupKFold` validation, and inference |
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

### Automated Tests

```bash
pytest
```

---

## 5. Dataset and Model Summary

### Datasets

| Dataset | Observations | Defect-Prone (1) | Candidate-Clean (0) | Repositories | Purpose |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `csharp_empirical_v1` (v1.0.0) | 483 | 226 (46.79%) | 257 (53.21%) | `Humanizer` (291), `CommandLineParser` (101), `MediatR` (91) | Initial exploratory corpus |
| `csharp_empirical_v2` (v2.0.0) | 578 | 279 (48.27%) | 299 (51.73%) | `Humanizer` (291), `Serilog` (134), `MediatR` (91), `Polly` (34), `FluentValidation` (28) | 5-fold `GroupKFold` and nested CV benchmark |
| Historical holdout | 159 | 79 (49.69%) | 80 (50.31%) | `JamesNK/Newtonsoft.Json` (159) | Historical external evaluation of baseline RF (excluded from optimization) |

Positive labels (`1`) are heuristic SZZ attributions from bug-fixing commits. Negative labels (`0`) are candidate-clean methods sampled from `HEAD` with no recorded bug fixes in the mined commit window.

### Model Configurations (Trained on Dataset #2, $N = 578$)

| Parameter | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) |
| :--- | ---: | ---: | ---: |
| Estimator | `RandomForestClassifier` | `RandomForestClassifier` | `ExtraTreesClassifier` |
| Estimators (`n_estimators`) | 100 | 200 | 200 |
| Maximum depth (`max_depth`) | 8 | 6 | 6 |
| Minimum split (`min_samples_split`) | 5 | 10 | 8 |
| Minimum leaf (`min_samples_leaf`) | 4 | 8 | 6 |
| Maximum features (`max_features`) | `sqrt` | `log2` | `log2` |
| Class weight | `balanced` | `balanced` | `balanced` |
| Random state | 42 | 42 | 42 |

### Nested Cross-Validation Comparison (Dataset #2, 5 Outer $\times$ 4 Inner `GroupKFold`)

| Model | Outer ROC-AUC | Outer PR-AUC | Outer Brier | Outer F1 ($\tau=0.50$) | Nested $\tau_{\text{inner}}^*$ F1 | Pooled OOF F1 ($\tau_{\text{inner}}^*$) | Pooled OOF Recall ($\tau_{\text{inner}}^*$) | Pooled OOF Precision ($\tau_{\text{inner}}^*$) | Pooled OOF Accuracy ($\tau_{\text{inner}}^*$) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | ---: |
| Baseline RF (`rf_compact_regularized`) | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 | 0.6879 ± 0.0243 | 0.7408 ± 0.0760 | 0.7294 | 88.89% | 61.85% | 68.17% |
| Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | 0.7216 ± 0.1156 | 0.6465 ± 0.1026 | 0.2055 ± 0.0374 | 0.7517 ± 0.0709 | 0.7539 ± 0.0706 | 0.7406 | 88.53% | 63.66% | 70.07% |
| Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) | 0.7349 ± 0.0703 | 0.6443 ± 0.0496 | 0.2062 ± 0.0213 | 0.6867 ± 0.1394 | 0.7667 ± 0.0723 | 0.7653 | 91.76% | 65.64% | 72.84% |

- **Historical Baseline Holdout (`JamesNK/Newtonsoft.Json`, $N = 159$):** Evaluated once for the original baseline RF prior to optimization (at $\tau = 0.50$: Accuracy 74.21%, Precision 69.79%, Recall 84.81%, F1 0.7657, ROC-AUC 0.8209, Brier 0.1713; at unnested CV threshold $\tau^* = 0.40$: Accuracy 75.47%, Precision 69.61%, Recall 89.87%, F1 0.7845). `Newtonsoft.Json` was excluded from the optimization experiment; the optimized models have not yet been evaluated on a new independent repository.
- **Deployed Application Configuration:** All four serialized `.joblib` bundles in `4_AppBuild/Assets/Models/` (`et_nested_opt_v3_depth6_leaf6_log2`, `rf_nested_opt_v3_depth6_leaf8_log2`, `exp_final_5fold_v2_best_rf_compact_regularized`, and `rf_csharp_empirical_model`) are selectable in the UI, with `et_nested_opt_v3_depth6_leaf6_log2` listed first. During live inference (`BugPredictor`), `predicted_label` uses `model.predict()` ($\tau = 0.50$), while `risk_category` maps `predict_proba()` to Low ($\le 0.30$), Medium ($0.31\text{--}0.60$), and High ($> 0.60$) risk bands.

---

## 6. Documentation References

| Document | Path | Scope |
| :--- | :--- | :--- |
| System Architecture | [5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md](5_Documentation/01_Architecture/SYSTEM_ARCHITECTURE.md) | Component structure and processing flow |
| Database Architecture | [5_Documentation/02_Database/DATABASE_ARCHITECTURE.md](5_Documentation/02_Database/DATABASE_ARCHITECTURE.md) | SQLite schema, tables, and SZZ provenance |
| Source Code Guide | [5_Documentation/03_SourceCode/SOURCE_CODE_GUIDE.md](5_Documentation/03_SourceCode/SOURCE_CODE_GUIDE.md) | Python packages, Roslyn AST analyzer, and build commands |
| Project Methodology | [5_Documentation/04_MachineLearning/PROJECT_METHODOLOGY.md](5_Documentation/04_MachineLearning/PROJECT_METHODOLOGY.md) | Repository selection, SZZ rules, source filtering, 26 metrics, and nested CV |
| Experimental Results | [5_Documentation/04_MachineLearning/EXPERIMENTAL_RESULTS.md](5_Documentation/04_MachineLearning/EXPERIMENTAL_RESULTS.md) | Baseline CV, historical holdout, and nested optimization results |
| Model Optimization Report | [3_TestResults/ModelOptimization/optimization_report.md](3_TestResults/ModelOptimization/optimization_report.md) | Full nested `GroupKFold` optimization study and error analysis |
| Validation & Limitations | [5_Documentation/05_Validation/VALIDATION_AND_LIMITATIONS.md](5_Documentation/05_Validation/VALIDATION_AND_LIMITATIONS.md) | Verification suite, error analysis, Bayesian base-rate analysis, and limitations |
| User Guide | [5_Documentation/06_UserGuide/USER_GUIDE.md](5_Documentation/06_UserGuide/USER_GUIDE.md) | Application pages, controls, and troubleshooting |
| Academic Report | [5_Documentation/07_AcademicReport/FINAL_REPORT.md](5_Documentation/07_AcademicReport/FINAL_REPORT.md) | Consolidated academic research report |
| Developer Study Protocol | [5_Documentation/07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md](5_Documentation/07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md) | Double-blind review protocol template (24 methods) |
| Defense Validation | [5_Documentation/09_Defense/DEFENSE_PACKAGE_VALIDATION.md](5_Documentation/09_Defense/DEFENSE_PACKAGE_VALIDATION.md) | Defense package inventory and numerical reference |
| Presentation Decks | [6_Presentation/](6_Presentation/) | Markdown slide decks (`01` through `07`) |
