"""Screen 7: Comparison View — Side-by-side 17-point checkpoint and pair-level diff viewer."""

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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import PALETTE, SPACE_SM
from ..widgets import configure_table, create_button, create_page_header, make_status_item


class ComparisonView(QWidget):
    """Side-by-side comparison across Reference, Upstream Lite, Local Parity, and Local Adapted runs."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh_selectors)
        self.refresh_selectors()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header_w, _ = create_page_header(
            "Comparison",
            "Compare two experiment runs across 17 intermediate checkpoints and pair-level alignments.",
        )
        root.addWidget(header_w)

        bar = QHBoxLayout()
        bar.setSpacing(SPACE_SM)
        self.cmb_a = QComboBox()
        self.cmb_a.setAccessibleName("Run A selector")
        self.cmb_b = QComboBox()
        self.cmb_b.setAccessibleName("Run B selector")
        btn_cmp = create_button(
            "Compare Runs",
            role="primary",
            tooltip="Compute pair-level differences and 17-point checkpoint comparison",
            accessible_name="Compare Runs",
        )
        btn_cmp.clicked.connect(self.run_comparison)
        bar.addWidget(QLabel("Run A:"))
        bar.addWidget(self.cmb_a, stretch=1)
        bar.addWidget(QLabel("Run B:"))
        bar.addWidget(self.cmb_b, stretch=1)
        bar.addWidget(btn_cmp)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)

        # Pair-level diff table
        self.tbl_pairs = QTableWidget(0, 6)
        self.tbl_pairs.setHorizontalHeaderLabels(
            ["Source URI", "Target URI", "In Reference", "In Run A", "In Run B", "Classification"]
        )
        configure_table(self.tbl_pairs, stretch_last=False)
        hh = self.tbl_pairs.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 6):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        splitter.addWidget(self.tbl_pairs)

        # Full 17-point JSON report
        self.txt_report = QPlainTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setPlaceholderText(
            "Select Run A and Run B above, then click Compare Runs to inspect pair-level diffs and checkpoints."
        )
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
        if self.cmb_a.count() > 0 and self.cmb_b.count() > 0:
            self.run_comparison()

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
        cat_level_map = {
            "Shared TP": "success",
            "Shared FP": "error",
            "Only in A (TP)": "info",
            "Only in B (TP)": "info",
            "Only in A (FP)": "warning",
            "Only in B (FP)": "warning",
            "Missed by Both (FN)": "neutral",
        }
        for r_idx, row in enumerate(diff_rows):
            cat = str(row["category"])
            lvl = cat_level_map.get(cat, "neutral")
            src_uri = str(row["source_uri"])
            tgt_uri = str(row["target_uri"])

            it_src = QTableWidgetItem(src_uri)
            it_src.setToolTip(src_uri)
            it_src.setForeground(QColor(PALETTE.text_primary))

            it_tgt = QTableWidgetItem(tgt_uri)
            it_tgt.setToolTip(tgt_uri)
            it_tgt.setForeground(QColor(PALETTE.text_primary))

            it_ref = QTableWidgetItem("Yes" if row["in_reference"] else "No")
            it_ref.setTextAlignment(Qt.AlignCenter)
            it_a = QTableWidgetItem("Yes" if row["in_run_a"] else "No")
            it_a.setTextAlignment(Qt.AlignCenter)
            it_b = QTableWidgetItem("Yes" if row["in_run_b"] else "No")
            it_b.setTextAlignment(Qt.AlignCenter)
            it_cat = make_status_item(cat, level=lvl)

            self.tbl_pairs.setItem(r_idx, 0, it_src)
            self.tbl_pairs.setItem(r_idx, 1, it_tgt)
            self.tbl_pairs.setItem(r_idx, 2, it_ref)
            self.tbl_pairs.setItem(r_idx, 3, it_a)
            self.tbl_pairs.setItem(r_idx, 4, it_b)
            self.tbl_pairs.setItem(r_idx, 5, it_cat)

        self.txt_report.setPlainText(json.dumps(res["report_17"], indent=2))
