# Bayesian Network vs. Rule-Based Classification — UCI Bank Marketing

A complete, beginner-friendly, and educational Python 3.13 machine learning project comparing a
probabilistic **Bayesian Network** against a transparent **Rule-Based Classifier** operating under
strict branching-statement constraints on the UCI Bank Marketing dataset.

Includes both a **Command-Line Interface (CLI)** and an interactive **Graphical User Interface (GUI)**
built with **Streamlit**, with native support for standalone **Windows Executable (.exe)** packaging.

---

## 1. Project Objective and Assignment Requirements

The assignment investigates whether a simple rule-based approach can match or exceed a Bayesian Network's
classification performance:

- **Part A — Machine Learning:** Implement a discrete Bayesian Network classifier using an established
  open-source library (*pgmpy*). Stages include data loading, preprocessing/discretization, structure learning,
  parameter estimation (CPTs), exact probabilistic inference (Variable Elimination), and held-out test evaluation.
- **Part B — Rule-Based Classification:** Implement an explicit, transparent branching classifier
  (`if/elif/else`). The classifier must use **no more than *n* branching statements**, where *n* is the number
  of input attributes actually used. Compliance is verified through static Abstract Syntax Tree (AST) analysis.
- **Fair Experimental Evaluation:** Both classifiers are evaluated on the exact same held-out test records
  using identical metrics: Accuracy, Precision, Recall, F1-score, and Confusion Matrices, with subscription (`yes`)
  explicitly configured as the positive class.
- **Educational Graphical Interface:** An interactive Streamlit application with dedicated pages for model
  comparison, Bayesian Network inspection, rule execution tracing, and dataset exploration.

---

## 2. Dataset and Target Definition

- **Source:** [UCI Bank Marketing Dataset](https://archive.ics.uci.edu/dataset/222/bank%2Bmarketing)
- **File:** `bank-full.csv` (45,211 records, 16 input attributes + target)
- **Storage:** Placed in `1_Dataset/bank-full.csv` (git-ignored, not committed to version control).
- **Automatic Download:** If the CSV file is not present locally, `1_Dataset/data_loader.py` automatically downloads
  and extracts it from the official UCI archive upon first run.
- **Manual Download Instructions:**
  1. Open `https://archive.ics.uci.edu/dataset/222/bank%2Bmarketing` and download the ZIP file.
  2. Unzip `bank.zip` inside the archive.
  3. Place `bank-full.csv` directly into the `1_Dataset/` folder.
- **Target `y`:** Binary indicator of whether the client subscribed to a term deposit:
  - `yes`: Positive class (5,289 instances, **11.7%**)
  - `no`: Negative class (39,922 instances, **88.3%**)
- **Target Leakage Prevention (`duration` exclusion):**
  The `duration` attribute represents the duration of the current telephone contact in seconds.
  In a realistic bank telemarketing deployment, the duration of a call is completely unknown before the
  call is initiated. Furthermore, call duration is heavily confounded with outcome (longer calls usually mean
  the customer agreed). Including `duration` would introduce severe target leakage. Therefore, `duration`
  is **strictly excluded** from all training and inference pipelines in both classifiers.
- **15 Selected Input Features:**
  - *Categorical (9):* `job`, `marital`, `education`, `default`, `housing`, `loan`, `contact`, `month`, `poutcome`
  - *Numerical (6):* `age`, `balance`, `day`, `campaign`, `pdays`, `previous`

---

## 3. Project Structure

```
CISE_Project1/
├── app.py                           # Main Streamlit GUI entry point
├── requirements.txt                 # Pinned dependencies for Python 3.13
├── README.md                        # Comprehensive educational documentation
├── .gitignore                       # Excludes dataset, results, cache, and virtual environment
├── 1_Dataset/
│   ├── bank-full.csv                # Raw UCI dataset (auto-downloaded, git-ignored)
│   └── data_loader.py               # Download, loading, and dataset inspection module
├── 2_BayesianNetworkClassification/
│   └── bayesian_network.py          # Part A: DAG learning, BDeu parameter estimation, inference
├── 3_RuleBasedClassification/
│   ├── rule_based.py                # Part B: Transparent 2-branch classification logic
│   └── branch_counter.py            # AST-based static analysis verifying branch limits
├── pages/
│   ├── 1_Overview.py                # Page 1: Comparative dashboard and evaluation findings
│   ├── 2_Bayesian_Network.py        # Page 2: BN config, training, DAG viz, CPTs, single inference
│   ├── 3_Rule_Based.py              # Page 3: Rule specs, AST verification, execution trace
│   └── 4_Dataset_Explorer.py        # Page 4: Raw dataset viewer, distributions, missing values
├── src/
│   ├── __init__.py
│   ├── config.py                    # Global paths, features, random seeds, and sys.path setup
│   ├── preprocessing.py             # Quantile discretizer & category handling (train-fitted only)
│   ├── evaluation.py                # Binary metrics, comparison tables, confusion matrices
│   ├── execution_log.py             # Reusable execution event logger for transparency
│   ├── model_service.py             # Service coordinating training, state, and cache invalidation
│   └── ui_helpers.py                # Streamlit CSS, custom metric cards, and plotting helpers
├── tests/
│   ├── conftest.py                  # Pytest configuration and path resolution
│   ├── test_preprocessing.py        # Tests for discretizer, category consistency, and edge cases
│   ├── test_rule_based.py           # Tests for rule logic, label validity, and branch compliance
│   ├── test_evaluation.py           # Tests for metrics calculation with positive label 'yes'
│   └── test_model_service.py        # Tests for service state, cache invalidation, and GUI imports
└── results/
    ├── .gitkeep
    ├── dataset_report.txt           # Pre-inspection dataset telemetry
    ├── network_description.txt      # Learned DAG nodes, edges, Markov blanket, and CPT of y
    ├── network_structure.png        # Rendered DAG graph diagram
    ├── metrics.csv                  # Evaluation metrics for BN, Rules, and Baseline
    ├── test_predictions.csv         # Row-by-row test predictions and posterior probabilities
    ├── confusion_bayesian_network.png
    ├── confusion_rule-based.png
    └── confusion_majority_baseline.png
```

---

## 4. Setup and Installation (Python 3.13)

### macOS / Linux
```bash
# 1. Create a Python 3.13 virtual environment
python3.13 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell
```powershell
# 1. Create a Python 3.13 virtual environment
py -3.13 -m venv .venv

# 2. Activate the virtual environment
.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Execution Commands

### Launch the Native Windows Desktop Application (GUI)
Run the pure native desktop GUI (Tkinter/ttk window, no web browser required):
```powershell
python desktop_app.py
# or via the unified runner:
python run_app.py
```
This opens a standalone desktop application window with tabs for model comparison, Bayesian network training/inference, rule-based execution tracing, and dataset inspection.

### Launch the Web Browser Dashboard (Streamlit - Optional)
If you prefer the web dashboard inside your web browser:
```powershell
python run_app.py --web
# or
python -m streamlit run app.py
```

### Run the Command-Line Experiment (CLI)
To run the full end-to-end experiment directly in the terminal:
```powershell
python run_app.py --cli
# or
python -m src.main
```
This command loads the data, fits preprocessing, trains the Bayesian Network, evaluates both models,
prints comparison tables to the console, and saves all metrics, logs, and plots into `results/`.

### Run Automated Tests
Execute all 31 unit tests without requiring the full dataset download:
```powershell
pytest
```

---

## 5.1 Standalone Application Builders (Windows & macOS)

The project provides dedicated, automated PyInstaller packaging scripts for both operating systems so users can build the application for their native machine.

### A. Windows Executable Build (.exe)
Run the automated Windows build script:
```powershell
python build_exe.py
```
This invokes PyInstaller using `BankMarketingClassifier.spec` and outputs to `dist/BankMarketingClassifier/`:
- **Native Desktop GUI:** Double-click `dist\BankMarketingClassifier\BankMarketingClassifier.exe`
- **CLI Pipeline:** `.\dist\BankMarketingClassifier\BankMarketingClassifier.exe --cli`
- **Web Dashboard:** `.\dist\BankMarketingClassifier\BankMarketingClassifier.exe --web`

### B. macOS Application Build (.app & Unix Binary)
Run the automated macOS build script on your MacBook:
```bash
python build_mac.py
```
This invokes PyInstaller using `BankMarketingClassifier_mac.spec` and outputs:
- **Native macOS Application Bundle (`.app`):** `dist/BankMarketingClassifier.app`
  - Double-click `BankMarketingClassifier.app` in Finder, or run:
    ```bash
    open dist/BankMarketingClassifier.app
    ```
- **Standalone Terminal Binary:** `dist/BankMarketingClassifier/BankMarketingClassifier`
  - CLI Experiment Pipeline:
    ```bash
    ./dist/BankMarketingClassifier/BankMarketingClassifier --cli
    ```
  - Interactive Web GUI:
    ```bash
    ./dist/BankMarketingClassifier/BankMarketingClassifier --web
    ```

> [!NOTE]
> When transferring `BankMarketingClassifier.app` to another Mac without an Apple Developer ID signature, macOS Gatekeeper may display a prompt. Clear the quarantine flag with:
> `xattr -cr dist/BankMarketingClassifier.app`

---

## 6. Navigating the Streamlit GUI Pages

### Page 1 — Overview / Model Comparison (`pages/1_Overview.py`)
- **Top Metrics:** Displays total records (45,211), input attributes (15), positive class frequency (11.7%), and train/test counts.
- **Evaluation Table:** Compares Accuracy, Precision, Recall, F1-score, and raw counts (TP, FP, FN, TN) side by side.
- **Bar Charts:** Visualizes metric trade-offs between the Bayesian Network, Rule-Based Classifier, and Majority Baseline.
- **Confusion Matrices:** Side-by-side heatmaps illustrating true/false positives and negatives.
- **Live Training Button:** Allows retraining the models directly if not already cached in memory.

### Page 2 — Bayesian Network (`pages/2_Bayesian_Network.py`)
- **A. Model Configuration:** Safe hyper-parameter controls (test size fraction, random seed, max in-degree parents, BDeu equivalent sample size, quantile bin counts). *Changing any setting automatically invalidates stale model artifacts and prompts for retraining.*
- **B. Training Execution:** Click **"Train Bayesian Network"** to trigger live training. Displays active execution stages (1/8 to 8/8), stage timers, and total duration.
- **C. Network Visualization & Node Inspector:** Displays the learned DAG layout (target `y` highlighted in red). The **Node Inspector** lets you select any node to view its parents, children, in/out degrees, and **Markov Blanket**.
- **D. Conditional Probability Tables:** Inspect CPTs for any chosen variable with an explanation of parent-conditioned states and BDeu smoothing.
- **E. Single Client Inference:** Fill in client features using interactive sliders and dropdowns. The app applies the exact training discretizer, runs Variable Elimination, outputs the MAP class, shows exact posterior probabilities $P(y=\text{yes}|\mathbf{e})$ and $P(y=\text{no}|\mathbf{e})$, and displays the evidence fed into the network.
- **F. Execution Details:** Expandable telemetry showing per-stage execution times, learned DAG edges, and numerical discretization cutoffs.

### Page 3 — Rule-Based Classifier (`pages/3_Rule_Based.py`)
- **A. Rule Inspection:** Clear table detailing Rule 1, Rule 2, and the Fallback Default Rule, accompanied by complete source code.
- **B. Branching Constraint Verification:** Displays the input attributes used ($n=2$), permitted branching limit ($n=2$), and actual branch count ($2$). Confirms compliance via static AST inspection.
- **C. Interactive Classification & Execution Trace:** Test client profiles with real-time condition evaluation. Displays the step-by-step trace showing which conditions evaluated to `True` or `False` and which rule triggered.
- **D. Test Evaluation:** Displays held-out test metrics and confusion matrix for the rule-based model.

### Page 4 — Dataset Explorer (`pages/4_Dataset_Explorer.py`)
- **Preview & Metadata:** View 100 randomly sampled rows and complete attribute schema.
- **Target Distribution:** Bar chart showing class imbalance (11.7% yes vs. 88.3% no).
- **Feature Deep-Dive:** Select any feature to view statistical summaries, distribution histograms, and empirical deposit rates.
- **Raw vs. Discretized Representation:** Side-by-side table comparing continuous features against their discrete quantile states.
- **Missing & Special Values:** Quantifies the `unknown` string marker across categorical fields, `pdays = -1` (never contacted before), and negative balances.

---

## 7. Algorithms and Theoretical Foundations

### Part A — Bayesian Network Step-by-Step

A **Bayesian Network** is a probabilistic graphical model representing a set of variables and their conditional
dependencies via a Directed Acyclic Graph (DAG) and Conditional Probability Tables (CPTs).

1. **Nodes and Edges:**
   - **Nodes:** Random variables (the 15 input features + target $y$).
   - **Directed Edges ($A \rightarrow B$):** Statistical dependencies between parent $A$ and child $B$.
   - **Markov Blanket of $y$:** The set of variables containing $y$'s parents, children, and spouses (other parents
     of $y$'s children). Given its Markov blanket (`contact, marital, month, poutcome`), $y$ is conditionally
     independent of all other nodes in the network.
2. **Structure Learning (Hill Climb Search with BIC):**
   - The graph topology is learned from training data using `HillClimbSearch`.
   - Score function: **Bayesian Information Criterion (BIC)**:
     $$\text{BIC}(G) = \ln P(D | \hat{\theta}, G) - \frac{\text{dim}(G)}{2} \ln N$$
     The first term measures log-likelihood fit to data; the second penalizes network complexity ($\text{dim}(G)$).
   - Local greedy search starts from an empty graph, evaluating edge additions, removals, and reversals up to
     `max_indegree=3` until no move improves the score.
3. **Parameter Estimation (BDeu Prior Smoothing):**
   - For each node $X_i$ with parents $\text{Pa}(X_i)$, the CPT entries are estimated:
     $$P(X_i = k \mid \text{Pa}(X_i) = j) = \frac{N_{ijk} + \alpha_{ijk}}{N_{ij} + \alpha_{ij}}$$
   - Using the **BDeu prior** with equivalent sample size $N' = 5$, uniform pseudo-counts $\alpha_{ijk}$ are added.
     This ensures no conditional probability is ever zero, preventing division-by-zero during inference on rare cases.
4. **Exact Probabilistic Inference (Variable Elimination):**
   - When evidence $\mathbf{e}$ (observed feature values) is supplied, exact posterior marginals are computed:
     $$P(y \mid \mathbf{e}) = \frac{P(y, \mathbf{e})}{P(\mathbf{e})} = \frac{\sum_{\mathbf{Z}} \prod_{i} P(X_i \mid \text{Pa}(X_i))}{\sum_{y} \sum_{\mathbf{Z}} \prod_{i} P(X_i \mid \text{Pa}(X_i))}$$
     where $\mathbf{Z}$ are hidden variables eliminated sequentially using a greedy elimination order.
   - Classification decision: If $P(y=\text{yes} \mid \mathbf{e}) \ge 0.50$, predict `yes`; otherwise `no`.

#### Small Illustrative Example (Hypothetical, Non-Bank Data)
Consider a toy medical diagnostic network with two symptoms: $\text{Flu} \rightarrow \text{Fever}$ and $\text{Flu} \rightarrow \text{Cough}$:
- Prior: $P(\text{Flu}=\text{yes}) = 0.10$
- CPTs:
  - $P(\text{Fever}=\text{yes} \mid \text{Flu}=\text{yes}) = 0.80$, $P(\text{Fever}=\text{yes} \mid \text{Flu}=\text{no}) = 0.10$
  - $P(\text{Cough}=\text{yes} \mid \text{Flu}=\text{yes}) = 0.70$, $P(\text{Cough}=\text{yes} \mid \text{Flu}=\text{no}) = 0.20$

If a patient exhibits evidence $\mathbf{e} = \{\text{Fever}=\text{yes}, \text{Cough}=\text{yes}\}$:
- Unnormalized joint for Flu=yes: $0.10 \times 0.80 \times 0.70 = 0.056$
- Unnormalized joint for Flu=no: $0.90 \times 0.10 \times 0.20 = 0.018$
- Total evidence: $0.056 + 0.018 = 0.074$
- Normalized posterior:
  $$P(\text{Flu}=\text{yes} \mid \text{Fever}, \text{Cough}) = \frac{0.056}{0.074} \approx 0.757 \quad (75.7\%)$$

---

### Part B — Rule-Based Classifier and Branching Limit

The rule-based classifier (`3_RuleBasedClassification/rule_based.py`) implements transparent decision logic:
```python
def classify_client(record: dict) -> str:
    if record["poutcome"] == "success":
        return "yes"                      # Rule 1
    elif record["month"] in ("mar", "sep", "oct", "dec"):
        return "yes"                      # Rule 2
    else:
        return "no"                       # Rule 3 (Default majority class)
```

1. **How the Rules Were Formulated (Training Split Only):**
   - In the training set, overall deposit rate is **11.7%**.
   - `poutcome == 'success'`: **64.6%** subscription rate (1,205 clients). This represents clients whose previous
     campaign resulted in a deposit.
   - `month in ('mar', 'sep', 'oct', 'dec')`: Shoulder months with low overall call volumes but high response rates
     (March: 50.9%, December: 47.2%, September: 45.2%, October: 43.8%). On the training split, adding this rule
     raised the positive-class F1 from 0.287 to 0.386.
   - All other records fall through to the default class (`no`).
2. **Branching Constraint Verification:**
   - **Attributes used ($n$):** 2 (`poutcome`, `month`).
   - **Allowed branching statements:** At most 2.
   - **Actual branching statements:** Exactly 2 (one `if` and one `elif`).
   - *Note on Rules vs. Branches:* There are 3 decision paths / return statements (Rules 1, 2, and Default),
     but only 2 branching conditions. The `else` clause is not a separate condition.
   - **AST Verification:** `3_RuleBasedClassification/branch_counter.py` parses the entire Python file using
     `ast.walk(ast.parse(source))`, counting all `ast.If`, `ast.IfExp` (ternary), `ast.match_case`, and comprehension filters.
     This ensures branches cannot be hidden in helper functions or dynamic code.

---

## 8. Experimental Evaluation and Verified Results

Both models were evaluated on the exact same 9,043 held-out test instances (80/20 stratified split, seed=42):

| Classifier | Accuracy | Precision (`yes`) | Recall (`yes`) | F1-Score (`yes`) | True Pos (TP) | False Pos (FP) | False Neg (FN) | True Neg (TN) |
|---|---|---|---|---|---|---|---|---|
| **Bayesian Network** | **0.8924** | **0.6300** | 0.1947 | 0.2975 | 206 | **121** | 852 | **7,864** |
| **Rule-Based (2 branches)** | 0.8882 | 0.5374 | **0.3195** | **0.4007** | **338** | 291 | **720** | 7,694 |
| **Majority Baseline (ref)** | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 1,058 | 7,985 |

*(Verified results generated by `python -m src.main` and saved in `results/metrics.csv`)*

### Factual Interpretation of Results
- **Accuracy is Not Enough:** The majority baseline gets 88.30% accuracy simply by predicting `no` for everyone.
  The BN (89.24%) and Rule-Based (88.82%) appear only slightly higher.
- **Precision vs. Recall Trade-Off:**
  - The **Bayesian Network** is more conservative: it achieves higher precision (63.0% vs 53.7%) and produces fewer
    false alarms (121 vs 291), but misses over 80% of actual subscribers (recall 19.5%).
  - The **Rule-Based Classifier** achieves significantly higher recall (31.95% vs 19.47%) and a higher F1-score
    (0.4007 vs 0.2975), discovering 338 actual subscribers compared to the BN's 206.
- **Answer to the Research Question:** Can a simple rule-based approach match or exceed the Bayesian Network?
  *Yes, on Recall and F1-score, while matching it on Accuracy within 0.4 percentage points.* However, the Bayesian
  Network retains an advantage in Precision. Which model is preferable in practice depends on whether the bank
  prioritizes minimizing wasted telemarketing calls (BN) or maximizing total deposit acquisitions (Rule-Based).

---

## 9. Testing and Quality Assurance

The test suite contains **31 automated tests** across 4 modules:
```bash
pytest -v
```

1. `tests/test_preprocessing.py`:
   - Validates stratified splitting and leak-free separation (ensures `y` and `duration` are never in feature set).
   - Validates quantile binning on training data only.
   - Verifies handling of unseen categories and boundary values.
   - Verifies special handling of `pdays = -1`.
2. `tests/test_rule_based.py`:
   - Verifies known rule classifications.
   - Verifies that `branch_counter.py` accurately detects `if`, `elif`, ternary expressions, and match cases.
   - Confirms that the actual classifier complies with the branching constraint ($2 \le 2$).
3. `tests/test_evaluation.py`:
   - Verifies binary metric calculations with `pos_label='yes'`.
   - Confirms zero-division handling for precision/recall.
   - Validates confusion matrix generation and CSV serialization.
4. `tests/test_model_service.py`:
   - Verifies deterministic signature calculation and cache invalidation upon hyper-parameter modification.
   - Verifies single-instance probabilistic inference on small synthetic networks.
   - Confirms that all core modules can be imported cleanly by the Streamlit GUI.

---

## 10. Known Technical Limitations and Assumptions

1. **Information Loss from Discretization:** The discrete Bayesian Network requires partitioning continuous variables
   into quantile bins. This loses fine-grained numerical gradients.
2. **Local Optima in Structure Learning:** `HillClimbSearch` performs greedy local search and can terminate at local
   score maxima. Alternative search paradigms (e.g., Tree-Augmented Naive Bayes or PC algorithm) were not compared.
3. **Fixed Probability Threshold:** The Bayesian Network uses the standard 0.50 MAP decision threshold. Because the
   dataset is imbalanced, predicted probabilities for `yes` are naturally depressed. Tuning the decision threshold
   on a validation set could improve BN recall.
4. **Single Train/Test Split:** Results reflect a single 80/20 stratified split (`seed=42`). K-fold cross-validation
   would yield confidence intervals.
5. **Seasonal Dependence of Calendar Rules:** The rule-based classifier relies on historical high-response months
   (March, September, October, December) observed in the 2008–2010 Portuguese bank dataset. These seasonal patterns
   may not generalize to other institutions or economic climates.
