# Database Architecture — CISE Bug Detector v5.0.0

## 1. Design Principles

- **SQLite 3 with WAL & Foreign Keys:** `1_Database/SQLite/bug_detector_v5.db` enables `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL` on every connection (`2_SourceCode/bug_detector/db/connection.py`).
- **Migration-Driven Schema:** SQL migrations in `2_SourceCode/bug_detector/db/migrations/` are tracked in `schema_migrations` and applied transactionally via `run_migrations()` or `python -m bug_detector init-db`.
- **Content-Addressed Source Storage:** `source_blobs` keys C# source text by its SHA-256 `source_hash` so `source_files`, `methods`, `dataset_samples`, and `detection_runs` reference source content without storing duplicate copies.
- **Full Provenance & Auditability:** `dataset_exclusions` records every rejected InferredBugs instance, GitHub commit, and duplicate conflict; `training_experiments`, `model_versions`, `evaluation_results`, `detection_runs`, and `prediction_results` maintain full lineage between datasets, hyperparameters, thresholds, and runtime predictions.

See [database_schema_v5.md](../../1_Database/Schema/database_schema_v5.md) for the complete ERD and table definitions.
