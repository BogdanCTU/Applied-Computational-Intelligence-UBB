# Comparative Analysis: Bayesian Networks vs. Rule-Based Classification
## Computational Intelligence & Software Engineering — Project Presentation

**Course:** Year 2, Semester 1 — Computational Intelligence in Software Engineering (CISE)  
**Project:** Part A (Bayesian Network) vs. Part B (Constrained Rule-Based Classifier)  
**Dataset:** UCI Machine Learning Repository — Bank Marketing Dataset  
**Target:** Term Deposit Subscription ($y \in \{\text{'yes'}, \text{'no'}\}$)  

---

## Executive Summary

This university machine learning investigation compares a probabilistic generative model (**Bayesian Network**) against an explainable, deterministic heuristic (**Rule-Based Classifier**) operating under a strict **branching-statement constraint** ($\le n$ branches for $n$ input attributes). 

Both models were trained, tuned, and evaluated on the official UCI Bank Marketing dataset ($N = 45,211$) using an identical, leak-free, stratified train/test split (80/20, $N_{\text{test}} = 9,043$).

### Key Verified Empirical Findings
- **Rule-Based Classifier:** **F1 = $0.4007$** (Precision: $53.74\%$, Recall: $31.95\%$, Accuracy: $88.82\%$).
- **Bayesian Network (Default MAP Cutoff $\tau = 0.50$):** **F1 = $0.2975$** (Precision: $63.00\%$, Recall: $19.47\%$, Accuracy: $89.24\%$).
- **Bayesian Network (Calibrated Cutoff $\tau^* = 0.21$):** **F1 = $0.4263$** (Precision: $45.91Default\%$, Recall: $39.79\%$, Accuracy: $87.47\%$). Tuned strictly on training-validation data with zero test leakage.
- **Majority Baseline:** **F1 = $0.0000$** (Precision: $0.00\%$, Recall: $0.00\%$, Accuracy: $88.30\%$).
- **Branching Constraint Compliance:** Verified by static AST analysis. The rule-based classifier contains exactly **$2$ branching statements** for **$2$ attributes used** ($2 \le 2 \text{ attributes used} \le 15 \text{ dataset attributes}$), completely free of helper-function or code-generation evasion.

---

## 1. Project Objective and Assignment Requirements

The assignment investigates the empirical trade-offs between probabilistic graphical modeling and constrained, interpretable expert systems:

1. **Part A — Bayesian Network:**
   - Implement a discrete Bayesian Network using an established open-source framework (`pgmpy 1.1.2`).
   - Pipeline must include data ingestion, leak-free discretization/preprocessing, score-based structure learning (DAG), parameter estimation (CPTs with smoothing prior), and exact probabilistic inference (Variable Elimination).
2. **Part B — Rule-Based Classifier:**
   - Solve the identical classification task using explicit `if/elif/else` branching logic.
   - Satisfy the constraint of using **no more than $n$ branching statements**, where $n$ represents the number of input attributes.
   - Prevent evasion through hidden helper functions, code generation, or lookup dictionaries.
   - Provide an automated compliance verification mechanism.
3. **Rigorous & Fair Evaluation:**
   - Prevent data leakage: strictly exclude the confounding telephone call `duration` feature, and learn preprocessing parameters strictly on the training partition.
   - Evaluate both models on the exact same held-out test records ($9,043$ instances).
   - Compute Accuracy, Precision, Recall, F1-score (positive class = `'yes'`), and Confusion Matrices.
4. **Interactive Software Interface:**
   - Provide both a native Windows desktop GUI (Tkinter/ttk) and an interactive web dashboard (Streamlit) enabling parameter exploration, network inspection, rule execution tracing, and comparison metrics.

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

The solution is engineered according to clean software architecture principles, separating core computational logic, statistical services, and user interfaces:

```
CISE_Project1/
├── 1_Dataset/                           # Data loading and telemetry
│   ├── bank-full.csv                    # Raw UCI dataset (auto-downloaded)
│   └── data_loader.py                   # Ingestion & dataset inspection
├── 2_BayesianNetworkClassification/     # Part A: Bayesian Network
│   └── bayesian_network.py              # Structure learning, CPT estimation, inference
├── 3_RuleBasedClassification/           # Part B: Constrained Rules
│   ├── rule_based.py                    # 2-branch deterministic classification logic
│   └── branch_counter.py                # AST static compliance verification
├── src/                                 # Shared Infrastructure
│   ├── config.py                        # Central settings, seeds, paths
│   ├── preprocessing.py                 # Quantile discretizer & category aligner
│   ├── evaluation.py                    # Binary metrics & confusion matrix heatmaps
│   ├── model_service.py                 # Service facade managing model state
│   ├── main.py                          # End-to-end experiment pipeline
│   └── ui_helpers.py                    # Web and styling helpers
├── desktop_app.py                       # Native Windows Desktop GUI (Tkinter/ttk)
├── app.py                               # Web Dashboard GUI (Streamlit)
├── run_app.py                           # Unified entry point launcher
├── build_exe.py                         # PyInstaller build automation
├── BankMarketingClassifier.spec         # Executable build specification
├── tests/                               # Comprehensive unit tests (32 test cases)
└── results/                             # Saved artifacts & evaluation logs
    ├── metrics.csv                      # Test set metrics table
    ├── test_predictions.csv             # Row-by-row posterior probabilities
    ├── threshold_analysis.csv           # Sweep across probability cutoffs
    ├── network_description.txt          # Learned DAG structure & CPTs
    ├── network_structure.png            # Visualized DAG graph
    └── confusion_*.png                  # Confusion matrix heatmaps
```

- **Core Technologies:** Python 3.13, `pgmpy 1.1.2`, `scikit-learn 1.9.1`, `pandas 3.0.6`, `numpy 2.4.6`, `matplotlib 3.11.2`, `seaborn 0.13.2`, `networkx 3.6.1`, `pytest 9.1.1`, `tkinter`, `PyInstaller 6.22`.

---

## 4. Methodology: Part A — Bayesian Network

The discrete Bayesian Network models the joint probability distribution over the bank client features and campaign response:

$$P(X_1, X_2, \dots, X_m, Y) = \prod_{i=1}^{m} P(X_i \mid \text{Parents}(X_i)) \cdot P(Y \mid \text{Parents}(Y))$$

### 4.1 Preprocessing and Discretization
Discrete Bayesian Networks require finite discrete sample spaces. Continuous numeric attributes (`age`, `balance`, `day`, `campaign`, `pdays`, `previous`) are converted into discrete quantile bins using `BankPreprocessor`.
- **Training-Only Fitting:** Bin split edges and known categories are fitted strictly on $X_{\text{train}}$ ($36,168$ records) to avoid information leakage.
- **Special Values:** `pdays = -1` (client never previously contacted) is explicitly partitioned into its own distinct state (`"never_contacted"`).
- **Out-of-Vocabulary Resilience:** Unseen test categories default to the most frequent training category.

### 4.2 Structure Learning (DAG Discovery)
- **Algorithm:** Score-based `HillClimbSearch` optimizing the Bayesian Information Criterion (BIC-D):
  $$\text{BIC}(G \mid D) = \log P(D \mid \hat{\theta}, G) - \frac{\text{dim}(G)}{2} \log N$$
  The BIC score balances goodness-of-fit against graph complexity, preventing over-parameterized dense graphs.
- **Structural Constraints:** `max_indegree = 3` (no node may have more than 3 parent nodes), preventing combinatorial explosion in CPT dimensions.
- **Learned DAG Topology:** The optimizer discovers $30$ directed edges across $16$ nodes. 
- **Direct Parents of Target $y$:** The learned graph establishes directed edges:
  $$\text{month} \longrightarrow y \quad \text{and} \quad \text{poutcome} \longrightarrow y$$
  The network automatically identified that campaign contact month and previous campaign outcome are the primary direct drivers of term deposit subscription.
- **Markov Blanket of Target $y$:** $[\text{'contact'}, \text{'marital'}, \text{'month'}, \text{'poutcome'}]$. Once these 4 variables are observed, $y$ is conditionally independent of all remaining features.

### 4.3 Parameter Estimation (CPTs with BDeu Prior)
- **Estimator:** `DiscreteBayesianEstimator` using a Bayesian Dirichlet equivalent uniform (BDeu) prior with equivalent sample size $\alpha = 5$.
- **Formula:**
  $$P(X = k \mid \text{Parents} = j) = \frac{N_{ijk} + \frac{\alpha}{r_i \cdot q_i}}{N_{ij} + \frac{\alpha}{q_i}}$$
- **Smoothing Guarantee:** Pseudo-counts ensure that no probability entry in any CPT is ever exactly zero, preventing zero-probability crashes during inference on unseen test combinations.

### 4.4 Exact Probabilistic Inference
- **Method:** `VariableElimination` computes the exact posterior marginal distribution:
  $$P(Y = \text{'yes'} \mid \mathbf{e}) = \frac{\sum_{\mathbf{Z}} P(Y = \text{'yes'}, \mathbf{e}, \mathbf{Z})}{\sum_{y'} \sum_{\mathbf{Z}} P(y', \mathbf{e}, \mathbf{Z})}$$
- **Decision Rule:** Maximum A Posteriori (MAP) classification thresholded at default cutoff $\tau = 0.50$:
  $$\hat{y} = \begin{cases} \text{'yes'}, & \text{if } P(Y = \text{'yes'} \mid \mathbf{e}) \ge \tau \\ \text{'no'}, & \text{otherwise} \end{cases}$$
- **Performance Optimization:** Inference is cached over unique binned test configurations, reducing inference runtime from minutes to seconds.

---

## 5. Methodology: Part B — Constrained Rule-Based Classifier

### 5.1 Formulation and Decision Logic
The rule-based model was designed by examining category subscription rates on the **training split only** ($36,168$ records):
1. **Baseline Population Rate:** $11.7\%$ subscription rate across all clients.
2. **Prior Campaign Success (`poutcome == 'success'`):** Yields a **$64.6\%$** positive rate ($778$ deposits out of $1,205$ clients in training).
3. **Shoulder Calendar Months (`month` $\in$ `['mar', 'sep', 'oct', 'dec']`):** Yield a **$43.8\% - 50.9\%$** positive rate (compared to $\le 19.5\%$ for other months).
4. **Default Class:** All other records default to the majority non-subscribing class (`'no'`).

```python
HIGH_SUCCESS_MONTHS = ("mar", "sep", "oct", "dec")

def classify_client(record: dict) -> str:
    if record["poutcome"] == "success":
        return "yes"
    elif record["month"] in HIGH_SUCCESS_MONTHS:
        return "yes"
    else:
        return "no"
```

### 5.2 Branching Statement Limit Verification
The assignment dictates:
> *"The rule-based solution must use no more than n branching statements, where n is the number of attributes."*

To ensure absolute academic integrity, static AST analysis is implemented in [`3_RuleBasedClassification/branch_counter.py`](file:///e:/PERSONAL/GitHub/1_Applied-Computational-Intelligence-UBB/Year2_Semester1_ComputationalIntelligenceSoftwareEngineering/CISE_Project1/3_RuleBasedClassification/branch_counter.py):
- **AST Parsing:** Traverses the entire `rule_based.py` source file counting `ast.If`, `ast.IfExp`, `ast.match_case`, and comprehension filters.
- **Distinction Between Branches and Rules:**
  - Branching statements: Exactly **$2$** (`if` and `elif`). A trailing `else` is the default fallthrough branch and not a conditional branch.
  - Return statements (decision rules): **$3$** (`return "yes"`, `return "yes"`, `return "no"`).
- **Compliance Proof:**
  - Number of attributes used by the model: $n = 2$ (`poutcome`, `month`).
  - Total dataset features available: $N = 15$ ($16$ including duration).
  - **Result:** $2 \text{ branches} \le 2 \text{ attributes used} \le 15 \text{ dataset attributes}$.
  - The classifier complies under both the strict interpretation ($n = \text{attributes accessed}$) and the broad interpretation ($n = \text{dataset attributes}$).

---

## 6. Experimental Verification & Results

### 6.1 Experimental Protocol
- **Stratified Partitioning:** $80\%$ Training ($36,168$ rows) and $20\%$ Held-Out Testing ($9,043$ rows), seeded with `random_state = 42`.
- **Identical Test Set:** Both models were evaluated on the exact same uncorrupted test partition.
- **Positive Label:** Subscription (`"yes"`) is explicitly designated as the positive class for all precision, recall, and F1 calculations (`pos_label="yes"`).

### 6.2 Primary Test Set Results (Default $\tau = 0.50$)

| Classifier | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rule-Based Classifier** | **88.82%** | **53.74%** | **31.95%** | **0.4007** | 7,694 | 291 | 720 | **338** |
| **Bayesian Network ($\tau = 0.50$)** | **89.24%** | **63.00%** | **19.47%** | **0.2975** | **7,864** | **121** | 852 | 206 |
| **Majority Baseline** | 88.30% | 0.00% | 0.00% | 0.0000 | 7,985 | 0 | 1,058 | 0 |

### 6.3 Metric Recalculation Verification

Every reported metric is mathematically derived from the verified confusion matrices:

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

- **Majority Baseline:**
  $$\text{Accuracy} = \frac{7985}{9043} = 88.3003\%, \quad \text{Precision} = 0.00\%, \quad \text{Recall} = 0.00\%, \quad \text{F1} = 0.0000$$

### 6.4 Confusion Matrices ($N = 9,043$)

```
Bayesian Network (tau = 0.50)           Rule-Based Classifier
                 Predicted                              Predicted
                 no     yes                              no     yes
Actual  no    [[ 7864,  121 ],         Actual  no    [[ 7694,  291 ],
        yes    [  852,  206 ]]                 yes    [  720,  338 ]]
```

---

## 7. Deep Audit: Posterior Probabilities & Threshold Investigation

### 7.1 Quantitative Audit of Bayesian Network Posteriors
An audit of the $9,043$ posterior probabilities $P(Y = \text{'yes'} \mid \mathbf{e})$ saved in `results/test_predictions.csv` reveals:
- **Sample Mean:** $\mu = 0.1178$ ($11.78\%$), closely matching the true empirical prevalence ($11.70\%$). The model is well-calibrated overall.
- **Median & Interquartile Range:** Median $= 0.0738$, 25th percentile $= 0.0644$, 75th percentile $= 0.1032$. Over $75\%$ of test records receive a predicted probability below $11\%$.
- **Class Separation:** 
  - Mean $P(\text{yes})$ for actual `'no'` instances: **$0.0994$** ($9.94\%$).
  - Mean $P(\text{yes})$ for actual `'yes'` instances: **$0.2568$** ($25.68\%$).
- **The Cutoff Penalty:** While the Bayesian Network assigns over **$2.5\times$ higher probability** to actual depositors, only **$327$ records ($3.6\%$)** achieve $P(\text{yes}) \ge 0.50$. Consequently, the standard $0.50$ MAP decision rule misses $852$ true subscribers ($80.5\%$ of all depositors).

### 7.2 Rigorous Threshold Calibration (Tuned Strictly on Validation Data)
To evaluate whether threshold calibration improves recall without data leakage, we conducted a controlled experiment:
1. An internal validation split ($20\%$, $N = 7,234$) was partitioned strictly from the training data ($X_{\text{train}}$).
2. The classification threshold $\tau$ was swept across $[0.10, 0.50]$ on the validation fold to maximize validation F1.
3. The optimal threshold selected on validation data was **$\tau^* = 0.21$** (Validation F1 = $0.4289$).
4. This frozen threshold was then evaluated on the untouched held-out test set ($N = 9,043$).

#### Test Set Performance Across Threshold Sweep

| Threshold $\tau$ | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) | Note |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0.50** | **89.24%** | **63.00%** | 19.47% | 0.2975 | **7,864** | **121** | 852 | 206 | Standard MAP cutoff |
| **0.40** | 89.10% | 57.26% | 26.84% | 0.3655 | 7,773 | 212 | 774 | 284 | Higher precision |
| **0.30** | 88.54% | 51.56% | 34.31% | 0.4120 | 7,644 | 341 | 695 | 363 | Balanced trade-off |
| **0.21 ($\tau^*$)** | **87.47%** | **45.91%** | **39.79%** | **0.4263** | 7,489 | 496 | **637** | **421** | **Validation-Tuned Cutoff** |
| **0.20** | 86.20% | 41.15% | 41.78% | 0.4146 | 7,353 | 632 | 616 | 442 | Recall prioritized |
| **0.15** | 84.41% | 36.75% | 46.12% | 0.4091 | 7,145 | 840 | 570 | 488 | High FP cost |

*Results saved in `results/threshold_analysis.csv`.*

### 7.3 Measured Reality vs. Hypotheses

| Factor | Measured Finding (Verified) | Scientific Hypothesis / Interpretation |
| :--- | :--- | :--- |
| **Default Model Ranking** | Rule-Based F1 ($0.4007$) > Bayesian Network F1 ($0.2975$) at $\tau = 0.50$. | The rule-based model succeeds because its two conditions operate at an implicit positive rate of $\sim 44\% - 65\%$, aligning with the minority-class density. |
| **Calibrated Model Ranking** | Calibrated Bayesian Network ($\tau^* = 0.21$) achieves F1 = **$0.4263$** on the test set. | When the probability threshold is aligned with the class prior, the Bayesian Network outperforms the rule-based classifier by leveraging joint probabilistic dependencies across features. |
| **Predictive Features** | `month` and `poutcome` are the parents of $y$ in the learned DAG. | Both human intuition and machine-learned structure search independently isolate past campaign outcome and calendar timing as the dominant pre-contact signals. |

---

## 8. Conclusions, Limitations, and Future Improvements

### 8.1 Conclusions
1. **Assignment Objective Met:** A simple rule-based model with only $2$ branches can match and outperform an uncalibrated Bayesian Network on imbalanced tabular data.
2. **Class Imbalance Dynamics:** In an $11.7\%$ positive environment, default $0.50$ probability thresholds severely penalize recall in generative probabilistic models.
3. **Threshold Calibration:** Tuning the decision threshold on validation data ($\tau^* = 0.21$) unlocks the true generative power of the Bayesian Network, boosting F1 to **$0.4263$** and capturing **$421$ true depositors** ($+104\%$ increase over default cutoff).
4. **Academic Integrity:** The rule-based classifier respects the $\le n$ branching limit under static AST analysis with no hidden evasion.

### 8.2 Limitations
- **Quantization Granularity:** Discretizing continuous variables (`age`, `balance`, `day`) into 3–4 quantile bins inevitably discards fine numerical trends.
- **Independence Assumptions:** Hill Climb search was restricted to `max_indegree = 3` to prevent memory blowup, potentially pruning higher-order feature interactions.

### 8.3 Future Improvements
- **Continuous Probabilistic Modeling:** Implementing Hybrid Bayesian Networks (Gaussian/Copula CPTs) to model numeric features without binning.
- **Cost-Sensitive Financial Optimization:** Incorporating actual commercial telemarketing costs (e.g., dialing cost vs. value of secured term deposit).

---

## 9. Instructions to Launch and Reproduce

### 9.1 Automated Test Suite
Run the 32 unit tests verifying metric recalculation, threshold optimization, preprocessing, and AST compliance:
```powershell
pytest
```

### 9.2 Reproduce Full Experiment Pipeline (CLI)
Re-runs the entire pipeline, structure learning, threshold sweep, and report generation:
```powershell
python -m src.main
# or:
python run_app.py --cli
```

### 9.3 Launch Native Windows Desktop Application (Tkinter)
Launch the pure desktop window application (no web browser):
```powershell
python desktop_app.py
# or:
python run_app.py
```

### 9.4 Launch Compiled Windows Executable (.exe)
Double-click or run:
```powershell
.\dist\BankMarketingClassifier\BankMarketingClassifier.exe
```

### 9.5 Launch Optional Web Browser Dashboard (Streamlit)
```powershell
python -m streamlit run app.py
```
