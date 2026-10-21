# Empirical Evaluation Results: Bayesian Networks vs. Rule-Based Classification

## 1. Dataset Profile ($N = 45,211$)

- **Source:** [UCI Bank Marketing Dataset](https://archive.ics.uci.edu/dataset/222/bank%2Bmarketing) (`bank-full.csv`, 45,211 records, 16 attributes + target `y`)
- **Target `y`:** Term deposit subscription:
  - `yes`: Positive class (5,289 instances, **11.7%**)
  - `no`: Negative class (39,922 instances, **88.3%**)
- **15 Selected Input Features:**
  - *Categorical (9):* `job`, `marital`, `education`, `default`, `housing`, `loan`, `contact`, `month`, `poutcome`
  - *Numerical (6):* `age`, `balance`, `day`, `campaign`, `pdays`, `previous`
  - *Leakage Prevention:* `duration` strictly excluded.

---

## 2. Master Evaluation Table

| Classifier | Evaluation Framework / Threshold | Accuracy | Precision | Recall | F1-Score | Total TP | Total FP | Total FN | Total TN | Mean and Standard Deviation (for K-Fold on Bayesian Network Classification) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Rule-Based Classifier** (2 branches) | **Full Dataset Evaluation** ($N = 45,211$) | **88.60%** | **52.18%** | **31.03%** | **0.3891** *(38.91%)* | **1,641** | 1,504 | 3,648 | 38,418 | *N/A (Deterministic full dataset evaluation, no K-Fold)* |
| **Bayesian Network** (Default $\tau = 0.50$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | **89.24%** | **62.00%** | 20.63% | 30.91% *(0.3091)* | 1,091 | **666** | 4,198 | 39,256 | **Accuracy: 89.24% ± 0.19%<br>Precision: 62.00% ± 1.56%<br>Recall: 20.63% ± 2.47%<br>F1-Score: 30.91% ± 3.00% (0.3091 ± 0.0300)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 89.24% | 62.09% | 20.63% | 0.3097 *(30.97%)* | 1,091 | 666 | 4,198 | 39,256 | *Pooled Out-of-Fold Global Totals* |
| **Bayesian Network** (Best Cutoff $\tau = 0.20$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | 86.18% | 41.37% | **42.90%** | **42.09% *(0.4209)*** | **2,269** | 3,230 | **3,020** | 36,692 | **Accuracy: 86.18% ± 0.77%<br>Precision: 41.37% ± 2.93%<br>Recall: 42.90% ± 1.57%<br>F1-Score: 42.09% ± 2.06% (0.4209 ± 0.0206)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 86.18% | 41.26% | 42.90% | 0.4207 *(42.07%)* | 2,269 | 3,230 | 3,020 | 36,692 | *Pooled Out-of-Fold Global Totals* |
| **Majority Baseline** (Always `"no"`) | Full Dataset Evaluation ($N = 45,211$) | 88.30% | 0.00% | 0.00% | 0.0000 | 0 | 0 | 5,289 | **39,922** | *N/A (Reference baseline)* |

---

## 3. Stratified 5-Fold Cross-Validation Detailed Breakdown (Bayesian Network)

| Cutoff | Fold | Accuracy | Precision | Recall | F1-Score | Total TP | Total FP | Total FN | Total TN | Duration |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$\tau = 0.50$** | **Fold 1** | 0.8934 | 0.6243 | 0.2231 | 0.3287 | 236 | 142 | 822 | 7,843 | 2.97s |
| | **Fold 2** | 0.8940 | 0.6313 | 0.2252 | 0.3319 | 238 | 139 | 819 | 7,846 | 3.03s |
| | **Fold 3** | 0.8923 | 0.6141 | 0.2136 | 0.3170 | 226 | 142 | 832 | 7,842 | 3.42s |
| | **Fold 4** | 0.8892 | 0.5959 | 0.1645 | 0.2578 | 174 | 118 | 884 | 7,866 | 3.22s |
| | **Fold 5** | 0.8932 | 0.6345 | 0.2051 | 0.3100 | 217 | 125 | 841 | 7,859 | 3.05s |
| | **Mean ± Std** | **0.8924 ± 0.0019** | **0.6200 ± 0.0156** | **0.2063 ± 0.0247** | **0.3091 ± 0.0300** | **218.2 ± 26.1** | **133.2 ± 11.0** | **839.6 ± 26.3** | **7,851.2 ± 10.7** | **3.14s avg** |
| | **Totals (Sum)** | — | — | — | — | **1,091** | **666** | **4,198** | **39,256** | **15.72s** |
| **$\tau = 0.20$** | **Fold 1** | 0.8552 | 0.3884 | 0.4130 | 0.4004 | 437 | 688 | 621 | 7,297 | 2.97s |
| | **Fold 2** | 0.8635 | 0.4202 | 0.4409 | 0.4303 | 466 | 643 | 591 | 7,342 | 3.03s |
| | **Fold 3** | 0.8741 | 0.4601 | 0.4357 | 0.4476 | 461 | 541 | 597 | 7,443 | 3.42s |
| | **Fold 4** | 0.8557 | 0.3894 | 0.4112 | 0.4000 | 435 | 682 | 623 | 7,302 | 3.22s |
| | **Fold 5** | 0.8602 | 0.4101 | 0.4442 | 0.4265 | 470 | 676 | 588 | 7,308 | 3.05s |
| | **Mean ± Std** | **0.8618 ± 0.0077** | **0.4137 ± 0.0293** | **0.4290 ± 0.0157** | **0.4209 ± 0.0206** | **453.8 ± 16.6** | **646.0 ± 61.2** | **604.0 ± 16.8** | **7,338.4 ± 61.1** | **3.14s avg** |
| | **Totals (Sum)** | — | — | — | — | **2,269** | **3,230** | **3,020** | **36,692** | **15.72s** |

---

## 4. Step-by-Step Metric Calculation Verification

### 4.1 Rule-Based Classifier on Full Dataset ($N = 45,211$)
- **Total TP** = $1,641$, **Total FP** = $1,504$, **Total FN** = $3,648$, **Total TN** = $38,418$
- **Calculations:**
  $$\text{Accuracy} = \frac{1641 + 38418}{45211} = \frac{40059}{45211} = 0.886045 \longrightarrow \mathbf{88.60\%}$$
  $$\text{Precision} = \frac{1641}{1641 + 1504} = \frac{1641}{3145} = 0.521781 \longrightarrow \mathbf{52.18\%}$$
  $$\text{Recall} = \frac{1641}{1641 + 3648} = \frac{1641}{5289} = 0.310267 \longrightarrow \mathbf{31.03\%}$$
  $$\text{F1-Score} = \frac{2 \cdot 0.521781 \cdot 0.310267}{0.521781 + 0.310267} = \frac{3282}{8434} = \mathbf{0.389139 \longrightarrow 38.91\%}$$

### 4.2 Bayesian Network 5-Fold Cross-Validation ($\tau = 0.50$)
- **Fold Means ($\mu$):**
  $$\mu_{\text{Accuracy}} = \frac{0.8934 + 0.8940 + 0.8923 + 0.8892 + 0.8932}{5} = \mathbf{0.8924 \quad (89.24\%)}$$
  $$\mu_{\text{Precision}} = \frac{0.6243 + 0.6313 + 0.6141 + 0.5959 + 0.6345}{5} = \mathbf{0.6200 \quad (62.00\%)}$$
  $$\mu_{\text{Recall}} = \frac{0.2231 + 0.2252 + 0.2136 + 0.1645 + 0.2051}{5} = \mathbf{0.2063 \quad (20.63\%)}$$
  $$\mu_{\text{F1}} = \frac{0.3287 + 0.3319 + 0.3170 + 0.2578 + 0.3100}{5} = \mathbf{0.3091 \quad (30.91\%)}$$
- **Sample Standard Deviations ($\sigma$, $\text{ddof}=1$):**
  $$\sigma_{\text{Accuracy}} = \mathbf{0.0019 \quad (\pm 0.19\%)}, \quad \sigma_{\text{Precision}} = \mathbf{0.0156 \quad (\pm 1.56\%)}, \quad \sigma_{\text{Recall}} = \mathbf{0.0247 \quad (\pm 2.47\%)}, \quad \sigma_{\text{F1}} = \mathbf{0.0300 \quad (\pm 3.00\%)}$$
- **Pooled Out-of-Fold Totals ($N = 45,211$):**
  - $\text{Total TP} = 1,091$, $\text{Total FP} = 666$, $\text{Total FN} = 4,198$, $\text{Total TN} = 39,256$
  $$\text{Pooled Accuracy} = \frac{1091 + 39256}{45211} = \mathbf{89.24\%}, \quad \text{Pooled Precision} = \frac{1091}{1091 + 666} = \mathbf{62.09\%}$$
  $$\text{Pooled Recall} = \frac{1091}{1091 + 4198} = \mathbf{20.63\%}, \quad \text{Pooled F1-Score} = \frac{2 \cdot 1091}{2 \cdot 1091 + 666 + 4198} = \mathbf{0.3097}$$

### 4.3 Bayesian Network 5-Fold Cross-Validation ($\tau = 0.20$, Best Threshold)
- **Fold Means ($\mu$):**
  $$\mu_{\text{Accuracy}} = \frac{0.8552 + 0.8635 + 0.8741 + 0.8557 + 0.8602}{5} = \mathbf{0.8618 \quad (86.18\%)}$$
  $$\mu_{\text{Precision}} = \frac{0.3884 + 0.4202 + 0.4601 + 0.3894 + 0.4101}{5} = \mathbf{0.4137 \quad (41.37\%)}$$
  $$\mu_{\text{Recall}} = \frac{0.4130 + 0.4409 + 0.4357 + 0.4112 + 0.4442}{5} = \mathbf{0.4290 \quad (42.90\%)}$$
  $$\mu_{\text{F1}} = \frac{0.4004 + 0.4303 + 0.4476 + 0.4000 + 0.4265}{5} = \mathbf{0.4209 \quad (42.09\%)}$$
- **Sample Standard Deviations ($\sigma$, $\text{ddof}=1$):**
  $$\sigma_{\text{Accuracy}} = \mathbf{0.0077 \quad (\pm 0.77\%)}, \quad \sigma_{\text{Precision}} = \mathbf{0.0293 \quad (\pm 2.93\%)}, \quad \sigma_{\text{Recall}} = \mathbf{0.0157 \quad (\pm 1.57\%)}, \quad \sigma_{\text{F1}} = \mathbf{0.0206 \quad (\pm 2.06\%)}$$
- **Pooled Out-of-Fold Totals ($N = 45,211$):**
  - $\text{Total TP} = 2,269$, $\text{Total FP} = 3,230$, $\text{Total FN} = 3,020$, $\text{Total TN} = 36,692$
  $$\text{Pooled Accuracy} = \frac{2269 + 36692}{45211} = \mathbf{86.18\%}, \quad \text{Pooled Precision} = \frac{2269}{2269 + 3230} = \mathbf{41.26\%}$$
  $$\text{Pooled Recall} = \frac{2269}{2269 + 3020} = \mathbf{42.90\%}, \quad \text{Pooled F1-Score} = \frac{2 \cdot 2269}{2 \cdot 2269 + 3230 + 3020} = \mathbf{0.4207}$$

---

## 5. Summary Findings
1. **Rule-Based (Full Dataset):** Achieves **F1 = 0.3891** with high explainability and low inference latency using only 2 branches.
2. **Bayesian Network ($\tau = 0.50$):** Maximizes Precision (**62.00% ± 1.56%**) and minimizes false alarms (**666 FP** total).
3. **Bayesian Network ($\tau = 0.20$):** Maximizes Recall (**42.90% ± 1.57%**) and achieves the overall highest F1-Score (**0.4209 ± 0.0206**), capturing **2,269 true subscribers**.
