"""Tests for metric calculation (positive class = 'yes')."""

import pandas as pd
import pytest

from src.evaluation import compute_metrics, comparison_table, save_results

# 10 clients: 4 really 'yes', 6 really 'no'.
Y_TRUE = ["yes"] * 4 + ["no"] * 6
# Predictions: 3 TP, 1 FN, 2 FP, 4 TN
Y_PRED = ["yes", "yes", "yes", "no", "yes", "yes", "no", "no", "no", "no"]


def test_positive_class_precision_recall_f1_accuracy():
    m = compute_metrics(Y_TRUE, Y_PRED)
    assert (m["TP"], m["FN"], m["FP"], m["TN"]) == (3, 1, 2, 4)
    assert m["precision"] == pytest.approx(3 / 5)      # TP / (TP + FP)
    assert m["recall"] == pytest.approx(3 / 4)         # TP / (TP + FN)
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.75 / (0.6 + 0.75))
    assert m["accuracy"] == pytest.approx(7 / 10)


def test_metrics_do_not_depend_on_label_order_in_data():
    flipped_true = list(reversed(Y_TRUE))
    flipped_pred = list(reversed(Y_PRED))
    assert compute_metrics(flipped_true, flipped_pred) == compute_metrics(Y_TRUE, Y_PRED)


def test_majority_baseline_has_zero_precision_and_recall_but_high_accuracy():
    m = compute_metrics(Y_TRUE, ["no"] * 10)
    assert m["accuracy"] == pytest.approx(0.6)
    assert m["precision"] == 0 and m["recall"] == 0 and m["f1"] == 0   # no warning/crash


def test_perfect_prediction():
    m = compute_metrics(Y_TRUE, Y_TRUE)
    assert m["precision"] == m["recall"] == m["accuracy"] == 1


def test_works_with_pandas_series():
    m = compute_metrics(pd.Series(Y_TRUE), pd.Series(Y_PRED, index=range(10, 20)))
    assert m["TP"] == 3


def test_invalid_inputs_raise():
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_metrics(["yes"], ["yes", "no"])
    with pytest.raises(ValueError, match="empty"):
        compute_metrics([], [])
    with pytest.raises(ValueError, match="Invalid predicted labels"):
        compute_metrics(["yes", "no"], ["yes", "maybe"])


def test_comparison_table_and_csv(tmp_path):
    table = comparison_table(Y_TRUE, {"A": Y_PRED, "B": ["no"] * 10})
    assert list(table.index) == ["A", "B"]
    assert {"accuracy", "precision", "recall", "f1"} <= set(table.columns)
    save_results(table, tmp_path / "out" / "m.csv")
    loaded = pd.read_csv(tmp_path / "out" / "m.csv", index_col="classifier")
    assert loaded.loc["A", "precision"] == pytest.approx(0.6)
