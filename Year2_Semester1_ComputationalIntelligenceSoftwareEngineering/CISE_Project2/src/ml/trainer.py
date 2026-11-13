"""Model Trainer module implementing Random Forest classification with GroupKFold cross-validation."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

from src.ml.cross_validation import InsufficientRepositoriesError
from src.utils.logger import setup_logger

logger = setup_logger("trainer")


class ModelTrainer:
    """Trains and validates a Random Forest classifier using repository-aware GroupKFold."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 15,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        max_features: Any = "sqrt",
        class_weight: Any = "balanced",
        random_state: int = 42,
        n_jobs: int = -1,
    ) -> None:
        self.params: Dict[str, Any] = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "min_samples_leaf": min_samples_leaf,
            "max_features": max_features,
            "class_weight": class_weight,
            "random_state": random_state,
            "n_jobs": n_jobs,
        }

    def train_with_cv(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        meta_train: pd.DataFrame,
        n_splits: int = 5,
        strict_repo_count: bool = False,
    ) -> Tuple[RandomForestClassifier, Dict[str, Any], Dict[str, Any], float]:
        """Perform GroupKFold CV on training data, compare with Dummy baseline, and fit final model.
        
        Args:
            X_train: Feature matrix.
            y_train: Target labels (0 or 1).
            meta_train: Metadata containing 'repository_id'.
            n_splits: Number of cross-validation folds.
            strict_repo_count: If True, strictly requires at least n_splits distinct repository groups,
                               raising InsufficientRepositoriesError instead of fallback.
        """
        start_time = time.time()
        groups = meta_train["repository_id"].values
        unique_repos = np.unique(groups)
        n_repos = len(unique_repos)

        if strict_repo_count and n_repos < n_splits:
            missing = n_splits - n_repos
            raise InsufficientRepositoriesError(
                f"Strict GroupKFold requested {n_splits} folds, but training dataset contains only {n_repos} "
                f"distinct repositories. Missing {missing} repositories. At least {missing} additional independent "
                f"repositories must be added before running {n_splits}-fold CV without intra-repository leakage."
            )

        cv_splits = min(n_splits, n_repos)
        if cv_splits < 2:
            if strict_repo_count:
                raise InsufficientRepositoriesError(
                    f"GroupKFold requires at least 2 distinct repositories to form folds, found only {n_repos}."
                )
            logger.warning(f"Only {n_repos} repository in training set; CV folds set to 2 with duplicated grouping for technical validation.")
            cv_splits = 2
            groups = np.arange(len(y_train)) % 2

        gkf = GroupKFold(n_splits=cv_splits)

        cv_metrics: Dict[str, List[float]] = {
            "accuracy": [],
            "precision": [],
            "recall": [],
            "f1": [],
            "roc_auc": [],
            "average_precision": [],
        }
        baseline_metrics: Dict[str, List[float]] = {
            "accuracy": [],
            "f1": [],
        }

        # 1. GroupKFold Cross-Validation on Training data only
        for fold, (train_idx, val_idx) in enumerate(gkf.split(X_train, y_train, groups=groups), 1):
            X_f_tr, X_f_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_f_tr, y_f_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            # Fit fold Random Forest
            fold_rf = RandomForestClassifier(**self.params)
            fold_rf.fit(X_f_tr, y_f_tr)
            y_pred = fold_rf.predict(X_f_val)

            # Fit fold Dummy baseline (predicts most frequent class)
            dummy = DummyClassifier(strategy="most_frequent")
            dummy.fit(X_f_tr, y_f_tr)
            y_dummy_pred = dummy.predict(X_f_val)

            acc = float(accuracy_score(y_f_val, y_pred))
            prec = float(precision_score(y_f_val, y_pred, zero_division=0))
            rec = float(recall_score(y_f_val, y_pred, zero_division=0))
            f1 = float(f1_score(y_f_val, y_pred, zero_division=0))

            # ROC-AUC & PR-AUC require probability estimates
            if len(np.unique(y_f_val)) > 1 and hasattr(fold_rf, "predict_proba"):
                try:
                    y_prob = fold_rf.predict_proba(X_f_val)[:, 1]
                    auc = float(roc_auc_score(y_f_val, y_prob))
                except Exception:
                    auc = 0.5
                try:
                    ap = float(average_precision_score(y_f_val, y_prob))
                except Exception:
                    ap = float(np.mean(y_f_val == 1))
            else:
                auc = 0.5
                ap = float(np.mean(y_f_val == 1)) if len(y_f_val) > 0 else 0.0

            cv_metrics["accuracy"].append(acc)
            cv_metrics["precision"].append(prec)
            cv_metrics["recall"].append(rec)
            cv_metrics["f1"].append(f1)
            cv_metrics["roc_auc"].append(auc)
            cv_metrics["average_precision"].append(ap)

            baseline_metrics["accuracy"].append(float(accuracy_score(y_f_val, y_dummy_pred)))
            baseline_metrics["f1"].append(float(f1_score(y_f_val, y_dummy_pred, zero_division=0)))

        cv_summary = {
            metric: {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
                "folds": [round(v, 4) for v in vals],
            }
            for metric, vals in cv_metrics.items()
        }

        baseline_summary = {
            metric: {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
            }
            for metric, vals in baseline_metrics.items()
        }

        # 2. Fit final model on complete training set
        final_model = RandomForestClassifier(**self.params)
        final_model.fit(X_train, y_train)

        duration = round(time.time() - start_time, 2)
        logger.info(
            f"Random Forest trained in {duration}s. CV F1: {cv_summary['f1']['mean']:.3f} +/- {cv_summary['f1']['std']:.3f} "
            f"(vs Baseline Dummy F1: {baseline_summary['f1']['mean']:.3f})"
        )
        return final_model, cv_summary, baseline_summary, duration
