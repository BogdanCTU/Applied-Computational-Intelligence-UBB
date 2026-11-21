# Machine Learning & Research Methodology (`v3.0.0`)

## 1. Research Objective & Problem Formulation

This study frames static defect detection in C# as **supervised binary classification at the C# type (class/struct/record) level**, with deterministic file-level aggregation across multi-type `.cs` source files. Formally, given a static Roslyn AST feature vector $\mathbf{x}_c \in \mathbb{R}^{40}$ extracted purely from an isolated type $c$ (strictly excluding nested types), the model estimates:

$$\hat{p}_c = P(y_c = 1 \mid \mathbf{x}_c), \quad \hat{y}_c = \mathbb{I}[\hat{p}_c \ge \tau]$$

where $y_c = 1$ denotes historical defect proneness traced via SZZ, $y_c = 0$ denotes a **candidate-clean** class under the Open-World Assumption (zero observed bug-fix commits in the mined commit window — **not** a formal proof of zero defects), and $\tau \in [0.30, 0.88]$ is a precision-calibrated classification threshold selected exclusively within inner CV folds.

**Decision Target:** Achieve $\text{Precision} \ge 0.80$ (preferred) or $\ge 0.75$ (minimum acceptable) while maintaining meaningful sensitivity ($\text{Recall} \ge 0.50$).

---

## 2. Repository Discovery & Resumable Corpus Construction (`run_100_repo_class_pipeline.py`)

### 2.1 Candidate Discovery & Ranking (`github_client.py`)
Repositories were queried via paginated GitHub REST API searches stratified across star tiers (`language:csharp fork:false archived:false size:150..18000 pushed:>=2019-01-01`). Each candidate was scored on repository stars, non-empty/non-archived status, recency, and C# relevance.

### 2.2 Filtering & Exclusion Protocol
After full-history Git cloning (`RepositoryManager` with `GIT_TERMINAL_PROMPT=0` and stale/incomplete clone recovery), repositories were audited and excluded when they failed empirical viability criteria:
- Insufficient production C# files (`< 5` files passing `is_production_csharp_file()`, excluding tests, `bin`/`obj`, and generated code).
- Absence of identifiable bug-fixing commits in the mined window (`max_commits=250`).
- Zero extractable substantive defect-prone or candidate-clean classes after SZZ analysis.

Across **`300` discovered** (`304` queued candidates), **`106` distinct C# repositories** succeeded with **`15` documented exclusions** and **`0` collection failures**.

---

## 3. Historical SZZ Attribution & Strict Heuristic Filtering

1. **Strict Bug-Fix Detection (`BugFixDetector` with `strict_mode=True`):** Commit messages are scored for explicit defect-repair keywords (`fix`, `bug`, `issue`, `crash`, `exception`, `null`, `regression`) while penalizing non-defect maintenance commits (`refactor`, `chore`, `style`, `docs`, `bump`, `dependabot`, `merge`, `ci`) and wide-sweeping edits (`> 18` touched files).
2. **SZZ Blame Attribution (`SZZAnalyzer`):** For each bug-fixing commit, deleted production C# lines in diffs against parent commit $c_{\text{parent}}$ are mapped via cached `git blame -w -M -C` back to bug-inducing commits (BICs).
3. **Pre-Fix Class Snapshot & Labeling (`ClassLabelManager`):**
   - **Label 1 (`2,829` classes):** Extracted from `c_parent` by mapping deleted line ranges to the innermost enclosing C# class/struct/record (`find_enclosing_class`) via batched Roslyn `--batch-stdin` parsing. Trivial stubs (`class_loc < 5` with `0` statements and `0` methods/properties) are excluded.
   - **Label 0 (`2,882` classes):** Substantive classes sampled from repository `HEAD` strictly inside production `.cs` files never touched by any bug-fixing commit or SZZ trace in the mined window.

---

## 4. Duplicate, Revision & Leakage Control (`DatasetBuilder`)

Before freezing Dataset #3 (`csharp_class_empirical_v3` v3.0.0), deterministic SHA-256 source and AST-structural fingerprinting inspected `5,743` candidate class records:
- **Exact Intra-Repo Hash Duplicates Removed:** `28`
- **Repeated Structural Revision Duplicates Removed:** `4`
- **Cross-Repository Exact Duplicates Removed:** `0`
- **Conflicting Clean Excluded:** `0`
- **Legitimate Historical Revisions Retained:** `819` (kept in Dataset #3 because bug-inducing state transitions represent real longitudinal history, and prevented from leaking across splits via **repository-level grouping**).

---

## 5. Roslyn `v3.0.0` Class Feature Schema (40 Features)

Unlike naive summation across file lines, `2_SourceCode/RoslynAnalyzer/Program.cs` isolates each `TypeDeclarationSyntax` using `GetTypeOwnedNodes<T>` (stopping traversal at nested type boundaries) and subtracts nested type line counts from outer `class_loc`. Local functions and lambdas remain isolated from parent callable complexities. Derived aggregates capture size (`class_loc`, `class_logical_loc`), composition (`method_count`, `constructor_count`, `property_count`, `field_count`, `nested_type_count`), WMC/complexity distribution (`total_cyclomatic_complexity`, `mean_method_complexity`, `max_method_complexity`, `std_method_complexity`), lexical nesting (`max_nesting_depth`, `mean_nesting_depth`), operators/control-flow/coupling totals, modifier counts (`static`, `async`, `generic`), high-risk counts (`high_complexity_method_count` $\ge 10$, `large_method_count`), and structural ratios (`complexity_concentration`, `structural_density`, `wmc_density`).

---

## 6. Zero-Leakage Validation, Model Families & Inner-CV Threshold Optimization

1. **Repository Holdout Partition:** Split via `GroupShuffleSplit(test_size=0.20, random_state=42)` on `repository_id`: **`84` Development repositories (`4,730` classes)** vs. **`22` Untouched Holdout repositories (`981` classes)**.
2. **7 Evaluated ML Model Families (`14` candidate configs):**
   - `DummyClassifier` (`stratified` baseline)
   - `LogisticRegression` (L2 regularized, standard & robust scaled, correlation-pruned)
   - `DecisionTreeClassifier` (depth/leaf regularized)
   - `RandomForestClassifier` (compact baseline + depth/leaf/`log2` regularized)
   - `ExtraTreesClassifier`
   - `HistGradientBoostingClassifier`
   - `CalibratedClassifierCV` (sigmoid RF & isotonic ET wrappers)
3. **Nested GroupKFold (`5` outer x `4` inner folds):** Median imputation, zero-variance filtering, optional correlation pruning (`threshold=0.95`), and scaling are fit **strictly inside training folds**. Within each outer fold, inner OOF probabilities sweep $\tau \in [0.30, 0.88]$ (`step=0.02`) using `select_precision_optimal_threshold()`: Tier 1 enforces $\text{Precision} \ge 0.80 \land \text{Recall} \ge 0.50$ maximizing $F_{0.5}$ (with ties favoring higher precision); Tier 2 relaxes precision floor to $0.75$.
4. **File-Level Aggregation (`predict_csharp_file`):** Analyzes every class/struct/record inside a `.cs` file independently, flagging classes where $\hat{p}_c \ge \tau$, reporting `max_defect_probability`, `mean_class_risk_score`, and `classes_flagged_count`.
