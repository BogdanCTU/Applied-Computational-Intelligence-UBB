# Empirical Experimental Results

**Project:** Machine Learning-Based Software Defect Prediction for C# Source Code  
**Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University  
**Course:** Computational Intelligence in Software Engineering (CISE) — Project 2  
**Authoritative Artifacts:**  
- Baseline Cross-Validation: `3_TestResults/CrossValidation/experiment_results.json`, `3_TestResults/CrossValidation/experiment_results.csv`  
- Historical Holdout: `3_TestResults/HoldoutEvaluation/newtonsoft_holdout_results.json`  
- Nested Optimization: `3_TestResults/ModelOptimization/nested_cv_summary.json`, `3_TestResults/ModelOptimization/nested_cv_results.csv`, `3_TestResults/ModelOptimization/model_comparison.csv`, `3_TestResults/ModelOptimization/per_repository_results.csv`, `3_TestResults/ModelOptimization/threshold_analysis.csv`  
- Model Bundles: `4_AppBuild/Assets/Models/` (`et_nested_opt_v3_depth6_leaf6_log2.joblib`, `rf_nested_opt_v3_depth6_leaf8_log2.joblib`, `exp_final_5fold_v2_best_rf_compact_regularized.joblib`, `rf_csharp_empirical_model.joblib`)  

---

## 1. Dataset Composition

| Dataset | Version | Observations | Repositories | Defect-Prone (1) | Candidate-Clean (0) | Purpose |
| :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| `csharp_empirical_v1` | `1.0.0` | 483 | 3 | 226 (46.79%) | 257 (53.21%) | Exploratory corpus |
| `csharp_empirical_v2` | `2.0.0` | 578 | 5 | 279 (48.27%) | 299 (51.73%) | 5-fold `GroupKFold` and $5 \times 4$ nested CV benchmark |
| `newtonsoft_holdout` | — | 159 | 1 | 79 (49.69%) | 80 (50.31%) | Historical baseline holdout (excluded from optimization) |

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

## 2. Validation Partitioning

Five-fold `GroupKFold` was used for outer validation. In the nested optimization experiment, four-fold `GroupKFold` was used within each outer training partition for inner model and threshold selection:

| Outer Fold | Validation Repository | Validation Methods | Outer Training Repositories (Used for 4-Fold Inner CV) | Training Methods |
| :---: | :--- | ---: | :--- | ---: |
| 1 | `Humanizr/Humanizer` | 291 | Serilog, MediatR, Polly, FluentValidation | 287 |
| 2 | `serilog/serilog` | 134 | Humanizer, MediatR, Polly, FluentValidation | 444 |
| 3 | `LuckyPennySoftware/MediatR` | 91 | Humanizer, Serilog, Polly, FluentValidation | 487 |
| 4 | `App-vNext/Polly` | 34 | Humanizer, Serilog, MediatR, FluentValidation | 544 |
| 5 | `FluentValidation/FluentValidation` | 28 | Humanizer, Serilog, MediatR, Polly | 550 |

---

## 3. Historical Baseline Results (5-Fold `GroupKFold`, Pre-Optimization)

In the initial baseline experiment (`experiment_results.json`, `scikit-learn 1.6.1`), nine configurations across Random Forest, Decision Tree, and Logistic Regression were evaluated on Dataset #2 at $\tau = 0.50$:

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

### Historical Baseline Accuracy and Holdout Summary (`rf_compact_regularized`)

| Evaluation | Threshold | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | Confusion Matrix [TN, FP, FN, TP] |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 5-Fold CV Fold Mean | 0.50 | 67.34% ± 4.91% | 68.24% ± 12.02% | 74.03% ± 15.57% | 0.6859 ± 0.0247 | 0.7025 | 0.6401 | 0.2144 | — |
| Pooled OOF (Nominal) | 0.50 | 67.13% | 63.86% | 73.48% | 0.6833 | 0.7025 | 0.6401 | 0.2144 | `[183, 116, 74, 205]` |
| Pooled OOF (Unnested $\tau^*$) | 0.40 | 70.42% | 64.21% | 87.46% | 0.7405 | 0.7025 | 0.6401 | 0.2144 | `[163, 136, 35, 244]` |
| `Newtonsoft.Json` Holdout ($N=159$) | 0.50 | 74.21% | 69.79% | 84.81% | 0.7657 | 0.8209 | 0.7917 | 0.1713 | `[51, 29, 12, 67]` |
| `Newtonsoft.Json` Holdout ($N=159$) | 0.40 | 75.47% | 69.61% | 89.87% | 0.7845 | 0.8209 | 0.7917 | 0.1713 | `[49, 31, 8, 71]` |

These `Newtonsoft.Json` results apply exclusively to the historical baseline model (`rf_compact_regularized`). `Newtonsoft.Json` was not used during the subsequent nested optimization study.

---

## 4. Nested Repository-Level Model Optimization Results ($5 \times 4$ `GroupKFold`)

To eliminate unnested threshold- and model-selection optimism, 20 configurations across six classifier families (Random Forest, Extra Trees, HistGradientBoosting, Gradient Boosting, Logistic Regression, and sigmoid-calibrated Random Forest via `CalibratedClassifierCV`) and four in-fold feature sets (`all_26`, `corr_pruned_085`, `inner_perm_top12`, `theoretical_core10`) were evaluated on Dataset #2 (`3_TestResults/ModelOptimization/nested_cv_results.csv`, `scikit-learn 1.9.1`).

### 4.1 Baseline vs. Optimized Model Configurations

| Parameter | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_nested_opt_v3_depth6_leaf8_log2`) | Optimized Extra Trees (`et_nested_opt_v3_depth6_leaf6_log2`) |
| :--- | ---: | ---: | ---: |
| Estimator | `RandomForestClassifier` | `RandomForestClassifier` | `ExtraTreesClassifier` |
| Feature Set | `all_26` | `all_26` | `all_26` |
| `n_estimators` | 100 | 200 | 200 |
| `max_depth` | 8 | 6 | 6 |
| `min_samples_split` | 5 | 10 | 8 |
| `min_samples_leaf` | 4 | 8 | 6 |
| `max_features` | `sqrt` | `log2` | `log2` |
| `class_weight` | `balanced` | `balanced` | `balanced` |
| `random_state` | 42 | 42 | 42 |

### 4.2 Nested Cross-Validation Comparison (`model_comparison.csv`)

| Configuration ID | Family | Outer ROC-AUC (Mean ± Std) | Outer PR-AUC (Mean ± Std) | Outer Brier (Mean ± Std) | Outer F1 $\tau=0.50$ (Mean ± Std) | Nested $\tau_{\text{inner}}^*$ F1 (Mean ± Std) | Pooled OOF ROC-AUC | Pooled OOF F1 ($\tau_{\text{inner}}^*$) | Pooled OOF Recall ($\tau_{\text{inner}}^*$) | Pooled OOF Precision ($\tau_{\text{inner}}^*$) | Pooled OOF Accuracy ($\tau_{\text{inner}}^*$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `et_depth6_leaf6_log2_bal` | Extra Trees | 0.7349 ± 0.0703 | 0.6443 ± 0.0496 | 0.2062 ± 0.0213 | 0.6867 ± 0.1394 | 0.7667 ± 0.0723 | 0.7470 | 0.7653 | 91.76% | 65.64% | 72.84% |
| `et_depth8_leaf4_sqrt_bal` | Extra Trees | 0.7349 ± 0.0801 | 0.6557 ± 0.0557 | 0.2056 ± 0.0260 | 0.6622 ± 0.1326 | 0.7324 ± 0.0492 | 0.7322 | 0.7492 | 88.89% | 64.75% | 71.28% |
| `rf_compact_corr_pruned` | Random Forest (FS) | 0.7315 ± 0.1142 | 0.6595 ± 0.1103 | 0.2096 ± 0.0280 | 0.6977 ± 0.0241 | 0.7302 ± 0.0533 | 0.7219 | 0.7262 | 90.32% | 60.72% | 67.13% |
| `rf_depth6_leaf8_log2_bal` | Random Forest | 0.7216 ± 0.1156 | 0.6465 ± 0.1026 | 0.2055 ± 0.0374 | 0.7517 ± 0.0709 | 0.7539 ± 0.0706 | 0.7119 | 0.7406 | 88.53% | 63.66% | 70.07% |
| `lr_c01_robust_bal` | Logistic Regression | 0.7146 ± 0.0973 | 0.6495 ± 0.0828 | 0.2345 ± 0.0334 | 0.5722 ± 0.1064 | 0.7316 ± 0.0677 | 0.7350 | 0.7304 | 91.76% | 60.66% | 67.30% |
| `rf_compact_calibrated_sigmoid` | Calibrated RF | 0.7060 ± 0.1219 | 0.6215 ± 0.1056 | 0.2180 ± 0.0334 | 0.6832 ± 0.0630 | 0.7363 ± 0.0679 | 0.6916 | 0.7347 | 90.32% | 61.92% | 68.51% |
| `rf_compact_regularized_baseline` | Baseline RF | 0.7037 ± 0.1292 | 0.6405 ± 0.1135 | 0.2146 ± 0.0398 | 0.6879 ± 0.0243 | 0.7408 ± 0.0760 | 0.7034 | 0.7294 | 88.89% | 61.85% | 68.17% |
| `hgb_lr003_depth3_leaf25_l2_5` | HistGradientBoosting | 0.6937 ± 0.1532 | 0.6363 ± 0.1143 | 0.2177 ± 0.0477 | 0.6862 ± 0.0676 | 0.7383 ± 0.0800 | 0.6883 | 0.7158 | 87.10% | 60.75% | 66.61% |
| `gb_lr003_depth2_leaf12_sub08` | Gradient Boosting | 0.6899 ± 0.1503 | 0.6398 ± 0.1149 | 0.2159 ± 0.0377 | 0.7102 ± 0.0605 | 0.7439 ± 0.0844 | 0.6925 | 0.7398 | 90.68% | 62.47% | 69.20% |

### 4.3 Per-Repository Outer-Fold Results (`per_repository_results.csv`)

| Held-Out Repository ($N$) | Metric | Baseline RF (`rf_compact_regularized`) | Optimized RF (`rf_depth6_leaf8_log2_bal`) | Optimized Extra Trees (`et_depth6_leaf6_log2_bal`) |
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

## 5. Threshold Analysis, Probability Calibration, and Deployment Configuration

### 5.1 Threshold Sweep vs. Nested Threshold Selection (`threshold_analysis.csv`)

ROC-AUC, PR-AUC, and Brier score measure probability ranking and probabilistic prediction error and remain unchanged across decision thresholds $\tau$. Threshold changes modify only classification metrics:

| Configuration | Threshold Mode | Threshold | Accuracy | Precision | Recall | F1 | F2 | Confusion Matrix [TN, FP, FN, TP] |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :---: |
| `rf_compact_regularized_baseline` | Nominal Fixed | 0.50 | 67.47% | 64.09% | 74.19% | 0.6877 | 0.7192 | `[183, 116, 72, 207]` |
| `rf_compact_regularized_baseline` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.4, 0.25, 0.3, 0.35]` | 68.17% | 61.85% | 88.89% | 0.7294 | 0.8174 | `[146, 153, 31, 248]` |
| `rf_depth6_leaf8_log2_bal` | Nominal Fixed | 0.50 | 71.28% | 66.77% | 80.65% | 0.7305 | 0.7743 | `[187, 112, 54, 225]` |
| `rf_depth6_leaf8_log2_bal` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.35, 0.3, 0.35, 0.4]` | 70.07% | 63.66% | 88.53% | 0.7406 | 0.8211 | `[158, 141, 32, 247]` |
| `et_depth6_leaf6_log2_bal` | Nominal Fixed | 0.50 | 73.18% | 70.00% | 77.78% | 0.7368 | 0.7609 | `[206, 93, 62, 217]` |
| `et_depth6_leaf6_log2_bal` | Fixed Modal Threshold | 0.40 | 73.01% | 65.81% | 91.76% | 0.7665 | 0.8505 | `[166, 133, 23, 256]` |
| `et_depth6_leaf6_log2_bal` | Nested Per-Fold $\tau_{\text{inner}}^*$ | `[0.4, 0.4, 0.4, 0.35, 0.4]` | 72.84% | 65.64% | 91.76% | 0.7653 | 0.8499 | `[165, 134, 23, 256]` |

### 5.2 Probability Calibration vs. Brier Score
- Brier score measures mean squared probabilistic prediction error; reporting a Brier score does not establish that a classifier is calibrated.
- Post-hoc sigmoid calibration via `CalibratedClassifierCV` (`rf_compact_calibrated_sigmoid`) increased outer Brier error to `0.2180 ± 0.0334` compared to uncalibrated `rf_compact_regularized` (`0.2146 ± 0.0398`). Stronger structural regularization (`rf_depth6_leaf8_log2_bal`: `0.2055 ± 0.0374`; `et_depth6_leaf6_log2_bal`: `0.2062 ± 0.0213`) lowered Brier error without post-hoc calibration.

### 5.3 Deployed Model Artifacts and Inference Thresholds

| Artifact File (`4_AppBuild/Assets/Models/`) | Estimator | Training Observations | UI Selector Order | Live `predicted_label` Threshold (`BugPredictor`) | Live `risk_category` Ceilings (`PredictionSettings`) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `et_nested_opt_v3_depth6_leaf6_log2.joblib` | `ExtraTreesClassifier` | Dataset #2 ($N=578$) | 1 (Default) | $\tau = 0.50$ (`model.predict()`) | Low $\le 0.30$, Medium $0.31\text{--}0.60$, High $> 0.60$ |
| `rf_nested_opt_v3_depth6_leaf8_log2.joblib` | `RandomForestClassifier` | Dataset #2 ($N=578$) | 2 | $\tau = 0.50$ (`model.predict()`) | Low $\le 0.30$, Medium $0.31\text{--}0.60$, High $> 0.60$ |
| `exp_final_5fold_v2_best_rf_compact_regularized.joblib` | `RandomForestClassifier` | Dataset #2 ($N=578$) | 3 (Preserved Baseline) | $\tau = 0.50$ (`model.predict()`) | Low $\le 0.30$, Medium $0.31\text{--}0.60$, High $> 0.60$ |
| `rf_csharp_empirical_model.joblib` | `RandomForestClassifier` | Dataset #1 ($N=382$ train) | 4 (Preserved v1) | $\tau = 0.50$ (`model.predict()`) | Low $\le 0.30$, Medium $0.31\text{--}0.60$, High $> 0.60$ |
