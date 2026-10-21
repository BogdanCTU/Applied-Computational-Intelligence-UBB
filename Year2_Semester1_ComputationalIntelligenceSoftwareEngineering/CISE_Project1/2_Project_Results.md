# Comparative Analysis: Bayesian Networks vs. Rule-Based Classification
## Computational Intelligence & Software Engineering — Project Presentation

**Course:** Year 2, Semester 1 — Computational Intelligence in Software Engineering (CISE)  
**Project:** Part A (Bayesian Network) vs. Part B (Constrained Rule-Based Classifier)  
**Dataset:** UCI Machine Learning Repository — Bank Marketing Dataset  
**Target:** Term Deposit Subscription ($y \in \{\text{'yes'}, \text{'no'}\}$)  

---

## Executive Summary

This university machine learning investigation compares a probabilistic generative model (**Bayesian Network**) against an explainable, deterministic heuristic (**Rule-Based Classifier**) operating under a strict **branching-statement constraint** ($\le n$ branches for $n$ input attributes). 

Following the project's rigorous evaluation protocol:
1. **Rule-Based Classification:** Evaluated directly on the **full dataset** ($N = 45,211$). Because it is deterministic, uses static decision rules derived from domain analysis, and has zero tunable continuous parameters requiring split-to-split fitting, **no K-Fold cross-validation is applied**.
2. **Bayesian Network Classification:** Evaluated using **Stratified 5-Fold Cross-Validation** ($N = 45,211$, $5$ folds, zero data leakage) reporting **Mean and Standard Deviation** across folds for both the default MAP threshold **$\tau = 0.50$** and the calibrated best threshold **$\tau = 0.20$**.
3. **Majority Baseline:** Evaluated on the full dataset ($N = 45,211$) as a non-learning benchmark.

### Key Verified Empirical Findings

#### Master Evaluation Table: Full Dataset Rule-Based vs. Bayesian Network 5-Fold Cross-Validation

| Classifier | Evaluation Framework / Threshold | Accuracy | Precision | Recall | F1-Score | Total TP | Total FP | Total FN | Total TN | Mean and Standard Deviation (for K-Fold on Bayesian Network Classification) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Rule-Based Classifier** (2 branches) | **Full Dataset Evaluation** ($N = 45,211$) | **88.60%** | **52.18%** | **31.03%** | **0.3891** *(38.91%)* | **1,641** | 1,504 | 3,648 | 38,418 | *N/A (Deterministic full dataset evaluation, no K-Fold)* |
| **Bayesian Network** (Default $\tau = 0.50$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | **89.24%** | **62.00%** | 20.63% | 30.91% *(0.3091)* | 1,091 | **666** | 4,198 | 39,256 | **Accuracy: 89.24% ± 0.19%<br>Precision: 62.00% ± 1.56%<br>Recall: 20.63% ± 2.47%<br>F1-Score: 30.91% ± 3.00% (0.3091 ± 0.0300)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 89.24% | 62.09% | 20.63% | 0.3097 *(30.97%)* | 1,091 | 666 | 4,198 | 39,256 | *Pooled Out-of-Fold Global Totals* |
| **Bayesian Network** (Best Cutoff $\tau = 0.20$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | 86.18% | 41.37% | **42.90%** | **42.09% *(0.4209)*** | **2,269** | 3,230 | **3,020** | 36,692 | **Accuracy: 86.18% ± 0.77%<br>Precision: 41.37% ± 2.93%<br>Recall: 42.90% ± 1.57%<br>F1-Score: 42.09% ± 2.06% (0.4209 ± 0.0206)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 86.18% | 41.26% | 42.90% | 0.4207 *(42.07%)* | 2,269 | 3,230 | 3,020 | 36,692 | *Pooled Out-of-Fold Global Totals* |
| **Majority Baseline** (Always `"no"`) | Full Dataset Evaluation ($N = 45,211$) | 88.30% | 0.00% | 0.00% | 0.0000 *(0.00%)* | 0 | 0 | 5,289 | **39,922** | *N/A (Reference baseline)* |

#### Core Scientific Conclusions
1. **Rule-Based Classifier on Full Dataset:** With just 2 branching statements (`poutcome`, `month`), the deterministic rule achieves an F1-score of **$0.3891$** ($38.91\%$) on all $45,211$ clients, capturing **$1,641$ true subscribers** with $52.18\%$ precision.
2. **Bayesian Network at Default Cutoff ($\tau = 0.50$):** Excels in Precision (**$62.00\% \pm 1.56\%$**) and Accuracy (**$89.24\% \pm 0.19\%$**), minimizing false alarms to only **$666$** across all folds, but achieves lower recall ($20.63\% \pm 2.47\%$, F1 = $0.3091 \pm 0.0300$).
3. **Bayesian Network at Best Cutoff ($\tau = 0.20$):** Dramatically elevates Recall to **$42.90\% \pm 1.57\%$** and achieves the highest overall F1-Score of **$42.09\% \pm 2.06\%$** ($0.4209 \pm 0.0206$), identifying **$2,269$ true subscribers** across the population.
4. **Model Stability Confirmed by Low Cross-Validation Standard Deviation:** The small standard deviations across folds ($\sigma < 0.03$ across all metrics) verify that the Bayesian Network's performance is highly stable across different partitions and free from data leakage.

## 1. Project Objective and Assignment Requirements

The assignment investigates the empirical trade-offs between probabilistic graphical modeling and constrained, interpretable expert systems:

1. **Part A — Bayesian Network:**
   - Implement a discrete Bayesian Network using an established open-source framework (`pgmpy 1.1.2`).
   - Pipeline must include data ingestion, leak-free discretization/preprocessing, score-based structure learning (DAG), parameter estimation (CPTs with smoothing prior), and exact probabilistic inference (Variable Elimination).
2. **Part B — Rule-Based Classifier:**
   - Solve the identical classification task using explicit `if/elif/else` branching logic.
   - Satisfy the constraint of using **no more than $n$ branching statements**, where $n$ represents the number of input attributes used.
   - Prevent evasion through hidden helper functions, code generation, or lookup dictionaries.
   - Provide an automated compliance verification mechanism.
3. **Rigorous & Fair Evaluation:**
   - Prevent data leakage: strictly exclude the confounding telephone call `duration` feature, and learn preprocessing parameters strictly on the training partition.
   - **Rule-Based Classification:** Evaluated directly on the **full dataset** ($N = 45,211$) without K-Fold cross-validation (deterministic heuristic with zero learned continuous parameters).
   - **Bayesian Network Classification:** Evaluated using **Stratified 5-Fold Cross-Validation** ($N = 45,211$) at both the default MAP cutoff **$\tau = 0.50$** and the calibrated best cutoff **$\tau = 0.20$**, reporting **Accuracy**, **Precision**, **Recall**, **F1-Score**, **Total TP**, **Total FP**, **Total FN**, **Total TN**, and **Mean and Standard Deviation** across folds.
   - Benchmarked against held-out 80/20 test split ($9,043$ records) for single-split verification.

4. **Interactive Software Interface:**
   - Provide both a native Windows desktop GUI (Tkinter/ttk) and an interactive web dashboard (Streamlit) enabling parameter exploration, network inspection, rule execution tracing, cross-validation telemetry, and comparison metrics.

---

## 2. Dataset and Target Definition

### 2.1 Dataset Profile
- **Repository:** UCI Machine Learning Repository (Bank Marketing Dataset, Portuguese banking institution).
- **Instances:** $45,211$ customer contact records.
- **Attributes:** $16$ input features + binary target $y$.
  - *Categorical ($9$):* `job`, `marital`, `education`, `default`, `housing`, `loan`, `contact`, `month`, `poutcome`.
  - *Numerical ($6$):* `age`, `balance`, `day`, `campaign`, `pdays`, `previous`.
  - *Target ($1$):* `y` $\in$ {`"yes"` ($5,289$, $11.7\%$), `"no"` ($39,922$, $88.3\%$)}.
- **Missing Value Handling:** Missing entries are codified natively in the dataset as the category `"unknown"` (e.g., `poutcome` has $81.7\%$ `"unknown"`, `contact` has $28.8\%$). These were retained as informative discrete states rather than arbitrarily imputed.

### 2.2 Strict Target Leakage Prevention (`duration` Exclusion)
The attribute `duration` denotes the duration of the telephone call in seconds. 
- *Why it is excluded:* The call duration is unknown prior to dialing a customer. Furthermore, call duration heavily correlates with success (a client who agrees to deposit talks longer). Including it constitutes classic target leakage.
- *Implementation:* `duration` is **strictly excluded** from feature sets in both classifiers, ensuring that all predictions reflect pre-contact customer intelligence.
- *Verified Features Used ($15$):* `['job', 'marital', 'education', 'default', 'housing', 'loan', 'contact', 'month', 'poutcome', 'age', 'balance', 'day', 'campaign', 'pdays', 'previous']`.

---

## 3. Technologies and Architecture

The solution is engineered according to clean software architecture principles:

```
CISE_Project1/
├── 1_Dataset/                           # Data loading and inspection
│   ├── bank-full.csv                    # Raw UCI dataset (45,211 records)
│   └── data_loader.py                   # Ingestion & dataset inspection
├── 2_BayesianNetworkClassification/     # Part A: Bayesian Network
│   └── bayesian_network.py              # Structure learning, CPT estimation, inference
├── 3_RuleBasedClassification/           # Part B: Constrained Rules
│   ├── rule_based.py                    # 2-branch deterministic classification logic
│   └── branch_counter.py                # AST static compliance verification
├── src/                                 # Shared Infrastructure
│   ├── config.py                        # Central settings, seeds, paths, features
│   ├── cross_validation.py              # Stratified 5-Fold CV orchestrator (leak-free)
│   ├── preprocessing.py                 # Quantile discretizer & category aligner
│   ├── evaluation.py                    # Binary metrics, CV aggregation & plot generation
│   ├── model_service.py                 # Service facade managing model & CV state
│   ├── main.py                          # CLI runner (--heldout, --cv, --all)
│   └── ui_helpers.py                    # Web and styling helpers (plots, forms)
├── pages/                               # Multi-Page Web GUI (Streamlit)
│   ├── 1_Overview.py                    # Model comparison & 5-Fold CV dashboard
│   ├── 2_Bayesian_Network.py            # DAG inspector, CPT browser, inference
│   ├── 3_Rule_Based.py                  # Rule logic & execution trace
│   └── 4_Dataset_Explorer.py            # Feature explorer & distributions
├── desktop_app.py                       # Native Desktop GUI (Tkinter/ttk)
├── app.py                               # Web Dashboard Entry Point (Streamlit)
├── tests/                               # Comprehensive unit tests (45 test cases)
│   ├── test_cross_validation.py         # 12 CV leakage, fold & metric tests
│   ├── test_evaluation.py               # Positive-class metrics & sweep tests
│   ├── test_model_service.py            # Service orchestration & CV tests
│   ├── test_preprocessing.py            # Discretization & category tests
│   └── test_rule_based.py               # AST branching limit & logic tests
└── results/                             # Saved artifacts & evaluation logs
    ├── cv_metrics_summary.csv           # CV Mean ± Std and pooled summary
    ├── cv_fold_metrics.csv              # Per-fold metrics for folds 1 to 5
    ├── cv_pooled_metrics.csv            # Pooled out-of-fold metrics across 45,211 rows
    ├── cv_predictions.csv               # Out-of-fold predictions for every row
    ├── cv_comparison.png                # Error-bar comparative visualization
    ├── metrics.csv                      # Held-out test set metrics
    ├── test_predictions.csv             # Held-out predictions & probabilities
    ├── threshold_analysis.csv           # Threshold calibration sweep
    └── network_structure.png            # Visualized DAG graph
```

- **Core Technologies:** Python 3.13, `pgmpy 1.1.2`, `scikit-learn 1.9.1`, `pandas 3.0.6`, `numpy 2.4.6`, `matplotlib 3.11.2`, `seaborn 0.13.2`, `networkx 3.6.1`, `pytest 9.1.1`, `streamlit 1.66`.

---

## 4. Methodology: Part A — Bayesian Network

The discrete Bayesian Network models the joint probability distribution over the bank client features and campaign response:

$$P(X_1, X_2, \dots, X_m, Y) = \prod_{i=1}^{m} P(X_i \mid \text{Parents}(X_i)) \cdot P(Y \mid \text{Parents}(Y))$$

### 4.1 Preprocessing and Discretization
- **Quantile Binning:** Continuous numeric features (`age`, `balance`, `day`, `campaign`, `pdays`, `previous`) are converted into discrete quantile bins using `BankPreprocessor`.
- **Training-Only Fitting:** Bin split edges and category sets are fitted strictly on the training partition ($4/5$ of data during CV, $80\%$ during held-out split).
- **Special Values:** `pdays = -1` (never previously contacted) is explicitly mapped to `"never_contacted"`.
- **Out-of-Vocabulary Resilience:** Unseen categories default to the most frequent training category.

### 4.2 Structure Learning (DAG Discovery)
- **Algorithm:** Score-based `HillClimbSearch` with the Bayesian Information Criterion (BIC-D):
  $$\text{BIC}(G \mid D) = \log P(D \mid \hat{\theta}, G) - \frac{\text{dim}(G)}{2} \log N$$
- **Structural Constraints:** `max_indegree = 3` (at most 3 parent nodes per variable).
- **Learned DAG Topology:** Discovers $30$ directed edges across $16$ nodes.
- **Direct Parents of Target $y$:** Direct edges $\text{month} \longrightarrow y$ and $\text{poutcome} \longrightarrow y$.
- **Markov Blanket of Target $y$:** $[\text{'contact'}, \text{'marital'}, \text{'month'}, \text{'poutcome'}]$.

### 4.3 Parameter Estimation (CPTs with BDeu Prior)
- **Estimator:** `DiscreteBayesianEstimator` using a Bayesian Dirichlet equivalent uniform (BDeu) prior ($\alpha = 5$).
- **Smoothing Guarantee:** Every conditional probability entry is positive, preventing zero-probability crashes during inference on rare test cases.

### 4.4 Exact Probabilistic Inference
- **Method:** `VariableElimination` computes exact posterior marginals:
  $$P(Y = \text{'yes'} \mid \mathbf{e}) = \frac{\sum_{\mathbf{Z}} P(Y = \text{'yes'}, \mathbf{e}, \mathbf{Z})}{\sum_{y'} \sum_{\mathbf{Z}} P(y', \mathbf{e}, \mathbf{Z})}$$
- **Decision Rule:** MAP classification at default threshold $\tau = 0.50$.

---

## 5. Methodology: Part B — Constrained Rule-Based Classifier

### 5.1 Formulation and Decision Logic
The rule-based model was designed by examining category subscription rates on the **training split only**:
1. **Prior Campaign Success (`poutcome == 'success'`):** Yields a **$64.6\%$** positive rate ($778$ deposits out of $1,205$ clients in training).
2. **Shoulder Calendar Months (`month` $\in$ `['mar', 'sep', 'oct', 'dec']`):** Yield a **$43.8\% - 50.9\%$** positive rate (compared to $\le 19.5\%$ for other months).
3. **Default Class:** All other records default to `'no'`.

```python
HIGH_SUCCESS_MONTHS = ("mar", "sep", "oct", "dec")

def classify_client(record: dict) -> str:
    if record["poutcome"] == "success":
        return "yes"                      # Rule 1: Previous campaign succeeded
    elif record["month"] in HIGH_SUCCESS_MONTHS:
        return "yes"                      # Rule 2: Contacted in shoulder month
    else:
        return "no"                       # Rule 3: Default majority class
```

### 5.2 Branching Statement Limit Verification
The assignment dictates:
> *"The rule-based solution must use no more than n branching statements, where n is the number of attributes."*

To ensure complete compliance, static AST analysis is implemented in [`branch_counter.py`](file:///Users/stefanapopa/Documents/8%29%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_ComputationalIntelligenceSoftwareEngineering/CISE_Project1/3_RuleBasedClassification/branch_counter.py):
- **Branching Statements Count:** Exactly **$2$** (`if` and `elif`).
- **Attributes Accessed:** Exactly **$2$** (`poutcome`, `month`).
- **Compliance Proof:** $2 \text{ branching statements} \le 2 \text{ attributes accessed} \le 15 \text{ dataset attributes}$.
- **Decision Rules (Return Paths):** **$3$** (`"yes"`, `"yes"`, `"no"`).

---

## 6. Empirical Results: Full Dataset Rule-Based vs. Bayesian Network 5-Fold Cross-Validation

### 6.1 Methodological Protocol: Full Dataset vs. Stratified 5-Fold Cross-Validation
- **Rule-Based Classification on Full Dataset:**
  - The Rule-Based Classifier is deterministic and governed by 2 static domain heuristics derived from training data inspection: `poutcome == 'success'` and `month in ('mar', 'sep', 'oct', 'dec')`.
  - It contains no continuous weights, threshold parameters, or CPT tables that need fold-by-fold fitting.
  - In accordance with the methodology requirement, **no K-Fold cross-validation is performed on the Rule-Based Classifier**; instead, it is evaluated across the entire population of $N = 45,211$ clients.
- **Bayesian Network 5-Fold Cross-Validation:**
  - In contrast, the Bayesian Network learns both its graph structure (DAG via `HillClimbSearch` with BIC scoring) and parameter distributions (CPTs via BDeu Dirichlet estimator) from empirical data.
  - To rigorously evaluate its generalization capacity and strictly prevent data leakage, it undergoes **Stratified 5-Fold Cross-Validation** (`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`).
  - Preprocessing bin edges and network parameters are learned **strictly inside each fold's $4/5$ training split**.
- **Dual Cutoff Evaluation for Bayesian Network:**
  - **Default MAP Cutoff ($\tau = 0.50$):** Standard maximum a posteriori decision boundary ($P(y=\text{'yes'} \mid \mathbf{e}) \ge 0.50$).
  - **Best Calibrated Cutoff ($\tau = 0.20$):** Optimal operational threshold addressing the severe class imbalance ($11.7\%$ subscribers), prioritizing recall while maximizing F1-score.

---

### 6.2 Master Empirical Results Table

The table below presents the verified empirical comparison between the **Rule-Based Classifier** evaluated on the full dataset and the **Bayesian Network** evaluated under Stratified 5-Fold Cross-Validation at both thresholds $\tau = 0.50$ and $\tau = 0.20$.

| Classifier | Evaluation Framework / Threshold | Accuracy | Precision | Recall | F1-Score | Total TP | Total FP | Total FN | Total TN | Mean and Standard Deviation (for K-Fold on Bayesian Network Classification) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Rule-Based Classifier** (2 branches) | **Full Dataset Evaluation** ($N = 45,211$) | **88.60%**<br>*(0.8860)* | **52.18%**<br>*(0.5218)* | **31.03%**<br>*(0.3103)* | **0.3891**<br>*(38.91%)* | **1,641** | 1,504 | 3,648 | 38,418 | *N/A (Deterministic full dataset evaluation, no K-Fold)* |
| **Bayesian Network** (Default $\tau = 0.50$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | **89.24%**<br>*(0.8924)* | **62.00%**<br>*(0.6200)* | 20.63%<br>*(0.2063)* | 30.91%<br>*(0.3091)* | 1,091 | **666** | 4,198 | 39,256 | **Accuracy: 89.24% ± 0.19%<br>Precision: 62.00% ± 1.56%<br>Recall: 20.63% ± 2.47%<br>F1-Score: 30.91% ± 3.00% (0.3091 ± 0.0300)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 89.24% | 62.09% | 20.63% | 0.3097 *(30.97%)* | 1,091 | 666 | 4,198 | 39,256 | *Pooled Out-of-Fold Global Totals* |
| **Bayesian Network** (Best Cutoff $\tau = 0.20$) | **Stratified 5-Fold Cross-Validation** (Fold Mean ± Std) | 86.18%<br>*(0.8618)* | 41.37%<br>*(0.4137)* | **42.90%**<br>*(0.4290)* | **42.09%**<br>*(0.4209)* | **2,269** | 3,230 | **3,020** | 36,692 | **Accuracy: 86.18% ± 0.77%<br>Precision: 41.37% ± 2.93%<br>Recall: 42.90% ± 1.57%<br>F1-Score: 42.09% ± 2.06% (0.4209 ± 0.0206)** |
| | Cross-Validation Pooled (Out-of-Fold, $N = 45,211$) | 86.18% | 41.26% | 42.90% | 0.4207 *(42.07%)* | 2,269 | 3,230 | 3,020 | 36,692 | *Pooled Out-of-Fold Global Totals* |
| **Majority Baseline** (Always `"no"`) | Full Dataset Evaluation ($N = 45,211$) | 88.30% | 0.00% | 0.00% | 0.0000 | 0 | 0 | 5,289 | **39,922** | *N/A (Reference baseline)* |

Total Cross-Validation runtime: **15.72 seconds** (~3.14s per fold).  
*Saved in `results/cv_metrics_summary.csv` and `results/cv_predictions.csv`.*

---

### 6.3 Complete Fold-by-Fold Detailed Breakdown for Bayesian Network (K-Fold)

The table below documents every individual fold's execution metrics, runtime, and confusion matrix counts for both decision thresholds:

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

### 6.4 Detailed Step-by-Step Mathematical Calculations & Explications

This section provides complete algebraic derivations and arithmetic substitutions explaining how each metric is calculated.

#### 1. Metric Formula Definitions
- **Accuracy:** The ratio of correct predictions to total instances:
  $$\text{Accuracy} = \frac{\text{Total TP} + \text{Total TN}}{\text{Total TP} + \text{Total TN} + \text{Total FP} + \text{Total FN}} = \frac{\text{Correct Predictions}}{N}$$
- **Precision:** The proportion of predicted positives that were actual subscribers:
  $$\text{Precision} = \frac{\text{Total TP}}{\text{Total TP} + \text{Total FP}}$$
- **Recall (Sensitivity):** The proportion of actual subscribers successfully captured:
  $$\text{Recall} = \frac{\text{Total TP}}{\text{Total TP} + \text{Total FN}}$$
- **F1-Score:** The harmonic mean of precision and recall:
  $$\text{F1-Score} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} = \frac{2 \cdot \text{Total TP}}{2 \cdot \text{Total TP} + \text{Total FP} + \text{Total FN}}$$
- **Sample Mean ($\mu$) across $K = 5$ Folds:**
  $$\mu = \frac{1}{K} \sum_{k=1}^K m_k$$
- **Sample Standard Deviation ($\sigma$, $\text{ddof}=1$) across $K = 5$ Folds:**
  $$\sigma = \sqrt{\frac{1}{K - 1} \sum_{k=1}^K (m_k - \mu)^2}$$

---

#### 2. Detailed Calculations: Rule-Based Classifier on Full Dataset ($N = 45,211$)
- **Population:** $N = 45,211$ clients (Actual `'yes'` = $5,289$, Actual `'no'` = $39,922$).
- **Confusion Matrix:** $\text{Total TP} = 1,641$, $\text{Total FP} = 1,504$, $\text{Total FN} = 3,648$, $\text{Total TN} = 38,418$.
- **Step-by-Step Substitutions:**
  1. **Accuracy:**
     $$\text{Accuracy} = \frac{1641 + 38418}{45211} = \frac{40059}{45211} = 0.886045 \longrightarrow \mathbf{88.60\%}$$
  2. **Precision:**
     $$\text{Precision} = \frac{1641}{1641 + 1504} = \frac{1641}{3145} = 0.521781 \longrightarrow \mathbf{52.18\%}$$
  3. **Recall:**
     $$\text{Recall} = \frac{1641}{1641 + 3648} = \frac{1641}{5289} = 0.310267 \longrightarrow \mathbf{31.03\%}$$
  4. **F1-Score:**
     $$\text{F1-Score} = \frac{2 \cdot 0.521781 \cdot 0.310267}{0.521781 + 0.310267} = \frac{2 \cdot 1641}{2 \cdot 1641 + 1504 + 3648} = \frac{3282}{8434} = \mathbf{0.389139 \longrightarrow 38.91\%}$$

---

#### 3. Detailed Calculations: Bayesian Network Cross-Validation at Default Cutoff ($\tau = 0.50$)
- **Fold-Level Arithmetic Means ($\mu$):**
  $$\mu_{\text{Accuracy}} = \frac{0.8934 + 0.8940 + 0.8923 + 0.8892 + 0.8932}{5} = \frac{4.4621}{5} = \mathbf{0.8924 \quad (89.24\%)}$$
  $$\mu_{\text{Precision}} = \frac{0.6243 + 0.6313 + 0.6141 + 0.5959 + 0.6345}{5} = \frac{3.1002}{5} = \mathbf{0.6200 \quad (62.00\%)}$$
  $$\mu_{\text{Recall}} = \frac{0.2231 + 0.2252 + 0.2136 + 0.1645 + 0.2051}{5} = \frac{1.0314}{5} = \mathbf{0.2063 \quad (20.63\%)}$$
  $$\mu_{\text{F1}} = \frac{0.3287 + 0.3319 + 0.3170 + 0.2578 + 0.3100}{5} = \frac{1.5454}{5} = \mathbf{0.3091 \quad (30.91\%)}$$

- **Sample Standard Deviations ($\sigma$, $\text{ddof}=1$):**
  $$\sigma_{\text{Accuracy}} = \sqrt{\frac{(0.8934 - \mu)^2 + (0.8940 - \mu)^2 + (0.8923 - \mu)^2 + (0.8892 - \mu)^2 + (0.8932 - \mu)^2}{4}} = \mathbf{0.0019 \quad (\pm 0.19\%)}$$
  $$\sigma_{\text{Precision}} = \sqrt{\frac{(0.6243 - \mu)^2 + (0.6313 - \mu)^2 + (0.6141 - \mu)^2 + (0.5959 - \mu)^2 + (0.6345 - \mu)^2}{4}} = \mathbf{0.0156 \quad (\pm 1.56\%)}$$
  $$\sigma_{\text{Recall}} = \sqrt{\frac{(0.2231 - \mu)^2 + (0.2252 - \mu)^2 + (0.2136 - \mu)^2 + (0.1645 - \mu)^2 + (0.2051 - \mu)^2}{4}} = \mathbf{0.0247 \quad (\pm 2.47\%)}$$
  $$\sigma_{\text{F1}} = \sqrt{\frac{(0.3287 - \mu)^2 + (0.3319 - \mu)^2 + (0.3170 - \mu)^2 + (0.2578 - \mu)^2 + (0.3100 - \mu)^2}{4}} = \mathbf{0.0300 \quad (\pm 3.00\%)}$$

- **Total Confusion Matrix Counts across all 5 Folds ($N = 45,211$):**
  - $\text{Total TP} = 236 + 238 + 226 + 174 + 217 = \mathbf{1,091}$ (Mean per fold: $218.2 \pm 26.1$)
  - $\text{Total FP} = 142 + 139 + 142 + 118 + 125 = \mathbf{666}$ (Mean per fold: $133.2 \pm 11.0$)
  - $\text{Total FN} = 822 + 819 + 832 + 884 + 841 = \mathbf{4,198}$ (Mean per fold: $839.6 \pm 26.3$)
  - $\text{Total TN} = 7843 + 7846 + 7842 + 7866 + 7859 = \mathbf{39,256}$ (Mean per fold: $7,851.2 \pm 10.7$)

- **Pooled Out-of-Fold Global Calculations:**
  $$\text{Pooled Accuracy} = \frac{1091 + 39256}{45211} = \frac{40347}{45211} = 0.892416 \longrightarrow \mathbf{89.24\%}$$
  $$\text{Pooled Precision} = \frac{1091}{1091 + 666} = \frac{1091}{1757} = 0.620945 \longrightarrow \mathbf{62.09\%}$$
  $$\text{Pooled Recall} = \frac{1091}{1091 + 4198} = \frac{1091}{5289} = 0.206277 \longrightarrow \mathbf{20.63\%}$$
  $$\text{Pooled F1-Score} = \frac{2 \cdot 1091}{2 \cdot 1091 + 666 + 4198} = \frac{2182}{7046} = \mathbf{0.309679 \longrightarrow 30.97\%}$$

---

#### 4. Detailed Calculations: Bayesian Network Cross-Validation at Best Cutoff ($\tau = 0.20$)
- **Fold-Level Arithmetic Means ($\mu$):**
  $$\mu_{\text{Accuracy}} = \frac{0.8552 + 0.8635 + 0.8741 + 0.8557 + 0.8602}{5} = \frac{4.3088}{5} = \mathbf{0.8618 \quad (86.18\%)}$$
  $$\mu_{\text{Precision}} = \frac{0.3884 + 0.4202 + 0.4601 + 0.3894 + 0.4101}{5} = \frac{2.0683}{5} = \mathbf{0.4137 \quad (41.37\%)}$$
  $$\mu_{\text{Recall}} = \frac{0.4130 + 0.4409 + 0.4357 + 0.4112 + 0.4442}{5} = \frac{2.1450}{5} = \mathbf{0.4290 \quad (42.90\%)}$$
  $$\mu_{\text{F1}} = \frac{0.4004 + 0.4303 + 0.4476 + 0.4000 + 0.4265}{5} = \frac{2.1047}{5} = \mathbf{0.4209 \quad (42.09\%)}$$

- **Sample Standard Deviations ($\sigma$, $\text{ddof}=1$):**
  $$\sigma_{\text{Accuracy}} = \sqrt{\frac{(0.8552 - \mu)^2 + (0.8635 - \mu)^2 + (0.8741 - \mu)^2 + (0.8557 - \mu)^2 + (0.8602 - \mu)^2}{4}} = \mathbf{0.0077 \quad (\pm 0.77\%)}$$
  $$\sigma_{\text{Precision}} = \sqrt{\frac{(0.3884 - \mu)^2 + (0.4202 - \mu)^2 + (0.4601 - \mu)^2 + (0.3894 - \mu)^2 + (0.4101 - \mu)^2}{4}} = \mathbf{0.0293 \quad (\pm 2.93\%)}$$
  $$\sigma_{\text{Recall}} = \sqrt{\frac{(0.4130 - \mu)^2 + (0.4409 - \mu)^2 + (0.4357 - \mu)^2 + (0.4112 - \mu)^2 + (0.4442 - \mu)^2}{4}} = \mathbf{0.0157 \quad (\pm 1.57\%)}$$
  $$\sigma_{\text{F1}} = \sqrt{\frac{(0.4004 - \mu)^2 + (0.4303 - \mu)^2 + (0.4476 - \mu)^2 + (0.4000 - \mu)^2 + (0.4265 - \mu)^2}{4}} = \mathbf{0.0206 \quad (\pm 2.06\%)}$$

- **Total Confusion Matrix Counts across all 5 Folds ($N = 45,211$):**
  - $\text{Total TP} = 437 + 466 + 461 + 435 + 470 = \mathbf{2,269}$ (Mean per fold: $453.8 \pm 16.6$)
  - $\text{Total FP} = 688 + 643 + 541 + 682 + 676 = \mathbf{3,230}$ (Mean per fold: $646.0 \pm 61.2$)
  - $\text{Total FN} = 621 + 591 + 597 + 623 + 588 = \mathbf{3,020}$ (Mean per fold: $604.0 \pm 16.8$)
  - $\text{Total TN} = 7297 + 7342 + 7443 + 7302 + 7308 = \mathbf{36,692}$ (Mean per fold: $7,338.4 \pm 61.1$)

- **Pooled Out-of-Fold Global Calculations:**
  $$\text{Pooled Accuracy} = \frac{2269 + 36692}{45211} = \frac{38961}{45211} = 0.861759 \longrightarrow \mathbf{86.18\%}$$
  $$\text{Pooled Precision} = \frac{2269}{2269 + 3230} = \frac{2269}{5499} = 0.412620 \longrightarrow \mathbf{41.26\%}$$
  $$\text{Pooled Recall} = \frac{2269}{2269 + 3020} = \frac{2269}{5289} = 0.429004 \longrightarrow \mathbf{42.90\%}$$
  $$\text{Pooled F1-Score} = \frac{2 \cdot 2269}{2 \cdot 2269 + 3230 + 3020} = \frac{4538}{10788} = \mathbf{0.420653 \longrightarrow 42.07\%}$$

---

### 6.5 Out-of-Fold (OOF) Pooled Metrics vs. Fold-Level Means Comparison

| Classifier | Cutoff / Method | Accuracy | Precision | Recall | F1-Score | Total TP | Total FP | Total FN | Total TN | Mean ± Std (Across Folds) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Bayesian Network** | **$\tau = 0.50$ (Fold Mean ± Std)** | **89.24%** | **62.00%** | 20.63% | 30.91% | 218.2 | 133.2 | 839.6 | 7,851.2 | **Acc: 89.24% ± 0.19%<br>Prec: 62.00% ± 1.56%<br>Rec: 20.63% ± 2.47%<br>F1: 30.91% ± 3.00%** |
| | **$\tau = 0.50$ (Pooled OOF)** | **89.24%** | **62.09%** | 20.63% | 0.3097 | 1,091 | **666** | 4,198 | 39,256 | *Global totals on N = 45,211* |
| **Bayesian Network** | **$\tau = 0.20$ (Fold Mean ± Std)** | 86.18% | 41.37% | **42.90%** | **42.09%** | 453.8 | 646.0 | 604.0 | 7,338.4 | **Acc: 86.18% ± 0.77%<br>Prec: 41.37% ± 2.93%<br>Rec: 42.90% ± 1.57%<br>F1: 42.09% ± 2.06%** |
| | **$\tau = 0.20$ (Pooled OOF)** | 86.18% | 41.26% | **42.90%** | **0.4207** | **2,269** | 3,230 | **3,020** | 36,692 | *Global totals on N = 45,211* |

---

### 6.6 Aggregated Confusion Matrices ($N = 45,211$)

```
Rule-Based (Full Dataset, N=45,211)          Bayesian Network (tau=0.50, Pooled OOF)      Bayesian Network (tau=0.20, Pooled OOF)
             Predicted                                    Predicted                                    Predicted
             no       yes                                 no       yes                                 no       yes
Actual  no  [[ 38418,  1504 ],           Actual  no  [[ 39256,   666 ],           Actual  no  [[ 36692,  3230 ],
        yes [  3648,  1641 ]]                    yes [  4198,  1091 ]]                    yes [  3020,  2269 ]]
```

## 7. Held-Out 80/20 Test Set Verification & Threshold Calibration

### 7.1 Primary Held-Out Test Set Results ($N_{\text{test}} = 9,043$)

| Classifier | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rule-Based Classifier** | **88.82%** | **53.74%** | **31.95%** | **0.4007** | 7,694 | 291 | 720 | **338** |
| **Bayesian Network ($\tau = 0.50$)** | **89.24%** | **63.00%** | **19.47%** | **0.2975** | **7,864** | **121** | 852 | 206 |
| **Majority Baseline** | 88.30% | 0.00% | 0.00% | 0.0000 | 7,985 | 0 | 1,058 | 0 |

*Saved in `results/metrics.csv`.*

### 7.2 Metric Recalculation Verification ($N_{\text{test}} = 9,043$)

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

### 7.3 Threshold Calibration Analysis (Tuned Strictly on Validation Data)

An internal validation split ($20\%$, $N = 7,234$) partitioned strictly from training data identified an optimal threshold of **$\tau^* = 0.21$** (Validation F1 = $0.4289$). Evaluating this frozen threshold on the held-out test set ($N = 9,043$) yields:

| Threshold $\tau$ | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) | Note |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0.50** | **89.24%** | **63.00%** | 19.47% | 0.2975 | **7,864** | **121** | 852 | 206 | Default MAP cutoff |
| **0.40** | 89.10% | 57.26% | 26.84% | 0.3655 | 7,773 | 212 | 774 | 284 | Higher precision |
| **0.30** | 88.54% | 51.56% | 34.31% | 0.4120 | 7,644 | 341 | 695 | 363 | Balanced trade-off |
| **0.21 ($\tau^*$)** | **87.47%** | **45.91%** | **39.79%** | **0.4263** | 7,489 | 496 | **637** | **421** | **Validation-Tuned Cutoff** |
| **0.20** | 86.20% | 41.15% | 41.78% | 0.4146 | 7,353 | 632 | 616 | 442 | Recall prioritized |
| **0.15** | 84.41% | 36.75% | 46.12% | 0.4091 | 7,145 | 840 | 570 | 488 | High FP cost |

*Saved in `results/threshold_analysis.csv`.*

---

## 8. Conclusions, Limitations, and Future Improvements

### 8.1 Conclusions
1. **Assignment Constraint Compliance:** The Rule-Based classifier satisfies the strict $\le n$ branching constraint (exactly $2$ branching statements for $2$ attributes read: `poutcome`, `month`) and achieves an F1-score of **$0.3891$** ($38.91\%$) on the full dataset ($N = 45,211$), capturing **$1,641$ true subscribers**.
2. **Bayesian Network at Default Cutoff ($\tau = 0.50$):** Under Stratified 5-Fold Cross-Validation, the default Bayesian Network achieves exceptionally high precision (**$62.00\% \pm 1.56\%$**) and accuracy (**$89.24\% \pm 0.19\%$**), yielding only **$666$ total false positives** across all $45,211$ clients.
3. **Bayesian Network at Best Cutoff ($\tau = 0.20$):** Lowering the classification threshold to $\tau = 0.20$ substantially improves recall to **$42.90\% \pm 1.57\%$**, achieving an overall F1-score of **$42.09\% \pm 2.06\%$** ($0.4209 \pm 0.0206$) and capturing **$2,269$ subscribers**—surpassing the Rule-Based Classifier in both recall and F1-score.
4. **Cross-Validation Conclusiveness:** The low standard deviations across the 5 folds ($\sigma < 0.03$ across all metrics) confirm that the Bayesian Network's performance is statistically steady and not an artifact of data partitioning.

### 8.2 Limitations
- Quantile discretization discards fine continuous trends in attributes such as `balance` and `age`.
- Restricting graph search to `max_indegree = 3` prunes potentially rich higher-order interactions.

### 8.3 Future Improvements
- Continuous Hybrid Bayesian Networks (Gaussian Mixture / Copula CPTs) to eliminate discretization loss.
- Cost-sensitive loss matrices reflecting commercial call center economics.

---

## 9. Instructions to Launch and Reproduce

### 9.1 Automated Test Suite
Run the 45 unit and integration tests (including 12 dedicated cross-validation leakage and partition tests):
```bash
pytest
```

### 9.2 Reproduce Full Experiment Pipeline (CLI)

```bash
# 1. Run Stratified 5-Fold Cross-Validation (saves cv_*.csv and cv_comparison.png)
python -m src.main --cv

# 2. Run Held-out 80/20 Test Split (saves metrics.csv and test_predictions.csv)
python -m src.main --heldout

# 3. Run Both Evaluations Sequentially
python -m src.main --all
```

### 9.3 Launch Interactive Web Application (Streamlit)
```bash
python -m streamlit run app.py
```

### 9.4 Launch Native Desktop Application (Tkinter)
```bash
python desktop_app.py
```
