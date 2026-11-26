# Database Architecture and Data Provenance (`v4.0.0`)

**Database Path:** `1_Database/SQLite/bug_detection.db`  
**Archived Method-Level Snapshot:** `1_Database/SQLite/bug_detection_method_v2_archive.db`  
**Datasets Path:** `1_Database/Datasets/`  
**System:** CISE Project 2 — Machine Learning-Based C# Bug Detection Classifier  

---

## 1. Storage Configuration

The system uses SQLite3 as its local relational datastore with:
- Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) for concurrent read access.
- Foreign key enforcement (`PRAGMA foreign_keys = ON;`).
- Non-destructive idempotent schema migrations in `Database._apply_migrations()` (`2_SourceCode/Python/database/connection.py`) that preserve all historical method-level tables (`observations`, `features`, `datasets`, `dataset_observations`, `models`) while adding class-level, method-localization, file-level, and collection-run entities.

---

## 2. Relational Schema & Live Record Counts (`bug_detection.db`)

| Table Name | Granularity / Scope | Live Rows / Description | Key Constraints / Indexes |
| :--- | :--- | :--- | :--- |
| `repositories` | Collection | `246` repos — GitHub metadata, `language`, star ranking, exclusion reasons, and per-repo counts. | `full_name (UNIQUE)` |
| `repository_collection_runs` | Collection | Tracks target (`200`), discovery (`500`), eligible (`367`), processed (`200`), excluded (`179`), failed (`0`), and checkpoints. | `run_id (UNIQUE)` |
| `commits` | Mining | `46,053` commits — parent SHAs, author metadata, C# flag, and bug-fix confidence. | `(repository_id, commit_sha)`, `idx_commits_bugfix` |
| `commit_files` | Mining | `405,930` diffs — file modification paths, insertions, deletions, C# flag. | `(commit_id, file_path)` |
| `szz_results` | SZZ | `24,166` traces — Git blame links mapping fixing commits to candidate BICs. | `idx_szz_fixing`, `idx_szz_inducing` |
| `file_observations` | **File** | `.cs` source file revision metadata (`total_lines`, `namespace_count`, `class_count`, `method_count`, `file_fingerprint`). | `(repository_id, commit_sha, file_path)` |
| `class_observations` | **Class (Primary)** | `9,648` class/struct/record observations + `localization_status`, `affected_methods_json`, `affected_line_ranges_json`. | `(repository_id, commit_sha, file_path, qualified_class_name, label)`, `idx_class_obs_fp` |
| `class_bug_localizations` | **Localization (v4)** | `7,361` verified historical SZZ method/line-range provenance records (`4,473` BUG class observations covered). | `UNIQUE(class_observation_id, method_signature, bug_fix_commit_sha)` |
| `class_features` | **Class (Primary)** | `9,648` feature vectors — 40 isolated Roslyn AST class metrics (`feature_schema_version = 3.0.0`). | `class_observation_id (UNIQUE)` |
| `dataset_class_observations` | **Class (Primary)** | `9,588` links mapping Dataset #3 (`csharp_class_top200_v4`) to retained deduplicated `class_observations`. | `(dataset_id, class_observation_id)` |
| `observations` & `features` | Method (Legacy) | `877` preserved historical method observations and 26 method metrics (Datasets #1 and #2). | `observation_id (UNIQUE)` |
| `datasets` & `dataset_observations` | Both | `3` registered datasets (`csharp_empirical_v1` `483`, `csharp_empirical_v2` `578`, `csharp_class_top200_v4` `9,588`). `csharp_class_empirical_v3` CSV (`5,711`) is also preserved on disk. | `name (UNIQUE)` |
| `models` | Registry | Unified ML registry (`class`, `method`, and `method_localizer` granularities) storing `decision_threshold`, parameters, and metrics. | `name (UNIQUE)` |
| `predictions` | Inference | Inference logs storing `classification_label` (`BUG`/`CLEAN`), `localization_json`, `granularity`, `decision_threshold`, `risk_score`, `file_summary_json`, and timestamp. | `idx_predictions_granularity`, `idx_predictions_created` |

Detailed SQL definitions and column schemas are located in:
- [1_Database/Schema/database_schema.md](../../1_Database/Schema/database_schema.md)
- [1_Database/Schema/dataset_schema.md](../../1_Database/Schema/dataset_schema.md)

---

## 3. Class Labeling & Localization Provenance (`v4.0.0`)

| Step | Procedure | Output |
| :--- | :--- | :--- |
| 1. Strict Bug-Fix Detection | Score commit messages via regex patterns, issue closures, and strict FP penalties (`modifies_csharp = 1`). | Candidate bug-fixing commits ($\text{confidence} \ge 0.50$). |
| 2. SZZ Line Blame | Run `git blame -w -M -C --porcelain` on deleted/modified production C# lines in the pre-fix parent commit. | Candidate Bug-Inducing Commits (BICs) and blamed line numbers. |
| 3. Enclosing Class + Method + Line Localization | Resolve blamed lines to the innermost substantive C# `class`/`struct`/`record` AND enclosing method declaration (`start_line`, `end_line`), compressing contiguous lines into ranges (`compress_line_ranges`). | `BUG` class observations (`label = 1`, `evidence_category = szz_class_bic`) + `class_bug_localizations` rows (`verified_historical` / `class_only`). |
| 4. Candidate-Clean Class Sampling | Sample substantive classes from production `HEAD` files never modified by any bug-fixing commit or SZZ trace in the mined window. | `CLEAN` class observations (`label = 0`, `evidence_category = stable_head_class`, `localization_status = not_applicable`). |
| 5. Deduplication & Exports | Remove `41` intra-repo exact, `12` cross-repo exact, and `5` repeated structural revisions (`9,646` -> `9,588` retained; `1,025` distinct historical revisions kept inside repo groups). | `csharp_class_top200_v4_v4.0.0.csv` (`65` cols, SHA-256 `c7ff8436...`) + `method_localization_top200_v4.csv` (`67,556` rows). |
