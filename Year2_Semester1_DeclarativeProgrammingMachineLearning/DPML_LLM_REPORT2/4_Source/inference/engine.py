"""Verification helpers for local Ollama and MLX-LM inference."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from source.ollama.client import OllamaClient


def verify_ollama_generation(
    model_identifier: str,
    host: str = "http://127.0.0.1:11434",
    prompt: str = "Reply in one sentence: why should SQL queries use parameters?",
) -> Dict[str, Any]:
    """Run a live single-turn inference check against local Ollama."""
    client = OllamaClient(host=host, timeout_seconds=120, retries=1, rate_limit_delay_seconds=0.0)
    resp = client.chat(
        model=model_identifier,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        num_predict=64,
        think=False,
    )
    return {
        "model": model_identifier,
        "success": not resp.is_infrastructure_error and bool(resp.content.strip()),
        "content": resp.content,
        "duration_seconds": resp.duration_seconds,
        "error": resp.error,
    }


def verify_mlx_generation(model_path: str | Path, prompt: str = "What is SQL parameterization?") -> Dict[str, Any]:
    """Verify a local MLX-LM checkpoint loads and generates tokens on Apple Silicon."""
    from mlx_lm import generate, load

    model, tokenizer = load(str(model_path))
    messages = [{"role": "user", "content": prompt}]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    text = generate(model, tokenizer, prompt=formatted, max_tokens=48, verbose=False)
    return {
        "model_path": str(model_path),
        "success": bool(text.strip()),
        "output": text.strip(),
    }
