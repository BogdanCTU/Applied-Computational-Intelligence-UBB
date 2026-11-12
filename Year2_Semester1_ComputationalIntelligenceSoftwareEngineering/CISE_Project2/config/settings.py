"""Application configuration module.
Loads settings from environment variables and provides centralized paths and parameters.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Root directory of the repository
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class StorageSettings(BaseModel):
    """File system storage paths."""
    repositories_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "repositories")
    raw_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "raw")
    processed_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "processed")
    database_path: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "database" / "bug_detection.db")
    models_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "models")
    exports_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "exports")
    reports_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "reports")


class GitHubSettings(BaseModel):
    """GitHub API configuration."""
    api_url: str = "https://api.github.com"
    token: str | None = None
    rate_limit_pause_threshold: int = 10
    timeout_seconds: int = 30


class RoslynSettings(BaseModel):
    """Roslyn Analyzer project settings."""
    project_path: Path = Field(default_factory=lambda: PROJECT_ROOT / "roslyn_analyzer" / "RoslynAnalyzer.csproj")
    assembly_path: Path | None = None
    timeout_seconds: int = 60


class MLSettings(BaseModel):
    """Machine learning hyperparameters and validation defaults."""
    default_n_estimators: int = 100
    default_max_depth: int | None = 15
    default_min_samples_split: int = 5
    default_min_samples_leaf: int = 2
    default_random_state: int = 42
    default_test_size: float = 0.25
    group_by: str = "repository"


class PredictionSettings(BaseModel):
    """Real-time defect prediction presentation and privacy settings."""
    low_risk_threshold: float = 0.30
    medium_risk_threshold: float = 0.60
    persist_history: bool = True
    persist_source_code: bool = False  # Privacy: do not persist raw code by default
    default_model_id: int | None = None


class AppSettings(BaseModel):
    """Overall application configuration."""
    app_name: str = "C# Defect Predictor"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    storage: StorageSettings = Field(default_factory=StorageSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    roslyn: RoslynSettings = Field(default_factory=RoslynSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    prediction: PredictionSettings = Field(default_factory=PredictionSettings)

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        for path in [
            self.storage.repositories_dir,
            self.storage.raw_dir,
            self.storage.processed_dir,
            self.storage.database_path.parent,
            self.storage.models_dir,
            self.storage.exports_dir,
            self.storage.reports_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> AppSettings:
    """Load settings with environment variable overrides."""
    # Check for .env file if present
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    storage = StorageSettings(
        repositories_dir=Path(os.getenv("STORAGE_REPOSITORIES_PATH", PROJECT_ROOT / "data" / "repositories")),
        raw_dir=Path(os.getenv("STORAGE_RAW_PATH", PROJECT_ROOT / "data" / "raw")),
        processed_dir=Path(os.getenv("STORAGE_PROCESSED_PATH", PROJECT_ROOT / "data" / "processed")),
        database_path=Path(os.getenv("STORAGE_DATABASE_PATH", PROJECT_ROOT / "data" / "database" / "bug_detection.db")),
        models_dir=Path(os.getenv("STORAGE_MODELS_PATH", PROJECT_ROOT / "models")),
        exports_dir=Path(os.getenv("STORAGE_EXPORTS_PATH", PROJECT_ROOT / "exports")),
        reports_dir=Path(os.getenv("STORAGE_REPORTS_PATH", PROJECT_ROOT / "reports")),
    )

    github = GitHubSettings(
        token=os.getenv("GITHUB_TOKEN") or None,
    )

    roslyn = RoslynSettings(
        project_path=Path(os.getenv("ROSLYN_ANALYZER_PROJECT_PATH", PROJECT_ROOT / "roslyn_analyzer" / "RoslynAnalyzer.csproj"))
    )

    prediction = PredictionSettings(
        low_risk_threshold=float(os.getenv("PREDICTION_LOW_THRESHOLD", "0.30")),
        medium_risk_threshold=float(os.getenv("PREDICTION_MED_THRESHOLD", "0.60")),
        persist_history=os.getenv("PREDICTION_PERSIST_HISTORY", "true").lower() in ("true", "1", "yes"),
        persist_source_code=os.getenv("PREDICTION_PERSIST_SOURCE", "false").lower() in ("true", "1", "yes"),
    )

    app = AppSettings(
        debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        storage=storage,
        github=github,
        roslyn=roslyn,
        prediction=prediction,
    )
    app.ensure_directories()
    return app

