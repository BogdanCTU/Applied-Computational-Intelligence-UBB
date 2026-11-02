"""Screen 7: Comparison View — Side-by-side Original vs Local 17-point & pair diff view."""

from __future__ import annotations

import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class ComparisonView(QWidget):
    """Side-by-side comparison across Original Reference, Upstream Lite, Local Parity, and Local Adapted."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh_selectors)
        self.refresh_selectors()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        title = QLabel("Original vs. Local Side-by-Side 17-Point Artifact & Alignment Comparison")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        bar = QHBoxLayout()
        self.cmb_a = QComboBox()
        self.cmb_b = QComboBox()
        btn_cmp = QPushButton("Run 17-Point Side-by-Side Comparison")
        btn_cmp.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 5px 10px;")
        btn_cmp.clicked.connect(self.run_comparison)
        bar.addWidget(QLabel("Run A:"))
        bar.addWidget(self.cmb_a, stretch=1)
        bar.addWidget(QLabel("vs. Run B:"))
        bar.addWidget(self.cmb_b, stretch=1)
        bar.addWidget(btn_cmp)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)

        # Pair-level diff table with color coding
        self.tbl_pairs = QTableWidget(0, 6)
        self.tbl_pairs.setHorizontalHeaderLabels(
            ["Source URI", "Target URI", "In Reference", "In Run A", "In Run B", "Diff Classification"]
        )
        self.tbl_pairs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_pairs.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.tbl_pairs)

        # Full 17-point JSON report
        self.txt_report = QPlainTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        splitter.addWidget(self.txt_report)
        splitter.setSizes([320, 280])

        root.addWidget(splitter, stretch=1)

    def refresh_selectors(self) -> None:
        runs = self.state.history_service.list_runs(include_historical=False)
        for cmb in (self.cmb_a, self.cmb_b):
            cmb.blockSignals(True)
            cmb.clear()
            for r in runs:
                cmb.addItem(str(r["display_name"]), userData=str(r["experiment_id"]))
            cmb.blockSignals(False)
        if self.cmb_b.count() > 1:
            self.cmb_b.setCurrentIndex(1)

    def run_comparison(self) -> None:
        id_a = self.cmb_a.currentData()
        id_b = self.cmb_b.currentData()
        if not id_a or not id_b:
            return
        res = self.state.comparison_service.compare_runs(
            run_a_id_or_dir=str(id_a),
            run_a_label=self.cmb_a.currentText(),
            run_b_id_or_dir=str(id_b),
            run_b_label=self.cmb_b.currentText(),
        )

        diff_rows = res["pair_diff_rows"]
        self.tbl_pairs.setRowCount(len(diff_rows))
        color_map = {
            "Shared TP": QColor("#DCFCE7"),
            "Shared FP": QColor("#FEE2E2"),
            "Only in A (TP)": QColor("#DBEAFE"),
            "Only in B (TP)": QColor("#EDE9FE"),
            "Only in A (FP)": QColor("#FEF3C7"),
            "Only in B (FP)": QColor("#FEF3C7"),
            "Missed by Both (FN)": QColor("#F1F5F9"),
        }
        for r_idx, row in enumerate(diff_rows):
            cat = str(row["category"])
            bg = color_map.get(cat, QColor("#FFFFFF"))
            vals = [
                str(row["source_uri"]),
                str(row["target_uri"]),
                "Yes" if row["in_reference"] else "No",
                "Yes" if row["in_run_a"] else "No",
                "Yes" if row["in_run_b"] else "No",
                cat,
            ]
            for c_idx, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setBackground(bg)
                if 2 <= c_idx <= 4:
                    it.setTextAlignment(Qt.AlignCenter)
                self.tbl_pairs.setItem(r_idx, c_idx, it)

        self.txt_report.setPlainText(json.dumps(res["report_17"], indent=2))

