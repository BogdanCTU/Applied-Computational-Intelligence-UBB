# Project Methodology: C# Software Defect Prediction Pipeline

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  

---

## 1. Pipeline Stages

| Stage | Component | Operation |
| :---: | :--- | :--- |
| 1 | `GitHubClient` | Query GitHub REST API (`GET /search/repositories`) and register C# repositories (requires network access). |
| 2 | `RepositoryManager`, `CommitCollector` | Clone full Git history locally and persist commit metadata and file diffs in SQLite. |
| 3 | `BugFixDetector` | Score commit messages using issue references and defect keyword regexes ($\text{confidence} \ge 0.50$). |
| 4 | `SZZAnalyzer` | Trace deleted or modified production C# lines in fixing commits to candidate Bug-Inducing Commits (BICs) via `git blame -w -M -C`. |
| 5 | `LabelManager` | Map blamed lines to enclosing C# method AST nodes in the pre-fix parent commit (`label = 1`) and sample candidate-clean methods from `HEAD` (`label = 0`). |
| 6 | `FeatureExtractor`, `RoslynClient` | Extract 26 static code metrics per method via the .NET 9.0 Roslyn CLI analyzer. |
| 7 | `DatasetBuilder`, `ExperimentRunner` | Export versioned CSV snapshots and evaluate models with repository-level `GroupKFold` ($K=5$). |

---

## 2. Repository Selection Criteria

| Criterion | Filter / Rule | Rationale |
| :--- | :--- | :--- |
| Language | `language:csharp` | Restricts compilation units to C#. |
| Popularity | $\ge 100$ stars | Excludes trivial or unmaintained repositories. |
| Repository Size | $\ge 100$ KB | Ensures sufficient method count and commit history. |
| Fork Status | `fork:false` | Avoids duplicate histories across repositories. |
| Archive Status | `archived:false` | Selects actively maintained projects. |
| License | MIT, Apache-2.0, BSD | Permits academic source analysis. |

### Selected Repositories

| Repository ID | Full Name | Domain | Role |
| :---: | :--- | :--- | :--- |
| 4 | `Humanizr/Humanizer` | String manipulation and localization | Training / CV Fold 1 |
| 15 | `serilog/serilog` | Structured diagnostic logging | Training / CV Fold 2 |
| 3 | `LuckyPennySoftware/MediatR` | In-process mediator messaging | Training / CV Fold 3 |
| 16 | `App-vNext/Polly` | Resilience and transient-fault handling | Training / CV Fold 4 |
| 14 | `FluentValidation/FluentValidation` | Fluent validation rules engine | Training / CV Fold 5 |
| 17 | `JamesNK/Newtonsoft.Json` | JSON serialization framework | Independent Holdout |
| 1 | `commandlineparser/commandline` | Command-line argument parsing | Dataset #1 Exploratory |

---

## 3. Git Mining and Bug-Fixing Commit Detection

1. **Full-History Cloning:** Repositories are cloned without `--depth` truncation into `1_Database/Repositories/{owner}/{name}` so ancestor blame walks remain intact.
2. **Incremental Commit Persistence:** Commits reachable from the default branch `HEAD` are persisted in batches of 100 along with modified file paths (`commit_files`).
3. **Bug-Fix Scoring (`services/mining/bug_fix_detector.py`):**
   - Issue-closing references (`(fix|fixes|fixed|resolve|resolves|resolved|close|closes|closed)\s+(gh-|#)?\d+`) add base confidence $\ge 0.55$.
   - Defect keywords (`bug`, `fix`, `defect`, `regression`, `crash`, `exception`, `nullreference`, `deadlock`, `race condition`, `memory leak`) increase confidence.
   - Non-code or maintenance keywords (`typo`, `formatting`, `stylecop`, `readme`, `docs`, `release`, `bump version`), commits modifying zero `.cs` files ($-0.35$), and bulk edits modifying $>30$ files ($-0.25$) reduce confidence.
   - Commits with net confidence $\ge 0.50$ are marked as candidate bug-fixing commits.

---

## 4. SZZ Line-Blame Attribution

`SZZAnalyzer` (`services/mining/szz_analyzer.py`) links candidate bug-fixing commits to candidate Bug-Inducing Commits (BICs):

1. **Mainline Parent Diff:** Diffs are computed against `parents[0]` to isolate mainline changes in merge commits.
2. **Syntactic Line Filtering:** Blank lines, comment lines (`//`, `/*`, `*`), and isolated brace or semicolon tokens (`{`, `}`, `;`) are ignored.
3. **Git Blame Execution:** `git blame -w -M -C --porcelain` runs on the pre-fix parent commit (`-w` ignores whitespace, `-M` tracks intra-file moves, `-C` tracks cross-file copies).
4. **Self-Reference Filtering:** Traces where `inducing_commit_sha == fixing_commit_sha` are discarded.

---

## 5. Method-Level Labeling and Sampling

| Label | Designation | Construction Rule | Methodological Constraint |
| :---: | :--- | :--- | :--- |
| `1` | Defect-Prone | Enclosing C# method AST node in the pre-fix revision at the blamed line. | Heuristic SZZ attribution; refactoring or tangled commits can introduce label noise. |
| `0` | Candidate-Clean | Production method sampled from `HEAD` with no recorded SZZ bug-fixing traces in the mined commit window. | Open-World Assumption: absence of recorded fixes does not establish confirmed defect-free code. |
| `-1` | Uncertain | Modifications outside method bodies or ambiguous traces. | Excluded from supervised training and evaluation snapshots. |

- **Class Balancing (1:1):** Candidate-clean methods are sampled per repository to match the count of SZZ-labeled defect-prone methods (Dataset #2: 279 defect-prone, 299 candidate-clean; Holdout: 79 defect-prone, 80 candidate-clean).
- **Temporal Asymmetry:** Defect-prone methods are extracted from historical pre-fix commits, whereas candidate-clean methods are sampled from `HEAD`.

---

## 6. Production Source-Path Filtering

`is_production_csharp_file()` (`utils/source_classifier.py`) excludes non-production files prior to observation creation:

| Rule Type | Excluded Patterns |
| :--- | :--- |
| Extension | Non-`.cs` files |
| Build & Package Directories | `obj/`, `bin/`, `.vs/`, `packages/`, `artifacts/` |
| Generated Code | `*.Designer.cs`, `*.g.cs`, `*.i.cs`, `*.generated.cs` |
| Test Directories & Projects | `Tests/`, `Test/`, `Specs/`, `Testing/`, `test-utils/`, `*.Tests/`, `*.Specs/`, `*.UnitTests/`, `*.IntegrationTests/` |
| Test Filenames | `*Tests.cs`, `*Test.cs`, `*Specs.cs`, `*Fixture.cs`, `*Tester.cs` |

Legitimate production files containing substrings such as `ContestManager.cs`, `ProtestHandler.cs`, or `ValidatorTestExtensions.cs` are preserved.

---

## 7. Static Code Metrics (26 Roslyn Features)

The .NET 9.0 Roslyn analyzer (`2_SourceCode/RoslynAnalyzer/`) computes 26 method-level metrics:

| Category | Metric | Definition |
| :--- | :--- | :--- |
| Basic Size | `loc` | Non-empty physical lines spanning the method node |
| Basic Size | `logical_loc` | Executable statements (+1 for expression body) |
| Basic Size | `method_length` | Character length of the method syntax span |
| Basic Size | `parameter_count` | Formal parameters in `ParameterList` |
| Basic Size | `local_variable_count` | `VariableDeclaratorSyntax` nodes in method scope |
| Basic Size | `statement_count` | `StatementSyntax` descendants (excluding root block) |
| Basic Size | `return_count` | `ReturnStatementSyntax` nodes (or 1 for expression body) |
| Complexity | `cyclomatic_complexity` | $1 + \text{if} + \text{ternary} + \text{loops} + \text{switch cases} + \text{catch} + \text{logical ops}$ |
| Complexity | `max_nesting_depth` | Maximum block nesting depth (`if`, `loop`, `switch`, `try`, `using`, `lock`) |
| Complexity | `boolean_operator_count` | Bitwise and unary boolean operators (`!`, `^`, `&`, `\|`) |
| Complexity | `logical_operator_count` | Short-circuit boolean and null-coalescing operators (`&&`, `\|\|`, `??`) |
| Complexity | `conditional_expression_count` | Ternary conditional expressions (`? :`) |
| Control Flow | `if_count` | `IfStatementSyntax` nodes |
| Control Flow | `switch_count` | `SwitchStatementSyntax` and `SwitchExpressionSyntax` nodes |
| Control Flow | `loop_count` | `for`, `foreach`, `while`, and `do-while` statements |
| Control Flow | `try_catch_count` | `TryStatementSyntax` blocks |
| Control Flow | `throw_count` | Explicit `throw` statements and expressions |
| Control Flow | `break_continue_count` | `break` and `continue` statements |
| Structure / OOP | `method_call_count` | `InvocationExpressionSyntax` nodes |
| Structure / OOP | `field_access_count` | Member access expressions targeting fields |
| Structure / OOP | `property_access_count` | Member access expressions targeting properties |
| Structure / OOP | `assignment_count` | `AssignmentExpressionSyntax` nodes |
| Structure / OOP | `object_creation_count` | `new` object creation expressions |
| Structure / OOP | `is_static` | `1` if `static` modifier present, else `0` |
| Structure / OOP | `is_async` | `1` if `async` modifier present, else `0` |
| Structure / OOP | `is_generic` | `1` if generic type parameters present, else `0` |

Statements, variables, and returns inside nested local functions or lambda expressions are excluded from the enclosing method's counts.

---

## 8. Validation Partitioning and Preprocessing Isolation

1. **Repository-Level Partitioning:** Cross-validation uses `GroupKFold` ($K=5$) grouped by `repository_id`, separating repositories between training and validation folds so methods from the same repository do not appear in both partitions simultaneously.
2. **In-Fold Preprocessing:** Median imputation, zero-variance feature pruning, and `StandardScaler` (for linear models) are fitted strictly on each fold's training partition.
3. **Independent Holdout:** `JamesNK/Newtonsoft.Json` (159 methods) was evaluated separately after model hyperparameters and decision thresholds were frozen.
