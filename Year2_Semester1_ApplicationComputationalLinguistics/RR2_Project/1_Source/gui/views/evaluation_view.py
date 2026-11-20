"""Screen 8: Evaluation View — Embedded Matplotlib FigureCanvasQTAgg charts & attrition tables."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class EvaluationView(QWidget):
    """Displays P/R/F1 comparison tables, stage-by-stage attrition, and interactive Matplotlib charts."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._canvases: list[FigureCanvasQTAgg] = []
        self._build_ui()
        self.state.runs_updated.connect(self.refresh)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("Experimental Evaluation, Stage Attrition & Matplotlib Charts")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        btn_refresh = QPushButton("Recompute Charts & Metrics")
        btn_refresh.clicked.connect(self.refresh)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_refresh)
        root.addLayout(top)

        splitter = QSplitter(Qt.Vertical)

        # Charts tab widget
        self.chart_tabs = QTabWidget()
        splitter.addWidget(self.chart_tabs)

        # Stage attrition table below charts
        bottom = QWidget()
        blay = QVBoxLayout(bottom)
        row_sel = QHBoxLayout()
        self.cmb_attr_run = QComboBox()
        self.cmb_attr_run.currentIndexChanged.connect(self._refresh_attrition_table)
        row_sel.addWidget(QLabel("Inspect Stage-by-Stage Candidate Attrition for Run:"))
        row_sel.addWidget(self.cmb_attr_run, stretch=1)
        blay.addLayout(row_sel)

        self.tbl_attrition = QTableWidget(0, 5)
        self.tbl_attrition.setHorizontalHeaderLabels(
            ["Pipeline Stage", "Candidate Pairs", "True Positives (TP)", "False Positives (FP)", "Recall Ceiling (%)"]
        )
        self.tbl_attrition.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_attrition.setEditTriggers(QTableWidget.NoEditTriggers)
        blay.addWidget(self.tbl_attrition)
        splitter.addWidget(bottom)
        splitter.setSizes([400, 220])

        root.addWidget(splitter, stretch=1)

    def refresh(self) -> None:
        # Rebuild embedded Matplotlib FigureCanvasQTAgg tabs
        self.chart_tabs.clear()
        self._canvases.clear()

        figs = self.state.evaluation_service.build_all_figures()
        titles = {
            "prf1_bar": "1. Precision / Recall / F1 Bar Comparison",
            "pr_scatter": "2. Precision vs. Recall (Iso-F1 Contours)",
            "stage_attrition": "3. Stage-by-Stage Candidate Attrition",
            "threshold_sensitivity": "4. Similarity Threshold Sensitivity",
        }
        for key, label in titles.items():
            if key in figs:
                canvas = FigureCanvasQTAgg(figs[key])
                self._canvases.append(canvas)
                self.chart_tabs.addTab(canvas, label)

        # Populate attrition selector
        self.cmb_attr_run.blockSignals(True)
        self.cmb_attr_run.clear()
        for r in self.state.history_service.list_runs(include_historical=False):
            exp_id = str(r["experiment_id"])
            if self.state.evaluation_service.load_stage_attrition_for_run(exp_id):
                self.cmb_attr_run.addItem(str(r["display_name"]), userData=exp_id)
        self.cmb_attr_run.blockSignals(False)
        self._refresh_attrition_table()

    def _refresh_attrition_table(self) -> None:
        exp_id = self.cmb_attr_run.currentData()
        if not exp_id:
            self.tbl_attrition.setRowCount(0)
            return
        att = self.state.evaluation_service.load_stage_attrition_for_run(str(exp_id))
        stages = (att or {}).get("stages", [])
        self.tbl_attrition.setRowCount(len(stages))
        for r_idx, st in enumerate(stages):
            vals = [
                str(st.get("label", "")),
                str(st.get("candidate_pairs", 0)),
                str(st.get("tp", 0)),
                str(st.get("fp", 0)),
                f"{float(st.get('recall_ceiling_pct', 0.0)):.2f}",
            ]
            for c_idx, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c_idx >= 1:
                    it.setTextAlignment(Qt.AlignCenter)
                self.tbl_attrition.setItem(r_idx, c_idx, it)

