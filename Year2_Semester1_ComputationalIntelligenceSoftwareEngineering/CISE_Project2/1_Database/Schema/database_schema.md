# SQLite Database Schema Specification

**Database File:** `1_Database/SQLite/bug_detection.db`  
**Engine:** SQLite 3 (WAL mode enabled, Foreign Key enforcement active)  
**System:** CISE Project 2 — Machine Learning-Based Bug Detection in C# Source Code  

---

## 1. Relational Entity Overview

```mermaid
erDiagram
    REPOSITORIES ||--o{ COMMITS : "contains"
    COMMITS ||--o{ COMMIT_FILES : "modifies"
    COMMITS ||--o{ SZZ_RESULTS : "fixes / induces"
    REPOSITORIES ||--o{ FILE_OBSERVATIONS : "snapshots"
    FILE_OBSERVATIONS ||--o{ CLASS_OBSERVATIONS : "contains"
    REPOSITORIES ||--o{ CLASS_OBSERVATIONS : "samples"
    CLASS_OBSERVATIONS ||--|| CLASS_FEATURES : "measured_by_40"
    DATASETS ||--o{ DATASET_CLASS_OBSERVATIONS : "groups"
    CLASS_OBSERVATIONS ||--o{ DATASET_CLASS_OBSERVATIONS : "included_in"
    REPOSITORIES ||--o{ METHODS : "declares_legacy"
    REPOSITORIES ||--o{ OBSERVATIONS : "samples_legacy"
    OBSERVATIONS ||--|| FEATURES : "measured_by_26_legacy"
    DATASETS ||--o{ DATASET_OBSERVATIONS : "groups_legacy"
    DATASETS ||--o{ MODELS : "trains"
    MODELS ||--o{ PREDICTIONS : "predicts"
```

---

## 2. Primary Class/File-Level & Collection Tables

### 2.1 `repositories`
Tracks discovered, selected, excluded, and processed open-source C# repositories.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT | Unique repository identifier |
| `full_name` | `TEXT` | UNIQUE NOT NULL | GitHub `owner/repo` slug |
| `name` / `owner` / `url` | `TEXT` | NOT NULL | Repository identity and clone URL |
| `description` / `license` | `TEXT` | | Description and SPDX license identifier |
| `default_branch` | `TEXT` | DEFAULT 'main' | Primary git branch |
| `stars` / `forks` / `size_kb` | `INTEGER` | DEFAULT 0 | Popularity and repository size metrics |
| `is_cloned` / `local_path` / `status` | `INTEGER` / `TEXT` | | Local clone tracking and pipeline state (`registered`, `cloned`, `synced`, `processed`, `excluded`, `failed`) |
| `selection_score` / `selection_rank` | `REAL` / `INTEGER` | | Composite discovery ranking score and rank |
| `selection_reason` / `exclusion_reason` | `TEXT` | | Explicit audit rationale for inclusion or exclusion |
| `is_selected` / `is_fork` / `is_archived` | `INTEGER` | DEFAULT 0/1 | Selection and GitHub status flags |
| `pushed_at` / `created_at_gh` | `TEXT` | | GitHub activity timestamps |
| `production_cs_files_count` / `commits_mined_count` / `bug_fixes_count` / `szz_traces_count` / `class_observations_count` | `INTEGER` | DEFAULT 0 | Per-repository mining summary counts |
| `processing_error` / `collection_run_id` | `TEXT` | | Failure diagnostics and collection batch identifier |

### 2.2 `repository_collection_runs`
Tracks resumable multi-repository collection runs (`run_id`, `target_repositories`, `discovered_count`, `selected_count`, `processed_count`, `excluded_count`, `failed_count`, `status`, `config_json`, `checkpoint_path`, `started_at`, `completed_at`).

### 2.3 `file_observations`
Tracks analyzed `.cs` source file revisions (`repository_id`, `commit_sha`, `file_path`, `total_lines`, `namespace_count`, `class_count`, `method_count`, `file_fingerprint`, `created_at`). Unique on `(repository_id, commit_sha, file_path)`.

### 2.4 `class_observations`
Primary prediction unit pairing C# class/struct/record declarations with SZZ defect provenance and fingerprints.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT | Unique class observation identifier |
| `file_observation_id` | `INTEGER` | FK -> `file_observations(id)` | Enclosing file revision record |
| `repository_id` | `INTEGER` | NOT NULL, FK -> `repositories(id)` | Source repository |
| `commit_sha` / `parent_sha` | `TEXT` | | Sampled revision SHA (pre-fix parent for Label 1, `HEAD` for Label 0) |
| `bug_fix_commit_sha` / `bug_inducing_commit_sha` | `TEXT` | | Fixing commit SHA and comma-separated blamed BIC SHAs |
| `file_path` / `namespace_name` | `TEXT` | | Production `.cs` relative path and enclosing namespace |
| `class_name` / `qualified_class_name` / `type_kind` | `TEXT` | | Type identifier, full qualified name, and `class` / `struct` / `record` |
| `start_line` / `end_line` / `is_nested` / `enclosing_type_name` | `INTEGER` / `TEXT` | | 1-based line bounds and nesting metadata |
| `source_code` / `corrected_code` | `TEXT` | | Pre-fix/sampled source and post-fix reference code |
| `source_fingerprint` / `structural_fingerprint` | `TEXT` | NOT NULL | SHA-256 hashes for exact and comment/whitespace-normalized deduplication |
| `label` / `label_confidence` | `INTEGER` / `REAL` | NOT NULL | `1` = Defect-prone class, `0` = Candidate-clean class, `-1` = Uncertain |
| `szz_trace_count` / `blamed_lines_json` | `INTEGER` / `TEXT` | | Number and list of SZZ blamed line numbers in class |
| `evidence_category` / `bug_fixing_commit_message` / `review_status` | `TEXT` | | `szz_class_bic`, `stable_head_class`, manual overrides, and commit message |

### 2.5 `class_features`
Stores the 40 static Roslyn class-level features (schema version `3.0.0`, analyzer version `2.0.0`) linked 1:1 to `class_observations(id)`:
- **Size & Composition (7):** `class_loc`, `class_logical_loc`, `method_count`, `constructor_count`, `property_count`, `field_count`, `nested_type_count`.
- **Parameters, Locals & Statements (5):** `total_parameter_count`, `max_parameter_count`, `total_local_variable_count`, `total_statement_count`, `total_return_count`.
- **Complexity & Nesting Distributions (6):** `total_cyclomatic_complexity`, `mean_method_complexity`, `max_method_complexity`, `std_method_complexity`, `max_nesting_depth`, `mean_nesting_depth`.
- **Control Flow & Operators (9):** `total_boolean_operator_count`, `total_logical_operator_count`, `total_conditional_expression_count`, `total_if_count`, `total_switch_count`, `total_loop_count`, `total_try_catch_count`, `total_throw_count`, `total_break_continue_count`.
- **Coupling & Member Access (5):** `total_method_call_count`, `total_field_access_count`, `total_property_access_count`, `total_assignment_count`, `total_object_creation_count`.
- **Modifiers & Density Ratios (8):** `static_method_count`, `async_method_count`, `generic_method_count`, `high_complexity_method_count`, `large_method_count`, `complexity_concentration`, `structural_density`, `wmc_density`.

---

## 3. Commits, SZZ, Datasets, Models & Predictions

- **`commits` & `commit_files` & `szz_results`**: Commit history, bug-fix scores, per-file diff stats, and `git blame -w -M -C` BIC traces.
- **`datasets` & `dataset_class_observations` & `dataset_observations`**: Versioned snapshots across both `granularity='class'` and historical `granularity='method'`, storing `repository_count`, `feature_schema_version`, `export_path`, `manifest_path`, and `sha256_checksum`.
- **`models`**: Unified model metadata registry (`name`, `algorithm`, `version`, `granularity`, `dataset_id`, `dataset_version`, `decision_threshold`, `threshold_selection_criterion`, `parameters_json`, `metrics_json`, `feature_names_json`, `model_file_path`).
- **`predictions`**: Inference audit log storing `granularity`, `dataset_version`, `decision_threshold`, `class_name`, `namespace_name`, `file_name`, `start_line`, `end_line`, `method_count`, `loc`, `cyclomatic_complexity`, `file_summary_json`, `predicted_label`, `risk_score`, `risk_category`, and `created_at`.

---

## 4. Historical Method-Level Tables (Preserved)

`methods`, `observations`, `features`, and `dataset_observations` remain untouched in `1_Database/SQLite/bug_detection.db` for backward compatibility with Datasets #1 (`v1.0.0`) and #2 (`v2.0.0`). An unmodified pre-migration copy is also preserved at `1_Database/SQLite/bug_detection_method_v2_archive.db`.

---

## 5. Database Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repository_id);
CREATE INDEX IF NOT EXISTS idx_commits_sha ON commits(commit_sha);
CREATE INDEX IF NOT EXISTS idx_commits_bugfix ON commits(is_bug_fix);
CREATE INDEX IF NOT EXISTS idx_commit_files_commit ON commit_files(commit_id);
CREATE INDEX IF NOT EXISTS idx_szz_fixing ON szz_results(fixing_commit_sha);
CREATE INDEX IF NOT EXISTS idx_szz_inducing ON szz_results(inducing_commit_sha);
CREATE INDEX IF NOT EXISTS idx_observations_repo ON observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_observations_label ON observations(label);
CREATE INDEX IF NOT EXISTS idx_observations_commit ON observations(commit_sha);
CREATE INDEX IF NOT EXISTS idx_features_obs ON features(observation_id);
CREATE INDEX IF NOT EXISTS idx_file_obs_repo ON file_observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_class_obs_repo ON class_observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_class_obs_label ON class_observations(label);
CREATE INDEX IF NOT EXISTS idx_class_obs_commit ON class_observations(commit_sha);
CREATE INDEX IF NOT EXISTS idx_class_obs_fp ON class_observations(source_fingerprint);
CREATE INDEX IF NOT EXISTS idx_class_obs_struct_fp ON class_observations(structural_fingerprint);
CREATE INDEX IF NOT EXISTS idx_class_features_obs ON class_features(class_observation_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_granularity ON predictions(granularity);
```
