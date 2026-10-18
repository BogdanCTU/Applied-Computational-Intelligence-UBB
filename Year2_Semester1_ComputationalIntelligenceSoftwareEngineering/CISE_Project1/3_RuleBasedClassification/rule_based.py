"""Part B: rule-based classifier (NOT machine learning - fixed, human-readable rules).

Attributes used by the classifier (n = 2):  poutcome, month
Allowed branching statements: n = 2.  Actual branching statements: 2 (one `if`, one `elif`).
Rules (decision paths): 3 -> "yes", "yes", "no".   (rules != branching statements)

How n is calculated: n = number of DISTINCT input attributes that are read by the
classifier (`record["..."]` below). The count is verified automatically by
branch_counter.py (AST based, whole file) and by tests/test_rule_based.py.

How the rules were chosen (TRAINING data only; test labels were never looked at):
  * On the training split, the yes-rate per category was tabulated (README + main.py
    print it). Overall yes-rate is 11.7%.
  * poutcome == "success" (previous campaign succeeded): 64.6% yes  -> predict yes.
  * Months mar, sep, oct, dec: 46% yes on average (about 4x the base rate, but far
    fewer calls than other months) -> predict yes. The 4 months were picked because each
    has a training yes-rate of 44-51%, much higher than every other month (<= 20%).
    Predicting yes for them (although the average is just below 50%) was chosen
    because it raises the positive-class F1 on the TRAINING split (measured: 0.287 with
    the poutcome rule alone -> 0.386 with both rules), at the price of slightly lower
    training accuracy (0.893 -> 0.886). F1 matters for an imbalanced problem; a strict
    50% cut-off would give almost no `yes` predictions.
  * Everyone else -> no.
Threshold choices are therefore data-informed by the training set, but are not tuned
on the test set.
"""

import pandas as pd

HIGH_SUCCESS_MONTHS = ("mar", "sep", "oct", "dec")


def classify_client(record: dict) -> str:
    """Return 'yes' or 'no' for one client (dict-like with the raw attributes)."""
    if record["poutcome"] == "success":
        return "yes"                      # rule 1: previous campaign was successful
    elif record["month"] in HIGH_SUCCESS_MONTHS:
        return "yes"                      # rule 2: contacted in a historically good month
    else:
        return "no"                       # rule 3: default (majority class)


def predict_rules(X: pd.DataFrame) -> pd.Series:
    """Apply the rules to every row of the RAW (non-discretised) feature table."""
    predictions = [classify_client(row) for row in X.to_dict("records")]
    return pd.Series(predictions, index=X.index, name="prediction")
