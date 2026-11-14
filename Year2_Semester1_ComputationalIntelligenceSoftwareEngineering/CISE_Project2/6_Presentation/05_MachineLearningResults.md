# 05 — Machine Learning Models & Experimental Results

---

## 1. The 11-Classifier Comparison Benchmark

Eleven candidate machine-learning classifiers were evaluated using 5-fold `GroupKFold` cross-validation partitioned strictly by repository:

| Model Classifier | Accuracy | Precision | Recall | F1 Score | ROC-AUC | MCC | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest (Champion)** | **67.13%** | **64.06%** | **73.48%** | **0.6845** | **0.7208** | **+0.3478** | **0.2079** |
| Extra Trees | 65.57% | 63.02% | 70.25% | 0.6644 | 0.7061 | +0.3142 | 0.2185 |
| Gradient Boosting (sklearn) | 65.40% | 63.64% | 66.31% | 0.6495 | 0.6970 | +0.3090 | 0.2223 |
| LightGBM | 64.71% | 62.77% | 66.67% | 0.6466 | 0.7001 | +0.2954 | 0.2255 |
| CatBoost | 65.05% | 63.67% | 65.23% | 0.6444 | 0.7018 | +0.3018 | 0.2212 |
| XGBoost | 64.01% | 62.33% | 65.23% | 0.6375 | 0.6957 | +0.2810 | 0.2319 |
| Logistic Regression (L2) | 63.15% | 62.90% | 58.78% | 0.6078 | 0.6728 | +0.2625 | 0.2304 |
| Multi-Layer Perceptron (MLP)| 61.94% | 60.57% | 60.93% | 0.6075 | 0.6582 | +0.2386 | 0.2380 |
| Support Vector Machine (RBF) | 61.59% | 60.91% | 57.71% | 0.5926 | 0.6541 | +0.2309 | 0.2401 |
| Decision Tree (CART) | 59.52% | 58.05% | 58.78% | 0.5841 | 0.5950 | +0.1899 | 0.4048 |
| Gaussian Naive Bayes | 53.63% | 51.68% | 74.55% | 0.6105 | 0.6279 | +0.0934 | 0.3592 |

---

## 2. Accuracy Figure Reconciliation

In the final 5-fold cross-validation experiment, three distinct accuracy metrics are reported depending on the mathematical framing:

| Metric Type | Value | Formula / Basis | Interpretation |
| :--- | :---: | :--- | :--- |
| **5-Fold CV Fold Mean** | **$67.34\% \pm 4.91\%$** | $\frac{1}{5} \sum_{k=1}^5 \text{Acc}_k$ | Unweighted average across the 5 repository folds ($70.45, 58.96, 65.93, 73.53, 67.86$) |
| **Pooled Nominal Out-of-Fold** | **$67.13\%$** | $\frac{388}{578}$ ($\tau = 0.50$) | Overall accuracy on pooled predictions at default 0.50 threshold ($TN=183, FP=116, FN=74, TP=205$) |
| **Pooled Tuned Out-of-Fold** | **$70.42\%$** | $\frac{407}{578}$ ($\tau^* = 0.40$) | Optimal operating point balancing precision ($64.21\%$) and high defect recall ($87.46\%$, F1 $0.7405$) |

---

## 3. Independent Holdout Evaluation (`Newtonsoft.Json`)

To test true out-of-sample generalization, the champion model was evaluated against an untouched holdout codebase (159 observations: 79 defect-prone, 80 candidate-clean):

| Quadrant | Prediction Outcome | Observations | Proportion |
| :--- | :--- | :---: | :---: |
| **True Positive (TP)** | Correctly Intercepted Defect | 71 | 44.65% |
| **True Negative (TN)** | Correctly Identified Candidate-Clean | 49 | 30.82% |
| **False Positive (FP)** | False Alarm (Candidate-Clean Flagged) | 31 | 19.50% |
| **False Negative (FN)** | Missed Defect | 8 | 5.03% |
| **Total** | Independent Holdout Corpus | **159** | **100.0%** |

- **Defect Recall:** **$89.87\%$** ($71 / 79$ defects captured)
- **Specificity:** **$61.25\%$** ($49 / 80$ candidate-clean methods passed)
- **Holdout Accuracy:** **$75.47\%$** ($120 / 159$)
- **Holdout F1 Score:** **$0.7845$**
- **Holdout ROC-AUC:** **$0.7958$**

---

## 4. Top Feature Importances (Gini Impurity)

Which code characteristics predict defects most strongly?

| Rank | Feature Name | Importance | Interpretation |
| :---: | :--- | :---: | :--- |
| 1 | `method_length` | **20.5%** | Total character span of the method declaration |
| 2 | `parameter_count` | **12.5%** | Number of inputs passed into the method |
| 3 | `loc` | **12.4%** | Physical lines of code |
| 4 | `method_call_count` | **8.7%** | Number of external and internal method invocations |
| 5 | `statement_count` | **6.2%** | Number of executable statements |
| 6 | `property_access_count` | **5.4%** | Density of property getters/setters |
| 7 | `logical_loc` | **4.9%** | Executable lines of code |
| 8 | `cyclomatic_complexity` | **3.8%** | McCabe control-flow branches ($M = \pi + 1$) |

