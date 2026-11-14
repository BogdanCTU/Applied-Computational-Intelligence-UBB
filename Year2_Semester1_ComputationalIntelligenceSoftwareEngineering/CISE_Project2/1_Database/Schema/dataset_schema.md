# Processed ML Dataset Schema Specification

**Dataset Snapshots:**
- Original Baseline (v1.0.0): `1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv` (483 observations, 5 repositories)
- Processed Final (v2.0.0): `1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv` (578 observations, 7 repositories)
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

### Dataset #1 (v1.0.0 — Original Baseline)
- **Observations:** 483 total (242 buggy [50.1%], 241 non-buggy [49.9%])
- **Repositories (5):** `App-vNext/Polly`, `commandlineparser/commandline`, `Humanizr/Humanizr`, `LuckyPennySoftware/21Questions`, `serilog/serilog`
- **Balanced Class Ratio:** $1.00 : 1.00$

### Dataset #2 (v2.0.0 — Processed Final Benchmark)
- **Observations:** 578 total (279 buggy [48.3%], 299 non-buggy [51.7%])
- **Repositories (7):** Expanded with `FluentValidation/FluentValidation` (60 observations: 19 buggy, 41 clean) and `JamesNK/Newtonsoft.Json` (holdout partition: 35 observations: 18 buggy, 17 clean)
- **5-Fold Cross-Validation Pool:** 578 observations strictly partitioned by repository using `GroupKFold(n_splits=5)` ensuring zero cross-project leakage.

