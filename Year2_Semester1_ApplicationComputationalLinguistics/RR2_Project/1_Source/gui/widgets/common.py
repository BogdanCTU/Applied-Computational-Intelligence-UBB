"""Shared UI components enforcing consistent layout, tables, status contrast, and dialogs."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..styles.theme import PALETTE, SPACE_SM, SPACE_XS, status_colors


def create_page_header(
    title: str,
    subtitle: str = "",
    right_widget: Optional[QWidget] = None,
) -> Tuple[QWidget, QLabel]:
    """Build standardized top page header with title, short description, and optional action widget."""
    container = QWidget()
    outer = QHBoxLayout(container)
    outer.setContentsMargins(0, 0, 0, SPACE_XS)
    outer.setSpacing(SPACE_SM)

    text_col = QVBoxLayout()
    text_col.setContentsMargins(0, 0, 0, 0)
    text_col.setSpacing(2)

    lbl_title = QLabel(title)
    lbl_title.setProperty("labelRole", "pageTitle")
    text_col.addWidget(lbl_title)

    if subtitle:
        lbl_sub = QLabel(subtitle)
        lbl_sub.setProperty("labelRole", "pageSubtitle")
        lbl_sub.setWordWrap(True)
        text_col.addWidget(lbl_sub)

    outer.addLayout(text_col, stretch=1)
    if right_widget is not None:
        outer.addWidget(right_widget, alignment=Qt.AlignRight | Qt.AlignVCenter)

    return container, lbl_title


def create_button(
    text: str,
    role: str = "secondary",
    tooltip: str = "",
    accessible_name: str = "",
) -> QPushButton:
    """Create a standardized QPushButton with semantic role (`primary`, `secondary`, `destructive`)."""
    btn = QPushButton(text)
    btn.setProperty("buttonRole", role)
    btn.setMinimumHeight(34)
    btn.setMaximumHeight(38)
    btn.setCursor(Qt.PointingHandCursor)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setAccessibleName(accessible_name or text)
    return btn


def configure_table(
    table: QTableWidget | QTableView,
    stretch_last: bool = True,
    hide_vertical_header: bool = True,
) -> None:
    """Apply consistent row heights, alternating backgrounds, selection behavior, and headers."""
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setEditTriggers(table.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
    table.setSelectionMode(table.SelectionMode.SingleSelection)
    table.setWordWrap(False)

    vh = table.verticalHeader()
    vh.setDefaultSectionSize(32)
    vh.setMinimumSectionSize(28)
    vh.setVisible(not hide_vertical_header)

    hh = table.horizontalHeader()
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setHighlightSections(False)
    if stretch_last:
        hh.setSectionResizeMode(QHeaderView.Stretch)


def make_status_item(
    text: str,
    level: str = "neutral",
    align: Qt.AlignmentFlag = Qt.AlignCenter,
) -> QTableWidgetItem:
    """Create a table item displaying readable status text paired with accessible contrast colors."""
    fg_hex, bg_hex = status_colors(level)
    it = QTableWidgetItem(text)
    it.setTextAlignment(align)
    it.setForeground(QColor(fg_hex))
    it.setBackground(QColor(bg_hex))
    font = QFont()
    font.setBold(level != "neutral")
    it.setFont(font)
    return it


def apply_status_label(
    label: QLabel,
    text: str,
    level: str = "neutral",
    bold: bool = True,
) -> None:
    """Style a status label using palette tokens so text remains legible against light surfaces."""
    fg_hex, _ = status_colors(level)
    if level == "neutral":
        fg_hex = PALETTE.text_secondary
    weight = "700" if bold else "400"
    label.setText(text)
    label.setStyleSheet(f"color: {fg_hex}; font-weight: {weight}; font-size: 13px; background: transparent;")


def format_user_error(exc: Exception | str) -> str:
    """Format an error cleanly for end-user dialogs without exposing multi-line tracebacks."""
    msg = str(exc).strip().splitlines()[0] if str(exc).strip() else "Unexpected error."
    return msg


def show_info_dialog(parent: Optional[QWidget], title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def show_warning_dialog(parent: Optional[QWidget], title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message)


def show_error_dialog(parent: Optional[QWidget], title: str, exc: Exception | str, next_action: str = "") -> None:
    detail = format_user_error(exc)
    body = f"{detail}\n\n{next_action}" if next_action else detail
    QMessageBox.critical(parent, title, body)


def confirm_destructive_action(parent: Optional[QWidget], title: str, message: str) -> bool:
    ans = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return ans == QMessageBox.Yes
