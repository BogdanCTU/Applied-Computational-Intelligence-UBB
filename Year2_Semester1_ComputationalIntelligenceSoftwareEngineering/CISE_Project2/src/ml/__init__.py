"""Machine Learning package."""
from src.ml.preprocessing import DataPreprocessor, split_by_repository, PreprocessingError
from src.ml.trainer import ModelTrainer
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager, ModelManagerError
from src.ml.predictor import (
    BugPredictor,
    MethodPrediction,
    PredictorError,
    NoMethodsFoundError,
    ModelCompatibilityError,
)
from src.ml.cross_validation import (
    CrossValidationError,
    InsufficientRepositoriesError,
    RepositoryReadinessReport,
    check_repository_readiness,
    RepositoryGroupKFoldValidator,
    FoldMetrics,
    CrossValidationResults,
)
from src.ml.experiment_runner import (
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
