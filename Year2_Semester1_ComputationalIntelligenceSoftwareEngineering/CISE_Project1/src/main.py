"""Run the whole experiment:  python -m src.main

Steps: load -> inspect -> split -> preprocess -> Bayesian Network (Part A)
       -> rule-based classifier (Part B) -> evaluate both on the SAME test rows -> save.
"""

import os
import subprocess
import sys

import pandas as pd

from src import config
from src.evaluation import (comparison_table, plot_confusion_matrix, report_text,
                            save_results)
from src.preprocessing import BankPreprocessor, split_data

# Modules from the numbered folders (config.py put these folders on sys.path).
import bayesian_network
import branch_counter
import data_loader
import rule_based


def main() -> None:
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and inspect the raw dataset
    df = data_loader.load_dataset()
    report = data_loader.inspect_dataset(df)
    print("=" * 70, "\nDATASET INSPECTION\n" + "=" * 70)
    print(report)
    (config.RESULTS_DIR / "dataset_report.txt").write_text(report + "\n", encoding="utf-8")

    # 2. Feature selection + stratified, seeded train/test split (raw values)
    X_train, X_test, y_train, y_test = split_data(df)
    print("\n" + "=" * 70)
    print(f"Features used by BOTH classifiers ({len(config.FEATURES)}): {config.FEATURES}")
    print(f"Excluded: {config.EXCLUDED_FEATURES} (known only after the call -> leakage)")
    print(f"Train: {len(X_train)} rows, test: {len(X_test)} rows, seed={config.RANDOM_SEED}")
    print(f"'yes' rate: train {(y_train == 'yes').mean():.1%}, test {(y_test == 'yes').mean():.1%}")

    # Training-only look at the attributes used by the rules (how the rules were motivated)
    train_view = X_train.assign(yes_rate=(y_train == "yes").astype(int))
    for column in ("poutcome", "month"):
        print(f"\nTRAINING yes-rate by {column}:")
        print(train_view.groupby(column)["yes_rate"].agg(["mean", "size"]).round(3)
              .sort_values("mean", ascending=False).to_string())

    # 3. Preprocessing for the Bayesian Network (fit on TRAIN only)
    preprocessor = BankPreprocessor().fit(X_train)
    P_train = preprocessor.transform(X_train)
    P_test = preprocessor.transform(X_test)
    print(f"\nUnseen categories replaced in test data: {preprocessor.n_unseen_replaced_}")
    print("Discretisation (bin states per numeric feature):")
    for column in config.NUMERIC_FEATURES:
        print(f"  {column:<9} {preprocessor.states(column)}")

    # 4. Part A - Bayesian Network
    print("\n" + "=" * 70 + "\nPART A: BAYESIAN NETWORK\n" + "=" * 70)
    train_table = P_train.assign(**{config.TARGET: y_train})
    edges = bayesian_network.learn_structure(train_table)
    state_names = {c: preprocessor.states(c) for c in config.FEATURES}
    state_names[config.TARGET] = config.LABELS
    model = bayesian_network.build_network(edges, list(train_table.columns))
    bayesian_network.fit_parameters(model, train_table, state_names)
    description = bayesian_network.describe_network(model)
    print(description)
    (config.RESULTS_DIR / "network_description.txt").write_text(description + "\n", encoding="utf-8")
    bayesian_network.save_network_plot(model, config.RESULTS_DIR / "network_structure.png")
    bn_output = bayesian_network.predict(model, P_test)
    bn_pred = bn_output["prediction"]

    # 5. Part B - rule-based classifier on the RAW test rows
    print("\n" + "=" * 70 + "\nPART B: RULE-BASED CLASSIFIER\n" + "=" * 70)
    rule_pred = rule_based.predict_rules(X_test)
    check = branch_counter.check_file(
        config.RULES_DIR / "rule_based.py", config.FEATURES)
    for key, value in check.items():
        print(f"  {key}: {value}")
    if not check["compliant"]:
        raise RuntimeError("The rule-based classifier violates the branching-statement limit!")

    # 6. Evaluation on exactly the same test records
    majority = config.NEGATIVE_LABEL
    baseline_pred = pd.Series(majority, index=y_test.index)   # optional reference only
    assert list(bn_pred.index) == list(rule_pred.index) == list(y_test.index)
    predictions = {
        "Bayesian Network": bn_pred,
        "Rule-based": rule_pred,
        "Majority baseline (reference)": baseline_pred,
    }
    table = comparison_table(y_test, predictions)
    print("\n" + "=" * 70 + "\nRESULTS ON THE HELD-OUT TEST SET (positive class = 'yes')\n" + "=" * 70)
    print(table.round(4).to_string())
    for name, pred in predictions.items():
        print(f"\nClassification report - {name}\n{report_text(y_test, pred)}")
    save_results(table, config.RESULTS_DIR / "metrics.csv")
    for name, pred in predictions.items():
        slug = name.split(" (")[0].lower().replace(" ", "_")
        plot_confusion_matrix(y_test, pred, name, config.RESULTS_DIR / f"confusion_{slug}.png")
    pd.DataFrame({"actual": y_test, "bayesian_network": bn_pred,
                  "bn_proba_yes": bn_output["proba_yes"], "rule_based": rule_pred}
                 ).to_csv(config.RESULTS_DIR / "test_predictions.csv", index_label="row_id")
    print(f"\nSaved metrics, plots and predictions to {config.RESULTS_DIR}")


def ensure_fixed_hash_seed() -> None:
    """Re-launch this program once with PYTHONHASHSEED=0.

    Observed: pgmpy's hill-climb structure search returned a slightly different
    network (30 vs 31 edges) in different Python processes, and the result depended
    on PYTHONHASHSEED (likely because ties between equally good moves are broken in
    set-iteration order; the exact cause was not investigated further). Fixing the
    hash seed makes the learned structure, and therefore all results, reproducible.
    """
    if os.environ.get("PYTHONHASHSEED") == "0":
        return
    env = dict(os.environ, PYTHONHASHSEED="0")
    command = [sys.executable, "-W", "ignore", "-m", "src.main", *sys.argv[1:]]
    sys.exit(subprocess.run(command, env=env, cwd=config.PROJECT_ROOT).returncode)


if __name__ == "__main__":
    ensure_fixed_hash_seed()
    main()
