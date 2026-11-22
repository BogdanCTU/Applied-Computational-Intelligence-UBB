"""Pydantic-validated centralized configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


def get_project_root() -> Path:
    """Return the resolved project workspace root directory."""
    return Path(__file__).resolve().parent.parent.parent


class ProjectConfig(BaseModel):
    name: str = "Local_LLM_Safety_Research"
    version: str = "1.0.0"
    python_version: str = "3.13"
    local_only: bool = True
    dataset_version: str = "v1.0"

    @field_validator("local_only")
    @classmethod
    def enforce_local_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Project enforces local_only=True; external inference APIs are prohibited.")
        return v


class ModelConfig(BaseModel):
    provider: str = "ollama"
    baseline: str = "qwen3.5:4b"
    mitigated: str = "qwen3.5:4b-safety"
    expected_architecture: str = "qwen3_5"
    max_parameters: int = Field(default=4_500_000_000, gt=0)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    num_predict: int = Field(default=256, ge=16, le=4096)
    think: bool = False

    @field_validator("provider")
    @classmethod
    def check_provider(cls, v: str) -> str:
        if v.lower() != "ollama":
            raise ValueError(f"Unsupported model provider '{v}'; only local 'ollama' is permitted.")
        return v.lower()


class OllamaConfig(BaseModel):
    host: str = "http://127.0.0.1:11434"
    timeout_seconds: int = Field(default=180, ge=5, le=1800)
    retries: int = Field(default=3, ge=0, le=10)
    concurrency: int = Field(default=1, ge=1, le=16)
    rate_limit_delay_seconds: float = Field(default=0.0, ge=0.0, le=10.0)

    @field_validator("host")
    @classmethod
    def check_local_host(cls, v: str) -> str:
        allowed_prefixes = ("http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost")
        if not v.startswith(allowed_prefixes):
            raise ValueError(f"Ollama host must be local loopback (127.0.0.1 or localhost), got: {v}")
        return v.rstrip("/")


class PenetrationConfig(BaseModel):
    minimum_tests_per_category: int = Field(default=100, ge=1)
    categories: int = Field(default=12, ge=10)
    random_seed: int = 42
    multi_turn_enabled: bool = True
    eval_split: str = "held_out_eval"
    baseline_discovery_sample_per_category: int = Field(default=10, ge=0)


class EvaluationConfig(BaseModel):
    preserve_raw_responses: bool = True
    manual_review_enabled: bool = True
    confidence_level: float = Field(default=0.95, gt=0.5, lt=1.0)
    rule_version: str = "v2"


class FineTuningConfig(BaseModel):
    enabled: bool = True
    method: str = "lora"
    max_sequence_length: int = Field(default=384, ge=128, le=8192)
    batch_size: int = Field(default=1, ge=1, le=16)
    num_layers: int = Field(default=4, ge=1, le=32)
    iters: int = Field(default=60, ge=1, le=5000)
    learning_rate: float = Field(default=1e-4, gt=0.0, le=1e-1)
    lora_rank: int = Field(default=8, ge=1, le=128)
    lora_alpha: float = Field(default=16.0, gt=0.0)
    lora_scale: float = Field(default=2.0, gt=0.0)
    lora_dropout: float = Field(default=0.0, ge=0.0, le=0.5)
    steps_per_report: int = Field(default=10, ge=1)
    steps_per_eval: int = Field(default=20, ge=1)
    save_every: int = Field(default=40, ge=1)
    val_batches: int = Field(default=10, ge=1)
    grad_checkpoint: bool = True
    mask_prompt: bool = True
    validation_enabled: bool = True
    seed: int = 42


class StorageConfig(BaseModel):
    sqlite_path: str = "5_Data/sqlite/research.db"
    preserve_experiments: bool = True
    backup_dir: str = "5_Data/backups"
    export_dir: str = "5_Data/exports"


class AppConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    penetration: PenetrationConfig = Field(default_factory=PenetrationConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    fine_tuning: FineTuningConfig = Field(default_factory=FineTuningConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    def resolve_path(self, rel_or_abs: str | Path) -> Path:
        p = Path(rel_or_abs)
        if p.is_absolute():
            return p
        return get_project_root() / p


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """Load and validate config.yaml at startup."""
    root = get_project_root()
    path = Path(config_path) if config_path else root / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(raw)
