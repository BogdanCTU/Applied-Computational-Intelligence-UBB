"""Run the evaluation pipeline: python -m src.main [--heldout | --cv | --all]

Modes:
  --heldout (default): Train/test split (80/20) evaluation with threshold analysis.
  --cv: Stratified 5-Fold Cross-Validation strictly preventing data leakage.
  --all: Run both held-out evaluation and Stratified 5-Fold Cross-Validation.
"""

import argparse
import os
import subprocess
import sys

import pandas as pd

from src import config
from src.evaluation import (comparison_table, plot_confusion_matrix, plot_cv_comparison,
                            report_text, save_results)
from src.preprocessing import BankPreprocessor, split_data

# Modules from the numbered folders (config.py put these folders on sys.path).
import bayesian_network
import branch_counter
import data_loader
import rule_based


def run_heldout_experiment(df: pd.DataFrame) -> None:
    """Execute the standard held-out 80/20 test split evaluation."""
    print("\n" + "=" * 78)
    print("HELD-OUT 80/20 TEST SET EVALUATION PIPELINE")
    print("=" * 78)

    # 1. Feature selection + stratified, seeded train/test split (raw values)
    X_train, X_test, y_train, y_test = split_data(df)
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

    # 2. Preprocessing for the Bayesian Network (fit on TRAIN only)
    preprocessor = BankPreprocessor().fit(X_train)
    P_train = preprocessor.transform(X_train)
    P_test = preprocessor.transform(X_test)
    print(f"\nUnseen categories replaced in test data: {preprocessor.n_unseen_replaced_}")
    print("Discretisation (bin states per numeric feature):")
    for column in config.NUMERIC_FEATURES:
        print(f"  {column:<9} {preprocessor.states(column)}")

    # 3. Part A - Bayesian Network
    print("\n" + "=" * 78 + "\nPART A: BAYESIAN NETWORK\n" + "=" * 78)
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

    # 4. Part B - rule-based classifier on the RAW test rows
    print("\n" + "=" * 78 + "\nPART B: RULE-BASED CLASSIFIER\n" + "=" * 78)
    rule_pred = rule_based.predict_rules(X_test)
    check = branch_counter.check_file(
        config.RULES_DIR / "rule_based.py", config.FEATURES)
    for key, value in check.items():
        print(f"  {key}: {value}")
    if not check["compliant"]:
        raise RuntimeError("The rule-based classifier violates the branching-statement limit!")

    # 5. Evaluation on exactly the same test records
    majority = config.NEGATIVE_LABEL
    baseline_pred = pd.Series(majority, index=y_test.index)   # optional reference only
    assert list(bn_pred.index) == list(rule_pred.index) == list(y_test.index)
    predictions = {
        "Bayesian Network": bn_pred,
        "Rule-based": rule_pred,
        "Majority baseline (reference)": baseline_pred,
    }
    table = comparison_table(y_test, predictions)
    print("\n" + "=" * 78 + "\nRESULTS ON THE HELD-OUT TEST SET (positive class = 'yes')\n" + "=" * 78)
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

    # 6. Additional Scientific Investigation: Threshold Calibration Analysis
    from sklearn.model_selection import train_test_split
    from src.evaluation import find_optimal_threshold, threshold_sweep_table

    _, X_val_sub, _, y_val_sub = train_test_split(
        X_train, y_train, test_size=0.20, random_state=config.RANDOM_SEED, stratify=y_train
    )
    P_val_sub = preprocessor.transform(X_val_sub)
    val_out = bayesian_network.predict(model, P_val_sub)
    opt_tau, val_f1 = find_optimal_threshold(y_val_sub, val_out["proba_yes"])

    sweep_thresholds = [0.15, 0.20, round(opt_tau, 2), 0.30, 0.40, 0.50]
    sweep_df = threshold_sweep_table(y_test, bn_output["proba_yes"], sorted(set(sweep_thresholds)))
    save_results(sweep_df, config.RESULTS_DIR / "threshold_analysis.csv")

    print("\n" + "=" * 78)
    print("SCIENTIFIC THRESHOLD INVESTIGATION (Validation-tuned, test-evaluated)")
    print("=" * 78)
    print(f"Optimal threshold chosen on train-validation: tau* = {opt_tau:.2f} (Validation F1 = {val_f1:.4f})")
    tau_key = round(opt_tau, 2)
    print(f"Calibrated Test F1: {sweep_df.loc[tau_key, 'f1']:.4f} (Recall: {sweep_df.loc[tau_key, 'recall']:.4f}, Precision: {sweep_df.loc[tau_key, 'precision']:.4f})")
    print(f"vs. Default Cutoff (tau=0.50): F1 = {sweep_df.loc[0.50, 'f1']:.4f} (Recall: {sweep_df.loc[0.50, 'recall']:.4f}, Precision: {sweep_df.loc[0.50, 'precision']:.4f})")
    print(f"vs. Rule-Based Classifier:    F1 = {table.loc['Rule-based', 'f1']:.4f} (Recall: {table.loc['Rule-based', 'recall']:.4f}, Precision: {table.loc['Rule-based', 'precision']:.4f})")
    print(f"\nSaved metrics, plots, predictions, and threshold analysis to {config.RESULTS_DIR}")


def run_cv_experiment(df: pd.DataFrame) -> None:
    """Execute Stratified 5-Fold Cross-Validation, preventing data leakage across folds."""
    from src.cross_validation import run_stratified_cv
    from src.model_service import ModelConfig

    print("\n" + "=" * 78)
    print("STARTING STRATIFIED 5-FOLD CROSS-VALIDATION")
    print("=" * 78)
    print("Evaluating Bayesian Network, Rule-Based Classifier, and Majority Baseline...")

    cv_results = run_stratified_cv(df, cfg=ModelConfig(), n_splits=5, random_state=config.RANDOM_SEED)
    cv_results.save(config.RESULTS_DIR)
    plot_cv_comparison(cv_results.summary_df, config.RESULTS_DIR / "cv_comparison.png")

    print("\n" + cv_results.format_report())
    print(f"\nSaved cross-validation metrics, predictions, and comparison plot to {config.RESULTS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bank Marketing Bayesian Network vs. Rule-Based Classification"
    )
    parser.add_argument(
        "--mode", choices=["heldout", "cv", "all"], default=None,
        help="Evaluation mode: 'heldout' (80/20 train/test split), 'cv' (Stratified 5-Fold CV), or 'all' (both)"
    )
    parser.add_argument("--cv", action="store_true", help="Run Stratified 5-Fold Cross-Validation")
    parser.add_argument("--heldout", action="store_true", help="Run held-out 80/20 test split evaluation")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Run both heldout and cross-validation")

    args, _ = parser.parse_known_args()

    # Determine execution mode
    if args.run_all or args.mode == "all" or (args.cv and args.heldout):
        mode = "all"
    elif args.cv or args.mode == "cv":
        mode = "cv"
    else:
        # Default mode preserves backward compatibility with standard run
        mode = "heldout"

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and inspect dataset
    df = data_loader.load_dataset()
    report = data_loader.inspect_dataset(df)
    print("=" * 78, "\nDATASET INSPECTION\n" + "=" * 78)
    print(report)
    (config.RESULTS_DIR / "dataset_report.txt").write_text(report + "\n", encoding="utf-8")

    # 2. Run selected evaluation mode(s)
    if mode in ("heldout", "all"):
        run_heldout_experiment(df)

    if mode in ("cv", "all"):
        run_cv_experiment(df)


def ensure_fixed_hash_seed() -> None:
    """Re-launch this program once with PYTHONHASHSEED=0 for deterministic DAG search."""
    if os.environ.get("PYTHONHASHSEED") == "0":
        return
    env = dict(os.environ, PYTHONHASHSEED="0")
    command = [sys.executable, "-W", "ignore", "-m", "src.main", *sys.argv[1:]]
    sys.exit(subprocess.run(command, env=env, cwd=config.PROJECT_ROOT).returncode)


if __name__ == "__main__":
    ensure_fixed_hash_seed()
    main()
