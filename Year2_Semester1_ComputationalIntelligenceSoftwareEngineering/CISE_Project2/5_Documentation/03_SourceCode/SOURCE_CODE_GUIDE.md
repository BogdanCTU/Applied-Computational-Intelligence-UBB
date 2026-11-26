# Source Code Architecture and Developer Guide (`v4.0.0`)

**Source Root:** `2_SourceCode/`  
**Runtimes:** Python >= 3.11 / .NET 9.0 SDK  
**System:** CISE Project 2 — Machine Learning-Based C# Bug Detection Classifier  

---

## 1. Directory Structure

```text
2_SourceCode/
├── Python/
│   ├── application/pages/     # 8 Streamlit UI pages (BUG/CLEAN detection, collection, SZZ, evaluation)
│   ├── core/                  # Configuration (target=200 repos, v4.0.0), precision targets, unpickle aliases
│   ├── database/              # SQLite WAL connection, v4 migrations (class_bug_localizations), typed CRUD
│   ├── ml/                    # Preprocessing, nested GroupKFold, threshold tuner, 7 estimators, BugPredictor
│   ├── repositories/          # Star-ranked Top-200 GitHub client, full-history repo manager, fast git-log collector
│   ├── services/
│   │   ├── analyzer/          # Cached & --batch-stdin Roslyn .NET subprocess bridge
│   │   ├── dataset/           # Class/method DatasetBuilder with localization cols, FeatureExtractor, DatasetExporter
│   │   ├── labeling/          # Class+method+line SZZ/HEAD LabelManager + backfill & method localization export
│   │   └── mining/            # Strict BugFixDetector & whole-file cached SZZAnalyzer
│   ├── utils/                 # Logging and production C# source classifier
│   └── app.py                 # Streamlit main launcher and sidebar workspace summary
├── RoslynAnalyzer/
│   ├── Program.cs             # .NET 9.0 Roslyn analyzer (40 class metrics, 26 method metrics, file metadata, --batch-stdin)
│   └── RoslynAnalyzer.csproj  # Microsoft.CodeAnalysis.CSharp 4.12.0
├── Tests/                     # Automated pytest suite (including test_bug_classifier_and_localization.py)
└── Scripts/                   # Top-200 collector (run_top200_csharp_pipeline.py) & optimizer (run_top200_classifier_optimization.py)
```

---

## 2. Python Modules & v4 Changes

| Module | Path | Responsibility |
| :--- | :--- | :--- |
| Settings | `core/settings.py` | `CollectionSettings` (`target_repositories=200`, `max_repo_size_kb=120000`), `MLSettings` (`min_precision_target=0.75`), and `PredictionSettings` (`app_version="4.0.0"`). |
| Database | `database/schema.py`, `connection.py`, `repository.py` | Non-destructive migrations adding `class_bug_localizations`, `localization_status`, `affected_methods_json`, `affected_line_ranges_json`, `classification_label`, `localization_json`; CRUD methods including `insert_class_bug_localization()` and `find_verified_historical_localizations()`. |
| Roslyn Client | `services/analyzer/roslyn_client.py` | `analyze_source()`, `extract_classes()`, `find_enclosing_class()`, `analyze_batch()`, and corrected default Release DLL resolution (`bin/Release/net9.0/RoslynAnalyzer.dll`). |
| Source Classifier | `utils/source_classifier.py` | Excludes test projects, test fixtures, `bin/`/`obj/` build dirs, and generated code (`*.g.cs`, `*.Designer.cs`). |
| Repositories & Mining | `repositories/github_client.py`, `repository_manager.py`, `commit_collector.py` | `discover_top_csharp_repositories_by_stars()` (`sort="stars"&order="desc"`), full-history clone, and fast `git log --numstat` mining. |
| Labeling & Datasets | `services/labeling/label_manager.py`, `services/dataset/` | `compress_line_ranges()`, SZZ class+method+line mapping, `extract_method_localization_examples()`, and v4 dataset manifest/CSV export (`65` columns). |
| ML & Prediction | `ml/cross_validation.py`, `model_manager.py`, `predictor.py` | Added `fnr` metrics and `select_classifier_threshold()`; `ModelManager` filters out `method_localizer` from primary classifier listings; `BugPredictor` outputs `BUG`/`CLEAN`, auto-loads `method_localizer_top200_v4`, enforces incomplete-analysis refusal to label syntax-broken files `CLEAN`, and separates verified historical SZZ vs. ML suspicious methods vs. unavailable exact lines. |
| Streamlit UI | `application/pages/bug_prediction.py` (plus sibling pages) | Fixed undefined `tab3`/`tab4` reference; added `format_class_verdict()` / `format_file_verdict()`; displays `BUG DETECTED` (`st.error`), `CLEAN` (`st.success`), and `ANALYSIS INCOMPLETE` (`st.warning`). |
| Pipeline Scripts | `Scripts/run_top200_csharp_pipeline.py`, `Scripts/run_top200_classifier_optimization.py` | Top-200 star-ranked collector/exporter and nested 5×4 `GroupKFold` classifier + method localizer optimizer. |

---

## 3. Roslyn C# Analyzer (`2_SourceCode/RoslynAnalyzer/`)

`Program.cs` (`AnalyzerVersion = "2.0.0"`, `FeatureSchemaVersion = "3.0.0"`) parses with `LanguageVersion.Latest`:
- Extracts 40 isolated class metrics via `GetTypeOwnedNodes<T>()` (halting at nested type boundaries and subtracting nested line spans from `class_loc`) plus 26 owned method metrics per enclosed method.
- Reports `parsing_diagnostics` (`SyntaxError` count and messages) so `BugPredictor.predict_csharp_file()` can detect incomplete files and never misclassify partially parsed files as `CLEAN`.

---

## 4. Build, Execution, and Testing

```bash
# 1. Build .NET 9.0 Roslyn Analyzer (Release)
dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release

# 2. Run Top-200 star-ranked repository collection & Dataset v4 export
.venv/bin/python 2_SourceCode/Scripts/run_top200_csharp_pipeline.py --target-repos 200 --max-discover 500

# 3. Run classifier & method localizer optimization (5x4 Nested GroupKFold + untouched holdout)
.venv/bin/python 2_SourceCode/Scripts/run_top200_classifier_optimization.py

# 4. Run full automated test suite
.venv/bin/pytest 2_SourceCode/Tests/ -v

# 5. Launch Streamlit web application
.venv/bin/streamlit run 2_SourceCode/Python/app.py
```
