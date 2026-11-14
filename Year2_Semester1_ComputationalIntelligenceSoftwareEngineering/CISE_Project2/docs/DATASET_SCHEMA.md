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
| `label` | Integer (0 or 1) | Target ($y$) | 1 = SZZ-Derived Defect Label, 0 = Candidate-Clean Observation (Stable HEAD) |
| `loc` ... `is_generic` | Numeric / Boolean (0 or 1) | Features ($X$) | 26 static code metrics extracted via Roslyn AST (23 structural/complexity metrics + 3 boolean OOP flags) |

### Labeling Semantics & Open-World Assumption (OWA)
- **Label 1 (SZZ-Derived Buggy)**: Grounded in historical pre-fix source revisions. Lines modified/deleted in bug-fixing commits are blamed to candidate Bug-Inducing Commits (BICs) via `git blame -w -M -C`, and the enclosing method in the pre-fix parent commit is extracted. Strictly filtered by `is_production_csharp_file()` to prevent test code from entering the buggy class.
- **Label 0 (Candidate Clean)**: Sampled from repository HEAD revisions that possess zero defect-fix traces in the mined commit window. Under the Open-World Assumption (OWA) of software engineering, code without recorded bug fixes is *candidate clean*, not certified defect-free. Latent or yet-unreported bugs may exist. Filtered using the exact same `is_production_csharp_file()` rules as Label 1 to maintain methodological symmetry.

### Production Source-Path Classification Rules (`src/utils/source_classifier.py`)
To ensure high ecological validity and eliminate test-code pollution, all candidate files must satisfy:
1. **Extension Check**: Case-insensitive `.cs` extension.
2. **Build / Tooling Exclusion**: Files inside `obj/`, `bin/`, `.vs/`, `packages/`, or `artifacts/` are rejected.
3. **Generated Code Exclusion**: Files matching `*.Designer.cs`, `*.g.cs`, `*.i.cs`, or `*.generated.cs` are rejected.
4. **Test Directory Exclusion**: Matches directories named `Tests/`, `Test/`, `Specs/`, `Testing/`, `test-utils/`, and C# test project suffix conventions (`*.Tests/`, `*.Specs/`, `*.UnitTests/`, `*.IntegrationTests/`).
5. **Test Filename Exclusion**: Files ending with `*Tests.cs`, `*Test.cs`, `*Specs.cs`, `*Fixture.cs`, or `*Tester.cs` (where name is a fixture, e.g. `FooTester.cs`).
6. **Legitimate Non-Test Preservation**: Whitelists standalone generic class names (`src/Utilities/Tester.cs`), compound non-test words (`ContestManager.cs`, `ProtestHandler.cs`), non-test directories (`src/TestingInfrastructure/ProductionTestConfiguration.cs`), and public test assertions packaged in production DLLs (`src/FluentValidation/TestHelper/ValidatorTestExtensions.cs`).

### `datasets` Table (Versioned Snapshots)
- `name`: Human-readable identifier (e.g. `csharp_methods_v1`).
- `version`: Semantic version string (`1.0.0`).
- `total_count`, `buggy_count`, `non_buggy_count`, `uncertain_count`.
- `feature_names`: JSON array of included feature column names.
- `export_path`: Path to exported CSV snapshot.
