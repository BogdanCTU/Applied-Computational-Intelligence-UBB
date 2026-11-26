# Experimental Results & Comparative Analysis (`v4.0.0`)

**Experiment Runner:** `2_SourceCode/Scripts/run_top200_classifier_optimization.py`  
**Primary Dataset:** Dataset #3 (`csharp_class_top200_v4` v4.0.0 — `9,588` classes across `200` Top-Star C# repositories)  
**Artifact Directory:** `3_TestResults/Top200ClassifierOptimization/`

---

## 1. Corpus Summary & Partitioning

- **Total Validated Classes (`200` repos, `4,409`–`121,429` stars):** `9,588` (**`4,425` BUG** / `46.15%`, **`5,163` CLEAN** / `53.85%`), `40` Roslyn features (`0` missing values).
- **Development Set (5×4 Nested `GroupKFold`):** `160` repositories, **`7,546` classes** (`3,414` BUG, `4,132` CLEAN).
- **Independent Untouched Holdout:** `40` unseen repositories, **`2,042` classes** (`1,011` BUG, `1,031` CLEAN). Zero repository overlap (`0` shared repos).

---

## 2. 5×4 Nested GroupKFold Benchmark (`160` Dev Repos, `7,546` Classes)

All thresholds ($\tau$) were selected exclusively inside inner CV folds (`select_classifier_threshold`):

| Config ID | Model Family | Inner $\tau$ | Outer Mean Prec (+/- std) | Outer Mean Rec (+/- std) | OOF Prec | OOF Rec | OOF F1 | OOF ROC-AUC | OOF PR-AUC | OOF FPR / FNR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`rf_depth12_leaf4_log2_all40`** | **Random Forest (Champ)** | **`0.52`** | **77.58% ± 2.49%** | **66.92% ± 4.33%** | **77.66%** | **66.99%** | **71.93%** | **0.8330** | **0.8102** | **15.92% / 33.01%** |
| `calibrated_rf_sigmoid` | Calibrated Ensemble | `0.54` | 77.71% ± 2.30% | 66.43% ± 3.96% | 77.77% | 66.49% | 71.69% | 0.8334 | 0.8112 | 15.71% / 33.51% |
| `rf_depth12_leaf4_corr_pruned` | RF (Pruned 30) | `0.54` | 77.94% ± 2.66% | 66.14% ± 4.01% | 77.96% | 66.20% | 71.60% | **0.8339** | **0.8120** | 15.46% / 33.80% |
| `rf_depth14_leaf3_sqrt_unweighted` | Random Forest | `0.52` | 77.99% ± 2.68% | 65.98% ± 4.68% | 78.05% | 66.05% | 71.55% | 0.8321 | 0.8092 | 15.34% / 33.95% |
| `hgb_depth4_leaf15_unweighted` | HistGradientBoosting | `0.54` | 77.81% ± 2.51% | 65.16% ± 4.27% | 77.87% | 65.23% | 70.99% | 0.8308 | 0.8096 | 15.32% / 34.77% |
| `et_depth12_leaf4_log2_bal` | Extra Trees | `0.54` | 78.12% ± 2.81% | 64.16% ± 4.59% | **78.24%** | 64.24% | 70.55% | 0.8302 | 0.8123 | 14.76% / 35.76% |
| `hgb_depth5_leaf20_l2_2` | HistGradientBoosting | `0.58` | 77.82% ± 2.38% | 64.34% ± 4.30% | 77.90% | 64.41% | 70.51% | 0.8277 | 0.8059 | 15.10% / 35.59% |
| `et_depth14_leaf5_sqrt` | Extra Trees | `0.52` | 77.74% ± 3.01% | 64.37% ± 5.03% | 77.82% | 64.44% | 70.50% | 0.8317 | **0.8126** | 15.17% / 35.56% |
| `lr_robust_l2_c02` | Logistic Regression | `0.50` | 77.89% ± 2.20% | 63.13% ± 5.04% | 77.91% | 63.21% | 69.79% | 0.8175 | 0.7961 | 14.81% / 36.79% |
| `lr_std_l2_c01_bal` | Logistic Regression | `0.56` | **78.20% ± 2.26%** | 62.47% ± 5.46% | **78.24%** | 62.57% | 69.53% | 0.8175 | 0.7970 | 14.38% / 37.43% |
| `dt_depth6_leaf12_bal` | Decision Tree | `0.64` | 78.19% ± 2.08% | 60.26% ± 4.67% | 78.23% | 60.31% | 68.11% | 0.8056 | 0.7846 | **13.87%** / 39.69% |
| `dummy_stratified` | `DummyClassifier` | `0.30` | 45.57% ± 1.10% | 46.12% ± 1.26% | 45.57% | 46.10% | 45.84% | 0.5030 | 0.4539 | 45.50% / 53.90% |

### Champion Outer Fold Breakdown (`top200_champion_outer_folds.csv`)

| Outer Fold | Val Repos | Val Classes | Inner $\tau$ | Prec ($\tau=0.50$) | Opt Prec ($\tau$) | Opt Rec ($\tau$) | Opt F1 | FPR / FNR | ROC-AUC | PR-AUC |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | 32 | 1,507 | `0.52` | 74.28% | 75.30% | 64.87% | 69.69% | 17.78% / 35.13% | 0.8194 | 0.7953 |
| 2 | 32 | 1,510 | `0.54` | 75.93% | 79.00% | 72.73% | 75.73% | 16.40% / 27.27% | **0.8540** | **0.8410** |
| 3 | 32 | 1,510 | `0.56` | 76.10% | **81.27%** | 71.49% | **76.07%** | **14.16% / 28.51%** | 0.8496 | 0.8325 |
| 4 | 32 | 1,510 | `0.52` | 73.17% | 74.42% | 62.84% | 68.14% | 16.86% / 37.16% | 0.8181 | 0.7910 |
| 5 | 32 | 1,509 | `0.52` | **76.35%** | 77.90% | 62.67% | 69.46% | 14.39% / 37.33% | 0.8281 | 0.7927 |

---

## 3. Independent Untouched Holdout Evaluation (`40` Unseen Repos, `2,042` Classes)

Evaluated once on the untouched `40`-repo holdout (`1,011` BUG, `1,031` CLEAN) using fixed inner-CV thresholds (`top200_holdout_results.csv`):

| Config ID | Inner $\tau$ | Precision | Recall | F1 | Accuracy | ROC-AUC | PR-AUC | FPR | FNR | Confusion Matrix `[[TN, FP], [FN, TP]]` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`rf_depth12_leaf4_log2_all40`** | **`0.52`** | **79.47%** | **62.02%** | **69.67%** | **73.26%** | 0.8180 | **0.8104** | 15.71% | **37.98%** | `[[869, 162], [384, 627]]` |
| `rf_depth12_leaf4_corr_pruned` | `0.54` | 80.83% | 60.04% | 68.90% | 73.16% | 0.8186 | 0.8074 | 13.97% | 39.96% | `[[887, 144], [404, 607]]` |
| `calibrated_rf_sigmoid` | `0.54` | 81.05% | 59.64% | 68.72% | 73.11% | 0.8182 | 0.8099 | 13.68% | 40.36% | `[[890, 141], [408, 603]]` |
| `hgb_depth5_leaf20_l2_2` | `0.58` | 81.84% | 58.85% | 68.47% | 73.16% | 0.8202 | 0.8078 | 12.80% | 41.15% | `[[899, 132], [416, 595]]` |
| `rf_depth14_leaf3_sqrt_unweighted` | `0.52` | 81.32% | 58.56% | 68.09% | 72.82% | 0.8168 | 0.8085 | 13.19% | 41.44% | `[[895, 136], [419, 592]]` |
| `hgb_depth4_leaf15_unweighted` | `0.54` | 81.84% | 57.07% | 67.25% | 72.48% | **0.8215** | 0.8081 | 12.42% | 42.93% | `[[903, 128], [434, 577]]` |
| `dt_depth6_leaf12_bal` | `0.64` | 81.56% | 56.87% | 67.02% | 72.28% | 0.7951 | 0.7747 | 12.61% | 43.13% | `[[901, 130], [436, 575]]` |
| `et_depth12_leaf4_log2_bal` | `0.54` | 79.17% | 56.78% | 66.13% | 71.20% | 0.8103 | 0.8014 | 14.65% | 43.22% | `[[880, 151], [437, 574]]` |
| `lr_robust_l2_c02` | `0.50` | 81.82% | 55.19% | 65.92% | 71.74% | 0.8051 | 0.7982 | 12.03% | 44.81% | `[[907, 124], [453, 558]]` |
| `et_depth14_leaf5_sqrt` | `0.52` | 80.49% | 55.09% | 65.41% | 71.16% | 0.8115 | 0.8023 | 13.09% | 44.91% | `[[896, 135], [454, 557]]` |
| `lr_std_l2_c01_bal` | `0.56` | **81.89%** | 54.10% | 65.16% | 71.35% | 0.8041 | 0.7972 | **11.74%** | 45.90% | `[[910, 121], [464, 547]]` |
| `dummy_stratified` | `0.30` | 51.93% | 47.97% | 49.87% | 52.25% | 0.5221 | 0.5067 | 43.55% | 52.03% | `[[582, 449], [526, 485]]` |

**Target Verification:** Champion (`class_bug_classifier_top200_v4`) achieves **`79.47%` Precision** on the untouched holdout (exceeding the **`>= 75%`** target by `+4.47 pp`), **`62.02%` Recall**, **`69.67%` F1**, **`0.8180` ROC-AUC**, **`0.8104` PR-AUC**, **`15.71%` FPR**, and **`37.98%` FNR** (Brier `0.1763`), strictly outperforming `DummyClassifier` (`+27.54 pp` precision, `+0.2959` ROC-AUC). Note that at $\tau = 0.50$ nominal, holdout precision/recall for `rf_depth12_leaf4_log2_all40` was `78.33%` / `65.08%`.

---

## 4. Separately Validated ML Method Localizer (`method_localizer_evaluation.json`)

Evaluated on the exact same repository-grouped holdout split across SZZ-localized `BUG` classes that contain multiple methods:
- **Dev:** `157` repos, `2,670` BUG classes, `54,678` methods.
- **Holdout:** `38` repos, `778` BUG classes, `12,878` methods (`1,321` SZZ-buggy methods = `10.26%` base rate).
- **Holdout Metrics ($\tau = 0.600$):**
  - **Top-1 Class Hit Rate:** **`44.99%`** | **Top-3 Class Hit Rate:** **`68.64%`**
  - **Method ROC-AUC:** `0.6611` | **Method PR-AUC:** `0.1906`
  - **Method Precision:** `22.46%` | **Method Recall:** `28.31%` | **F1:** `25.05%` | **FPR:** `11.17%` | **FNR:** `71.69%`
  - **Confusion Matrix:** `[[10266, 1291], [947, 374]]`

Because method-level positive prevalence within a single BUG class averages `~10.3%`, exact method classification is intentionally presented as a **Top-$k$ suspicious method ranking (`68.64%` Top-3 recall)** labeled *ML-Estimated (not verified ground truth)* rather than definitive line proof.

---

## 5. Per-Repository Holdout Variance & Base-Rate Sensitivity

- **Per-Repository Holdout Highlights (`top200_holdout_per_repository.csv`):** Strong precision on dense libraries/systems (`ClosedXML` `100.0%`, `ScreenToGif` `100.0%`, `microsoft/FASTER` `95.95%`, `FastEndpoints` `93.55%`, `dotnetcore/CAP` `92.59%`, `MassTransit` `91.30%`, `protobuf-net` `89.66%`, `RestSharp` `89.66%`, `microsoft/semantic-kernel` `87.50%`), lower precision on small-sample UI/utility repos (`TechnitiumSoftware/DnsServer` `36.84%`, `seerge/g-helper` `40.00%`, `stride3d/stride` `44.44%`, `Notepads` `48.15%`).
- **Bayesian Base-Rate Sensitivity:** Applying holdout `TPR = 62.02%` and `FPR = 15.71%`: at empirical dataset prevalence (`46.15%`), Bayes PPV is `77.18%`; at realistic real-world code defect rates (`20%`, `10%`, `5%`, `2%`), deployed precision drops to **`49.67%`**, **`30.49%`**, **`17.20%`**, and **`7.45%`** respectively.
