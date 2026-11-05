"""Official Python MCP stdio client managing the local MCP server subprocess.

Used by both integration tests and the agent orchestrator so all database and
reporting operations travel over genuine MCP JSON-RPC stdio transport.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from config.paths import app_root, is_frozen, user_data_root
from config.settings import AppSettings

log = logging.getLogger(__name__)

# Keys to sanitize from argument and result logs
_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(?:password|passwd|token|secret|api[_-]?key|auth|bearer|credentials|private[_-]?key)",
    re.IGNORECASE,
)


def mask_sensitive_data(value: Any, *, max_depth: int = 5) -> Any:
    """Recursively scrub sensitive keys and credentials from data payloads without agent dependency."""
    if max_depth <= 0:
        return "<depth-limit>"

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for k, v in value.items():
            if _SENSITIVE_KEY_PATTERNS.search(str(k)):
                cleaned[k] = "[REDACTED_CREDENTIAL]"
            else:
                cleaned[k] = mask_sensitive_data(v, max_depth=max_depth - 1)
        return cleaned

    if isinstance(value, (list, tuple)):
        if len(value) > 30:
            preview = [mask_sensitive_data(x, max_depth=max_depth - 1) for x in value[:20]]
            preview.append(f"... [+{len(value) - 20} more items]")
            return preview
        return [mask_sensitive_data(x, max_depth=max_depth - 1) for x in value]

    if isinstance(value, str):
        if len(value) > 200 and "eyJ" in value:
            return "[REDACTED_TOKEN_PATTERN]"
        return value

    return value


class MCPClientError(RuntimeError):
    """Raised when the MCP client is not connected or transport communication fails."""


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPInvocationLog:
    """Structured diagnostic record captured for every MCP tool invocation."""

    invocation_id: str
    tool_name: str
    arguments: dict[str, Any]
    start_time: str
    end_time: str
    duration_ms: float
    status: str  # "success" or "failed"
    error_origin: str | None = None  # "client", "server", "tool_arguments", "sqlite", "report_generation"
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "arguments": mask_sensitive_data(self.arguments),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_origin": self.error_origin,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "metadata": self.metadata,
        }


@dataclass
class MCPToolCallResult:
    tool_name: str
    is_error: bool
    data: dict[str, Any]
    raw_text: str
    invocation_id: str = ""
    duration_ms: float = 0.0
    error_origin: str | None = None
    original_exception_type: str | None = None
    original_exception_message: str | None = None
    traceback: str | None = None
    invocation_log: MCPInvocationLog | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_subprocess_env(
    settings: AppSettings | None = None,
    env_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = get_default_environment()
    if not is_frozen():
        root_str = str(app_root())
        existing_py = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{root_str}{os.pathsep}{existing_py}" if existing_py else root_str
        )

    for key, val in os.environ.items():
        if key.startswith("REPORT_AGENT_"):
            env[key] = val

    if settings is not None:
        env["REPORT_AGENT_DB_PATH"] = str(settings.database_path)
        env["REPORT_AGENT_OUTPUT_DIR"] = str(settings.output_dir)
        env["REPORT_AGENT_MAX_ROWS"] = str(settings.database.max_result_rows)
        env["REPORT_AGENT_QUERY_TIMEOUT"] = str(settings.database.query_timeout_s)
        env["REPORT_AGENT_LOG_LEVEL"] = str(settings.logging.level)

    if env_overrides:
        for key, val in env_overrides.items():
            env[str(key)] = str(val)

    return env


def build_stdio_server_params(
    settings: AppSettings | None = None,
    env_overrides: Mapping[str, str] | None = None,
) -> StdioServerParameters:
    """Construct ``StdioServerParameters`` for source or PyInstaller execution."""
    if is_frozen():
        command = sys.executable
        args = ["--mcp-server"]
    else:
        command = sys.executable
        args = ["-m", "mcp_layer.server"]

    return StdioServerParameters(
        command=command,
        args=args,
        env=_build_subprocess_env(settings=settings, env_overrides=env_overrides),
        cwd=str(user_data_root() if is_frozen() else app_root()),
    )


class MCPStdioClient:
    """Async context-managed, loop-aware MCP stdio client speaking to ``mcp_layer.server``."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        env_overrides: Mapping[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._env_overrides = dict(env_overrides) if env_overrides else None
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._owner_loop: asyncio.AbstractEventLoop | None = None

    def _get_current_loop(self) -> asyncio.AbstractEventLoop | None:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    @property
    def is_connected(self) -> bool:
        curr_loop = self._get_current_loop()
        if self._session is None or self._owner_loop is None:
            return False
        if curr_loop is not None and (self._owner_loop is not curr_loop or self._owner_loop.is_closed()):
            return False
        return True

    async def connect(self) -> "MCPStdioClient":
        curr_loop = self._get_current_loop()
        if self.is_connected:
            return self

        # Cleanly dispose of stale stack if event loop changed or connection died
        if self._exit_stack is not None:
            try:
                if self._owner_loop is curr_loop and self._owner_loop is not None and not self._owner_loop.is_closed():
                    await self._exit_stack.aclose()
            except Exception as e:
                log.debug("Ignoring exception while resetting stale exit stack: %s", e)
            finally:
                self._exit_stack = None
                self._session = None

        params = build_stdio_server_params(
            settings=self._settings,
            env_overrides=self._env_overrides,
        )
        stack = AsyncExitStack()
        try:
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(params)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except BaseException as exc:
            await stack.aclose()
            raise MCPClientError(f"Failed to start/initialize MCP stdio server: {exc}") from exc

        self._exit_stack = stack
        self._session = session
        self._owner_loop = curr_loop
        log.info("Connected to local MCP stdio server subprocess (loop=%s)", id(curr_loop))
        return self

    async def reconnect(self) -> "MCPStdioClient":
        """Force a clean reconnection to the MCP stdio server."""
        await self.close()
        return await self.connect()

    async def close(self) -> None:
        stack = self._exit_stack
        owner_loop = self._owner_loop
        curr_loop = self._get_current_loop()

        self._session = None
        self._exit_stack = None
        self._owner_loop = None

        if stack is not None:
            if owner_loop is not None and not owner_loop.is_closed() and owner_loop is curr_loop:
                try:
                    await stack.aclose()
                    log.info("Closed MCP stdio server subprocess cleanly")
                except Exception as exc:
                    log.warning("Non-critical error closing MCP stack: %s", exc)

    async def __aenter__(self) -> "MCPStdioClient":
        return await self.connect()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def _require_session(self) -> ClientSession:
        if not self.is_connected or self._session is None:
            raise MCPClientError("MCPStdioClient is not connected")
        return self._session

    async def list_tools(self) -> list[MCPToolSpec]:
        if not self.is_connected:
            await self.connect()
        session = self._require_session()
        resp = await session.list_tools()
        return [
            MCPToolSpec(
                name=t.name,
                description=t.description or "",
                input_schema=dict(t.inputSchema or {}),
            )
            for t in resp.tools
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        max_retries: int = 1,
    ) -> MCPToolCallResult:
        inv_id = str(uuid.uuid4())[:8]
        raw_args = dict(arguments or {})
        sanitized_args = mask_sensitive_data(raw_args)
        start_time_iso = datetime.now().isoformat(timespec="milliseconds")
        t0 = time.perf_counter()

        last_exc: Exception | None = None
        raw_res: Any = None

        for attempt in range(max_retries + 1):
            try:
                if not self.is_connected:
                    log.info("Re-establishing MCP stdio connection for tool '%s' (invocation %s)", tool_name, inv_id)
                    await self.connect()

                session = self._require_session()
                raw_res = await session.call_tool(tool_name, raw_args)
                last_exc = None
                break
            except (RuntimeError, BrokenPipeError, ConnectionResetError, ConnectionError, MCPClientError) as exc:
                last_exc = exc
                err_str = str(exc)
                is_connection_loss = (
                    "closed" in err_str.lower()
                    or "broken pipe" in err_str.lower()
                    or isinstance(exc, (BrokenPipeError, ConnectionResetError, MCPClientError))
                )
                if is_connection_loss and attempt < max_retries:
                    log.warning(
                        "MCP connection lost during '%s' (attempt %d/%d): %s. Reconnecting...",
                        tool_name,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                    )
                    self._session = None
                    self._exit_stack = None
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                break

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        end_time_iso = datetime.now().isoformat(timespec="milliseconds")

        # Handle exception during RPC invocation
        if last_exc is not None:
            tb_str = traceback.format_exc()
            exc_type = last_exc.__class__.__name__
            exc_msg = str(last_exc)

            if "closed" in exc_msg.lower() or isinstance(last_exc, (BrokenPipeError, ConnectionResetError, MCPClientError)):
                err_origin = "client"
                err_code = "MCP_CONNECTION_ERROR"
            else:
                err_origin = "server"
                err_code = "MCP_COMMUNICATION_ERROR"

            inv_log = MCPInvocationLog(
                invocation_id=inv_id,
                tool_name=tool_name,
                arguments=sanitized_args,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=duration_ms,
                status="failed",
                error_origin=err_origin,
                error_type=exc_type,
                error_message=exc_msg,
                traceback=tb_str,
            )
            log.error(
                "MCP Invocation FAILED [%s] tool=%s duration=%.2fms error_origin=%s type=%s: %s",
                inv_id,
                tool_name,
                duration_ms,
                err_origin,
                exc_type,
                exc_msg,
            )
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                data={
                    "status": "error",
                    "error_code": err_code,
                    "error": f"MCP tool '{tool_name}' communication failed ({exc_type}): {exc_msg}",
                    "error_origin": err_origin,
                    "invocation_id": inv_id,
                },
                raw_text=exc_msg,
                invocation_id=inv_id,
                duration_ms=duration_ms,
                error_origin=err_origin,
                original_exception_type=exc_type,
                original_exception_message=exc_msg,
                traceback=tb_str,
                invocation_log=inv_log,
            )

        # Parse valid MCP JSON-RPC response
        raw_text_parts = [
            block.text
            for block in (getattr(raw_res, "content", None) or [])
            if getattr(block, "type", None) == "text" and hasattr(block, "text")
        ]
        raw_text = "\n".join(raw_text_parts).strip()

        structured: dict[str, Any] = {}
        if isinstance(getattr(raw_res, "structuredContent", None), dict):
            sc = raw_res.structuredContent
            # FastMCP may wrap non-dict primitives under {"result": ...}
            if set(sc.keys()) == {"result"} and isinstance(sc["result"], dict):
                structured = dict(sc["result"])
            else:
                structured = dict(sc)
        elif raw_text:
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    structured = parsed
            except json.JSONDecodeError:
                pass

        protocol_error = bool(getattr(raw_res, "isError", False))
        domain_error = structured.get("status") == "error"
        is_error = protocol_error or domain_error

        # Categorize origin of error
        error_origin: str | None = None
        if is_error:
            err_code = structured.get("error_code", "")
            if err_code.startswith("SQL_") or err_code in {
                "SYNTAX_ERROR",
                "EXECUTION_ERROR",
                "QUERY_TIMEOUT",
                "DATABASE_NOT_FOUND",
                "TABLE_NOT_FOUND",
                "INSPECTION_ERROR",
                "SAMPLE_ERROR",
            }:
                error_origin = "sqlite"
            elif err_code.startswith("REPORT_") or err_code in {"SECURITY_ERROR", "VALIDATION_ERROR"}:
                error_origin = "report_generation"
            elif err_code in {"INVALID_ARGUMENT", "INVALID_TOOL_ARGUMENTS", "UNKNOWN_TOOL"}:
                error_origin = "tool_arguments"
            elif protocol_error:
                error_origin = "server"
            else:
                error_origin = "server"

        if protocol_error and not structured:
            structured = {
                "status": "error",
                "error_code": "MCP_PROTOCOL_TOOL_ERROR",
                "error": raw_text or f"Tool '{tool_name}' failed validation in MCP server",
                "error_origin": error_origin or "server",
            }

        response_meta = {
            "content_blocks": len(getattr(raw_res, "content", []) or []),
            "has_structured": bool(getattr(raw_res, "structuredContent", None)),
            "protocol_is_error": protocol_error,
        }

        inv_log = MCPInvocationLog(
            invocation_id=inv_id,
            tool_name=tool_name,
            arguments=sanitized_args,
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_ms=duration_ms,
            status="failed" if is_error else "success",
            error_origin=error_origin,
            error_type=structured.get("error_code") if is_error else None,
            error_message=structured.get("error") if is_error else None,
            metadata=response_meta,
        )

        if is_error:
            log.error(
                "MCP Invocation ERROR [%s] tool=%s duration=%.2fms error_origin=%s code=%s error=%s",
                inv_id,
                tool_name,
                duration_ms,
                error_origin,
                structured.get("error_code"),
                structured.get("error"),
            )
        else:
            log.info(
                "MCP Invocation OK [%s] tool=%s duration=%.2fms rows=%s",
                inv_id,
                tool_name,
                duration_ms,
                structured.get("record_count", len(structured.get("rows", []))),
            )

        return MCPToolCallResult(
            tool_name=tool_name,
            is_error=is_error,
            data=structured,
            raw_text=raw_text,
            invocation_id=inv_id,
            duration_ms=duration_ms,
            error_origin=error_origin,
            original_exception_type=structured.get("error_code") if is_error else None,
            original_exception_message=structured.get("error") if is_error else None,
            invocation_log=inv_log,
            metadata=response_meta,
        )
