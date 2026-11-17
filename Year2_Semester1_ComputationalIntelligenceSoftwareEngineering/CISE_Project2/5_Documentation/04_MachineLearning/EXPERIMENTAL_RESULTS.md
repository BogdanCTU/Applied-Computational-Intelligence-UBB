# Empirical Experimental Results

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Artifacts:**  
- Cross-Validation: `3_TestResults/CrossValidation/experiment_results.json`, `3_TestResults/CrossValidation/experiment_results.csv`  
- Frozen Model: `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib`  
- Independent Holdout: `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json`  

---

## 1. Dataset Composition

| Dataset | Version | Observations | Repositories | Defect-Prone (1) | Candidate-Clean (0) | Purpose |
| :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| `csharp_empirical_v1` | `1.0.0` | 483 | 3 | 226 (46.79%) | 257 (53.21%) | Exploratory corpus |
| `csharp_empirical_v2` | `2.0.0` | 578 | 5 | 279 (48.27%) | 299 (51.73%) | 5-fold `GroupKFold` cross-validation |
| `newtonsoft_holdout` | — | 159 | 1 | 79 (49.69%) | 80 (50.31%) | Independent holdout evaluation |

### Dataset #2 Repository Distribution

| Repository ID | Full Name | Defect-Prone (1) | Candidate-Clean (0) | Total | Share |
| :---: | :--- | ---: | ---: | ---: | ---: |
| 4 | `Humanizr/Humanizer` | 139 | 152 | 291 | 50.35% |
| 15 | `serilog/serilog` | 66 | 68 | 134 | 23.18% |
| 3 | `LuckyPennySoftware/MediatR` | 43 | 48 | 91 | 15.74% |
| 16 | `App-vNext/Polly` | 17 | 17 | 34 | 5.88% |
| 14 | `FluentValidation/FluentValidation` | 14 | 14 | 28 | 4.84% |
| **Total** | **5 Repositories** | **279** | **299** | **578** | **100.00%** |

All 578 observations contain 26 numeric Roslyn metrics with 0 missing values and 0 test files.

---

## 2. Five-Fold GroupKFold Partitioning

`GroupKFold` ($K=5$) groups observations by `repository_id`. Each fold holds out one repository for validation while training on the remaining four repositories:

| Fold | Validation Repository | Validation Methods | Training Repositories | Training Methods |
| :---: | :--- | ---: | :--- | ---: |
| 1 | `Humanizr/Humanizer` | 291 | Serilog, MediatR, Polly, FluentValidation | 287 |
| 2 | `serilog/serilog` | 134 | Humanizer, MediatR, Polly, FluentValidation | 444 |
| 3 | `LuckyPennySoftware/MediatR` | 91 | Humanizer, Serilog, Polly, FluentValidation | 487 |
| 4 | `App-vNext/Polly` | 34 | Humanizer, Serilog, MediatR, FluentValidation | 544 |
| 5 | `FluentValidation/FluentValidation` | 28 | Humanizer, Serilog, MediatR, Polly | 550 |

---

## 3. Multi-Model Cross-Validation Benchmark ($\tau = 0.50$)

| Rank | Configuration ID | Algorithm | F1 (Mean ± Std) | Recall (Mean ± Std) | Precision (Mean ± Std) | Accuracy (Mean ± Std) | ROC-AUC | PR-AUC | Brier Score |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | ---: | ---: | :---: |
| 1 | `rf_compact_regularized` | Random Forest | 0.6859 ± 0.0247 | 0.7403 ± 0.1557 | 0.6824 ± 0.1202 | 0.6734 ± 0.0491 | 0.7025 | 0.6401 | 0.2144 ± 0.0396 |
| 2 | `rf_feature_constrained_log2` | Random Forest | 0.6385 ± 0.0641 | 0.6831 ± 0.1706 | 0.6384 ± 0.1197 | 0.6369 ± 0.0673 | 0.6974 | 0.6309 | 0.2209 ± 0.0375 |
| 3 | `rf_heavy_bagging_300` | Random Forest | 0.6262 ± 0.0633 | 0.6788 ± 0.1738 | 0.6117 ± 0.0984 | 0.6212 ± 0.0617 | 0.6874 | 0.6277 | 0.2265 ± 0.0376 |
| 4 | `rf_baseline_balanced` | Random Forest | 0.6108 ± 0.1176 | 0.6678 ± 0.1982 | 0.6046 ± 0.1157 | 0.6074 ± 0.0827 | 0.6792 | 0.6200 | 0.2249 ± 0.0410 |
| 5 | `dt_shallow_depth4` | Decision Tree | 0.5734 ± 0.2172 | 0.6166 ± 0.2646 | 0.5573 ± 0.1884 | 0.5721 ± 0.1345 | 0.5849 | 0.5630 | 0.2807 ± 0.0699 |
| 6 | `rf_deep_capacity` | Random Forest | 0.5577 ± 0.0739 | 0.5794 ± 0.1737 | 0.5811 ± 0.1147 | 0.5815 ± 0.0647 | 0.6552 | 0.5982 | 0.2429 ± 0.0435 |
| 7 | `lr_balanced_c1` | Logistic Regression | 0.4989 ± 0.1252 | 0.4538 ± 0.1469 | 0.5994 ± 0.1557 | 0.5709 ± 0.0894 | 0.6225 | 0.5694 | 0.2620 ± 0.0368 |
| 8 | `lr_standard_c1` | Logistic Regression | 0.4890 ± 0.1409 | 0.4360 ± 0.1651 | 0.6095 ± 0.1593 | 0.5744 ± 0.0877 | 0.6231 | 0.5699 | 0.2643 ± 0.0366 |
| 9 | `dt_depth8` | Decision Tree | 0.4695 ± 0.2194 | 0.4907 ± 0.2529 | 0.4844 ± 0.1983 | 0.5050 ± 0.1425 | 0.5097 | 0.5033 | 0.3993 ± 0.1017 |

### Per-Fold Results for `rf_compact_regularized` ($\tau = 0.50$)

| Fold | Held-Out Repository | Val Obs | Confusion Matrix [TN, FP, FN, TP] | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier |
| :---: | :--- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `Humanizr/Humanizer` | 291 | `[115, 37, 49, 90]` | 0.7045 | 0.7087 | 0.6475 | 0.6767 | 0.7972 | 0.1843 |
| 2 | `serilog/serilog` | 134 | `[15, 53, 2, 64]` | 0.5896 | 0.5470 | 0.9697 | 0.6995 | 0.5865 | 0.2702 |
| 3 | `LuckyPennySoftware/MediatR` | 91 | `[30, 18, 13, 30]` | 0.6593 | 0.6250 | 0.6977 | 0.6593 | 0.6781 | 0.2210 |
| 4 | `App-vNext/Polly` | 34 | `[16, 1, 8, 9]` | 0.7353 | 0.9000 | 0.5294 | 0.6667 | 0.8997 | 0.1579 |
| 5 | `FluentValidation` | 28 | `[7, 7, 2, 12]` | 0.6786 | 0.6316 | 0.8571 | 0.7273 | 0.5510 | 0.2384 |
| **Mean** | **5 Folds** | — | — | **0.6734** | **0.6824** | **0.7403** | **0.6859** | **0.7025** | **0.2144** |
| **Std** | Population ($\text{ddof}=0$) | — | — | 0.0491 | 0.1202 | 0.1557 | 0.0247 | 0.1303 | 0.0396 |

---

## 4. Cross-Validation Accuracy Reconciliation

| Metric | Aggregation Protocol | Threshold | Formula | Value |
| :--- | :--- | :---: | :--- | :---: |
| 5-Fold Mean Accuracy | Unweighted arithmetic mean across 5 folds | $\tau = 0.50$ | $\frac{1}{5}\sum_{k=1}^5 \text{Acc}_k$ | $0.6734 \pm 0.0491$ (67.34%) |
| Pooled OOF Nominal Accuracy | Pooled out-of-fold predictions ($N=578$) | $\tau = 0.50$ | $(183 + 205) / 578$ | 0.6713 (67.13%) |
| Pooled OOF Tuned Accuracy | Pooled out-of-fold predictions ($N=578$) | $\tau^* = 0.40$ | $(163 + 244) / 578$ | 0.7042 (70.42%) |

---

## 5. Out-of-Fold Decision Threshold Sweep (`rf_compact_regularized`)

| Threshold ($\tau$) | Accuracy | Precision | Recall | F1-Score | TN | FP | FN | TP |
| :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.20 | 0.5848 | 0.5401 | 0.9857 | 0.6978 | 63 | 236 | 4 | 275 |
| 0.30 | 0.6696 | 0.6046 | 0.9498 | 0.7388 | 122 | 177 | 14 | 265 |
| **0.40 ($\tau^*$)** | **0.7042** | **0.6421** | **0.8746** | **0.7405** | **163** | **136** | **35** | **244** |
| 0.45 | 0.6834 | 0.6385 | 0.7993 | 0.7099 | 172 | 127 | 56 | 223 |
| **0.50 (Nominal)** | **0.6713** | **0.6386** | **0.7348** | **0.6833** | **183** | **116** | **74** | **205** |
| 0.55 | 0.6765 | 0.6631 | 0.6703 | 0.6667 | 204 | 95 | 92 | 187 |
| 0.60 | 0.6626 | 0.6828 | 0.5556 | 0.6126 | 227 | 72 | 124 | 155 |
| 0.70 | 0.6211 | 0.7344 | 0.3369 | 0.4619 | 265 | 34 | 185 | 94 |
| 0.80 | 0.5467 | 0.8261 | 0.1362 | 0.2338 | 291 | 8 | 241 | 38 |

Selecting $\tau^* = 0.40$ on pooled out-of-fold predictions without nested cross-validation introduces mild threshold-selection bias on CV metrics; generalization of $\tau^* = 0.40$ is verified on the independent holdout repository below.

---

## 6. Frozen Model Specification

| Parameter | Value |
| :--- | :--- |
| Artifact Path | `4_AppBuild/Assets/Models/exp_final_5fold_v2_best_rf_compact_regularized.joblib` |
| SHA-256 | `625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e` |
| Algorithm | `RandomForestClassifier` |
| `n_estimators` | 100 |
| `max_depth` | 8 |
| `min_samples_split` | 5 |
| `min_samples_leaf` | 4 |
| `max_features` | `sqrt` |
| `class_weight` | `balanced` |
| `random_state` | 42 |
| Preprocessor | `DataPreprocessor` (median imputation, zero-variance pruning, 26 features) |

---

## 7. Independent Holdout Evaluation (`JamesNK/Newtonsoft.Json`)

Evaluated post-freeze on 159 production methods (79 defect-prone, 80 candidate-clean):

| Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier | TN | FP | FN | TP |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nominal ($\tau = 0.50$) | 74.21% | 69.79% | 84.81% | 0.7657 | 0.8209 | 0.7917 | 0.1713 | 51 | 29 | 12 | 67 |
| Tuned ($\tau^* = 0.40$) | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.7917 | 0.1713 | 49 | 31 | 8 | 71 |
