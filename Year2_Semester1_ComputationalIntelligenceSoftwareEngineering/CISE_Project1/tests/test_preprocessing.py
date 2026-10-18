"""Tests for splitting and preprocessing. They use a tiny synthetic table (no download)."""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.preprocessing import BankPreprocessor, split_data


def make_raw(n: int = 200, seed: int = 0) -> pd.DataFrame:
    """Synthetic data with the same columns as the real dataset."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "age": rng.integers(18, 90, n),
        "job": rng.choice(["admin.", "technician", "student"], n),
        "marital": rng.choice(["married", "single"], n),
        "education": rng.choice(["primary", "secondary", "tertiary"], n),
        "default": rng.choice(["no", "yes"], n),
        "balance": rng.integers(-500, 20000, n),
        "housing": rng.choice(["no", "yes"], n),
        "loan": rng.choice(["no", "yes"], n),
        "contact": rng.choice(["cellular", "unknown"], n),
        "day": rng.integers(1, 32, n),
        "month": rng.choice(["jan", "may", "oct"], n),
        "duration": rng.integers(0, 2000, n),
        "campaign": rng.integers(1, 20, n),
        "pdays": rng.choice([-1, -1, -1, 30, 90, 200], n),
        "previous": rng.choice([0, 0, 0, 1, 2, 5], n),
        "poutcome": rng.choice(["unknown", "success", "failure"], n),
    })
    df["y"] = np.where(np.arange(n) % 5 == 0, "yes", "no")   # 20% yes
    return df


def test_split_is_stratified_reproducible_and_leak_free():
    df = make_raw()
    X_tr, X_te, y_tr, y_te = split_data(df, test_size=0.25, seed=1)
    X_tr2, X_te2, _, _ = split_data(df, test_size=0.25, seed=1)
    assert len(X_te) == 50 and len(X_tr) == 150
    assert list(X_te.index) == list(X_te2.index)                  # reproducible
    assert (y_tr == "yes").mean() == pytest.approx(0.2, abs=0.01)  # stratified
    assert (y_te == "yes").mean() == pytest.approx(0.2, abs=0.01)
    assert config.TARGET not in X_tr.columns                      # no target leakage
    assert "duration" not in X_tr.columns
    assert set(X_tr.index).isdisjoint(X_te.index)


def test_split_rejects_bad_labels():
    df = make_raw()
    df.loc[0, "y"] = "maybe"
    with pytest.raises(ValueError, match="Unexpected target labels"):
        split_data(df)


def test_output_is_all_strings_and_complete():
    X_tr, X_te, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    out = pre.transform(X_te)
    assert list(out.columns) == config.FEATURES
    assert len(out) == len(X_te)
    assert not out.isna().any().any()
    assert all(isinstance(v, str) for v in out.to_numpy().ravel())


def test_every_transformed_value_is_a_known_state():
    X_tr, X_te, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    out = pre.transform(X_te)
    for col in config.FEATURES:
        assert set(out[col]) <= set(pre.states(col)), col


def test_bin_edges_come_from_training_data_only():
    X_tr, _, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    shifted = X_tr.copy()
    shifted["age"] = shifted["age"] + 1000        # transform must not change learned edges
    edges_before = list(pre.bin_edges_["age"])
    pre.transform(shifted)
    assert pre.bin_edges_["age"] == edges_before


def test_out_of_range_numbers_land_in_outer_bins():
    X_tr, _, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    probe = X_tr.iloc[:2].copy()
    probe["age"] = [1, 500]
    out = pre.transform(probe)
    assert out["age"].iloc[0] == pre.states("age")[0]
    assert out["age"].iloc[1] == pre.states("age")[-1]


def test_unseen_category_is_replaced_by_most_frequent_training_category():
    X_tr, X_te, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    probe = X_te.iloc[:3].copy()
    probe["job"] = "astronaut"
    out = pre.transform(probe)
    assert set(out["job"]) == {pre.most_frequent_["job"]}
    assert pre.n_unseen_replaced_ == 3


def test_pdays_minus_one_is_its_own_state():
    X_tr, _, _, _ = split_data(make_raw())
    pre = BankPreprocessor().fit(X_tr)
    probe = X_tr.iloc[:2].copy()
    probe["pdays"] = [-1, 90]
    out = pre.transform(probe)
    assert out["pdays"].iloc[0] == "never_contacted"
    assert out["pdays"].iloc[1] != "never_contacted"


def test_constant_numeric_column_does_not_crash():
    X_tr, _, _, _ = split_data(make_raw())
    X_tr = X_tr.assign(campaign=3)
    pre = BankPreprocessor().fit(X_tr)
    assert pre.states("campaign") == ["<=3", ">3"]     # duplicate quantile edges collapsed
    assert set(pre.transform(X_tr)["campaign"]) == {"<=3"}


def test_errors_are_explicit():
    X_tr, _, _, _ = split_data(make_raw())
    with pytest.raises(RuntimeError, match="fit"):
        BankPreprocessor().transform(X_tr)
    with pytest.raises(ValueError, match="Missing feature columns"):
        BankPreprocessor().fit(X_tr.drop(columns=["age"]))
    bad = X_tr.copy().astype({"balance": float})
    bad.iloc[0, bad.columns.get_loc("balance")] = np.nan
    with pytest.raises(ValueError, match="missing values"):
        BankPreprocessor().fit(bad)
