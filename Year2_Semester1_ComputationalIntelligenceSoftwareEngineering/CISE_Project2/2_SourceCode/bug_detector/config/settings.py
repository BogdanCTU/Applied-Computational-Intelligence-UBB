"""Pydantic v2 configuration models and persistence for v5.0.0."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

EXPERIMENT_DEFINITIONS: dict[str, list[str]] = {
    "A": ["structural"],
    "B": ["lexical"],
    "C": ["ast"],
    "D": ["control_flow"],
    "E": ["data_flow"],
    "F": ["lexical", "ast"],
    "G": ["lexical", "ast", "control_flow"],
    "H": ["lexical", "ast", "control_flow", "data_flow"],
    "I": ["lexical", "ast", "control_flow", "data_flow", "structural"],
}

ALL_FEATURE_GROUPS = ("lexical", "ast", "control_flow", "data_flow", "structural")


def get_project_root() -> Path:
    """Resolve the CISE_Project2 root directory dynamically from this module's location."""
    return Path(__file__).resolve().parents[3]


class CollectionConfig(BaseModel):
    """Settings for dataset acquisition from InferredBugs, GitHub, and hard negatives."""

    inferredbugs_repo_url: str = "https://github.com/microsoft/InferredBugs.git"
    inferredbugs_max_records: int = Field(default=5000, ge=1, le=50000)
    github_max_repos: int = Field(default=60, ge=1, le=500)
    github_max_commits_per_repo: int = Field(default=400, ge=10, le=5000)
    github_max_pairs_per_repo: int = Field(default=20, ge=1, le=200)
    github_max_changed_files: int = Field(default=3, ge=1, le=10)
    github_max_changed_lines_per_method: int = Field(default=40, ge=5, le=200)
    hard_negatives_max_repos: int = Field(default=45, ge=1, le=200)
    hard_negatives_max_per_repo: int = Field(default=25, ge=1, le=200)
    hard_negative_min_complexity: int = Field(default=4, ge=1, le=50)
    hard_negative_min_logical_loc: int = Field(default=12, ge=3, le=200)
    github_api_timeout_seconds: int = Field(default=20, ge=5, le=120)
    github_api_max_retries: int = Field(default=4, ge=1, le=10)


class NormalizationConfig(BaseModel):
    """Controlled C# source-code normalization options."""

    strip_comments: bool = True
    collapse_whitespace: bool = True
    abstract_string_literals: bool = True
    abstract_numeric_literals: bool = True
    preserve_special_literals: bool = True
    preserve_identifiers: bool = True
    preserve_api_names: bool = True
    preserve_type_names: bool = True


class FeatureConfig(BaseModel):
    """Feature group selection and lexical vectorizer settings."""

    experiment_code: Literal["A", "B", "C", "D", "E", "F", "G", "H", "I"] = "I"
    enabled_groups: list[Literal["lexical", "ast", "control_flow", "data_flow", "structural"]] = Field(
        default_factory=lambda: list(ALL_FEATURE_GROUPS)
    )
    tfidf_max_token_features: int = Field(default=300, ge=20, le=5000)
    tfidf_max_api_features: int = Field(default=100, ge=10, le=1000)
    tfidf_ngram_min: int = Field(default=1, ge=1, le=3)
    tfidf_ngram_max: int = Field(default=2, ge=1, le=4)
    tfidf_min_df: int = Field(default=2, ge=1, le=50)

    @model_validator(mode="after")
    def validate_ngrams_and_groups(self) -> "FeatureConfig":
        if self.tfidf_ngram_min > self.tfidf_ngram_max:
            raise ValueError("tfidf_ngram_min must be <= tfidf_ngram_max")
        if not self.enabled_groups:
            raise ValueError("At least one feature group must be enabled")
        return self


class RandomForestConfig(BaseModel):
    """Random Forest primary classifier hyperparameters."""

    n_estimators: int = Field(default=300, ge=10, le=2000)
    max_depth: int | None = Field(default=20, ge=2, le=100)
    min_samples_split: int = Field(default=4, ge=2, le=50)
    min_samples_leaf: int = Field(default=2, ge=1, le=50)
    max_features: Literal["sqrt", "log2"] | float = "sqrt"
    class_weight: Literal["balanced", "balanced_subsample"] | None = "balanced_subsample"
    random_state: int = 42
    n_jobs: int = -1


class ThresholdConfig(BaseModel):
    """Three-way classification thresholds defining BUG / UNCERTAIN / CLEAN."""

    threshold_low: float = Field(default=0.40, gt=0.0, lt=1.0)
    threshold_center: float = Field(default=0.50, gt=0.0, lt=1.0)
    threshold_high: float = Field(default=0.60, gt=0.0, lt=1.0)
    target_confident_error: float = Field(default=0.25, gt=0.01, lt=0.50)
    calibration_method: Literal["none", "sigmoid", "isotonic"] = "none"

    @model_validator(mode="after")
    def validate_ordering(self) -> "ThresholdConfig":
        if not (self.threshold_low < self.threshold_center < self.threshold_high):
            raise ValueError(
                "Thresholds must satisfy 0.0 < threshold_low < threshold_center < threshold_high < 1.0"
            )
        return self


class ValidationConfig(BaseModel):
    """Repository-grouped splitting and nested CV configuration."""

    outer_folds: int = Field(default=5, ge=2, le=10)
    inner_folds: int = Field(default=3, ge=2, le=5)
    independent_test_repo_fraction: float = Field(default=0.22, gt=0.05, lt=0.50)
    hard_negative_test_repos: int = Field(default=12, ge=2, le=50)
    temporal_test_fraction: float = Field(default=0.25, gt=0.05, lt=0.50)
    random_state: int = 42


class InferenceConfig(BaseModel):
    """Runtime inference and explainability behavior."""

    active_model_version: str | None = None
    active_model_path: str | None = None
    require_clean_syntax: bool = True
    top_local_evidence_count: int = Field(default=8, ge=3, le=30)
    roslyn_timeout_seconds: int = Field(default=30, ge=5, le=180)
    roslyn_batch_chunk_size: int = Field(default=250, ge=10, le=2000)


class AppConfig(BaseModel):
    """Top-level application configuration for CISE v5.0.0."""

    app_name: str = "C# Source-Code Bug Detection System"
    system_version: str = "5.0.0"
    dataset_version: str = "v5.0.0"
    database_relpath: str = "1_Database/SQLite/bug_detector_v5.db"
    datasets_dir_relpath: str = "1_Database/Datasets/v5"
    external_dir_relpath: str = "1_Database/External"
    repositories_dir_relpath: str = "1_Database/Repositories"
    models_dir_relpath: str = "4_AppBuild/Models/v5"
    results_dir_relpath: str = "3_TestResults/v5"
    roslyn_project_relpath: str = "2_SourceCode/RoslynPreprocessor/RoslynPreprocessor.csproj"
    config_relpath: str = "4_AppBuild/Config/active_config.json"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    random_forest: RandomForestConfig = Field(default_factory=RandomForestConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)

    def resolve(self, relpath: str, project_root: Path | None = None) -> Path:
        root = project_root or get_project_root()
        p = Path(relpath)
        return p if p.is_absolute() else (root / p)

    @property
    def project_root(self) -> Path:
        return get_project_root()

    @property
    def db_path(self) -> Path:
        override = os.getenv("BUG_DETECTOR_DB_PATH")
        return self.resolve(override or self.database_relpath)

    @property
    def datasets_dir(self) -> Path:
        return self.resolve(self.datasets_dir_relpath)

    @property
    def external_dir(self) -> Path:
        return self.resolve(self.external_dir_relpath)

    @property
    def repositories_dir(self) -> Path:
        return self.resolve(self.repositories_dir_relpath)

    @property
    def models_dir(self) -> Path:
        return self.resolve(self.models_dir_relpath)

    @property
    def results_dir(self) -> Path:
        return self.resolve(self.results_dir_relpath)

    @property
    def roslyn_project_path(self) -> Path:
        override = os.getenv("BUG_DETECTOR_ROSLYN_PROJECT")
        return self.resolve(override or self.roslyn_project_relpath)

    @property
    def roslyn_dll_path(self) -> Path:
        return self.roslyn_project_path.parent / "bin" / "Release" / "net9.0" / "RoslynPreprocessor.dll"

    @property
    def config_path(self) -> Path:
        override = os.getenv("BUG_DETECTOR_CONFIG_PATH")
        return self.resolve(override or self.config_relpath)

    @property
    def github_token(self) -> str | None:
        token = os.getenv("GITHUB_TOKEN", "").strip()
        return token or None


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from JSON file (if present) and `.env` environment."""
    root = get_project_root()
    env_file = root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    default_cfg = AppConfig()
    target = config_path or default_cfg.config_path
    if target.exists():
        raw: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
        cfg = AppConfig.model_validate(raw)
    else:
        cfg = default_cfg

    env_log = os.getenv("BUG_DETECTOR_LOG_LEVEL", "").strip().upper()
    if env_log in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        cfg.log_level = env_log  # type: ignore[assignment]
    return cfg


def save_config(cfg: AppConfig, config_path: Path | None = None) -> Path:
    """Validate and atomically persist configuration to JSON."""
    validated = AppConfig.model_validate(cfg.model_dump())
    target = config_path or validated.config_path
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(validated.model_dump_json(indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target
