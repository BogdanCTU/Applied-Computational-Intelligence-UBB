"""Chronological Agent Execution Inspector widget displaying detailed timeline of agent actions."""

from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from agent.events import ActivityCategory, ActivityEvent, mask_sensitive_data
from app.widgets.sql_highlighter import SqlSyntaxHighlighter

log = logging.getLogger(__name__)

# Category styling configuration: (Icon, Background Color, Text/Border Color)
CATEGORY_STYLES: dict[str, tuple[str, str, str]] = {
    ActivityCategory.USER_REQUEST.value: ("👤", "#0284c720", "#38bdf8"),
    ActivityCategory.AGENT_STATUS.value: ("🤖", "#64748b20", "#94a3b8"),
    ActivityCategory.REASONING_SUMMARY.value: ("🧠", "#a855f720", "#c084fc"),
    ActivityCategory.PLANNING.value: ("🗺️", "#8b5cf620", "#a78bfa"),
    ActivityCategory.TOOL_CALL.value: ("🔧", "#f59e0b20", "#fbbf24"),
    ActivityCategory.TOOL_ARGUMENTS.value: ("⚙️", "#d9770620", "#f59e0b"),
    ActivityCategory.TOOL_RESULT.value: ("📦", "#10b98120", "#34d399"),
    ActivityCategory.SQL_GENERATION.value: ("📝", "#06b6d420", "#22d3ee"),
    ActivityCategory.SQL_VALIDATION.value: ("🛡️", "#0d948820", "#2dd4bf"),
    ActivityCategory.APPROVAL_REQUIRED.value: ("⚠️", "#b4530925", "#fbbf24"),
    ActivityCategory.APPROVAL_RESULT.value: ("⚖️", "#4f46e520", "#818cf8"),
    ActivityCategory.SQL_EXECUTION.value: ("⚡", "#ea580c20", "#fb923c"),
    ActivityCategory.SQL_RESULT.value: ("📊", "#05966920", "#10b981"),
    ActivityCategory.REPORT_PLANNING.value: ("📐", "#9333ea20", "#c084fc"),
    ActivityCategory.REPORT_GENERATION.value: ("📄", "#4338ca20", "#818cf8"),
    ActivityCategory.COMPLETION.value: ("✅", "#16a34a20", "#4ade80"),
    ActivityCategory.ERROR.value: ("❌", "#dc262625", "#f87171"),
}

STATUS_ICONS: dict[str, str] = {
    "in_progress": "⏳",
    "success": "🟢",
    "auto_approved": "🟢",
    "waiting_approval": "⚠️",
    "rejected": "⛔",
    "failed": "❌",
}


class ActivityEventCard(QFrame):
    """Visual timeline card representing a single atomic agent event."""

    def __init__(self, activity_event: ActivityEvent, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.activity_event = activity_event
        self._is_expanded = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("activity_event_card")
        self.setStyleSheet(
            "QFrame#activity_event_card { background-color: #1a1a24; border: 1px solid #2d2d3d; "
            "border-radius: 6px; padding: 6px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        # Status icon
        status_sym = STATUS_ICONS.get(self.activity_event.status, "•")
        self.status_lbl = QLabel(status_sym)
        self.status_lbl.setFixedWidth(16)
        header_row.addWidget(self.status_lbl)

        # Timestamp
        time_lbl = QLabel(self.activity_event.timestamp)
        time_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-family: monospace;")
        header_row.addWidget(time_lbl)

        # Category Pill
        cat_info = CATEGORY_STYLES.get(self.activity_event.category, ("•", "#33415520", "#94a3b8"))
        cat_icon, cat_bg, cat_color = cat_info
        cat_pill = QLabel(f"{cat_icon} {self.activity_event.category}")
        cat_pill.setStyleSheet(
            f"background-color: {cat_bg}; color: {cat_color}; border: 1px solid {cat_color}40; "
            "border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 600;"
        )
        header_row.addWidget(cat_pill)

        # Title
        title_lbl = QLabel(self.activity_event.title or "")
        title_lbl.setStyleSheet("color: #f1f5f9; font-weight: 600; font-size: 11px;")
        header_row.addWidget(title_lbl, stretch=1)

        # Duration badge if available
        if self.activity_event.duration_ms is not None:
            dur_lbl = QLabel(f"{self.activity_event.duration_ms:.0f}ms")
            dur_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
            header_row.addWidget(dur_lbl)

        # Expand/Collapse toggle button if details exist
        has_details = bool(
            self.activity_event.arguments
            or self.activity_event.result_summary
            or self.activity_event.metadata.get("sql_query")
            or self.activity_event.metadata.get("error")
        )

        if has_details:
            self.expand_btn = QPushButton("▼")
            self.expand_btn.setFixedSize(20, 20)
            self.expand_btn.setStyleSheet(
                "QPushButton { background-color: transparent; color: #94a3b8; border: none; font-size: 10px; } "
                "QPushButton:hover { color: #f1f5f9; }"
            )
            self.expand_btn.clicked.connect(self._toggle_expand)
            header_row.addWidget(self.expand_btn)
        else:
            self.expand_btn = None

        layout.addLayout(header_row)

        # Description (if present)
        if self.activity_event.description:
            desc_lbl = QLabel(self.activity_event.description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; margin-left: 22px;")
            layout.addWidget(desc_lbl)

        # Expandable Details Container
        if has_details:
            self.details_widget = QWidget()
            details_layout = QVBoxLayout(self.details_widget)
            details_layout.setContentsMargins(22, 4, 4, 4)
            details_layout.setSpacing(4)

            # SQL Query box if present
            sql_text = self.activity_event.metadata.get("sql_query")
            if sql_text:
                sql_title = QLabel("SQL Statement:")
                sql_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
                details_layout.addWidget(sql_title)

                sql_edit = QPlainTextEdit()
                sql_edit.setReadOnly(True)
                sql_edit.setPlainText(str(sql_text).strip())
                sql_edit.setMaximumHeight(90)
                sql_edit.setFont(QFont("JetBrains Mono, Menlo, Courier New", 10))
                sql_edit.setStyleSheet(
                    "background-color: #0f172a; color: #e2e8f0; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 4px;"
                )
                self.sql_highlighter = SqlSyntaxHighlighter(sql_edit.document())
                details_layout.addWidget(sql_edit)

            # Sanitized Arguments
            if self.activity_event.arguments:
                arg_title = QLabel("Tool Arguments (Sanitized):")
                arg_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
                details_layout.addWidget(arg_title)

                clean_args = mask_sensitive_data(self.activity_event.arguments)
                arg_edit = QPlainTextEdit()
                arg_edit.setReadOnly(True)
                arg_edit.setPlainText(json.dumps(clean_args, indent=2))
                arg_edit.setMaximumHeight(80)
                arg_edit.setFont(QFont("JetBrains Mono, Menlo, Courier New", 10))
                arg_edit.setStyleSheet(
                    "background-color: #0f172a; color: #94a3b8; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 4px;"
                )
                details_layout.addWidget(arg_edit)

            # Result Summary
            if self.activity_event.result_summary:
                res_title = QLabel("Result Summary:")
                res_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
                details_layout.addWidget(res_title)

                res_lbl = QLabel(self.activity_event.result_summary)
                res_lbl.setWordWrap(True)
                res_lbl.setStyleSheet(
                    "background-color: #0f172a; color: #cbd5e1; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 6px; font-size: 11px;"
                )
                details_layout.addWidget(res_lbl)
                details_layout.addWidget(res_title)

                res_lbl = QLabel(self.event.result_summary)
                res_lbl.setWordWrap(True)
                res_lbl.setStyleSheet(
                    "background-color: #0f172a; color: #cbd5e1; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 6px; font-size: 11px;"
                )
                details_layout.addWidget(res_lbl)

            layout.addWidget(self.details_widget)
            self.details_widget.setVisible(False)

    def _toggle_expand(self) -> None:
        self._is_expanded = not self._is_expanded
        if self.details_widget:
            self.details_widget.setVisible(self._is_expanded)
        if self.expand_btn:
            self.expand_btn.setText("▲" if self._is_expanded else "▼")


class AgentActivityInspectorWidget(QWidget):
    """Collapsible / dockable activity timeline inspector providing live visibility into agent execution."""

    cleared = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._events: list[ActivityEvent] = []
        self._cards: list[ActivityEventCard] = []
        self._user_scrolled_up = False
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Header Toolbar
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        header.setSpacing(8)

        title = QLabel("🔍 Agent Activity Inspector")
        title.setStyleSheet("font-weight: 700; font-size: 12px; color: #f3f4f6;")
        header.addWidget(title)

        self.count_badge = QLabel("0 events")
        self.count_badge.setStyleSheet(
            "background-color: #3b82f620; color: #60a5fa; border: 1px solid #3b82f640; "
            "border-radius: 10px; padding: 1px 8px; font-size: 10px; font-weight: 600;"
        )
        header.addWidget(self.count_badge)

        header.addStretch()

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header.addWidget(self.chk_autoscroll)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Clear activity timeline")
        self.btn_clear.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_clear.clicked.connect(self.clear_events)
        header.addWidget(self.btn_clear)

        main_layout.addLayout(header)

        # Scrollable Activity Cards Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #111116; border: 1px solid #2d2d3d; border-radius: 6px; }"
        )

        # Scrollbar detection for auto-scroll pause
        v_bar = self.scroll_area.verticalScrollBar()
        v_bar.valueChanged.connect(self._on_scroll_value_changed)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(6, 6, 6, 6)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _on_scroll_value_changed(self, value: int) -> None:
        v_bar = self.scroll_area.verticalScrollBar()
        # If user scrolled more than 30px away from bottom, consider scrolled up
        if v_bar.maximum() > 0 and (v_bar.maximum() - value) > 30:
            self._user_scrolled_up = True
        else:
            self._user_scrolled_up = False

    def add_activity_event(self, event: ActivityEvent | dict[str, Any]) -> None:
        """Append a new activity event card to the timeline."""
        if isinstance(event, dict):
            act_event = ActivityEvent(
                category=event.get("category", ActivityCategory.AGENT_STATUS.value),
                title=event.get("title", ""),
                description=event.get("description", ""),
                tool_name=event.get("tool_name"),
                arguments=mask_sensitive_data(event.get("arguments")),
                result_summary=event.get("result_summary"),
                duration_ms=event.get("duration_ms"),
                status=event.get("status", "success"),
                metadata=event.get("metadata", {}),
            )
        else:
            act_event = event

        self._events.append(act_event)
        card = ActivityEventCard(act_event, parent=self.cards_container)
        self._cards.append(card)

        # Insert before stretch at bottom
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.count_badge.setText(f"{len(self._events)} events")

        if self.chk_autoscroll.isChecked() and not self._user_scrolled_up:
            v_bar = self.scroll_area.verticalScrollBar()
            v_bar.setValue(v_bar.maximum())

    def clear_events(self) -> None:
        """Clear all event cards from the timeline."""
        self._events.clear()
        for card in self._cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self.count_badge.setText("0 events")
        self._user_scrolled_up = False
        self.cleared.emit()

    def event_count(self) -> int:
        return len(self._events)
