"""Unit tests for adapter path and checkpoint management."""

from pathlib import Path
from app.training.lora_manager import LoRAManager


def test_lora_manager_paths(tmp_path: Path):
    manager = LoRAManager(adapters_dir=tmp_path / "adapters")
    p = manager.get_adapter_path("run_test_01")
    assert p.exists()
    assert manager.is_adapter_valid("run_test_01") is False

    # Simulate adapter file creation
    (p / "adapters.safetensors").touch()
    assert manager.is_adapter_valid("run_test_01") is True
