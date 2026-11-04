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

from app.widgets.sql_highlighter import SqlSyntaxHighlighter

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
        self.sql_query = (sql_query or "").strip()
        self.explanation = (explanation or "").strip()
        self.database_name = database_name or "ecommerce.db"
        self.is_approved: bool = False

        self.setWindowTitle("SQL Execution Approval")
        self.setModal(True)
        self.setMinimumSize(660, 520)
        self.resize(740, 580)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 1. Header Banner
        header = QLabel("⚠️ SQL Query Approval Required")
        header.setStyleSheet("font-size: 16px; font-weight: 700; color: #f59e0b;")
        layout.addWidget(header)

        desc = QLabel(
            "The AI agent has prepared the following read-only SQL query and requests permission "
            f"to execute it against the local database: <b>{self.database_name}</b>.<br>"
            "Please review the exact statement, operation mode, and explanation before deciding."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #d1d5db; line-height: 1.4; font-size: 12px;")
        layout.addWidget(desc)

        # 2. Metadata / Parameters Bar (Database, Operation, Guards)
        meta_frame = QFrame()
        meta_frame.setStyleSheet(
            "QFrame { background-color: #1a1a24; border: 1px solid #3b82f640; border-radius: 6px; padding: 6px; }"
        )
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(10, 4, 10, 4)
        meta_layout.setSpacing(16)

        db_badge = QLabel(f"🗄️ <b>Database:</b> {self.database_name}")
        db_badge.setStyleSheet("color: #93c5fd; font-size: 11px;")
        meta_layout.addWidget(db_badge)

        op_badge = QLabel("🛡️ <b>Operation:</b> Read-Only SELECT / CTE")
        op_badge.setStyleSheet("color: #34d399; font-size: 11px;")
        meta_layout.addWidget(op_badge)

        guard_badge = QLabel("⏱️ <b>Timeout:</b> 120s  |  <b>Max Rows:</b> 1,000")
        guard_badge.setStyleSheet("color: #9ca3af; font-size: 11px;")
        meta_layout.addWidget(guard_badge)

        meta_layout.addStretch()
        layout.addWidget(meta_frame)

        # 3. SQL Query Display with Copy Button & Syntax Highlighter
        sql_label_row = QHBoxLayout()
        sql_title = QLabel("Proposed SQL Statement (Exact Executable Query):")
        sql_title.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 12px;")
        sql_label_row.addWidget(sql_title)

        sql_label_row.addStretch()

        self.copy_btn = QPushButton("Copy SQL")
        self.copy_btn.setToolTip("Copy exact SQL query to clipboard")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.clicked.connect(self._copy_sql_to_clipboard)
        sql_label_row.addWidget(self.copy_btn)

        layout.addLayout(sql_label_row)

        self.sql_edit = QPlainTextEdit()
        self.sql_edit.setObjectName("sql_editor")
        self.sql_edit.setReadOnly(True)
        self.sql_edit.setPlainText(self.sql_query)
        self.sql_edit.setFont(QFont("JetBrains Mono, Menlo, Consolas, Courier New", 12))
        self.sql_edit.setStyleSheet(
            "QPlainTextEdit#sql_editor { background-color: #111116; color: #f3f4f6; "
            "border: 1px solid #3e3e52; border-radius: 6px; padding: 8px; }"
        )
        # Attach SQL Syntax Highlighter
        self.highlighter = SqlSyntaxHighlighter(self.sql_edit.document())
        layout.addWidget(self.sql_edit, stretch=2)

        # 4. Agent Explanation / Purpose
        if self.explanation:
            exp_label = QLabel("Query Purpose / Agent Explanation:")
            exp_label.setStyleSheet("font-weight: 600; color: #9ca3af; font-size: 12px;")
            layout.addWidget(exp_label)

            self.exp_box = QPlainTextEdit()
            self.exp_box.setReadOnly(True)
            self.exp_box.setPlainText(self.explanation)
            self.exp_box.setMaximumHeight(75)
            self.exp_box.setStyleSheet(
                "background-color: #1a1a24; color: #e5e7eb; border: 1px solid #3e3e52; "
                "border-radius: 6px; padding: 6px; font-size: 12px;"
            )
            layout.addWidget(self.exp_box)

        # 5. Action Buttons (Reject has default focus to prevent accidental approval)
        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        info_lbl = QLabel("⚠️ The query will execute ONLY if you approve. Closing or rejecting cancels execution.")
        info_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        button_row.addWidget(info_lbl)

        button_row.addStretch()

        # Reject Button (Default focus)
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
        self.is_approved = False
        super().closeEvent(event)

    def reject(self) -> None:
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
        """Convenience method displaying modal approval dialog and returning approval status.
        
        Strict Safety Invariant:
        If sql_query is empty, missing, or whitespace, this method REJECTS immediately
        without displaying any dialog.
        """
        cleaned_sql = (sql_query or "").strip()
        if not cleaned_sql:
            log.error("SqlApprovalDialog.ask_approval blocked: refusing to display dialog for empty SQL query")
            return False

        dialog = cls(
            sql_query=cleaned_sql,
            explanation=explanation,
            database_name=database_name,
            parent=parent,
        )
        dialog.exec()
        return dialog.is_approved

