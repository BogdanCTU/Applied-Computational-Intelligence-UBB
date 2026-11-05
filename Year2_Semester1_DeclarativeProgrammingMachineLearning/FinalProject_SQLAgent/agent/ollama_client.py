"""Local Ollama HTTP API client supporting native tool calling and structured JSON fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import httpx

from config.settings import LOCAL_HOSTS, OllamaSettings

log = logging.getLogger(__name__)

# Regular expressions for cleaning and isolating JSON in fallback responses
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class OllamaClientError(RuntimeError):
    """Base error for Ollama client failures."""


class OllamaConnectionError(OllamaClientError):
    """Raised when the local Ollama server cannot be reached."""


class OllamaConnectionRefusedError(OllamaConnectionError):
    """Raised when connection is actively refused (e.g. Ollama daemon not running)."""


class OllamaDisconnectError(OllamaClientError):
    """Raised when Ollama abruptly disconnects, resets connection, or closes socket without responding."""


class OllamaTimeoutError(OllamaClientError):
    """Raised when a request to Ollama times out."""


class OllamaResponseError(OllamaClientError):
    """Raised when Ollama returns an HTTP error, malformed, or invalid response."""


class OllamaHTTPError(OllamaResponseError):
    """Raised when Ollama returns an HTTP error status code (e.g. 4xx, 5xx)."""

    def __init__(self, status_code: int, message: str, raw_text: str = "") -> None:
        super().__init__(f"Ollama HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.raw_text = raw_text


class OllamaModelNotFoundError(OllamaHTTPError):
    """Raised when the specified model is not available locally."""

    def __init__(self, model_name: str, message: str = "") -> None:
        msg = message or f"Model '{model_name}' not found in Ollama. Run: ollama pull {model_name}"
        super().__init__(status_code=404, message=msg, raw_text=msg)
        self.model_name = model_name


class OllamaInvalidJSONError(OllamaResponseError):
    """Raised when Ollama returns invalid, unparseable, or malformed JSON."""


class OllamaEmptyResponseError(OllamaResponseError):
    """Raised when Ollama returns an empty response with no content and no tool calls."""


@dataclass
class OllamaToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments,
            },
        }


@dataclass
class OllamaChatResponse:
    content: str
    tool_calls: list[OllamaToolCall] = field(default_factory=list)
    thinking: str | None = None
    finish_reason: str | None = None
    raw_message: dict[str, Any] = field(default_factory=dict)
    total_duration_s: float | None = None
    used_fallback: bool = False

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class OllamaClient:
    """Asynchronous HTTP client for the local Ollama daemon."""

    def __init__(self, settings: OllamaSettings) -> None:
        self.settings = settings
        self.base_url = self._validate_and_normalize_host(settings.host)
        self.model = settings.model.strip()
        self.timeout_s = float(settings.request_timeout_s)

    @staticmethod
    def _validate_and_normalize_host(host: str) -> str:
        cleaned = (host or "").strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise OllamaConnectionError(
                f"Invalid Ollama host URL: '{host}'. Expected e.g. 'http://localhost:11434'"
            )
        if parsed.hostname not in LOCAL_HOSTS:
            raise OllamaConnectionError(
                f"Refusing to connect to remote host '{parsed.hostname}'. "
                "Only local endpoints (localhost / 127.0.0.1) are permitted for data privacy."
            )
        return cleaned

    def _create_http_client(self, *, force_close: bool = False) -> httpx.AsyncClient:
        headers = {"Connection": "close"} if force_close else None
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(
                timeout=self.timeout_s,
                connect=10.0,
                read=self.timeout_s,
                write=30.0,
                pool=10.0,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            ),
        )

    async def check_connection(self) -> tuple[bool, str]:
        """Check if local Ollama daemon is reachable. Return (is_ok, version_or_error)."""
        try:
            async with self._create_http_client() as client:
                resp = await client.get("/api/version")
                if resp.status_code == 200:
                    ver = resp.json().get("version", "unknown")
                    return True, str(ver)
                return False, f"HTTP {resp.status_code}: {resp.text}"
        except httpx.TimeoutException:
            return False, f"Connection timed out after {self.timeout_s}s"
        except httpx.ConnectError as exc:
            return False, f"Failed to connect to {self.base_url}: {exc}"
        except httpx.RequestError as exc:
            return False, f"Request error communicating with {self.base_url}: {exc}"

    async def list_installed_models(self) -> list[str]:
        """Return list of locally installed model tags."""
        try:
            async with self._create_http_client() as client:
                resp = await client.get("/api/tags")
                if resp.status_code != 200:
                    raise OllamaHTTPError(
                        status_code=resp.status_code,
                        message=f"Failed to query /api/tags: HTTP {resp.status_code}",
                        raw_text=resp.text,
                    )
                models = resp.json().get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Timed out listing Ollama models") from exc
        except httpx.RemoteProtocolError as exc:
            raise OllamaDisconnectError(f"Ollama disconnected while querying models: {exc}") from exc
        except httpx.ConnectError as exc:
            err_lower = str(exc).lower()
            if "refused" in err_lower or "10061" in err_lower or "econnrefused" in err_lower:
                raise OllamaConnectionRefusedError(
                    f"Connection refused at {self.base_url}. Ensure Ollama is running (`ollama serve`)."
                ) from exc
            raise OllamaConnectionError(f"Cannot connect to Ollama: {exc}") from exc
        except httpx.RequestError as exc:
            raise OllamaConnectionError(f"Cannot connect to Ollama: {exc}") from exc

    async def check_model_availability(self, model_name: str | None = None) -> bool:
        """Verify whether the requested model is installed locally."""
        target = (model_name or self.model).strip()
        tags = await self.list_installed_models()
        wanted = target if ":" in target else f"{target}:latest"
        return wanted in tags or target in tags

    async def probe_tool_capability(self) -> str:
        """Probe model's tool calling capability. Return 'native' or 'json'."""
        probe_tool = {
            "type": "function",
            "function": {
                "name": "probe_tool",
                "description": "Probe tool to check function calling",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "echo": {"type": "string", "description": "Echo message"}
                    },
                    "required": ["echo"],
                },
            },
        }
        messages = [
            {
                "role": "user",
                "content": "Call the probe_tool function with echo='hello'.",
            }
        ]

        try:
            res = await self.chat(
                messages=messages,
                tools=[probe_tool],
                tool_mode="native",
            )
            if res.has_tool_calls and res.tool_calls[0].name == "probe_tool":
                log.info("Native tool calling verified for model '%s'", self.model)
                return "native"
        except Exception as exc:  # noqa: BLE001
            log.warning("Tool calling probe failed (%s); defaulting to JSON mode", exc)

        log.info(
            "Native tool calling not confirmed; using structured JSON mode for '%s'",
            self.model,
        )
        return "json"

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        tool_mode: str = "native",
    ) -> OllamaChatResponse:
        """Send a chat request to Ollama `/api/chat` with bounded retry and strict error classification."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "options": {
                "temperature": float(self.settings.temperature),
                "top_p": float(self.settings.top_p),
                "num_ctx": int(self.settings.num_ctx),
            },
            "keep_alive": self.settings.keep_alive,
        }

        if tool_mode == "native" and tools:
            payload["tools"] = list(tools)
        elif tool_mode == "json":
            payload["format"] = "json"

        payload_bytes = len(json.dumps(payload))
        start_ts = time.perf_counter()
        MAX_RETRIES = 1
        resp = None

        for attempt in range(MAX_RETRIES + 1):
            is_retry = attempt > 0
            try:
                log.info(
                    "Ollama chat request [attempt %d/%d] endpoint=%s/api/chat model=%s mode=%s msgs=%d tools=%d payload_size=%d bytes",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    self.base_url,
                    self.model,
                    tool_mode,
                    len(messages),
                    len(tools) if tools else 0,
                    payload_bytes,
                )
                async with self._create_http_client(force_close=is_retry) as client:
                    resp = await client.post("/api/chat", json=payload)
                break  # Request completed (may still be non-200, handled below)
            except httpx.RemoteProtocolError as exc:
                elapsed = time.perf_counter() - start_ts
                log.warning(
                    "Ollama remote protocol disconnect on attempt %d/%d (duration=%.2fs, payload=%d bytes): %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    elapsed,
                    payload_bytes,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5)
                    continue
                raise OllamaDisconnectError(
                    f"Ollama server disconnected without sending a response: {exc}. "
                    "The local model runner may have crashed, run out of memory, or dropped the socket."
                ) from exc
            except (ConnectionResetError, BrokenPipeError) as exc:
                elapsed = time.perf_counter() - start_ts
                log.warning(
                    "Ollama connection reset on attempt %d/%d (duration=%.2fs): %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    elapsed,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5)
                    continue
                raise OllamaDisconnectError(f"Connection to Ollama was reset: {exc}") from exc
            except httpx.TimeoutException as exc:
                elapsed = time.perf_counter() - start_ts
                log.error(
                    "Ollama request timed out after %.2fs (configured timeout=%.1fs): %s",
                    elapsed,
                    self.timeout_s,
                    exc,
                )
                raise OllamaTimeoutError(
                    f"Ollama chat request timed out after {self.timeout_s}s"
                ) from exc
            except httpx.ConnectError as exc:
                err_str = str(exc).lower()
                is_refused = "refused" in err_str or "10061" in err_str or "econnrefused" in err_str
                log.error(
                    "Ollama connection error (refused=%s): %s",
                    is_refused,
                    exc,
                )
                if is_refused:
                    raise OllamaConnectionRefusedError(
                        f"Cannot connect to Ollama at {self.base_url}: connection refused. "
                        "Please ensure the Ollama daemon is running (`ollama serve`)."
                    ) from exc
                raise OllamaConnectionError(
                    f"Failed to connect to Ollama at {self.base_url}: {exc}"
                ) from exc
            except httpx.ProtocolError as exc:
                log.error("Ollama HTTP protocol error: %s", exc)
                raise OllamaDisconnectError(f"HTTP protocol error communicating with Ollama: {exc}") from exc
            except httpx.RequestError as exc:
                err_str = str(exc).lower()
                if "reset" in err_str or "10054" in err_str or "disconnected" in err_str:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(0.5)
                        continue
                    raise OllamaDisconnectError(f"Ollama disconnected during request: {exc}") from exc
                raise OllamaConnectionError(
                    f"Failed to communicate with Ollama at {self.base_url}: {exc}"
                ) from exc

        if resp is None:
            raise OllamaDisconnectError("No response received from Ollama after all attempts.")

        if resp.status_code == 404:
            raise OllamaModelNotFoundError(
                self.model,
                f"Model '{self.model}' not found in Ollama. Run: ollama pull {self.model}",
            )
        if resp.status_code != 200:
            # Check for native tool-calling XML parse failure in Ollama (HTTP 500 / XML syntax error)
            if tool_mode == "native" and tools and (
                resp.status_code == 500
                or "XML syntax error" in resp.text
                or "element <function>" in resp.text
                or "element " in resp.text
            ):
                log.warning(
                    "Ollama native tool calling failed with HTTP %d (%s); automatically falling back to structured JSON mode",
                    resp.status_code,
                    resp.text.strip(),
                )
                return await self._fallback_chat_json(messages)

            raise OllamaHTTPError(
                status_code=resp.status_code,
                message=resp.text.strip(),
                raw_text=resp.text,
            )

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise OllamaInvalidJSONError(f"Ollama returned invalid JSON response: {exc}") from exc

        raw_msg = data.get("message", {})
        content = raw_msg.get("content", "") or ""
        thinking = raw_msg.get("thinking")

        # Strip inline <think>...</think> tags if present in content
        if "<think>" in content and "</think>" in content:
            think_match = re.search(r"<think>([\s\S]*?)</think>", content)
            if think_match and not thinking:
                thinking = think_match.group(1).strip()
            content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()

        finish_reason = data.get("done_reason")
        total_duration = data.get("total_duration")
        duration_s = (
            round(total_duration / 1e9, 3) if total_duration is not None else None
        )

        tool_calls: list[OllamaToolCall] = []

        if tool_mode == "native":
            raw_tool_calls = raw_msg.get("tool_calls", [])
            for idx, call in enumerate(raw_tool_calls):
                func = call.get("function", {})
                name = func.get("name", "")
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except json.JSONDecodeError:
                        args = {"raw": args}
                if name:
                    call_id = call.get("id") or f"call_{idx}_{name}"
                    tool_calls.append(
                        OllamaToolCall(
                            id=call_id,
                            name=name,
                            arguments=args if isinstance(args, dict) else {},
                        )
                    )

            # Fallback check: if native mode returned empty tool_calls but content has explicit tool call
            if not tool_calls and content.strip():
                extracted = self._extract_json_tool_call(content)
                if extracted:
                    tool_calls.append(extracted)
                else:
                    fn_call = self._extract_text_function_call(content)
                    if fn_call:
                        tool_calls.append(fn_call)

        elif tool_mode == "json":
            # Parse structured JSON fallback response
            extracted = self._extract_json_tool_call(content)
            if extracted:
                tool_calls.append(extracted)
            else:
                fn_call = self._extract_text_function_call(content)
                if fn_call:
                    tool_calls.append(fn_call)
                else:
                    final_msg = self._extract_json_final_response(content)
                    if final_msg is not None:
                        content = final_msg

        # Empty assistant response check
        if not content.strip() and not tool_calls and not thinking:
            raise OllamaEmptyResponseError(
                "Ollama returned an empty response containing no content, tool calls, or reasoning."
            )

        return OllamaChatResponse(
            content=content,
            tool_calls=tool_calls,
            thinking=thinking,
            finish_reason=finish_reason,
            raw_message=raw_msg,
            total_duration_s=duration_s,
        )

    async def _fallback_chat_json(
        self,
        messages: Sequence[Mapping[str, Any]],
    ) -> OllamaChatResponse:
        """Fallback to structured JSON mode when native tool calling fails."""
        from config.prompts import JSON_FALLBACK_INSTRUCTIONS

        fallback_messages: list[dict[str, Any]] = []
        has_system = False
        for m in messages:
            m_copy = dict(m)
            if m_copy.get("role") == "system":
                has_system = True
                content = str(m_copy.get("content", ""))
                if "IMPORTANT OUTPUT FORMAT" not in content:
                    m_copy["content"] = content.rstrip() + "\n\n" + JSON_FALLBACK_INSTRUCTIONS.strip()
            fallback_messages.append(m_copy)

        if not has_system:
            fallback_messages.insert(
                0,
                {
                    "role": "system",
                    "content": JSON_FALLBACK_INSTRUCTIONS.strip(),
                },
            )

        resp = await self.chat(
            messages=fallback_messages,
            tools=None,
            tool_mode="json",
        )
        resp.used_fallback = True
        return resp

    @classmethod
    def _extract_json_tool_call(cls, text: str) -> OllamaToolCall | None:
        """Parse structured tool call JSON from text if present across various format variations."""
        cleaned = text.strip()
        candidates: list[str] = []

        # 1. Search for markdown ```json ... ``` blocks
        for match in _JSON_BLOCK_RE.finditer(cleaned):
            candidates.append(match.group(1).strip())

        # 2. Search for bracketed candidates
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first != -1 and last > first:
            candidates.append(cleaned[first : last + 1].strip())

        candidates.append(cleaned)

        for cand in candidates:
            try:
                data = json.loads(cand)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            # Case A: {"tool_calls": [{"function": {"name": ..., "arguments": ...}}]}
            if "tool_calls" in data and isinstance(data["tool_calls"], list) and data["tool_calls"]:
                first_call = data["tool_calls"][0]
                if isinstance(first_call, dict):
                    fn = first_call.get("function", first_call)
                    t_name = fn.get("name") or fn.get("tool")
                    raw_args = fn.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            raw_args = {}
                    if t_name and isinstance(t_name, str):
                        return OllamaToolCall(
                            id=f"json_call_{t_name}",
                            name=t_name,
                            arguments=raw_args if isinstance(raw_args, dict) else {},
                        )

            # Case B: {"function": {"name": ..., "arguments": ...}}
            if "function" in data and isinstance(data["function"], dict):
                t_name = data["function"].get("name")
                raw_args = data["function"].get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {}
                if t_name and isinstance(t_name, str):
                    return OllamaToolCall(
                        id=f"json_call_{t_name}",
                        name=t_name,
                        arguments=raw_args if isinstance(raw_args, dict) else {},
                    )

            # Case C: Direct tool call dict (type="tool_call" or explicit tool / name / action key)
            t_name = None
            if data.get("type") == "tool_call":
                t_name = data.get("tool") or data.get("name")
            elif "tool" in data and isinstance(data["tool"], str):
                t_name = data["tool"]
            elif "action" in data and isinstance(data["action"], str) and data["action"] != "final_response":
                t_name = data["action"]
            elif "name" in data and isinstance(data["name"], str) and data["name"] not in {"assistant", "user", "system"}:
                t_name = data["name"]

            if t_name and isinstance(t_name, str):
                raw_args = (
                    data.get("arguments")
                    or data.get("parameters")
                    or data.get("params")
                    or data.get("args")
                )
                if raw_args is None:
                    # Model provided flat arguments at top level of JSON
                    reserved = {"type", "tool", "name", "action", "function", "id", "thought", "thinking"}
                    raw_args = {k: v for k, v in data.items() if k not in reserved}
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {}
                return OllamaToolCall(
                    id=f"json_call_{t_name}",
                    name=t_name,
                    arguments=raw_args if isinstance(raw_args, dict) else {},
                )

        return None

    @classmethod
    def _extract_json_final_response(cls, text: str) -> str | None:
        """Extract message from a structured JSON final_response payload across schema variants."""
        cleaned = text.strip()
        candidates: list[str] = []

        for match in _JSON_BLOCK_RE.finditer(cleaned):
            candidates.append(match.group(1).strip())

        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first != -1 and last > first:
            candidates.append(cleaned[first : last + 1].strip())

        candidates.append(cleaned)

        for cand in candidates:
            try:
                data = json.loads(cand)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            if data.get("type") == "final_response":
                msg = data.get("message") or data.get("content") or data.get("response") or ""
                return str(msg)
            for k in ("final_response", "response", "message", "answer"):
                if k in data and isinstance(data[k], str):
                    return str(data[k])

        return None

    @classmethod
    def _extract_text_function_call(cls, text: str) -> OllamaToolCall | None:
        """Parse pseudo function call syntax like inspect_database_schema() or execute_readonly_sql(...)."""
        permitted = [
            "inspect_database_schema",
            "get_table_sample",
            "prepare_sql_query",
            "execute_readonly_sql",
            "generate_pdf_report",
            "generate_csv_report",
        ]
        pattern = r"\b(" + "|".join(permitted) + r")\s*\(([\s\S]*?)\)"
        match = re.search(pattern, text)
        if not match:
            return None
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        args: dict[str, Any] = {}
        if not args_str:
            return OllamaToolCall(id=f"text_call_{tool_name}", name=tool_name, arguments=args)

        if "=" in args_str:
            kv_matches = re.finditer(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))', args_str)
            for kv in kv_matches:
                k = kv.group(1)
                v = kv.group(2) if kv.group(2) is not None else (kv.group(3) if kv.group(3) is not None else kv.group(4))
                args[k] = v
        else:
            str_match = re.match(r'^(?:"([^"]*)"|\'([^\']*)\')$', args_str, re.DOTALL)
            if str_match:
                val = str_match.group(1) if str_match.group(1) is not None else str_match.group(2)
                if tool_name in {"prepare_sql_query", "execute_readonly_sql"}:
                    args["sql_query"] = val
                elif tool_name in {"inspect_database_schema", "get_table_sample"}:
                    args["table_name"] = val

        return OllamaToolCall(id=f"text_call_{tool_name}", name=tool_name, arguments=args)


