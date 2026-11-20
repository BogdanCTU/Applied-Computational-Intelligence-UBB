"""Low-level loopback-only HTTP client for the local Ollama API (`/api/*`)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..config import validate_loopback_url

logger = logging.getLogger(__name__)


class OllamaClientError(RuntimeError):
    """Raised when a local Ollama API call fails or times out."""


class OllamaClient:
    """Strictly loopback Ollama REST client with retry, timeout, and telemetry tracking."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 120.0,
        max_retries: int = 2,
        retry_backoff_s: float = 0.5,
    ) -> None:
        self.base_url = validate_loopback_url(base_url)
        self.timeout_s = float(timeout_s)
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_s = float(retry_backoff_s)
        self.telemetry_records: List[Dict[str, Any]] = []

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        effective_timeout = float(timeout_s if timeout_s is not None else self.timeout_s)

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    parsed = json.loads(raw) if raw.strip() else {}
                    self.telemetry_records.append(
                        {
                            "method": method,
                            "path": path,
                            "attempt": attempt + 1,
                            "status": resp.status,
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                    return parsed
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                last_exc = OllamaClientError(
                    f"Ollama HTTP {exc.code} on {method} {path}: {body or exc.reason}"
                )
                # Do not retry 404 (model not found) or 400 (bad request)
                if exc.code in (400, 404):
                    raise last_exc from exc
            except Exception as exc:
                last_exc = OllamaClientError(
                    f"Ollama connection failure on {method} {path} ({self.base_url}): {exc}"
                )
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff_s * (attempt + 1))

        assert last_exc is not None
        raise last_exc

    def get_version(self) -> str:
        data = self._request_json("GET", "/api/version", timeout_s=5.0)
        return str(data.get("version", "unknown"))

    def is_reachable(self) -> bool:
        try:
            _ = self.get_version()
            return True
        except Exception:
            return False

    def list_tags(self) -> List[Dict[str, Any]]:
        data = self._request_json("GET", "/api/tags", timeout_s=10.0)
        return list(data.get("models", []) or [])

    def list_running(self) -> List[Dict[str, Any]]:
        data = self._request_json("GET", "/api/ps", timeout_s=5.0)
        return list(data.get("models", []) or [])

    def show_model(self, model_name: str) -> Dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/show",
            payload={"name": str(model_name).strip()},
            timeout_s=15.0,
        )

    def embed(
        self,
        model_name: str,
        inputs: List[str] | str,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        texts = [inputs] if isinstance(inputs, str) else list(inputs)
        return self._request_json(
            "POST",
            "/api/embed",
            payload={"model": str(model_name).strip(), "input": texts},
            timeout_s=timeout_s,
        )

    def chat(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        think: Optional[bool] = None,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": str(model_name).strip(),
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        if think is not None:
            payload["think"] = bool(think)
        return self._request_json("POST", "/api/chat", payload=payload, timeout_s=timeout_s)

    def unload_model(self, model_name: str) -> bool:
        """Unload an active model from unified memory / VRAM via keep_alive=0."""
        try:
            self._request_json(
                "POST",
                "/api/generate",
                payload={"model": str(model_name).strip(), "keep_alive": 0},
                timeout_s=10.0,
            )
            return True
        except Exception as exc:
            logger.debug("Optional model unload for %s skipped: %s", model_name, exc)
            return False
