"""Verify local Ollama models, capabilities, context lengths, and disk/memory constraints."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from source.config.settings import AppConfig
from source.ollama.client import OllamaClient


@dataclass
class ModelVerification:
    identifier: str
    available: bool
    digest: Optional[str] = None
    architecture: Optional[str] = None
    parameters: Optional[str] = None
    context_length: Optional[int] = None
    quantization: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)
    runner: Optional[str] = None
    format: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EnvironmentStatus:
    python_version: str
    platform_machine: str
    total_memory_bytes: Optional[int]
    free_disk_gb: float
    ollama_reachable: bool
    ollama_version: Optional[str]
    available_models: list[str]
    baseline_model: ModelVerification
    mitigated_model: ModelVerification
    mlx_available: bool
    mlx_lm_version: Optional[str]


def get_system_memory_bytes() -> Optional[int]:
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            return int(out)
        except Exception:
            return None
    return None


class ModelVerifier:
    """Verifies local Ollama model identity, capabilities, and Apple Silicon MLX availability."""

    def __init__(self, config: AppConfig, client: Optional[OllamaClient] = None):
        self.config = config
        self.client = client or OllamaClient(
            host=config.ollama.host,
            timeout_seconds=config.ollama.timeout_seconds,
            retries=config.ollama.retries,
            rate_limit_delay_seconds=config.ollama.rate_limit_delay_seconds,
        )

    def verify_model(self, identifier: str) -> ModelVerification:
        """Inspect /api/tags and /api/show for exact local model metadata."""
        try:
            tags = self.client.list_models()
        except Exception as exc:
            return ModelVerification(identifier=identifier, available=False, error=f"Ollama unreachable: {exc}")

        matched = next((m for m in tags if m.get("name") == identifier or m.get("model") == identifier), None)
        if not matched:
            return ModelVerification(
                identifier=identifier,
                available=False,
                error=f"Model '{identifier}' not found in local Ollama registry.",
            )

        try:
            info = self.client.show_model(identifier)
        except Exception as exc:
            return ModelVerification(
                identifier=identifier,
                available=False,
                digest=matched.get("digest"),
                error=f"/api/show failed: {exc}",
            )

        model_info: dict[str, Any] = info.get("model_info") or {}
        details: dict[str, Any] = info.get("details") or matched.get("details") or {}
        arch = model_info.get("general.architecture") or details.get("family") or "unknown"
        ctx = model_info.get(f"{arch}.context_length") or details.get("context_length")
        param_count = model_info.get("general.parameter_count")
        params_str = f"{param_count / 1e9:.2f}B" if isinstance(param_count, (int, float)) else details.get("parameter_size")
        capabilities = list(info.get("capabilities") or matched.get("capabilities") or [])

        return ModelVerification(
            identifier=identifier,
            available=True,
            digest=matched.get("digest"),
            architecture=str(arch),
            parameters=str(params_str) if params_str else None,
            context_length=int(ctx) if ctx else None,
            quantization=details.get("quantization_level") or None,
            capabilities=capabilities,
            runner=details.get("runner"),
            format=details.get("format"),
            error=None,
        )

    def check_environment(self, root_path: Optional[Path] = None) -> EnvironmentStatus:
        """Collect comprehensive verification report of Python, disk, memory, MLX, and Ollama."""
        target_path = root_path or Path(".")
        disk = shutil.disk_usage(target_path)
        free_gb = round(disk.free / (1024**3), 2)

        ollama_version: Optional[str] = None
        available_models: list[str] = []
        ollama_reachable = False
        try:
            ollama_version = self.client.get_version()
            available_models = [str(m.get("name")) for m in self.client.list_models()]
            ollama_reachable = True
        except Exception:
            ollama_reachable = False

        baseline_ver = self.verify_model(self.config.model.baseline)
        mitigated_ver = self.verify_model(self.config.model.mitigated)

        mlx_ok = False
        mlx_lm_ver: Optional[str] = None
        try:
            import importlib.metadata
            import mlx.core  # noqa: F401
            import mlx_lm  # noqa: F401

            mlx_ok = True
            mlx_lm_ver = importlib.metadata.version("mlx-lm")
        except Exception:
            mlx_ok = False

        return EnvironmentStatus(
            python_version=sys.version.split()[0],
            platform_machine=platform.machine(),
            total_memory_bytes=get_system_memory_bytes(),
            free_disk_gb=free_gb,
            ollama_reachable=ollama_reachable,
            ollama_version=ollama_version,
            available_models=available_models,
            baseline_model=baseline_ver,
            mitigated_model=mitigated_ver,
            mlx_available=mlx_ok,
            mlx_lm_version=mlx_lm_ver,
        )
