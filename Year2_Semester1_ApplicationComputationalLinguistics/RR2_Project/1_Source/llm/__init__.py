"""Local LLM and Embedding Provider Architecture for Agent-OM.

Strictly enforces:
- Loopback-only Ollama execution (`http://127.0.0.1:11434`).
- Separation of chat inference (`LocalChatProvider`) and embedding providers (`LocalEmbeddingProvider`).
- Runtime model metadata verification via `/api/show` (`ModelValidator`).
- Strict <= 4,000,000,000 (4.0B) total parameter count enforcement for lightweight profiles.
- Explicit vector dimension verification before database storage or search.
"""

from __future__ import annotations

from .chat_provider import LocalChatProvider
from .embedding_provider import LocalEmbeddingProvider
from .model_registry import (
    APPROVED_4B_CANDIDATES,
    DEDICATED_EMBEDDING_MODELS,
    OUT_OF_LIMIT_REFERENCE_MODELS,
    STRICT_4B_MAX_PARAMETERS,
    ModelMetadata,
    ModelRegistry,
)
from .model_validator import (
    EmbeddingDimensionMismatchError,
    ModelNotAvailableError,
    ModelValidationError,
    ModelValidator,
    ParameterLimitExceededError,
)
from .ollama_client import OllamaClient, OllamaClientError

__all__ = [
    "APPROVED_4B_CANDIDATES",
    "DEDICATED_EMBEDDING_MODELS",
    "EmbeddingDimensionMismatchError",
    "LocalChatProvider",
    "LocalEmbeddingProvider",
    "ModelMetadata",
    "ModelNotAvailableError",
    "ModelRegistry",
    "ModelValidationError",
    "ModelValidator",
    "OUT_OF_LIMIT_REFERENCE_MODELS",
    "OllamaClient",
    "OllamaClientError",
    "ParameterLimitExceededError",
    "STRICT_4B_MAX_PARAMETERS",
]
