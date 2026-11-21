"""Local Ollama API client with retry handling, rate limiting, and tool support."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)


@dataclass
class OllamaResponse:
    model: str
    content: str
    thinking: Optional[str]
    tool_calls: list[dict[str, Any]]
    raw_payload: dict[str, Any]
    duration_seconds: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    done_reason: Optional[str]
    error: Optional[str] = None
    is_infrastructure_error: bool = False


def extract_thinking(content: str) -> tuple[str, Optional[str]]:
    """Strip inline <think> blocks from content if present."""
    matches = THINK_RE.findall(content or "")
    thinking = "\n".join(m.strip() for m in matches).strip() if matches else None
    cleaned = THINK_RE.sub("", content or "").strip()
    return cleaned, thinking


class OllamaClient:
    """Synchronous and asynchronous client for local Ollama REST API."""

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 180,
        retries: int = 2,
        rate_limit_delay_seconds: float = 0.05,
    ):
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.rate_limit_delay_seconds = rate_limit_delay_seconds

    def get_version(self) -> str:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.host}/api/version")
            resp.raise_for_status()
            return str(resp.json().get("version", "unknown"))

    def list_models(self) -> list[dict[str, Any]]:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{self.host}/api/tags")
            resp.raise_for_status()
            return list(resp.json().get("models", []))

    def show_model(self, model_name: str) -> dict[str, Any]:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{self.host}/api/show", json={"model": model_name})
            resp.raise_for_status()
            return dict(resp.json())

    def _build_payload(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        num_predict: int = 96,
        think: bool = False,
        tools: Optional[list[dict[str, Any]]] = None,
        seed: Optional[int] = 42,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": num_predict,
        }
        if seed is not None:
            options["seed"] = seed
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": options,
        }
        if tools:
            payload["tools"] = tools
        return payload

    def _parse_response(self, model: str, data: dict[str, Any], duration: float) -> OllamaResponse:
        msg = data.get("message") or {}
        raw_content = str(msg.get("content") or "")
        cleaned, inline_thinking = extract_thinking(raw_content)
        thinking = msg.get("thinking") or inline_thinking
        tool_calls = list(msg.get("tool_calls") or [])
        return OllamaResponse(
            model=model,
            content=cleaned,
            thinking=thinking,
            tool_calls=tool_calls,
            raw_payload=data,
            duration_seconds=round(duration, 4),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            done_reason=data.get("done_reason"),
            error=None,
            is_infrastructure_error=False,
        )

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        num_predict: int = 96,
        think: bool = False,
        tools: Optional[list[dict[str, Any]]] = None,
        seed: Optional[int] = 42,
    ) -> OllamaResponse:
        payload = self._build_payload(model, messages, temperature, num_predict, think, tools, seed)
        last_err: Optional[str] = None
        for attempt in range(self.retries + 1):
            t0 = time.perf_counter()
            try:
                if self.rate_limit_delay_seconds > 0:
                    time.sleep(self.rate_limit_delay_seconds)
                with httpx.Client(timeout=float(self.timeout_seconds)) as client:
                    resp = client.post(f"{self.host}/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                return self._parse_response(model, data, time.perf_counter() - t0)
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
        return OllamaResponse(
            model=model,
            content="",
            thinking=None,
            tool_calls=[],
            raw_payload={"error": last_err},
            duration_seconds=0.0,
            prompt_tokens=None,
            completion_tokens=None,
            done_reason="error",
            error=last_err,
            is_infrastructure_error=True,
        )

    async def achat(
        self,
        client: httpx.AsyncClient,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        num_predict: int = 96,
        think: bool = False,
        tools: Optional[list[dict[str, Any]]] = None,
        seed: Optional[int] = 42,
    ) -> OllamaResponse:
        payload = self._build_payload(model, messages, temperature, num_predict, think, tools, seed)
        last_err: Optional[str] = None
        for attempt in range(self.retries + 1):
            t0 = time.perf_counter()
            try:
                if self.rate_limit_delay_seconds > 0:
                    await asyncio.sleep(self.rate_limit_delay_seconds)
                resp = await client.post(
                    f"{self.host}/api/chat",
                    json=payload,
                    timeout=float(self.timeout_seconds),
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(model, data, time.perf_counter() - t0)
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
        return OllamaResponse(
            model=model,
            content="",
            thinking=None,
            tool_calls=[],
            raw_payload={"error": last_err},
            duration_seconds=0.0,
            prompt_tokens=None,
            completion_tokens=None,
            done_reason="error",
            error=last_err,
            is_infrastructure_error=True,
        )
