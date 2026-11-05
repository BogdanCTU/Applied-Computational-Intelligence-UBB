"""Conversation state management for the Local Report SQL Agent."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Sequence


@dataclass
class ConversationMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # tool name for role="tool"
    thinking: str | None = None  # model reasoning chain (if available)
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_ollama_dict(self) -> dict[str, Any]:
        """Convert to the message format expected by Ollama /api/chat."""
        d: dict[str, Any] = {
            "role": self.role,
            "content": self.content or "",
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.name:
            d["name"] = self.name
        return d


class ConversationManager:
    """Maintains conversation history with bounded context and tool-pair preservation."""

    def __init__(self, max_history_messages: int = 30) -> None:
        self.max_history_messages = max(4, max_history_messages)
        self.messages: list[ConversationMessage] = []

    def clear(self) -> None:
        """Reset conversation history completely."""
        self.messages.clear()

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        self.messages.append(message)
        self._enforce_limit()
        return message

    def add_user_message(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> ConversationMessage:
        msg = ConversationMessage(
            role="user",
            content=content,
            metadata=metadata or {},
        )
        return self.add_message(msg)

    def add_assistant_message(
        self,
        content: str,
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        thinking: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            thinking=thinking,
            metadata=metadata or {},
        )
        return self.add_message(msg)

    def add_tool_message(
        self,
        tool_name: str,
        content: str | dict[str, Any],
        *,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        if isinstance(content, dict):
            text_content = json.dumps(content, ensure_ascii=False)
        else:
            text_content = str(content)

        msg = ConversationMessage(
            role="tool",
            content=text_content,
            name=tool_name,
            tool_call_id=tool_call_id,
            metadata=metadata or {},
        )
        return self.add_message(msg)

    def get_messages_for_llm(
        self, system_prompt: str | None = None
    ) -> list[dict[str, Any]]:
        """Return formatted messages for the Ollama API, prepending system_prompt if given."""
        llm_messages: list[dict[str, Any]] = []
        if system_prompt and system_prompt.strip():
            llm_messages.append({"role": "system", "content": system_prompt.strip()})

        for msg in self.messages:
            llm_messages.append(msg.to_ollama_dict())
        return llm_messages

    def _enforce_limit(self) -> None:
        """Trim oldest messages when exceeding max_history_messages while keeping tool pairs intact."""
        if len(self.messages) <= self.max_history_messages:
            return

        excess = len(self.messages) - self.max_history_messages
        cut_idx = excess

        # Avoid splitting an assistant tool_call and its subsequent tool response messages
        while cut_idx < len(self.messages) and self.messages[cut_idx].role == "tool":
            cut_idx += 1

        self.messages = self.messages[cut_idx:]


def compact_tool_result_for_llm(
    tool_name: str,
    raw_data: dict[str, Any],
    *,
    preview_rows_limit: int = 15,
) -> dict[str, Any]:
    """Produce a compact copy of query results for LLM context to prevent window overflow.

    The complete uncompacted data remains preserved in the orchestrator for reporting.
    """
    if tool_name != "execute_readonly_sql":
        return raw_data

    if raw_data.get("status") != "ok":
        return raw_data

    rows = raw_data.get("rows", [])
    if len(rows) <= preview_rows_limit:
        return raw_data

    compact = dict(raw_data)
    compact["rows"] = rows[:preview_rows_limit]
    compact["rows_preview_notice"] = (
        f"Showing preview of first {preview_rows_limit} rows out of {len(rows)} total returned rows. "
        "All records are retained in full for report generation."
    )
    return compact

