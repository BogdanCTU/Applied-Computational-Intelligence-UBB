# Bayesian Network vs. Rule-Based Classification — UCI Bank Marketing

University assignment: classify whether a bank client subscribes to a term deposit (`y`), using
**Part A** a Bayesian Network (pgmpy) and **Part B** a hand-written rule-based classifier with a
limited number of `if/elif` statements, then compare them honestly.

## 1. Assignment and dataset

- **Part A** – ML classifier: Bayesian Network built with the open-source library *pgmpy*.
- **Part B** – explicit branching logic with **at most n branching statements**, where n = number of
  input attributes the classifier actually uses.
- **Dataset** – [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank%2Bmarketing),
  file `bank-full.csv` (45,211 records, 16 input attributes + target). The program uses
  `1_Dataset/bank-full.csv` if it exists and otherwise downloads it from UCI (`1_Dataset/data_loader.py`).
  If the download fails the error message explains how to place the file manually. The CSV is
  git-ignored.
- **Target `y`** – `yes` (subscribed, the **positive class**) / `no`. Distribution: 11.7 % yes, 88.3 % no.
- **Excluded attribute `duration`** – the length of the *current* call is only known after the call, and
  it almost determines the outcome. A realistic "who should we call?" model cannot use it, so it is
  removed from **both** classifiers (config: `EXCLUDED_FEATURES`). Results with `duration` would look
  much better but would not be achievable in practice. (Not run in this project.)
- **Features used (15)**: age, job, marital, education, default, balance, housing, loan, contact, day,
  month, campaign, pdays, previous, poutcome. `y` is never an input.

Dataset facts printed by the program (`results/dataset_report.txt`): no NaN values; 0 duplicate rows;
the dataset's own missing marker `unknown` appears in job (0.6 %), education (4.1 %), contact (28.8 %),
poutcome (81.7 %); `pdays = -1` (never contacted before) for 81.7 %; 3,766 negative balances.

## 2. Project structure

```
CISE_Project1/
├── README.md, requirements.txt, .gitignore
├── 1_Dataset/                       bank-full.csv (not committed) + data_loader.py
├── 2_BayesianNetworkClassification/ bayesian_network.py   (Part A)
├── 3_RuleBasedClassification/       rule_based.py (Part B), branch_counter.py (AST verification)
├── src/                             config.py, preprocessing.py, evaluation.py, main.py
├── tests/                           test_preprocessing.py, test_rule_based.py, test_evaluation.py
└── results/                         generated outputs (git-ignored except .gitkeep)
```

Folder names starting with a digit are not importable Python packages, so `src/config.py` adds the three
part-folders to `sys.path`; their modules are imported as `data_loader`, `bayesian_network`, `rule_based`.
All paths are built with `pathlib` relative to the project root, so the working directory does not matter.

## 3. Setup (Python 3.11)

macOS / Linux:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Windows PowerShell:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Run

```bash
python -m src.main     # full experiment (~1 minute)
pytest                 # 26 automated tests, no download needed
```

Outputs in `results/`: `metrics.csv`, `test_predictions.csv`, `dataset_report.txt`,
`network_description.txt`, `network_structure.png`, `confusion_bayesian_network.png`,
`confusion_rule-based.png`, `confusion_majority_baseline.png`, `run_log.txt` (if you redirect output).

`src.main` re-launches itself once with `PYTHONHASHSEED=0`. Reason: in this environment pgmpy's hill
climbing gave a different network (30 vs 31 edges) in different processes depending on the hash seed.
With the seed fixed, two consecutive runs gave byte-identical `metrics.csv`.

## 5. Part A — Bayesian Network step by step

A **Bayesian Network** is a directed acyclic graph (DAG) plus probability tables:
- **Nodes** = random variables (the 15 features and `y`).
- **Directed edges** = "direct probabilistic dependence" (parent → child). Edges are *statistical*
  dependencies learned from data; they are **not** proof of causation.
- **Conditional probability table (CPT)** of a node = P(node | its parents), one row per node state, one
  column per combination of parent states. The joint distribution factorises as the product of all CPTs.

Pipeline (see `src/main.py`):
1. **Load / inspect** the data. 2. **Select** the 15 features. 3. **Split** 80/20, stratified,
   `random_state=42` (36,168 train / 9,043 test rows).
4. **Preprocess** (`src/preprocessing.py`, fitted on training data only). A discrete network needs finite states:
   - Categorical features stay as strings. Category lists come from the training data; an unseen category
     in new data would be replaced by the most frequent training category (counted; **0** occurred here).
   - Numeric features are discretised into **quantile bins** (edges = training quantiles; duplicate edges
     collapsed): age 4, balance 4, day 3, campaign 3, previous 2 (effectively `0` vs `>0`), pdays =
     `never_contacted` (-1) + 3 bins. Test values outside the training range fall in the first/last bin.
5. **Learn the structure** (`learn_structure`): pgmpy `HillClimbSearch` with the **BIC** score
   (`bic-d`, `max_indegree=3`). It starts with no edges and greedily adds/removes/reverses the single edge
   that improves BIC most, until nothing improves. BIC rewards fit and penalises complexity. Hill climbing
   finds a *local* optimum and is not guaranteed to find the best DAG. I did not compare against other
   structure learners (e.g. Tree-Augmented Naive Bayes), so I cannot say whether a different structure
   would classify better.
6. **Learn the parameters** (`fit_parameters`): `DiscreteBayesianEstimator` with a BDeu prior
   (`equivalent_sample_size=5`) — essentially counting with a small smoothing pseudo-count. Parent-state
   combinations never seen in training still get a valid, near-uniform distribution; no probability is
   exactly 0, so unseen combinations in the test set cannot produce zero-probability evidence.
7. **Inference** (`predict`): for each test client the observed feature values are given as evidence and
   pgmpy's exact **Variable Elimination** computes P(y = yes | evidence). Predict `yes` if it is ≥ 0.5.
   Identical rows are computed once and reused (same result, faster).
8. **Evaluate** on the held-out test set.

**Structure vs. parameters vs. inference** — structure learning decides *which* variables are connected;
parameter learning fills in *the numbers* in each CPT for that fixed graph; inference uses the finished
network to answer a query for one new client. They are three separate stages.

**Learned network (this run):** 16 nodes, 30 edges (list in `results/network_description.txt`, picture in
`results/network_structure.png`). `y` has parents `month` and `poutcome` and one child, `marital`. The Markov
blanket of `y` is `contact, marital, month, poutcome` (the variables that influence P(y | rest)).
Inspect any CPT in code with `model.get_cpds("job")`.

### Tiny illustrative example (NOT the bank data)
Hypothetical network `Flu → Fever`, `Flu → Cough`, with made-up probabilities:

| P(Flu=yes) = 0.10 | P(Fever=yes \| Flu=yes) = 0.80 | P(Fever=yes \| Flu=no) = 0.10 |
|---|---|---|
| | P(Cough=yes \| Flu=yes) = 0.70 | P(Cough=yes \| Flu=no) = 0.20 |

*Inference:* a patient has fever and cough. Flu-yes: 0.10 × 0.8 × 0.7 = 0.056; Flu-no: 0.90 × 0.1 × 0.2 = 0.018.
Normalise: P(Flu=yes | fever, cough) = 0.056 / (0.056 + 0.018) ≈ **0.757**. The bank experiment does exactly this
with `y` instead of `Flu` and the client attributes instead of symptoms.

## 6. Part B — rule-based classifier

`3_RuleBasedClassification/rule_based.py`:
```python
if record["poutcome"] == "success":       return "yes"   # rule 1
elif record["month"] in ("mar","sep","oct","dec"): return "yes"   # rule 2
else:                                     return "no"    # rule 3
```
- **How the rules were chosen (training split only; test labels never used):** training yes-rate is 64.6 %
  for `poutcome = success` (base rate 11.7 %), and 44–51 % for March, September, October and December
  (all other months ≤ 20 %). Rule 2 was kept although the average (46 %) is below 50 %, because on the
  *training* split it raises F1 from 0.287 to 0.386 while lowering accuracy from 0.893 to 0.886. Those
  four months were selected by reading the training table, so the thresholds are data-informed, though not
  tuned on the test set. The months are a seasonal pattern in this dataset and may not generalise.
- **How n is calculated:** n = number of distinct input attributes the classifier reads = **2**
  (`poutcome`, `month`). Allowed branching statements = **2**.
- **Branching statements actually used: 2** (one `if`, one `elif`; the final `else` is not a separate
  statement). **Number of rules (decision paths): 3.** These are two different quantities.
- **Verification:** `branch_counter.py` parses the whole of `rule_based.py` with Python's `ast` module and
  counts every `if`/`elif`, conditional expression, `match` case and comprehension filter, so branches cannot
  hide in helpers. `src.main` aborts if the limit is exceeded and `tests/test_rule_based.py` checks it (and
  checks the counter itself on small examples).
- The rules read the **raw** feature values (no binning) of exactly the same test rows.

## 7. Evaluation

Metrics (positive class = `yes`, set explicitly): **accuracy**; **precision** = TP/(TP+FP);
**recall** = TP/(TP+FN); **F1**; confusion matrix; classification report.
- *False positive*: a client we predict will subscribe but does not → wasted call.
- *False negative*: a client who would have subscribed but is not predicted → lost sale.
- *Imbalance*: 88.3 % of clients say `no`, so always predicting `no` already reaches 88.3 % accuracy; accuracy alone
  is misleading and precision/recall for `yes` are more informative. The majority baseline is included only as an
  optional reference.

### Results (verified: output of `python -m src.main`, test set of 9,043 clients, 1,058 `yes`)

| Classifier | Accuracy | Precision (yes) | Recall (yes) | F1 (yes) | TN | FP | FN | TP |
|---|---|---|---|---|---|---|---|---|
| Bayesian Network | 0.8924 | 0.6300 | 0.1947 | 0.2975 | 7864 | 121 | 852 | 206 |
| Rule-based (2 branches) | 0.8882 | 0.5374 | 0.3195 | 0.4007 | 7694 | 291 | 720 | 338 |
| Majority baseline (reference) | 0.8830 | 0.0000 | 0.0000 | 0.0000 | 7985 | 0 | 1058 | 0 |

(also in `results/metrics.csv`).

### Interpretation (what the numbers show / what they do not)
- Accuracy of the two classifiers is almost the same (BN +0.4 percentage points) and both are only slightly
  above the 88.3 % majority baseline.
- The BN is more *precise* (63 % vs 54 % of predicted yes are real) but finds fewer subscribers
  (recall 19 % vs 32 %). The rule-based classifier has the higher F1 (0.40 vs 0.30) and recall.
- So in this experiment the 2-branch rule classifier **matched the BN on accuracy and exceeded it on recall and
  F1**, but had lower precision. Which is "better" depends on the cost of a wasted call vs a missed sale.
- Caveats: one single train/test split (no repeated splits or confidence intervals), so small differences such
  as the 0.4-point accuracy gap should not be over-interpreted. The BN uses a fixed 0.5 probability threshold;
  its predicted probabilities for `yes` are mostly low because `yes` is rare, which is a likely reason for its
  low recall (this explanation was not tested, e.g. by lowering the threshold). Both models are weak at finding
  `yes` clients without `duration`.

## 8. Limitations and possible improvements
- Equal-frequency binning loses information; other bin counts or supervised discretisation were not tried.
- Hill climbing finds a local optimum; no other structure learners, scores or `max_indegree` values were compared.
- No hyper-parameter tuning, cross-validation or probability-threshold tuning was performed.
- The rules (esp. months) were derived from the training split of this particular dataset (collected 2008–2010).
- Without `duration` both models are weak; with it, results would be better but unrealistic (not evaluated here).
- Tests cover preprocessing, rules/branch counting and metrics; there are **no** automated tests for the
  pgmpy network code itself (it was validated only by running the experiment).
