"""Repository-aware cross-validation, precision-oriented threshold selection, and leakage prevention."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    brier_score_loss,
)

from ml.preprocessing import DataPreprocessor, PreprocessingError
from utils.logger import setup_logger

logger = setup_logger("cross_validation")


class CrossValidationError(Exception):
    """Base exception for cross-validation failures."""
    pass


class InsufficientRepositoriesError(CrossValidationError):
    """Raised when repository count is insufficient for the requested GroupKFold split count."""
    pass


@dataclass
class RepositoryReadinessReport:
    """Diagnostic report on repository group availability for cross-validation."""
    is_ready: bool
    available_repo_count: int
    required_repo_count: int
    missing_repo_count: int
    unique_repositories: List[Any]
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "available_repo_count": self.available_repo_count,
            "required_repo_count": self.required_repo_count,
            "missing_repo_count": self.missing_repo_count,
            "unique_repositories": [str(r) for r in self.unique_repositories],
            "recommendation": self.recommendation,
        }


def check_repository_readiness(
    metadata: pd.DataFrame,
    n_splits: int = 5,
    group_col: str = "repository_id",
) -> RepositoryReadinessReport:
    """Inspect repository grouping and determine feasibility for GroupKFold."""
    if group_col not in metadata.columns:
        raise CrossValidationError(f"Metadata DataFrame is missing required grouping column '{group_col}'.")

    unique_repos = sorted(list(metadata[group_col].dropna().unique()))
    avail = len(unique_repos)
    missing = max(0, n_splits - avail)
    is_ready = avail >= n_splits

    if is_ready:
        recommendation = (
            f"Dataset has {avail} distinct repositories, which satisfies the {n_splits}-fold GroupKFold requirement."
        )
    else:
        recommendation = (
            f"Dataset has only {avail} distinct repositories in the training partition, but {n_splits}-fold "
            f"GroupKFold requires at least {n_splits}. Exactly {missing} additional independent repositories must "
            f"be mined and added to the training set before running strict {n_splits}-fold CV without leakage."
        )

    return RepositoryReadinessReport(
        is_ready=is_ready,
        available_repo_count=avail,
        required_repo_count=n_splits,
        missing_repo_count=missing,
        unique_repositories=unique_repos,
        recommendation=recommendation,
    )


@dataclass
class FoldMetrics:
    """Comprehensive evaluation metrics for an individual validation fold."""
    fold_index: int
    train_repo_count: int
    val_repo_count: int
    train_sample_count: int
    val_sample_count: int
    train_buggy_count: int
    train_clean_count: int
    val_buggy_count: int
    val_clean_count: int
    train_repos: List[Any]
    val_repos: List[Any]
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    average_precision: float
    brier_score: float
    confusion_matrix: List[List[int]]
    train_duration_s: float
    val_duration_s: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "train_repo_count": self.train_repo_count,
            "val_repo_count": self.val_repo_count,
            "train_sample_count": self.train_sample_count,
            "val_sample_count": self.val_sample_count,
            "train_buggy_count": self.train_buggy_count,
            "train_clean_count": self.train_clean_count,
            "val_buggy_count": self.val_buggy_count,
            "val_clean_count": self.val_clean_count,
            "train_repos": [str(r) for r in self.train_repos],
            "val_repos": [str(r) for r in self.val_repos],
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "roc_auc": round(self.roc_auc, 4),
            "average_precision": round(self.average_precision, 4),
            "brier_score": round(self.brier_score, 4),
            "confusion_matrix": self.confusion_matrix,
            "train_duration_s": round(self.train_duration_s, 4),
            "val_duration_s": round(self.val_duration_s, 4),
        }


@dataclass
class CrossValidationResults:
    """Aggregate cross-validation results across all folds."""
    n_splits: int
    n_repos: int
    fold_metrics: List[FoldMetrics]
    aggregate_metrics: Dict[str, Dict[str, float]]
    total_duration_s: float
    baseline_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    oof_predictions: Optional[Dict[str, List[float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "n_splits": self.n_splits,
            "n_repos": self.n_repos,
            "aggregate_metrics": self.aggregate_metrics,
            "baseline_metrics": self.baseline_metrics,
            "total_duration_s": round(self.total_duration_s, 3),
            "folds": [f.to_dict() for f in self.fold_metrics],
        }
        if self.oof_predictions:
            res["oof_prediction_summary"] = {
                "total_samples": len(self.oof_predictions.get("y_true", [])),
                "mean_predicted_risk": round(float(np.mean(self.oof_predictions.get("y_prob", [0.0]))), 4),
            }
        return res


def compute_threshold_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    thresholds: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate classification performance across decision thresholds strictly on CV predictions."""
    if thresholds is None:
        thresholds = [0.20, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]

    y_true_arr = np.asarray(y_true).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)

    curve = []
    for t in thresholds:
        y_pred = (y_prob_arr >= t).astype(int)
        acc = float(accuracy_score(y_true_arr, y_pred))
        prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
        rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
        f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))
        f05 = float(fbeta_score(y_true_arr, y_pred, beta=0.5, zero_division=0))
        cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1]).tolist()
        tn, fp = cm[0][0], cm[0][1]
        fn, tp = cm[1][0], cm[1][1]
        fpr = float(fp / max(1, fp + tn))
        fnr = float(fn / max(1, fn + tp))
        curve.append({
            "threshold": round(float(t), 4),
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "f05": round(f05, 4),
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
            "predicted_positives": int(tp + fp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        })
    return curve


def select_classifier_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_precision_target: float = 0.77,
    min_precision_floor: float = 0.75,
    min_recall: float = 0.50,
    min_predicted_positives: int = 5,
    thresholds: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Select decision threshold strictly on CV probabilities optimizing F1/Recall above the 75% precision floor."""
    if thresholds is None:
        thresholds = [round(x, 2) for x in np.arange(0.30, 0.90, 0.02)]

    curve = compute_threshold_curve(y_true, y_prob, thresholds=thresholds)
    nontrivial = [c for c in curve if c["predicted_positives"] >= min_predicted_positives]
    if not nontrivial:
        nontrivial = [c for c in curve if c["predicted_positives"] >= 1] or curve

    tier1 = [
        c for c in nontrivial
        if c["precision"] >= min_precision_target and c["recall"] >= min_recall
    ]
    if tier1:
        best = max(tier1, key=lambda c: (c["f1"], c["recall"], c["precision"]))
        criterion = f"tier1_precision>={min_precision_target:.2f}_recall>={min_recall:.2f}_max_f1_recall"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    tier2 = [
        c for c in nontrivial
        if c["precision"] >= min_precision_floor and c["recall"] >= min_recall
    ]
    if tier2:
        best = max(tier2, key=lambda c: (c["f1"], c["recall"], c["precision"]))
        criterion = f"tier2_precision>={min_precision_floor:.2f}_recall>={min_recall:.2f}_max_f1_recall"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    tier3 = [c for c in nontrivial if c["recall"] >= min_recall]
    if tier3:
        best = max(tier3, key=lambda c: (c["f1"], c["precision"], c["recall"]))
        criterion = f"tier3_recall>={min_recall:.2f}_max_f1"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    best = max(nontrivial, key=lambda c: (c["f1"], c["precision"]))
    return {
        "selected_threshold": best["threshold"],
        "criterion": "tier4_fallback_max_f1",
        "inner_metrics": best,
        "curve": curve,
    }


def select_precision_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_precision_preferred: float = 0.80,
    min_precision_acceptable: float = 0.75,
    min_recall: float = 0.50,
    min_predicted_positives: int = 5,
    thresholds: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Select an operating decision threshold strictly from inner-fold CV probabilities.

    Prioritizes Precision >= 0.80 (then >= 0.75) while keeping meaningful recall (>= 0.50)
    and avoiding degenerate thresholds that flag almost nothing.
    """
    if thresholds is None:
        thresholds = [round(x, 2) for x in np.arange(0.30, 0.90, 0.02)]

    curve = compute_threshold_curve(y_true, y_prob, thresholds=thresholds)
    nontrivial = [c for c in curve if c["predicted_positives"] >= min_predicted_positives]
    if not nontrivial:
        nontrivial = [c for c in curve if c["predicted_positives"] >= 1] or curve

    tier1 = [
        c for c in nontrivial
        if c["precision"] >= min_precision_preferred and c["recall"] >= min_recall
    ]
    if tier1:
        best = max(tier1, key=lambda c: (c["f05"], c["precision"], c["f1"]))
        criterion = f"tier1_precision>={min_precision_preferred:.2f}_recall>={min_recall:.2f}_max_f05"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    tier2 = [
        c for c in nontrivial
        if c["precision"] >= min_precision_acceptable and c["recall"] >= min_recall
    ]
    if tier2:
        best = max(tier2, key=lambda c: (c["f05"], c["f1"], c["precision"]))
        criterion = f"tier2_precision>={min_precision_acceptable:.2f}_recall>={min_recall:.2f}_max_f05"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    tier3 = [c for c in nontrivial if c["recall"] >= min_recall]
    if tier3:
        best = max(tier3, key=lambda c: (c["f05"], c["precision"], c["f1"]))
        criterion = f"tier3_recall>={min_recall:.2f}_max_f05"
        return {"selected_threshold": best["threshold"], "criterion": criterion, "inner_metrics": best, "curve": curve}

    best = max(nontrivial, key=lambda c: (c["f05"], c["f1"], c["precision"]))
    return {
        "selected_threshold": best["threshold"],
        "criterion": "tier4_fallback_max_f05",
        "inner_metrics": best,
        "curve": curve,
    }


def compute_binary_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Compute complete classification, ranking, and calibration metrics at a given threshold."""
    y_t = np.asarray(y_true).astype(int)
    y_p = np.asarray(y_prob).astype(float)
    y_pred = (y_p >= threshold).astype(int)

    acc = float(accuracy_score(y_t, y_pred))
    prec = float(precision_score(y_t, y_pred, zero_division=0))
    rec = float(recall_score(y_t, y_pred, zero_division=0))
    f1 = float(f1_score(y_t, y_pred, zero_division=0))
    f05 = float(fbeta_score(y_t, y_pred, beta=0.5, zero_division=0))

    cm = confusion_matrix(y_t, y_pred, labels=[0, 1]).tolist()
    tn, fp = cm[0][0], cm[0][1]
    fn, tp = cm[1][0], cm[1][1]
    fpr = float(fp / max(1, fp + tn))
    fnr = float(fn / max(1, fn + tp))

    has_multi = len(np.unique(y_t)) > 1
    roc_auc = float(roc_auc_score(y_t, y_p)) if has_multi else 0.5
    pr_auc = float(average_precision_score(y_t, y_p)) if has_multi else float(np.mean(y_t == 1))
    brier = float(brier_score_loss(y_t, y_p)) if len(y_t) > 0 else 0.5

    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "f05": round(f05, 4),
        "fpr": round(fpr, 4),
        "fnr": round(fnr, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "detected_defects": int(tp),
        "total_defects": int(tp + fn),
        "confusion_matrix": cm,
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def compute_bayesian_precision(sensitivity: float, false_positive_rate: float, prevalence: float) -> float:
    """Estimate expected precision under a target base-rate prevalence using Bayes' theorem."""
    denom = sensitivity * prevalence + false_positive_rate * (1.0 - prevalence)
    if denom <= 0.0:
        return 0.0
    return round((sensitivity * prevalence) / denom, 4)


class RepositoryGroupKFoldValidator:
    """Executes strict repository-aware cross-validation with per-fold isolated preprocessing."""

    def __init__(
        self,
        n_splits: int = 5,
        strict_repo_count: bool = True,
        impute_missing: bool = True,
        remove_constant: bool = True,
        group_col: str = "repository_id",
    ) -> None:
        self.n_splits = n_splits
        self.strict_repo_count = strict_repo_count
        self.impute_missing = impute_missing
        self.remove_constant = remove_constant
        self.group_col = group_col

    def validate_and_generate_splits(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        metadata: pd.DataFrame,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Validate grouping constraints and generate leakage-free fold indices."""
        if self.group_col not in metadata.columns:
            raise CrossValidationError(f"Metadata must contain '{self.group_col}' column.")

        groups = metadata[self.group_col].values
        unique_repos = np.unique(groups)
        n_repos = len(unique_repos)

        if self.strict_repo_count and n_repos < self.n_splits:
            missing = self.n_splits - n_repos
            raise InsufficientRepositoriesError(
                f"Requested {self.n_splits}-fold GroupKFold cross-validation, but training dataset contains only "
                f"{n_repos} distinct repositories ({list(unique_repos)}). At least {missing} additional repositories "
                f"must be collected to run {self.n_splits}-fold cross-validation without intra-repository leakage. "
                f"Falling back to non-group splits or random KFold is strictly disallowed."
            )

        splits_to_use = min(self.n_splits, n_repos)
        if splits_to_use < 2:
            raise InsufficientRepositoriesError(
                f"GroupKFold requires at least 2 distinct repositories to form folds, found only {n_repos}."
            )

        gkf = GroupKFold(n_splits=splits_to_use)
        splits = list(gkf.split(X, y, groups=groups))

        repo_val_appearances: Dict[Any, int] = {r: 0 for r in unique_repos}

        for fold_idx, (train_idx, val_idx) in enumerate(splits, 1):
            train_r = set(metadata.iloc[train_idx][self.group_col].unique())
            val_r = set(metadata.iloc[val_idx][self.group_col].unique())

            overlap = train_r.intersection(val_r)
            if overlap:
                raise CrossValidationError(
                    f"Fatal repository leakage in fold {fold_idx}: Repositories present in both train and val: {overlap}"
                )

            for r in val_r:
                repo_val_appearances[r] += 1

        for r, count in repo_val_appearances.items():
            if count != 1:
                raise CrossValidationError(
                    f"Repository '{r}' appeared in {count} validation folds; expected exactly 1."
                )

        return splits

    def evaluate_model(
        self,
        model_factory: Callable[[], Any],
        X_train_raw: pd.DataFrame,
        y_train: pd.Series,
        meta_train: pd.DataFrame,
        needs_scaling: bool = False,
    ) -> CrossValidationResults:
        """Run GroupKFold cross-validation with independent per-fold preprocessing and optional scaling."""
        start_time = time.time()
        splits = self.validate_and_generate_splits(X_train_raw, y_train, meta_train)
        groups = meta_train[self.group_col].values
        n_repos = len(np.unique(groups))

        fold_metrics_list: List[FoldMetrics] = []
        oof_y_true: List[int] = []
        oof_y_prob: List[float] = []

        for fold_idx, (train_idx, val_idx) in enumerate(splits, 1):
            X_f_tr_raw = X_train_raw.iloc[train_idx].copy()
            X_f_val_raw = X_train_raw.iloc[val_idx].copy()
            y_f_tr = y_train.iloc[train_idx].copy()
            y_f_val = y_train.iloc[val_idx].copy()
            meta_f_tr = meta_train.iloc[train_idx]
            meta_f_val = meta_train.iloc[val_idx]

            train_repos = sorted(list(meta_f_tr[self.group_col].unique()))
            val_repos = sorted(list(meta_f_val[self.group_col].unique()))

            preproc = DataPreprocessor(
                impute_missing=self.impute_missing,
                remove_constant=self.remove_constant,
            )
            X_f_tr = preproc.fit_transform(X_f_tr_raw)
            X_f_val = preproc.transform(X_f_val_raw)

            if needs_scaling:
                scaler = StandardScaler()
                X_f_tr = pd.DataFrame(
                    scaler.fit_transform(X_f_tr),
                    columns=X_f_tr.columns,
                    index=X_f_tr.index,
                )
                X_f_val = pd.DataFrame(
                    scaler.transform(X_f_val),
                    columns=X_f_val.columns,
                    index=X_f_val.index,
                )

            t_train_start = time.time()
            model = model_factory()
            model.fit(X_f_tr, y_f_tr)
            train_duration = time.time() - t_train_start

            t_val_start = time.time()
            y_pred = model.predict(X_f_val)
            val_duration = time.time() - t_val_start

            has_proba = hasattr(model, "predict_proba")
            y_prob = model.predict_proba(X_f_val)[:, 1] if has_proba else None

            acc = float(accuracy_score(y_f_val, y_pred))
            prec = float(precision_score(y_f_val, y_pred, zero_division=0))
            rec = float(recall_score(y_f_val, y_pred, zero_division=0))
            f1 = float(f1_score(y_f_val, y_pred, zero_division=0))

            has_multiclass = len(np.unique(y_f_val)) > 1
            if has_multiclass and y_prob is not None:
                try:
                    auc = float(roc_auc_score(y_f_val, y_prob))
                except Exception:
                    auc = 0.5
                try:
                    ap = float(average_precision_score(y_f_val, y_prob))
                except Exception:
                    ap = float(np.mean(y_f_val == 1))
                try:
                    brier = float(brier_score_loss(y_f_val, y_prob))
                except Exception:
                    brier = 0.5
            else:
                auc = 0.5
                ap = float(np.mean(y_f_val == 1)) if len(y_f_val) > 0 else 0.0
                brier = 0.5

            cm = confusion_matrix(y_f_val, y_pred, labels=[0, 1]).tolist()

            oof_y_true.extend(y_f_val.tolist())
            if y_prob is not None:
                oof_y_prob.extend(y_prob.tolist())
            else:
                oof_y_prob.extend(y_pred.tolist())

            fold_metric = FoldMetrics(
                fold_index=fold_idx,
                train_repo_count=len(train_repos),
                val_repo_count=len(val_repos),
                train_sample_count=len(X_f_tr),
                val_sample_count=len(X_f_val),
                train_buggy_count=int((y_f_tr == 1).sum()),
                train_clean_count=int((y_f_tr == 0).sum()),
                val_buggy_count=int((y_f_val == 1).sum()),
                val_clean_count=int((y_f_val == 0).sum()),
                train_repos=train_repos,
                val_repos=val_repos,
                accuracy=acc,
                precision=prec,
                recall=rec,
                f1=f1,
                roc_auc=auc,
                average_precision=ap,
                brier_score=brier,
                confusion_matrix=cm,
                train_duration_s=train_duration,
                val_duration_s=val_duration,
            )
            fold_metrics_list.append(fold_metric)

        total_duration = time.time() - start_time

        metric_keys = [
            "accuracy", "precision", "recall", "f1", "roc_auc",
            "average_precision", "brier_score", "train_duration_s", "val_duration_s"
        ]
        aggregate: Dict[str, Dict[str, float]] = {}

        for k in metric_keys:
            vals = [getattr(fm, k) for fm in fold_metrics_list]
            aggregate[k] = {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
                "min": round(float(np.min(vals)), 4),
                "max": round(float(np.max(vals)), 4),
            }

        return CrossValidationResults(
            n_splits=len(splits),
            n_repos=n_repos,
            fold_metrics=fold_metrics_list,
            aggregate_metrics=aggregate,
            baseline_metrics={},
            total_duration_s=total_duration,
            oof_predictions={"y_true": oof_y_true, "y_prob": oof_y_prob},
        )
