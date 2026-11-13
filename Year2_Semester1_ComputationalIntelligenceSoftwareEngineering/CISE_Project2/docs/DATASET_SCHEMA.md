# Dataset Schema Specification

## 1. Database Table Relationships

```
repositories (1) ───< commits (N) ───< commit_files (N)
       │                    │
       │                    └───< szz_results (N)
       │
       └───< observations (N) ───(1:1)─── features (Phase 4)
                   │
                   └───< dataset_observations >─── datasets (Phase 4)
                                                       │
                                                       └───< models (Phase 5)
```

## 2. Processed ML Dataset Column Definitions

When exported to CSV or queried for model training:

| Column Name | Data Type | Role | Description |
| :--- | :--- | :--- | :--- |
| `observation_id` | Integer | Metadata / ID | Primary key of the observation |
| `repository_id` | Integer | Metadata | Parent repository identifier |
| `repository_name` | String | Group Variable | Used for `GroupKFold` split to avoid leakage |
| `commit_sha` | String | Provenance | Git commit hash where method was observed |
| `file_path` | String | Provenance | Relative path to `.cs` file in repository |
| `class_name` | String | Provenance | Enclosing class / struct name |
| `method_name` | String | Provenance | Name of the extracted C# method |
| `method_signature` | String | Provenance | Parameterized signature for unambiguous matching |
| `label` | Integer (0 or 1) | Target ($y$) | 1 = Buggy (SZZ-traced), 0 = Candidate Clean (Stable HEAD) |
| `loc` ... `is_generic` | Numeric / Boolean (0 or 1) | Features ($X$) | 26 static code metrics extracted via Roslyn AST (23 structural/complexity metrics + 3 boolean OOP flags) |

### Labeling Semantics & Open-World Assumption (OWA)
- **Label 1 (Buggy)**: Grounded in historical pre-fix source revisions. Lines modified/deleted in bug-fixing commits are blamed to candidate Bug-Inducing Commits (BICs) via `git blame -w -M -C`, and the enclosing method in the pre-fix parent commit is extracted.
- **Label 0 (Candidate Clean)**: Sampled from repository HEAD revisions that possess zero defect-fix traces in the mined commit window. Under the Open-World Assumption (OWA) of software engineering, code without recorded bug fixes is *candidate clean*, not certified defect-free. Latent or yet-unreported bugs may exist.

### `datasets` Table (Versioned Snapshots)
- `name`: Human-readable identifier (e.g. `csharp_methods_v1`).
- `version`: Semantic version string (`1.0.0`).
- `total_count`, `buggy_count`, `non_buggy_count`, `uncertain_count`.
- `feature_names`: JSON array of included feature column names.
- `export_path`: Path to exported CSV snapshot.
