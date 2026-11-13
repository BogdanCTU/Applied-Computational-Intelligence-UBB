# Automated ML Experiment Report: exp_20261113_162850

**Generated:** 2026-11-13 16:28:59 UTC  
**Dataset Snapshot:** `csharp_empirical_v1`  
**Execution Duration:** 8.36s  
**Selection Metric:** `f1`  
**Cross-Validation Strategy:** 2-fold GroupKFold by `repository_id`  

---

## 1. Experiment Objective & Protocol

This experiment evaluates multiple Random Forest classification configurations on method-level software defect prediction using static code metrics. To eliminate cross-repository data leakage, evaluation is conducted via **2-fold GroupKFold cross-validation**, where code from the same repository never appears in both training and validation splits. Preprocessing (median imputation and zero-variance pruning) is fitted strictly within each training fold.

### Repository Grouping Feasibility
- **Available Training Repositories:** 2
- **Required Repositories for 2-fold GroupKFold:** 2
- **Readiness Status:** [PASS] Sufficient Repositories
- **Diagnostic Note:** Dataset has 2 distinct repositories, which satisfies the 2-fold GroupKFold requirement.

---

## 2. Hyperparameter Evaluation Matrix & Results

| Rank | Configuration ID | n_estimators | max_depth | min_samples_split | min_samples_leaf | max_features | class_weight | Mean F1 | F1 Std | Mean ROC-AUC | Mean AP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | `rf_compact_regularized` | 100 | 8 | 5 | 4 | `sqrt` | `balanced` | **0.7206** | $\pm 0.0595$ | 0.7052 | 0.6173 |
| **#2** | `rf_heavy_bagging_300` | 300 | 15 | 4 | 2 | `sqrt` | `balanced` | **0.6885** | $\pm 0.0830$ | 0.6581 | 0.5753 |
| **#3** | `rf_baseline_balanced` | 100 | 10 | 4 | 2 | `sqrt` | `balanced` | **0.6849** | $\pm 0.0794$ | 0.6288 | 0.5712 |
| **#4** | `rf_ultra_bagging_500` | 500 | 15 | 5 | 2 | `sqrt` | `balanced` | **0.6820** | $\pm 0.0894$ | 0.6735 | 0.5847 |
| **#5** | `rf_feature_constrained_log2` | 200 | 10 | 4 | 2 | `log2` | `balanced` | **0.6741** | $\pm 0.0946$ | 0.6954 | 0.5972 |
| **#6** | `rf_deep_capacity` | 200 | 15 | 2 | 1 | `sqrt` | `balanced` | **0.6683** | $\pm 0.0889$ | 0.5956 | 0.5360 |
| **#7** | `rf_unweighted_log2` | 200 | 12 | 5 | 2 | `log2` | `None` | **0.6666** | $\pm 0.0925$ | 0.6868 | 0.5953 |
| **#8** | `rf_unlimited_depth` | 300 | None | 5 | 2 | `sqrt` | `balanced` | **0.6607** | $\pm 0.1222$ | 0.6568 | 0.5722 |

---

## 3. Best Model Selection & Rationale

- **Selected Configuration:** `rf_compact_regularized` (Rank #1)
- **Cross-Validation F1:** **0.7206**
- **Hyperparameters:** `{"n_estimators": 100, "max_depth": 8, "min_samples_split": 5, "min_samples_leaf": 4, "max_features": "sqrt", "class_weight": "balanced", "random_state": 42, "n_jobs": -1}`
- **Saved Model Artifact:** `exp_20261113_162850_best_rf_compact_regularized.joblib`

### Baseline Comparison (DummyClassifier)
- **Dummy (Most Frequent) Cross-Validation F1:** `0.0000`
- **Dummy (Most Frequent) Cross-Validation Accuracy:** `0.5249`
- **Statistical Lift:** The selected Random Forest model outperforms majority-class guessing by +0.7206 F1 points.

---

## 4. Fold-Level Performance & Stability Analysis

| Fold | Train Repos | Val Repos | Train Obs | Val Obs | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 1 | 1 | 91 | 291 | 0.7869 | 0.7692 | 0.7914 | **0.7801** | 0.8260 |
| Fold 2 | 1 | 1 | 291 | 91 | 0.5495 | 0.5128 | 0.9302 | **0.6612** | 0.5843 |

---

## 5. Independent Repository Holdout Evaluation

> [!IMPORTANT]
> The holdout repository was strictly isolated from hyperparameter exploration, model selection, > and preprocessing fitting. These metrics reflect one-shot generalization to an unseen repository.

- **Holdout Repositories:** `['1']`
- **Holdout Methods Tested:** 101
- **Accuracy:** **0.5545**
- **Precision:** **0.4932**
- **Recall:** **0.8182**
- **F1-Score:** **0.6154**
- **ROC-AUC:** **0.6252**
- **Average Precision (PR-AUC):** **0.5088**
- **Confusion Matrix [TN, FP, FN, TP]:** `[[20, 37], [8, 36]]`

---

## 6. Methodological Limitations & Future Work

1. **Corpus Size for 5-Fold GroupKFold:** Running full 5-fold cross-validation requires at least 5 distinct training repositories. With the current dataset of 2 training repositories, cross-validation evaluates across $K=2$ folds.
2. **Open-World Assumption on Candidate Clean Labels:** Methods without bug-fix blame traces are candidate clean; unreported latent bugs may introduce label noise.
3. **Artificial Balance:** Experimental balance (~47% buggy) improves tree split stability but does not reflect industrial defect prevalence (5%–15%).
