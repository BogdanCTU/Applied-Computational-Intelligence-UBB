# Executive Project Summary — C# Bug Detection Classifier (`v4.0.0`)

**Title:** Machine Learning-Based C# Bug Detection Classifier  
**Institution:** Babeș-Bolyai University, Faculty of Mathematics and Computer Science — Applied Computational Intelligence (CISE Project 2)

---

## 1. System Evolution Overview

The project evolved across four documented milestones from a 5-repository method-level prototype (`v2.0.0`, `578` methods, `26` metrics) through a 106-repository class-level study (`v3.0.0`, `5,711` classes, `40` metrics) into the **`v4.0.0` Top-200 star-ranked C# Bug Detection Classifier** (`csharp_class_top200_v4`, **`9,588` classes** across **`200` repositories**), paired with a separately validated ML Method Localizer and provenance-aware historical SZZ localization.

| Dimension | Legacy Method v2 | Class Study v3 | Current Classifier v4.0.0 |
|---|---|---|---|
| Primary Task | Individual method defect scoring | Class/file defect risk scoring | Explicit binary **`BUG` / `CLEAN` class & multi-class `.cs` classifier** |
| Empirical Corpus | `5` repos (`578` methods) | `106` repos (`5,711` classes) | **`200` Top-Star C# repos (`9,588` classes: `4,425` BUG, `5,163` CLEAN)** |
| Feature Schema | `26` method metrics | `40` class metrics | **`40` isolated class metrics** + separate **`26`-metric ML Method Localizer** |
| Evaluation Split | 5×4 Nested GroupKFold (+ 1 holdout repo) | `84` dev / `22` holdout repos | **`160` dev (`7,546` classes) / `40` untouched holdout (`2,042` classes)** |
| Precision Target | Unconstrained (`69.61%` holdout) | >= 80% preferred | **>= 75% holdout precision target with balanced recall** |
| Champion Holdout Metrics | `69.61%` Prec / `89.87%` Rec / `0.8209` AUC | `83.43%` Prec / `61.99%` Rec / `0.8449` AUC | **`79.47%` Prec / `62.02%` Rec / `69.67%` F1 / `0.8180` AUC / `15.71%` FPR / `37.98%` FNR** |
| Localization Scope | None | Class probability only | **Verified historical SZZ lines/methods (`7,361` rows) vs. ML suspicious methods (`Top-3 68.64%`); exact unseen lines `unavailable`** |

---

## 2. Top-200 Star-Ranked Dataset & Labeling (`1_Database/`)

- **GitHub Discovery & Collection (`top200_v4_20261125_135308`):** Queried `language:csharp fork:false archived:false` sorted strictly by **GitHub stars descending**. Discovered **`500` repositories**, filtered **`367` eligible candidates**, successfully collected and validated **`200` repositories** (star range **`4,409`** [`tmenier/Flurl`] to **`121,429`** [`2dust/v2rayN`]), transparently recorded **`179` exclusions** (`132` `excluded_excessive_size_kb` >120,000 KB, `1` `excluded_insufficient_size_kb`, `29` `no_bug_fixing_commits_detected`, `10` `insufficient_production_csharp_files`, `5` `no_szz_traces_on_production_csharp`, `1` `no_substantive_buggy_classes`, `1` `no_candidate_clean_classes`), and experienced **`0` failures**.
- **SZZ Provenance & Method/Line Localization:**
  - **BUG (`4,425` classes, `46.15%`):** Extracted from pre-fix parent commits traced via bug-fix commit classification and `git blame -w -M -C` SZZ mapping to enclosing classes and enclosing methods, persisting **`7,361` verified historical localization records** (`class_bug_localizations`) across `4,473` SQLite BUG observations.
  - **CLEAN (`5,163` classes, `53.85%`):** Candidate-clean substantive production classes sampled from `HEAD` files with zero observed bug-fixing or SZZ history in the mined window (**Open-World Assumption**).
- **Duplicate & Leakage Audit (`collection_summary_top200_v4.json`):** `9,646` candidates reduced to **`9,588`** (`41` intra-repo exact, `12` cross-repo exact, `5` repeated structural revisions removed; `1,025` legitimate historical revisions retained inside repo groups; `0` test files; `0` conflicting clean classes; `0` missing values across all `40` features).
- **Method Localization Corpus (`method_localization_top200_v4.csv`):** `67,556` method rows extracted from SZZ-localized BUG classes to train and evaluate the separate ML Method Localizer without holdout leakage.

---

## 3. Binary Classifier, Localization Separation & Streamlit GUI (`2_SourceCode/`)

- **Roslyn `.NET 9.0` Analyzer (`2_SourceCode/RoslynAnalyzer/Program.cs`):** Supports C# `LanguageVersion.Latest`, `--batch-stdin` NDJSON streaming, isolated class metrics (`GetTypeOwnedNodes<T>`), enclosed method signatures/line bounds, and full syntax diagnostics.
- **ML Classifier (`rf_depth12_leaf4_log2_all40`, bundle `class_bug_classifier_top200_v4.joblib`, $\tau = 0.520$):**
  - Threshold selection (`select_classifier_threshold`) runs strictly on inner CV folds (`160` dev repos), achieving **`77.66%` Nested CV OOF precision** (`66.99%` recall, `0.8330` ROC-AUC) and **`79.47%` untouched holdout precision** (`62.02%` recall, `69.67%` F1, `0.8180` ROC-AUC, `0.8104` PR-AUC, `15.71%` FPR, `37.98%` FNR, CM `[[869, 162], [384, 627]]`).
  - Feature sufficiency audit verified all `40` Roslyn features have nonzero variance (`0` nulls); removing 10 collinear features (`|ρ| > 0.90`) slightly reduced Nested CV F1 (`0.7160` vs. `0.7193`) and Holdout F1 (`68.90%` vs. `69.67%`), justifying retaining all 40 features.
- **ML Method Localizer (`method_localizer_top200_v4.joblib`, `26` method features):** Evaluated on the strict matching `38`-repo holdout (`778` BUG classes, `12,878` methods, `10.26%` positive rate): **Top-1 hit `44.99%`**, **Top-3 hit `68.64%`**, **ROC-AUC `0.6611`**, **Precision `22.46%`**, **Recall `28.31%`**. Explicitly distinguishes **Verified Historical SZZ Locations** from **ML-Estimated Suspicious Methods**, and marks **exact line localization `unavailable` on unseen code**.
- **Streamlit UI (`app.py`, `application/pages/bug_prediction.py`):** Displays **`BUG DETECTED`** (error) or **`CLEAN`** (success) as primary output with probability/confidence secondary, per-class and file summary counts for multi-class `.cs` files, and refuses to classify syntax-broken/incomplete files as `CLEAN` (`ANALYSIS INCOMPLETE` / `BUG (PARTIAL ANALYSIS)`).

---

## 4. Preserved Historical Artifacts

All legacy method-level CSVs (`v1.0.0`, `v2.0.0`), the v3 106-repo CSV (`csharp_class_empirical_v3_v3.0.0.csv`), all prior `.joblib` model bundles, historical JSON evaluation reports, `bug_detection_method_v2_archive.db`, and SQLite method `observations` (`877` rows) remain intact and verified via SHA-256 checksums.
