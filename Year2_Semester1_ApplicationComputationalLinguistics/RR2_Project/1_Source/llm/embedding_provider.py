"""Separated local Ollama Embedding Provider with dynamic vector dimension verification and telemetry."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

from .model_registry import ModelMetadata, ModelRegistry
from .model_validator import EmbeddingDimensionMismatchError, ModelValidator
from .ollama_client import OllamaClient


class LocalEmbeddingProvider:
    """Dedicated local embedding provider enforcing dimension parity and prohibiting silent truncation/padding."""

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        expected_dim: int = 768,
        base_url: str = "http://127.0.0.1:11434",
        ctx_size: int = 2048,
        batch_size: int = 64,
        normalize_l2: bool = False,
        allow_llama_bridge: bool = False,
        timeout_s: float = 120.0,
        client: Optional[OllamaClient] = None,
        validator: Optional[ModelValidator] = None,
        validate_on_init: bool = False,
    ) -> None:
        ModelValidator.assert_not_cloud_model(model_name)
        if int(expected_dim) <= 0:
            raise EmbeddingDimensionMismatchError(
                f"expected_dim must be positive; got {expected_dim}."
            )
        self.client = client or OllamaClient(base_url=base_url, timeout_s=timeout_s)
        self.registry = ModelRegistry(self.client)
        self.validator = validator or ModelValidator(self.registry)

        self.model = str(model_name).strip()
        self.model_name = self.model
        self.expected_dim = int(expected_dim)
        self.base_url = self.client.base_url
        self.ctx_size = int(ctx_size)
        self.batch_size = max(1, int(batch_size))
        self.normalize_l2 = bool(normalize_l2)
        self.allow_llama_bridge = bool(allow_llama_bridge) or self.model.lower().startswith("llama3")
        self.timeout_s = float(timeout_s)

        self.verified_metadata: Optional[ModelMetadata] = None
        self.total_requests: int = 0
        self.total_texts_embedded: int = 0
        self.total_latency_ms: float = 0.0
        self._llama_bridge: Optional[Any] = None

        if validate_on_init:
            self.verify_runtime_model()

    def verify_runtime_model(self, verify_live_vector: bool = True) -> ModelMetadata:
        meta = self.validator.validate_embedding_model(
            self.model_name,
            expected_dimension=self.expected_dim,
            allow_llama_bridge=self.allow_llama_bridge,
            verify_live_vector=verify_live_vector,
        )
        self.verified_metadata = meta
        return meta

    @staticmethod
    def _l2_normalize(vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            return [v / norm for v in vec]
        return vec

    def _validate_vectors(self, vectors: List[List[float]]) -> List[List[float]]:
        out: List[List[float]] = []
        for idx, vec in enumerate(vectors):
            actual_dim = len(vec)
            if actual_dim != self.expected_dim:
                raise EmbeddingDimensionMismatchError(
                    f"Embedding dimension mismatch on '{self.model_name}' (item {idx}): "
                    f"expected {self.expected_dim}, got {actual_dim}. "
                    "Silent truncation, padding, or substitution is prohibited."
                )
            out.append(self._l2_normalize(vec) if self.normalize_l2 else vec)
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents and verify every vector matches `expected_dim`."""
        if not texts:
            return []

        if self.model_name.lower().startswith("llama3"):
            if self._llama_bridge is None:
                from ..utils.llama_embed_bridge import LlamaBridgeEmbeddings

                self._llama_bridge = LlamaBridgeEmbeddings(
                    model_name=self.model_name,
                    expected_dim=self.expected_dim,
                    ctx_size=self.ctx_size,
                    ollama_base_url=self.base_url,
                )
            t0 = time.perf_counter()
            raw_vecs = self._llama_bridge.embed_documents(list(texts))
            self.total_latency_ms += (time.perf_counter() - t0) * 1000.0
            self.total_requests += 1
            self.total_texts_embedded += len(raw_vecs)
            return self._validate_vectors(raw_vecs)

        all_vectors: List[List[float]] = []
        items = [str(t) for t in texts]
        for start in range(0, len(items), self.batch_size):
            batch = items[start : start + self.batch_size]
            t0 = time.perf_counter()
            resp = self.client.embed(self.model_name, batch, timeout_s=self.timeout_s)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            batch_vecs = resp.get("embeddings") or []
            if len(batch_vecs) != len(batch):
                raise RuntimeError(
                    f"Ollama /api/embed returned {len(batch_vecs)} vectors for batch of {len(batch)} texts."
                )
            validated = self._validate_vectors(batch_vecs)
            all_vectors.extend(validated)
            self.total_requests += 1
            self.total_texts_embedded += len(validated)
            self.total_latency_ms += elapsed_ms

        return all_vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string and verify its vector dimension."""
        vecs = self.embed_documents([str(text)])
        return vecs[0] if vecs else []

    def release_vram(self) -> None:
        if self._llama_bridge is not None:
            self._llama_bridge.release_vram()
        else:
            self.client.unload_model(self.model_name)

    def get_telemetry_summary(self) -> Dict[str, Any]:
        avg_ms = (
            round(self.total_latency_ms / self.total_texts_embedded, 2)
            if self.total_texts_embedded
            else 0.0
        )
        return {
            "model_name": self.model_name,
            "expected_dim": self.expected_dim,
            "normalize_l2": self.normalize_l2,
            "verified_metadata": self.verified_metadata.to_dict() if self.verified_metadata else None,
            "total_requests": self.total_requests,
            "total_texts_embedded": self.total_texts_embedded,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_ms_per_text": avg_ms,
        }
