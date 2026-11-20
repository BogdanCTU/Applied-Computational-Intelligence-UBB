# Source Code Architecture and Developer Guide

**Source Root:** `2_SourceCode/`  
**Runtimes:** Python >= 3.11 / .NET 9.0 SDK  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Directory Structure

```text
2_SourceCode/
├── Python/
│   ├── application/pages/     # Streamlit UI pages (8 modules)
│   ├── core/                  # Configuration, PROJECT_ROOT resolution, unpickle aliases
│   ├── database/              # SQLite connection, schema, and repository queries
│   ├── ml/                    # Preprocessing, training, cross-validation, evaluation, inference
│   ├── repositories/          # GitHub API client, Git manager, commit collector
│   ├── services/
│   │   ├── analyzer/          # Subprocess bridge to .NET Roslyn analyzer
│   │   ├── dataset/           # Dataset builder, feature extractor, CSV exporter
│   │   ├── labeling/          # Observation label manager
│   │   └── mining/            # Bug-fix detector and SZZ blame analyzer
│   ├── utils/                 # Logging and production C# file classifier
│   └── app.py                 # Streamlit main launcher and navigation
├── RoslynAnalyzer/
│   ├── Program.cs             # C# AST syntax walker computing 26 static metrics
│   └── RoslynAnalyzer.csproj  # .NET 9.0 project (Microsoft.CodeAnalysis.CSharp 4.12.0)
├── Tests/                     # 16 pytest modules (123 tests)
└── Scripts/                   # Experiment execution, nested optimization, and database audit scripts
```

---

## 2. Python Modules

| Module | Path | Responsibility |
| :--- | :--- | :--- |
| Settings | `core/settings.py` | Pydantic configuration, `find_project_root()`, storage path resolution, risk band thresholds (`0.30` / `0.60`), and unpickle aliases. |
| Database | `database/connection.py`, `database/repository.py` | SQLite WAL connection management, schema creation, and CRUD operations. |
| Roslyn Client | `services/analyzer/roslyn_client.py` | Invokes `RoslynAnalyzer.dll` via `dotnet`, normalizes line endings, and parses JSON metric output. |
| Source Classifier | `utils/source_classifier.py` | Filters out test projects, test fixtures, build directories (`bin/`, `obj/`), and generated files (`*.g.cs`, `*.Designer.cs`). |
| Mining & SZZ | `services/mining/bug_fix_detector.py`, `szz_analyzer.py` | Scores commit messages for bug fixes and traces modified lines via `git blame -w -M -C`. |
| Labeling & Datasets | `services/labeling/label_manager.py`, `services/dataset/` | Maps SZZ traces to methods, samples candidate-clean methods, extracts features, and exports CSV snapshots. |
| ML Pipeline | `ml/preprocessing.py`, `trainer.py`, `cross_validation.py`, `evaluator.py` | Median imputation, zero-variance pruning, `GroupKFold` validation, and evaluation metrics. |
| Model Manager & Predictor | `ml/model_manager.py`, `ml/predictor.py` | Loads `.joblib` bundles (`ExtraTreesClassifier` and `RandomForestClassifier`) and runs method/file inference (`model.predict()` at $\tau = 0.50$ for `predicted_label`; `predict_proba()` for risk scores). |
| Optimization Script | `Scripts/run_model_optimization.py` | Executes the $5 \times 4$ nested `GroupKFold` optimization experiment and writes artifacts to `3_TestResults/ModelOptimization/`. |

---

## 3. Roslyn C# Analyzer (`2_SourceCode/RoslynAnalyzer/`)

`Program.cs` implements a `CSharpSyntaxWalker` on `Microsoft.CodeAnalysis.CSharp` to extract 26 method-level metrics:
- **Size:** `loc`, `logical_loc`, `method_length`, `parameter_count`, `local_variable_count`, `statement_count`, `return_count`.
- **Complexity:** `cyclomatic_complexity`, `max_nesting_depth`, `boolean_operator_count`, `logical_operator_count`, `conditional_expression_count`.
- **Control Flow:** `if_count`, `switch_count`, `loop_count`, `try_catch_count`, `throw_count`, `break_continue_count`.
- **OOP and Structure:** `method_call_count`, `field_access_count`, `property_access_count`, `assignment_count`, `object_creation_count`, `is_static`, `is_async`, `is_generic`.

Statements inside nested local functions and lambda expressions are excluded from the enclosing method's statement and return counts.

---

## 4. Build, Execution, and Testing

```bash
# 1. Create and activate virtual environment (Linux / macOS)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Build .NET 9.0 Roslyn Analyzer
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release

# 4. Run automated test suite (123 tests)
pytest

# 5. Launch Streamlit application
python -m streamlit run app.py
```
