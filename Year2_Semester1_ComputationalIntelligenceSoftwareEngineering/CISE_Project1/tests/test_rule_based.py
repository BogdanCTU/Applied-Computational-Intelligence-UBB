"""Tests for the rule-based classifier and the branching-statement limit."""

import pandas as pd
import pytest

from src import config
import branch_counter
import rule_based

RULES_FILE = config.RULES_DIR / "rule_based.py"


def record(**overrides) -> dict:
    base = {"poutcome": "unknown", "month": "may"}
    base.update(overrides)
    return base


def test_known_decisions():
    assert rule_based.classify_client(record(poutcome="success")) == "yes"
    assert rule_based.classify_client(record(month="mar")) == "yes"
    assert rule_based.classify_client(record()) == "no"
    assert rule_based.classify_client(record(poutcome="failure", month="jul")) == "no"


def test_predictions_are_valid_labels_and_keep_the_index():
    X = pd.DataFrame({"poutcome": ["success", "unknown", "failure"],
                      "month": ["may", "dec", "jun"]}, index=[10, 20, 30])
    out = rule_based.predict_rules(X)
    assert list(out.index) == [10, 20, 30]
    assert list(out) == ["yes", "yes", "no"]
    assert set(out) <= set(config.LABELS)


def test_empty_input_gives_empty_output():
    X = pd.DataFrame({"poutcome": [], "month": []})
    assert len(rule_based.predict_rules(X)) == 0


def test_missing_attribute_raises_a_clear_error():
    with pytest.raises(KeyError):
        rule_based.classify_client({"month": "may"})


def test_real_classifier_respects_branching_limit():
    result = branch_counter.check_file(RULES_FILE, config.FEATURES)
    assert result["n_attributes_used"] >= 1
    assert result["branching_statements"] <= result["allowed_branches"]
    assert result["compliant"]
    # Documented numbers (update the docstring/README if you change the rules):
    assert result["attributes_used"] == ["month", "poutcome"]
    assert result["branching_statements"] == 2
    assert result["return_statements_(rules)"] == 3


def test_classifier_does_not_use_forbidden_columns():
    used = branch_counter.attributes_used(RULES_FILE.read_text(), config.FEATURES + ["y", "duration"])
    assert "y" not in used and "duration" not in used


# --- the counter itself must be trustworthy
def test_counter_counts_if_elif_but_not_else():
    src = "def f(r):\n if r['a']: return 1\n elif r['b']: return 2\n else: return 3\n"
    assert branch_counter.count_branching_statements(src) == 2


def test_counter_detects_hidden_branches():
    assert branch_counter.count_branching_statements("x = 1 if a else 2") == 1
    assert branch_counter.count_branching_statements("x = [i for i in y if i]") == 1
    assert branch_counter.count_branching_statements(
        "match v:\n case 1: pass\n case _: pass\n") == 2
    assert branch_counter.count_branching_statements("def g():\n if a:\n  if b: pass\n") == 2


def test_counter_flags_violation():
    path = config.PROJECT_ROOT / "results" / "_tmp_violation.py"
    path.write_text("def f(r):\n if r['age']: return 1\n elif r['job']: return 2\n"
                    " elif r['month']: return 3\n else: return 4\n")
    try:
        result = branch_counter.check_file(path, config.FEATURES)
    finally:
        path.unlink()
    assert result["allowed_branches"] == 3 and result["branching_statements"] == 3
    assert result["compliant"]
    path.write_text("x=1")  # recreate for a second case with too many branches
    path.write_text("def f(r):\n if r['age']: return 1\n elif r['age']: return 2\n else: return 4\n")
    try:
        result = branch_counter.check_file(path, config.FEATURES)
    finally:
        path.unlink()
    assert result["allowed_branches"] == 1 and result["branching_statements"] == 2
    assert not result["compliant"]
