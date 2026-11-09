"""Controlled MCP tool dispatcher and argument validator for the agent."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from mcp_layer.client import MCPClientError, MCPStdioClient, MCPToolCallResult, MCPToolSpec

log = logging.getLogger(__name__)

EXPECTED_MCP_TOOLS: tuple[str, ...] = (
    "inspect_database_schema",
    "get_table_sample",
    "prepare_sql_query",
    "execute_readonly_sql",
    "generate_pdf_report",
    "generate_csv_report",
)

PERMITTED_TOOLS: frozenset[str] = frozenset(EXPECTED_MCP_TOOLS)


class ToolHandlerError(RuntimeError):
    """Base error for tool dispatcher."""


class ToolDiscoveryError(ToolHandlerError):
    """Raised when MCP tool discovery fails or expected tools are missing."""


class UnknownToolError(ToolHandlerError):
    """Raised when an unapproved tool is requested."""


class ToolArgumentError(ToolHandlerError):
    """Raised when tool arguments fail pre-execution validation."""


class ToolExecutionTimeoutError(ToolHandlerError):
    """Raised when an MCP tool invocation exceeds its timeout."""


def _clean_schema_for_ollama(
    schema: Any,
    *,
    tool_name: str | None = None,
    _is_property_map: bool = False,
) -> Any:
    """Normalize MCP JSON Schema into the exact Ollama function-tool schema format.

    - Preserves parameter names, descriptions, types, required fields, and nested properties.
    - Flattens nullable ``anyOf`` unions into concrete parameter types.
    - Strips ``default: None`` and Pydantic ``title`` / ``additionalProperties`` metadata.
    - Assigns concrete types to untyped ``Any`` properties and bare ``items: {}`` arrays.
    - Ensures ``inspect_database_schema`` marks ``table_name`` required (``'ALL'`` or a table name)
      so Qwen3.5's XML parser in Ollama never receives an empty ``<parameter>`` tag.
    """
    if not isinstance(schema, dict):
        return schema

    if _is_property_map:
        cleaned_props: dict[str, Any] = {}
        for prop_name, prop_schema in schema.items():
            c_prop = _clean_schema_for_ollama(prop_schema, _is_property_map=False)
            if isinstance(c_prop, dict):
                c_prop.pop("title", None)
                if "type" not in c_prop and "anyOf" not in c_prop:
                    c_prop["type"] = "object"
                if prop_name not in ("table_name", "num_records", "row_limit"):
                    c_prop.pop("default", None)
            cleaned_props[prop_name] = c_prop
        return cleaned_props

    cleaned: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "default" and v is None:
            continue
        if k in ("title", "additionalProperties"):
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
        if k == "properties" and isinstance(v, dict):
            cleaned[k] = _clean_schema_for_ollama(v, _is_property_map=True)
        elif isinstance(v, dict):
            cleaned[k] = _clean_schema_for_ollama(v)
        elif isinstance(v, list):
            cleaned[k] = [_clean_schema_for_ollama(item) for item in v]
        else:
            cleaned[k] = v

    if cleaned.get("type") == "object" and "properties" not in cleaned:
        cleaned["properties"] = {}

    if tool_name == "inspect_database_schema":
        props = cleaned.setdefault("properties", {})
        tbl_prop = props.setdefault("table_name", {"type": "string"})
        if isinstance(tbl_prop, dict):
            tbl_prop["type"] = "string"
            tbl_prop["description"] = (
                "Pass 'ALL' to inspect all database tables, columns, relationships, "
                "and date ranges, or pass a specific table name."
            )
            tbl_prop.pop("default", None)
        cleaned["required"] = ["table_name"]

    return cleaned


@dataclass(frozen=True)
class DiscoveredTool:
    """Structured runtime representation of a single discovered MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    required_parameters: tuple[str, ...]
    ollama_schema: dict[str, Any]

    def to_mcp_spec(self) -> MCPToolSpec:
        return MCPToolSpec(
            name=self.name,
            description=self.description,
            input_schema=dict(self.input_schema),
        )


@dataclass
class MCPToolRegistry:
    """Authoritative runtime registry of MCP tools discovered from the MCP server."""

    tools: dict[str, DiscoveredTool] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return bool(self.tools) and all(name in self.tools for name in EXPECTED_MCP_TOOLS)

    @property
    def missing_tools(self) -> list[str]:
        return [name for name in EXPECTED_MCP_TOOLS if name not in self.tools]

    @property
    def tool_names(self) -> list[str]:
        return list(self.tools.keys())

    def get_tool(self, name: str) -> DiscoveredTool | None:
        return self.tools.get(name)

    def get_tool_specs(self) -> list[MCPToolSpec]:
        return [t.to_mcp_spec() for t in self.tools.values()]

    def get_ollama_tools(self) -> list[dict[str, Any]]:
        return [dict(t.ollama_schema) for t in self.tools.values()]

    def format_prompt_summary(self) -> str:
        """Render a concise summary of discovered MCP tools for the system prompt."""
        if not self.tools:
            return ""
        lines: list[str] = ["DISCOVERED MCP TOOLS (ACTIVE RUNTIME REGISTRY):"]
        for name in EXPECTED_MCP_TOOLS:
            tool = self.tools.get(name)
            if tool is None:
                continue
            props = (
                tool.ollama_schema.get("function", {})
                .get("parameters", {})
                .get("properties", {})
            )
            req = set(tool.required_parameters)
            param_parts: list[str] = []
            for p_name in props.keys():
                if p_name in req:
                    param_parts.append(f"{p_name} (required)")
                else:
                    param_parts.append(f"{p_name} (optional)")
            sig = ", ".join(param_parts[:6])
            if len(param_parts) > 6:
                sig += ", ..."
            lines.append(f"- {tool.name}({sig}): {tool.description}")
        return "\n".join(lines)


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
        self._registry: MCPToolRegistry = MCPToolRegistry()

    @property
    def tool_specs(self) -> dict[str, MCPToolSpec]:
        return dict(self._tool_specs)

    @property
    def registry(self) -> MCPToolRegistry:
        return self._registry

    async def initialize(self) -> list[MCPToolSpec]:
        """Discover tools from the MCP server and validate all 6 expected MCP tools."""
        if not self.mcp_client.is_connected:
            await self.mcp_client.connect()

        specs = await self.mcp_client.list_tools()
        if not specs:
            raise ToolDiscoveryError(
                "MCP tool discovery returned 0 tools from the MCP server subprocess."
            )

        spec_map: dict[str, MCPToolSpec] = {
            t.name: t for t in specs if t.name in PERMITTED_TOOLS
        }
        missing = [name for name in EXPECTED_MCP_TOOLS if name not in spec_map]
        if missing:
            raise ToolDiscoveryError(
                f"MCP tool discovery incomplete: missing expected tools {missing}. "
                f"Discovered tools: {sorted(spec_map.keys())}"
            )

        ordered_specs: dict[str, MCPToolSpec] = {}
        discovered_tools: dict[str, DiscoveredTool] = {}
        for name in EXPECTED_MCP_TOOLS:
            spec = spec_map[name]
            if not spec.description or not spec.description.strip():
                raise ToolDiscoveryError(
                    f"MCP tool '{name}' has an empty description."
                )
            if not isinstance(spec.input_schema, dict):
                raise ToolDiscoveryError(
                    f"MCP tool '{name}' has an invalid input_schema: {type(spec.input_schema).__name__}"
                )

            cleaned_params = _clean_schema_for_ollama(spec.input_schema, tool_name=name)
            if not isinstance(cleaned_params, dict):
                cleaned_params = {"type": "object", "properties": {}}
            cleaned_params.setdefault("type", "object")
            cleaned_params.setdefault("properties", {})

            req_list = cleaned_params.get("required") or spec.input_schema.get("required") or []
            req_tuple = tuple(str(r) for r in req_list if isinstance(r, str))

            ollama_tool = {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": cleaned_params,
                },
            }
            ordered_specs[name] = spec
            discovered_tools[name] = DiscoveredTool(
                name=spec.name,
                description=spec.description,
                input_schema=dict(spec.input_schema),
                required_parameters=req_tuple,
                ollama_schema=ollama_tool,
            )

        self._tool_specs = ordered_specs
        self._registry = MCPToolRegistry(tools=discovered_tools)
        log.info(
            "ToolHandler initialized with %d verified MCP tools: %s",
            len(self._tool_specs),
            list(self._tool_specs.keys()),
        )
        return list(self._tool_specs.values())

    def get_ollama_tools_schema(self) -> list[dict[str, Any]]:
        """Export discovered tool specifications into the Ollama function calling schema format."""
        if self._registry.tools:
            return self._registry.get_ollama_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": _clean_schema_for_ollama(t.input_schema, tool_name=t.name),
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
                cleaned_tbl = tbl.strip()
                if cleaned_tbl.upper() in {"ALL", "*", "ALL_TABLES"}:
                    cleaned_tbl = ""
                args["table_name"] = cleaned_tbl

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

            if not args.get("title") or not str(args.get("title")).strip():
                args["title"] = "Analytical Report"

            if "columns" not in args or "rows" not in args:
                return False, "Missing required argument: columns and rows must be provided", {}

            args.setdefault("description", "")
            args.setdefault("sql_query", "")

            if not isinstance(args["columns"], (list, tuple)):
                return False, "columns must be a list of strings", {}
            if not isinstance(args["rows"], (list, tuple)):
                return False, "rows must be a list of table rows", {}

        elif tool_name == "generate_csv_report":
            if "title" not in args and "name" in args:
                args["title"] = args.pop("name")
            if not args.get("title") or not str(args.get("title")).strip():
                args["title"] = "Data Export"

            if "columns" not in args or "rows" not in args:
                return False, "Missing required argument: columns and rows must be provided", {}

            args.setdefault("description", "")
            args.setdefault("sql_query", "")

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
                error_origin="tool_arguments",
                original_exception_type="ToolArgumentError",
                original_exception_message=err_msg or "Invalid tool arguments",
                data={
                    "status": "error",
                    "error_code": code,
                    "error": err_msg or "Invalid tool arguments",
                    "error_origin": "tool_arguments",
                },
                raw_text=err_msg or "Invalid tool arguments",
            )

        timeout = float(timeout_s or self.default_tool_timeout_s)
        try:
            res = await asyncio.wait_for(
                self.mcp_client.call_tool(tool_name, sanitized_args),
                timeout=timeout,
            )
            if isinstance(res, dict):
                is_err = res.get("status") == "error"
                return MCPToolCallResult(
                    tool_name=tool_name,
                    is_error=is_err,
                    error_origin=res.get("error_origin", "server" if is_err else None),
                    data=res,
                    raw_text=str(res),
                )
            return res
        except asyncio.TimeoutError:
            err = f"MCP tool '{tool_name}' timed out after {timeout:.1f}s"
            log.error(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                error_origin="client",
                original_exception_type="TimeoutError",
                original_exception_message=err,
                data={
                    "status": "error",
                    "error_code": "TOOL_TIMEOUT",
                    "error": err,
                    "error_origin": "client",
                },
                raw_text=err,
            )
        except MCPClientError as exc:
            err = f"MCP client communication error for '{tool_name}': {exc}"
            log.error(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                error_origin="client",
                original_exception_type=exc.__class__.__name__,
                original_exception_message=str(exc),
                data={
                    "status": "error",
                    "error_code": "MCP_COMMUNICATION_ERROR",
                    "error": err,
                    "error_origin": "client",
                },
                raw_text=err,
            )
        except Exception as exc:  # noqa: BLE001
            err = f"Unexpected error executing MCP tool '{tool_name}': {exc}"
            log.exception(err)
            return MCPToolCallResult(
                tool_name=tool_name,
                is_error=True,
                error_origin="server",
                original_exception_type=exc.__class__.__name__,
                original_exception_message=str(exc),
                data={
                    "status": "error",
                    "error_code": "TOOL_EXECUTION_ERROR",
                    "error": err,
                    "error_origin": "server",
                },
                raw_text=err,
            )

