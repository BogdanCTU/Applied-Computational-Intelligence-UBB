"""Configuration management using Pydantic and YAML."""

from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """Returns the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


class PathsConfig(BaseModel):
    """Core directory locations."""
    root_dir: Path = Field(default_factory=get_project_root)
    database_dir: Path = Field(default_factory=lambda: get_project_root() / "2_Database")
    models_dir: Path = Field(default_factory=lambda: get_project_root() / "6_Models")
    results_dir: Path = Field(default_factory=lambda: get_project_root() / "7_Results")
    logs_dir: Path = Field(default_factory=lambda: get_project_root() / "8_Logs")


class ModelConfig(BaseModel):
    """Base model identifier and runtime configuration."""
    model_id: str = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
    display_name: str = "Qwen2.5-Coder-3B-Instruct (4-bit MLX)"
    architecture: str = "qwen2"
    parameter_count_b: float = 3.09
    context_window: int = 32768
    quantization: str = "4-bit"
    local_path: Optional[str] = None


class LoRAConfig(BaseModel):
    """LoRA / QLoRA fine-tuning hyperparameters."""
    fine_tune_type: str = "lora"  # 'lora' or 'dora'
    rank: int = 8
    alpha: float = 16.0
    dropout: float = 0.05
    num_layers: int = 16  # -1 for all layers, or subset for memory efficiency
    learning_rate: float = 1e-4
    batch_size: int = 2
    iters: int = 600
    val_batches: int = 25
    steps_per_report: int = 10
    steps_per_eval: int = 50
    save_every: int = 100
    grad_accumulation_steps: int = 2
    grad_checkpoint: bool = True
    max_seq_length: int = 2048
    seed: int = 42


class DatasetConfig(BaseModel):
    """Dataset acquisition and split configuration."""
    sources: List[str] = Field(default_factory=lambda: ["spider", "synthetic"])
    train_split_ratio: float = 0.85
    valid_split_ratio: float = 0.10
    test_split_ratio: float = 0.05
    max_samples_per_source: Optional[int] = None
    seed: int = 42


class EvaluationConfig(BaseModel):
    """Inference and execution benchmark configuration."""
    batch_size: int = 1
    max_tokens: int = 512
    temperature: float = 0.0
    timeout_seconds: float = 5.0
    strict_row_order: bool = False
    metrics: List[str] = Field(
        default_factory=lambda: ["execution_accuracy", "exact_match", "valid_sql_rate"]
    )


class ProjectConfig(BaseModel):
    """Master project configuration."""
    version: str = "1.0.0"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    lora: LoRAConfig = Field(default_factory=LoRAConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)


def load_config(config_path: Optional[Path] = None) -> ProjectConfig:
    """Loads configuration from YAML file or returns defaults."""
    if config_path is None:
        config_path = get_project_root() / "1_Source" / "config" / "default_config.yaml"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return ProjectConfig(**data)
    return ProjectConfig()


def save_config(config: ProjectConfig, config_path: Path) -> None:
    """Saves configuration to YAML file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(mode="json"), f, sort_keys=False)
