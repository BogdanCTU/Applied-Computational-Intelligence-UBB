# Comparative Analysis: Bayesian Networks vs. Rule-Based Classification
## Computational Intelligence & Software Engineering — Project Presentation

**Course:** Year 2, Semester 1 — Computational Intelligence in Software Engineering (CISE)  
**Project:** Part A (Bayesian Network) vs. Part B (Constrained Rule-Based Classifier)  
**Dataset:** UCI Machine Learning Repository — Bank Marketing Dataset  
**Target:** Term Deposit Subscription ($y \in \{\text{'yes'}, \text{'no'}\}$)  

---

## Executive Summary

This university machine learning investigation compares a probabilistic generative model (**Bayesian Network**) against an explainable, deterministic heuristic (**Rule-Based Classifier**) operating under a strict **branching-statement constraint** ($\le n$ branches for $n$ input attributes). 

Both models were trained, tuned, and evaluated on the official UCI Bank Marketing dataset ($N = 45,211$) using an identical, leak-free, stratified train/test split (80/20).

### Key Empirical Findings
- **Rule-Based F1-Score:** **$0.4007$** (Precision: $53.74\%$, Recall: $31.95\%$, Accuracy: $88.82\%$).
- **Bayesian Network F1-Score:** **$0.2975$** (Precision: $63.00\%$, Recall: $19.47\%$, Accuracy: $89.24\%$).
- **Majority Baseline F1-Score:** **$0.0000$** (Precision: $0.00\%$, Recall: $0.00\%$, Accuracy: $88.30\%$).
- **Branching Constraint Verification:** The rule-based classifier strictly complies with the assignment constraint, utilizing **$2$ branching statements** for **$2$ attributes** ($2 \le 2$ attributes used $\le 15$ dataset features), verified by automated static AST analysis.

---

## 1. Project Objective and Assignment Requirements

The assignment investigates the empirical trade-offs between probabilistic graphical modeling and constrained, interpretable expert systems:

1. **Part A — Bayesian Network:**
   - Implement a discrete Bayesian Network using an established open-source framework (`pgmpy`).
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
   - Provide an educational GUI enabling parameter exploration, network inspection, rule execution tracing, and comparison metrics.

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
- *Why it is excluded:* The call duration is unknown prior to dialing a customer. Furthermore, call duration heavily correlates with success (a client who agrees to deposit talks longer).
- *Implementation:* `duration` is **strictly excluded** from feature sets in both classifiers, ensuring that all predictions reflect pre-contact customer intelligence.

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
└── tests/                               # Comprehensive unit tests (31 test cases)
```

- **Core Technologies:** Python 3.13, `pgmpy 1.1.2`, `scikit-learn 1.9.1`, `pandas 3.0.6`, `numpy 2.4.6`, `matplotlib 3.11.2`, `seaborn 0.13.2`, `networkx 3.6.1`, `pytest 9.1.1`, `tkinter`, `PyInstaller 6.22`.

---

## 4. Methodology: Part A — Bayesian Network

The discrete Bayesian Network models the joint probability distribution over the bank client features and campaign response:

$$P(X_1, X_2, \dots, X_m, Y) = \prod_{i=1}^{m} P(X_i \mid \text{Parents}(X_i)) \cdot P(Y \mid \text{Parents}(Y))$$

### 4.1 Preprocessing and Discretization
Discrete Bayesian Networks require finite discrete sample spaces. Continuous numeric attributes (`age`, `balance`, `day`, `campaign`, `pdays`, `previous`) are converted into discrete quantile bins using `BankPreprocessor`.
- **Training-Only Fitting:** Bin split edges and known categories are fitted strictly on $X_{\text{train}}$ to avoid information leakage.
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
- **Decision Rule:** Maximum A Posteriori (MAP) classification thresholded at $0.50$.
- **Performance Optimization:** Inference is cached over unique binned test configurations, reducing inference runtime from minutes to seconds.

---

## 5. Methodology: Part B — Constrained Rule-Based Classifier

### 5.1 Formulation and Decision Logic
The rule-based model was designed by examining category subscription rates on the **training split only** ($36,168$ records):
1. **Baseline Population Rate:** $11.7\%$ subscription rate across all clients.
2. **Prior Campaign Success (`poutcome == 'success'`):** Yields a **$64.6\%$** positive rate ($778$ deposits out of $1,205$ clients in training).
3. **Shoulder Calendar Months (`month` $\in$ `['mar', 'sep', 'oct', 'dec']`):** Yield a **$44.0\% - 50.9\%$** positive rate (compared to $\le 20\%$ for other months).
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
  - Branching statements: Exactly **$2$** (`if` and `elif`). A trailing `else` is the default fallthrough branch and not a condition.
  - Return statements (decision rules): **$3$** (`return "yes"`, `return "yes"`, `return "no"`).
- **Compliance Proof:**
  - Number of attributes used by the model: $n = 2$ (`poutcome`, `month`).
  - Total dataset features available: $N = 15$ ($16$ including duration).
  - **Result:** $2 \text{ branches} \le 2 \text{ attributes used} \le 15 \text{ dataset attributes}$.
  - The classifier complies under both the strict interpretation ($n = \text{attributes accessed}$) and the broad interpretation ($n = \text{dataset attributes}$).

---

## 6. Experimental Methodology & Evaluation

### 6.1 Experimental Protocol
- **Stratified Partitioning:** $80\%$ Training ($36,168$ rows) and $20\%$ Held-Out Testing ($9,043$ rows), seeded with `random_state = 42`.
- **Identical Test Set:** Both models were evaluated on the exact same uncorrupted test partition.
- **Positive Label:** Subscription (`"yes"`) is explicitly designated as the positive class for all precision, recall, and F1 calculations (`pos_label="yes"`).

### 6.2 Empirical Results

| Classifier | Accuracy | Precision | Recall | F1-Score | True Neg (TN) | False Pos (FP) | False Neg (FN) | True Pos (TP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rule-Based Classifier** | **88.82%** | **53.74%** | **31.95%** | **0.4007** | 7,694 | 291 | 720 | **338** |
| **Bayesian Network** | **89.24%** | **63.00%** | **19.47%** | **0.2975** | **7,864** | **121** | 852 | 206 |
| **Majority Baseline** | 88.30% | 0.00% | 0.00% | 0.0000 | 7,985 | 0 | 1,058 | 0 |

### 6.3 Confusion Matrices (Held-Out Test Set: $N = 9,043$)

```
Bayesian Network                       Rule-Based Classifier
                 Predicted                              Predicted
                 no     yes                              no     yes
Actual  no    [[ 7864,  121 ],         Actual  no    [[ 7694,  291 ],
        yes    [  852,  206 ]]                 yes    [  720,  338 ]]
```

### 6.4 Scientific Interpretation

1. **Why the Rule-Based Classifier Achieved a Higher F1-Score ($0.4007$ vs. $0.2975$):**
   - The Bank Marketing dataset is heavily imbalanced ($88.3\%$ negative). 
   - Generative probabilistic models like Bayesian Networks estimate the full joint distribution $P(\mathbf{X}, Y)$. Because the prior probability $P(Y = \text{'yes'}) = 0.117$ is low, the posterior $P(Y = \text{'yes'} \mid \mathbf{e})$ rarely exceeds the standard $0.50$ MAP threshold, resulting in very low recall ($19.47\%$).
   - The Rule-Based Classifier specifically targets the two high-density positive pockets (`poutcome = 'success'` and high-yield months), yielding a substantially higher recall ($31.95\%$) and discovering **$338$ subscribers** versus **$206$ subscribers** for the Bayesian Network.

2. **Precision vs. Recall Trade-off:**
   - The Bayesian Network provides higher precision ($63.00\%$ vs. $53.74\%$). When it predicts `"yes"`, it is correct nearly two-thirds of the time.
   - The Rule-Based Classifier accepts slightly more false positives ($291$ vs. $121$) to capture $64\%$ more actual depositors ($338$ vs $206$), which is advantageous in telemarketing where missed conversions are costly.

3. **Structural Alignment:**
   - Both classifiers independently isolated `month` and `poutcome` as the primary predictive signals. Hill Climb Search selected them as parents of $y$ without human intervention.

---

## 7. Conclusions, Limitations, and Future Improvements

### 7.1 Conclusions
- An interpretable, 2-branch deterministic rule set can match and outperform a Bayesian Network in F1-score on imbalanced tabular data.
- Transparency and auditability can be achieved without sacrificing diagnostic performance.
- The assignment's branching limit ($\le n$) forces disciplined regularization, preventing overfitting.

### 7.2 Limitations
- **Discrete Quantization Loss:** Coarse quantile binning of continuous attributes (`age`, `balance`) discards granular non-linear relationships.
- **Fixed MAP Threshold:** The Bayesian Network's default $0.50$ classification cutoff is suboptimal for an $11.7\%$ imbalanced class distribution.

### 7.3 Possible Improvements
- **Decision Threshold Optimization:** Calibrating the Bayesian Network's decision threshold (e.g., using precision-recall curve analysis at threshold $\tau \approx 0.25$) would increase recall.
- **Continuous Bayesian Networks:** Employing Gaussian or Copula Bayesian Networks to model numerical attributes without discretization loss.
- **Cost-Sensitive Loss Matrix:** Incorporating asymmetric financial costs (e.g., cost of dialing vs. value of secured deposit).

---

## 8. Instructions to Launch and Reproduce

### 8.1 Automated Unit Tests
Verify the entire test suite ($31$ automated tests covering preprocessing, model service, rule compliance, and metrics):
```powershell
pytest
```

### 8.2 Reproducing the Experiment (CLI Pipeline)
Execute the complete end-to-end pipeline, saving metrics, plots, and reports to `results/`:
```powershell
python -m src.main
# or via the unified launcher:
python run_app.py --cli
```

### 8.3 Launching the Native Windows Desktop GUI (Recommended)
Run the native desktop application (Tkinter/ttk window, no web browser required):
```powershell
python desktop_app.py
# or
python run_app.py
```

### 8.4 Launching the Standalone Windows Executable (.exe)
Double-click or run the pre-compiled binary:
```powershell
.\dist\BankMarketingClassifier\BankMarketingClassifier.exe
```

### 8.5 Launching the Web Dashboard (Streamlit)
```powershell
python -m streamlit run app.py
```
