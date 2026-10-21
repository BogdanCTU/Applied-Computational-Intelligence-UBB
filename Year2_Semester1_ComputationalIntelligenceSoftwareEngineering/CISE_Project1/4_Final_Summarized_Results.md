# Empirical Evaluation Results: Bayesian Networks vs. Rule-Based Classification

## 1. Dataset Overview

- **Source:** [UCI Bank Marketing Dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing)
- **Total records:** 45,211
- **Target:** Term deposit subscription (`y`)
  - `yes`: 5,289 (11.7%)
  - `no`: 39,922 (88.3%)
- **Input features:** 15 categorical and numerical attributes.

---

## 2. Results

| Classifier | Evaluation Method | Accuracy | Precision | Recall | F1-Score | TP | FP | FN | TN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Rule-Based** (2 branches) | Full dataset | 88.60% | 52.18% | 31.03% | **0.3891** | 1,641 | 1,504 | 3,648 | 38,418 |
| **Bayesian Network** (T=0.50) | 5-Fold CV | **89.24%** | **62.00%** | 20.63% | 0.3091 | 1,091 | **666** | 4,198 | 39,256 |
| **Bayesian Network** (T=0.20) | 5-Fold CV | 86.18% | 41.37% | **42.90%** | **0.4209** | **2,269** | 3,230 | **3,020** | 36,692 |

### Bayesian Network: Cross-Validation Stability

| Threshold | Accuracy (Mean ± SD) | Precision (Mean ± SD) | Recall (Mean ± SD) | F1-Score (Mean ± SD) |
|---|---:|---:|---:|---:|
| **0.50** | 89.24% ± 0.19% | 62.00% ± 1.56% | 20.63% ± 2.47% | 30.91% ± 3.00% |
| **0.20** | 86.18% ± 0.77% | 41.37% ± 2.93% | 42.90% ± 1.57% | 42.09% ± 2.06% |

The relatively low standard deviations indicate consistent performance across the five folds.

---

## 3. Calculation Verification

The evaluation uses four standard classification metrics:

- **Accuracy** = `(TP + TN) / (TP + TN + FP + FN)`
- **Precision** = `TP / (TP + FP)`
- **Recall** = `TP / (TP + FN)`
- **F1-score** = `2 × Precision × Recall / (Precision + Recall)`

### 3.1 Rule-Based Classifier

Using `TP = 1641`, `FP = 1504`, `FN = 3648`, and `TN = 38418`:

- **Accuracy** = `(1641 + 38418) / 45211` = **88.60%**
- **Precision** = `1641 / (1641 + 1504)` = **52.18%**
- **Recall** = `1641 / (1641 + 3648)` = **31.03%**
- **F1-score** = `3282 / (3282 + 1504 + 3648)` = **0.3891**

### 3.2 Bayesian Network (`τ = 0.50`)

Using the pooled out-of-fold totals: `TP = 1091`, `FP = 666`, `FN = 4198`, and `TN = 39256`:

- **Accuracy** = `(1091 + 39256) / 45211` = **89.24%**
- **Precision** = `1091 / (1091 + 666)` = **62.09%**
- **Recall** = `1091 / (1091 + 4198)` = **20.63%**
- **F1-score** = `2182 / (2182 + 666 + 4198)` = **0.3097**

### 3.3 Bayesian Network (`τ = 0.20`)

Using the pooled out-of-fold totals: `TP = 2269`, `FP = 3230`, `FN = 3020`, and `TN = 36692`:

- **Accuracy** = `(2269 + 36692) / 45211` = **86.18%**
- **Precision** = `2269 / (2269 + 3230)` = **41.26%**
- **Recall** = `2269 / (2269 + 3020)` = **42.90%**
- **F1-score** = `4538 / (4538 + 3230 + 3020)` = **0.4207**

---

## 4. Final Conclusions

1. **Rule-Based Classifier:** Simple and interpretable, satisfying the two-branch constraint. It achieves an F1-score of **0.3891** on the full dataset.
2. **Bayesian Network (T=0.50):** Provides the highest cross-validation accuracy (**89.24%**) and precision (**62.00%**), with only 666 false positives, but misses many actual subscribers.
3. **Bayesian Network (T=0.20):** Achieves the highest cross-validation F1-score (**0.4209**) and recall (**42.90%**), identifying more subscribers at the cost of additional false positives.
