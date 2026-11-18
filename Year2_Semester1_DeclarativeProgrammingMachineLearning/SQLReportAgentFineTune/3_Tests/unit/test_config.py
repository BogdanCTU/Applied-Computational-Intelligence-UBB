"""Unit tests for configuration loading and validation."""

import pytest
from pathlib import Path
from app.core.config import ProjectConfig, load_config, save_config, get_project_root


def test_default_config_instantiation():
    cfg = ProjectConfig()
    assert cfg.version == "1.0.0"
    assert cfg.model.architecture == "qwen2"
    assert cfg.lora.rank == 8
    assert cfg.lora.alpha == 16.0
    assert cfg.dataset.train_split_ratio == 0.85
    assert "execution_accuracy" in cfg.evaluation.metrics


def test_load_and_save_config(tmp_path: Path):
    cfg = ProjectConfig()
    cfg.model.parameter_count_b = 3.09
    save_path = tmp_path / "test_config.yaml"
    save_config(cfg, save_path)
    assert save_path.exists()

    loaded = load_config(save_path)
    assert loaded.model.parameter_count_b == 3.09
    assert loaded.version == "1.0.0"


def test_project_root_resolution():
    root = get_project_root()
    assert root.exists()
    assert (root / "1_Source").exists()
