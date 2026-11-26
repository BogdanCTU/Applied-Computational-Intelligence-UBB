"""Global and local explainability, suspicious method ranking, and provenance separation."""

from bug_detector.explainability.global_importance import compute_global_importances
from bug_detector.explainability.local_evidence import (
    compute_tree_path_contributions,
    rank_suspicious_methods,
)

__all__ = [
    "compute_global_importances",
    "compute_tree_path_contributions",
    "rank_suspicious_methods",
]
