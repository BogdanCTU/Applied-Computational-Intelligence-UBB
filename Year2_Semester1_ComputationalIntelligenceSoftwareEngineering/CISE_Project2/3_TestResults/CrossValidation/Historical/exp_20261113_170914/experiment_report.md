# Multi-Model Defect Prediction Experiment Report: exp_20261113_170914

**Generated:** 2026-11-13 17:09:20 UTC  
**Dataset Snapshot:** `csharp_empirical_v1_v1.0.0`  
**Execution Duration:** 6.67s  
**Selection Metric:** `f1`  
**Cross-Validation Strategy:** 2-fold GroupKFold by `repository_id`  

---

## 1. Experiment Objective & Protocol

This experiment evaluates multiple classification model families on method-level software defect prediction using static code metrics. Evaluated model families include **Dummy baselines** (most frequent and stratified), **Logistic Regression** (linear baseline with in-fold standard scaling), **Decision Tree** (interpretable tree baseline), and **Random Forest** (non-linear ensemble).

### Leakage Prevention Guarantees
1. **Repository-Aware Partitioning:** Zero overlap between training and validation repositories within any fold.
2. **Independent Preprocessing:** Median imputation, zero-variance pruning, and feature scaling (`StandardScaler`) are fitted strictly on the training partition of each fold and applied to the validation partition without leakage.
3. **Holdout Isolation:** The holdout repository was strictly isolated from training, preprocessing, hyperparameter search, and decision threshold selection.

### Repository Grouping Feasibility
- **Available Training Repositories:** 2
- **Required Repositories for 2-fold GroupKFold:** 2
- **Readiness Status:** [PASS] Sufficient Repositories
- **Diagnostic Note:** Dataset has 2 distinct repositories, which satisfies the 2-fold GroupKFold requirement.

---

## 2. Multi-Model Benchmark & Cross-Validation Results

| Rank | Configuration ID | Algorithm | Hyperparameters | Mean F1 | F1 Std | Mean ROC-AUC | Mean AP | Mean Brier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | `rf_feature_constrained_log2` | `random_forest` | trees=200, depth=10, leaf=2, feat=log2 | **0.6801** | $\pm 0.0908$ | 0.6525 | 0.5875 | 0.2317 |
| **#2** | `rf_baseline_balanced` | `random_forest` | trees=100, depth=10, leaf=2, feat=sqrt | **0.6768** | $\pm 0.0896$ | 0.6349 | 0.5664 | 0.2336 |
| **#3** | `rf_heavy_bagging_300` | `random_forest` | trees=300, depth=15, leaf=2, feat=sqrt | **0.6729** | $\pm 0.0935$ | 0.6386 | 0.5726 | 0.2343 |
| **#4** | `rf_compact_regularized` | `random_forest` | trees=100, depth=8, leaf=4, feat=sqrt | **0.6721** | $\pm 0.0932$ | 0.6970 | 0.6210 | 0.2182 |
| **#5** | `dt_depth8` | `decision_tree` | depth=8, leaf=2, weight=balanced | **0.6388** | $\pm 0.1272$ | 0.6430 | 0.5859 | 0.3423 |
| **#6** | `rf_deep_capacity` | `random_forest` | trees=200, depth=15, leaf=1, feat=sqrt | **0.6381** | $\pm 0.0773$ | 0.6107 | 0.5520 | 0.2484 |
| **#7** | `lr_balanced_c1` | `logistic_regression` | C=1.0, weight=balanced | **0.6362** | $\pm 0.0097$ | 0.6858 | 0.6493 | 0.2884 |
| **#8** | `lr_standard_c1` | `logistic_regression` | C=1.0, weight=None | **0.6187** | $\pm 0.0017$ | 0.6862 | 0.6495 | 0.2877 |
| **#9** | `dt_shallow_depth4` | `decision_tree` | depth=4, leaf=4, weight=balanced | **0.6102** | $\pm 0.1352$ | 0.6769 | 0.6306 | 0.3025 |
| **#10** | `dummy_stratified` | `dummy` | strategy=stratified | **0.4170** | $\pm 0.0074$ | 0.4536 | 0.4544 | 0.5441 |
| **#11** | `dummy_most_frequent` | `dummy` | strategy=most_frequent | **0.0000** | $\pm 0.0000$ | 0.5000 | 0.4751 | 0.4751 |

---

## 3. Best Model Selection & Baseline Lift

- **Selected Model:** `rf_feature_constrained_log2` (Rank #1)
- **Algorithm:** `random_forest`
- **Cross-Validation F1:** **0.6801**
- **Saved Model Artifact:** `exp_20261113_170914_best_rf_feature_constrained_log2.joblib`

### Baseline Comparison (DummyClassifier)
- **Dummy (Most Frequent) Cross-Validation F1:** `0.0000`
- **Lift over Majority Guessing:** The selected model achieves **+0.6801** F1 points over `DummyClassifier(strategy='most_frequent')`.

### Comparative Model Family Breakdown
- **Best DECISION_TREE:** `dt_depth8` — F1: `0.6388`, ROC-AUC: `0.6430`, Brier: `0.3423`
- **Best DUMMY:** `dummy_stratified` — F1: `0.4170`, ROC-AUC: `0.4536`, Brier: `0.5441`
- **Best LOGISTIC_REGRESSION:** `lr_balanced_c1` — F1: `0.6362`, ROC-AUC: `0.6858`, Brier: `0.2884`
- **Best RANDOM_FOREST:** `rf_feature_constrained_log2` — F1: `0.6801`, ROC-AUC: `0.6525`, Brier: `0.2317`

---

## 4. Fold-Level Performance & Stability Analysis

| Fold | Train Repos | Val Repos | Train (Buggy / Clean) | Val (Buggy / Clean) | Confusion Matrix [TN, FP, FN, TP] | F1 | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 1 | 1 | 43 / 48 | 139 / 152 | `[122, 30, 33, 106]` | **0.7709** | 0.8200 | 0.1730 |
| Fold 2 | 1 | 1 | 139 / 152 | 43 / 48 | `[12, 36, 10, 33]` | **0.5893** | 0.4850 | 0.2904 |

---

## 5. Decision Threshold Optimization (Out-of-Fold Cross-Validation)

Decision threshold was swept strictly across out-of-fold validation predictions to analyze precision-recall trade-offs without holdout data leakage:

| Threshold | Accuracy | Precision | Recall | F1-Score | False Positives | True Positives |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0.20 | 0.6911 | 0.6143 | 0.9451 | 0.7446 | 108 | 172 |
| **0.30** | 0.7068 | 0.6287 | 0.9396 | **0.7533** | 101 | 171 |
| 0.40 | 0.7094 | 0.6449 | 0.8681 | 0.7400 | 87 | 158 |
| 0.45 | 0.7199 | 0.6652 | 0.8297 | 0.7384 | 76 | 151 |
| 0.50 | 0.7147 | 0.6780 | 0.7637 | 0.7183 | 66 | 139 |
| 0.55 | 0.6623 | 0.6532 | 0.6209 | 0.6366 | 60 | 113 |
| 0.60 | 0.6178 | 0.6268 | 0.4890 | 0.5494 | 53 | 89 |
| 0.70 | 0.5524 | 0.6078 | 0.1703 | 0.2661 | 20 | 31 |
| 0.80 | 0.5052 | 0.2308 | 0.0165 | 0.0308 | 10 | 3 |

> **Optimal CV Decision Threshold:** `0.30` (F1 = 0.7533)

---

## 6. Independent Repository Holdout Evaluation

> [!IMPORTANT]
> The holdout repository (`commandlineparser/commandline`) was strictly isolated from hyperparameter exploration, > model selection, and threshold tuning. These metrics evaluate true out-of-domain transferability.

- **Holdout Repositories:** `['1']`
- **Holdout Methods Evaluated:** 101

### Performance at Standard Decision Threshold (0.50)
- **Accuracy:** **0.5149**
- **Precision:** **0.4658**
- **Recall:** **0.7727**
- **F1-Score:** **0.5812**
- **ROC-AUC:** **0.6041**
- **Average Precision (PR-AUC):** **0.5252**
- **Brier Score (Probability Calibration):** **0.2627**
- **Confusion Matrix [TN, FP, FN, TP]:** `[[18, 39], [10, 34]]`

### Transfer of CV-Optimized Threshold (0.30)
- **Holdout Accuracy:** `0.5149`
- **Holdout Precision:** `0.4719`
- **Holdout Recall:** `0.9545`
- **Holdout F1-Score:** `0.6316`
- **Confusion Matrix:** `[[10, 47], [2, 42]]`

---

## 7. Methodological Limitations & Future Work

1. **Corpus Size for 5-Fold GroupKFold:** Running full 5-fold cross-validation requires at least 5 distinct training repositories. With the current dataset of 2 training repositories, cross-validation evaluates across $K=2$ folds.
2. **Open-World Assumption on Candidate Clean Labels:** Methods without bug-fix blame traces are candidate clean; unreported latent bugs may introduce label noise.
3. **Artificial Balance:** Experimental balance (~47% buggy) improves tree split stability but does not reflect industrial defect prevalence (5%–15%).
4. **Threshold Generalization:** While threshold tuning on CV optimizes within-domain F1, domain shifts across unseen repositories may affect optimal operating points.
