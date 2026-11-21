# Source Code Architecture and Developer Guide

**Source Root:** `2_SourceCode/`  
**Runtimes:** Python >= 3.11 / .NET 9.0 SDK  
**System:** CISE Project 2 — Machine Learning-Based Bug Detection in C# Source Code  

---

## 1. Directory Structure

```text
2_SourceCode/
├── Python/
│   ├── application/pages/     # 8 Streamlit UI pages (class/file detection, collection, SZZ, evaluation)
│   ├── core/                  # Configuration, collection limits, precision targets, unpickle aliases
│   ├── database/              # SQLite WAL connection, non-destructive migrations, typed CRUD
│   ├── ml/                    # Preprocessing, nested GroupKFold, precision threshold tuning, 7 estimators, BugPredictor
│   ├── repositories/          # Paginated GitHub client & ranking, full-history repo manager, fast git-log collector
│   ├── services/
│   │   ├── analyzer/          # Cached & --batch-stdin Roslyn .NET subprocess bridge
│   │   ├── dataset/           # Class/method DatasetBuilder with deduplication, FeatureExtractor, manifest DatasetExporter
│   │   ├── labeling/          # Class-level SZZ/HEAD LabelManager + preserved method labeling
│   │   └── mining/            # Strict BugFixDetector & whole-file cached SZZAnalyzer
│   ├── utils/                 # Logging and production C# source classifier
│   └── app.py                 # Streamlit main launcher and sidebar workspace summary
├── RoslynAnalyzer/
│   ├── Program.cs             # .NET 9.0 Roslyn analyzer (40 class metrics, 26 method metrics, file metadata, --batch-stdin)
│   └── RoslynAnalyzer.csproj  # Microsoft.CodeAnalysis.CSharp 4.12.0
├── Tests/                     # Comprehensive pytest modules covering unit & integration workflows
└── Scripts/                   # Resumable 100+ collection (run_100_repo_class_pipeline.py) & optimization runners
```

---

## 2. Python Modules

| Module | Path | Responsibility |
| :--- | :--- | :--- |
| Settings | `core/settings.py` | Pydantic `CollectionSettings`, `MLSettings` (precision targets), `RoslynSettings`, `PredictionSettings`, and `find_project_root()`. |
| Database | `database/connection.py`, `schema.py`, `repository.py` | Idempotent SQLite migrations adding class/file/collection tables while preserving historical method tables. |
| Roslyn Client | `services/analyzer/roslyn_client.py` | `analyze_source()`, `extract_classes()`, `find_enclosing_class()`, `analyze_batch()` (`--batch-stdin`), and SHA-256 response caching. |
| Source Classifier | `utils/source_classifier.py` | Filters out test projects, test fixtures, build directories (`bin/`, `obj/`), and generated files (`*.g.cs`, `*.Designer.cs`). |
| Repositories & Mining | `repositories/github_client.py`, `repository_manager.py`, `commit_collector.py` | Paginated C# discovery with composite ranking, full-history clone with timeout guards, and single-call `git log --numstat` mining. |
| Bug-Fix & SZZ | `services/mining/bug_fix_detector.py`, `szz_analyzer.py` | Strict bug-fix commit classification (`strict_mode=True`) and cached whole-file `git blame -w -M -C`. |
| Labeling & Datasets | `services/labeling/label_manager.py`, `services/dataset/` | Class-level SZZ attribution, HEAD candidate-clean sampling, fingerprint deduplication, and SHA-256 manifest export. |
| ML & Prediction | `ml/cross_validation.py`, `experiment_runner.py`, `model_manager.py`, `predictor.py` | 7 retained model families, `select_precision_optimal_threshold()`, unified `ModelManager.list_saved_models()`, `BugPredictor.predict_csharp_file()`. |
| Pipeline Scripts | `Scripts/run_100_repo_class_pipeline.py`, `Scripts/run_class_model_optimization.py` | Checkpointed 100+ repo collection and nested 5x4 `GroupKFold` + holdout precision optimization. |

---

## 3. Roslyn C# Analyzer (`2_SourceCode/RoslynAnalyzer/`)

`Program.cs` (`AnalyzerVersion = "2.0.0"`, `FeatureSchemaVersion = "3.0.0"`) uses `CSharpParseOptions` with `LanguageVersion.Latest`:
- **Targets:** Identifies namespaces (block and file-scoped), `class`, `struct`, `record` (and `record struct`), constructors (including primary constructors), properties, fields, methods, and nested types.
- **Nested Type Isolation:** `GetTypeOwnedNodes<T>()` halts recursion at nested `TypeDeclarationSyntax` boundaries and subtracts nested type line spans from `class_loc`, ensuring nested classes are never double-counted inside outer classes.
- **Local Function & Lambda Isolation:** Preserves `GetMethodOwnedDescendants<T>()` exclusion of local functions and lambda expressions in both method and class member metrics.
- **Outputs:** Structured JSON containing `file_metadata`, `classes` (each with 40 `ClassMetrics` and owned `methods`), `methods`, `extraction_warnings`, and `parsing_diagnostics`.
- **High-Throughput Mode:** `--batch-stdin` streams NDJSON requests through a single compiled .NET process.

---

## 4. Build, Execution, and Testing

```bash
# 1. Activate environment (macOS / Linux)
source .venv/bin/activate

# 2. Build .NET 9.0 Roslyn Analyzer
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release

# 3. Run resumable 100+ repository collection & Dataset v3 export
python 2_SourceCode/Scripts/run_100_repo_class_pipeline.py --target-repos 106

# 4. Run nested GroupKFold precision optimization across all 7 model families
python 2_SourceCode/Scripts/run_class_model_optimization.py

# 5. Run complete automated test suite
pytest

# 6. Launch Streamlit workbench
python -m streamlit run app.py
```
