# Source Code Architecture & Developer Guide

**Source Root:** `2_SourceCode/`  
**Languages:** Python 3.10+ / C# (.NET 9.0 SDK)  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Directory Structure

```text
2_SourceCode/
├── Python/
│   ├── application/pages/     # Streamlit web interface pages (8 tabs)
│   ├── core/                  # Settings, PROJECT_ROOT finder, path defaults
│   ├── database/              # SQLite connection, schema, and repository DB
│   ├── ml/                    # ML pipeline, cross-validation, models, predictor
│   ├── repositories/          # GitHub API client, git repository manager, commit collector
│   ├── services/
│   │   ├── analyzer/          # Subprocess bridge to .NET Roslyn analyzer
│   │   ├── dataset/           # Dataset builder, feature extractor, CSV exporter
│   │   ├── labeling/          # Ground-truth label manager
│   │   └── mining/            # Bug-fix detector, SZZ blame analyzer
│   ├── utils/                 # Logging, production C# file classifier
│   ├── src/                   # Compatibility facade re-exporting modules
│   └── app.py                 # Primary Streamlit application entry point
│
├── RoslynAnalyzer/
│   ├── Program.cs             # C# AST visitor calculating 26 static metrics
│   └── RoslynAnalyzer.csproj  # .NET 9 project file (Microsoft.CodeAnalysis.CSharp)
│
├── Tests/                     # 16 automated test modules (121 tests)
│
└── Scripts/                   # Operational and maintenance scripts
```

---

## 2. Python Architecture & Module Responsibilities

### `core/settings.py`
Centralizes application configuration via Pydantic models. It includes a dynamic `find_project_root()` function that walks parent directories until finding repository boundary markers (`1_Database`, `2_SourceCode`, `pytest.ini`, `.git`). It defines paths for databases, datasets, models, analyzer executables, and reports with automatic backward-compatibility fallbacks.

### `database/connection.py` & `repository.py`
- `Database`: Manages SQLite connection lifecycle, executes schema initialization, enables WAL mode, and enforces foreign keys.
- `RepositoryDB`: Provides domain-specific CRUD operations for repositories, commits, SZZ traces, observations, features, and model registry entries.

### `services/analyzer/roslyn_client.py`
Provides the Python-to-.NET bridge. It invokes `RoslynAnalyzer.dll` via `subprocess.run`, transmits C# code via `stdin` or `--file` arguments, handles UTF-8 encoding and newline normalization, and parses structured JSON output containing method signatures, byte offsets, and the 26 static code metrics.

### `utils/source_classifier.py`
Implements the production C# file filter (`is_production_csharp_file`). It eliminates test fixtures, test directories (`Tests/`, `Specs/`, `UnitTests/`), generated files (`*.Designer.cs`, `*.g.cs`), and build outputs (`bin/`, `obj/`), ensuring only real production code enters both the buggy and non-buggy datasets.

### `ml/` (Machine Learning Engine)
- `preprocessing.py`: Feature scaling, missing-value imputation, zero-variance filtering, and repository group splitting.
- `trainer.py`: Trains candidate classifiers (Random Forest, Extra Trees, Gradient Boosting, LightGBM, XGBoost, etc.).
- `cross_validation.py`: Executes 5-fold `GroupKFold` cross-validation grouped by repository name.
- `evaluator.py`: Computes accuracy, precision, recall, F1, ROC-AUC, Matthew's Correlation Coefficient (MCC), and Brier score.
- `predictor.py`: Implements real-time inference using the bundled champion model, outputting probability scores, categorical risk bands, and top influential features.

---

## 3. Roslyn C# Analyzer (`2_SourceCode/RoslynAnalyzer/`)

The Roslyn analyzer is implemented as a .NET 9 console application using `Microsoft.CodeAnalysis.CSharp`. It overrides `CSharpSyntaxWalker` to traverse C# Abstract Syntax Trees:
- **Executable statements:** `statement_count`, `loc`, `logical_loc`.
- **Complexity:** McCabe cyclomatic complexity ($M = \pi + 1$, incremented by `if`, `while`, `for`, `case`, `catch`, `&&`, `||`, `??`).
- **Nesting:** `max_nesting_depth` tracking lexical block hierarchy.
- **Language constructs:** Lambdas, LINQ expressions, object instantiations, property accessors, exception handling (`try-catch`, `throw`).

Build command:
```powershell
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release
```

---

## 4. Developer Instructions

### Installation
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Build Roslyn Analyzer
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release
```

### Running the Application
```powershell
# From repository root
streamlit run app.py
# Or directly
streamlit run 2_SourceCode/Python/app.py
```

### Running Tests
```powershell
pytest
```

