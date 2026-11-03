"""Official Python MCP stdio client managing the local MCP server subprocess.

Used by both integration tests and the agent orchestrator so all database and
reporting operations travel over genuine MCP JSON-RPC stdio transport.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Mapping

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from config.paths import app_root, is_frozen
from config.settings import AppSettings

log = logging.getLogger(__name__)


class MCPClientError(RuntimeError):
    """Raised when the MCP client is not connected or transport communication fails."""


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPToolCallResult:
    tool_name: str
    is_error: bool
    data: dict[str, Any]
    raw_text: str


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
        cwd=str(app_root()),
    )


class MCPStdioClient:
    """Async context-managed MCP stdio client speaking to ``mcp_layer.server``."""

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

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> "MCPStdioClient":
        if self._session is not None:
            return self

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
        log.info("Connected to local MCP stdio server subprocess")
        return self

    async def close(self) -> None:
        stack = self._exit_stack
        self._session = None
        self._exit_stack = None
        if stack is not None:
            await stack.aclose()
            log.info("Closed MCP stdio server subprocess")

    async def __aenter__(self) -> "MCPStdioClient":
        return await self.connect()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise MCPClientError("MCPStdioClient is not connected")
        return self._session

    async def list_tools(self) -> list[MCPToolSpec]:
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
    ) -> MCPToolCallResult:
        session = self._require_session()
        raw_res = await session.call_tool(tool_name, dict(arguments or {}))

        raw_text_parts = [
            block.text
            for block in (raw_res.content or [])
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
        if protocol_error and not structured:
            structured = {
                "status": "error",
                "error_code": "MCP_PROTOCOL_TOOL_ERROR",
                "error": raw_text or f"Tool '{tool_name}' failed validation",
            }

        return MCPToolCallResult(
            tool_name=tool_name,
            is_error=protocol_error or domain_error,
            data=structured,
            raw_text=raw_text,
        )

