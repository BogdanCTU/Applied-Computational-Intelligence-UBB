"""Application configuration module.
Loads settings from environment variables and provides centralized paths and parameters.
Updated for CISE Project 2 sequential structure (1_Database, 2_SourceCode, etc.).
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field


def find_project_root() -> Path:
    """Dynamically determine repository root by walking upward from current file."""
    if "PROJECT_ROOT" in os.environ:
        return Path(os.environ["PROJECT_ROOT"]).resolve()
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "1_Database").exists() or (current / "2_SourceCode").exists() or (current / "pytest.ini").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent.parent


PROJECT_ROOT = find_project_root()


def register_unpickle_aliases() -> None:
    """Register in-memory module aliases in sys.modules so serialized models unpickle cleanly without legacy directories."""
    import sys
    import types

    if "src.ml.preprocessing" in sys.modules and getattr(sys.modules.get("src.ml.preprocessing"), "__name__", None) == "ml.preprocessing":
        return

    try:
        import ml
        import ml.preprocessing as ml_prep
        import database
        import repositories
        import services
        import utils

        src_mod = sys.modules.get("src") or types.ModuleType("src")
        src_mod.database = database
        src_mod.ml = ml
        src_mod.repositories = repositories
        src_mod.services = services
        src_mod.utils = utils

        sys.modules.setdefault("src", src_mod)
        sys.modules.setdefault("src.database", database)
        sys.modules.setdefault("src.ml", ml)
        sys.modules["src.ml.preprocessing"] = ml_prep
        sys.modules.setdefault("src.repositories", repositories)
        sys.modules.setdefault("src.services", services)
        sys.modules.setdefault("src.utils", utils)
    except (ImportError, AttributeError):
        pass


def _resolve_first_existing(*candidates: Path) -> Path:
    """Return the first candidate path that exists on disk, or the first candidate if none exist."""
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


class StorageSettings(BaseModel):
    """File system storage paths with sequential structure and legacy fallbacks."""
    repositories_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "1_Database" / "Repositories",
            PROJECT_ROOT / "data" / "repositories",
        )
    )
    raw_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "1_Database" / "Datasets" / "Original",
            PROJECT_ROOT / "data" / "raw",
        )
    )
    processed_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "1_Database" / "Datasets" / "Processed",
            PROJECT_ROOT / "data" / "processed",
        )
    )
    database_path: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "1_Database" / "SQLite" / "bug_detection.db",
            PROJECT_ROOT / "1_Database" / "SQLite" / "bug_detection.db",
        )
    )
    models_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "4_AppBuild" / "Assets" / "Models",
            PROJECT_ROOT / "3_TestResults" / "ModelEvaluation",
            PROJECT_ROOT / "models",
        )
    )
    exports_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "1_Database" / "Datasets" / "Processed",
            PROJECT_ROOT / "exports",
        )
    )
    reports_dir: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "3_TestResults",
            PROJECT_ROOT / "reports",
        )
    )


class GitHubSettings(BaseModel):
    """GitHub API configuration."""
    api_url: str = "https://api.github.com"
    token: str | None = None
    rate_limit_pause_threshold: int = 10
    timeout_seconds: int = 30


class RoslynSettings(BaseModel):
    """Roslyn Analyzer project settings with sequential structure support."""
    project_path: Path = Field(
        default_factory=lambda: _resolve_first_existing(
            PROJECT_ROOT / "2_SourceCode" / "RoslynAnalyzer" / "RoslynAnalyzer.csproj",
            PROJECT_ROOT / "roslyn_analyzer" / "RoslynAnalyzer.csproj",
        )
    )
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
    persist_source_code: bool = False
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
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    storage = StorageSettings(
        repositories_dir=Path(os.getenv("STORAGE_REPOSITORIES_PATH", str(StorageSettings().repositories_dir))),
        raw_dir=Path(os.getenv("STORAGE_RAW_PATH", str(StorageSettings().raw_dir))),
        processed_dir=Path(os.getenv("STORAGE_PROCESSED_PATH", str(StorageSettings().processed_dir))),
        database_path=Path(os.getenv("STORAGE_DATABASE_PATH", str(StorageSettings().database_path))),
        models_dir=Path(os.getenv("STORAGE_MODELS_PATH", str(StorageSettings().models_dir))),
        exports_dir=Path(os.getenv("STORAGE_EXPORTS_PATH", str(StorageSettings().exports_dir))),
        reports_dir=Path(os.getenv("STORAGE_REPORTS_PATH", str(StorageSettings().reports_dir))),
    )

    github = GitHubSettings(
        token=os.getenv("GITHUB_TOKEN") or None,
    )

    roslyn = RoslynSettings(
        project_path=Path(os.getenv("ROSLYN_ANALYZER_PROJECT_PATH", str(RoslynSettings().project_path)))
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
