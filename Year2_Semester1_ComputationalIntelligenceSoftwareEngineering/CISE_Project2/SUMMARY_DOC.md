# Executive Project Summary — C# Static Bug Detection (`v3.0.0`)

**Title:** Machine Learning-Based Bug Detection in C# Source Code  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science — Applied Computational Intelligence (CISE Project 2)

---

## 1. System Transformation Overview

This project evolved from a **5-repository method-level** defect predictor (`csharp_empirical_v2`, 578 methods, 26 metrics) into a **106-repository class- and file-level** C# static bug detection platform (`csharp_class_empirical_v3`, 5,711 classes, 40 metrics) optimized for **high precision**.

| Dimension | Legacy Method v2 | Transformed Class/File v3.0.0 |
|---|---|---|
| Primary Prediction Target | Individual C# methods | Complete C# classes / structs / records (+ multi-class `.cs` files) |
| Empirical Corpus | `5` repos, `578` methods (+`159` holdout) | **`106` public C# repos**, **`5,711` classes** (`84` dev / `22` holdout repos) |
| Roslyn Feature Schema | `26` method metrics (`v1.0.0`) | **`40` isolated class metrics (`v3.0.0`)** + legacy `26` method metrics |
| Precision Target | Unconstrained / recall-tilted (`64.21%` CV, `69.61%` holdout) | **>= 80% preferred / >= 75% min** with recall >= 50% |
| Achieved Champion Precision | `69.61%` (Newtonsoft holdout at $\tau=0.40$) | **82.30% Nested CV OOF / 83.43% Untouched Holdout ($\tau=0.600$)** |
| Achieved Champion Recall / AUC | `89.87%` / `0.8209` ROC-AUC | **61.99% Recall / 0.8449 ROC-AUC / 0.8327 PR-AUC** |
| Application Interface | Method paste / single-method scan | **Class paste, full multi-class `.cs` upload, unified ModelManager, legacy method mode** |

---

## 2. Empirical Dataset & Data Quality (`1_Database/`)

- **GitHub Discovery & Collection (`class_v3_20261121_124127`):** Queried `300` star-stratified non-fork non-archived C# repositories (`304` queued including local/existing seeded repos), excluded `15` (lack of production `.cs` files, missing bug-fix commits, or insufficient buggy/clean classes), failed `0`, and fully mined **`106` repositories** (`28,972` commits, `158,722` commit file entries, `16,161` SZZ blame traces stored in SQLite `1_Database/SQLite/bug_detection.db`).
- **Provenance & Labeling Integrity:**
  - **Label 1 (`2,829` classes, `49.54%`):** Extracted from pre-fix parent revisions of commits traced via strict heuristic bug-fix classification and `git blame -w -M -C` SZZ mapping to the innermost enclosing type.
  - **Label 0 (`2,882` classes, `50.46%`):** Candidate-clean substantive production classes sampled from `HEAD` files having zero bug-fixing or SZZ history in the mined window (**Open-World Assumption**: not guaranteed defect-free).
- **Duplicate & Leakage Audit (`collection_summary_v3.json`):** `5,743` candidate records reduced to `5,711` by removing `28` intra-repository exact duplicates and `4` repeated structural revisions (`0` cross-repository exact duplicates, `0` conflicting clean classes, `0` test files); `819` distinct historical class revisions were retained and strictly grouped by `repository_id` during train/test/CV splits so no historical revision ever straddles folds.

---

## 3. Roslyn `v3.0.0` Analyzer & Application Architecture (`2_SourceCode/`)

- **`2_SourceCode/RoslynAnalyzer/Program.cs` (.NET 9.0):** Supports C# `LanguageVersion.Latest` (records, structs, primary constructors, file-scoped namespaces), `--batch-stdin` NDJSON streaming, strict nested-type isolation (`GetTypeOwnedNodes<T>` + nested span subtraction from `class_loc`), and outputs structured JSON (`FileMetadata`, `ClassLocation`, `ClassMetrics`, nested `MethodLocation`s, `ExtractionWarnings`, `ParsingDiagnostics`).
- **`2_SourceCode/Python/ml/` (`model_manager.py`, `predictor.py`, `cross_validation.py`, `experiment_runner.py`):**
  - `ModelManager.list_saved_models()` provides an authoritative single registry serving all 8 Streamlit pages (`class_precision_champion_v3` first, followed by 7 class bundles and 4 preserved method bundles).
  - `BugPredictor` executes explicit threshold classification `int(prob >= self.decision_threshold)` using `predict_proba()[:, 1]` for both pasted classes (`predict_class_code`) and multi-class `.cs` uploads (`predict_csharp_file`), reporting file-level flags, max/mean probabilities, and per-class drill-down alongside an explicit static-indicator disclaimer.

---

## 4. Machine Learning Validation & Error Insights (`3_TestResults/ClassModelOptimization/`)

- **Zero-Leakage Evaluation Design:**
  - **Development Partition:** `84` repositories (`4,730` classes: `2,366` buggy, `2,364` clean).
  - **Untouched Independent Holdout:** `22` repositories (`981` classes: `463` buggy, `518` clean).
  - **5x4 Nested `GroupKFold`:** All preprocessing (median imputation, zero-variance pruning, correlation pruning / scaling where configured) and precision threshold selection (`select_precision_optimal_threshold`, prioritizing `Precision >= 0.80` & `Recall >= 0.50` maximizing $F_{0.5}$) occur **exclusively inside inner folds**.
- **Champion Performance (`rf_opt_depth12_leaf4_log2` / `class_precision_champion_v3`, $\tau = 0.600$):**
  - Exceeds the `>= 80%` preferred precision target in both Nested CV OOF (**82.30%**, outer fold range `78.27%–85.30%`, `std = 2.70%`) and Untouched Holdout (**83.43%**, `981` classes, `TP=287, FP=57, FN=176, TN=461`).
  - Nominal threshold $\tau = 0.50$ on holdout achieved `78.47%` precision / `73.22%` recall; inner-CV threshold selection lifted precision by **+4.96 percentage points** cleanly past `80%` while preserving `61.99%` recall.
- **Error Pattern Analysis (`holdout_error_analysis.csv`):**
  - Flagged TPs are structurally large/complex (`median_loc = 351.0, median_wmc = 57.0`), FNs occur primarily in concise classes containing subtle semantic defects (`median_loc = 48.0, median_wmc = 7.0`), and FPs represent structurally large candidate-clean classes (`median_loc = 186.0, median_wmc = 36.0`). Under realistic industrial defect base rates (`10%–20%`), Bayes' rule yields deployed PPV of **`38.50%–58.48%`**, reinforcing human-in-the-loop code review rather than automated blocking.

---

## 5. Preserved Historical Artifacts

All legacy method-level datasets (`v1.0.0`, `v2.0.0`), 4 `.joblib` method bundles, historical JSON evaluation outputs, pre-migration DB archive (`bug_detection_method_v2_archive.db`), and SQLite method `observations` (`877` rows) remain completely unmodified and verified via SHA-256 digests.
