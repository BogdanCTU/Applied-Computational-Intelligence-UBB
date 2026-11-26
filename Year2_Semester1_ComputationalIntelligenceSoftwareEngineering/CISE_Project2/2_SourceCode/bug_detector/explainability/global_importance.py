"""Global Random Forest impurity and held-out permutation importance by feature and group."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse
from sklearn.inspection import permutation_importance


def _unwrap_forest(estimator: Any) -> Any:
    if hasattr(estimator, "estimators_") and hasattr(estimator, "feature_importances_"):
        return estimator
    if hasattr(estimator, "calibrated_classifiers_") and estimator.calibrated_classifiers_:
        inner = estimator.calibrated_classifiers_[0].estimator
        if hasattr(inner, "feature_importances_"):
            return inner
    return None


def compute_global_importances(
    estimator: Any,
    X_eval: Any,
    y_eval: np.ndarray,
    feature_names: list[str],
    group_map: dict[str, list[int]],
    n_repeats: int = 5,
    random_state: int = 42,
    top_k: int = 25,
) -> dict[str, Any]:
    """Compute both RF impurity importances and held-out permutation importances."""
    X_dense = X_eval.toarray() if sparse.issparse(X_eval) else np.asarray(X_eval)

    forest = _unwrap_forest(estimator)
    if forest is not None:
        imp_vec = np.asarray(forest.feature_importances_, dtype=float)
    else:
        imp_vec = np.zeros(len(feature_names), dtype=float)

    perm_mean = np.zeros(len(feature_names), dtype=float)
    perm_std = np.zeros(len(feature_names), dtype=float)
    if len(y_eval) >= 20 and len(np.unique(y_eval)) >= 2:
        # Cap evaluation sample count to keep permutation runtime bounded on large sparse sets
        if len(y_eval) > 800:
            rng = np.random.default_rng(random_state)
            idx = rng.choice(len(y_eval), size=800, replace=False)
            X_sub = X_dense[idx]
            y_sub = y_eval[idx]
        else:
            X_sub = X_dense
            y_sub = y_eval
        perm = permutation_importance(
            estimator,
            X_sub,
            y_sub,
            scoring="average_precision",
            n_repeats=n_repeats,
            random_state=random_state,
            n_jobs=1,
        )
        perm_mean = np.asarray(perm.importances_mean, dtype=float)
        perm_std = np.asarray(perm.importances_std, dtype=float)

    group_summary: dict[str, dict[str, float]] = {}
    for gname, indices in group_map.items():
        if not indices:
            continue
        group_summary[gname] = {
            "num_features": float(len(indices)),
            "impurity_importance_sum": float(np.sum(imp_vec[indices])),
            "permutation_importance_sum": float(np.sum(perm_mean[indices])),
            "permutation_importance_positive_sum": float(np.sum(np.maximum(0.0, perm_mean[indices]))),
        }

    top_imp_idx = np.argsort(imp_vec)[::-1][:top_k]
    top_perm_idx = np.argsort(perm_mean)[::-1][:top_k]

    return {
        "note": "Global feature importance measures statistical association with model predictions, not causal proof of defects.",
        "group_importance": group_summary,
        "top_impurity_features": [
            {"feature": feature_names[i], "importance": round(float(imp_vec[i]), 6)}
            for i in top_imp_idx
        ],
        "top_permutation_features": [
            {
                "feature": feature_names[i],
                "importance_mean": round(float(perm_mean[i]), 6),
                "importance_std": round(float(perm_std[i]), 6),
            }
            for i in top_perm_idx
        ],
    }
