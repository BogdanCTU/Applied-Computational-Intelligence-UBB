"""Screen 8: Evaluation View — Embedded Matplotlib charts and stage-by-stage attrition tables."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import PALETTE, SPACE_SM
from ..widgets import configure_table, create_button, create_page_header


class EvaluationView(QWidget):
    """Displays P/R/F1 comparison tables, stage-by-stage attrition, and Matplotlib charts."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._canvases: list[FigureCanvasQTAgg] = []
        self._build_ui()
        self.state.runs_updated.connect(self.refresh)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        btn_refresh = create_button(
            "Refresh Charts",
            role="secondary",
            tooltip="Recompute evaluation metrics and regenerate figures",
            accessible_name="Refresh Charts",
        )
        btn_refresh.clicked.connect(self.refresh)
        header_w, _ = create_page_header(
            "Evaluation",
            "Analyze alignment quality metrics, stage-by-stage candidate attrition, and charts.",
            right_widget=btn_refresh,
        )
        root.addWidget(header_w)

        splitter = QSplitter(Qt.Vertical)

        # Charts tab widget
        self.chart_tabs = QTabWidget()
        splitter.addWidget(self.chart_tabs)

        # Stage attrition table below charts
        bottom = QWidget()
        blay = QVBoxLayout(bottom)
        blay.setContentsMargins(0, 8, 0, 0)
        blay.setSpacing(SPACE_SM)
        row_sel = QHBoxLayout()
        row_sel.setSpacing(SPACE_SM)
        self.cmb_attr_run = QComboBox()
        self.cmb_attr_run.setAccessibleName("Attrition Run Selector")
        self.cmb_attr_run.currentIndexChanged.connect(self._refresh_attrition_table)
        row_sel.addWidget(QLabel("Experiment:"))
        row_sel.addWidget(self.cmb_attr_run, stretch=1)
        blay.addLayout(row_sel)

        self.tbl_attrition = QTableWidget(0, 5)
        self.tbl_attrition.setHorizontalHeaderLabels(
            ["Pipeline Stage", "Candidate Pairs", "True Positives", "False Positives", "Recall Ceiling (%)"]
        )
        configure_table(self.tbl_attrition, stretch_last=False)
        hh = self.tbl_attrition.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        blay.addWidget(self.tbl_attrition)
        splitter.addWidget(bottom)
        splitter.setSizes([470, 190])

        root.addWidget(splitter, stretch=1)

    def refresh(self) -> None:
        self.chart_tabs.clear()
        self._canvases.clear()

        figs = self.state.evaluation_service.build_all_figures()
        titles = {
            "prf1_bar": "Precision, Recall && F1",
            "pr_scatter": "Precision vs. Recall",
            "stage_attrition": "Stage Attrition",
            "threshold_sensitivity": "Threshold Sensitivity",
        }
        for key, label in titles.items():
            if key in figs:
                fig = figs[key]
                fig.set_dpi(96)
                fig.patch.set_facecolor(PALETTE.surface_primary)
                for ax in fig.get_axes():
                    if ax.get_title():
                        ax.title.set_fontsize(10)
                fig.tight_layout(pad=1.0)
                canvas = FigureCanvasQTAgg(fig)
                canvas.setMinimumHeight(260)
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
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_attrition.setItem(r_idx, c_idx, it)
