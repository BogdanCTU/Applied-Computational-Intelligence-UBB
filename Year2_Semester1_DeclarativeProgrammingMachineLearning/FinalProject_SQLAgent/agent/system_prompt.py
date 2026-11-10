"""System prompt construction for the Local Report SQL Agent."""

from __future__ import annotations

from typing import Any

from config.prompts import DEFAULT_SYSTEM_PROMPT, JSON_FALLBACK_INSTRUCTIONS
from config.settings import AppSettings, load_settings


def _format_discovered_tools_section(discovered_tools: Any) -> str:
    """Format discovered MCP tools or registry into a concise prompt block."""
    if discovered_tools is None:
        return ""
    if hasattr(discovered_tools, "format_prompt_summary"):
        return str(discovered_tools.format_prompt_summary()).strip()
    if isinstance(discovered_tools, (list, tuple)):
        lines: list[str] = ["DISCOVERED MCP TOOLS (ACTIVE RUNTIME REGISTRY):"]
        for item in discovered_tools:
            if hasattr(item, "name") and hasattr(item, "description"):
                lines.append(f"- {item.name}: {item.description}")
            elif isinstance(item, dict):
                fn = item.get("function", item)
                name = fn.get("name", "")
                desc = fn.get("description", "")
                if name:
                    lines.append(f"- {name}: {desc}")
        return "\n".join(lines) if len(lines) > 1 else ""
    return ""


def build_system_prompt(
    settings: AppSettings | None = None,
    *,
    tool_mode: str = "native",
    schema_overview: str | None = None,
    discovered_tools: Any | None = None,
    reporting_period: dict[str, str] | None = None,
) -> str:
    """Build the complete capability-aware system prompt for the agent.

    Parameters
    ----------
    settings:
        Application settings instance (defaults to global ``get_settings()``).
    tool_mode:
        "native" for Ollama native tool calling, "json" for structured JSON fallback.
    schema_overview:
        Optional pre-discovered database schema text to prime the agent context.
    discovered_tools:
        Optional ``MCPToolRegistry``, list of ``MCPToolSpec``, or Ollama tool dicts.
    reporting_period:
        Optional resolved reporting period metadata (e.g. ``start_date``, ``end_date_exclusive``).
    """
    active_settings = settings or load_settings()
    override = (active_settings.agent.system_prompt_override or "").strip()
    base_prompt = override if override else DEFAULT_SYSTEM_PROMPT

    sections: list[str] = [base_prompt.strip()]

    tools_block = _format_discovered_tools_section(discovered_tools)
    if tools_block:
        sections.append(tools_block)

    if reporting_period and isinstance(reporting_period, dict):
        label = reporting_period.get("period_label", "")
        start_d = reporting_period.get("start_date", "")
        end_d = reporting_period.get("end_date_exclusive", "")
        if start_d and end_d:
            sections.append(
                f"ACTIVE REPORTING PERIOD ({label}): "
                f"Filter using column 'o.order_date' on table 'orders' (e.g. o.order_date >= '{start_d}' AND o.order_date < '{end_d}'). "
                f"Note: table 'orders' has NO column named 'start_date'."
            )

    if schema_overview and schema_overview.strip():
        sections.append(
            f"CURRENT DATABASE SCHEMA SUMMARY:\n{schema_overview.strip()}"
        )

    if tool_mode == "json":
        sections.append(JSON_FALLBACK_INSTRUCTIONS.strip())

    return "\n\n".join(sections)

