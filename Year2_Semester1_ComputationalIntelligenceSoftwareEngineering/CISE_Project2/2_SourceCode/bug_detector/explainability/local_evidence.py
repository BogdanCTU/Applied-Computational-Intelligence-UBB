"""Local TreeInterpreter / Saabas path decomposition and suspicious method ranking."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse


def _extract_forests(estimator: Any) -> list[Any]:
    if hasattr(estimator, "estimators_"):
        return [estimator]
    if hasattr(estimator, "calibrated_classifiers_") and estimator.calibrated_classifiers_:
        return [cc.estimator for cc in estimator.calibrated_classifiers_ if hasattr(cc.estimator, "estimators_")]
    return []


def compute_tree_path_contributions(
    estimator: Any,
    X_row: Any,
    feature_names: list[str],
    group_map: dict[str, list[int]],
    top_k: int = 8,
) -> dict[str, Any]:
    """
    Compute exact additive Saabas / TreeInterpreter path contributions for the BUG class (class 1)
    across all trees in a Random Forest:
        raw_forest_prob = bias + sum(contributions)
    """
    X_vec = X_row.toarray()[0] if sparse.issparse(X_row) else np.asarray(X_row).ravel()
    forests = _extract_forests(estimator)
    if not forests:
        return {
            "method": "unavailable",
            "disclaimer": "Local tree-path decomposition is only available for tree-ensemble estimators.",
            "base_rate_bias": None,
            "raw_forest_probability": None,
            "top_feature_contributions": [],
            "group_contributions": {},
        }

    n_features = len(feature_names)
    total_bias = 0.0
    total_contribs = np.zeros(n_features, dtype=np.float64)
    total_trees = 0

    for forest in forests:
        for tree_est in forest.estimators_:
            tree = tree_est.tree_
            node = 0
            # Probability of class 1 at root
            root_counts = tree.value[0, 0]
            root_sum = float(np.sum(root_counts))
            curr_prob = float(root_counts[1] / root_sum) if (root_sum > 0 and len(root_counts) > 1) else 0.5
            total_bias += curr_prob

            while tree.children_left[node] != tree.children_right[node]:
                feat_idx = int(tree.feature[node])
                thresh = float(tree.threshold[node])
                next_node = int(
                    tree.children_left[node] if X_vec[feat_idx] <= thresh else tree.children_right[node]
                )
                next_counts = tree.value[next_node, 0]
                next_sum = float(np.sum(next_counts))
                next_prob = float(next_counts[1] / next_sum) if (next_sum > 0 and len(next_counts) > 1) else curr_prob
                total_contribs[feat_idx] += (next_prob - curr_prob)
                curr_prob = next_prob
                node = next_node
            total_trees += 1

    bias = total_bias / max(total_trees, 1)
    contribs = total_contribs / max(total_trees, 1)
    raw_forest_prob = float(bias + np.sum(contribs))

    group_contributions = {
        gname: round(float(np.sum(contribs[idxs])), 6)
        for gname, idxs in group_map.items()
        if idxs
    }

    # Sort by absolute contribution magnitude
    order = np.argsort(np.abs(contribs))[::-1][:top_k]
    top_features = []
    for idx in order:
        cval = float(contribs[idx])
        if abs(cval) < 1e-6:
            continue
        top_features.append(
            {
                "feature": feature_names[idx],
                "feature_value": round(float(X_vec[idx]), 4),
                "contribution": round(cval, 6),
                "direction": "increases_bug_score" if cval > 0 else "decreases_bug_score",
            }
        )

    return {
        "method": "tree_path_saabas_decomposition",
        "disclaimer": (
            "Feature contributions explain how the Random Forest shifted its probability estimate from the "
            "training base rate; they represent learned statistical evidence, not causal proof or exact line localization."
        ),
        "base_rate_bias": round(float(bias), 6),
        "raw_forest_probability": round(raw_forest_prob, 6),
        "group_contributions": group_contributions,
        "top_feature_contributions": top_features,
    }


def rank_suspicious_methods(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign descending suspicious_rank (1 = highest bug probability) within a single source file."""
    valid = [p for p in predictions if p.get("probability") is not None]
    ordered = sorted(valid, key=lambda p: float(p["probability"]), reverse=True)
    for rank, pred in enumerate(ordered, start=1):
        pred["suspicious_rank"] = rank
    return predictions
