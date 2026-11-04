"""Visual message card widget for chat dialogue display."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MessageWidget(QFrame):
    """Custom message card representing user, assistant, or system chat turns."""

    def __init__(
        self,
        role: str,
        content: str,
        *,
        thinking: str | None = None,
        timestamp: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.role = role
        self.content = content
        self.thinking = thinking
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: Name/Badge and Timestamp
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        if self.role == "user":
            self.setObjectName("user_message_bubble")
            sender_lbl = QLabel("👤 You")
            sender_lbl.setStyleSheet("font-weight: 700; color: #93c5fd; font-size: 12px;")
        elif self.role == "assistant":
            self.setObjectName("assistant_message_bubble")
            sender_lbl = QLabel("🤖 Report Agent")
            sender_lbl.setStyleSheet("font-weight: 700; color: #60a5fa; font-size: 12px;")
        else:
            self.setObjectName("system_event_bubble")
            sender_lbl = QLabel("⚙️ System")
            sender_lbl.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 11px;")

        header_row.addWidget(sender_lbl)
        header_row.addStretch()

        time_lbl = QLabel(self.timestamp)
        time_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        header_row.addWidget(time_lbl)
        layout.addLayout(header_row)

        # Collapsible Thinking Block (for assistant messages with CoT reasoning)
        if self.thinking and self.thinking.strip():
            self.think_btn = QPushButton("💡 Show reasoning process")
            self.think_btn.setCheckable(True)
            self.think_btn.setChecked(False)
            self.think_btn.setFixedWidth(180)
            self.think_btn.setStyleSheet(
                "QPushButton { background-color: rgba(245, 158, 11, 0.15); "
                "color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); "
                "font-size: 11px; padding: 2px 8px; border-radius: 4px; } "
                "QPushButton:hover { background-color: rgba(245, 158, 11, 0.25); }"
            )

            self.think_box = QTextEdit()
            self.think_box.setReadOnly(True)
            self.think_box.setPlainText(self.thinking.strip())
            self.think_box.setVisible(False)
            self.think_box.setMaximumHeight(130)
            self.think_box.setStyleSheet(
                "background-color: #17171e; color: #fbbf24; font-size: 11px; "
                "border: 1px solid #3e3e52; border-radius: 4px; padding: 6px;"
            )

            self.think_btn.toggled.connect(self._toggle_thinking)
            layout.addWidget(self.think_btn)
            layout.addWidget(self.think_box)

        # Body text
        self.body_label = QLabel()
        self.body_label.setTextFormat(Qt.TextFormat.RichText)
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.body_label.setText(self._format_content(self.content))
        self.body_label.setStyleSheet("color: #f9fafb; font-size: 13px; line-height: 1.45;")
        layout.addWidget(self.body_label)

    def _toggle_thinking(self, checked: bool) -> None:
        self.think_box.setVisible(checked)
        self.think_btn.setText("💡 Hide reasoning process" if checked else "💡 Show reasoning process")

    def _format_content(self, raw_text: str) -> str:
        """Format message content to HTML according to role and security rules."""
        if not raw_text:
            return ""

        import html
        import re

        # Strip internal reasoning tags so CoT is never leaked into message body
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()

        # 1. User messages: strictly escape all HTML to prevent injection
        if self.role == "user":
            return html.escape(cleaned).replace("\n", "<br>")

        # 2. Assistant messages: support markdown formatting (code blocks, inline code, bold, italic)
        if self.role == "assistant":
            # Code blocks
            def _replace_code_block(match: re.Match[str]) -> str:
                code_content = html.escape(match.group(2).strip())
                return (
                    f"<pre style='background-color: #17171e; border: 1px solid #3e3e52; "
                    f"border-radius: 4px; padding: 8px; font-family: monospace; "
                    f"color: #67e8f9; overflow-x: auto;'><code>{code_content}</code></pre>"
                )

            cleaned = re.sub(r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)```", _replace_code_block, cleaned)

            # Inline code
            def _replace_inline_code(match: re.Match[str]) -> str:
                inline_content = html.escape(match.group(1))
                return (
                    f"<code style='background-color: #111116; color: #67e8f9; "
                    f"padding: 2px 4px; border-radius: 3px; font-family: monospace;'>{inline_content}</code>"
                )

            cleaned = re.sub(r"`([^`\n]+)`", _replace_inline_code, cleaned)

            # Markdown bold **text**
            cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
            # Markdown italic *text* (when not within a word or tag)
            cleaned = re.sub(r"(?<![a-zA-Z0-9])\*([^*]+?)\*(?![a-zA-Z0-9])", r"<i>\1</i>", cleaned)

        # 3. Sanitize HTML tags for system and assistant roles:
        # Allow safe tags (b, strong, i, em, code, br, span, p, ul, ol, li, pre) while escaping unsafe ones
        safe_tags = {"b", "strong", "i", "em", "code", "br", "span", "p", "ul", "ol", "li", "pre"}
        tag_re = re.compile(r"(</?[a-zA-Z0-9]+(?: [^>]*)?>)")
        parts = tag_re.split(cleaned)
        out: list[str] = []

        for part in parts:
            m = re.fullmatch(r"<(/)?([a-zA-Z0-9]+)([^>]*)>", part)
            if m:
                is_closing = m.group(1) == "/"
                tag_name = m.group(2).lower()
                attrs = m.group(3) or ""
                if tag_name in safe_tags:
                    if is_closing:
                        out.append(f"</{tag_name}>")
                        continue
                    lower_attrs = attrs.lower()
                    # Block scripts, events, and dangerous URI schemes in attributes
                    if any(bad in lower_attrs for bad in ("javascript:", "onerror", "onload", "onclick", "onmouse", "eval")):
                        out.append(html.escape(part))
                    elif tag_name == "br":
                        out.append("<br>")
                    else:
                        out.append(f"<{tag_name}{attrs}>")
                    continue
                # Unsafe or unrecognized tag: escape it
                out.append(html.escape(part))
            else:
                # Plain text: escape angle brackets and ampersands
                # If part already has converted newlines, preserve them
                text_part = html.escape(part).replace("\n", "<br>")
                out.append(text_part)

        return "".join(out)

