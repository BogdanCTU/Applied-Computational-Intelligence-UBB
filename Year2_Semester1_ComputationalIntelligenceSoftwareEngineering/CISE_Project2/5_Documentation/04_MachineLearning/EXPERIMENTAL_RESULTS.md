# Experimental Results & Comparative Analysis (`v3.0.0`)

**Experiment Runner:** `2_SourceCode/Scripts/run_class_model_optimization.py`  
**Primary Dataset:** Dataset #3 (`csharp_class_empirical_v3` v3.0.0 — `5,711` classes across `106` public C# repositories)  
**Artifact Directory:** `3_TestResults/ClassModelOptimization/`

---

## 1. Corpus Summary & Feature Distributional Separation

Across `106` successfully mined C# repositories (`4,730` Development classes across `84` repos; `981` Untouched Holdout classes across `22` repos), defect-prone classes exhibit substantially higher size, cyclomatic mass, nesting depth, and interaction density than candidate-clean classes:

| Roslyn Feature (`v3.0.0`) | Defect-Prone Median (Mean) | Candidate-Clean Median (Mean) |
|---|---:|---:|
| `class_loc` | **176.00** (342.21) | 29.00 (64.53) |
| `class_logical_loc` | **75.00** (155.53) | 7.00 (24.94) |
| `method_count` | **7.00** (13.69) | 2.00 (3.25) |
| `total_cyclomatic_complexity` | **29.00** (60.98) | 4.00 (11.60) |
| `max_method_complexity` | **8.00** (13.64) | 2.00 (4.27) |
| `max_nesting_depth` | **3.00** (3.01) | 0.00 (0.99) |
| `total_method_call_count` | **35.00** (76.45) | 4.00 (13.19) |
| `total_if_count` | **10.00** (22.14) | 0.00 (3.10) |
| `large_method_count` | **1.00** (1.91) | 0.00 (0.23) |
| `structural_density` | **0.42** (0.40) | 0.23 (0.25) |
| `complexity_concentration` | 0.30 (0.38) | 0.50 (0.61) |

---

## 2. 5x4 Nested GroupKFold Benchmark Across All 7 Model Families (`84` Dev Repos, `4,730` Classes)

All thresholds ($\tau$) were selected exclusively within inner folds and evaluated out-of-fold on unseen outer repositories (`class_model_comparison.csv`):

| Config ID | Model Family | Inner-CV $\tau$ | Outer Mean Prec (+/- std) | Outer Mean Rec (+/- std) | OOF Prec | OOF Rec | OOF F1 | OOF ROC-AUC | OOF PR-AUC | OOF Brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`rf_opt_depth12_leaf4_log2`** | **Random Forest (Champ)** | **`0.60`** | **82.45% +/- 2.70%** | **61.59% +/- 4.01%** | **82.30%** | **61.71%** | **70.53%** | **0.8260** | **0.8280** | **0.1697** |
| `rf_opt_depth10_leaf6_unweighted` | Random Forest | `0.60` | 81.94% +/- 3.15% | 61.71% +/- 4.38% | 81.69% | 61.83% | 70.39% | 0.8263 | 0.8290 | 0.1694 |
| `calibrated_rf_sigmoid` | Calibrated Ensemble | `0.64` | 81.90% +/- 3.26% | 61.57% +/- 5.07% | 81.56% | 61.71% | 70.26% | 0.8261 | 0.8298 | 0.1694 |
| `et_opt_depth10_leaf4_log2_bal` | Extra Trees | `0.60` | 82.84% +/- 3.00% | 60.92% +/- 7.23% | 82.63% | 61.12% | 70.26% | 0.8254 | 0.8282 | 0.1709 |
| `calibrated_et_isotonic` | Calibrated Ensemble | `0.64` | 82.36% +/- 3.14% | 60.62% +/- 4.04% | 82.11% | 60.74% | 69.83% | 0.8250 | 0.8276 | 0.1700 |
| `rf_baseline_compact` | Random Forest (Base) | `0.62` | 82.81% +/- 3.66% | 60.20% +/- 7.08% | 82.27% | 60.40% | 69.66% | 0.8262 | 0.8275 | 0.1694 |
| `hgb_depth4_leaf25_unweighted` | HistGradientBoosting | `0.64` | 81.83% +/- 3.97% | 60.77% +/- 4.16% | 81.40% | 60.86% | 69.65% | 0.8211 | 0.8227 | 0.1721 |
| `et_opt_depth12_leaf5_sqrt` | Extra Trees | `0.60` | 82.80% +/- 2.55% | 59.73% +/- 4.47% | 82.66% | 59.85% | 69.43% | 0.8267 | 0.8298 | 0.1696 |
| `lr_std_l2_c01_bal` | Logistic Regression | `0.58` | 81.11% +/- 3.04% | 60.47% +/- 3.86% | 80.82% | 60.57% | 69.24% | 0.8138 | 0.8174 | 0.1761 |
| `lr_robust_l2_c01` | Logistic Regression | `0.58` | 81.22% +/- 3.53% | 59.97% +/- 4.24% | 80.83% | 60.06% | 68.91% | 0.8137 | 0.8172 | 0.1765 |
| `hgb_depth5_leaf20_l2_2` | HistGradientBoosting | `0.66` | 82.04% +/- 2.33% | 58.16% +/- 2.29% | 82.01% | 58.20% | 68.08% | 0.8147 | 0.8168 | 0.1759 |
| `dt_depth5_leaf15` | Decision Tree | `0.70` | 82.20% +/- 3.43% | 53.85% +/- 3.14% | 82.01% | 53.93% | 65.07% | 0.8010 | 0.7958 | 0.1850 |
| `dt_depth6_leaf10_bal` | Decision Tree | `0.70` | 82.08% +/- 3.78% | 53.16% +/- 4.64% | 81.61% | 53.25% | 64.45% | 0.7905 | 0.7910 | 0.1906 |
| `dummy_stratified` | DummyClassifier | `0.30` | 49.44% +/- 1.65% | 49.52% +/- 1.53% | 49.43% | 49.49% | 49.46% | 0.4941 | 0.4973 | 0.5059 |

### Champion Outer Fold Consistency (`champion_outer_folds.csv`)

| Outer Fold | Val Repos | Val Classes | Inner $\tau$ | Selection Criterion | Prec ($\tau=0.50$) | Opt Prec ($\tau$) | Opt Rec ($\tau$) | Opt F1 | ROC-AUC |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 16 | 942 | `0.60` | `tier1_precision>=0.80_recall>=0.50_max_f05` | 75.00% | 80.35% | 60.17% | 68.81% | 0.8241 |
| 2 | 17 | 946 | `0.62` | `tier1_precision>=0.80_recall>=0.50_max_f05` | 77.09% | 83.60% | 57.36% | 68.04% | 0.8255 |
| 3 | 17 | 946 | `0.62` | `tier1_precision>=0.80_recall>=0.50_max_f05` | 72.64% | 78.27% | 64.96% | 71.00% | 0.7929 |
| 4 | 17 | 946 | `0.60` | `tier1_precision>=0.80_recall>=0.50_max_f05` | 79.59% | 85.30% | 57.92% | 68.99% | 0.8466 |
| 5 | 17 | 950 | `0.60` | `tier1_precision>=0.80_recall>=0.50_max_f05` | 76.80% | 84.73% | 67.55% | 75.17% | 0.8464 |

---

## 3. Untouched Independent Repository Holdout (`22` Unseen Repos, `981` Classes)

Single-shot evaluation on `22` held-out repositories (`463` buggy, `518` clean) after full Development fit (`class_holdout_results.csv`):

| Config ID | Inner-CV $\tau$ | Holdout Prec ($\tau$) | Holdout Rec ($\tau$) | Holdout F1 | Holdout Acc | Holdout ROC-AUC | Holdout PR-AUC | Holdout FPR | Nom ($\tau=0.50$) Prec / Rec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`rf_opt_depth12_leaf4_log2`** | **`0.60`** | **83.43%** | **61.99%** | **71.13%** | **76.25%** | **0.8449** | **0.8327** | **11.00%** | 78.47% / 73.22% |
| `rf_opt_depth10_leaf6_unweighted` | `0.60` | 82.66% | 61.77% | 70.70% | 75.84% | 0.8460 | 0.8338 | 11.58% | 78.14% / 72.57% |
| `calibrated_rf_sigmoid` | `0.64` | 83.09% | 61.56% | 70.72% | 75.94% | **0.8478** | **0.8350** | 11.20% | 77.55% / 73.87% |
| `et_opt_depth10_leaf4_log2_bal` | `0.60` | 83.33% | 58.32% | 68.61% | 74.82% | 0.8368 | 0.8299 | 10.42% | 77.45% / 68.25% |
| `calibrated_et_isotonic` | `0.64` | 83.28% | 58.10% | 68.45% | 74.72% | 0.8365 | 0.8296 | 10.42% | 77.37% / 68.68% |
| `rf_baseline_compact` | `0.62` | 82.88% | 59.61% | 69.35% | 75.13% | 0.8428 | 0.8288 | 11.00% | 77.55% / 72.35% |
| `hgb_depth4_leaf25_unweighted` | `0.64` | 81.85% | 57.45% | 67.51% | 73.90% | **0.8502** | 0.8324 | 11.39% | 78.37% / 72.79% |
| `hgb_depth5_leaf20_l2_2` | `0.66` | 83.06% | 54.00% | 65.45% | 73.09% | 0.8433 | 0.8261 | 9.85% | 78.27% / 72.35% |
| `lr_std_l2_c01_bal` | `0.58` | 80.18% | 56.80% | 66.50% | 72.99% | 0.8184 | 0.8100 | 12.55% | 76.06% / 65.87% |
| `lr_robust_l2_c01` | `0.58` | 80.31% | 56.37% | 66.24% | 72.88% | 0.8116 | 0.8031 | 12.36% | 76.01% / 65.01% |
| `dt_depth6_leaf10_bal` | `0.70` | **84.23%** | 50.76% | 63.34% | 72.27% | 0.7953 | 0.7896 | **8.49%** | 74.00% / 68.25% |
| `dt_depth5_leaf15` | `0.70` | 81.95% | 47.08% | 59.81% | 70.13% | 0.8104 | 0.7790 | 9.27% | 72.59% / 71.49% |
| `dummy_stratified` | `0.30` | 44.83% | 47.73% | 46.23% | 47.60% | 0.4761 | 0.4607 | 52.51% | 44.83% / 47.73% |

**Champion Confusion Matrix (Untouched 22-Repo Holdout, $\tau=0.600$):** `TN = 461`, `FP = 57`, `FN = 176`, `TP = 287` (`287 / 463` defects detected; `F0.5 = 78.03%`, `Brier = 0.1599`). Both `>= 75%` and `>= 80%` precision targets plus `>= 50%` recall floor are met simultaneously on OOF and untouched holdout.

---

## 4. Method-Level (v2) vs. Class-Level (v3) Empirical Comparison

| Evaluation Axis | Method-Level v2 (`csharp_empirical_v2` / `JamesNK/Newtonsoft.Json`) | Class-Level v3 (`csharp_class_empirical_v3`) | Observed Gain |
|---|---|---|---|
| Repository Scale | `5` train + `1` holdout (`6` total) | **`84` dev + `22` holdout (`106` total)** | **17.7x repos** |
| Observations & Features | `578` methods + `159` holdout (`26` features) | **`5,711` classes (`40` features)** | **9.9x samples** |
| Nested CV OOF Precision | `65.64%` (`et_nested_opt_v3`, $\tau \in [0.35, 0.40]$) | **`82.30%`** (`rf_opt_depth12_leaf4_log2`, $\tau=0.600$) | **+16.66 pp** |
| Nested CV ROC-AUC | `0.7470` (`et_nested_opt_v3`) | **`0.8260`** (Champion RF) | **+0.0790** |
| Untouched Holdout Precision | `69.61%` ($\tau=0.40$) / `69.79%` ($\tau=0.50$) | **`83.43%`** (`22` repos, $\tau=0.600$) | **+13.82 pp** |
| Untouched Holdout ROC-AUC | `0.8209` (`1` repo) | **`0.8449`** (`22` unseen repos) | **+0.0240** |

Aggregating structural signals to the isolated C# class/struct/record eliminates tiny single-method noise (getters, one-line lambdas) while amplifying multi-method complexity, nesting, and coupling differences across heterogeneous codebases.

---

## 5. Feature Importances & Holdout Error Analysis

### Top Global Feature Drivers (`class_precision_champion_v3`)
- **By Holdout Permutation Importance:** `class_loc` (`0.0118`), `total_property_access_count` (`0.0102`), `wmc_density` (`0.0102`), `total_method_call_count` (`0.0077`), `structural_density` (`0.0071`), `class_logical_loc` (`0.0069`), `total_parameter_count` (`0.0061`), `mean_method_complexity` (`0.0057`), `constructor_count` (`0.0057`), `field_count` (`0.0049`).
- **By Training MDI Importance:** `class_loc` (`0.1027`), `total_method_call_count` (`0.0713`), `total_statement_count` (`0.0698`), `class_logical_loc` (`0.0651`), `total_property_access_count` (`0.0628`), `total_if_count` (`0.0479`), `total_cyclomatic_complexity` (`0.0450`).

### Error Breakdown & Base-Rate PPV Sensitivity (`holdout_error_analysis.csv`)
- **True Positives (`n=287`):** `median_loc=351.0`, `median_methods=12.0`, `median_wmc=57.0`, `median_nest=4.0`, `mean_prob=0.8186`.
- **False Positives (`n=57`):** Large, complex candidate-clean classes (e.g., `StableSwarmUI/BackendHandler` [`class_loc=894, WMC=118, prob=0.9753`], `slskd/Application` [`1691 LOC, WMC=209, prob=0.9527`], `EFCore.BulkExtensions/BatchUtil` [`955 LOC, WMC=168, prob=0.9499`]) whose structural complexity closely mirrors defect-prone classes or may mask dormant unreported bugs under Open-World labeling (`median_loc=186.0`, `median_wmc=36.0`).
- **False Negatives (`n=176`):** Concise classes carrying semantic, API-contract, serialization, or domain-logic bugs that do not inflate AST volume (`median_loc=48.0`, `median_wmc=7.0`, `mean_prob=0.3761`; e.g., `coverlet/ConfigurationExtensions` [`7 LOC, WMC=1, prob=0.0924`], `YamlDotNet/YamlSerializableAttribute` [`21 LOC, WMC=2, prob=0.1011`]).
- **Per-Repository Holdout Variance:** Strongest precision on dense stateful systems (`MessagePack-CSharp` `100.0%`, `testcontainers-dotnet` `100.0%`, `microsoft/FASTER` `98.36%`, `modelcontextprotocol/csharp-sdk` `94.29%`); lower precision on small repositories with very few positive classes (`slskd` `33.33%` [`1` pos], `RetroBar` `38.46%` [`6` pos], `Electron.NET` `40.00%` [`6` pos]).
- **Bayesian Prevalence Adjustment (`class_optimization_summary.json`):** At empirical study prevalence ($\pi = 0.4954$), Bayes PPV $= 84.69\%$; at real-world defect prevalences ($\pi \in \{0.20, 0.10, 0.05, 0.02\}$), expected PPV shifts to **`58.48%`**, **`38.50%`**, **`22.87%`**, and **`10.31%`** respectively.
