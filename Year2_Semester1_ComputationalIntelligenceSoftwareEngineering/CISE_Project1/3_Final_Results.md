# Initial Tests


## First Test Set Results (Default $\tau = 0.50$)

| Classifier | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rule-Based Classifier** | **88.82%** | **53.74%** | **31.95%** | **0.4007** | 7,694 | 291 | 720 | **338** |
| **Bayesian Network ($\tau = 0.50$)** | **89.24%** | **63.00%** | **19.47%** | **0.2975** | **7,864** | **121** | 852 | 206 |

## Metric Clculation Verification

- **Rule-Based Classifier:**
  $$\text{Accuracy} = \frac{7694 + 338}{9043} = \frac{8032}{9043} = 88.8201\%$$
  $$\text{Precision} = \frac{338}{338 + 291} = \frac{338}{629} = 53.7361\%$$
  $$\text{Recall} = \frac{338}{338 + 720} = \frac{338}{1058} = 31.9471\%$$
  $$\text{F1-Score} = \frac{2 \cdot 0.537361 \cdot 0.319471}{0.537361 + 0.319471} = \frac{676}{1687} = \mathbf{0.400711}$$

- **Bayesian Network ($\tau = 0.50$):**
  $$\text{Accuracy} = \frac{7864 + 206}{9043} = \frac{8070}{9043} = 89.2403\%$$
  $$\text{Precision} = \frac{206}{206 + 121} = \frac{206}{327} = 62.9969\%$$
  $$\text{Recall} = \frac{206}{206 + 852} = \frac{206}{1058} = 19.4707\%$$
  $$\text{F1-Score} = \frac{2 \cdot 0.629969 \cdot 0.194707}{0.629969 + 0.194707} = \frac{412}{1385} = \mathbf{0.297473}$$

---

# Stratified 5-Fold Cross-Validation

Results obtained from the 5-fold cross-validation pipeline (`random_state=42`):

#### 1. Fold Results (Mean ± Standard Deviation)

| Classifier | Accuracy | Precision (`yes`) | Recall (`yes`) | F1-Score (`yes`) | Total TP | Total FP | Total FN | Total TN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bayesian Network** ($\tau=0.50$) | **89.24% ± 0.19%** | **62.00% ± 1.56%** | 20.63% ± 2.47% | 30.91% ± 3.00% | 1,091 | 666 | 4,198 | 39,256 |
| **Rule-Based** (2 branches) | 88.60% ± 0.14% | 52.17% ± 0.96% | **31.03% ± 1.39%** | **38.90% ± 1.30%** | **1,641** | 1,504 | 3,648 | 38,418 |
