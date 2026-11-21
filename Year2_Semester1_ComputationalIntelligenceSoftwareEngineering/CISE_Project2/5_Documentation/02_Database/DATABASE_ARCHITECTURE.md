# Database Architecture and Data Provenance

**Database Path:** `1_Database/SQLite/bug_detection.db`  
**Archived Method-Level Snapshot:** `1_Database/SQLite/bug_detection_method_v2_archive.db`  
**Datasets Path:** `1_Database/Datasets/`  
**System:** CISE Project 2 — Machine Learning-Based Bug Detection in C# Source Code  

---

## 1. Storage Configuration

The system uses SQLite3 as its local relational datastore with:
- Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) for concurrent read access.
- Foreign key enforcement (`PRAGMA foreign_keys = ON;`).
- Non-destructive idempotent schema migrations in `Database._apply_migrations()` (`2_SourceCode/Python/database/connection.py`) that preserve all historical method-level tables (`observations`, `features`, `datasets`, `dataset_observations`, `models`) while adding class-level, file-level, and collection-run entities.

---

## 2. Relational Schema Summary

| Table Name | Granularity / Scope | Description | Key Constraints / Indexes |
| :--- | :--- | :--- | :--- |
| `repositories` | Collection | GitHub metadata, composite selection score/rank, exclusion reasons, and per-repo mining counts. | `full_name (UNIQUE)` |
| `repository_collection_runs` | Collection | Tracks target repository counts, discovery/selection/processed/excluded/failed totals, and checkpoint paths. | `run_id (UNIQUE)` |
| `commits` | Mining | Git commit logs, parent SHAs, author metadata, C# modification flag, and bug-fix confidence. | `(repository_id, commit_sha)`, `idx_commits_bugfix` |
| `commit_files` | Mining | File modification diffs (`change_type`, insertions, deletions, C# flag). | `(commit_id, file_path)` |
| `szz_results` | SZZ | Line-level Git blame links mapping fixing commits to candidate Bug-Inducing Commits (BICs). | `idx_szz_fixing`, `idx_szz_inducing` |
| `file_observations` | **File** | `.cs` source file revision metadata (`total_lines`, `namespace_count`, `class_count`, `method_count`, `file_fingerprint`). | `(repository_id, commit_sha, file_path)` |
| `class_observations` | **Class (Primary)** | C# class/struct/record observations (`qualified_class_name`, `type_kind`, line range, SZZ trace count, `source_fingerprint`, `structural_fingerprint`, label). | `(repository_id, commit_sha, file_path, qualified_class_name, label)`, `idx_class_obs_fp` |
| `class_features` | **Class (Primary)** | 40 isolated Roslyn AST class metrics (`feature_schema_version = 3.0.0`, `analyzer_version = 2.0.0`). | `class_observation_id (UNIQUE)` |
| `dataset_class_observations` | **Class (Primary)** | Junction table mapping versioned class datasets to `class_observations`. | `(dataset_id, class_observation_id)` |
| `observations` & `features` | Method (Legacy) | Preserved historical method-level observations and 26 method metrics for Datasets #1 and #2. | `observation_id (UNIQUE)` |
| `datasets` & `dataset_observations` | Both | Versioned dataset snapshots storing `granularity`, `repository_count`, `feature_schema_version`, `manifest_path`, and `sha256_checksum`. | `name (UNIQUE)` |
| `models` | Registry | Unified ML model registry storing `algorithm`, `granularity`, `version`, `dataset_version`, `decision_threshold`, and serialized metrics. | `name (UNIQUE)` |
| `predictions` | Inference | Inference logs storing `granularity`, `dataset_version`, `decision_threshold`, class/file metadata, probability, label, and risk category. | `idx_predictions_granularity`, `idx_predictions_created` |

Detailed SQL definitions and column schemas are located in:
- [1_Database/Schema/database_schema.md](../../1_Database/Schema/database_schema.md)
- [1_Database/Schema/dataset_schema.md](../../1_Database/Schema/dataset_schema.md)

---

## 3. Class-Level Labeling Provenance

| Step | Procedure | Output |
| :--- | :--- | :--- |
| 1. Strict Bug-Fix Detection | Score commit messages via regex patterns, issue closures, and strict FP penalties (requiring `modifies_csharp = 1`). | Candidate bug-fixing commits ($\text{confidence} \ge 0.50$). |
| 2. SZZ Line Blame | Run `git blame -w -M -C --porcelain` on deleted/modified production C# lines in the pre-fix parent commit. | Candidate Bug-Inducing Commits (BICs) and blamed line numbers. |
| 3. Enclosing Class Attribution | Resolve blamed lines to the innermost substantive C# `class`, `struct`, or `record` in the pre-fix parent revision; aggregate multi-line hits per class. | Positive class observations (`label = 1`, `evidence_category = szz_class_bic`). |
| 4. Candidate-Clean Class Sampling | Sample substantive classes from production `HEAD` files never modified by any bug-fixing commit or SZZ trace in the repository's history. | Candidate-clean class observations (`label = 0`, `evidence_category = stable_head_class`). |
| 5. Deduplication & Open-World Assumption | Deduplicate exact `source_fingerprint` matches and identical `structural_fingerprint` revisions; exclude conflicting clean labels; interpret `label = 0` under the Open-World Assumption. | Versioned class dataset (`csharp_class_empirical_v3 v3.0.0`). |
