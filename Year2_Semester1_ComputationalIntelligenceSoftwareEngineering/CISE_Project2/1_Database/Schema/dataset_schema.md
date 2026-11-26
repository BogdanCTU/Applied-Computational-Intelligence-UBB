# Processed ML Dataset Schema Specification

**Dataset Snapshots:**
- Dataset #1 (`v1.0.0`): `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` (483 observations, 3 repositories)
- Dataset #2 (`v2.0.0`): `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` (578 observations, 5 repositories)
**System:** CISE Project 2 — Machine Learning-Based Software Defect Prediction for C# Source Code  

---

## 1. Column Specifications

The exported CSV datasets contain 35 columns: 8 metadata/provenance columns, 1 binary ground-truth label, and 26 numerical/boolean features extracted via Roslyn AST analysis.

| Column Index | Column Name | Data Type | Value Domain | Role | Description |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `observation_id` | Integer | $\ge 1$ | Metadata | Unique observation primary key in SQLite database |
| 2 | `repository_id` | Integer | $1 \dots 7$ | Metadata | Foreign key to `repositories.id` |
| 3 | `repository_name` | String | Categorical | Grouping | Open-source project name (e.g., `Polly`, `FluentValidation`). Used as the group variable in `GroupKFold` |
| 4 | `commit_sha` | String | 40-char Hex | Provenance | Git commit hash where the method observation was extracted |
| 5 | `file_path` | String | Path String | Provenance | Relative path to the production `.cs` file within the repository |
| 6 | `class_name` | String | Identifier | Provenance | Declaring class, struct, or interface name |
| 7 | `method_name` | String | Identifier | Provenance | Method identifier name |
| 8 | `method_signature`| String | Signature | Provenance | Fully qualified signature including parameter types |
| 9 | `label` | Integer | $\{0, 1\}$ | **Target ($y$)** | $1$ = SZZ-derived buggy observation; $0$ = Candidate-clean observation |
| 10 | `loc` | Integer | $\ge 1$ | Feature ($X$) | Lines of code (physical lines between opening and closing braces) |
| 11 | `logical_loc` | Integer | $\ge 0$ | Feature ($X$) | Executable statements and declarations count |
| 12 | `method_length` | Integer | $\ge 1$ | Feature ($X$) | Character span of the method declaration |
| 13 | `parameter_count` | Integer | $\ge 0$ | Feature ($X$) | Number of formal parameters in signature |
| 14 | `local_variable_count`| Integer | $\ge 0$ | Feature ($X$) | Number of declared local variables |
| 15 | `statement_count` | Integer | $\ge 0$ | Feature ($X$) | Total statement AST nodes |
| 16 | `return_count` | Integer | $\ge 0$ | Feature ($X$) | Number of `return` statements |
| 17 | `cyclomatic_complexity`| Integer | $\ge 1$ | Feature ($X$) | McCabe cyclomatic complexity $M = \pi + 1$ |
| 18 | `max_nesting_depth` | Integer | $\ge 0$ | Feature ($X$) | Maximum lexical block nesting depth |
| 19 | `boolean_operator_count`| Integer | $\ge 0$ | Feature ($X$) | Occurrences of boolean operators (`&&`, `\|\|`, `!`) |
| 20 | `logical_operator_count`| Integer | $\ge 0$ | Feature ($X$) | Occurrences of bitwise/logical operators (`&`, `\|`, `^`) |
| 21 | `conditional_expression_count`| Integer | $\ge 0$ | Feature ($X$) | Ternary conditional expressions (`? :`) |
| 22 | `if_count` | Integer | $\ge 0$ | Feature ($X$) | Count of `if` statements |
| 23 | `switch_count` | Integer | $\ge 0$ | Feature ($X$) | Count of `switch` statements and expressions |
| 24 | `loop_count` | Integer | $\ge 0$ | Feature ($X$) | Loop count (`for`, `foreach`, `while`, `do-while`) |
| 25 | `try_catch_count` | Integer | $\ge 0$ | Feature ($X$) | Exception handler blocks (`try-catch-finally`) |
| 26 | `throw_count` | Integer | $\ge 0$ | Feature ($X$) | Explicit `throw` statements |
| 27 | `break_continue_count`| Integer | $\ge 0$ | Feature ($X$) | Control-flow jumping statements (`break`, `continue`) |
| 28 | `method_call_count` | Integer | $\ge 0$ | Feature ($X$) | Method invocation expressions |
| 29 | `field_access_count`| Integer | $\ge 0$ | Feature ($X$) | Explicit field reference expressions |
| 30 | `property_access_count`| Integer | $\ge 0$ | Feature ($X$) | Property getter/setter access expressions |
| 31 | `assignment_count` | Integer | $\ge 0$ | Feature ($X$) | Variable and field assignment operations |
| 32 | `object_creation_count`| Integer | $\ge 0$ | Feature ($X$) | `new` expressions instantiation count |
| 33 | `is_static` | Boolean | $\{0, 1\}$ | Feature ($X$) | 1 if declared with `static`, 0 otherwise |
| 34 | `is_async` | Boolean | $\{0, 1\}$ | Feature ($X$) | 1 if declared with `async`, 0 otherwise |
| 35 | `is_generic` | Boolean | $\{0, 1\}$ | Feature ($X$) | 1 if method has generic type parameters `<T>` |

---

## 2. Labeling Methodology & Scientific Principles

### 2.1 Label 1: SZZ-Derived Defect Observations
1. **Bug-Fix Identification:** Commits whose messages match curated bug-fix patterns (e.g. `\b(fix(es|ed)?|bug(s)?|issue(s)?|resolve[sd]?)\b`) are mined.
2. **Line Blame Traceability:** Deleted or modified lines are traced back using `git blame -w -M -C` to identify the Bug-Inducing Commit (BIC).
3. **AST Extraction:** The method enclosing the blamed line in the pre-fix revision is extracted using the .NET Roslyn analyzer.
4. **Strict Production Filtering:** Observations are strictly verified against `is_production_csharp_file()` to eliminate test fixtures and generated code.

### 2.2 Label 0: Candidate-Clean Observations (Open-World Assumption)
1. **Sampling Revision:** Sampled from the stable `HEAD` commit of target repositories.
2. **Purity Criterion:** Methods must possess zero defect-fixing commit traces in the observed Git history.
3. **Methodological Note:** Under the Open-World Assumption (OWA), unblamed methods are designated *candidate-clean* rather than guaranteed bug-free, acknowledging that latent defects may remain undetected.
4. **Symmetric Filtering:** The exact same production source filtering (`is_production_csharp_file()`) is applied to prevent distribution shifts between classes.

---

## 3. Dataset Versions

### Dataset #1 (`v1.0.0` — Initial Baseline Corpus)
- **Observations:** 483 total (226 defect-prone [46.79%], 257 candidate-clean [53.21%])
- **Repositories (3):** `Humanizr/Humanizer` (291), `commandlineparser/commandline` (101), `LuckyPennySoftware/MediatR` (91)

### Dataset #2 (`v2.0.0` — Expanded Cross-Validation Corpus)
- **Observations:** 578 total (279 defect-prone [48.27%], 299 candidate-clean [51.73%])
- **Repositories (5):** `Humanizr/Humanizer` (291), `serilog/serilog` (134), `LuckyPennySoftware/MediatR` (91), `App-vNext/Polly` (34), `FluentValidation/FluentValidation` (28)
- **Validation Partitioning:** 578 observations partitioned by `repository_name` under 5-fold outer $\times$ 4-fold inner nested `GroupKFold` cross-validation.
- **Historical Independent Holdout (`1_Database/SQLite/bug_detection.db`):** `JamesNK/Newtonsoft.Json` (159 observations: 79 defect-prone, 80 candidate-clean), used exclusively for historical baseline evaluation (`rf_compact_regularized`) and excluded from nested model optimization.



---

## Dataset Snapshot #3: `csharp_class_empirical_v3` (Version 3.0.0 — Class-Level Multi-Repository Corpus)

- **File**: `1_Database/Datasets/Processed/csharp_class_empirical_v3_v3.0.0.csv`
- **Metadata**: `1_Database/Datasets/Processed/csharp_class_empirical_v3_v3.0.0_metadata.json`
- **Manifest**: `1_Database/Datasets/Processed/csharp_class_empirical_v3_v3.0.0_manifest.json`
- **SHA-256 Checksum**: `7087edb539cf44690a3b97fbd66f6cf0cd6853b320c328f4f58522561a07e70c`
- **Generation Date**: `2026-11-21T13:02:31Z` (Pipeline run `class_v3_20261121_124127`)
- **Granularity**: **Class / Struct / Record** (`class_observations` + `class_features` joined via `dataset_class_observations`)
- **Observation Count**: `5,711` classes (`2,829` defect-prone / Label 1 = `49.54%`, `2,882` candidate-clean / Label 0 = `50.46%`) across **`106` distinct public C# GitHub repositories** (`300` discovered, `304` candidates queued, `106` processed, `15` excluded with documented reasons, `0` failures).
- **Columns**: `62` exported CSV columns (`22` provenance/identifier/target metadata columns + `40` isolated numeric Roslyn `v3.0.0` class metrics with `0` missing values).

### Duplicate & Leakage Audit Summary (`collection_summary_v3.json`)

- **Candidate Records Before Filtering**: `5,743`
- **Intra-Repository Exact Hash Duplicates Removed**: `28`
- **Repeated Structural Revision Duplicates Removed**: `4`
- **Cross-Repository Exact Duplicates Detected/Removed**: `0`
- **Conflicting Candidate-Clean Excluded**: `0`
- **Test Files Excluded**: `0` (all excluded upstream via `is_production_csharp_file()`)
- **Legitimate Historical Revisions Retained**: `819` (same class across distinct defect commits/SHAs; separated at repository level during ML splitting so historical revisions never leak across train/validation/test folds)
- **Final Retained Rows**: `5,711`

### 40 Class-Level Feature Columns (Roslyn Analyzer Schema `v3.0.0`)

All metrics strictly exclude direct nested types (`GetTypeOwnedNodes<T>` AST isolation and nested line span subtraction):

1. Size & Member Composition (12): `class_loc`, `class_logical_loc`, `method_count`, `constructor_count`, `property_count`, `field_count`, `nested_type_count`, `total_parameter_count`, `max_parameter_count`, `total_local_variable_count`, `total_statement_count`, `total_return_count`
2. Complexity & Nesting (6): `total_cyclomatic_complexity`, `mean_method_complexity`, `max_method_complexity`, `std_method_complexity`, `max_nesting_depth`, `mean_nesting_depth`
3. Control Flow & Operators (9): `total_boolean_operator_count`, `total_logical_operator_count`, `total_conditional_expression_count`, `total_if_count`, `total_switch_count`, `total_loop_count`, `total_try_catch_count`, `total_throw_count`, `total_break_continue_count`
4. Coupling & Memory (5): `total_method_call_count`, `total_field_access_count`, `total_property_access_count`, `total_assignment_count`, `total_object_creation_count`
5. Modifiers & Derived Ratios (8): `static_method_count`, `async_method_count`, `generic_method_count`, `high_complexity_method_count`, `large_method_count`, `complexity_concentration`, `structural_density`, `wmc_density`

---

## Dataset Snapshot #4: `csharp_class_top200_v4` (Version 4.0.0 — Top-200 Star-Ranked Classifier Corpus)

- **File**: `1_Database/Datasets/Processed/csharp_class_top200_v4_v4.0.0.csv`
- **Metadata**: `1_Database/Datasets/Processed/csharp_class_top200_v4_v4.0.0_metadata.json`
- **Manifest**: `1_Database/Datasets/Processed/csharp_class_top200_v4_v4.0.0_manifest.json`
- **Collection Audit**: `1_Database/Datasets/Processed/collection_summary_top200_v4.json`, `1_Database/Datasets/Processed/discovered_top200_csharp_repos_v4.json`
- **SHA-256 Checksum**: `c7ff8436b3d9beae096df413985bf128095fc6b25cad0239cb27b452f07226c2`
- **Generation Date**: `2026-11-25T14:37:41Z` (Pipeline run `top200_v4_20261125_135308`, SQLite `dataset_id = 3`)
- **Granularity**: **Class / Struct / Record** with `BUG` (`1`) / `CLEAN` (`0`) target and SZZ localization provenance
- **Observation Count**: **`9,588` classes** (`4,425` `BUG` / `46.15%`, `5,163` `CLEAN` / `53.85%`) across **`200` public C# repositories** ranked by GitHub stars descending (`4,409` [`tmenier/Flurl`] to `121,429` [`2dust/v2rayN`]; `500` discovered, `367` eligible candidates, `179` documented exclusions, `0` failures)
- **Columns**: **`65` exported CSV columns** (`25` provenance/identifier/localization/target columns + `40` Roslyn `v3.0.0` numeric class metrics with `0` missing values). Adds `localization_status`, `affected_methods_json`, and `affected_line_ranges_json` relative to v3 (`62` columns).

### Duplicate & Leakage Audit Summary (`collection_summary_top200_v4.json`)

- **Candidate Records Before Filtering**: `9,646`
- **Intra-Repository Exact Duplicates Removed**: `41`
- **Cross-Repository Exact Duplicates Removed**: `12`
- **Repeated Structural Revision Duplicates Removed**: `5`
- **Conflicting Candidate-Clean Excluded / Test Files Excluded**: `0` / `0`
- **Legitimate Historical Revisions Retained**: `1,025` (isolated within single-repository groups during all splits)
- **Final Retained Rows**: **`9,588`**

### Auxiliary Corpus: `method_localization_top200_v4.csv`

- **File**: `1_Database/Datasets/Processed/method_localization_top200_v4.csv`
- **Row Count**: **`67,556` method observations** extracted from SZZ-localized `BUG` classes (`195` repositories with localized method spans; split strictly along the exact same `160` dev / `40` holdout repository boundary: `54,678` dev methods across `157` repos and `12,878` holdout methods across `38` repos, `10.26%` positive rate)
- **Purpose**: Trains and evaluates `method_localizer_top200_v4.joblib` (26 method-level Roslyn features) strictly separate from class-level `BUG`/`CLEAN` feature importances.
