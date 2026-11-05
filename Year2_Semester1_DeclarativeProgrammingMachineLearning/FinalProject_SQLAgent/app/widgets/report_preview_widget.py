"""Central Report Workspace widget supporting native PDF viewing and tabular CSV preview."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models.csv_table_model import CsvTableModel

log = logging.getLogger(__name__)

# Check native QtPdf availability
try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    HAS_QT_PDF = True
except ImportError:
    HAS_QT_PDF = False
    QPdfDocument = None
    QPdfView = None


class ReportPreviewWidget(QWidget):
    """Primary workspace widget rendering PDF documents and CSV tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_report_path: Path | None = None
        self.current_format: str = "NONE"  # "PDF", "CSV", or "NONE"

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Top Controls Bar
        # -------------------------------------------------------------
        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("card_frame")
        self.toolbar_frame.setFixedHeight(48)

        tb_layout = QHBoxLayout(self.toolbar_frame)
        tb_layout.setContentsMargins(12, 6, 12, 6)
        tb_layout.setSpacing(8)

        # Document format badge
        self.format_badge = QLabel("READY")
        self.format_badge.setStyleSheet(
            "background-color: #3e3e52; color: #d1d5db; font-size: 11px; "
            "font-weight: 700; padding: 2px 8px; border-radius: 4px;"
        )
        tb_layout.addWidget(self.format_badge)

        # File name and details
        self.filename_label = QLabel("No report loaded")
        self.filename_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #f9fafb;")
        tb_layout.addWidget(self.filename_label)

        tb_layout.addStretch()

        # PDF Specific controls container
        self.pdf_controls = QWidget()
        pdf_h = QHBoxLayout(self.pdf_controls)
        pdf_h.setContentsMargins(0, 0, 0, 0)
        pdf_h.setSpacing(6)

        self.btn_prev_page = QPushButton("◀")
        self.btn_prev_page.setFixedSize(28, 28)
        self.btn_prev_page.setToolTip("Previous Page")
        self.btn_prev_page.clicked.connect(self._prev_page)
        pdf_h.addWidget(self.btn_prev_page)

        self.page_indicator = QLabel("Page 1 of 1")
        self.page_indicator.setStyleSheet("color: #d1d5db; font-size: 12px;")
        pdf_h.addWidget(self.page_indicator)

        self.btn_next_page = QPushButton("▶")
        self.btn_next_page.setFixedSize(28, 28)
        self.btn_next_page.setToolTip("Next Page")
        self.btn_next_page.clicked.connect(self._next_page)
        pdf_h.addWidget(self.btn_next_page)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(28, 28)
        self.btn_zoom_in.setToolTip("Zoom In")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        pdf_h.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(28, 28)
        self.btn_zoom_out.setToolTip("Zoom Out")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        pdf_h.addWidget(self.btn_zoom_out)

        self.btn_fit_width = QPushButton("Fit Width")
        self.btn_fit_width.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_fit_width.clicked.connect(self._fit_to_width)
        pdf_h.addWidget(self.btn_fit_width)

        self.btn_fit_page = QPushButton("Fit Page")
        self.btn_fit_page.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_fit_page.clicked.connect(self._fit_to_page)
        pdf_h.addWidget(self.btn_fit_page)

        tb_layout.addWidget(self.pdf_controls)
        self.pdf_controls.setVisible(False)

        # CSV Specific controls container
        self.csv_controls = QWidget()
        csv_h = QHBoxLayout(self.csv_controls)
        csv_h.setContentsMargins(0, 0, 0, 0)
        self.csv_stats_label = QLabel("0 records")
        self.csv_stats_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        csv_h.addWidget(self.csv_stats_label)
        tb_layout.addWidget(self.csv_controls)
        self.csv_controls.setVisible(False)

        # External action buttons
        self.btn_open_external = QPushButton("Open in App")
        self.btn_open_external.setToolTip("Open this report file in your default system application")
        self.btn_open_external.clicked.connect(self._open_in_external_app)
        tb_layout.addWidget(self.btn_open_external)

        self.btn_open_folder = QPushButton("Folder")
        self.btn_open_folder.setToolTip("Open containing directory in Finder / File Explorer")
        self.btn_open_folder.clicked.connect(self._open_containing_folder)
        tb_layout.addWidget(self.btn_open_folder)

        main_layout.addWidget(self.toolbar_frame)

        # -------------------------------------------------------------
        # 2. Main Stacked Workspace (Placeholder, PDF, CSV, Fallback)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        # View Index 0: Empty Placeholder
        self.placeholder_page = self._create_placeholder_page()
        self.stack.addWidget(self.placeholder_page)

        # View Index 1: PDF Viewer
        self.pdf_page = self._create_pdf_page()
        self.stack.addWidget(self.pdf_page)

        # View Index 2: CSV Table Viewer
        self.csv_page = self._create_csv_page()
        self.stack.addWidget(self.csv_page)

        # View Index 3: Fallback / Error Page
        self.error_page = self._create_error_page()
        self.stack.addWidget(self.error_page)

        main_layout.addWidget(self.stack, stretch=1)
        self.set_empty_state()

    def _create_placeholder_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card_frame")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon_lbl = QLabel("📊")
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel("Report Workspace")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #f9fafb;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Your reports will appear here.<br>"
            "Ask the AI assistant to analyze sales, products, or customers to generate a report."
        )
        sub_lbl.setStyleSheet("font-size: 13px; color: #9ca3af; line-height: 1.5;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_lbl)

        return page

    def _create_pdf_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card_frame")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)

        if HAS_QT_PDF:
            self.pdf_document = QPdfDocument(self)
            self.pdf_view = QPdfView(self)
            self.pdf_view.setDocument(self.pdf_document)
            self.pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

            # Connect page changes to update indicator
            nav = self.pdf_view.pageNavigator()
            nav.currentPageChanged.connect(self._on_pdf_page_changed)

            layout.addWidget(self.pdf_view)
        else:
            self.pdf_document = None
            self.pdf_view = None
            lbl = QLabel(
                "Native QtPdf is not available on this platform.<br>"
                "Use the 'Open in App' button above to view this PDF report."
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #f59e0b; font-size: 14px;")
            layout.addWidget(lbl)

        return page

    def _create_csv_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card_frame")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)

        self.csv_model = CsvTableModel(parent=self)
        self.csv_table = QTableView(self)
        self.csv_table.setModel(self.csv_model)
        self.csv_table.setAlternatingRowColors(True)
        self.csv_table.setSortingEnabled(False)
        self.csv_table.horizontalHeader().setStretchLastSection(True)
        self.csv_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.csv_table.verticalHeader().setDefaultSectionSize(26)

        layout.addWidget(self.csv_table)
        return page

    def _create_error_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("card_frame")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.error_title = QLabel("⚠️ Unable to load report")
        self.error_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ef4444;")
        self.error_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_title)

        self.error_details = QLabel("File could not be found or read.")
        self.error_details.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.error_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_details)

        return page

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def set_empty_state(self) -> None:
        """Reset workspace to initial welcome state."""
        self.current_report_path = None
        self.current_format = "NONE"
        self.format_badge.setText("READY")
        self.format_badge.setStyleSheet(
            "background-color: #3e3e52; color: #d1d5db; font-size: 11px; "
            "font-weight: 700; padding: 2px 8px; border-radius: 4px;"
        )
        self.filename_label.setText("No report loaded")
        self.pdf_controls.setVisible(False)
        self.csv_controls.setVisible(False)
        self.btn_open_external.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.stack.setCurrentIndex(0)

    def load_report(self, file_path: str | Path, format_type: str | None = None) -> bool:
        """Load a generated report file into the workspace (PDF or CSV)."""
        p = Path(file_path).resolve()
        if not p.is_file():
            self._show_error("File Not Found", f"The report file does not exist at:<br>{p}")
            return False

        detected_format = (format_type or p.suffix.lstrip(".").upper()).upper()
        self.current_report_path = p
        self.current_format = detected_format

        self.filename_label.setText(p.name)
        self.btn_open_external.setEnabled(True)
        self.btn_open_folder.setEnabled(True)

        if detected_format == "PDF":
            return self._load_pdf(p)
        elif detected_format == "CSV":
            return self._load_csv(p)
        else:
            self._show_error("Unsupported Format", f"Cannot preview report format: {detected_format}")
            return False

    # -----------------------------------------------------------------
    # Internal Loading & Navigation
    # -----------------------------------------------------------------

    def _load_pdf(self, path: Path) -> bool:
        self.format_badge.setText("PDF")
        self.format_badge.setStyleSheet(
            "background-color: rgba(239, 68, 68, 0.2); color: #f87171; "
            "border: 1px solid rgba(239, 68, 68, 0.4); font-size: 11px; "
            "font-weight: 700; padding: 2px 8px; border-radius: 4px;"
        )
        self.pdf_controls.setVisible(True)
        self.csv_controls.setVisible(False)

        if HAS_QT_PDF and self.pdf_document is not None:
            self.pdf_document.load(str(path))
            total_pages = self.pdf_document.pageCount()
            self.page_indicator.setText(f"Page 1 of {max(1, total_pages)}")
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.stack.setCurrentIndex(1)
            return True
        else:
            self.stack.setCurrentIndex(1)
            return True

    def _load_csv(self, path: Path) -> bool:
        self.format_badge.setText("CSV")
        self.format_badge.setStyleSheet(
            "background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; "
            "border: 1px solid rgba(59, 130, 246, 0.4); font-size: 11px; "
            "font-weight: 700; padding: 2px 8px; border-radius: 4px;"
        )
        self.pdf_controls.setVisible(False)
        self.csv_controls.setVisible(True)

        ok = self.csv_model.load_file(path)
        if not ok:
            self._show_error("CSV Error", f"Failed to parse CSV file: {path.name}")
            return False

        rows = self.csv_model.total_file_rows
        cols = len(self.csv_model.headers)
        stats = f"{rows:,} rows × {cols} columns"
        if self.csv_model.is_truncated:
            stats += " (Preview capped)"
        self.csv_stats_label.setText(stats)

        self.csv_table.resizeColumnsToContents()
        self.stack.setCurrentIndex(2)
        return True

    def _show_error(self, title: str, details: str) -> None:
        self.error_title.setText(f"⚠️ {title}")
        self.error_details.setText(details)
        self.stack.setCurrentIndex(3)

    def _on_pdf_page_changed(self, current_page: int) -> None:
        if self.pdf_document:
            total = self.pdf_document.pageCount()
            self.page_indicator.setText(f"Page {current_page + 1} of {max(1, total)}")

    def _prev_page(self) -> None:
        if HAS_QT_PDF and self.pdf_view:
            nav = self.pdf_view.pageNavigator()
            cur = nav.currentPage()
            if cur > 0:
                nav.jump(cur - 1, nav.currentLocation(), nav.currentZoom())

    def _next_page(self) -> None:
        if HAS_QT_PDF and self.pdf_view and self.pdf_document:
            nav = self.pdf_view.pageNavigator()
            cur = nav.currentPage()
            if cur < self.pdf_document.pageCount() - 1:
                nav.jump(cur + 1, nav.currentLocation(), nav.currentZoom())

    def _zoom_in(self) -> None:
        if HAS_QT_PDF and self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(self.pdf_view.zoomFactor() * 1.2)

    def _zoom_out(self) -> None:
        if HAS_QT_PDF and self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(max(0.2, self.pdf_view.zoomFactor() / 1.2))

    def _fit_to_width(self) -> None:
        if HAS_QT_PDF and self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _fit_to_page(self) -> None:
        if HAS_QT_PDF and self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _open_in_external_app(self) -> None:
        if self.current_report_path and self.current_report_path.is_file():
            url = QUrl.fromLocalFile(str(self.current_report_path))
            QDesktopServices.openUrl(url)

    def _open_containing_folder(self) -> None:
        if self.current_report_path and self.current_report_path.is_file():
            folder_url = QUrl.fromLocalFile(str(self.current_report_path.parent))
            QDesktopServices.openUrl(folder_url)
