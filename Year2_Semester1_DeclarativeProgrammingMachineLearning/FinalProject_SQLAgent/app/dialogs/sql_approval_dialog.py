"""Modal approval dialog enforcing human-in-the-loop review of proposed SQL queries."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


class SqlApprovalDialog(QDialog):
    """Dedicated modal dialog requiring explicit user approval before SQL query execution."""

    def __init__(
        self,
        sql_query: str,
        explanation: str = "",
        *,
        database_name: str = "ecommerce.db",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sql_query = sql_query.strip()
        self.explanation = explanation.strip()
        self.database_name = database_name
        self.is_approved: bool = False

        self.setWindowTitle("SQL Execution Approval")
        self.setModal(True)
        self.setMinimumSize(620, 480)
        self.resize(700, 540)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header Banner
        header = QLabel("⚠️ SQL Query Approval Required")
        header.setStyleSheet("font-size: 16px; font-weight: 700; color: #f59e0b;")
        layout.addWidget(header)

        desc = QLabel(
            "The AI agent has prepared the following read-only SQL query and requests permission "
            f"to execute it against the local database: <b>{self.database_name}</b>.<br>"
            "Please review the query statement and explanation before approving."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #d1d5db; line-height: 1.4;")
        layout.addWidget(desc)

        # 2. SQL Query Display with Copy Button
        sql_label_row = QHBoxLayout()
        sql_title = QLabel("Proposed SQL Statement:")
        sql_title.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 12px;")
        sql_label_row.addWidget(sql_title)

        sql_label_row.addStretch()

        self.copy_btn = QPushButton("Copy SQL")
        self.copy_btn.setToolTip("Copy SQL query to clipboard")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.clicked.connect(self._copy_sql_to_clipboard)
        sql_label_row.addWidget(self.copy_btn)

        layout.addLayout(sql_label_row)

        self.sql_edit = QPlainTextEdit()
        self.sql_edit.setObjectName("sql_editor")
        self.sql_edit.setReadOnly(True)
        self.sql_edit.setPlainText(self.sql_query)
        self.sql_edit.setFont(QFont("JetBrains Mono, Menlo, Consolas, Courier New", 12))
        layout.addWidget(self.sql_edit, stretch=2)

        # 3. Agent Explanation
        if self.explanation:
            exp_label = QLabel("Agent Explanation / Purpose:")
            exp_label.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 12px;")
            layout.addWidget(exp_label)

            self.exp_box = QPlainTextEdit()
            self.exp_box.setReadOnly(True)
            self.exp_box.setPlainText(self.explanation)
            self.exp_box.setMaximumHeight(85)
            self.exp_box.setStyleSheet(
                "background-color: #22222b; color: #e5e7eb; border: 1px solid #3e3e52; border-radius: 6px;"
            )
            layout.addWidget(self.exp_box)

        # 4. Action Buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        info_lbl = QLabel("🛡️ Enforced read-only mode with query timeout and row caps.")
        info_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        button_row.addWidget(info_lbl)

        button_row.addStretch()

        # Reject Button (Default focus to guarantee accidental presses never approve)
        self.reject_btn = QPushButton("Reject Execution")
        self.reject_btn.setObjectName("danger_button")
        self.reject_btn.setDefault(True)
        self.reject_btn.setFocus()
        self.reject_btn.clicked.connect(self._on_reject)
        button_row.addWidget(self.reject_btn)

        # Approve Button
        self.approve_btn = QPushButton("Approve & Execute")
        self.approve_btn.setObjectName("success_button")
        self.approve_btn.clicked.connect(self._on_approve)
        button_row.addWidget(self.approve_btn)

        layout.addLayout(button_row)

    def _copy_sql_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.sql_query)
            self.copy_btn.setText("Copied!")
            self.copy_btn.setEnabled(False)

    def _on_approve(self) -> None:
        log.info("User explicitly APPROVED SQL query execution: %s", self.sql_query[:60])
        self.is_approved = True
        self.accept()

    def _on_reject(self) -> None:
        log.info("User explicitly REJECTED SQL query execution.")
        self.is_approved = False
        self.reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        # Closing the window is always treated as an explicit rejection
        self.is_approved = False
        super().closeEvent(event)

    def reject(self) -> None:
        # Guarantee rejection flag is set on any escape or cancel
        self.is_approved = False
        super().reject()

    @classmethod
    def ask_approval(
        cls,
        parent: QWidget | None,
        sql_query: str,
        explanation: str = "",
        database_name: str = "ecommerce.db",
    ) -> bool:
        """Convenience method displaying the modal dialog and returning approval status."""
        dialog = cls(
            sql_query=sql_query,
            explanation=explanation,
            database_name=database_name,
            parent=parent,
        )
        dialog.exec()
        return dialog.is_approved

