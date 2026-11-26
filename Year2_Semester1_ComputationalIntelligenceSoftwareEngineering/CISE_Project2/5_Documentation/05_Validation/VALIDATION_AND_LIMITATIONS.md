# System Validation & Scientific Limitations (`v4.0.0`)

## 1. End-to-End Verification Matrix

1. **Static Analyzer Integrity (`2_SourceCode/RoslynAnalyzer/`):**
   - Verified clean Release compilation via `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release` (`0 Warning(s), 0 Error(s)`).
   - Verified 40 isolated class metrics (`schema v3.0.0`) with nested-type exclusion (`GetTypeOwnedNodes<T>` + nested span subtraction), C# `LanguageVersion.Latest` constructs, `--batch-stdin` NDJSON streaming, 26 method-level metrics, and `parsing_diagnostics` error reporting.
2. **Database & Historical Preservation (`1_Database/`):**
   - Archived pre-migration SQLite snapshot at [../../1_Database/SQLite/bug_detection_method_v2_archive.db](../../1_Database/SQLite/bug_detection_method_v2_archive.db).
   - Verified unmodified historical CSVs (`csharp_empirical_v1_v1.0.0.csv`, `csharp_empirical_v2_v2.0.0.csv`, `csharp_class_empirical_v3_v3.0.0.csv`), historical `.joblib` models, historical JSON artifacts, and `877` SQLite method `observations`.
   - Verified Top-200 Dataset (`csharp_class_top200_v4` v4.0.0): `200` processed repos, `9,588` classes (`4,425` BUG, `5,163` CLEAN), `0` missing feature values, SHA-256 `c7ff8436b3d9beae096df413985bf128095fc6b25cad0239cb27b452f07226c2`, plus `7,361` verified historical SZZ localizations in `class_bug_localizations` and `67,556` method localization rows in `method_localization_top200_v4.csv`.
3. **Zero-Leakage ML Classifier & Separate Localizer (`3_TestResults/Top200ClassifierOptimization/`):**
   - Strict repository-ID partitioning (`160` dev / `40` untouched holdout repos) prevents cross-split historical revision leakage.
   - Inner-CV threshold selection ($\tau = 0.520$ for `rf_depth12_leaf4_log2_all40`) achieves **`77.66%` Nested CV OOF precision** and **`79.47%` untouched holdout precision** (`62.02%` recall, `69.67%` F1, `0.8180` ROC-AUC, `0.8104` PR-AUC, `15.71%` FPR, `37.98%` FNR).
   - Separately validated `method_localizer_top200_v4.joblib` evaluated on the matching `38`-repo holdout (`778` BUG classes, `12,878` methods): `Top-1 = 44.99%`, `Top-3 = 68.64%`, `ROC-AUC = 0.6611`, `Precision = 22.46%`, `Recall = 28.31%`.
4. **Application & Guardrail Verification (`2_SourceCode/Python/`):**
   - `ModelManager.list_saved_models()` serves trained class & legacy method bundles consistently while filtering `method_localizer` bundles out of primary class dropdowns.
   - `BugPredictor` outputs `BUG` / `CLEAN`, preserves confidence as secondary context, separates verified SZZ historical evidence from ML-estimated suspicious methods, marks exact lines `unavailable` on unseen code, and refuses to classify syntax-broken or partially parsed `.cs` files as `CLEAN` (`ANALYSIS INCOMPLETE`).

---

## 2. Scientific & Practical Limitations (Threats to Validity)

### 2.1 Open-World Assumption for `CLEAN` Labels
Candidate-clean observations (`5,163` classes) come from production `HEAD` files with zero recorded bug fixes or SZZ traces in the mined window (`250` commits). Absence of observed fixes does **not** prove defect-free code; dormant or unreported bugs may exist (**Open-World Assumption**). Classifier outputs remain ML-based indications, not formal verification.

### 2.2 SZZ Heuristic & Tangled-Commit Noise
Even with strict `BugFixDetector` filtering and `git blame -w -M -C`, SZZ blame tracing can be affected by tangled multi-concern commits, formatting-adjacent edits, or deleted lines lacking pre-fix executable statements.

### 2.3 Unavailable Exact Line Localization on Unseen Code & Localizer Bounds
- **Exact Line Localization:** Exact buggy line ranges are **only available when a analyzed class matches a mined historical revision in `class_bug_localizations`**. On unseen code, exact line localization is explicitly **`unavailable`** (`exact_line_localization_status == "unavailable"`), and class-level feature importances are **never** presented as line-level bug proof.
- **ML Method Localizer Bounds:** Within an SZZ-buggy class, only `~10.26%` of methods contain SZZ-traced lines, so method-level binary precision at $\tau = 0.600$ is `22.46%` (`28.31%` recall, `0.6611` ROC-AUC). Its value lies strictly in ranking suspicious methods (**`68.64%` Top-3 class hit rate**) to guide human inspection—never as ground truth.

### 2.4 Structural Blind Spots on Semantic Bugs
Compact classes containing off-by-one indexing, nullability omissions, wrong API contracts, or concurrency race conditions often exhibit low LOC and low cyclomatic complexity, contributing to the holdout false-negative rate (`37.98%`, `384 / 1,011` missed BUG classes). Conversely, large well-structured parser or controller classes can trigger false positives (`15.71%` FPR, `162 / 1,031`).

### 2.5 Base-Rate Shift in Production Repositories
Holdout evaluation has `49.51%` positive class prevalence (`1,011 / 2,042`). Under realistic industrial defect prevalence (`2%–20%`), Bayesian PPV at `TPR = 62.02%` / `FPR = 15.71%` shifts to `7.45%` (at `2%`), `17.20%` (at `5%`), `30.49%` (at `10%`), and `49.67%` (at `20%`). Thus, flagged `BUG` classes should guide developer triage rather than serve as automated CI/CD merge blockers.

### 2.6 Binary Defense Package & Live Browser UI Verification Note
- Pre-existing binary deliverables inside `5_Documentation/09_Defense/` (`.pptx`, `.docx`, `.pdf`) remain preserved at their original v2 method-level snapshot; current v4.0.0 materials are maintained in Markdown under `6_Presentation/` and `5_Documentation/`.
- Automated verification validated the Roslyn build, pure Python GUI formatting helpers (`format_class_verdict`, `format_file_verdict`), AST page correctness, and `BugPredictor` end-to-end execution via `pytest`, without launching an interactive headless browser against a live Streamlit server.
