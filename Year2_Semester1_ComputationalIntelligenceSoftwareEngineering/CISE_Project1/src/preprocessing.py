"""Train/test splitting and preprocessing for the (discrete) Bayesian Network.

A discrete Bayesian Network (pgmpy `DiscreteBayesianNetwork`) can only handle
variables with a finite set of states, so:
  * categorical features are kept as strings (their states are the categories);
  * numeric features are DISCRETISED into a few bins (quantile bins).

All "learned" values (category lists, bin edges) are computed from the TRAINING
data only (`fit`) and then merely applied to the test data (`transform`).
The rule-based classifier does NOT use this preprocessing: it works on the raw
(un-binned) test records, but on exactly the same rows.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src import config


def split_data(df: pd.DataFrame, test_size: float = config.TEST_SIZE,
               seed: int = config.RANDOM_SEED):
    """Select features + target and make a reproducible, stratified split.

    Returns raw (un-preprocessed) X_train, X_test, y_train, y_test.
    `y` is never part of X and `duration` is excluded (see config.py).
    """
    if config.TARGET not in df.columns:
        raise ValueError(f"Target column '{config.TARGET}' not found.")
    unexpected = set(df[config.TARGET].unique()) - set(config.LABELS)
    if unexpected:
        raise ValueError(f"Unexpected target labels: {unexpected}")
    features = df[config.FEATURES].copy()
    assert config.TARGET not in features.columns        # leakage guard
    assert not set(config.EXCLUDED_FEATURES) & set(features.columns)
    return train_test_split(features, df[config.TARGET], test_size=test_size,
                            random_state=seed, stratify=df[config.TARGET])


class BankPreprocessor:
    """Discretises numeric columns and fixes the category sets of categorical columns."""

    def __init__(self, n_bins: dict[str, int] | None = None):
        self.n_bins = dict(config.N_BINS if n_bins is None else n_bins)
        self.bin_edges_: dict[str, list[float]] = {}
        self.categories_: dict[str, list[str]] = {}
        self.most_frequent_: dict[str, str] = {}
        self.n_unseen_replaced_ = 0   # how many unseen categories were replaced in transform

    # ------------------------------------------------------------------ fit
    def fit(self, X: pd.DataFrame) -> "BankPreprocessor":
        """Learn category lists and quantile bin edges from TRAINING data only."""
        missing = set(config.FEATURES) - set(X.columns)
        if missing:
            raise ValueError(f"Missing feature columns: {sorted(missing)}")
        for col in config.CATEGORICAL_FEATURES:
            values = X[col].fillna("unknown").astype(str)
            counts = values.value_counts()
            self.categories_[col] = sorted(counts.index)
            self.most_frequent_[col] = counts.index[0]
        for col in config.NUMERIC_FEATURES:
            if X[col].isna().any():
                raise ValueError(f"Numeric column '{col}' contains missing values.")
            values = X[col]
            if col == "pdays":
                values = values[values >= 0]   # -1 is a special code, binned separately
            self.bin_edges_[col] = self._quantile_edges(values, self.n_bins[col])
        return self

    @staticmethod
    def _quantile_edges(values: pd.Series, n_bins: int) -> list[float]:
        """Inner bin edges at equally spaced quantiles; duplicates removed (many ties)."""
        quantiles = np.linspace(0, 1, n_bins + 1)[1:-1]
        return sorted({float(e) for e in np.quantile(values, quantiles)})

    @staticmethod
    def _bin_label(edges: list[float], index: int) -> str:
        """Readable label such as '<=33', '(33,39]' or '>48' for bin number `index`."""
        if not edges:
            return "all"
        if index == 0:
            return f"<={edges[0]:g}"
        if index == len(edges):
            return f">{edges[-1]:g}"
        return f"({edges[index - 1]:g},{edges[index]:g}]"

    def states(self, column: str) -> list[str]:
        """All possible states of a column (needed so the BN knows every state)."""
        if column in config.CATEGORICAL_FEATURES:
            return list(self.categories_[column])
        edges = self.bin_edges_[column]
        labels = [self._bin_label(edges, i) for i in range(len(edges) + 1)]
        return (["never_contacted"] + labels) if column == "pdays" else labels

    # ------------------------------------------------------------ transform
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply the learned categories/bins. Output: all columns are strings."""
        if not self.categories_:
            raise RuntimeError("Call fit() before transform().")
        out = pd.DataFrame(index=X.index)
        for col in config.CATEGORICAL_FEATURES:
            values = X[col].fillna("unknown").astype(str)
            unseen = ~values.isin(self.categories_[col])
            self.n_unseen_replaced_ += int(unseen.sum())
            # Unseen category -> most frequent TRAINING category (documented choice).
            out[col] = values.mask(unseen, self.most_frequent_[col]).astype(object)
        for col in config.NUMERIC_FEATURES:
            if X[col].isna().any():
                raise ValueError(f"Numeric column '{col}' contains missing values.")
            edges = self.bin_edges_[col]
            # np.searchsorted(side="left") puts a value equal to an edge in the lower bin,
            # i.e. bins are (edge_i-1, edge_i]. Values outside the training range simply
            # land in the first/last bin.
            index = np.searchsorted(edges, X[col].to_numpy(), side="left")
            labels = np.array([self._bin_label(edges, i) for i in range(len(edges) + 1)],
                              dtype=object)
            binned = labels[index]
            if col == "pdays":
                binned = np.where(X[col].to_numpy() < 0, "never_contacted", binned)
            out[col] = pd.Series(binned, index=X.index, dtype=object)
        return out[config.FEATURES]

    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return self.fit(X).transform(X)
