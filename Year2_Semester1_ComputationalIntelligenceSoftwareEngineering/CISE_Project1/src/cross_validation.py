"""Stratified 5-Fold Cross-Validation for Bayesian Network and Rule-Based Classifiers.

Prevents data leakage by ensuring that within each fold:
  1. The dataset is partitioned into training and validation folds using StratifiedKFold.
  2. Preprocessing (category sets, quantile binning edges) is fitted exclusively on the
     fold's training data.
  3. Preprocessing transformation is applied to the validation fold without refitting.
  4. The Bayesian Network structure (DAG) is learned from scratch on the training fold.
  5. The Bayesian Network parameters (CPTs with BDeu prior) are estimated on the training fold.
  6. The Bayesian Network is evaluated on the validation fold.
  7. The Rule-Based classifier is evaluated on the exact same validation records (raw features).
  8. Majority baseline is evaluated on the exact same validation records as a reference.
  9. Fold-level metrics, out-of-fold pooled metrics, and execution diagnostics are recorded.
"""

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from src import config
from src.evaluation import compute_metrics
from src.execution_log import ExecutionLogger, global_logger
from src.preprocessing import BankPreprocessor
import bayesian_network
import rule_based


@dataclass
class FoldResult:
    """Execution telemetry and evaluation metrics for a single cross-validation fold."""
    fold: int
    train_count: int
    val_count: int
    bn_metrics: Dict[str, Any]
    rule_metrics: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    bn_edges_count: int
    duration_seconds: float


@dataclass
class CrossValidationResults:
    """Aggregated cross-validation metrics, fold breakdown, and out-of-fold predictions."""
    n_splits: int
    random_state: int
    total_duration: float
    fold_results: List[FoldResult]
    fold_metrics_df: pd.DataFrame
    summary_df: pd.DataFrame
    pooled_df: pd.DataFrame
    oof_predictions: pd.DataFrame

    def get_display_summary(self) -> pd.DataFrame:
        """User-friendly summary table formatting Mean ± Std for display."""
        cols = {
            "accuracy_display": "Accuracy (Mean ± Std)",
            "precision_display": "Precision (yes)",
            "recall_display": "Recall (yes)",
            "f1_display": "F1-Score (yes)",
            "total_TP": "Total TP",
            "total_FP": "Total FP",
            "total_FN": "Total FN",
            "total_TN": "Total TN",
        }
        df = self.summary_df[[c for c in cols if c in self.summary_df.columns]].copy()
        df.rename(columns=cols, inplace=True)
        return df

    def save(self, results_dir: Path) -> None:
        """Persist cross-validation artifacts to reproducible CSV files."""
        results_dir.mkdir(parents=True, exist_ok=True)
        self.summary_df.to_csv(results_dir / "cv_metrics_summary.csv", index_label="classifier")
        self.fold_metrics_df.to_csv(results_dir / "cv_fold_metrics.csv", index=False)
        self.pooled_df.to_csv(results_dir / "cv_pooled_metrics.csv", index_label="classifier")
        self.oof_predictions.to_csv(results_dir / "cv_predictions.csv", index_label="row_id")

    def format_report(self) -> str:
        """Formatted text report for CLI and execution logs."""
        lines = [
            "=" * 78,
            f"STRATIFIED {self.n_splits}-FOLD CROSS-VALIDATION RESULTS (seed={self.random_state})",
            "=" * 78,
            f"Total execution time: {self.total_duration:.2f} seconds",
            "",
            "1. FOLD-LEVEL SUMMARY (Mean ± Std across folds):",
            "-" * 78,
        ]
        display = self.get_display_summary()
        lines.append(display.to_string())
        lines.extend([
            "",
            "2. OUT-OF-FOLD POOLED METRICS (Evaluated on all N instances concatenated):",
            "-" * 78,
            self.pooled_df.round(4).to_string(),
            "",
            "3. FOLD-BY-FOLD BREAKDOWN:",
            "-" * 78,
            self.fold_metrics_df.round(4).to_string(index=False),
            "=" * 78,
        ])
        return "\n".join(lines)


def _compute_summary_and_pooled(
    fold_rows: List[Dict[str, Any]],
    oof_predictions: pd.DataFrame,
    classifiers: List[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aggregate fold-level statistics and calculate out-of-fold pooled metrics."""
    fold_metrics_df = pd.DataFrame(fold_rows)

    metric_keys = ["accuracy", "precision", "recall", "f1"]
    count_keys = ["TP", "FP", "FN", "TN"]

    summary_rows: Dict[str, Dict[str, Any]] = {}
    pooled_rows: Dict[str, Dict[str, Any]] = {}

    y_true_all = oof_predictions["actual"]

    for clf in classifiers:
        clf_fold_df = fold_metrics_df[fold_metrics_df["classifier"] == clf]
        row: Dict[str, Any] = {}

        # 1. Fold-level Mean and Sample Standard Deviation (ddof=1)
        for m in metric_keys:
            vals = clf_fold_df[m].to_numpy(dtype=float)
            m_mean = float(np.mean(vals))
            m_std = float(pd.Series(vals).std(ddof=1)) if len(vals) > 1 else 0.0
            row[f"{m}_mean"] = m_mean
            row[f"{m}_std"] = m_std
            row[f"{m}_display"] = f"{m_mean:.4f} ± {m_std:.4f}"

        # 2. Confusion matrix counts (total and fold mean ± std)
        for c in count_keys:
            c_vals = clf_fold_df[c].to_numpy(dtype=float)
            row[f"total_{c}"] = int(np.sum(c_vals))
            row[f"{c}_mean"] = float(np.mean(c_vals))
            row[f"{c}_std"] = float(pd.Series(c_vals).std(ddof=1)) if len(c_vals) > 1 else 0.0

        # 3. Out-of-fold pooled metrics
        # Map classifier names to oof_prediction columns
        col_map = {
            "Bayesian Network": "bayesian_network",
            "Rule-based": "rule_based",
            "Majority baseline (reference)": "majority_baseline"
        }
        pred_col = col_map.get(clf, clf.lower().replace(" ", "_"))
        if pred_col in oof_predictions.columns:
            pooled_m = compute_metrics(y_true_all, oof_predictions[pred_col])
            pooled_rows[clf] = pooled_m
            for m in metric_keys:
                row[f"pooled_{m}"] = pooled_m[m]

        summary_rows[clf] = row

    summary_df = pd.DataFrame(summary_rows).T
    pooled_df = pd.DataFrame(pooled_rows).T

    return fold_metrics_df, summary_df, pooled_df


def run_stratified_cv(
    df: pd.DataFrame,
    cfg: Optional[Any] = None,
    n_splits: int = 5,
    random_state: int = config.RANDOM_SEED,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    logger: Optional[ExecutionLogger] = None
) -> CrossValidationResults:
    """Execute complete Stratified K-Fold Cross-Validation strictly preventing data leakage."""
    log = logger or global_logger
    total_start = time.time()

    # 1. Validation & Leakage Prevention on input DataFrame
    if config.TARGET not in df.columns:
        raise ValueError(f"Target column '{config.TARGET}' not found in dataframe.")
    unexpected = set(df[config.TARGET].unique()) - set(config.LABELS)
    if unexpected:
        raise ValueError(f"Unexpected target labels: {unexpected}")
    missing_features = set(config.FEATURES) - set(df.columns)
    if missing_features:
        raise ValueError(f"Missing feature columns: {sorted(missing_features)}")

    # Extract features, explicitly excluding target and duration
    features = df[config.FEATURES].copy()
    assert config.TARGET not in features.columns, "Target leakage: 'y' in features"
    assert not set(config.EXCLUDED_FEATURES) & set(features.columns), "Leakage: duration in features"
    y = df[config.TARGET].copy()

    # Model settings
    from src.model_service import ModelConfig
    active_cfg = cfg if isinstance(cfg, ModelConfig) else ModelConfig()
    bins_dict = active_cfg.to_n_bins_dict()

    log.info("CV", f"Initializing StratifiedKFold: n_splits={n_splits}, shuffle=True, random_state={random_state}.")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    fold_results: List[FoldResult] = []
    fold_metric_rows: List[Dict[str, Any]] = []

    # Out-of-fold prediction tracking
    oof_df = pd.DataFrame(
        index=df.index,
        columns=["fold", "actual", "bayesian_network", "bn_proba_yes", "rule_based", "majority_baseline"]
    )
    oof_df["actual"] = y

    classifiers = ["Bayesian Network", "Rule-based", "Majority baseline (reference)"]

    for fold_num, (train_idx, val_idx) in enumerate(skf.split(features, y), start=1):
        fold_start = time.time()
        progress_base = (fold_num - 1) / n_splits
        progress_step = 1.0 / n_splits

        def update_progress(msg: str, sub_frac: float):
            if progress_callback:
                overall_frac = progress_base + (sub_frac * progress_step)
                progress_callback(f"Fold {fold_num}/{n_splits}: {msg}", min(0.99, overall_frac))

        update_progress("Splitting fold subsets...", 0.05)
        log.info("CV", f"--- Starting Fold {fold_num}/{n_splits} (train={len(train_idx)}, val={len(val_idx)}) ---")

        # Partition fold subsets
        X_train_fold = features.iloc[train_idx].copy()
        y_train_fold = y.iloc[train_idx].copy()
        X_val_fold = features.iloc[val_idx].copy()
        y_val_fold = y.iloc[val_idx].copy()

        # Step 2 & 3: Fit preprocessor strictly on training fold only, transform validation without refit
        update_progress("Fitting preprocessing on training fold only...", 0.20)
        preprocessor = BankPreprocessor(n_bins=bins_dict).fit(X_train_fold)
        P_train_fold = preprocessor.transform(X_train_fold)
        P_val_fold = preprocessor.transform(X_val_fold)

        # Step 4: Learn Bayesian Network DAG on training fold only
        update_progress("Learning Bayesian Network DAG structure...", 0.40)
        train_table = P_train_fold.assign(**{config.TARGET: y_train_fold})
        edges = bayesian_network.learn_structure(
            train_table,
            max_indegree=active_cfg.max_indegree,
            scoring_method=active_cfg.scoring_method
        )

        # Step 5: Parameter estimation on training fold only
        update_progress("Estimating CPT parameters (BDeu prior)...", 0.60)
        state_names = {c: preprocessor.states(c) for c in config.FEATURES}
        state_names[config.TARGET] = config.LABELS
        model = bayesian_network.build_network(edges, list(train_table.columns))
        bayesian_network.fit_parameters(
            model,
            train_table,
            state_names=state_names,
            equivalent_sample_size=active_cfg.equivalent_sample_size
        )

        # Step 6: Bayesian Network validation inference
        update_progress("Inferring probabilities on validation fold...", 0.75)
        bn_out = bayesian_network.predict(model, P_val_fold)
        bn_pred = bn_out["prediction"]
        bn_proba = bn_out["proba_yes"]

        # Step 7: Rule-Based Classifier on exact same validation fold (raw features)
        update_progress("Evaluating Rule-Based Classifier...", 0.88)
        rule_pred = rule_based.predict_rules(X_val_fold)

        # Majority baseline on exact same validation fold
        baseline_pred = pd.Series(config.NEGATIVE_LABEL, index=y_val_fold.index)

        # Ensure index alignment
        assert list(bn_pred.index) == list(rule_pred.index) == list(y_val_fold.index)

        # Record out-of-fold predictions
        val_indices = df.index[val_idx]
        oof_df.loc[val_indices, "fold"] = fold_num
        oof_df.loc[val_indices, "bayesian_network"] = bn_pred.values
        oof_df.loc[val_indices, "bn_proba_yes"] = bn_proba.values
        oof_df.loc[val_indices, "rule_based"] = rule_pred.values
        oof_df.loc[val_indices, "majority_baseline"] = baseline_pred.values

        # Step 8: Compute metrics for each classifier on this fold
        update_progress("Computing fold metrics...", 0.95)
        bn_m = compute_metrics(y_val_fold, bn_pred)
        rule_m = compute_metrics(y_val_fold, rule_pred)
        base_m = compute_metrics(y_val_fold, baseline_pred)

        fold_duration = time.time() - fold_start

        fold_results.append(FoldResult(
            fold=fold_num,
            train_count=len(train_idx),
            val_count=len(val_idx),
            bn_metrics=bn_m,
            rule_metrics=rule_m,
            baseline_metrics=base_m,
            bn_edges_count=len(edges),
            duration_seconds=fold_duration
        ))

        # Store rows for fold_metrics_df
        for name, m in [("Bayesian Network", bn_m), ("Rule-based", rule_m), ("Majority baseline (reference)", base_m)]:
            row = {"classifier": name, "fold": fold_num, "duration_seconds": fold_duration}
            row.update(m)
            fold_metric_rows.append(row)

        log.info(
            "CV",
            f"Fold {fold_num} finished in {fold_duration:.2f}s: "
            f"BN F1={bn_m['f1']:.4f}, Rule F1={rule_m['f1']:.4f}, Base F1={base_m['f1']:.4f}."
        )

    total_duration = time.time() - total_start
    if progress_callback:
        progress_callback("Aggregating cross-validation results...", 1.0)

    # Compute summary and pooled tables
    fold_metrics_df, summary_df, pooled_df = _compute_summary_and_pooled(
        fold_metric_rows, oof_df, classifiers
    )

    results = CrossValidationResults(
        n_splits=n_splits,
        random_state=random_state,
        total_duration=total_duration,
        fold_results=fold_results,
        fold_metrics_df=fold_metrics_df,
        summary_df=summary_df,
        pooled_df=pooled_df,
        oof_predictions=oof_df
    )

    log.success(
        "CV",
        f"Completed {n_splits}-fold cross-validation in {total_duration:.2f}s. "
        f"Mean F1: BN={summary_df.loc['Bayesian Network', 'f1_mean']:.4f} ± {summary_df.loc['Bayesian Network', 'f1_std']:.4f}, "
        f"Rule={summary_df.loc['Rule-based', 'f1_mean']:.4f} ± {summary_df.loc['Rule-based', 'f1_std']:.4f}."
    )

    return results


def load_cv_results(results_dir: Path) -> Optional[CrossValidationResults]:
    """Load previously saved cross-validation results from disk if available."""
    summary_path = results_dir / "cv_metrics_summary.csv"
    fold_path = results_dir / "cv_fold_metrics.csv"
    pooled_path = results_dir / "cv_pooled_metrics.csv"
    pred_path = results_dir / "cv_predictions.csv"

    if not (summary_path.exists() and fold_path.exists() and pooled_path.exists()):
        return None

    try:
        summary_df = pd.read_csv(summary_path, index_col="classifier")
        fold_metrics_df = pd.read_csv(fold_path)
        pooled_df = pd.read_csv(pooled_path, index_col="classifier")
        oof_predictions = pd.read_csv(pred_path, index_col="row_id") if pred_path.exists() else pd.DataFrame()

        n_splits = int(fold_metrics_df["fold"].nunique()) if not fold_metrics_df.empty else 5

        # Build dummy FoldResult objects from fold_metrics_df
        fold_results: List[FoldResult] = []
        for f in range(1, n_splits + 1):
            f_slice = fold_metrics_df[fold_metrics_df["fold"] == f]
            bn_row = f_slice[f_slice["classifier"] == "Bayesian Network"]
            rule_row = f_slice[f_slice["classifier"] == "Rule-based"]
            base_row = f_slice[f_slice["classifier"].str.startswith("Majority")]

            dur = float(f_slice["duration_seconds"].iloc[0]) if "duration_seconds" in f_slice else 0.0

            bn_dict = bn_row.iloc[0].to_dict() if not bn_row.empty else {}
            rule_dict = rule_row.iloc[0].to_dict() if not rule_row.empty else {}
            base_dict = base_row.iloc[0].to_dict() if not base_row.empty else {}

            fold_results.append(FoldResult(
                fold=f,
                train_count=0,
                val_count=0,
                bn_metrics=bn_dict,
                rule_metrics=rule_dict,
                baseline_metrics=base_dict,
                bn_edges_count=0,
                duration_seconds=dur
            ))

        total_dur = float(fold_metrics_df["duration_seconds"].sum()) if "duration_seconds" in fold_metrics_df else 0.0

        return CrossValidationResults(
            n_splits=n_splits,
            random_state=config.RANDOM_SEED,
            total_duration=total_dur,
            fold_results=fold_results,
            fold_metrics_df=fold_metrics_df,
            summary_df=summary_df,
            pooled_df=pooled_df,
            oof_predictions=oof_predictions
        )
    except Exception:
        return None
