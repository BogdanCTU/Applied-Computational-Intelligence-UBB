# Slide 4 — Dataset #3 & Validation Methodology

## Empirical Corpus (`csharp_class_empirical_v3` v3.0.0)

- **Repository Funnel:** `300` discovered (`304` queued candidates) $\rightarrow$ **`106` processed repositories**, `15` documented exclusions (`9` zero bug-fix commits, `4` `< 5` production C# files, `2` insufficient buggy/clean classes), `0` failures.
- **Total Class Observations:** **`5,711`** (`2,829` SZZ defect-prone / `49.54%`, `2,882` candidate-clean / `50.46%`), `0` missing feature values across `40` isolated class metrics (`62` CSV columns; SHA-256: `7087edb5...`).
- **Duplicate & Revision Integrity:** From `5,743` extracted candidates, removed `28` intra-repo exact hash duplicates and `4` repeated structural revisions (`0` cross-repo exact duplicates, `0` conflicting clean classes); retained `819` legitimate historical class revisions strictly grouped by `repository_id`.

## Zero-Leakage Validation Design

1. **Strict Repository Holdout (`GroupShuffleSplit`):** `84` Development repos (`4,730` classes) vs. **`22` Untouched Holdout repos (`981` classes)**.
2. **5x4 Nested `GroupKFold`:** Inside Development repos, median imputation, zero-variance filtering, correlation pruning / scaling (for LR), and precision threshold selection ($\tau \in [0.30, 0.88]$ targeting $\text{Prec} \ge 0.80 \land \text{Rec} \ge 0.50$ maximizing $F_{0.5}$) happen **strictly in inner folds**.
3. **7 Model Families Benchmarked:** `RandomForestClassifier`, `ExtraTreesClassifier`, `HistGradientBoostingClassifier`, `CalibratedClassifierCV`, `LogisticRegression`, `DecisionTreeClassifier`, and `DummyClassifier`.

---

*Previous:* [System Architecture](03_SystemArchitecture.md) | *Next:* [Machine Learning Results](05_MachineLearningResults.md)
