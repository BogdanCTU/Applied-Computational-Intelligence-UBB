"""Integration tests verifying live local Ollama connectivity, model identity, and MLX-LM."""

from __future__ import annotations

import pytest

from source.config.settings import load_config
from source.inference.engine import verify_ollama_generation
from source.models.verifier import ModelVerifier


@pytest.mark.integration
def test_ollama_baseline_qwen35_4b_verified() -> None:
    cfg = load_config()
    verifier = ModelVerifier(cfg)
    status = verifier.check_environment()
    if not status.ollama_reachable:
        pytest.skip("Local Ollama daemon is not running.")
    assert status.baseline_model.available is True
    assert status.baseline_model.architecture == "qwen3_5"
    assert status.baseline_model.context_length == 262144

    res = verify_ollama_generation(cfg.model.baseline, host=cfg.ollama.host)
    assert res["success"] is True
    assert len(res["content"]) > 5


@pytest.mark.integration
def test_ollama_mitigated_model_if_deployed() -> None:
    cfg = load_config()
    verifier = ModelVerifier(cfg)
    mit = verifier.verify_model(cfg.model.mitigated)
    if not mit.available:
        pytest.skip(f"Mitigated model '{cfg.model.mitigated}' not yet deployed.")
    res = verify_ollama_generation(cfg.model.mitigated, host=cfg.ollama.host)
    assert res["success"] is True
