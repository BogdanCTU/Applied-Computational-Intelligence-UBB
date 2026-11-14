"""Machine Learning package."""
from ml.preprocessing import DataPreprocessor, split_by_repository, PreprocessingError
from ml.trainer import ModelTrainer
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager, ModelManagerError
from ml.predictor import (
    BugPredictor,
    MethodPrediction,
    PredictorError,
    NoMethodsFoundError,
    ModelCompatibilityError,
)
from ml.cross_validation import (
    CrossValidationError,
    InsufficientRepositoriesError,
    RepositoryReadinessReport,
    check_repository_readiness,
    RepositoryGroupKFoldValidator,
    FoldMetrics,
    CrossValidationResults,
)
from ml.experiment_runner import (
    ExperimentConfig,
    ExperimentRunner,
    ConfigurationResult,
    DEFAULT_EXPERIMENT_GRID,
)

__all__ = [
    "DataPreprocessor",
    "split_by_repository",
    "PreprocessingError",
    "ModelTrainer",
    "ModelEvaluator",
    "ModelManager",
    "ModelManagerError",
    "BugPredictor",
    "MethodPrediction",
    "PredictorError",
    "NoMethodsFoundError",
    "ModelCompatibilityError",
    "CrossValidationError",
    "InsufficientRepositoriesError",
    "RepositoryReadinessReport",
    "check_repository_readiness",
    "RepositoryGroupKFoldValidator",
    "FoldMetrics",
    "CrossValidationResults",
    "ExperimentConfig",
    "ExperimentRunner",
    "ConfigurationResult",
    "DEFAULT_EXPERIMENT_GRID",
]
