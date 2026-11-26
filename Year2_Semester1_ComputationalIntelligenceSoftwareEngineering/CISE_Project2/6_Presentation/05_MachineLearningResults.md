# Slide 5 — Classifier & Localizer Holdout Results (`v4.0.0`)

## Binary Class Classifier (`5×4` Nested OOF vs. Untouched `40`-Repo Holdout)

| Model Family | Config ID | $\tau_{\text{CV}}$ | Nested OOF Prec / Rec / F1 | Holdout Prec | Holdout Rec | Holdout F1 | ROC-AUC | PR-AUC | FPR / FNR |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| **Random Forest (Champ)** | `rf_depth12_leaf4_log2_all40` | `0.52` | **77.66%** / **66.99%** / **71.93%** | **79.47%** | **62.02%** | **69.67%** | 0.8180 | **0.8104** | 15.71% / **37.98%** |
| Random Forest (Pruned 30) | `rf_depth12_leaf4_corr_pruned` | `0.54` | 77.96% / 66.20% / 71.60% | 80.83% | 60.04% | 68.90% | 0.8186 | 0.8074 | 13.97% / 39.96% |
| Calibrated Ensemble | `calibrated_rf_sigmoid` | `0.54` | 77.77% / 66.49% / 71.69% | 81.05% | 59.64% | 68.72% | 0.8182 | 0.8099 | 13.68% / 40.36% |
| HistGradientBoosting | `hgb_depth5_leaf20_l2_2` | `0.58` | 77.90% / 64.41% / 70.51% | 81.84% | 58.85% | 68.47% | **0.8202** | 0.8078 | 12.80% / 41.15% |
| Extra Trees | `et_depth12_leaf4_log2_bal` | `0.54` | **78.24%** / 64.24% / 70.55% | 79.17% | 56.78% | 66.13% | 0.8103 | 0.8014 | 14.65% / 43.22% |
| Logistic Regression | `lr_std_l2_c01_bal` | `0.56` | **78.24%** / 62.57% / 69.53% | **81.89%** | 54.10% | 65.16% | 0.8041 | 0.7972 | **11.74%** / 45.90% |
| Decision Tree | `dt_depth6_leaf12_bal` | `0.64` | 78.23% / 60.31% / 68.11% | 81.56% | 56.87% | 67.02% | 0.7951 | 0.7747 | 12.61% / 43.13% |
| `DummyClassifier` | `dummy_stratified` | `0.30` | 45.57% / 46.10% / 45.84% | 51.93% | 47.97% | 49.87% | 0.5221 | 0.5067 | 43.55% / 52.03% |

- **Precision Target Exceeded:** **`79.47%` untouched holdout precision** (`>= 75%` target met cleanly without holdout tuning), Confusion Matrix `[[869, 162], [384, 627]]` (`627 / 1,011` bugs detected).
- **Separate ML Method Localizer Holdout (`38` repos, `778` BUG classes, `12,878` methods):** **Top-1 Hit = `44.99%`**, **Top-3 Hit = `68.64%`**, **ROC-AUC = `0.6611`**, **Precision = `22.46%`**, **Recall = `28.31%`**, **FPR = `11.17%`**.

---

*Previous:* [Dataset & Methodology](04_DatasetAndMethodology.md) | *Next:* [Application Demo](06_ApplicationDemo.md)
