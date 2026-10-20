# Bayesian Networks vs. Rule-Based Classification

Computational Intelligence in Software Engineering — Project Presentation

## 1. Objective

Compare two approaches for predicting whether a bank customer subscribes to a term deposit:

- Part A: Bayesian Network using `pgmpy`.
- Part B: Rule-Based Classifier constrained by the assignment's branching-statement limit.

Both models are evaluated on the same held-out test set.

## 2. Dataset and Technologies

- Dataset: UCI Bank Marketing — 45,211 records.
- Target: `y` (`yes` / `no`).
- Class distribution: 11.7% subscribers and 88.3% non-subscribers.
- Input features: 15, excluding `duration` to prevent target leakage.
- Technologies: Python, pgmpy, pandas, scikit-learn, Streamlit, Tkinter, Matplotlib, NetworkX and pytest.

The data is split into 80% training and 20% testing, using stratification and `random_state=42`. Preprocessing is fitted on training data only.

## 3. Methodology

### Bayesian Network

The model represents probabilistic dependencies between variables using a directed acyclic graph (DAG).

1. Discretize numerical features and encode categorical variables.
2. Learn the network structure using Hill Climb Search and BIC scoring.
3. Estimate conditional probability tables (CPTs) using BDeu smoothing.
4. Perform inference using Variable Elimination.
5. Classify customers using posterior probabilities and a decision threshold.

The learned network contains 16 nodes and 30 directed edges. The target's direct parents are `month` and `poutcome`.

### Rule-Based Classifier

The classifier uses two explicit branching statements based on:

- `poutcome == 'success'`
- `month` belonging to `mar`, `sep`, `oct` or `dec`

If either condition is satisfied, the prediction is `yes`; otherwise, it is `no`.

Static AST analysis verifies the two-branch implementation against the assignment's constraint. The interpretation of the permitted attribute count should be confirmed with the professor.

## 4. Experimental Results

The following are the reported results from the held-out test set of 9,043 records.

| Classifier                             | Accuracy | Precision | Recall | F1-score |
| -------------------------------------- | -------- | --------- | ------ | -------- |
| Rule-Based                             | 88.82%   | 53.74%    | 31.95% | 0.4007   |
| Bayesian Network, threshold 0.50       | 89.24%   | 63.00%    | 19.47% | 0.2975   |
| Bayesian Network, tuned threshold 0.21 | 87.47%   | 45.91%    | 39.79% | 0.4263   |

The tuned Bayesian Network threshold was selected using validation data, not the held-out test set.

### Interpretation

- The default Bayesian Network achieves the highest accuracy and precision but misses more subscribers.
- The Rule-Based classifier achieves a higher F1-score than the default Bayesian Network.
- Threshold tuning improves the Bayesian Network's recall and F1-score, producing the best F1-score among the reported models.
- The majority baseline demonstrates why accuracy alone is insufficient for an imbalanced dataset.

## 5. Limitations and Future Work

- Discretization loses some numerical information.
- Restricting network nodes to at most three parents may limit the dependencies learned.
- Threshold optimization changes the precision–recall trade-off.
- Future work could explore hybrid Bayesian Networks and cost-sensitive classification based on campaign costs and deposit value.

## 6. Application and Reproducibility

The application provides dataset exploration, model training, network visualization, CPT inspection, rule execution traces, predictions, evaluation metrics and model comparisons.

Run the tests:

```
pytest
```

Run the experiment:

```
python -m src.main
```

Launch the desktop GUI:

```
python desktop_app.py
```

Launch the web GUI:

```
python -m streamlit run app.py
```

Build standalone executables:

- **Windows Build (.exe):**
  ```powershell
  python build_exe.py
  ```
  Executable generated at: `dist/BankMarketingClassifier/BankMarketingClassifier.exe`

- **macOS Build (.app & Unix binary):**
  ```bash
  python build_mac.py
  ```
  Native Application Bundle generated at: `dist/BankMarketingClassifier.app`

## Conclusion

The experiment demonstrates that a highly constrained, interpretable rule-based classifier can outperform a default Bayesian Network in F1-score. However, optimizing the Bayesian Network's classification threshold improves its F1-score further. This highlights the importance of selecting evaluation metrics appropriate to the problem and distinguishing probabilistic modeling from the decision threshold used to convert probabilities into classifications.