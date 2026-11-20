# Controlled Machine Learning Model Optimization Report

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code (`CISE_Project2`)  
**Dataset:** Dataset Snapshot #2 (`csharp_empirical_v2_v2.0.0.csv`, $N = 578$ methods, 5 repositories, 26 Roslyn static metrics)  
**Validation Protocol:** Nested Repository-Level Cross-Validation ($5$-Fold Outer `GroupKFold` $\times$ $4$-Fold Inner `GroupKFold`)  
**Experiment Script:** [`2_SourceCode/Scripts/run_model_optimization.py`](../../2_SourceCode/Scripts/run_model_optimization.py)  

---

## 1. Objective

Evaluate whether cross-repository defect prediction ranking (`ROC-AUC`, `PR-AUC`), probabilistic prediction error (`Brier score`), and thresholded classification performance (`F1`, `Recall`, `Precision`) on Dataset #2 can be improved over the baseline `rf_compact_regularized` configuration without introducing data leakage, label modification, or holdout reuse.

---

## 2. Baseline Configuration

### 2.1 Dataset #2 Composition

| Repository ID | Repository Name | Total Methods | Defect-Prone (`1`) | Candidate-Clean (`0`) | Positive Rate |
| :---: | :--- | ---: | ---: | ---: | ---: |
| 4 | `Humanizr/Humanizer` | 291 | 139 | 152 | 47.77% |
| 15 | `serilog/serilog` | 134 | 66 | 68 | 49.25% |
| 3 | `LuckyPennySoftware/MediatR` | 91 | 43 | 48 | 47.25% |
| 16 | `App-vNext/Polly` | 34 | 17 | 17 | 50.00% |
| 14 | `FluentValidation/FluentValidation` | 28 | 14 | 14 | 50.00% |
| **Total** | **5 Repositories** | **578** | **279** | **299** | **48.27%** |

### 2.2 Baseline Model (`rf_compact_regularized`)

| Parameter | Baseline Value |
| :--- | :--- |
| Estimator | `RandomForestClassifier` |
| `n_estimators` | 100 |
| `max_depth` | 8 |
| `min_samples_split` | 5 |
| `min_samples_leaf` | 4 |
| `max_features` | `sqrt` |
| `class_weight` | `balanced` |
| `random_state` | 42 |

### 2.3 Baseline Reference Metrics

The historical baseline (`3_TestResults/CrossValidation/experiment_results.json`, `scikit-learn 1.6.1`) selected both the model configuration and the tuned threshold ($\tau^* = 0.40$) on the 5-fold outer out-of-fold predictions. Under the current runtime (`scikit-learn 1.9.1`) and under nested threshold selection ($\tau_{\text{inner}}^*$ chosen inside each 4-repository inner loop), baseline performance is:

| Evaluation Protocol | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical 5-Fold Mean (`sklearn 1.6.1`) | 0.50 | 67.34% ± 4.91% | 68.24% ± 12.02% | 74.03% ± 15.57% | 0.6859 ± 0.0247 | 0.7025 ± 0.1303 | 0.6401 ± 0.1138 | 0.2144 ± 0.0396 |
| Historical Pooled OOF (Unnested $\tau^*$) | 0.40 | 70.42% | 64.21% | 87.46% | 0.7405 | 0.7025 | 0.6401 | 0.2144 |
| Current 5-Fold Mean (`sklearn 1.9.1`) | 0.50 | 67.48% ± 4.86% | 68.34% ± 12.06% | 74.32% ± 15.32% | 0.6879 ± 0.0243 | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 |
| Current 5-Fold Mean (Nested $\tau_{\text{inner}}^*$) | `[0.40, 0.40, 0.25, 0.30, 0.35]` | 67.28% ± 11.98% | 62.54% ± 10.55% | 92.81% ± 6.38% | 0.7408 ± 0.0760 | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 |
| Current Pooled OOF (Nested $\tau_{\text{inner}}^*$) | `[0.40, 0.40, 0.25, 0.30, 0.35]` | 68.17% | 61.85% | 88.89% | 0.7294 | 0.7034 | 0.5949 | 0.2109 |
| Historical Holdout (`Newtonsoft.Json`, $N=159$) | 0.40 | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.7917 | 0.1713 |

When evaluated with nested threshold selection ($\tau_{\text{inner}}^*$), the baseline `rf_compact_regularized` pooled OOF F1 is `0.7294` (`TN=146, FP=153, FN=31, TP=248`) versus `0.7405` under unnested threshold selection ($\tau^*=0.40$), showing $+1.11$ percentage points of threshold-selection optimism in the unnested protocol.

---

## 3. Experimental Methodology

Five-fold `GroupKFold` was used for outer validation. Four-fold `GroupKFold` was used for inner model and threshold selection. Each validation fold contained a repository excluded from the corresponding training partition:

1. **Outer Validation Loop ($K_{\text{outer}} = 5$):** Holds out one complete repository per outer fold and passes the remaining four repositories to the inner loop.
2. **Inner Validation Loop ($K_{\text{inner}} = 4$):** Holds out one repository per inner fold (training on the remaining three repositories).
3. **In-Fold Preprocessing and Feature Selection:** Median imputation (`SimpleImputer`), zero-variance pruning (`VarianceThreshold`), feature subset selection, and feature scaling (`StandardScaler` / `RobustScaler` for linear models) are fitted only on the training partition of each fold.
4. **Inner Out-of-Fold Threshold Selection:** Predicted probabilities across the 4 inner validation folds are pooled to select operating thresholds ($\tau_{F1}^*$, $\tau_{F2}^*$, $\tau_{F0.5}^*$) without access to the outer validation repository.
5. **Outer Refit and Evaluation:** Each pipeline is refitted on the 4 outer-training repositories and evaluated once on the outer validation repository at $\tau = 0.50$ and at the inner-selected $\tau_{F1}^*$.
6. **Holdout Quarantine:** `JamesNK/Newtonsoft.Json` was not used during feature analysis, hyperparameter tuning, threshold selection, or model selection.

---

## 4. Candidate Models and Search Spaces

Twenty configurations across six estimator families, four feature selection strategies, and three scaling modes were evaluated:

| Config ID | Family | Feature Set | Scaler | Key Hyperparameters |
| :--- | :--- | :--- | :--- | :--- |
| `rf_compact_regularized_baseline` | Random Forest (Baseline) | `all_26` | `none` | `n_estimators=100, max_depth=8, min_samples_split=5, min_samples_leaf=4, max_features='sqrt', class_weight='balanced'` |
| `rf_shallow_depth6_leaf6_bal` | Random Forest | `all_26` | `none` | `n_estimators=200, max_depth=6, min_samples_split=8, min_samples_leaf=6, max_features='sqrt', class_weight='balanced'` |
| `rf_depth6_leaf8_log2_bal` | Random Forest | `all_26` | `none` | `n_estimators=200, max_depth=6, min_samples_split=10, min_samples_leaf=8, max_features='log2', class_weight='balanced'` |
| `rf_depth8_leaf6_balsub` | Random Forest | `all_26` | `none` | `n_estimators=200, max_depth=8, min_samples_split=6, min_samples_leaf=6, max_features='sqrt', class_weight='balanced_subsample'` |
| `rf_compact_unweighted` | Random Forest | `all_26` | `none` | `n_estimators=100, max_depth=8, min_samples_split=5, min_samples_leaf=4, max_features='sqrt', class_weight=None` |
| `rf_compact_corr_pruned` | Random Forest (FS) | `corr_pruned_085` | `none` | Baseline RF with in-fold Spearman $|\rho| > 0.85$ collinearity pruning |
| `rf_compact_perm_top12` | Random Forest (FS) | `inner_perm_top12` | `none` | Baseline RF with in-fold top-12 permutation importance selection |
| `rf_compact_theoretical_core10` | Random Forest (FS) | `theoretical_core10` | `none` | Baseline RF on 10 complexity/control-flow/OOP metrics |
| `et_depth8_leaf4_sqrt_bal` | Extra Trees | `all_26` | `none` | `n_estimators=200, max_depth=8, min_samples_split=5, min_samples_leaf=4, max_features='sqrt', class_weight='balanced'` |
| `et_depth6_leaf6_log2_bal` | Extra Trees | `all_26` | `none` | `n_estimators=200, max_depth=6, min_samples_split=8, min_samples_leaf=6, max_features='log2', class_weight='balanced'` |
| `et_depth8_leaf4_unweighted` | Extra Trees | `all_26` | `none` | `n_estimators=200, max_depth=8, min_samples_split=5, min_samples_leaf=4, max_features='sqrt', class_weight=None` |
| `hgb_lr005_depth5_leaf20_l2_1` | HistGradientBoosting | `all_26` | `none` | `learning_rate=0.05, max_iter=100, max_depth=5, max_leaf_nodes=15, min_samples_leaf=20, l2=1.0, class_weight='balanced'` |
| `hgb_lr003_depth3_leaf25_l2_5` | HistGradientBoosting | `all_26` | `none` | `learning_rate=0.03, max_iter=100, max_depth=3, max_leaf_nodes=7, min_samples_leaf=25, l2=5.0, class_weight='balanced'` |
| `gb_lr005_depth3_leaf8_sub08` | Gradient Boosting | `all_26` | `none` | `n_estimators=100, learning_rate=0.05, max_depth=3, min_samples_leaf=8, subsample=0.8` |
| `gb_lr003_depth2_leaf12_sub08` | Gradient Boosting | `all_26` | `none` | `n_estimators=100, learning_rate=0.03, max_depth=2, min_samples_leaf=12, subsample=0.8` |
| `lr_c01_std_bal` | Logistic Regression | `all_26` | `standard` | `C=0.1, penalty='l2', class_weight='balanced'` |
| `lr_c1_std_bal` | Logistic Regression | `all_26` | `standard` | `C=1.0, penalty='l2', class_weight='balanced'` |
| `lr_c01_robust_bal` | Logistic Regression | `all_26` | `robust` | `C=0.1, penalty='l2', class_weight='balanced'` |
| `lr_c01_robust_corr_pruned` | Logistic Regression | `corr_pruned_085` | `robust` | `C=0.1, penalty='l2', class_weight='balanced'`, collinearity-pruned |
| `rf_compact_calibrated_sigmoid` | Calibrated RF | `all_26` | `none` | Baseline RF wrapped in `CalibratedClassifierCV(method='sigmoid', cv=3)` |

---

## 5. Nested Cross-Validation Results

### 5.1 Complete 20-Configuration Benchmark (Sorted by Outer 5-Fold Mean ROC-AUC)

| Rank | Configuration ID | Outer ROC-AUC (Mean ± Std) | Outer PR-AUC (Mean ± Std) | Outer Brier (Mean ± Std) | Outer F1 $\tau=0.50$ (Mean ± Std) | Outer F1 Nested $\tau_{\text{inner}}^*$ (Mean ± Std) | Pooled ROC-AUC | Pooled Brier | Pooled F1 ($\tau_{\text{inner}}^*$) | Pooled Recall ($\tau_{\text{inner}}^*$) | Pooled Precision ($\tau_{\text{inner}}^*$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `et_depth6_leaf6_log2_bal` | 0.7349 ± 0.0703 | 0.6443 ± 0.0496 | 0.2062 ± 0.0213 | 0.6867 ± 0.1394 | 0.7667 ± 0.0723 | 0.7470 | 0.2008 | 0.7653 | 91.76% | 65.64% |
| 2 | `et_depth8_leaf4_sqrt_bal` | 0.7349 ± 0.0801 | 0.6557 ± 0.0557 | 0.2056 ± 0.0260 | 0.6622 ± 0.1326 | 0.7324 ± 0.0492 | 0.7322 | 0.2006 | 0.7492 | 88.89% | 64.75% |
| 3 | `et_depth8_leaf4_unweighted` | 0.7319 ± 0.0739 | 0.6488 ± 0.0434 | 0.2063 ± 0.0246 | 0.6320 ± 0.1266 | 0.7417 ± 0.0907 | 0.7308 | 0.2015 | 0.7428 | 87.46% | 64.55% |
| 4 | `rf_compact_corr_pruned` | 0.7315 ± 0.1142 | 0.6595 ± 0.1103 | 0.2096 ± 0.0280 | 0.6977 ± 0.0241 | 0.7302 ± 0.0533 | 0.7219 | 0.2069 | 0.7262 | 90.32% | 60.72% |
| 5 | `rf_compact_theoretical_core10` | 0.7233 ± 0.1072 | 0.6663 ± 0.1008 | 0.2218 ± 0.0348 | 0.6437 ± 0.1361 | 0.7225 ± 0.0473 | 0.7076 | 0.2210 | 0.7300 | 86.74% | 63.02% |
| 6 | `rf_depth6_leaf8_log2_bal` | 0.7216 ± 0.1156 | 0.6465 ± 0.1026 | 0.2055 ± 0.0374 | 0.7517 ± 0.0709 | 0.7539 ± 0.0706 | 0.7119 | 0.2043 | 0.7406 | 88.53% | 63.66% |
| 7 | `lr_c01_robust_corr_pruned` | 0.7150 ± 0.0851 | 0.6425 ± 0.0712 | 0.2370 ± 0.0294 | 0.5359 ± 0.1124 | 0.7153 ± 0.0606 | 0.7350 | 0.2204 | 0.7052 | 85.30% | 60.10% |
| 8 | `lr_c01_robust_bal` | 0.7146 ± 0.0973 | 0.6495 ± 0.0828 | 0.2345 ± 0.0334 | 0.5722 ± 0.1064 | 0.7316 ± 0.0677 | 0.7350 | 0.2212 | 0.7304 | 91.76% | 60.66% |
| 9 | `rf_depth8_leaf6_balsub` | 0.7103 ± 0.1156 | 0.6340 ± 0.1012 | 0.2116 ± 0.0334 | 0.7075 ± 0.0254 | 0.7287 ± 0.0359 | 0.7031 | 0.2086 | 0.7212 | 85.30% | 62.47% |
| 10 | `rf_compact_calibrated_sigmoid` | 0.7060 ± 0.1219 | 0.6215 ± 0.1056 | 0.2180 ± 0.0334 | 0.6832 ± 0.0630 | 0.7363 ± 0.0679 | 0.6916 | 0.2130 | 0.7347 | 90.32% | 61.92% |
| 11 | `rf_compact_regularized_baseline` | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 | 0.6879 ± 0.0243 | 0.7408 ± 0.0760 | 0.7034 | 0.2109 | 0.7294 | 88.89% | 61.85% |
| 12 | `lr_c01_std_bal` | 0.7027 ± 0.0857 | 0.6336 ± 0.0738 | 0.2438 ± 0.0263 | 0.5144 ± 0.1776 | 0.6703 ± 0.0776 | 0.7165 | 0.2299 | 0.6738 | 78.49% | 59.03% |
| 13 | `rf_shallow_depth6_leaf6_bal` | 0.7011 ± 0.1329 | 0.6292 ± 0.1114 | 0.2118 ± 0.0360 | 0.7176 ± 0.0335 | 0.7393 ± 0.0485 | 0.7068 | 0.2070 | 0.7395 | 88.53% | 63.50% |
| 14 | `hgb_lr003_depth3_leaf25_l2_5` | 0.6937 ± 0.1532 | 0.6363 ± 0.1143 | 0.2177 ± 0.0477 | 0.6862 ± 0.0676 | 0.7383 ± 0.0800 | 0.6883 | 0.2179 | 0.7158 | 87.10% | 60.75% |
| 15 | `rf_compact_unweighted` | 0.6925 ± 0.1114 | 0.6204 ± 0.0886 | 0.2207 ± 0.0306 | 0.6507 ± 0.0688 | 0.7532 ± 0.0712 | 0.6938 | 0.2154 | 0.7362 | 88.53% | 63.01% |
| 16 | `gb_lr003_depth2_leaf12_sub08` | 0.6899 ± 0.1503 | 0.6398 ± 0.1149 | 0.2159 ± 0.0377 | 0.7102 ± 0.0605 | 0.7439 ± 0.0844 | 0.6925 | 0.2127 | 0.7398 | 90.68% | 62.47% |
| 17 | `lr_c1_std_bal` | 0.6834 ± 0.1012 | 0.6235 ± 0.0842 | 0.2619 ± 0.0385 | 0.4988 ± 0.1252 | 0.6904 ± 0.1124 | 0.6880 | 0.2507 | 0.6802 | 78.14% | 60.22% |
| 18 | `hgb_lr005_depth5_leaf20_l2_1` | 0.6814 ± 0.0990 | 0.6261 ± 0.0741 | 0.2465 ± 0.0416 | 0.6022 ± 0.0607 | 0.6750 ± 0.1008 | 0.6738 | 0.2401 | 0.6239 | 66.31% | 58.92% |
| 19 | `gb_lr005_depth3_leaf8_sub08` | 0.6797 ± 0.1070 | 0.6186 ± 0.0782 | 0.2384 ± 0.0308 | 0.6281 ± 0.0419 | 0.7486 ± 0.0565 | 0.6880 | 0.2310 | 0.7410 | 91.76% | 62.14% |
| 20 | `rf_compact_perm_top12` | 0.6765 ± 0.1435 | 0.6165 ± 0.1253 | 0.2251 ± 0.0470 | 0.7123 ± 0.0377 | 0.7316 ± 0.0724 | 0.6832 | 0.2178 | 0.7319 | 88.53% | 62.37% |

### 5.2 Full Multi-Family Nested Selection (Inner 4-Fold Model + Threshold Selection per Outer Fold)

| Outer Fold | Held-Out Repository | Inner-Selected Configuration | Inner Pooled ROC-AUC | Inner Selected $\tau_{\text{inner}}^*$ | Outer ROC-AUC | Outer PR-AUC | Outer Brier | Outer F1 ($\tau_{\text{inner}}^*$) | Outer Recall ($\tau_{\text{inner}}^*$) | Outer Precision ($\tau_{\text{inner}}^*$) |
| :---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `Humanizr/Humanizer` | `rf_compact_calibrated_sigmoid` | 0.7301 | 0.35 | 0.7846 | 0.6337 | 0.1872 | 0.7947 | 86.33% | 73.62% |
| 2 | `serilog/serilog` | `lr_c01_robust_bal` | 0.7846 | 0.25 | 0.7130 | 0.6651 | 0.2293 | 0.6702 | 96.97% | 51.20% |
| 3 | `LuckyPennySoftware/MediatR` | `lr_c01_robust_corr_pruned` | 0.7638 | 0.30 | 0.6233 | 0.5667 | 0.2499 | 0.6609 | 88.37% | 52.78% |
| 4 | `App-vNext/Polly` | `et_depth6_leaf6_log2_bal` | 0.7469 | 0.35 | 0.8270 | 0.7125 | 0.1908 | 0.8649 | 94.12% | 80.00% |
| 5 | `FluentValidation` | `et_depth6_leaf6_log2_bal` | 0.7462 | 0.40 | 0.7041 | 0.6342 | 0.1985 | 0.7778 | 100.00% | 63.64% |
| **Mean ± Std** | **5 Outer Folds** | — | — | — | **0.7304 ± 0.0703** | **0.6424 ± 0.0475** | **0.2111 ± 0.0239** | **0.7537 ± 0.0777** | **93.16%** | **64.25%** |
| **Pooled OOF** | **$N = 578$** | — | — | — | — | — | — | **0.7401** | **90.32%** | **62.69%** |

---

## 6. Per-Repository Performance Comparison

| Repository ($N$) | Metric | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_depth6_leaf8_log2_bal`) | Optimized Extra Trees (`et_depth6_leaf6_log2_bal`) |
| :--- | :--- | ---: | ---: | ---: |
| `Humanizr/Humanizer` ($N=291$) | ROC-AUC / Brier | 0.7981 / 0.1839 | 0.7869 / 0.1819 | 0.7983 / 0.1803 |
| | F1 ($\tau = 0.50$) | 0.6866 | 0.7402 | 0.7724 |
| | F1 (Nested $\tau_{\text{inner}}^*$) | 0.7703 ($\tau=0.40$) | 0.7744 ($\tau=0.40$) | 0.8113 ($\tau=0.40$) |
| `serilog/serilog` ($N=134$) | ROC-AUC / Brier | 0.5865 / 0.2702 | 0.6377 / 0.2503 | 0.7146 / 0.2231 |
| | F1 ($\tau = 0.50$) | 0.6995 | 0.7191 | 0.7891 |
| | F1 (Nested $\tau_{\text{inner}}^*$) | 0.6842 ($\tau=0.40$) | 0.6878 ($\tau=0.35$) | 0.7251 ($\tau=0.40$) |
| `LuckyPennySoftware/MediatR` ($N=91$) | ROC-AUC / Brier | 0.6781 / 0.2210 | 0.6783 / 0.2238 | 0.6306 / 0.2381 |
| | F1 ($\tau = 0.50$) | 0.6593 | 0.6593 | 0.5870 |
| | F1 (Nested $\tau_{\text{inner}}^*$) | 0.6555 ($\tau=0.25$) | 0.7027 ($\tau=0.30$) | 0.6542 ($\tau=0.40$) |
| `App-vNext/Polly` ($N=34$) | ROC-AUC / Brier | 0.8997 / 0.1580 | 0.9135 / 0.1449 | 0.8270 / 0.1908 |
| | F1 ($\tau = 0.50$) | 0.6667 | 0.8750 | 0.4615 |
| | F1 (Nested $\tau_{\text{inner}}^*$) | 0.8718 ($\tau=0.30$) | 0.8824 ($\tau=0.35$) | 0.8649 ($\tau=0.35$) |
| `FluentValidation` ($N=28$) | ROC-AUC / Brier | 0.5561 / 0.2399 | 0.5918 / 0.2264 | 0.7041 / 0.1985 |
| | F1 ($\tau = 0.50$) | 0.7273 | 0.7647 | 0.8235 |
| | F1 (Nested $\tau_{\text{inner}}^*$) | 0.7222 ($\tau=0.35$) | 0.7222 ($\tau=0.40$) | 0.7778 ($\tau=0.40$) |

---

## 7. Feature Analysis

Full feature statistics and pairwise correlations are stored in [`feature_importance.csv`](feature_importance.csv) and [`feature_correlation.csv`](feature_correlation.csv).

### 7.1 Collinearity Among Size and Control-Flow Metrics

| Feature 1 | Feature 2 | Pearson $r$ | Spearman $\rho$ | Relationship |
| :--- | :--- | ---: | ---: | :--- |
| `logical_loc` | `statement_count` | 0.9995 | 0.9700 | Executable statements count |
| `loc` | `method_length` | 0.9585 | 0.9559 | Physical lines vs. character length |
| `max_nesting_depth` | `if_count` | 0.7675 | 0.9040 | Conditional branching vs. block depth |
| `cyclomatic_complexity` | `max_nesting_depth` | 0.7757 | 0.8850 | Branch predicates vs. nested blocks |
| `cyclomatic_complexity` | `if_count` | 0.9119 | 0.8829 | `if` statements drive McCabe complexity |
| `logical_loc` | `max_nesting_depth` | 0.6641 | 0.8643 | Statement count vs. nesting depth |

### 7.2 Near-Constant and Weak Features

| Feature | Zero Fraction | Variance | Univariate ROC-AUC | Outer Permutation ROC-AUC Mean | Note |
| :--- | ---: | ---: | ---: | ---: | :--- |
| `field_access_count` | 99.48% | 0.0103 | 0.5019 | 0.00000 | Zero in 575/578 methods; pruned as constant in 2 of 5 outer folds |
| `switch_count` | 97.75% | 0.0220 | 0.5010 | 0.00000 | Present in 2.25% of methods |
| `try_catch_count` | 96.19% | 0.0518 | 0.5186 | 0.00015 | Sparse across library methods |
| `is_async` | 94.29% | 0.0538 | 0.5106 | 0.00346 | Sparse modifier flag |
| `break_continue_count` | 91.35% | 0.6447 | 0.5444 | -0.00030 | Sparse loop-jump counter |

### 7.3 MDI vs. Held-Out Permutation Importance and Repository Proxy Risk

| Feature | MDI Mean (Gini) | Outer Perm ROC-AUC Mean (Pos Folds) | Outer Perm F1 Mean | Univariate ROC-AUC | Repo Proxy OvR AUC |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `property_access_count` | 0.0568 | +0.00834 (4/5) | -0.00583 | 0.6572 | 0.5872 |
| `local_variable_count` | 0.0253 | +0.00710 (2/5) | +0.00209 | 0.6641 | 0.5465 |
| `assignment_count` | 0.0162 | +0.00654 (5/5) | -0.01124 | 0.6126 | 0.5246 |
| `loop_count` | 0.0060 | +0.00442 (4/5) | +0.00406 | 0.5884 | 0.5464 |
| `if_count` | 0.0232 | +0.00373 (4/5) | +0.00250 | 0.6590 | 0.5798 |
| `return_count` | 0.0726 | +0.00182 (2/5) | +0.03012 | 0.5358 | 0.5987 |
| `method_length` | 0.1822 | -0.00899 (3/5) | +0.05187 | 0.7823 | 0.5566 |
| `loc` | 0.1406 | -0.01026 (2/5) | +0.05348 | 0.7812 | 0.5520 |
| `parameter_count` | 0.0989 | -0.01575 (3/5) | +0.00838 | 0.7368 | 0.6286 |
| `is_static` | 0.0623 | -0.04154 (2/5) | -0.01424 | 0.6577 | 0.5634 |

---

## 8. Decision Threshold and Probability Calibration Analysis

Ranking metrics (`ROC-AUC`, `PR-AUC`) and probabilistic prediction error (`Brier score`) depend only on the predicted probabilities $\hat{p}_i$ and do not change when the decision threshold $\tau$ is varied. Adjusting $\tau$ alters only thresholded classification metrics (`F1`, `F2`, `Precision`, `Recall`, `Accuracy`).

| Model Configuration | Threshold Mode | Threshold ($\tau$) | Accuracy | Precision | Recall | F1 | F2 | FPR | ROC-AUC | Brier | Confusion Matrix [TN, FP, FN, TP] |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `rf_compact_regularized_baseline` | Nominal Fixed | 0.50 | 67.47% | 64.09% | 74.19% | 0.6877 | 0.7192 | 38.80% | 0.7034 | 0.2109 | `[183, 116, 72, 207]` |
| `rf_compact_regularized_baseline` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.4, 0.25, 0.3, 0.35]` | 68.17% | 61.85% | 88.89% | 0.7294 | 0.8174 | 51.17% | 0.7034 | 0.2109 | `[146, 153, 31, 248]` |
| `rf_depth6_leaf8_log2_bal` | Nominal Fixed | 0.50 | 71.28% | 66.77% | 80.65% | 0.7305 | 0.7743 | 37.46% | 0.7119 | 0.2043 | `[187, 112, 54, 225]` |
| `rf_depth6_leaf8_log2_bal` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.35, 0.3, 0.35, 0.4]` | 70.07% | 63.66% | 88.53% | 0.7406 | 0.8211 | 47.16% | 0.7119 | 0.2043 | `[158, 141, 32, 247]` |
| `et_depth6_leaf6_log2_bal` | Recall Screening Fixed | 0.35 | 70.93% | 63.25% | 94.98% | 0.7593 | 0.8632 | 51.51% | 0.7470 | 0.2008 | `[145, 154, 14, 265]` |
| `et_depth6_leaf6_log2_bal` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.4, 0.4, 0.35, 0.4]` | 72.84% | 65.64% | 91.76% | 0.7653 | 0.8499 | 44.82% | 0.7470 | 0.2008 | `[165, 134, 23, 256]` |
| `et_depth6_leaf6_log2_bal` | Fixed Modal Threshold | 0.40 | 73.01% | 65.81% | 91.76% | 0.7665 | 0.8505 | 44.48% | 0.7470 | 0.2008 | `[166, 133, 23, 256]` |
| `et_depth6_leaf6_log2_bal` | Balanced / Triage Fixed | 0.45 | 74.39% | 68.45% | 87.10% | 0.7666 | 0.8260 | 37.46% | 0.7470 | 0.2008 | `[187, 112, 36, 243]` |
| `et_depth6_leaf6_log2_bal` | Nominal Fixed | 0.50 | 73.18% | 70.00% | 77.78% | 0.7368 | 0.7609 | 31.10% | 0.7470 | 0.2008 | `[206, 93, 62, 217]` |

Note on probability calibration vs. Brier score:
- Brier score ($\frac{1}{N}\sum_{i=1}^N (\hat{p}_i - y_i)^2$) measures probabilistic prediction error; reporting a Brier score does not establish that a classifier is probability-calibrated.
- Explicit sigmoid calibration via `CalibratedClassifierCV(method='sigmoid', cv=3)` (`rf_compact_calibrated_sigmoid`) was evaluated inside the training partitions and yielded an outer Brier score of `0.2180 ± 0.0334` (worse than uncalibrated `rf_compact_regularized` at `0.2146 ± 0.0398`), because fitting a parametric sigmoid on 4 repositories overfits to the training repositories' probability distribution. Regularizing tree depth and leaf size (`rf_depth6_leaf8_log2_bal`: `0.2055 ± 0.0374`; `et_depth6_leaf6_log2_bal`: `0.2062 ± 0.0213`) reduced outer Brier error without post-hoc calibration.

---

## 9. Error Analysis

Observation-level predictions and error classifications are recorded in [`error_analysis.csv`](error_analysis.csv). Under nested threshold evaluation on Dataset #2 ($N = 578$), `et_depth6_leaf6_log2_bal` produced 256 True Positives (TP), 165 True Negatives (TN), 134 False Positives (FP), and 23 False Negatives (FN).

| Quadrant | Count | Median `loc` (Mean) | Median `logical_loc` (Mean) | Median `cc` (Mean) | Median `nesting` (Mean) | Median `params` (Mean) | Median `calls` (Mean) |
| :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: |
| True Positive (TP) | 256 | 18.5 (30.33) | 7.0 (12.67) | 2.0 (4.74) | 1.0 (1.17) | 2.0 (2.47) | 4.0 (9.34) |
| True Negative (TN) | 165 | 3.0 (4.06) | 1.0 (1.12) | 1.0 (1.02) | 0.0 (0.02) | 0.0 (0.45) | 1.0 (1.05) |
| False Positive (FP) | 134 | 15.0 (18.26) | 5.0 (8.07) | 2.0 (3.43) | 1.0 (0.87) | 2.0 (2.14) | 2.0 (4.39) |
| False Negative (FN) | 23 | 5.0 (6.74) | 1.0 (1.13) | 1.0 (1.17) | 0.0 (0.04) | 2.0 (1.91) | 1.0 (0.83) |

- **False Negatives ($N = 23$):** 18 of 23 false negatives (`78.3%`) are 1-to-2 statement methods with `loc <= 12` and `cyclomatic_complexity <= 2` (median `loc = 5.0`, `cc = 1.0`). These defects involve semantic, literal, or type-contract errors not captured by static AST structure.
- **False Positives ($N = 134$):** Candidate-clean methods with elevated structural complexity (median `loc = 15.0`, mean `cc = 3.43`; 27 have `cc >= 6` or `loc >= 35`). Because `label = 0` reflects the absence of recorded bug fixes in the mined commit window rather than confirmed defect-free status, high-complexity false positives represent structurally complex code candidates for review.

---

## 10. Selected Models and Deployment Verification

### 10.1 Saved Versioned Artifacts

Both optimized models were retrained on all $N = 578$ observations of Dataset #2 (`DataPreprocessor` retaining all 26 Roslyn metrics) and saved in `3_TestResults/ModelOptimization/models/` and `4_AppBuild/Assets/Models/` without modifying the preserved baseline models:

1. **`et_nested_opt_v3_depth6_leaf6_log2.joblib` (`ExtraTreesClassifier`):** `n_estimators=200, max_depth=6, min_samples_split=8, min_samples_leaf=6, max_features='log2', class_weight='balanced', random_state=42`.
2. **`rf_nested_opt_v3_depth6_leaf8_log2.joblib` (`RandomForestClassifier`):** `n_estimators=200, max_depth=6, min_samples_split=10, min_samples_leaf=8, max_features='log2', class_weight='balanced', random_state=42`.

### 10.2 Verified Application Deployment and Threshold Behavior

- **Default Model Selection:** `ModelManager.list_saved_models()` orders `et_nested_opt_v3_depth6_leaf6_log2` first, followed by `rf_nested_opt_v3_depth6_leaf8_log2`, `exp_final_5fold_v2_best_rf_compact_regularized`, and `rf_csharp_empirical_model`.
- **Inference Threshold Behavior (`BugPredictor` in `2_SourceCode/Python/ml/predictor.py`):**
  - Binary prediction (`predicted_label`) calls `self.model.predict(df_proc)`, which uses `scikit-learn`'s nominal **$\tau = 0.50$** threshold (`argmax` over class probabilities). At $\tau = 0.50$, `et_nested_opt_v3_depth6_leaf6_log2` achieves pooled OOF F1 = `0.7368` (Accuracy `73.18%`, Precision `70.00%`, Recall `77.78%`), and `rf_nested_opt_v3_depth6_leaf8_log2` achieves outer fold mean F1 = `0.7517 ± 0.0709` (pooled OOF F1 = `0.7305`).
  - Risk categorization (`risk_category`) maps `predict_proba(df_proc)[:, 1]` using `PredictionSettings`: Low risk ($\le 0.30$), Medium risk ($0.31\text{--}0.60$), and High risk ($> 0.60$).
  - The serialized model bundles store nested cross-validation evaluation metrics (where inner-loop threshold selection selected $\tau_{\text{inner}}^* = 0.40$ in 4 of 5 folds and $0.35$ in 1 fold for Extra Trees), but `BugPredictor` does not override `model.predict()` with a custom threshold during live inference.

---

## 11. Comparison with the Original Baseline

| Metric (Nested 5-Fold GroupKFold on Dataset #2) | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_depth6_leaf8_log2_bal`) | Optimized Extra Trees (`et_depth6_leaf6_log2_bal`) |
| :--- | :---: | :---: | :---: |
| Outer 5-Fold ROC-AUC (Mean ± Std) | 0.7037 ± 0.1292 | 0.7216 ± 0.1156 | 0.7349 ± 0.0703 |
| Outer 5-Fold PR-AUC (Mean ± Std) | 0.6405 ± 0.1135 | 0.6465 ± 0.1026 | 0.6443 ± 0.0496 |
| Outer 5-Fold Brier Score (Mean ± Std) | 0.2146 ± 0.0398 | 0.2055 ± 0.0374 | 0.2062 ± 0.0213 |
| Pooled OOF ROC-AUC | 0.7034 | 0.7119 | 0.7470 |
| Pooled OOF PR-AUC | 0.5949 | 0.6070 | 0.6402 |
| Pooled OOF Brier Score | 0.2109 | 0.2043 | 0.2008 |
| Outer 5-Fold F1 at $\tau = 0.50$ (Mean ± Std) | 0.6879 ± 0.0243 | 0.7517 ± 0.0709 | 0.6867 ± 0.1394 |
| Pooled OOF F1 at $\tau = 0.50$ | 0.6877 | 0.7305 | 0.7368 |
| Outer 5-Fold F1 at Nested $\tau_{\text{inner}}^*$ (Mean ± Std) | 0.7408 ± 0.0760 | 0.7539 ± 0.0706 | 0.7667 ± 0.0723 |
| Pooled OOF F1 at Nested $\tau_{\text{inner}}^*$ | 0.7294 | 0.7406 | 0.7653 |
| Pooled OOF Recall at Nested $\tau_{\text{inner}}^*$ | 88.89% (248/279) | 88.53% (247/279) | 91.76% (256/279) |
| Pooled OOF Precision at Nested $\tau_{\text{inner}}^*$ | 61.85% | 63.66% | 65.64% |
| Pooled OOF Accuracy at Nested $\tau_{\text{inner}}^*$ | 68.17% | 70.07% | 72.84% |

---

## 12. Limitations and Conclusion

### 12.1 Limitations
1. **Repository Count and Size Imbalance:** Only five repositories were used for training and nested cross-validation. `Humanizer` accounts for 50.35% of Dataset #2 (291/578 methods), whereas `Polly` (34) and `FluentValidation` (28) represent 10.73% combined.
2. **Static Metric Scope:** Static AST metrics cannot identify semantic or type-contract defects in short, low-complexity methods (`18/23` false negatives have `loc <= 12` and `cc <= 2`).
3. **Candidate-Clean and Temporal Constraints:** Candidate-clean methods (`label = 0`) are sampled from `HEAD` and are not confirmed defect-free, whereas positive observations (`label = 1`) are extracted from historical pre-fix revisions.
4. **Absence of External Holdout Evaluation for Optimized Models:** Because `JamesNK/Newtonsoft.Json` was used in the historical baseline study, it was excluded from optimization. A new independent repository is required to evaluate the optimized models externally.

### 12.2 Conclusion
Nested repository-level cross-validation ($5 \times 4$ `GroupKFold`) established an unbiased baseline (`Pooled OOF F1 = 0.7294`, `Outer ROC-AUC = 0.7037 ± 0.1292`) and showed that stronger tree regularization (`max_depth=6`, `min_samples_leaf=6..8`, `max_features='log2'`) reduces sensitivity to collinear size metrics across repositories. On Dataset #2, `rf_depth6_leaf8_log2_bal` achieved outer ROC-AUC `0.7216 ± 0.1156` and nested F1 `0.7539 ± 0.0706` (pooled `0.7406`), and `et_depth6_leaf6_log2_bal` achieved outer ROC-AUC `0.7349 ± 0.0703` (pooled `0.7470`) and nested F1 `0.7667 ± 0.0723` (pooled `0.7653`).
