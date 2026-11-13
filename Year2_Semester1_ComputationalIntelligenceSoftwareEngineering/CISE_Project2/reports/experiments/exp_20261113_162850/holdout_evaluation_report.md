# Independent Holdout Evaluation Report: exp_20261113_162850

**Model ID:** `rf_compact_regularized`  
**Generated:** 2026-11-13 16:28:59 UTC  

## Performance on Unseen Holdout Repository

| Metric | Value |
| :--- | :--- |
| Accuracy | 0.5545 |
| Precision | 0.4932 |
| Recall | 0.8182 |
| F1-Score | 0.6154 |
| ROC-AUC | 0.6252 |
| Average Precision (PR-AUC) | 0.5088 |
| Confusion Matrix | `[[20, 37], [8, 36]]` |

## Distinction Between Cross-Validation and Holdout Evaluation
Cross-validation was conducted exclusively within the training partition to select the optimal hyperparameter 
configuration. The holdout dataset was never observed during training, feature pruning, median calculation, 
or model selection. This confirms the model's true out-of-domain generalization capacity.
