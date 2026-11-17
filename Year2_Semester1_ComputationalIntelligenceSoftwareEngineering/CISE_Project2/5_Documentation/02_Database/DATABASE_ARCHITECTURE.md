# Database Architecture and Data Provenance

**Database Path:** `1_Database/SQLite/bug_detection.db`  
**Datasets Path:** `1_Database/Datasets/`  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Storage Configuration

The system uses SQLite3 as its local relational datastore with the following connection settings:
- Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) for concurrent read access.
- Foreign key enforcement (`PRAGMA foreign_keys = ON;`).
- Secondary indexes on repository IDs, commit SHAs, labels, and observation IDs.

---

## 2. Relational Schema Summary

| Table Name | Description | Key Constraints / Indexes |
| :--- | :--- | :--- |
| `repositories` | GitHub repository metadata, clone status, and local path. | `full_name (UNIQUE)` |
| `commits` | Mined Git commits, author metadata, and bug-fix classification. | `(repository_id, commit_sha)`, `idx_commits_bugfix` |
| `commit_files` | File modifications per commit (status, additions, deletions, C# flag). | `(commit_id, file_path)` |
| `szz_results` | SZZ line-blame traces linking fixing commits to inducing commits. | `idx_szz_fixing`, `idx_szz_inducing` |
| `methods` | Method catalog across analyzed source files. | `(repository_id, file_path, class_name, method_signature)` |
| `observations` | Method observations with binary or uncertain labels ($y \in \{1, 0, -1\}$). | `idx_observations_repo`, `idx_observations_label` |
| `features` | 26 Roslyn AST static code metrics per observation. | `observation_id (UNIQUE)` |
| `datasets` | Versioned dataset snapshot metadata and class counts. | `name (UNIQUE)` |
| `dataset_observations` | Junction table linking dataset snapshots to observations. | `(dataset_id, observation_id)` |
| `models` | Registered machine learning models, parameters, and evaluation metrics. | `name (UNIQUE)` |
| `predictions` | Local inference log (timestamp, risk score, method signature). | `idx_predictions_model`, `idx_predictions_created` |

Detailed SQL definitions and column schemas are located in:
- [1_Database/Schema/database_schema.md](../../1_Database/Schema/database_schema.md)
- [1_Database/Schema/dataset_schema.md](../../1_Database/Schema/dataset_schema.md)

---

## 3. Labeling Provenance

| Step | Procedure | Output |
| :--- | :--- | :--- |
| 1. Bug-Fix Detection | Score commit messages using issue references and defect keyword regexes; penalize non-code edits. | Candidate bug-fixing commits ($\text{confidence} \ge 0.50$). |
| 2. SZZ Line Blame | Run `git blame -w -M -C` on deleted/modified production C# lines in the pre-fix parent commit. | Candidate Bug-Inducing Commits (BICs). |
| 3. Defect-Prone Extraction | Resolve blamed line numbers to the enclosing C# method AST node in the pre-fix revision. | Positive observations (`label = 1`). |
| 4. Candidate-Clean Sampling | Sample production C# methods from `HEAD` with no recorded SZZ defect traces in the mined commit window. | Candidate-clean observations (`label = 0`). |
| 5. Open-World Assumption | Treat `label = 0` as candidate-clean rather than confirmed defect-free, and `label = 1` as heuristic SZZ attribution. | Balanced dataset snapshots (`v1.0.0`, `v2.0.0`). |
