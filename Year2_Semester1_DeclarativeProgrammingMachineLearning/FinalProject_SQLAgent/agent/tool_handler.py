"""Controlled MCP tool dispatcher and argument validator for the agent."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Mapping

from mcp_layer.client import MCPClientError, MCPStdioClient, MCPToolCallResult, MCPToolSpec

log = logging.getLogger(__name__)

PERMITTED_TOOLS: frozenset[str] = frozenset(
    {
        "inspect_database_schema",
        "get_table_sample",
        "prepare_sql_query",
        "execute_readonly_sql",
        "generate_pdf_report",
        "generate_csv_report",
    }
)


class ToolHandlerError(RuntimeError):
    """Base error for tool dispatcher."""


class UnknownToolError(ToolHandlerError):
    """Raised when an unapproved tool is requested."""


class ToolArgumentError(ToolHandlerError):
    """Raised when tool arguments fail pre-execution validation."""


class ToolExecutionTimeoutError(ToolHandlerError):
    """Raised when an MCP tool invocation exceeds its timeout."""


def _clean_schema_for_ollama(schema: Any) -> Any:
    """Normalize JSON schema for Ollama Go template compatibility.
    
    Flattens nullable anyOf, strips null defaults, and assigns concrete item types to bare arrays.
    """
    if not isinstance(schema, dict):
        return schema
    cleaned: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "default" and v is None:
            continue
        if k == "items" and v == {}:
            cleaned[k] = {"type": "string"}
            continue
        if k == "anyOf" and isinstance(v, list):
            non_null = [
                item for item in v if isinstance(item, dict) and item.get("type") != "null"
            ]
            if len(non_null) == 1:
                inner = _clean_schema_for_ollama(non_null[0])
                if isinstance(inner, dict):
                    cleaned.update(inner)
                continue
        if isinstance(v, dict):
            cleaned[k] = _clean_schema_for_ollama(v)
        elif isinstance(v, list):
            cleaned[k] = [_clean_schema_for_ollama(item) for item in v]
        else:
            cleaned[k] = v
    return cleaned


class ToolHandler:
    """Manages MCP tool discovery, validation, and safe execution."""

    def __init__(
        self,
        mcp_client: MCPStdioClient,
        *,
        default_tool_timeout_s: float = 30.0,
    ) -> None:
        self.mcp_client = mcp_client
        self.default_tool_timeout_s = float(default_tool_timeout_s)
        self._tool_specs: dict[str, MCPToolSpec] = {}

    @property
    def tool_specs(self) -> dict[str, MCPToolSpec]:
        return dict(self._tool_specs)

    async def initialize(self) -> list[MCPToolSpec]:
        """Discover tools from the MCP server and filter against the permitted whitelist."""
        if not self.mcp_client.is_connected:
            await self.mcp_client.connect()

        specs = await self.mcp_client.list_tools()
        self._tool_specs = {
            t.name: t for t in specs if t.name in PERMITTED_TOOLS
        }
        log.info(
            "ToolHandler initialized with %d permitted MCP tools: %s",
            len(self._tool_specs),
            list(self._tool_specs.keys()),
        )
        return list(self._tool_specs.values())

    def get_ollama_tools_schema(self) -> list[dict[str, Any]]:
        """Export tool specifications into the Ollama function calling schema format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": _clean_schema_for_ollama(t.input_schema),
                },
            }
            for t in self._tool_specs.values()
        ]

    def validate_tool_request(
        self, tool_name: str, arguments: Mapping[str, Any] | None
    ) -> tuple[bool, str | None, dict[str, Any]]:
        """Validate tool name and arguments against strict security rules.

        Returns (is_valid, error_message, sanitized_arguments).
        """
        if not tool_name or tool_name not in PERMITTED_TOOLS:
            return (
                False,
                f"Tool '{tool_name}' is not recognized or not permitted. "
                f"Permitted tools: {sorted(PERMITTED_TOOLS)}",
                {},
            )

        args = dict(arguments or {})

        # Security check: never allow arbitrary code/shell attributes
        forbidden_keys = {"__", "eval", "exec", "os.", "sys.", "subprocess"}
        for k in args.keys():
            if any(bad in k.lower() for bad in forbidden_keys):
                return False, f"Prohibited argument key '{k}' detected", {}

        # Domain-specific argument validation
        if tool_name == "inspect_database_schema":
            tbl = args.get("table_name")
            if tbl is not None and not isinstance(tbl, str):
                return False, "table_name must be a string", {}
            if tbl is None:
                args["table_name"] = ""
            else:
                args["table_name"] = tbl.strip()

        elif tool_name == "get_table_sample":
            tbl = args.get("table_name")
            if not tbl or not isinstance(tbl, str) or not tbl.strip():
                return False, "table_name is required and must be a non-empty string", {}
            if "num_records" in args:
                try:
                    args["num_records"] = int(args["num_records"])
                    if args["num_records"] < 1:
                        return False, "num_records must be >= 1", {}
                except (ValueError, TypeError):
                    return False, "num_records must be an integer", {}

        elif tool_name in {"prepare_sql_query", "execute_readonly_sql"}:
            sql = args.get("sql_query") or args.get("query") or args.get("sql")
            if not sql or not isinstance(sql, str) or not sql.strip():
                return False, "sql_query is required and must be a non-empty string", {}
            args["sql_query"] = sql.strip()
            if tool_name == "execute_readonly_sql" and "row_limit" in args and args["row_limit"] is not None:
                try:
                    args["row_limit"] = int(args["row_limit"])
                    if args["row_limit"] < 1:
                        return False, "row_limit must be >= 1", {}
                except (ValueError, TypeError):
                    return False, "row_limit must be an integer", {}

        elif tool_name == "generate_pdf_report":
            if "sql_query" not in args:
                if "query" in args:
                    args["sql_query"] = args.pop("query")
                elif "sql" in args:
                    args["sql_query"] = args.pop("sql")
            if "title" not in args and "name" in args:
                args["title"] = args.pop("name")
            for req in ("title", "description", "sql_query", "columns", "rows"):
                if req not in args or args[req] is None:
                    return False, f"Missing required argument '{req}' for generate_pdf_report", {}
            if not isinstance(args["columns"], (list, tuple)):
                return False, "columns must be a list of strings", {}
            if not isinstance(args["rows"], (list, tuple)):
                return False, "rows must be a list of table rows", {}

        elif tool_name == "generate_csv_report":
            if "title" not in args and "name" in args:
                args["title"] = args.pop("name")
            for req in ("title", "columns", "rows"):
                if req not in args or args[req] is None:
                    return False, f"Missing required argument '{req}' for generate_csv_report", {}
            if not isinstance(args["columns"], (list, tuple)):
                return False, "columns must be a list of strings", {}
            if not isinstance(args["rows"], (list, tuple)):
                return False, "rows must be a list of table rows", {}

        return True, None, args

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
        *,
        timeout_s: float | None = None,
    ) -> MCPToolCallResult:
        """Validate and dispatch tool call to the MCP server subprocess."""
        is_valid, err_msg, sanitized_args = self.validate_tool_request(
            tool_name, arguments
        )
        if not is_valid:
            log.warning("Tool validation rejected '%s': %s", tool_name, err_msg)
            code = "UNKNOWN_TOOL" if (not tool_name or tool_name not in PERMITTED_TOOLS) else "INVALID_TOOL_ARGUMENTS"
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                data={
                    "status": "error",
                    "error_code": code,
                    "error": err_msg or "Invalid tool arguments",
                },
                raw_text=err_msg or "Invalid tool arguments",
            )

        timeout = float(timeout_s or self.default_tool_timeout_s)
        try:
            return await asyncio.wait_for(
                self.mcp_client.call_tool(tool_name, sanitized_args),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            err = f"MCP tool '{tool_name}' timed out after {timeout:.1f}s"
            log.error(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                data={
                    "status": "error",
                    "error_code": "TOOL_TIMEOUT",
                    "error": err,
                },
                raw_text=err,
            )
        except MCPClientError as exc:
            err = f"MCP client communication error for '{tool_name}': {exc}"
            log.error(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                data={
                    "status": "error",
                    "error_code": "MCP_COMMUNICATION_ERROR",
                    "error": err,
                },
                raw_text=err,
            )
        except Exception as exc:  # noqa: BLE001
            err = f"Unexpected error executing MCP tool '{tool_name}': {exc}"
            log.exception(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                data={
                    "status": "error",
                    "error_code": "TOOL_EXECUTION_ERROR",
                    "error": err,
                },
                raw_text=err,
            )

