"""Integration test verifying output parity between adapter-loaded model and fused model."""

import pytest
from pathlib import Path
from app.core.config import get_project_root
from app.inference.engine import InferenceEngine


def test_fusion_parity_greedy():
    root = get_project_root()
    base_model = root / "6_Models" / "base" / "Qwen2.5-Coder-3B-Instruct-4bit"
    adapter_path = root / "6_Models" / "adapters" / "exp_b_lora_r16"
    fused_model = root / "6_Models" / "exported" / "exp_b_lora_r16_fused"

    if not base_model.exists() or not adapter_path.exists() or not fused_model.exists():
        pytest.skip("Base model, adapter, or fused model not found on disk.")

    schema = "Database Schema [users]:\n- Table `users`: id (INT [PK]), name (TEXT), department (TEXT)"
    questions = [
        "What are the names of all users in Engineering?",
        "Count the total number of users.",
        "List all unique departments.",
    ]

    # 1. Generate with adapter
    engine_adapter = InferenceEngine(
        model_path_or_id=str(base_model),
        adapter_path=str(adapter_path),
    )
    engine_adapter.load()
    adapter_outputs = []
    for q in questions:
        sql, _ = engine_adapter.generate_sql(schema, q, temperature=0.0, max_tokens=64)
        adapter_outputs.append(sql.strip())
    del engine_adapter

    # 2. Generate with fused model
    engine_fused = InferenceEngine(
        model_path_or_id=str(fused_model),
        adapter_path=None,
    )
    engine_fused.load()
    fused_outputs = []
    for q in questions:
        sql, _ = engine_fused.generate_sql(schema, q, temperature=0.0, max_tokens=64)
        fused_outputs.append(sql.strip())
    del engine_fused

    # 3. Assert parity
    for idx, (out_a, out_f) in enumerate(zip(adapter_outputs, fused_outputs)):
        assert out_a == out_f, f"Mismatch at query {idx}: adapter='{out_a}' vs fused='{out_f}'"
