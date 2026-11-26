# Application User Guide (CLI & Streamlit GUI)

## 1. Command-Line Interface (`python -m bug_detector`)

All workflows run without the GUI using `PYTHONPATH=2_SourceCode .venv/bin/python -m bug_detector <subcommand>`:

- `init-db` — Initialize `1_Database/SQLite/bug_detector_v5.db` and run pending SQL migrations.
- `collect-inferredbugs` — Sparse-clone and validate Microsoft InferredBugs C# bug-fix pairs.
- `collect-github [--repos owner/repo ...] [--resume]` — Collect verified GitHub bug-fix pairs from local mirrors or GitHub REST API.
- `collect-hard-negatives` — Mine complex, unit-test-backed C# methods with clean recent git history.
- `build-dataset` — Run all collectors, deduplicate, generate audit report, export Parquet/CSV, and populate SQLite.
- `run-experiments` — Execute Experiments `A`–`I`, leave-one-group-out ablation, secondary baselines, and independent/hard-negative/temporal evaluation.
- `train --experiment I --activate` — Train a custom Random Forest model.
- `evaluate --split independent_test` — Re-evaluate a registered model bundle.
- `detect <file1.cs> [file2.cs ...] [--json]` — Classify every method in `.cs` files into `BUG`, `CLEAN`, `UNCERTAIN`, or `ANALYSIS_ERROR`.

## 2. Minimal Streamlit GUI

Launch from repository root:
```bash
.venv/bin/streamlit run app.py
```

### Navigation Pages
1. **Dashboard:** Active model status, dataset totals, independent/hard-negative/temporal metrics, registered models, recent detection runs.
2. **Manual Detection:** Paste C# source or upload `.cs` files, inspect `BUG`/`CLEAN`/`UNCERTAIN`/`ANALYSIS_ERROR` verdicts, navigate line-highlighted method source, inspect tree-path evidence and historical matches, and export JSON/CSV.
3. **Results:** Filter and sort persisted prediction records across runs and inspect source excerpts and local evidence.
4. **Dataset Explorer:** Browse paginated dataset samples, BUG/CLEAN distributions, defect categories, label provenance, verification status, and exclusion audit reports.
5. **Model Training:** Configure feature experiments (`A`–`I`) and Random Forest hyperparameters, train models or run the full suite, compare experiments, and activate a model.
6. **Model Configuration:** Edit and Pydantic-validate active model, feature groups, thresholds (`threshold_low < threshold_center < threshold_high`), and inference settings.
