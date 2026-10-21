# Bayesian Networks vs. Rule-Based Classification

Computational Intelligence in Software Engineering — Project Presentation

## 1. Objective

Compare two approaches for predicting whether a bank customer subscribes to a term deposit:

- **Part A:** Discrete Bayesian Network implemented with `pgmpy`.
- **Part B:** Rule-Based Classifier constrained by the assignment's branching-statement limit (≤ *n* branches for *n* input attributes used).
- **Baseline:** Majority-class classifier predicting `no` for all clients.

Both models are evaluated via two complementary regimes:
1. The original **80/20 stratified held-out test split** (9,043 test records).
2. **Stratified 5-Fold Cross-Validation** (evaluating all 45,211 records out-of-sample with zero data leakage).

## 2. Dataset and Technologies

- **Dataset:** UCI Bank Marketing — 45,211 records.
- **Target:** `y` (`yes` / `no`).
- **Class distribution:** 11.7% subscribers (`yes`) and 88.3% non-subscribers (`no`).
- **Input features:** 15, excluding `duration` to prevent target leakage (duration is only known after the call concludes and outcome is determined).
- **Technologies:** Python 3.13, pgmpy, pandas, scikit-learn, Streamlit, Tkinter, Matplotlib, NetworkX, Seaborn, and pytest.

## 3. Methodology

### Bayesian Network (Part A)

The model represents probabilistic dependencies between variables using a directed acyclic graph (DAG):

1. **Discretization:** Numeric features are partitioned into quantile bins; categorical categories are fixed based on training data.
2. **Structure Learning:** Hill Climb Search with Bayesian Information Criterion (BIC) score learns the DAG structure from scratch.
3. **Parameter Estimation:** Conditional Probability Tables (CPTs) are estimated using a Bayesian estimator with BDeu Dirichlet prior smoothing to prevent zero-probability inference failures.
4. **Exact Inference:** Variable Elimination computes posterior $P(y = \text{'yes'} \mid \text{evidence})$.
5. **Decision:** Clients are classified as `yes` if $P(y = \text{'yes'} \mid \text{evidence}) \ge \tau$ (default MAP threshold $\tau = 0.50$).

### Rule-Based Classifier (Part B)

The classifier uses two explicit branching statements based on the two most predictive attributes discovered in the training data:

```python
def classify_client(record: dict) -> str:
    if record["poutcome"] == "success":
        return "yes"                      # Rule 1: Previous campaign succeeded
    elif record["month"] in ("mar", "sep", "oct", "dec"):
        return "yes"                      # Rule 2: Contacted in shoulder high-response month
    else:
        return "no"                       # Rule 3: Default majority class
```

- **Branching Constraint:** 2 input attributes read (`poutcome`, `month`), 2 branching statements (`if`, `elif`).
- **Verification:** Automatically validated via AST parsing by `branch_counter.py` and test suites.

---

### Stratified 5-Fold Cross-Validation

#### Why Cross-Validation is Useful

A single train/test split (e.g. 80/20) provides an evaluation on only one random partition. If that partition happens to contain an unusually easy or difficult sample, reported metrics may be overly optimistic or pessimistic.

**Stratified 5-Fold Cross-Validation** addresses this by:
1. Partitioning the entire dataset into 5 equal-sized folds while preserving the 11.7% / 88.3% class ratio in every fold.
2. Training on 4 folds (80%) and validating on the remaining fold (20%), cycling 5 times.
3. Evaluating every single record in the dataset exactly once as an unseen validation instance.
4. Measuring both the **mean** (expected performance) and **standard deviation** (stability/variance across data splits).

#### Strict Leakage Prevention Inside Each Fold

A common error in machine learning is performing preprocessing or feature selection on the whole dataset before cross-validation. This leaks information from validation folds into training.

In this project, data leakage is strictly prevented:
- **Independent Preprocessing:** Quantile bin edges and category vocabularies are learned solely from the training fold (4/5). Unseen categories in the validation fold are mapped to the training fold's most frequent category without refitting.
- **Independent Structure Learning:** The Bayesian Network DAG is learned from scratch using Hill Climb Search solely on the training fold. No network structure is carried over across folds.
- **Independent Parameter Estimation:** CPTs are estimated strictly from training fold counts.
- **Identical Evaluation:** The Rule-Based classifier and majority baseline are evaluated on the exact same validation records in each fold.

#### Interpreting Mean and Standard Deviation

- **Mean ($\mu$):** The average metric value across the 5 folds: $\mu = \frac{1}{K} \sum_{k=1}^K m_k$. It represents the expected performance on new, unseen data drawn from the same distribution.
- **Sample Standard Deviation ($\sigma$, with $ddof=1$):** Measures the variability of model performance across different training/validation partitions: $\sigma = \sqrt{\frac{1}{K-1} \sum_{k=1}^K (m_k - \mu)^2}$.
  - A low $\sigma$ (e.g. $\sigma < 0.02$) demonstrates that model performance is robust and not an artifact of a lucky split.
  - A high $\sigma$ indicates sensitivity to training set composition.

#### Distinguishing Fold-Level Means from Out-of-Fold (OOF) Pooled Metrics

This project explicitly distinguishes between two complementary aggregations:
1. **Fold-Level Mean (± Std):** Average of the metric scores computed independently on each validation slice. Reflects split-to-split variance.
2. **Out-of-Fold Pooled Metrics:** All 5 validation prediction slices are concatenated to form a complete out-of-fold prediction vector for all 45,211 records. Precision, recall, and F1 are then calculated globally from the pooled confusion matrix ($\sum TP / (\sum TP + \sum FP)$).
3. *Why they differ:* Non-linear metrics like F1 and Precision are non-linear ratios; the mean of ratios is not strictly equal to the ratio of totals (Jensen's inequality). Both are reported for full scientific transparency.

---

## 4. Experimental Results

### Regime A: Stratified 5-Fold Cross-Validation (Full Dataset, N = 45,211)

The following reproducible results were obtained from the leak-free 5-fold cross-validation pipeline (`random_state=42`):

#### 1. Fold-Level Summary (Mean ± Standard Deviation)

| Classifier | Accuracy | Precision (`yes`) | Recall (`yes`) | F1-Score (`yes`) | Total TP | Total FP | Total FN | Total TN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bayesian Network** ($\tau=0.50$) | **89.24% ± 0.19%** | **62.00% ± 1.56%** | 20.63% ± 2.47% | 30.91% ± 3.00% | 1,091 | 666 | 4,198 | 39,256 |
| **Rule-Based** (2 branches) | 88.60% ± 0.14% | 52.17% ± 0.96% | **31.03% ± 1.39%** | **38.90% ± 1.30%** | **1,641** | 1,504 | 3,648 | 38,418 |
| **Majority Baseline** (reference) | 88.30% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | 0.00% ± 0.00% | 0 | 0 | 5,289 | 39,922 |

#### 2. Out-of-Fold Pooled Metrics (Concatenated across all 45,211 instances)

| Classifier | Pooled Accuracy | Pooled Precision | Pooled Recall | Pooled F1-score |
| :--- | :---: | :---: | :---: | :---: |
| **Bayesian Network** | 89.24% | 62.09% | 20.63% | 0.3097 |
| **Rule-Based** | 88.60% | 52.18% | 31.03% | 0.3891 |
| **Majority Baseline** | 88.30% | 0.00% | 0.00% | 0.0000 |

Total Cross-Validation runtime: **15.72 seconds** (~3.14s per fold).

---

### Regime B: Held-Out Test Set (Single 80/20 Split, 9,043 Records)

| Classifier | Accuracy | Precision | Recall | F1-score |
| :--- | :---: | :---: | :---: | :---: |
| **Rule-Based** | 88.82% | 53.74% | 31.95% | 0.4007 |
| **Bayesian Network** ($\tau = 0.50$) | 89.24% | 63.00% | 19.47% | 0.2975 |
| **Bayesian Network** (calibrated $\tau^* = 0.21$) | 87.47% | 45.91% | 39.79% | 0.4263 |
| **Majority Baseline** | 88.30% | 0.00% | 0.00% | 0.0000 |

---

### Interpretation and Key Findings

1. **Cross-Validation Confirms Model Stability:**
   The low standard deviations across the 5 folds ($\sigma_{F1} = 0.030$ for BN, $\sigma_{F1} = 0.013$ for Rule-Based) confirm that the differences observed between the two classifiers are statistically consistent properties of the models, not random artifacts of a single split.

2. **Precision vs. Recall Trade-Off:**
   - **Bayesian Network:** Achieves higher precision (62.0% vs 52.2%) and higher accuracy (89.24% vs 88.60%). It produces far fewer false alarms (666 FP vs 1,504 FP across all 45,211 clients), making it optimal when contacting a client is costly.
   - **Rule-Based Classifier:** Achieves significantly higher recall (31.0% vs 20.6%) and a higher F1-score (0.389 vs 0.309). It successfully identifies 1,641 subscribers compared to 1,091 identified by the default Bayesian Network.

3. **Accuracy is Deceptive on Imbalanced Datasets:**
   Because 88.3% of clients decline deposits, predicting `no` for every client achieves 88.30% accuracy with zero predictive utility (0 TP). Both models achieve ~89% accuracy, but their value lies in positive-class detection (Precision, Recall, F1).

4. **Constraint Compliance:**
   The Rule-Based classifier adheres strictly to the assignment's branching limit (≤ 2 branches for 2 attributes). It outperforms the default Bayesian Network in F1-score while maintaining total transparency and sub-millisecond inference.

---

## 5. Application and Reproducibility

### Automated Test Suite

Run all 44 unit and integration tests (including cross-validation leakage, fold partitioning, stratification, and AST branch-count compliance tests):

```bash
pytest
```

### Command-Line Interface (CLI)

The CLI supports both evaluation modes:

```bash
# 1. Run Stratified 5-Fold Cross-Validation (saves cv_*.csv and cv_comparison.png)
python -m src.main --cv

# 2. Run Held-out 80/20 Test Evaluation (saves metrics.csv and test_predictions.csv)
python -m src.main --heldout

# 3. Run Both Evaluations Sequentially
python -m src.main --all
```

### Interactive Web Application (Streamlit GUI)

Launch the multi-page Streamlit application:

```bash
python -m streamlit run app.py
```

- **Page 1 (Overview):** Displays both held-out evaluation and a dedicated **Stratified 5-Fold Cross-Validation Dashboard** with Mean ± Std metrics, comparison plots with error bars, fold breakdown tables, and pooled confusion matrices.
- **Page 2 (Bayesian Network):** Interactive DAG visualizer, Node Inspector, CPT browser, and single-client probabilistic inference.
- **Page 3 (Rule-Based Classifier):** Rule breakdown, AST constraint verifier, and single-client step-by-step execution traces.
- **Page 4 (Dataset Explorer):** Feature distributions, unknown value inspection, and deposit rate correlations.

### Desktop GUI (Tkinter)

```bash
python desktop_app.py
```

### Standalone Executable Builds

- **Windows Build (.exe):** `python build_exe.py`
- **macOS Build (.app & Unix binary):** `python build_mac.py`

---

## 6. Project Architecture

```
├── 1_Dataset/
│   ├── bank-full.csv                 # Raw UCI Bank Marketing dataset (45,211 rows)
│   └── data_loader.py                # Dataset download, loading, and inspection
├── 2_BayesianNetworkClassification/
│   └── bayesian_network.py           # DAG structure learning, BDeu CPT estimation, inference
├── 3_RuleBasedClassification/
│   ├── branch_counter.py             # AST-based static branching statement verifier
│   └── rule_based.py                 # Compliant 2-branch rule classifier
├── pages/                            # Multi-page Streamlit GUI
│   ├── 1_Overview.py                 # Held-out comparison & 5-Fold Cross-Validation dashboard
│   ├── 2_Bayesian_Network.py         # Bayesian Network configuration, DAG, CPTs, inference
│   ├── 3_Rule_Based.py               # Rule inspection & execution trace
│   └── 4_Dataset_Explorer.py         # Exploratory data analysis
├── results/                          # Generated reproducible artifacts
│   ├── cv_metrics_summary.csv        # Cross-validation Mean ± Std and pooled metrics
│   ├── cv_fold_metrics.csv           # Detailed metrics for folds 1 to 5
│   ├── cv_pooled_metrics.csv         # Pooled out-of-fold metrics across 45,211 records
│   ├── cv_predictions.csv            # Out-of-fold predictions for every row
│   ├── cv_comparison.png             # Performance bar chart with standard deviation error bars
│   ├── metrics.csv                   # Held-out test set metrics
│   ├── test_predictions.csv          # Held-out predictions and posterior probabilities
│   └── network_structure.png         # Learned DAG visualization
├── src/
│   ├── config.py                     # Central configuration, paths, features, seed
│   ├── cross_validation.py           # StratifiedKFold orchestrator preventing data leakage
│   ├── evaluation.py                 # Metric computation, aggregation, and plotting
│   ├── execution_log.py              # Structured logging and event tracking
│   ├── model_service.py              # Singleton service layer for CLI and GUI
│   ├── preprocessing.py              # Quantile discretization and category encoding
│   └── ui_helpers.py                 # Styling, interactive widgets, and plot helpers
├── tests/                            # Automated test suite (44 tests)
│   ├── test_cross_validation.py      # Folds, stratification, leakage prevention, metrics
│   ├── test_evaluation.py            # Positive-class metrics, threshold optimization
│   ├── test_model_service.py         # Service orchestration, single-record inference
│   ├── test_preprocessing.py         # Leak-free quantile binning, unseen category handling
│   └── test_rule_based.py            # AST branching limit, rule classifications
├── app.py                            # Streamlit entry point
├── desktop_app.py                    # Tkinter desktop GUI
└── requirements.txt                  # Python dependencies
```

## 7. Conclusion

This empirical comparison demonstrates that:
1. A strictly constrained, transparent rule-based classifier using only two branching statements achieves an F1-score of **0.389 ± 0.013** across 5-fold cross-validation, substantially higher than the default Bayesian Network (**0.309 ± 0.030**).
2. The Bayesian Network achieves higher precision (**62.0% vs 52.2%**) and higher accuracy (**89.2% vs 88.6%**), demonstrating that the two paradigms optimize for distinct operational goals.
3. Stratified 5-Fold Cross-Validation with strict inside-fold fitting confirms that these results are statistically robust across partitions and free from data leakage.