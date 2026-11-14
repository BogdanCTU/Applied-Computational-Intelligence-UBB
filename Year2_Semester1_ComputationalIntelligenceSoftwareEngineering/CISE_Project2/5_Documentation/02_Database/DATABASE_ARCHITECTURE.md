# Database Architecture & Data Provenance

**Database Path:** `1_Database/SQLite/bug_detection.db`  
**Datasets Path:** `1_Database/Datasets/`  
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Database Storage Overview

The repository utilizes SQLite as its embedded relational datastore. SQLite provides zero-configuration deployment, transactional integrity (ACID), and robust performance when configured with:
- **Write-Ahead Logging (WAL)** mode for concurrent read access.
- **Foreign Key Enforcement** (`PRAGMA foreign_keys = ON;`) to prevent orphan records.
- **Indexed Lookups** on repository IDs, commit hashes, labels, and observation IDs.

The database tracks the complete provenance of every software observation—from the raw git commit SHA down to the individual C# method AST span and its 26 extracted static metrics.

---

## 2. Table Summary

| Table Name | Description | Key Indexes |
| :--- | :--- | :--- |
| `repositories` | GitHub repository metadata (URLs, stars, clone status, default branch). | `full_name (UNIQUE)` |
| `commits` | Mined git commits, author metadata, and heuristic bug-fix classification. | `(repository_id, commit_sha)`, `idx_commits_bugfix` |
| `commit_files` | File changes per commit (status, additions, deletions, C# flag). | `(commit_id, file_path)` |
| `szz_results` | SZZ algorithm line-blame attributions from fixing commit to BIC. | `idx_szz_fixing`, `idx_szz_inducing` |
| `methods` | Method catalog across analyzed source files. | `(repository_id, file_path, class_name, method_signature)` |
| `observations` | Ground-truth observations with binary defect labels ($y \in \{0, 1\}$). | `idx_observations_repo`, `idx_observations_label` |
| `features` | 26 Roslyn-extracted AST metrics for each observation ($X$). | `observation_id (UNIQUE)` |
| `datasets` | Versioned dataset generation runs (counts, feature lists, export paths). | `name (UNIQUE)` |
| `dataset_observations` | Many-to-many junction table between datasets and observations. | `(dataset_id, observation_id)` |
| `models` | Trained machine learning model registry with serialized metrics. | `name (UNIQUE)` |
| `predictions` | Live inference audit trail (timestamp, risk score, method signature). | `idx_predictions_model`, `idx_predictions_created` |

Detailed schema SQL and column descriptions are maintained in:
- [1_Database/Schema/database_schema.md](../../1_Database/Schema/database_schema.md)
- [1_Database/Schema/dataset_schema.md](../../1_Database/Schema/dataset_schema.md)

---

## 3. Data Provenance & The SZZ Heuristic

Defect prediction models in software engineering depend heavily on ground-truth labeling fidelity. This project employs the **SZZ Algorithm** (Śliwerski, Zimmermann, and Zeller) augmented with C# production filtering:

1. **Bug-Fix Identification:** Mined commit messages are matched against standard regular expression patterns (`\b(fix(es|ed)?|bug(s)?|issue(s)?|resolve[sd]?)\b`).
2. **Line Blaming:** For each deleted line in a bug-fixing commit, `git blame -w -M -C` identifies the candidate Bug-Inducing Commit (BIC) that originally introduced the line, ignoring whitespace-only adjustments and intra-file movements.
3. **Pre-Fix Revision Extraction:** The enclosing method is extracted from the immediate parent commit of the bug-fix revision, capturing the exact buggy state of the method before corrective modification.
4. **Candidate-Clean Sampling:** Non-buggy methods are sampled from stable HEAD commits that have zero bug-fix traces in the analyzed commit window.
5. **Open-World Assumption (OWA):** Non-buggy observations are explicitly treated as *candidate clean* rather than mathematically verified bug-free, acknowledging that latent defects may exist.

