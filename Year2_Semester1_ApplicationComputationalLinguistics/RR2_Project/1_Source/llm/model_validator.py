"""Runtime model availability, strict <=4B parameter limit, and vector dimension validator."""

from __future__ import annotations

from typing import Optional

from ..config import CLOUD_MODEL_PREFIXES
from .model_registry import (
    DEDICATED_EMBEDDING_MODELS,
    STRICT_4B_MAX_PARAMETERS,
    ModelMetadata,
    ModelRegistry,
)
from .ollama_client import OllamaClientError


class ModelValidationError(RuntimeError):
    """Base exception for local LLM or embedding validation failures."""


class ModelNotAvailableError(ModelValidationError):
    """Raised when a configured model is not installed in local Ollama."""


class ParameterLimitExceededError(ModelValidationError):
    """Raised when a model's total parameter count exceeds the strict 4,000,000,000 limit."""


class EmbeddingDimensionMismatchError(ModelValidationError):
    """Raised when a model's actual embedding dimension does not match the configured database vector length."""


class ModelValidator:
    """Enforces local-only execution, runtime model availability, <=4B parameter limits, and vector dimensions."""

    def __init__(self, registry: Optional[ModelRegistry] = None) -> None:
        self.registry = registry or ModelRegistry()

    @staticmethod
    def assert_not_cloud_model(model_name: str) -> None:
        cleaned = str(model_name).strip().lower()
        if any(cleaned.startswith(prefix) for prefix in CLOUD_MODEL_PREFIXES):
            raise PermissionError(
                f"Cloud model '{model_name}' is prohibited. Only local Ollama models on 127.0.0.1 are permitted."
            )

    def validate_chat_model(
        self,
        model_name: str,
        enforce_4b_limit: bool = False,
        max_parameters: int = STRICT_4B_MAX_PARAMETERS,
    ) -> ModelMetadata:
        """Verify that `model_name` exists locally, supports completion, and satisfies `max_parameters` if enforced."""
        self.assert_not_cloud_model(model_name)
        try:
            meta = self.registry.inspect_model(model_name)
        except OllamaClientError as exc:
            raise ModelNotAvailableError(
                f"Required local chat model '{model_name}' is unavailable in local Ollama: {exc}"
            ) from exc

        if meta.supports_embedding and not meta.supports_completion:
            raise ModelValidationError(
                f"Model '{model_name}' is a dedicated embedding model and cannot be used as a chat generator."
            )

        if enforce_4b_limit and meta.total_parameter_count > max_parameters:
            raise ParameterLimitExceededError(
                f"Model '{model_name}' has {meta.total_parameter_count:,} total parameters "
                f"({meta.parameter_size_label}), exceeding the strict <= {max_parameters:,} (4.0B) parameter limit."
            )
        return meta

    def validate_embedding_model(
        self,
        model_name: str,
        expected_dimension: int,
        allow_llama_bridge: bool = False,
        verify_live_vector: bool = True,
    ) -> ModelMetadata:
        """Verify that `model_name` exists locally, is embedding-capable, and outputs `expected_dimension` floats."""
        self.assert_not_cloud_model(model_name)
        if expected_dimension <= 0:
            raise EmbeddingDimensionMismatchError(
                f"Invalid expected_dimension={expected_dimension}; must be a positive integer."
            )

        try:
            meta = self.registry.inspect_model(model_name)
        except OllamaClientError as exc:
            raise ModelNotAvailableError(
                f"Required local embedding model '{model_name}' is unavailable in local Ollama: {exc}"
            ) from exc

        is_llama_bridge_target = allow_llama_bridge and str(model_name).lower().startswith("llama3")
        if not meta.supports_embedding and not is_llama_bridge_target:
            raise ModelValidationError(
                f"Model '{model_name}' (capabilities={meta.capabilities}) does not declare 'embedding' capability "
                "and is not a dedicated embedding model. Never assume a chat model is a suitable embedding model."
            )

        if meta.embedding_length is not None and meta.embedding_length != expected_dimension:
            raise EmbeddingDimensionMismatchError(
                f"Embedding dimension mismatch for '{model_name}': model metadata reports "
                f"{meta.embedding_length} dimensions, but profile/database expects {expected_dimension}."
            )

        norm_key = str(model_name).strip()
        if norm_key in DEDICATED_EMBEDDING_MODELS and DEDICATED_EMBEDDING_MODELS[norm_key] != expected_dimension:
            raise EmbeddingDimensionMismatchError(
                f"Embedding dimension mismatch for '{model_name}': registry expects "
                f"{DEDICATED_EMBEDDING_MODELS[norm_key]}, got {expected_dimension}."
            )

        if verify_live_vector and not is_llama_bridge_target:
            resp = self.registry.client.embed(model_name, ["dimension verification probe"])
            vecs = resp.get("embeddings") or []
            if not vecs or not isinstance(vecs[0], list):
                raise ModelValidationError(
                    f"Ollama /api/embed probe for '{model_name}' returned no embedding vector."
                )
            actual_dim = len(vecs[0])
            if actual_dim != expected_dimension:
                raise EmbeddingDimensionMismatchError(
                    f"Runtime embedding vector dimension mismatch for '{model_name}': "
                    f"expected {expected_dimension}, actual vector length is {actual_dim}."
                )

        return meta
