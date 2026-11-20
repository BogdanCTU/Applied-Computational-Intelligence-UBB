"""Unit tests for LoRA hyperparameter serialization."""

from pathlib import Path
import yaml
from app.training.config import TrainingHyperparameters


def test_training_hyperparameters_yaml(tmp_path: Path):
    params = TrainingHyperparameters(
        fine_tune_type="lora",
        iters=50,
        batch_size=4,
        learning_rate=2e-4,
        lora_rank=16,
    )
    yaml_file = tmp_path / "lora_config.yaml"
    params.save_yaml(yaml_file)

    assert yaml_file.exists()
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
    assert data["iters"] == 50
    assert data["batch_size"] == 4
    assert data["lora_parameters"]["rank"] == 16
