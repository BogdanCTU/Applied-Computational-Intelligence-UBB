# Comparative Analysis: Bayesian Networks vs. Rule-Based Classification
## Computational Intelligence & Software Engineering — Project Presentation

**Course:** Year 2, Semester 1 — Computational Intelligence in Software Engineering (CISE)  
**Project:** Part A (Bayesian Network) vs. Part B (Constrained Rule-Based Classifier)  
**Dataset:** UCI Machine Learning Repository — Bank Marketing Dataset  
**Target:** Term Deposit Subscription ($y \in \{\text{'yes'}, \text{'no'}\}$)  

---

## Executive Summary

This university machine learning investigation compares a probabilistic generative model (**Bayesian Network**) against an explainable, deterministic heuristic (**Rule-Based Classifier**) operating under a strict **branching-statement constraint** ($\le n$ branches for $n$ input attributes). 

Both models were trained, tuned, and evaluated on the official UCI Bank Marketing dataset ($N = 45,211$) across two complementary evaluation frameworks:
1. **Stratified 5-Fold Cross-Validation:** Full dataset out-of-fold evaluation ($N = 45,211$, $5$ folds, zero data leakage) reporting **Mean** and **Standard Deviation** across all folds.
2. **Held-Out Test Set Split:** Fixed 80/20 stratified split ($N_{\text{train}} = 36,168$, $N_{\text{test}} = 9,043$).

### Key Verified Empirical Findings

#### Comprehensive Evaluation Table: Cross Validation vs. Held-Out Test Set

| Classifier | Evaluation Framework | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rule-Based Classifier** (2 branches) | **Stratified 5-Fold Cross Validation (Mean ± Standard Deviation)** | 88.60% ± 0.14% | 52.17% ± 0.96% | **31.03% ± 1.39%** | **38.90% ± 1.30%** | 38,418 | 1,504 | **3,648** | **1,641** |
| | **Cross Validation Pooled (Out-of-Fold, N = 45,211)** | 88.60% | 52.18% | **31.03%** | **0.3891** | 38,418 | 1,504 | **3,648** | **1,641** |
| | Held-Out Test Split (80/20, $N_{\text{test}} = 9,043$) | 88.82% | 53.74% | 31.95% | 0.4007 | 7,694 | 291 | 720 | 338 |
| **Bayesian Network** ($\tau = 0.50$) | **Stratified 5-Fold Cross Validation (Mean ± Standard Deviation)** | **89.24% ± 0.19%** | **62.00% ± 1.56%** | 20.63% ± 2.47% | 30.91% ± 3.00% | 39,256 | **666** | 4,198 | 1,091 |
| | **Cross Validation Pooled (Out-of-Fold, N = 45,211)** | **89.24%** | **62.09%** | 20.63% | 0.3097 | 39,256 | **666** | 4,198 | 1,091 |
| | Held-Out Test Split (80/20, $N_{\text{test}} = 9,043$) | 89.24% | 63.00% | 19.47% | 0.2975 | 7,864 | 121 | 852 | 206 |
| **Bayesian Network** (Tuned $\tau^* = 0.21$) | Held-Out Test Split (Validation-tuned, test-evaluated) | 87.47% | 45.91% | 39.79% | 0.4263 | 7,489 | 496 | 637 | 421 |
| **Majority Baseline** (Always `"no"`) | **Stratified 5-Fold Cross Validation (Mean ± Standard Deviation)** | 88.30% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | **39,922** | **0** | 5,289 | 0 |
| | **Cross Validation Pooled (Out-of-Fold, N = 45,211)** | 88.30% | 0.00% | 0.00% | 0.0000 | **39,922** | **0** | 5,289 | 0 |
| | Held-Out Test Split (80/20, $N_{\text{test}} = 9,043$) | 88.30% | 0.00% | 0.00% | 0.0000 | 7,985 | 0 | 1,058 | 0 |

#### Core Scientific Conclusions from Cross Validation
1. **Model Stability Confirmed by Low Standard Deviation:** The small standard deviations across the 5 folds ($\sigma_{F1} = 0.013$ for Rule-Based, $\sigma_{F1} = 0.030$ for Bayesian Network) confirm that performance is steady across data partitions and not dependent on a fortunate split.
2. **Distinct Optimization Targets:** 
   - The **Rule-Based Classifier** achieves significantly higher **Recall** ($31.03\% \pm 1.39\%$ vs. $20.63\% \pm 2.47\%$) and **F1-Score** ($0.3890 \pm 0.0130$ vs. $0.3091 \pm 0.0300$), capturing **$1,641$ true positive subscribers** compared to **$1,091$**.
   - The **Bayesian Network** achieves higher **Precision** ($62.00\% \pm 1.56\%$ vs. $52.17\% \pm 0.96\%$) and higher **Accuracy** ($89.24\% \pm 0.19\%$ vs. $88.60\% \pm 0.14\%$), producing less than half the false positive calls ($666$ vs. $1,504$ False Positives).
3. **Branching Constraint Integrity:** The Rule-Based classifier satisfies the strict $\le n$ branching limit (exactly $2$ branching statements for $2$ attributes read: `poutcome`, `month`) verified by automated AST inspection.


---

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
   - Support both **Stratified 5-Fold Cross-Validation** (evaluating all $45,211$ instances) and the standard **Held-Out 80/20 Test Split** ($9,043$ instances).
   - Compute **Accuracy**, **Precision**, **Recall**, **F1-Score** (positive class = `'yes'`), and Confusion Matrix: **True Neg (TN)**, **False Pos (FP)**, **False Neg (FN)**, **True Pos (TP)**.
   - Report **Mean** and **Standard Deviation** across cross-validation folds.
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

## 6. Stratified 5-Fold Cross-Validation Empirical Results

### 6.1 Experimental Protocol
- **Stratified Partitioning:** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
- **Total Population:** $N = 45,211$ instances ($39,922$ `"no"` and $5,289$ `"yes"`).
- **Partition Size:** Each validation fold contains exactly $9,042$ or $9,043$ instances ($1,057$–$1,058$ actual `"yes"` and $7,984$–$7,985$ `"no"`).
- **Leakage Prevention:** Preprocessing, quantile binning, DAG structure learning, and CPT parameter estimation are fitted **strictly on the $4/5$ training fold**. No network structure, bin boundaries, or category dictionaries are shared across folds.
- **Identical Evaluation:** The Rule-Based classifier and majority baseline are evaluated on the exact same records in every fold.

---

### 6.2 Summary Performance: Cross Validation Mean and Standard Deviation across Folds

The table below reports the **Cross Validation Fold-Level Summary (Mean ± Sample Standard Deviation, $\text{ddof}=1$)** across the 5 validation folds (as established in `README.md`), alongside the **Total Confusion Matrix Counts** summed across all 45,211 validation records. Positive class is explicitly `"yes"`.

| Classifier | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bayesian Network** ($\tau=0.50$) | **89.24% ± 0.19%**<br>*(0.8924 ± 0.0019)* | **62.00% ± 1.56%**<br>*(0.6200 ± 0.0156)* | 20.63% ± 2.47%<br>*(0.2063 ± 0.0247)* | 30.91% ± 3.00%<br>*(0.3091 ± 0.0300)* | 39,256 | **666** | 4,198 | 1,091 |
| **Rule-Based Classifier** (2 branches) | 88.60% ± 0.14%<br>*(0.8860 ± 0.0014)* | 52.17% ± 0.96%<br>*(0.5217 ± 0.0096)* | **31.03% ± 1.39%**<br>*(0.3103 ± 0.0139)* | **38.90% ± 1.30%**<br>*(0.3890 ± 0.0130)* | 38,418 | 1,504 | **3,648** | **1,641** |
| **Majority Baseline** (reference) | 88.30% ± 0.00%<br>*(0.8830 ± 0.0000)* | 0.00% ± 0.00%<br>*(0.0000 ± 0.0000)* | 0.00% ± 0.00%<br>*(0.0000 ± 0.0000)* | 0.00% ± 0.00%<br>*(0.0000 ± 0.0000)* | **39,922** | **0** | 5,289 | 0 |

Total Cross-Validation runtime: **15.72 seconds** (~3.14s per fold).  
*Saved in `results/cv_metrics_summary.csv`.*

#### Fold-Level Confusion Matrix Means (Mean ± Standard Deviation per Fold):
- **Bayesian Network:** True Neg (TN): $7,851.2 \pm 10.7$, False Pos (FP): $133.2 \pm 11.0$, False Neg (FN): $839.6 \pm 26.3$, True Pos (TP): $218.2 \pm 26.1$.
- **Rule-Based Classifier:** True Neg (TN): $7,683.6 \pm 8.9$, False Pos (FP): $300.8 \pm 8.6$, False Neg (FN): $729.6 \pm 14.7$, True Pos (TP): $328.2 \pm 14.7$.
- **Majority Baseline:** True Neg (TN): $7,984.4 \pm 0.5$, False Pos (FP): $0.0 \pm 0.0$, False Neg (FN): $1,057.8 \pm 0.4$, True Pos (TP): $0.0 \pm 0.0$.

---

### 6.3 Complete Fold-by-Fold Detailed Breakdown

The table below documents every individual fold's execution time, classification metrics, and confusion matrix counts:

| Classifier | Fold | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) | Duration |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bayesian Network** | **Fold 1** | 0.8934 | 0.6243 | 0.2231 | 0.3287 | 7,843 | 142 | 822 | 236 | 2.97s |
| **Rule-Based Classifier** | **Fold 1** | 0.8858 | 0.5200 | 0.3072 | 0.3862 | 7,685 | 300 | 733 | 325 | 2.97s |
| **Majority Baseline** | **Fold 1** | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 7,985 | 0 | 1,058 | 0 | 2.97s |
| **Bayesian Network** | **Fold 2** | 0.8940 | 0.6313 | 0.2252 | 0.3319 | 7,846 | 139 | 819 | 238 | 3.03s |
| **Rule-Based Classifier** | **Fold 2** | 0.8879 | 0.5345 | 0.3150 | 0.3964 | 7,695 | 290 | 724 | 333 | 3.03s |
| **Majority Baseline** | **Fold 2** | 0.8831 | 0.0000 | 0.0000 | 0.0000 | 7,985 | 0 | 1,057 | 0 | 3.03s |
| **Bayesian Network** | **Fold 3** | 0.8923 | 0.6141 | 0.2136 | 0.3170 | 7,842 | 142 | 832 | 226 | 3.42s |
| **Rule-Based Classifier** | **Fold 3** | 0.8851 | 0.5154 | 0.3006 | 0.3797 | 7,685 | 299 | 740 | 318 | 3.42s |
| **Majority Baseline** | **Fold 3** | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 7,984 | 0 | 1,058 | 0 | 3.42s |
| **Bayesian Network** | **Fold 4** | 0.8892 | 0.5959 | 0.1645 | 0.2578 | 7,866 | 118 | 884 | 174 | 3.22s |
| **Rule-Based Classifier** | **Fold 4** | 0.8844 | 0.5106 | 0.2968 | 0.3754 | 7,683 | 301 | 744 | 314 | 3.22s |
| **Majority Baseline** | **Fold 4** | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 7,984 | 0 | 1,058 | 0 | 3.22s |
| **Bayesian Network** | **Fold 5** | 0.8932 | 0.6345 | 0.2051 | 0.3100 | 7,859 | 125 | 841 | 217 | 3.05s |
| **Rule-Based Classifier** | **Fold 5** | 0.8871 | 0.5278 | 0.3318 | 0.4074 | 7,670 | 314 | 707 | 351 | 3.05s |
| **Majority Baseline** | **Fold 5** | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 7,984 | 0 | 1,058 | 0 | 3.05s |

*Saved in `results/cv_fold_metrics.csv`.*

---

### 6.4 Out-of-Fold (OOF) Pooled Metrics vs. Fold-Level Means

Every client in the dataset was predicted out-of-fold. The table below presents the mathematical comparison between the **Cross Validation Fold-Level Mean (± Standard Deviation)** and the **Pooled Out-of-Fold Metrics** calculated on all $45,211$ concatenated predictions (as detailed in `README.md`):

| Classifier | Aggregation Method | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bayesian Network** | **Fold Mean ± Std** | **89.24% ± 0.19%** | **62.00% ± 1.56%** | 20.63% ± 2.47% | 30.91% ± 3.00% | 7,851.2 ± 10.7 | 133.2 ± 11.0 | 839.6 ± 26.3 | 218.2 ± 26.1 |
| | **Pooled Out-of-Fold** | **89.24%** | **62.09%** | 20.63% | 0.3097 *(30.97%)* | 39,256 | **666** | 4,198 | 1,091 |
| **Rule-Based Classifier** | **Fold Mean ± Std** | 88.60% ± 0.14% | 52.17% ± 0.96% | **31.03% ± 1.39%** | **38.90% ± 1.30%** | 7,683.6 ± 8.9 | 300.8 ± 8.6 | 729.6 ± 14.7 | 328.2 ± 14.7 |
| | **Pooled Out-of-Fold** | 88.60% | 52.18% | **31.03%** | **0.3891 *(38.91%)*** | 38,418 | 1,504 | **3,648** | **1,641** |
| **Majority Baseline** | **Fold Mean ± Std** | 88.30% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | 7,984.4 ± 0.5 | 0.0 ± 0.0 | 1,057.8 ± 0.4 | 0.0 ± 0.0 |
| | **Pooled Out-of-Fold** | 88.30% | 0.00% | 0.00% | 0.0000 *(0.00%)* | **39,922** | **0** | 5,289 | 0 |

*Saved in `results/cv_pooled_metrics.csv` and `results/cv_predictions.csv`.*

---

### 6.5 Aggregated Out-of-Fold Confusion Matrices ($N = 45,211$)

```
Bayesian Network (Pooled OOF)             Rule-Based Classifier (Pooled OOF)
                 Predicted                                Predicted
                 no       yes                              no       yes
Actual  no    [[ 39256,   666 ],          Actual  no    [[ 38418,  1504 ],
        yes   [  4198,  1091 ]]                  yes   [  3648,  1641 ]]
```

---

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
1. **Assignment Constraint Compliance:** The Rule-Based classifier satisfies the $\le n$ branching constraint (exactly $2$ branching statements for $2$ attributes) and outperforms the default Bayesian Network in F1-score (**$0.3890 \pm 0.0130$ vs. $0.3091 \pm 0.0300$**).
2. **Cross-Validation Conclusiveness:** Stratified 5-Fold Cross-Validation verifies that the performance gap is not a fluke of a single split; standard deviations are exceptionally low ($\sigma < 0.03$).
3. **Operational Trade-Offs:** The Bayesian Network minimizes wasted calls (Precision $62.00\%$, only $666$ total FP), whereas the Rule-Based classifier maximizes subscriber acquisition (Recall $31.03\%$, $1,641$ total TP).
4. **Threshold Sensitivity:** Probability threshold calibration on internal validation data ($\tau^* = 0.21$) boosts the Bayesian Network's F1 to **$0.4263$**, revealing that generative modeling requires calibration when evaluated on imbalanced decision boundaries.

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
