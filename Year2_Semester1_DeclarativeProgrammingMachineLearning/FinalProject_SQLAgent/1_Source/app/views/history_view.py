"""Report History dialog displaying previously generated PDF and CSV reports."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from reporting.report_manager import ReportHistoryManager, ReportMetadata

log = logging.getLogger(__name__)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class HistoryView(QDialog):
    """Dialog displaying persistent report history with preview and external open actions."""

    preview_report_requested = Signal(str, str)  # (file_path, format)

    def __init__(
        self,
        history_manager: ReportHistoryManager,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.history_manager = history_manager
        self._reports: list[ReportMetadata] = []

        self.setWindowTitle("Generated Report History")
        self.setMinimumSize(840, 520)
        self.resize(880, 540)

        self._init_ui()
        self.refresh_history()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header bar
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        top_row = QHBoxLayout()
        title_lbl = QLabel("📚 Generated Report History")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        top_row.addWidget(title_lbl)

        top_row.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setMinimumHeight(32)
        self.btn_refresh.clicked.connect(self.refresh_history)
        top_row.addWidget(self.btn_refresh)

        self.btn_open_folder = QPushButton("Open Reports Folder")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setMinimumHeight(32)
        self.btn_open_folder.clicked.connect(self._open_reports_dir)
        top_row.addWidget(self.btn_open_folder)

        header_box.addLayout(top_row)

        desc_lbl = QLabel("Browse previously generated analytical reports. Double-click or select to preview in workspace.")
        desc_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_box.addWidget(desc_lbl)

        layout.addLayout(header_box)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Title / Filename",
            "Format",
            "Created Date",
            "Records",
            "File Size",
            "Status",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        # Bottom Action Bar
        bottom_row = QHBoxLayout()
        self.summary_label = QLabel("0 reports recorded")
        self.summary_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        bottom_row.addWidget(self.summary_label)

        bottom_row.addStretch()

        self.btn_preview = QPushButton("Preview in Workspace")
        self.btn_preview.setObjectName("primary_button")
        self.btn_preview.setProperty("primary", True)
        self.btn_preview.setMinimumHeight(34)
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.setEnabled(False)
        self.btn_preview.clicked.connect(self._on_preview_clicked)
        bottom_row.addWidget(self.btn_preview)

        self.btn_open_file = QPushButton("Open in App")
        self.btn_open_file.setMinimumHeight(34)
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.clicked.connect(self._on_open_file_clicked)
        bottom_row.addWidget(self.btn_open_file)

        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(34)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def refresh_history(self) -> None:
        """Reload all records from the persistent ReportHistoryManager."""
        self._reports = self.history_manager.list_reports()
        self.table.setRowCount(len(self._reports))

        for row_idx, r in enumerate(self._reports):
            # 0. Title & filename
            p = Path(r.output_path)
            item_title = QTableWidgetItem(r.title or p.name)
            item_title.setToolTip(f"Path: {r.output_path}\nDescription: {r.description}")
            self.table.setItem(row_idx, 0, item_title)

            # 1. Format Badge
            item_fmt = QTableWidgetItem(r.output_format.upper())
            item_fmt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, item_fmt)

            # 2. Date
            date_str = r.created_at[:19].replace("T", " ") if r.created_at else "Unknown"
            item_date = QTableWidgetItem(date_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, item_date)

            # 3. Records
            item_recs = QTableWidgetItem(f"{r.record_count:,}")
            item_recs.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, item_recs)

            # 4. Size
            size_str = _format_size(r.file_size_bytes) if r.file_size_bytes else "—"
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, item_size)

            # 5. Availability
            exists = p.is_file()
            status_text = "● Available" if exists else "✕ Missing"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not exists:
                item_status.setForeground(QColor("#f87171"))
            else:
                item_status.setForeground(QColor("#34d399"))
            self.table.setItem(row_idx, 5, item_status)

        self.summary_label.setText(f"{len(self._reports)} reports recorded in history")
        self._on_selection_changed()

    def _get_selected_report(self) -> ReportMetadata | None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        idx = selected_rows[0].row()
        if 0 <= idx < len(self._reports):
            return self._reports[idx]
        return None

    def _on_selection_changed(self) -> None:
        rep = self._get_selected_report()
        has_valid_file = rep is not None and Path(rep.output_path).is_file()
        self.btn_preview.setEnabled(has_valid_file)
        self.btn_open_file.setEnabled(has_valid_file)

    def _on_row_double_clicked(self) -> None:
        self._on_preview_clicked()

    def _on_preview_clicked(self) -> None:
        rep = self._get_selected_report()
        if rep and Path(rep.output_path).is_file():
            self.preview_report_requested.emit(rep.output_path, rep.output_format)
            self.accept()

    def _on_open_file_clicked(self) -> None:
        rep = self._get_selected_report()
        if rep and Path(rep.output_path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(rep.output_path))

    def _open_reports_dir(self) -> None:
        reports_dir = self.history_manager.reports_dir
        if reports_dir.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(reports_dir)))

