# System Validation & Scientific Limitations (`v3.0.0`)

## 1. End-to-End Verification Matrix

1. **Static Analyzer Integrity (`2_SourceCode/RoslynAnalyzer/`):**
   - Verified clean Release compilation via `dotnet build 2_SourceCode/RoslynAnalyzer/RoslynAnalyzer.csproj -c Release` (`0 Warning(s), 0 Error(s)`).
   - Verified 40 isolated class metrics (`schema v3.0.0`) with nested-type exclusion (`GetTypeOwnedNodes<T>` + nested span subtraction), C# `LanguageVersion.Latest` constructs (records, primary constructors, file-scoped namespaces), `--batch-stdin` NDJSON streaming, and full backward compatibility for the 26 legacy method metrics.
2. **Database & Pipeline Non-Destructive Preservation (`1_Database/`):**
   - Archived pre-migration SQLite snapshot to [../../1_Database/SQLite/bug_detection_method_v2_archive.db](../../1_Database/SQLite/bug_detection_method_v2_archive.db).
   - Verified untouched legacy CSVs (`csharp_empirical_v1_v1.0.0.csv`, `csharp_empirical_v2_v2.0.0.csv`), all 4 historical `.joblib` models, historical `experiment_results.json` and `newtonsoft_holdout_results.json`, and all `877` SQLite method `observations` via matching SHA-256 checksums and automated tests.
   - Verified Dataset #3 (`csharp_class_empirical_v3` v3.0.0): `106` processed repositories, `5,711` classes, `0` missing feature values, SHA-256 `7087edb539cf44690a3b97fbd66f6cf0cd6853b320c328f4f58522561a07e70c`.
3. **Zero-Leakage ML Verification (`3_TestResults/ClassModelOptimization/`):**
   - Enforced strict repository-ID partitioning (`84` dev / `22` untouched holdout repos) so no class history, near-duplicate, or repository style leaked across training and evaluation sets.
   - Confirmed inner-CV threshold selection ($\tau = 0.600$ for `rf_opt_depth12_leaf4_log2`) holds out-of-sample precision of **`82.30%`** (Nested CV OOF) and **`83.43%`** (Untouched Holdout).
4. **Application & Model Registry Verification (`2_SourceCode/Python/`):**
   - Verified `ModelManager.list_saved_models()` discovers and serves all `12` bundles (`8` class-level v3.0.0 + `4` method-level v1.0.0) consistently across all 8 Streamlit pages.
   - Verified `BugPredictor.predict_class_code()` and `BugPredictor.predict_csharp_file()` across all 8 class bundles using `predict_proba()[:, 1] >= stored_decision_threshold`.

---

## 2. Scientific & Practical Limitations (Threats to Validity)

### 2.1 Open-World Assumption for Negative Labels (`Label 0`)
Negative samples (`2,882` classes) are sampled from `HEAD` files that had zero detected bug-fix commits or SZZ traces in the `250`-commit mining window. Absence of historical fix records does **not** formally guarantee defect-free code; dormant, unreported, or newly introduced bugs may reside in candidate-clean classes (**Open-World Assumption**). Consequently, predictions must be framed strictly as **ML-based static defect indications**, never as formal verification.

### 2.2 SZZ Attribution & Commit Heuristic Noise
While `BugFixDetector(..., strict_mode=True)` penalizes refactoring, formatting, Dependabot, and bulk commits (`> 18` files) and `SZZAnalyzer` uses whitespace- and rename-aware `git blame -w -M -C`, SZZ remains vulnerable to tangled commits (where bug fixes coincide with feature additions in the same commit) and deleted-line blame ambiguity.

### 2.3 Structural Metrics Blind Spot to Semantic Bugs
Holdout error analysis (`holdout_error_analysis.csv`) demonstrates that False Negatives are significantly smaller and simpler (`median_loc = 48.0`, `median_wmc = 7.0`) than True Positives (`median_loc = 351.0`, `median_wmc = 57.0`). Off-by-one boundaries, serialization attribute omissions, nullability mistakes, race conditions, and wrong API contracts inside concise classes cannot be reliably detected from AST structural counts alone without dataflow/semantic analysis.

### 2.4 False Alarms on Legitimately Complex Infrastructure Classes
Holdout False Positives (`median_loc = 186.0`, `median_wmc = 36.0`) often represent legitimately large parser/dispatcher or framework utility classes that follow repetitive safe patterns despite elevated LOC and complexity.

### 2.5 Base-Rate Shift in Deployed Codebases
Both Nested CV (`50.02%` positive) and Untouched Holdout (`47.20%` positive) reflect balanced empirical sampling for discrimination training. Under realistic industrial repository defect rates (`10%–20%`), Bayesian PPV shifts from `83.43%` toward `38.50%–58.48%`, meaning flagged classes should prioritize human code review rather than trigger hard CI/CD merge failures.

### 2.6 Binary Defense Archive Sync Notice
Pre-existing binary deliverables inside `5_Documentation/09_Defense/` (`.pptx`, `.docx`, `.pdf`) remain preserved at their original method-level state; all updated v3.0.0 slides and academic reports are maintained in Markdown under `6_Presentation/` and `5_Documentation/`.
