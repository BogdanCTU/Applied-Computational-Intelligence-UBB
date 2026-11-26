# Testing Guide

## 1. Automated Test Suite (`2_SourceCode/Tests/`)

Run the full automated suite:
```bash
.venv/bin/pytest 2_SourceCode/Tests/ -v
```

### Test Modules & Fixtures
- `2_SourceCode/Tests/fixtures/`:
  - `verified_buggy.cs` — resource leak, null dereference after `FirstOrDefault`, unsafe `as`-cast dereference.
  - `verified_fixed.cs` — corrected `using`, null-check, and `is not string` variants.
  - `complex_clean_hard_negative.cs` — multi-guard, properly disposed stream reader loop.
  - `malformed_syntax.cs` — syntax-broken C# file verifying `ANALYSIS_ERROR` refusal of `CLEAN`.
  - `diverse_constructs.cs` — structs, records, nested classes, constructors, static/generic/async/expression-bodied/overloaded methods.
- `test_dataset_pipeline.py` — deduplication, cross-label conflict rejection, commit classification, InferredBugs ingestion & exclusions, repository split zero-leakage verification.
- `test_roslyn_preprocessing.py` — C# construct extraction, line mapping, syntax error reporting, controlled normalization.
- `test_feature_extractors.py` — all 5 extractors, determinism, empty/missing semantic handling, `A`–`I` train/infer parity.
- `test_ml_pipeline_and_calibration.py` — 3-way threshold calibration, Random Forest grouped CV training, bundle persistence & reload parity.
- `test_explainability.py` — additive Saabas tree-path decomposition check (`bias + sum == predict_proba`), permutation importance, suspicious-method ranking.
- `test_database_persistence.py` — SQLite foreign keys, blob deduplication, model registry, detection run CRUD.
- `test_gui_and_cli.py` — `py_compile` checks, CLI smoke check, headless Streamlit `AppTest` rendering across all 6 pages.
- `test_end_to_end.py` — full Roslyn -> FeaturePipeline -> RandomForest -> Explainability tests on all 5 C# fixtures.
