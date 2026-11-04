"""Conversational chat view with multi-turn message history, live status, and input controls."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.widgets.message_widget import MessageWidget
from app.widgets.sql_preview_widget import SqlPreviewWidget

log = logging.getLogger(__name__)


class ChatInputEdit(QPlainTextEdit):
    """Multiline input editor where Enter sends and Shift+Enter inserts a newline."""

    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
                event.accept()
        else:
            super().keyPressEvent(event)


class ChatView(QWidget):
    """Lateral conversational panel interfacing with the Agent Orchestrator."""

    message_submitted = Signal(str)
    cancellation_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_processing = False
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Header with clear button
        # -------------------------------------------------------------
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)

        chat_title = QLabel("💬 AI Report Assistant")
        chat_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #f3f4f6;")
        header.addWidget(chat_title)

        header.addStretch()

        self.btn_clear = QPushButton("Clear Chat")
        self.btn_clear.setToolTip("Reset conversation history")
        self.btn_clear.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        header.addWidget(self.btn_clear)

        main_layout.addLayout(header)

        # -------------------------------------------------------------
        # 2. Scrollable Message History Area
        # -------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #3e3e52; border-radius: 6px; }")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # -------------------------------------------------------------
        # 3. Live Progress & Status Banner
        # -------------------------------------------------------------
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("card_frame")
        self.progress_frame.setStyleSheet(
            "QFrame#card_frame { background-color: #1f2937; border: 1px solid #374151; "
            "border-radius: 6px; padding: 4px; }"
        )
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setContentsMargins(8, 6, 8, 6)
        prog_layout.setSpacing(4)

        prog_header = QHBoxLayout()
        self.status_icon = QLabel("⏳")
        prog_header.addWidget(self.status_icon)

        self.status_label = QLabel("Analyzing request...")
        self.status_label.setStyleSheet("font-weight: 600; color: #60a5fa; font-size: 12px;")
        prog_header.addWidget(self.status_label, stretch=1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("danger_button")
        self.btn_cancel.setToolTip("Cancel running agent workflow")
        self.btn_cancel.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        prog_header.addWidget(self.btn_cancel)

        prog_layout.addLayout(prog_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate pulsing progress
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #374151; border: none; border-radius: 2px; } "
            "QProgressBar::chunk { background-color: #3b82f6; border-radius: 2px; }"
        )
        prog_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.progress_frame)
        self.progress_frame.setVisible(False)

        # -------------------------------------------------------------
        # 4. Message Input & Send Button
        # -------------------------------------------------------------
        input_frame = QFrame()
        input_frame.setObjectName("card_frame")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(6)

        self.input_edit = ChatInputEdit()
        self.input_edit.setPlaceholderText("Ask a question or request a report (e.g., 'Revenue by country as PDF')...")
        self.input_edit.setMaximumHeight(85)
        self.input_edit.send_requested.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_edit)

        btn_row = QHBoxLayout()
        hint_lbl = QLabel("Enter to send • Shift+Enter for newline")
        hint_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        btn_row.addWidget(hint_lbl)

        btn_row.addStretch()

        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("primary_button")
        self.btn_send.setProperty("primary", True)
        self.btn_send.setFixedWidth(80)
        self.btn_send.clicked.connect(self._on_send_clicked)
        btn_row.addWidget(self.btn_send)

        input_layout.addLayout(btn_row)
        main_layout.addWidget(input_frame)

        # Initial Welcome Message
        self.add_system_message(
            "👋 Welcome to the <b>Local Report SQL Agent</b>.<br>"
            "Ask for sales summaries, product comparisons, or customer reports in natural language.<br>"
            "Reports are generated in <b>PDF format by default</b> (or CSV upon explicit request)."
        )

    # -----------------------------------------------------------------
    # Public Message Appending API
    # -----------------------------------------------------------------

    def add_user_message(self, text: str) -> MessageWidget:
        widget = MessageWidget(role="user", content=text)
        self._append_widget(widget)
        return widget

    def add_assistant_message(
        self, text: str, thinking: str | None = None
    ) -> MessageWidget:
        widget = MessageWidget(role="assistant", content=text, thinking=thinking)
        self._append_widget(widget)
        return widget

    def add_system_message(self, text: str) -> MessageWidget:
        widget = MessageWidget(role="system", content=text)
        self._append_widget(widget)
        return widget

    def add_sql_preview(
        self,
        sql_query: str,
        *,
        title: str = "Proposed SQL Query",
        status: str = "Validated",
        explanation: str = "",
    ) -> SqlPreviewWidget:
        widget = SqlPreviewWidget(
            sql_query=sql_query,
            title=title,
            status=status,
            explanation=explanation,
        )
        self._append_widget(widget)
        return widget

    def _append_widget(self, widget: QWidget) -> None:
        count = self.messages_layout.count()
        # Insert before the trailing stretch item
        self.messages_layout.insertWidget(max(0, count - 1), widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    # -----------------------------------------------------------------
    # Processing and State Management
    # -----------------------------------------------------------------

    def set_processing_state(
        self, is_processing: bool, status_text: str = "Processing..."
    ) -> None:
        self.is_processing = is_processing
        self.progress_frame.setVisible(is_processing)
        self.status_label.setText(status_text)
        self.btn_send.setEnabled(not is_processing)
        self.input_edit.setEnabled(not is_processing)
        self.btn_clear.setEnabled(not is_processing)
        if not is_processing:
            self.input_edit.setFocus()

    def update_status_message(self, text: str) -> None:
        if self.is_processing:
            self.status_label.setText(text)

    def clear_chat(self) -> None:
        """Clear all messages from the conversation view."""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    # -----------------------------------------------------------------
    # Internal Slots
    # -----------------------------------------------------------------

    def _on_send_clicked(self) -> None:
        if self.is_processing:
            return
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.input_edit.clear()
        self.add_user_message(text)
        self.message_submitted.emit(text)

    def _on_cancel_clicked(self) -> None:
        self.update_status_message("Cancelling agent operations...")
        self.cancellation_requested.emit()

    def _on_clear_clicked(self) -> None:
        self.clear_chat()
        self.clear_requested.emit()
        self.add_system_message("Conversation history cleared.")

