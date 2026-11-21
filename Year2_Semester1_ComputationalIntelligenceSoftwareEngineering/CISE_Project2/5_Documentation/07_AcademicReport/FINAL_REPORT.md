# Machine Learning-Based Bug Detection in C# Source Code (v3.0.0)
## Comprehensive Academic Project Report — CISE Project 2

**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science  
**Programme:** Applied Computational Intelligence, Master's Degree  
**Course:** Computational Intelligence in Software Engineering (CISE), Project 2  
**Date:** November 21, 2026  

---

## 1. Abstract & Research Context

Software defect prediction (SDP) assists engineering teams by triaging source modules before dynamic test suites or production failures uncover costly bugs. While earlier project iterations modeled individual C# methods across five repositories (`578` training methods, `69.61%` holdout precision), real-world static inspection operates on entire C# classes and multi-class `.cs` files and demands substantially higher positive predictive confidence (`>= 75%–80%` precision) to avoid alert fatigue.

This work transforms the system into a **106-repository class- and file-level static C# bug detection platform**. An extended .NET 9.0 Roslyn analyzer (`schema v3.0.0`) extracts `40` isolated class metrics across C# classes, structs, and records while excluding nested-type bleed-over. Mining `300` star-stratified public GitHub C# repositories yielded `106` validated repositories (`5,711` unique/deduplicated class observations: `2,829` defect-prone via SZZ, `2,882` candidate-clean). Under strict repository-grouped `5x4` Nested `GroupKFold` validation (`84` development repositories) and a `22`-repository untouched holdout (`981` classes), a depth-regularized Random Forest with inner-CV threshold optimization (`tau = 0.600`, `class_precision_champion_v3`) achieves **82.30% precision / 61.71% recall** in Nested CV and **83.43% precision / 61.99% recall / 0.8449 ROC-AUC** on the untouched holdout — exceeding both the `>= 75%` minimum and `>= 80%` preferred precision targets. All predictions remain statistical risk indications rather than formal verification.

---

## 2. Problem Transformation: Method-Level v2 to Class/File-Level v3

1. **Granularity Upgrade:** Single short methods frequently lack contextual signal (`3–10` LOC), creating overlapping metric signatures between buggy and clean getters or helpers. Elevating the primary prediction target to **classes/structs/records** captures structural coupling, responsibility concentration, exception-handling surfaces, and weighted complexity per type.
2. **Multi-Class File Support:** Production `.cs` files commonly declare multiple classes, structs, or records. Rather than concatenating AST totals blindly across an entire file, the updated pipeline scores every type independently via `BugPredictor.predict_csharp_file()` and aggregates file risk via flagged class count, peak probability, and mean probability.
3. **Repository Generalization:** Scaling from `5` training repositories (`578` observations) to `106` diverse repositories (`5,711` observations across frameworks, networking libraries, parsers, UI apps, databases, and CLI tooling) directly mitigates repository-specific overfitting.

---

## 3. Multi-Repository Discovery, Filtering & Collection Pipeline

Using `GitHubClient.discover_csharp_repositories()` and resumable `2_SourceCode/Scripts/run_100_repo_class_pipeline.py` (`run_id: class_v3_20261121_124127`):
- **Discovery & Selection:** Stratified GitHub REST searches (`language:csharp fork:false archived:false size:150..18000 pushed:>=2019-01-01`) discovered `300` repositories (`304` queued including seeded local repositories).
- **Resumable Execution & Documented Exclusions:** `106` repositories processed cleanly (`0` failed); `15` excluded due to `no_bug_fixing_commits_detected` (`9`), `insufficient_production_csharp_files` (`4`), `no_candidate_clean_classes` (`1`: `redis-windows/redis-windows`), and `no_substantive_buggy_classes` (`1`: `evolutionary-architecture/evolutionary-architecture-by-example`).
- **Mined Git & SZZ Activity:** `28,972` commits, `158,722` changed file records, and `16,161` SZZ blame line traces persisted in `1_Database/SQLite/bug_detection.db`.

---

## 4. Historical SZZ Attribution, Labeling Provenance & Duplicate Audit

- **Bug-Fix Commit Identification:** `BugFixDetector(strict_mode=True)` identifies defect-fixing commits while penalizing refactors, formatting changes, dependency bots, and large sweeps (`> 18` files).
- **Pre-Fix Class Extraction (`Label 1`):** `SZZAnalyzer` runs `git blame -w -M -C` over deleted lines in production `.cs` files and `ClassLabelManager` extracts the enclosing class/struct/record from `c_parent` via batched `--batch-stdin` Roslyn analysis (`2,829` defect-prone observations, `49.54%`).
- **Candidate-Clean Sampling (`Label 0`):** Substantive production classes (`>= 5` LOC or callable/property members) from `HEAD` files with zero bug-fix or SZZ involvement in the commit window (`2,882` observations, `50.46%`) under the **Open-World Assumption**.
- **Duplicate & Leakage Audit (`collection_summary_v3.json`):** Out of `5,743` extracted candidates, `28` intra-repo exact duplicates and `4` repeated structural revisions were removed (`0` cross-repo exact duplicates, `0` conflicting clean exclusions, `819` legitimate historical revisions preserved safely inside single-repository groups).

---

## 5. Roslyn `v3.0.0` Class & File Static Metric Extractor

`2_SourceCode/RoslynAnalyzer/Program.cs` compiles under `.NET 9.0` with `0 Warning(s), 0 Error(s)` using `LanguageVersion.Latest` and adds:
1. **`ClassMetrics` (40 isolated features):** Strict lexical/AST isolation via `GetTypeOwnedNodes<T>` ensures nested classes/structs/records are never double-counted in enclosing parent metrics; nested type line spans are subtracted from outer `class_loc`. Local functions and lambdas retain callable isolation.
2. **NDJSON `--batch-stdin` Engine:** Eliminates per-snippet `.NET` JIT startup latency during multi-thousand commit snapshot mining.
3. **Structured JSON Output:** Returns `FileMetadata`, `ClassLocation`, `ClassMetrics`, owned `MethodLocation`s, `ExtractionWarnings`, and `ParsingDiagnostics`.

---

## 6. Database Schema & Non-Destructive Artifact Preservation

SQLite schema `1_Database/SQLite/bug_detection.db` expanded non-destructively with `repository_collection_runs`, `file_observations`, `class_observations`, `class_features` (40 columns), and `dataset_class_observations`, plus additive columns on `repositories`, `datasets`, `models`, and `predictions`. Pre-migration archive [../../1_Database/SQLite/bug_detection_method_v2_archive.db](../../1_Database/SQLite/bug_detection_method_v2_archive.db), both method CSVs (`483` and `578` rows), `877` SQLite method `observations`, and all 4 historical `.joblib` bundles remain byte-for-byte intact.

---

## 7. Experimental Methodology: Nested GroupKFold & Precision Thresholding

To guarantee zero repository or historical-revision leakage:
1. `GroupShuffleSplit(test_size=0.20, random_state=42)` partitioned Dataset #3 into **`84` Development repositories (`4,730` classes, `50.02%` positive)** and **`22` Untouched Holdout repositories (`981` classes, `47.20%` positive)**.
2. Inside the Development corpus, **`5` outer x `4` inner `GroupKFold`** evaluated **`14` configurations across all `7` model families** (`DummyClassifier`, `LogisticRegression`, `DecisionTreeClassifier`, `RandomForestClassifier`, `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, `CalibratedClassifierCV`).
3. Inside every inner fold, median imputation, zero-variance filtering, optional correlation pruning, and scaling were fitted solely on inner-training partitions, and `select_precision_optimal_threshold()` selected $\tau \in [0.30, 0.88]$ targeting **$\text{Precision} \ge 0.80 \land \text{Recall} \ge 0.50$ maximizing $F_{0.5}$**.

---

## 8. Empirical Results Across 7 Model Families

Complete comparison on `84` Development repos (`5x4` Nested OOF) and `22` Untouched Holdout repos (`981` classes):

| Model Family | Champion / Representative Config | Inner $\tau$ | Nested OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | Holdout ROC-AUC |
|---|---|---:|---|---:|---:|---:|---:|
| **Random Forest** | **`rf_opt_depth12_leaf4_log2` (Champ)** | **`0.60`** | **82.30%** / **61.71%** / **70.53%** | **83.43%** | **61.99%** | **71.13%** | **0.8449** |
| Extra Trees | `et_opt_depth10_leaf4_log2_bal` | `0.60` | 82.63% / 61.12% / 70.26% | 83.33% | 58.32% | 68.61% | 0.8368 |
| Calibrated Ensemble | `calibrated_rf_sigmoid` | `0.64` | 81.56% / 61.71% / 70.26% | 83.09% | 61.56% | 70.72% | 0.8478 |
| HistGradientBoosting | `hgb_depth4_leaf25_unweighted` | `0.64` | 81.40% / 60.86% / 69.65% | 81.85% | 57.45% | 67.51% | **0.8502** |
| Logistic Regression | `lr_std_l2_c01_bal` | `0.58` | 80.82% / 60.57% / 69.24% | 80.18% | 56.80% | 66.50% | 0.8184 |
| Decision Tree | `dt_depth6_leaf10_bal` | `0.70` | 81.61% / 53.25% / 64.45% | **84.23%** | 50.76% | 63.34% | 0.7953 |
| DummyClassifier | `dummy_stratified` | `0.30` | 49.43% / 49.49% / 49.46% | 44.83% | 47.73% | 46.23% | 0.4761 |

All non-dummy model families substantially exceed the `>= 75%` minimum target, and **`class_precision_champion_v3` (`rf_opt_depth12_leaf4_log2`) surpasses the `>= 80%` preferred target in both Nested CV (`82.30%`, 5-fold mean `82.45% +/- 2.70%`) and Untouched Holdout (`83.43%`)** while maintaining `> 61%` recall (`TN=461, FP=57, FN=176, TP=287`, `FPR=11.00%`). Compared against the legacy method-level v2 holdout (`69.61%`), precision improved by **+13.82 percentage points**.

---

## 9. Feature Importance & Error Analysis

- **Primary Structural Predictors:** Permutation and MDI importances consistently rank `class_loc` (Permutation `0.0118`, MDI `0.1027`), `total_property_access_count`, `wmc_density`, `total_method_call_count`, `structural_density`, `class_logical_loc`, and `total_cyclomatic_complexity` highest — confirming that both raw functional scale and normalized complexity/statement density drive class defect risk.
- **Error Dichotomy (`holdout_error_analysis.csv`):** True Positives are complex multi-method classes (`median_loc=351.0, median_wmc=57.0`), whereas False Negatives cluster in compact classes (`median_loc=48.0, median_wmc=7.0`) harboring semantic logic errors invisible to syntax counters, and False Positives (`n=57, median_loc=186.0`) represent large well-structured components or Open-World latent defects.

---

## 10. Base-Rate Shift & Deployment Risk Calibration

Because SZZ datasets contain ~50% positives whereas live software projects typically exhibit `2%–20%` defective classes per release, Bayes' theorem transforms the champion's sensitivity (`61.99%`) and specificity (`89.00%`) into expected production PPV of **`58.48%` at 20% defect rate**, **`38.50%` at 10%**, and **`22.87%` at 5%**. Predictions should therefore prioritize reviewer attention rather than replace human judgment or act as hard merge blockers.

---

## 11. End-to-End Application Integration (`Streamlit`)

`2_SourceCode/Python/app.py` and all `8` pages under `application/pages/` operate on a single authoritative `ModelManager.list_saved_models()` registry (`12` models: `8` class-level, `4` historical method-level). Users can submit pasted classes (`predict_class_code`) or full `.cs` files (`predict_csharp_file`), inspect class-level risk cards, compare methods inside flagged classes, and inspect historical repository metrics alongside transparent disclaimers.

---

## 12. Quality Assurance Summary

Verified components include clean `.NET 9.0` Roslyn Release builds, non-destructive SQLite schema migrations preserving legacy DB invariants (`test_fluentvalidation_pilot.py`), `ModelManager`/`BugPredictor` smoke scoring across all 8 class bundles, SHA-256 preservation checks across all historical datasets/models/JSON artifacts, and automated unit + integration test suites covering Roslyn v3.0.0 isolation, collection deduplication, ML leakage guarantees, and Streamlit application pages.

---

## 13. Threats to Validity & Future Work

Key limitations include the Open-World negative labeling assumption, SZZ tangled-commit sensitivity, inability of syntactic AST counters to detect subtle semantic/concurrency faults inside short classes, and pre-existing binary defense documents inside `5_Documentation/09_Defense/` remaining at v2 state. Future extensions could incorporate Git churn/developer entropy features, inter-class dependency graphs, or lightweight semantic taint indicators.

---

## 14. Conclusion

Expanding the empirical corpus 17.7-fold (`5` to `106` C# repositories) and shifting static prediction from isolated methods (`26` features) to Roslyn-isolated C# classes (`40` features) with inner-CV threshold calibration raised holdout precision from `69.61%` to **`83.43%`** (`0.8449` ROC-AUC, `61.99%` recall) with zero repository leakage, delivering a reproducible, high-precision academic research system and interactive class/file inspection tool.
