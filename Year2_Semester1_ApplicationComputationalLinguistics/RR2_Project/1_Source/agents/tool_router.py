"""Optional LLM JSON tool-routing parity module reproducing upstream `create_tool_use_agent`."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, render_text_description


@dataclass
class ToolRouterStats:
    """Telemetry recorded by `LLMJsonToolRouter` for overhead and reliability analysis."""

    total_calls: int = 0
    total_duration_ms: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    parse_or_schema_errors: int = 0
    fallback_invocations: int = 0
    error_messages: List[str] = field(default_factory=list)


class LLMJsonToolRouter:
    """
    Reproduces upstream Agent-OM's `ChatPromptTemplate | llm | JsonOutputParser() | tool_chain`
    routing pattern (`om_ontology_to_csv.py:432-445`, `om_database_matching.py:486-500`).

    When `strict=True`, requires exact `{"name": ..., "arguments": {...}}` output matching
    upstream's `itemgetter("arguments") | tool_map[model_output["name"]]`.
    When `strict=False` (default for local small-LLM resilience), normalizes common key aliases
    (`"tool"` / `"function"`) and optionally falls back to `expected_tool_name` while recording
    the schema deviation in `stats`.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        strict: bool = False,
        allow_fallback: bool = True,
    ):
        self.llm = llm
        self.tools = list(tools)
        self.tool_map: Dict[str, BaseTool] = {t.name: t for t in self.tools}
        self.strict = strict
        self.allow_fallback = allow_fallback
        self.stats = ToolRouterStats()

        rendered_tools = render_text_description(self.tools)
        # Escape curly braces inside rendered tool signatures for ChatPromptTemplate
        escaped_rendered = rendered_tools.replace("{", "{{").replace("}", "}}")
        system_prompt = (
            "You are an assistant who has access to the following set of tools.\n"
            "                    Here are the names and descriptions of each tool:\n"
            f"                    {escaped_rendered}\n"
            "                    Given the user input, return the name of the tool to use and the arguments passed to the tool.\n"
            "                    Return your response as a JSON blob with the key 'name' and 'arguments'.\n"
            "                    The value associated with the key 'arguments' should be a dictionary of parameters.\n"
            "                    "
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", "{input}")]
        )
        self.parser = JsonOutputParser()

    def invoke(
        self,
        user_input: str,
        expected_tool_name: Optional[str] = None,
        fallback_args: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Route `user_input` through the LLM JSON parser and invoke the selected tool."""
        messages = self.prompt.format_messages(input=user_input)
        t0 = time.perf_counter()
        raw_msg = self.llm.invoke(messages)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.stats.total_calls += 1
        self.stats.total_duration_ms += elapsed_ms
        resp_meta = getattr(raw_msg, "response_metadata", {}) or {}
        self.stats.total_prompt_tokens += int(resp_meta.get("prompt_eval_count", 0) or 0)
        self.stats.total_completion_tokens += int(resp_meta.get("eval_count", 0) or 0)

        try:
            parsed = self.parser.invoke(raw_msg)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object from router, got {type(parsed).__name__}")

            if self.strict:
                tool_name = parsed["name"]
                tool_args = parsed["arguments"]
            else:
                tool_name = parsed.get("name") or parsed.get("tool") or parsed.get("function")
                tool_args = parsed.get("arguments", parsed.get("args", {}))
                if tool_args is None:
                    tool_args = {}

            if tool_name not in self.tool_map:
                raise KeyError(f"Unknown routed tool '{tool_name}'")
            if not isinstance(tool_args, dict):
                raise TypeError(f"Tool arguments must be dict, got {type(tool_args).__name__}")

            return self.tool_map[tool_name].invoke(tool_args)
        except Exception as exc:
            self.stats.parse_or_schema_errors += 1
            self.stats.error_messages.append(f"{type(exc).__name__}: {exc}")
            if self.strict or not self.allow_fallback or expected_tool_name not in self.tool_map:
                raise
            self.stats.fallback_invocations += 1
            return self.tool_map[expected_tool_name].invoke(fallback_args or {})

