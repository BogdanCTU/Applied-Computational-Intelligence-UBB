"""Inline SQL preview card for chat and workflow streams."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SqlPreviewWidget(QFrame):
    """Inline card displaying SQL statements with status, syntax styling, and copy action."""

    def __init__(
        self,
        sql_query: str,
        *,
        title: str = "Proposed SQL Query",
        status: str = "Validated",
        explanation: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sql_query = sql_query.strip()
        self.title = title
        self.status = status
        self.explanation = explanation.strip()

        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("card_frame")
        self.setStyleSheet(
            "QFrame#card_frame { background-color: #1a1a24; border: 1px solid #3b82f640; border-radius: 8px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header bar
        header = QHBoxLayout()
        title_lbl = QLabel(f"📄 {self.title}")
        title_lbl.setStyleSheet("font-weight: 700; color: #93c5fd; font-size: 12px;")
        header.addWidget(title_lbl)

        status_lbl = QLabel(f"[{self.status}]")
        status_lbl.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px;")
        header.addWidget(status_lbl)

        header.addStretch()

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setFixedWidth(60)
        self.copy_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.copy_btn.clicked.connect(self._copy_sql)
        header.addWidget(self.copy_btn)

        layout.addLayout(header)

        # SQL Code block
        self.sql_box = QPlainTextEdit()
        self.sql_box.setObjectName("sql_editor")
        self.sql_box.setReadOnly(True)
        self.sql_box.setPlainText(self.sql_query)
        self.sql_box.setFont(QFont("JetBrains Mono, Menlo, Consolas, Courier New", 11))
        # Dynamically size height based on line count, capped at 160px
        lines = len(self.sql_query.splitlines())
        calc_height = max(50, min(160, lines * 20 + 20))
        self.sql_box.setFixedHeight(calc_height)
        layout.addWidget(self.sql_box)

        # Explanation if provided
        if self.explanation:
            exp_lbl = QLabel(self.explanation)
            exp_lbl.setWordWrap(True)
            exp_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; font-style: italic;")
            layout.addWidget(exp_lbl)

    def _copy_sql(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.sql_query)
            self.copy_btn.setText("Copied!")
            self.copy_btn.setEnabled(False)

