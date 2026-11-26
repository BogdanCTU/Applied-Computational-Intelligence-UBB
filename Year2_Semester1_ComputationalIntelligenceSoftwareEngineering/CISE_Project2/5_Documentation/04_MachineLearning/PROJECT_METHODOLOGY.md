# Machine Learning & Research Methodology (`v4.0.0`)

## 1. Problem Formulation: Binary C# Bug Detection Classifier

This project formulates static C# bug detection as **explicit binary classification (`BUG` vs. `CLEAN`) at the C# class/struct/record level**, with deterministic multi-class aggregation across `.cs` files:

$$\hat{p}_c = P(y_c = 1 \mid \mathbf{x}_c), \quad \hat{y}_c = \begin{cases} \text{BUG} & \text{if } \hat{p}_c \ge \tau \\ \text{CLEAN} & \text{if } \hat{p}_c < \tau \end{cases}$$

where $\mathbf{x}_c \in \mathbb{R}^{40}$ is the Roslyn static AST vector of isolated type $c$, $y_c = 1$ (`BUG`) denotes historical defect evidence traced via SZZ, $y_c = 0$ (`CLEAN`) denotes a candidate-clean class with no observed defect history under the Open-World Assumption (not formal verification), and $\tau$ is selected **exclusively inside inner CV folds**.

**Holdout Target:** Achieve $\text{Precision} \ge 75\%$ on an untouched repository-level holdout while maximizing balanced Recall and F1-score without artificially sacrificing sensitivity or tuning against holdout results.

---

## 2. Top-200 Star-Ranked Repository Collection (`run_top200_csharp_pipeline.py`)

### 2.1 Discovery & Star Ranking (`github_client.py`)
`GitHubClient.discover_top_csharp_repositories_by_stars()` queries `language:csharp fork:false archived:false` paginated strictly by **GitHub stars descending** (`sort="stars"&order="desc"`). Across **`500` discovered** repositories:
- **`133` pre-clone API exclusions** (`132` exceeding `max_repo_size_kb = 120,000` KB such as mega-monorepos `dotnet/roslyn` or `abpframework/abp`, plus `1` insufficient size/empty repo) yielded **`367` eligible candidates**.
- Full-history (`--no-tags`) cloning and mining of top candidates yielded **`200` successfully processed & validated repositories** (`4,409` [`tmenier/Flurl`] to `121,429` [`2dust/v2rayN`] stars), **`46` post-clone exclusions** (`29` `no_bug_fixing_commits_detected`, `10` `insufficient_production_csharp_files`, `5` `no_szz_traces_on_production_csharp`, `1` `no_substantive_buggy_classes`, `1` `no_candidate_clean_classes`), totaling **`179` documented exclusions** and **`0` failures**.

---

## 3. Historical SZZ Labeling & Method/Line Localization (`label_manager.py`)

1. **Strict Bug-Fix Detection (`BugFixDetector`):** Commit messages are scored for repair keywords (`fix`, `bug`, `crash`, `exception`, `null`, `regression`) while penalizing refactors/chores/merges and wide commits (`> 18` files).
2. **SZZ Blame Attribution (`SZZAnalyzer`):** Deleted production C# lines in each fixing commit are traced via `git blame -w -M -C` in the pre-fix parent commit $c_{\text{parent}}$.
3. **Class + Method + Line Localization Mapping:**
   - Every SZZ blamed line in $c_{\text{parent}}$ is resolved via Roslyn `--batch-stdin` to the innermost enclosing class/struct/record **and** the innermost enclosing method (`method_name`, `method_signature`, `method_start_line`, `method_end_line`), with contiguous lines compressed into `[start, end]` intervals (`compress_line_ranges()`).
   - Verified historical records (`7,361` rows across `4,473` SQLite BUG class observations) are persisted in `class_bug_localizations` with explicit `localization_status = 'verified_historical'` (or `'class_only'`/`'unavailable'` when a change falls outside method spans).
   - **CLEAN (`5,163` classes):** Substantive classes sampled from repository `HEAD` inside production `.cs` files untouched by bug fixes/SZZ traces (`localization_status = 'not_applicable'`).

---

## 4. Duplicate Control, Feature Sufficiency & Leakage Prevention

- **Deduplication (`DatasetBuilder`):** Across `9,646` candidates, removed `41` intra-repo exact duplicates, `12` cross-repo exact duplicates, and `5` repeated structural revisions (`0` test files, `0` conflicting clean) -> **`9,588` retained classes** (`4,425` BUG = `46.15%`, `5,163` CLEAN = `53.85%`; `1,025` distinct longitudinal revisions retained inside single-repository groups).
- **40-Feature Sufficiency Audit (`feature_sufficiency_audit.json`):** All `40` Roslyn features have `0` nulls and nonzero variance. `10` features exhibit Spearman $|\rho| > 0.90$ collinearity (`class_logical_loc`, `total_local_variable_count`, `total_statement_count`, `total_cyclomatic_complexity`, `max_method_complexity`, `std_method_complexity`, `max_nesting_depth`, `total_if_count`, `total_method_call_count`, `total_property_access_count`), leaving `30` correlation-pruned features. Ablation in `5×4` Nested CV + holdout compared all `40` vs. pruned `30`: keeping all `40` yielded higher Nested CV F1 (`0.7193` vs. `0.7160`) and higher Holdout F1/Recall/PR-AUC (`69.67%` / `62.02%` / `0.8104` vs. `68.90%` / `60.04%` / `0.8074`).

---

## 5. Zero-Leakage Classifier Training & Separate Method Localizer

1. **Strict Repository Partition:** `GroupShuffleSplit(test_size=0.20, random_state=42)` on `repository_id`:
   - **Development (160 repos, `7,546` classes):** `3,414` BUG, `4,132` CLEAN.
   - **Untouched Independent Holdout (40 repos, `2,042` classes):** `1,011` BUG, `1,031` CLEAN.
2. **Evaluated Model Families (12 configurations, 7 families):** `DummyClassifier` (`stratified`), `LogisticRegression` (`std` & `robust`), `DecisionTreeClassifier`, `RandomForestClassifier` (all-40, corr-pruned, unweighted), `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, and `CalibratedClassifierCV` (sigmoid).
3. **Inner-CV Threshold Selection (`select_classifier_threshold()`):** Inside each of the 5 outer `GroupKFold` folds, 4 inner folds optimize $\tau \in [0.30, 0.88]$ (`step=0.02`): Tier 1 requires $\text{Precision} \ge 0.77 \land \text{Recall} \ge 0.50$ maximizing $(F_1, \text{Recall}, \text{Precision})$; Tier 2 relaxes precision floor to $\ge 0.75$.
4. **Separately Validated ML Method Localizer (`method_localizer_top200_v4.joblib`):**
   - Built from `method_localization_top200_v4.csv` (`67,556` methods belonging to SZZ-localized BUG classes).
   - Trained strictly on methods from the `157` matching dev repos (`54,678` methods across `2,670` BUG classes) using the `26` method Roslyn features, evaluated on the `38` matching holdout repos (`12,878` methods across `778` BUG classes, `1,321` SZZ-buggy methods).
   - **Provenance Separation:** At inference time, exact SZZ lines are shown ONLY if a class matches historical `class_bug_localizations`; on unseen `BUG` classes, the separate ML Method Localizer ranks suspicious methods (`provenance = 'ml_estimated'`) while exact line localization is reported explicitly as **`unavailable`**. Class-level feature importances are never presented as buggy line evidence.
5. **Partial-Analysis Guard (`predict_csharp_file`):** Any `.cs` file containing Roslyn syntax errors or failed class extractions sets `analysis_complete = False` and reports `ANALYSIS INCOMPLETE` (or `BUG (PARTIAL ANALYSIS)` if another class flagged `BUG`), never `CLEAN`.
