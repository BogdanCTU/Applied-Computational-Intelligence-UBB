"""MCP layer: official Python MCP stdio server, client, and tool definitions.

Server symbols are loaded lazily via ``__getattr__`` so running
``python -m mcp_layer.server`` never triggers a ``runpy`` pre-import warning.
"""

from __future__ import annotations

from typing import Any

from .client import (
    MCPClientError,
    MCPStdioClient,
    MCPToolCallResult,
    MCPToolSpec,
    build_stdio_server_params,
)

__all__ = [
    "MCPClientError",
    "MCPStdioClient",
    "MCPToolCallResult",
    "MCPToolSpec",
    "SERVER_NAME",
    "build_stdio_server_params",
    "create_mcp_server",
    "run_stdio_server",
]


def __getattr__(name: str) -> Any:
    if name in {"SERVER_NAME", "create_mcp_server", "run_stdio_server"}:
        from . import server as _server

        return getattr(_server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
