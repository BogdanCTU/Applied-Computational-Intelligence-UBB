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
        """Lightweight conversion of text to HTML with paragraph, code, and newline formatting."""
        if not raw_text:
            return ""

        import html
        import re

        # Strip raw <think>...</think> tags so internal CoT is never displayed in message body
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
        escaped = html.escape(cleaned)

        # Basic markdown-like formatting for display
        # Bold **text**
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        # Inline code `code`
        escaped = re.sub(
            r"`([^`]+)`",
            r"<code style='background-color: #111116; color: #67e8f9; padding: 2px 4px; border-radius: 3px; font-family: monospace;'>\1</code>",
            escaped,
        )
        # Convert newlines to breaks
        escaped = escaped.replace("\n", "<br>")
        return escaped

