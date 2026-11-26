"""Machine-learning splitting, calibration, training, experiments, evaluation, and inference."""

from bug_detector.ml.calibration import (
    apply_three_way_decision,
    calibrate_three_way_thresholds,
)
from bug_detector.ml.evaluator import compute_classification_metrics
from bug_detector.ml.experiments import ExperimentSuiteRunner
from bug_detector.ml.predictor import BugDetectorPredictor
from bug_detector.ml.registry import load_model_bundle, save_model_bundle
from bug_detector.ml.splitting import build_repository_splits, verify_zero_leakage
from bug_detector.ml.trainer import train_random_forest_with_cv

__all__ = [
    "BugDetectorPredictor",
    "ExperimentSuiteRunner",
    "apply_three_way_decision",
    "build_repository_splits",
    "calibrate_three_way_thresholds",
    "compute_classification_metrics",
    "load_model_bundle",
    "save_model_bundle",
    "train_random_forest_with_cv",
    "verify_zero_leakage",
]
