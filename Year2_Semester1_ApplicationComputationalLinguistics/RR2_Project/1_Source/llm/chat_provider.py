"""Separated local Ollama Chat Provider with runtime validation, deterministic settings, and telemetry."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .model_registry import STRICT_4B_MAX_PARAMETERS, ModelMetadata, ModelRegistry
from .model_validator import ModelValidator
from .ollama_client import OllamaClient


class LocalChatProvider:
    """Provides local-only LLM chat generation backed by Ollama, with optional strict <=4B enforcement."""

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://127.0.0.1:11434",
        temperature: float = 0.0,
        seed: Optional[int] = 42,
        top_k: Optional[int] = 1,
        top_p: Optional[float] = 1.0,
        repeat_penalty: Optional[float] = 1.0,
        num_ctx: int = 2048,
        reasoning: Optional[bool] = False,
        enforce_4b_limit: bool = False,
        max_parameters: int = STRICT_4B_MAX_PARAMETERS,
        timeout_s: float = 120.0,
        client: Optional[OllamaClient] = None,
        validator: Optional[ModelValidator] = None,
        validate_on_init: bool = False,
    ) -> None:
        self.client = client or OllamaClient(base_url=base_url, timeout_s=timeout_s)
        self.registry = ModelRegistry(self.client)
        self.validator = validator or ModelValidator(self.registry)

        self.ValidatorCheck(model_name)
        self.model_name = str(model_name).strip()
        self.base_url = self.client.base_url
        self.temperature = float(temperature)
        self.seed = seed
        self.top_k = top_k
        self.top_p = top_p
        self.repeat_penalty = repeat_penalty
        self.num_ctx = int(num_ctx)
        self.reasoning = reasoning
        self.enforce_4b_limit = bool(enforce_4b_limit)
        self.max_parameters = int(max_parameters)
        self.timeout_s = float(timeout_s)

        self.verified_metadata: Optional[ModelMetadata] = None
        self.total_requests: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_latency_ms: float = 0.0
        self.prompt_tokens_measured: bool = False

        if validate_on_init:
            self.verify_runtime_model()

    def ValidatorCheck(self, model_name: str) -> None:
        ModelValidator.assert_not_cloud_model(model_name)

    def verify_runtime_model(self) -> ModelMetadata:
        """Verify model availability and parameter limit against live local Ollama `/api/show`."""
        meta = self.validator.validate_chat_model(
            self.model_name,
            enforce_4b_limit=self.enforce_4b_limit,
            max_parameters=self.max_parameters,
        )
        self.verified_metadata = meta
        return meta

    def build_langchain_chat_model(self, **overrides: Any) -> Any:
        """Return a LangChain `ChatOllama` instance configured with deterministic sampling settings."""
        if self.enforce_4b_limit and self.verified_metadata is None:
            self.verify_runtime_model()
        from langchain_ollama import ChatOllama

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed
        if self.top_k is not None:
            kwargs["top_k"] = self.top_k
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        if self.repeat_penalty is not None:
            kwargs["repeat_penalty"] = self.repeat_penalty
        if self.reasoning is not None:
            kwargs["reasoning"] = self.reasoning
        kwargs.update(overrides)
        return ChatOllama(**kwargs)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Execute a direct chat completion via Ollama `/api/chat` and record latency & token telemetry."""
        if self.enforce_4b_limit and self.verified_metadata is None:
            self.verify_runtime_model()

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": str(prompt)})

        options: Dict[str, Any] = {
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
        }
        if self.seed is not None:
            options["seed"] = int(self.seed)
        if self.top_k is not None:
            options["top_k"] = int(self.top_k)
        if self.top_p is not None:
            options["top_p"] = float(self.top_p)
        if self.repeat_penalty is not None:
            options["repeat_penalty"] = float(self.repeat_penalty)

        t0 = time.perf_counter()
        resp = self.client.chat(
            model_name=self.model_name,
            messages=messages,
            options=options,
            think=self.reasoning,
            timeout_s=self.timeout_s,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        msg = resp.get("message") or {}
        content = str(msg.get("content", ""))

        p_tok = resp.get("prompt_eval_count")
        c_tok = resp.get("eval_count")
        self.total_requests += 1
        self.total_latency_ms += elapsed_ms
        if isinstance(p_tok, int):
            self.total_prompt_tokens += p_tok
            self.prompt_tokens_measured = True
        if isinstance(c_tok, int):
            self.total_completion_tokens += c_tok

        return {
            "content": content,
            "model": str(resp.get("model", self.model_name)),
            "elapsed_ms": elapsed_ms,
            "prompt_eval_count": p_tok,
            "eval_count": c_tok,
            "load_duration_ns": resp.get("load_duration"),
            "total_duration_ns": resp.get("total_duration"),
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        avg_ms = round(self.total_latency_ms / self.total_requests, 2) if self.total_requests else 0.0
        return {
            "model_name": self.model_name,
            "enforce_4b_limit": self.enforce_4b_limit,
            "verified_metadata": self.verified_metadata.to_dict() if self.verified_metadata else None,
            "total_requests": self.total_requests,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": avg_ms,
            "prompt_tokens_measured": self.prompt_tokens_measured,
            "total_prompt_tokens": self.total_prompt_tokens if self.prompt_tokens_measured else None,
            "total_completion_tokens": self.total_completion_tokens if self.prompt_tokens_measured else None,
        }
