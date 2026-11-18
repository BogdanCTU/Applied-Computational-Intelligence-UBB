"""Model registry for sub-4B open-source architectures."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModelSpec:
    model_id: str
    display_name: str
    architecture: str
    parameter_count_b: float
    quantization: str
    context_window: int
    hf_repo: str
    is_default: bool = False
    notes: str = ""


class ModelRegistry:
    """Catalog of certified sub-4B models for Text-to-SQL on Apple Silicon."""

    _MODELS: Dict[str, ModelSpec] = {
        "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit": ModelSpec(
            model_id="mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
            display_name="Qwen2.5-Coder-3B-Instruct (4-bit MLX)",
            architecture="qwen2",
            parameter_count_b=3.09,
            quantization="4-bit",
            context_window=32768,
            hf_repo="mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
            is_default=True,
            notes="Optimal for Apple Silicon 16GB RAM; ultra-fast QLoRA training (< 2.5 GB peak VRAM).",
        ),
        "mlx-community/Qwen2.5-Coder-3B-Instruct-8bit": ModelSpec(
            model_id="mlx-community/Qwen2.5-Coder-3B-Instruct-8bit",
            display_name="Qwen2.5-Coder-3B-Instruct (8-bit MLX)",
            architecture="qwen2",
            parameter_count_b=3.09,
            quantization="8-bit",
            context_window=32768,
            hf_repo="mlx-community/Qwen2.5-Coder-3B-Instruct-8bit",
            is_default=False,
            notes="Higher precision quantization for near-lossless baseline evaluation.",
        ),
        "mlx-community/Qwen2.5-Coder-3B-Instruct-bf16": ModelSpec(
            model_id="mlx-community/Qwen2.5-Coder-3B-Instruct-bf16",
            display_name="Qwen2.5-Coder-3B-Instruct (BF16 MLX)",
            architecture="qwen2",
            parameter_count_b=3.09,
            quantization="bf16",
            context_window=32768,
            hf_repo="mlx-community/Qwen2.5-Coder-3B-Instruct-bf16",
            is_default=False,
            notes="Full-precision weights in MLX format; requires ~6.5 GB RAM.",
        ),
        "Qwen/Qwen2.5-Coder-3B-Instruct": ModelSpec(
            model_id="Qwen/Qwen2.5-Coder-3B-Instruct",
            display_name="Qwen2.5-Coder-3B-Instruct (Upstream HF)",
            architecture="qwen2",
            parameter_count_b=3.09,
            quantization="none",
            context_window=32768,
            hf_repo="Qwen/Qwen2.5-Coder-3B-Instruct",
            is_default=False,
            notes="Standard PyTorch / Safetensors upstream repository.",
        ),
        "mlx-community/Llama-3.2-3B-Instruct-4bit": ModelSpec(
            model_id="mlx-community/Llama-3.2-3B-Instruct-4bit",
            display_name="Llama-3.2-3B-Instruct (4-bit MLX)",
            architecture="llama",
            parameter_count_b=3.21,
            quantization="4-bit",
            context_window=131072,
            hf_repo="mlx-community/Llama-3.2-3B-Instruct-4bit",
            is_default=False,
            notes="Alternative general-purpose sub-4B baseline model.",
        ),
    }

    @classmethod
    def list_models(cls) -> List[ModelSpec]:
        """Returns all registered models."""
        return list(cls._MODELS.values())

    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelSpec]:
        """Fetches specification for model_id."""
        return cls._MODELS.get(model_id)

    @classmethod
    def get_default_model(cls) -> ModelSpec:
        """Returns the default certified model."""
        for spec in cls._MODELS.values():
            if spec.is_default:
                return spec
        return list(cls._MODELS.values())[0]
