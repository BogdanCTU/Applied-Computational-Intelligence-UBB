# Slide 5 — Machine Learning Results & Precision Target Achievement

## 7-Family Comparison (`5x4` Nested OOF vs. Untouched `22`-Repo Holdout)

| Model Family | Config ID | Inner $\tau$ | Nested OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | Holdout ROC-AUC |
|---|---|---:|---|---:|---:|---:|---:|
| **Random Forest (Champ)** | `rf_opt_depth12_leaf4_log2` | **`0.60`** | **82.30%** / 61.71% / **70.53%** | **83.43%** | **61.99%** | **71.13%** | **0.8449** |
| Calibrated Ensemble | `calibrated_rf_sigmoid` | `0.64` | 81.56% / 61.71% / 70.26% | 83.09% | 61.56% | 70.72% | **0.8478** |
| Extra Trees | `et_opt_depth10_leaf4_log2_bal` | `0.60` | 82.63% / 61.12% / 70.26% | 83.33% | 58.32% | 68.61% | 0.8368 |
| HistGradientBoosting | `hgb_depth4_leaf25_unweighted` | `0.64` | 81.40% / 60.86% / 69.65% | 81.85% | 57.45% | 67.51% | **0.8502** |
| Logistic Regression | `lr_std_l2_c01_bal` | `0.58` | 80.82% / 60.57% / 69.24% | 80.18% | 56.80% | 66.50% | 0.8184 |
| Decision Tree | `dt_depth6_leaf10_bal` | `0.70` | 81.61% / 53.25% / 64.45% | **84.23%** | 50.76% | 63.34% | 0.7953 |
| DummyClassifier | `dummy_stratified` | `0.30` | 49.43% / 49.49% / 49.46% | 44.83% | 47.73% | 46.23% | 0.4761 |

- **Precision Target Outcome:** **BOTH `>= 80%` preferred and `>= 75%` minimum precision achieved** (`82.30%` OOF / `83.43%` holdout, `TP=287, FP=57, FN=176, TN=461`, `FPR=11.00%`, `+13.82 pp` vs. v2 holdout precision `69.61%`).
- **Top Drivers (Permutation Importance):** `class_loc` (`0.0118`), `total_property_access_count` (`0.0102`), `wmc_density` (`0.0102`), `total_method_call_count` (`0.0077`), `structural_density` (`0.0071`).

---

*Previous:* [Dataset & Methodology](04_DatasetAndMethodology.md) | *Next:* [Application Demo](06_ApplicationDemo.md)
