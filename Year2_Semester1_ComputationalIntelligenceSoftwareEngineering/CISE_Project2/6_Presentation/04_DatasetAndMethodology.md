# Slide 4 — Top-200 Dataset & Validation Methodology

## Empirical Corpus (`csharp_class_top200_v4` v4.0.0)

- **Repository Funnel:** `500` discovered (`stars` descending) -> `367` eligible -> **`200` processed repositories** (`4,409`–`121,429` stars), **`179` documented exclusions** (`132` oversized >120MB, `1` insufficient size, `29` no bug fixes, `10` insufficient production `.cs` files, `5` no SZZ traces on production `.cs`, `1` no buggy classes, `1` no clean classes), **`0` failed**.
- **Dataset Size & Balance:** **`9,588` classes** (**`4,425` BUG** / `46.15%`, **`5,163` CLEAN** / `53.85%`), `0` nulls across `40` Roslyn features (`65` CSV columns; SHA-256 `c7ff8436...`), plus `67,556` method localization rows.
- **Duplicate Audit:** `9,646` -> `9,588` retained (`41` intra-repo exact, `12` cross-repo exact, `5` repeated structural revisions removed; `1,025` historical revisions retained strictly inside single-repository groups).

## Zero-Leakage Validation & Feature Audit

1. **Strict Repository Holdout (`GroupShuffleSplit`):** **`160` Dev repos (`7,546` classes)** vs. **`40` Untouched Holdout repos (`2,042` classes)**.
2. **40-Feature Sufficiency:** All `40` nonzero variance; ablation removing `10` collinear features (`|ρ| > 0.90`) slightly hurt Nested CV F1 (`0.7160` vs. `0.7193`) and Holdout F1 (`68.90%` vs. `69.67%`), so all 40 were kept.
3. **Inner-CV Thresholding:** `5×4` Nested `GroupKFold` (`select_classifier_threshold`) tuned $\tau$ strictly in inner folds (`rf_depth12_leaf4_log2_all40`: $\tau = 0.520$).
4. **Separate Method Localizer:** Trained on matching `157` dev repos (`54,678` methods) and tested on matching `38` holdout repos (`12,878` methods).

---

*Previous:* [System Architecture](03_SystemArchitecture.md) | *Next:* [Machine Learning Results](05_MachineLearningResults.md)
