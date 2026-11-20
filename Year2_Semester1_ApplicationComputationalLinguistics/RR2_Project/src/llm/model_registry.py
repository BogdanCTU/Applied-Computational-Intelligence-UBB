"""Centralized model registry and metadata definitions for Agent-OM Local."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .ollama_client import OllamaClient

# Strict parameter ceiling for <= 4B lightweight profiles: 4,000,000,000 total parameters
STRICT_4B_MAX_PARAMETERS: int = 4_000_000_000

# Candidate models eligible for <=4B verification (must still pass runtime /api/show parameter check!)
APPROVED_4B_CANDIDATES: tuple[str, ...] = (
    "qwen2.5:3b",
    "deepseek-r1:1.5b",
    "llama3.2:3b",
    "phi4-mini:latest",
    "phi4-mini",
    "gemma2:2b",
    "qwen2.5:1.5b",
)

# Models known or discovered to exceed 4,000,000,000 total parameters
OUT_OF_LIMIT_REFERENCE_MODELS: Dict[str, str] = {
    "qwen3.5:4b": "Contains 4,538,986,496 total parameters (4.54B > 4.00B strict limit).",
    "qwen3.5:9b": "9B-class model (> 4.00B strict limit).",
    "llama3:8b": "Contains 8,030,261,248 total parameters (8.03B > 4.00B strict limit).",
    "gemma4:12b": "Contains 12,382,568,756 total parameters (12.38B > 4.00B strict limit).",
}

# Dedicated embedding models and their canonical vector dimensions
DEDICATED_EMBEDDING_MODELS: Dict[str, int] = {
    "nomic-embed-text": 768,
    "nomic-embed-text:latest": 768,
    "mxbai-embed-large": 1024,
    "mxbai-embed-large:latest": 1024,
    "bge-m3": 1024,
    "bge-m3:latest": 1024,
    "all-minilm": 384,
    "all-minilm:latest": 384,
}


@dataclass(frozen=True)
class ModelMetadata:
    """Verified runtime metadata for a local Ollama model."""

    name: str
    digest: str
    size_bytes: int
    architecture: str
    family: str
    format: str
    runner: str
    quantization_level: str
    parameter_size_label: str
    total_parameter_count: int
    active_parameter_count: Optional[int]
    context_length: Optional[int]
    embedding_length: Optional[int]
    capabilities: List[str] = field(default_factory=list)
    supports_completion: bool = False
    supports_embedding: bool = False
    is_strict_4b_compliant: bool = False
    compliance_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    """Discovers and caches runtime metadata for all locally installed Ollama models."""

    def __init__(self, client: Optional[OllamaClient] = None) -> None:
        self.client = client or OllamaClient()
        self._cache: Dict[str, ModelMetadata] = {}

    @staticmethod
    def _normalize_name(model_name: str) -> str:
        cleaned = str(model_name).strip()
        return cleaned

    def inspect_model(self, model_name: str, use_cache: bool = True) -> ModelMetadata:
        """Query `/api/tags` and `/api/show` to extract authoritative parameter count and capabilities."""
        norm = self._normalize_name(model_name)
        if use_cache and norm in self._cache:
            return self._cache[norm]

        tags = self.client.list_tags()
        tag_entry: Optional[Dict[str, Any]] = None
        for entry in tags:
            ename = str(entry.get("name", ""))
            if ename == norm or ename == f"{norm}:latest" or ename.split(":")[0] == norm:
                tag_entry = entry
                break

        show_data = self.client.show_model(norm)
        details = show_data.get("details") or (tag_entry.get("details") if tag_entry else {}) or {}
        model_info = show_data.get("model_info") or {}
        capabilities = [str(c) for c in (show_data.get("capabilities") or [])]

        arch = str(model_info.get("general.architecture") or details.get("family") or "unknown")
        raw_param_count = model_info.get("general.parameter_count")
        if raw_param_count is None:
            raise ValueError(
                f"Ollama /api/show did not return 'general.parameter_count' for model '{norm}'. "
                "Cannot verify parameter count from model tag alone."
            )
        total_params = int(raw_param_count)
        active_params_raw = model_info.get(f"{arch}.active_parameter_count")
        active_params = int(active_params_raw) if active_params_raw is not None else None

        ctx_raw = model_info.get(f"{arch}.context_length")
        if ctx_raw is None:
            for k, v in model_info.items():
                if k.endswith(".context_length"):
                    ctx_raw = v
                    break
        context_length = int(ctx_raw) if ctx_raw is not None else None

        emb_raw = model_info.get(f"{arch}.embedding_length")
        if emb_raw is None:
            for k, v in model_info.items():
                if k.endswith(".embedding_length"):
                    emb_raw = v
                    break
        embedding_length = int(emb_raw) if emb_raw is not None else None

        supports_completion = "completion" in capabilities or (
            "embedding" not in capabilities and norm not in DEDICATED_EMBEDDING_MODELS
        )
        supports_embedding = (
            "embedding" in capabilities
            or norm in DEDICATED_EMBEDDING_MODELS
            or f"{norm}:latest" in DEDICATED_EMBEDDING_MODELS
        )

        is_compliant = 0 < total_params <= STRICT_4B_MAX_PARAMETERS
        if is_compliant:
            note = (
                f"COMPLIANT: {total_params:,} total parameters <= {STRICT_4B_MAX_PARAMETERS:,} (4.0B ceiling)."
            )
        else:
            note = (
                f"EXCLUDED FROM <=4B: {total_params:,} total parameters exceeds "
                f"{STRICT_4B_MAX_PARAMETERS:,} (4.0B ceiling) by {total_params - STRICT_4B_MAX_PARAMETERS:,}."
            )

        meta = ModelMetadata(
            name=str(tag_entry.get("name", norm)) if tag_entry else norm,
            digest=str((tag_entry or {}).get("digest", show_data.get("digest", "unknown"))),
            size_bytes=int((tag_entry or {}).get("size", 0) or 0),
            architecture=arch,
            family=str(details.get("family", arch)),
            format=str(details.get("format", "unknown")),
            runner=str(details.get("runner", "ggml")),
            quantization_level=str(details.get("quantization_level", "unknown")),
            parameter_size_label=str(details.get("parameter_size", "unknown")),
            total_parameter_count=total_params,
            active_parameter_count=active_params,
            context_length=context_length,
            embedding_length=embedding_length,
            capabilities=capabilities,
            supports_completion=supports_completion,
            supports_embedding=supports_embedding,
            is_strict_4b_compliant=is_compliant,
            compliance_note=note,
        )
        self._cache[norm] = meta
        self._cache[meta.name] = meta
        return meta

    def discover_all_models(self) -> List[ModelMetadata]:
        """Inspect all currently installed Ollama models and return their verified metadata."""
        tags = self.client.list_tags()
        results: List[ModelMetadata] = []
        for entry in tags:
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            try:
                results.append(self.inspect_model(name, use_cache=False))
            except Exception:
                continue
        return results

    def list_compliant_4b_chat_models(self) -> List[ModelMetadata]:
        """Return installed models that support chat completion and have <= 4,000,000,000 total parameters."""
        return [
            m
            for m in self.discover_all_models()
            if m.supports_completion and not m.supports_embedding and m.is_strict_4b_compliant
        ]

    def list_embedding_models(self) -> List[ModelMetadata]:
        """Return installed dedicated embedding models."""
        return [m for m in self.discover_all_models() if m.supports_embedding]
