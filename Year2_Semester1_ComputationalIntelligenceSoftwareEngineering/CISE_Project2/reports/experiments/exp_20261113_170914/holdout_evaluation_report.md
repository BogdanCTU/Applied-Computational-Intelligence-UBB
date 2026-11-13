# Independent Holdout Evaluation Report: exp_20261113_170914

**Selected Model:** `rf_feature_constrained_log2` (random_forest)  
**Generated:** 2026-11-13 17:09:20 UTC  

## Performance on Unseen Holdout Repository (`commandlineparser/commandline`)

| Metric | Standard Threshold (0.50) | CV-Optimized Threshold (0.30) |
| :--- | :--- | :--- |
| Accuracy | 0.5149 | 0.5149 |
| Precision | 0.4658 | 0.4719 |
| Recall | 0.7727 | 0.9545 |
| F1-Score | 0.5812 | 0.6316 |
| ROC-AUC | 0.6041 | N/A |
| PR-AUC | 0.5252 | N/A |
| Brier Score | 0.2627 | N/A |
| Confusion Matrix | `[[18, 39], [10, 34]]` | `[[10, 47], [2, 42]]` |

## Methodological Distinction Between Cross-Validation and Holdout Evaluation
Cross-validation was conducted exclusively within the training partition to select the optimal model 
family, hyperparameters, and decision threshold. The holdout dataset was never observed during training, 
feature pruning, imputation fitting, or threshold selection, confirming true out-of-domain generalization capacity.
