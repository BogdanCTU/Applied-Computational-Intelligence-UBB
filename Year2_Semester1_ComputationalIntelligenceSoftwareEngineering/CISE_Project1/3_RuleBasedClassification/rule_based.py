"""
Part B: Rule-Based Classifier
The classifier uses two fixed rules based on `poutcome` and `month`.
It has 2 branching statements (`if` and `elif`) and 3 decision paths.
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
