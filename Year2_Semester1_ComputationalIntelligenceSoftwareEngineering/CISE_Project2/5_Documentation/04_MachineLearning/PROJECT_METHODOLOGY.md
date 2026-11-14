# Project Methodology: C# Software Defect Prediction Pipeline

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Role:** Canonical Technical Methodology & Data Engineering Reference  

---

## 1. Overview & Data Pipeline Architecture

The objective of this pipeline is to construct a leak-free, reproducible, method-level empirical dataset for software defect prediction in C# source code. The end-to-end data engineering architecture spans seven stages:

```
[1. GitHub Discovery & Repository Selection]
                     │
                     ▼
[2. Full-History Git Mining & Commit Persistence]
                     │
                     ▼
[3. Heuristic Bug-Fixing Commit (BFC) Detection]
                     │
                     ▼
[4. SZZ Line Blame Tracing & Bug-Inducing Commit (BIC) Identification]
                     │
                     ▼
[5. Roslyn AST Enclosing Method Localization & Metric Extraction]
                     │
                     ▼
[6. Production Code Filtering & Candidate-Clean Sampling (1:1 Ratio)]
                     │
                     ▼
[7. Repository-Aware Snapshot Versioning & Leakage-Free Partitioning]
```

---

## 2. Repository Selection & Discovery Criteria

Repositories are discovered via the GitHub REST API (`GET /search/repositories`) and filtered automatically according to empirical software engineering standards:

| Selection Dimension | Criterion | Methodological Rationale |
| :--- | :--- | :--- |
| **Language Target** | `language:csharp` | Restricts syntax to C# compilation units. |
| **Popularity & Maturity** | $\ge 100$ GitHub Stars | Filters out transient toy projects, student homework, and unmaintained personal forks. |
| **Codebase Scale** | $\ge 100$ KB physical repository size | Ensures non-trivial project volume with meaningful method distributions. |
| **Fork Exclusion** | `fork:false` | Eliminates duplicated histories and synthetic cross-project overlap. |
| **Maintenance Status** | `archived:false` | Guarantees active maintenance practices and standard issue-tracking conventions. |
| **Licensing** | Permissive Open Source (MIT, Apache-2.0, BSD) | Complies with research and educational analysis guidelines. |

### Selected Training & Holdout Repositories

| Repository ID | Full Name | Domain / Specialty | Role in Evaluation |
| :---: | :--- | :--- | :---: |
| **Repo #4** | `Humanizr/Humanizer` | String manipulation & localization library | Training (Fold 1 Val) |
| **Repo #15** | `serilog/serilog` | High-performance diagnostic logging library | Training (Fold 2 Val) |
| **Repo #3** | `LuckyPennySoftware/MediatR` | In-process mediator messaging framework | Training (Fold 3 Val) |
| **Repo #16** | `App-vNext/Polly` | Resilience and transient-fault-handling library | Training (Fold 4 Val) |
| **Repo #14** | `FluentValidation/FluentValidation` | Fluent input validation rules engine | Training (Fold 5 Val) |
| **Repo #17** | `JamesNK/Newtonsoft.Json` | Standard .NET JSON serialization library | **Quarantined Holdout** |

---

## 3. Full-History Git Mining & Incremental Synchronization

Cloning and commit traversal are implemented in `src/mining/commit_collector.py` using `GitPython`:

1. **Full-History Preservation:** Repositories are cloned without `--depth` constraints. SZZ line-level blame tracing strictly requires an unbroken commit DAG and ancestor walks.
2. **Local Path Isolation:** Repositories reside under `data/repositories/{owner}/{name}`. Path slugs are validated against `^[a-zA-Z0-9_\-\.]+$` to block directory traversal vulnerabilities.
3. **Incremental Synchronization:**
   - Commit collection queries existing hashes in SQLite (`SELECT commit_sha FROM commits WHERE repository_id = ?`).
   - Commits reachable from the default branch `HEAD` are traversed chronologically. Previously processed commit hashes are skipped.
   - New commits and associated file modifications (`commit_files` records) are persisted in atomic transactions of 100 commits to support interruption recovery.

---

## 4. Bug-Fixing Commit (BFC) Detection

Candidate bug-fixing commits are identified using a multi-pattern heuristic classifier (`src/mining/bug_fix_detector.py`):

1. **Issue Reference Linking (Base Score $\ge 0.55$):**
   - Matches issue-closing directives: `(fix|fixes|fixed|resolve|resolves|resolved|close|closes|closed)\s+(gh-|#)?\d+`.
2. **Defect Keyword Heuristics:**
   - Scans commit messages for defect indicators: `bug`, `fix`, `defect`, `regression`, `crash`, `exception`, `nullreference`, `deadlock`, `race condition`, `memory leak`.
3. **False-Positive Penalties:**
   - Non-defect maintenance commits (`typo`, `formatting`, `stylecop`, `readme`, `docs`, `release`, `bump version`) are penalized.
   - Commits that modify zero C# files receive a $-0.35$ penalty.
   - Massive multi-file bulk refactorings (>30 modified files) receive a $-0.25$ confidence deduction.
4. **Classification Boundary:**
   - Commits with aggregate confidence score $\ge 0.50$ are classified as candidate Bug-Fixing Commits.

---

## 5. SZZ Algorithm: Blame Tracing & Bug-Inducing Commits (BICs)

Defect-inducing historical revisions are identified using an enhanced implementation of the Śliwerski–Zimmermann–Zeller (SZZ) algorithm (`src/mining/szz_analyzer.py`):

```
[Candidate Bug-Fixing Commit (BFC)]
                 │
                 ▼ (Diff against mainline parent; strip comments & whitespace)
[Modified / Deleted Production C# Lines]
                 │
                 ▼ (git blame -w -M -C --porcelain)
[Candidate Bug-Inducing Commit (BIC)]
                 │
                 ▼ (Roslyn AST Enclosing Method Locator)
[Pre-Fix Method Observation: Label 1]
```

### SZZ Algorithmic Rules:
1. **Mainline Parent Comparison:** For merge commits with multiple parents, the diff is computed strictly against `parents[0]` (the target mainline parent) to isolate modifications merged into trunk.
2. **Noise & Whitespace Filtering:**
   - Empty lines and pure whitespace edits are ignored.
   - Comment modifications (`//`, `/*`, `*`) are stripped.
   - Isolated syntactic punctuation tokens (`{`, `}`, `;`) are omitted.
3. **Move & Copy Detection:**
   - Git blame runs with `-w` (ignore whitespace), `-M` (detect line moves within file), and `-C` (detect line copies from other files).
   - Blame traces are executed on the immediate pre-fix parent commit to identify the exact commit that introduced each deleted or modified line.
4. **Self-Reference Prevention:** Commits where `inducing_commit_sha == fixing_commit_sha` are discarded.

---

## 6. Method-Level Defect Labeling & Sampling Strategy

The atomic observation unit is an individual C# method syntax node:

### 6.1 Label 1: SZZ-Derived Defect Observations
- Located by mapping blamed line numbers to the enclosing method syntax node in the pre-fix revision (`commit_sha = bic_sha`).
- Captures the exact syntactic state of the method when the defect was introduced, prior to correction.

### 6.2 Label 0: Candidate-Clean Observations
- Sampled from stable repository `HEAD` commits.
- **Open-World Assumption (OWA):** In empirical software engineering, methods without recorded bug fixes cannot be proven to be permanently defect-free (latent or unreported bugs may exist). They are scientifically classified as *candidate clean*, indicating the absence of bug-fixing traces in the observed Git history.
- To avoid temporal leakage, candidate-clean methods are sampled only from methods that have survived untouched by bug fixes throughout the mined commit history.

### 6.3 1:1 Class Balancing
To prevent supervised estimators from degenerating into trivial majority predictors, candidate-clean methods are sampled to match the volume of SZZ-derived defective methods within each repository:
- Dataset Snapshot #2: 279 positive (48.27%) and 299 candidate-clean (51.73%) across 5 training repositories ($N = 578$).
- Quarantined Holdout: 79 positive (49.69%) and 80 candidate-clean (50.31%) in `Newtonsoft.Json` ($N = 159$).

---

## 7. Production-Code Source-Path Classification

To guarantee ecological validity and prevent test fixtures from biasing defect predictions, all candidate files pass through a strict classification filter (`src/utils/source_classifier.py`):

1. **Extension Verification:** Must have `.cs` extension (case-insensitive).
2. **Build Artifact Rejection:** Files residing in `obj/`, `bin/`, `.vs/`, `packages/`, or `artifacts/` are excluded.
3. **Generated Code Rejection:** Files matching `*.Designer.cs`, `*.g.cs`, `*.i.cs`, or `*.generated.cs` are excluded.
4. **Test Directory Exclusion:** Paths matching `Tests/`, `Test/`, `Specs/`, `Testing/`, `test-utils/`, and C# test project suffix conventions (`*.Tests/`, `*.Specs/`, `*.UnitTests/`, `*.IntegrationTests/`) are rejected.
5. **Test Fixture Naming Exclusion:** Filenames matching `*Tests.cs`, `*Test.cs`, `*Specs.cs`, `*Fixture.cs`, or `*Tester.cs` are rejected.
6. **Legitimate Non-Test Whitelisting:** Preserves non-test words (`ContestManager.cs`, `ProtestHandler.cs`), non-test directories (`src/TestingInfrastructure/ProductionTestConfiguration.cs`), and public assertions packaged in production DLLs (`src/FluentValidation/TestHelper/ValidatorTestExtensions.cs`).

All 578 training observations and 159 holdout observations were verified to have **0% test leakage**.

---

## 8. Static Code Metrics Suite (26 Roslyn Features)

The .NET 9.0 Roslyn Analyzer (`Microsoft.CodeAnalysis.CSharp`) extracts 26 static features across five categories:

| Category | Feature Name | Description & Roslyn AST Calculation Rule |
| :--- | :--- | :--- |
| **Basic Size** | `loc` | Non-empty physical lines spanning the method syntax node. |
| **Basic Size** | `logical_loc` | Count of executable statements + 1 for expression body. |
| **Basic Size** | `method_length` | Total raw character count of method text including trivia. |
| **Basic Size** | `parameter_count` | Number of formal parameters in `method.ParameterList`. |
| **Basic Size** | `local_variable_count` | Number of `VariableDeclaratorSyntax` nodes declared in the method. |
| **Basic Size** | `statement_count` | Number of `StatementSyntax` descendants (excluding root block). |
| **Basic Size** | `return_count` | Number of `ReturnStatementSyntax` nodes (or 1 if expression-bodied). |
| **Complexity** | `cyclomatic_complexity` | McCabe metric: $1 + \text{if} + \text{ternary} + \text{loops} + \text{switch cases} + \text{catch} + \text{logical ops}$. |
| **Complexity** | `max_nesting_depth` | Deepest block nesting level (`if`, `while`, `for`, `switch`, `try`, `using`, `lock`). |
| **Complexity** | `boolean_operator_count` | Bitwise & unary boolean negation operators (`!`, `^`, `&`, `\|`). |
| **Complexity** | `logical_operator_count` | Short-circuit boolean operators (`&&`, `\|\|`, null-coalescing `??`). |
| **Complexity** | `conditional_expression_count` | Ternary conditional expressions (`? :`). |
| **Control Flow** | `if_count` | Count of `IfStatementSyntax` nodes. |
| **Control Flow** | `switch_count` | Count of `SwitchStatementSyntax` and `SwitchExpressionSyntax` nodes. |
| **Control Flow** | `loop_count` | Total `for`, `foreach`, `while`, and `do-while` loops. |
| **Control Flow** | `try_catch_count` | Count of `TryStatementSyntax` blocks. |
| **Control Flow** | `throw_count` | Count of explicit `throw` statements and expressions. |
| **Control Flow** | `break_continue_count` | Count of `break` and `continue` jump statements. |
| **Structure / OOP** | `method_call_count` | Count of `InvocationExpressionSyntax` nodes. |
| **Structure / OOP** | `field_access_count` | Member access expressions targeting fields (lowercase / `_` convention). |
| **Structure / OOP** | `property_access_count` | Member access expressions targeting properties (PascalCase convention). |
| **Structure / OOP** | `assignment_count` | Count of `AssignmentExpressionSyntax` expressions. |
| **Structure / OOP** | `object_creation_count` | Count of `new Foo(...)` object allocation expressions. |
| **Structure / OOP** | `is_static` | Boolean indicator (1 if method carries `static` modifier, else 0). |
| **Structure / OOP** | `is_async` | Boolean indicator (1 if method carries `async` modifier, else 0). |
| **Structure / OOP** | `is_generic` | Boolean indicator (1 if method defines type parameters, else 0). |

### AST Extraction Rules
- **Local Functions and Lambdas:** Statements, variable declarations, and loops inside nested local functions (`LocalFunctionStatementSyntax`) or lambda expressions (`SimpleLambdaExpressionSyntax`) are isolated and excluded from outer method metrics.
- **Standalone Snippet Parsing:** When analyzing bare code snippets, the analyzer wraps the snippet inside `class __DummyContainer__ { ... }` to guarantee valid syntax tree compilation.

---

## 9. Data Leakage Prevention Guarantees

1. **Repository-Level Partitioning:** All cross-validation splits use `GroupKFold` grouped strictly by `repository_id`. Methods from the same codebase never appear in both training and validation slices.
2. **In-Fold Preprocessing:**
   - Median imputation and constant feature pruning are fitted strictly on each fold's training slice.
   - For linear models, `StandardScaler` is fitted exclusively on training folds.
3. **Quarantined Holdout Isolation:** `JamesNK/Newtonsoft.Json` was cloned and mined strictly after model architectures, hyperparameter selections, and decision thresholds were frozen.

---

## 10. Dataset Versioning & Database Schema

All raw and processed data are maintained in SQLite (`data/database/bug_detection.db`) with relational integrity:

```
repositories (1) ───< commits (N) ───< commit_files (N)
       │                    │
       │                    └───< szz_results (N)
       │
       └───< observations (N) ───(1:1)─── features (26 columns)
                   │
                   └───< dataset_observations >─── datasets (versioned snapshots)
```

### Versioned Snapshots
- **Snapshot #1 (`csharp_empirical_v1`, v1.0.0):** 483 observations across 3 repositories (`Humanizer`, `MediatR`, `commandline`). Preserved as historical baseline.
- **Snapshot #2 (`csharp_empirical_v2`, v2.0.0):** 578 observations across 5 repositories (`Humanizer`, `Serilog`, `MediatR`, `Polly`, `FluentValidation`). Authoritative training corpus.
- **Quarantined Holdout (`newtonsoft_holdout`):** 159 observations from `Newtonsoft.Json`. Evaluated once as an independent test set.

