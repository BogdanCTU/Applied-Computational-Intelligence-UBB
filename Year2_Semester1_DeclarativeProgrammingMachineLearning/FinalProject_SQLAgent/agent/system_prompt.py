"""System prompt construction for the Local Report SQL Agent."""

from __future__ import annotations

from config.prompts import DEFAULT_SYSTEM_PROMPT, JSON_FALLBACK_INSTRUCTIONS
from config.settings import AppSettings


def build_system_prompt(
    settings: AppSettings,
    *,
    tool_mode: str = "native",
    schema_overview: str | None = None,
) -> str:
    """Build the complete system prompt for the agent.

    Parameters
    ----------
    settings:
        Application settings instance.
    tool_mode:
        "native" for Ollama native tool calling, "json" for structured JSON fallback.
    schema_overview:
        Optional pre-discovered database schema text to prime the agent context.
    """
    override = (settings.agent.system_prompt_override or "").strip()
    base_prompt = override if override else DEFAULT_SYSTEM_PROMPT

    sections: list[str] = [base_prompt.strip()]

    if schema_overview and schema_overview.strip():
        sections.append(
            f"\nCURRENT DATABASE SCHEMA SUMMARY:\n{schema_overview.strip()}"
        )

    if tool_mode == "json":
        sections.append(JSON_FALLBACK_INSTRUCTIONS.strip())

    return "\n\n".join(sections)

