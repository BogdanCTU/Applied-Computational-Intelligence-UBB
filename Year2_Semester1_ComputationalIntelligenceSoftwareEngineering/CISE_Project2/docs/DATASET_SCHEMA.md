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
| `label` | Integer (0 or 1) | Target ($y$) | 1 = Buggy, 0 = Candidate Non-Buggy |
| `loc` ... `object_creation_count` | Numeric (int/float) | Features ($X$) | 24 static code metrics extracted via Roslyn AST |

### `datasets` Table (Versioned Snapshots)
- `name`: Human-readable identifier (e.g. `csharp_methods_v1`).
- `version`: Semantic version string (`1.0.0`).
- `total_count`, `buggy_count`, `non_buggy_count`, `uncertain_count`.
- `feature_names`: JSON array of included feature column names.
- `export_path`: Path to exported CSV snapshot.
