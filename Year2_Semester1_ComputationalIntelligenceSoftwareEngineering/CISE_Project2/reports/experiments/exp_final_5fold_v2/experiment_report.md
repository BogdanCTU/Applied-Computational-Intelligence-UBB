# Multi-Model Defect Prediction Experiment Report: exp_final_5fold_v2

**Generated:** 2026-11-14 11:58:21 UTC  
**Dataset Snapshot:** `csharp_empirical_v2_v2.0.0`  
**Execution Duration:** 11.18s  
**Selection Metric:** `f1`  
**Cross-Validation Strategy:** 5-fold GroupKFold by `repository_id`  

---

## 1. Experiment Objective & Protocol

This experiment evaluates multiple classification model families on method-level software defect prediction using static code metrics. Evaluated model families include **Dummy baselines** (most frequent and stratified), **Logistic Regression** (linear baseline with in-fold standard scaling), **Decision Tree** (interpretable tree baseline), and **Random Forest** (non-linear ensemble).

### Leakage Prevention Guarantees
1. **Repository-Aware Partitioning:** Zero overlap between training and validation repositories within any fold.
2. **Independent Preprocessing:** Median imputation, zero-variance pruning, and feature scaling (`StandardScaler`) are fitted strictly on the training partition of each fold and applied to the validation partition without leakage.
3. **Holdout Isolation:** The holdout repository was strictly isolated from training, preprocessing, hyperparameter search, and decision threshold selection.

### Repository Grouping Feasibility
- **Available Training Repositories:** 5
- **Required Repositories for 5-fold GroupKFold:** 5
- **Readiness Status:** [PASS] Sufficient Repositories
- **Diagnostic Note:** Dataset has 5 distinct repositories, which satisfies the 5-fold GroupKFold requirement.

---

## 2. Multi-Model Benchmark & Cross-Validation Results

| Rank | Configuration ID | Algorithm | Hyperparameters | Mean F1 | F1 Std | Mean ROC-AUC | Mean AP | Mean Brier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | `rf_compact_regularized` | `random_forest` | trees=100, depth=8, leaf=4, feat=sqrt | **0.6859** | $\pm 0.0247$ | 0.7025 | 0.6401 | 0.2144 |
| **#2** | `rf_feature_constrained_log2` | `random_forest` | trees=200, depth=10, leaf=2, feat=log2 | **0.6385** | $\pm 0.0641$ | 0.6909 | 0.6255 | 0.2209 |
| **#3** | `rf_heavy_bagging_300` | `random_forest` | trees=300, depth=15, leaf=2, feat=sqrt | **0.6262** | $\pm 0.0633$ | 0.6731 | 0.5951 | 0.2265 |
| **#4** | `rf_baseline_balanced` | `random_forest` | trees=100, depth=10, leaf=2, feat=sqrt | **0.6108** | $\pm 0.1176$ | 0.6802 | 0.6101 | 0.2249 |
| **#5** | `dt_shallow_depth4` | `decision_tree` | depth=4, leaf=4, weight=balanced | **0.5734** | $\pm 0.2172$ | 0.6376 | 0.6156 | 0.2807 |
| **#6** | `rf_deep_capacity` | `random_forest` | trees=200, depth=15, leaf=1, feat=sqrt | **0.5577** | $\pm 0.0739$ | 0.6477 | 0.5834 | 0.2429 |
| **#7** | `lr_balanced_c1` | `logistic_regression` | C=1.0, weight=balanced | **0.4989** | $\pm 0.1252$ | 0.6834 | 0.6235 | 0.2620 |
| **#8** | `dummy_stratified` | `dummy` | strategy=stratified | **0.4919** | $\pm 0.0821$ | 0.5266 | 0.5118 | 0.4726 |
| **#9** | `lr_standard_c1` | `logistic_regression` | C=1.0, weight=None | **0.4890** | $\pm 0.1409$ | 0.6827 | 0.6231 | 0.2643 |
| **#10** | `dt_depth8` | `decision_tree` | depth=8, leaf=2, weight=balanced | **0.4695** | $\pm 0.2194$ | 0.5656 | 0.5761 | 0.3993 |
| **#11** | `dummy_most_frequent` | `dummy` | strategy=most_frequent | **0.0000** | $\pm 0.0000$ | 0.5000 | 0.4885 | 0.4885 |

---

## 3. Best Model Selection & Baseline Lift

- **Selected Model:** `rf_compact_regularized` (Rank #1)
- **Algorithm:** `random_forest`
- **Cross-Validation F1:** **0.6859**
- **Saved Model Artifact:** `exp_final_5fold_v2_best_rf_compact_regularized.joblib`

### Baseline Comparison (DummyClassifier)
- **Dummy (Most Frequent) Cross-Validation F1:** `0.0000`
- **Lift over Majority Guessing:** The selected model achieves **+0.6859** F1 points over `DummyClassifier(strategy='most_frequent')`.

### Comparative Model Family Breakdown
- **Best DECISION_TREE:** `dt_shallow_depth4` — F1: `0.5734`, ROC-AUC: `0.6376`, Brier: `0.2807`
- **Best DUMMY:** `dummy_stratified` — F1: `0.4919`, ROC-AUC: `0.5266`, Brier: `0.4726`
- **Best LOGISTIC_REGRESSION:** `lr_balanced_c1` — F1: `0.4989`, ROC-AUC: `0.6834`, Brier: `0.2620`
- **Best RANDOM_FOREST:** `rf_compact_regularized` — F1: `0.6859`, ROC-AUC: `0.7025`, Brier: `0.2144`

---

## 4. Fold-Level Performance & Stability Analysis

| Fold | Train Repos | Val Repos | Train (Buggy / Clean) | Val (Buggy / Clean) | Confusion Matrix [TN, FP, FN, TP] | F1 | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 4 | 1 | 140 / 147 | 139 / 152 | `[115, 37, 49, 90]` | **0.6767** | 0.7972 | 0.1843 |
| Fold 2 | 4 | 1 | 213 / 231 | 66 / 68 | `[15, 53, 2, 64]` | **0.6995** | 0.5865 | 0.2702 |
| Fold 3 | 4 | 1 | 236 / 251 | 43 / 48 | `[30, 18, 13, 30]` | **0.6593** | 0.6781 | 0.2210 |
| Fold 4 | 4 | 1 | 262 / 282 | 17 / 17 | `[16, 1, 8, 9]` | **0.6667** | 0.8997 | 0.1579 |
| Fold 5 | 4 | 1 | 265 / 285 | 14 / 14 | `[7, 7, 2, 12]` | **0.7273** | 0.5510 | 0.2384 |

---

## 5. Decision Threshold Optimization (Out-of-Fold Cross-Validation)

Decision threshold was swept strictly across out-of-fold validation predictions to analyze precision-recall trade-offs without holdout data leakage:

| Threshold | Accuracy | Precision | Recall | F1-Score | True Negatives | False Positives | False Negatives | True Positives |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0.20 | 0.6609 | 0.5928 | 0.9498 | 0.7300 | 117 | 182 | 14 | 265 |
| 0.30 | 0.6834 | 0.6143 | 0.9247 | 0.7382 | 137 | 162 | 21 | 258 |
| **0.40** | 0.7042 | 0.6421 | 0.8746 | **0.7405** | 163 | 136 | 35 | 244 |
| 0.45 | 0.7076 | 0.6528 | 0.8423 | 0.7355 | 174 | 125 | 44 | 235 |
| 0.50 | 0.6713 | 0.6386 | 0.7348 | 0.6833 | 183 | 116 | 74 | 205 |
| 0.55 | 0.6540 | 0.6367 | 0.6595 | 0.6479 | 194 | 105 | 95 | 184 |
| 0.60 | 0.6453 | 0.6516 | 0.5699 | 0.6080 | 214 | 85 | 120 | 159 |
| 0.70 | 0.5502 | 0.5655 | 0.2939 | 0.3868 | 236 | 63 | 197 | 82 |
| 0.80 | 0.5173 | 0.5000 | 0.0538 | 0.0971 | 284 | 15 | 264 | 15 |

> **Optimal CV Decision Threshold:** `0.40` (F1 = 0.7405)

---

## 7. Methodological Limitations & Future Work

1. **Corpus Size for 5-Fold GroupKFold:** Running full 5-fold cross-validation requires at least 5 distinct training repositories. With the current dataset of 2 training repositories, cross-validation evaluates across $K=2$ folds.
2. **Open-World Assumption on Candidate Clean Labels:** Methods without bug-fix blame traces are candidate clean; unreported latent bugs may introduce label noise.
3. **Artificial Balance:** Experimental balance (~47% buggy) improves tree split stability but does not reflect industrial defect prevalence (5%–15%).
4. **Threshold Generalization:** While threshold tuning on CV optimizes within-domain F1, domain shifts across unseen repositories may affect optimal operating points.
