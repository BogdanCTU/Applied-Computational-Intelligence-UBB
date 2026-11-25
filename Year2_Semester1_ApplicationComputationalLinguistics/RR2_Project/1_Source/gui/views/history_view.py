"""Screen 9: Run History View — Live streaming console, cancellation, and run history browser."""

from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import SPACE_SM
from ..widgets import (
    apply_status_label,
    configure_table,
    confirm_destructive_action,
    create_button,
    create_page_header,
    format_user_error,
    make_status_item,
)


class HistoryLogsView(QWidget):
    """Provides real-time execution log monitoring, run cancellation, and historical run browsing."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._runs_cache: list[dict] = []
        self._build_ui()
        self._connect_signals()
        self.refresh_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        btn_refresh = create_button(
            "Refresh",
            role="secondary",
            tooltip="Reload the list of recorded experiment runs",
            accessible_name="Refresh Run History",
        )
        btn_refresh.clicked.connect(self.refresh_history)
        header_w, _ = create_page_header(
            "Run History",
            "Monitor active execution logs and inspect completed experiment runs.",
            right_widget=btn_refresh,
        )
        root.addWidget(header_w)

        # Active run control bar
        grp_live = QGroupBox("Execution Status")
        live_lay = QHBoxLayout(grp_live)
        live_lay.setSpacing(SPACE_SM)
        self.lbl_live_status = QLabel("Ready")
        apply_status_label(self.lbl_live_status, "Ready", level="neutral")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(210)
        self.progress.setAccessibleName("Active run progress")

        self.btn_cancel = create_button(
            "Cancel Run",
            role="destructive",
            tooltip="Stop the currently running experiment at the next safe checkpoint",
            accessible_name="Cancel Active Run",
        )
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        self.btn_clear_log = create_button(
            "Clear Log",
            role="secondary",
            tooltip="Clear messages from the live log console",
            accessible_name="Clear Execution Log",
        )
        self.btn_clear_log.clicked.connect(lambda: self.txt_live_log.clear())

        live_lay.addWidget(self.lbl_live_status, stretch=1)
        live_lay.addWidget(self.progress)
        live_lay.addWidget(self.btn_cancel)
        live_lay.addWidget(self.btn_clear_log)
        root.addWidget(grp_live)

        splitter = QSplitter(Qt.Vertical)

        # Top pane: Live streaming console
        grp_console = QGroupBox("Execution Log")
        con_lay = QVBoxLayout(grp_console)
        self.txt_live_log = QPlainTextEdit()
        self.txt_live_log.setReadOnly(True)
        self.txt_live_log.setMaximumBlockCount(2000)
        self.txt_live_log.setPlaceholderText("Live stage progress and telemetry appear here during execution.")
        con_lay.addWidget(self.txt_live_log)
        splitter.addWidget(grp_console)

        # Bottom pane: Experiment History table + JSON detail inspector stacked vertically for full table readability
        grp_hist = QGroupBox("Recorded Runs")
        hist_lay = QVBoxLayout(grp_hist)
        detail_split = QSplitter(Qt.Vertical)

        self.tbl_runs = QTableWidget(0, 9)
        self.tbl_runs.setHorizontalHeaderLabels(
            [
                "Experiment ID",
                "Profile",
                "Status",
                "F1 (%)",
                "Precision (%)",
                "Recall (%)",
                "Runtime (s)",
                "Calls",
                "Tokens",
            ]
        )
        configure_table(self.tbl_runs, stretch_last=False)
        hh = self.tbl_runs.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 9):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.tbl_runs.itemSelectionChanged.connect(self._on_run_selected)
        detail_split.addWidget(self.tbl_runs)

        self.txt_detail = QPlainTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setPlaceholderText("Select a run above to inspect its summary and configuration JSON.")
        detail_split.addWidget(self.txt_detail)
        detail_split.setSizes([260, 150])

        hist_lay.addWidget(detail_split, stretch=1)
        splitter.addWidget(grp_hist)
        splitter.setSizes([130, 440])

        root.addWidget(splitter, stretch=1)

    def _connect_signals(self) -> None:
        self.state.runs_updated.connect(self.refresh_history)
        r = self.state.runner_service
        r.run_started.connect(self._on_run_started)
        r.stage_updated.connect(self._on_stage_updated)
        r.log_emitted.connect(self.txt_live_log.appendPlainText)
        r.run_finished.connect(self._on_run_finished)
        r.run_cancelled.connect(self._on_run_cancelled)
        r.run_failed.connect(self._on_run_failed)

    def _on_cancel_clicked(self) -> None:
        if confirm_destructive_action(
            self,
            "Cancel Experiment",
            "Stop the running experiment at the next safe checkpoint?",
        ):
            self.state.runner_service.cancel_active_run()

    def _on_run_started(self, exp_id: str) -> None:
        apply_status_label(self.lbl_live_status, f"Running: {exp_id}", level="info")
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(5)

    def _on_stage_updated(self, stage: str, cur: int, tot: int, msg: str) -> None:
        pct = min(98, max(5, int((cur / max(tot, 1)) * 100)))
        self.progress.setValue(pct)
        apply_status_label(self.lbl_live_status, f"Running: {stage} ({cur}/{tot})", level="info")

    def _on_run_finished(self, summary: dict) -> None:
        apply_status_label(
            self.lbl_live_status,
            f"Completed: {summary.get('experiment_id', '')}",
            level="success",
        )
        self.btn_cancel.setEnabled(False)
        self.progress.setValue(100)
        self.refresh_history()

    def _on_run_cancelled(self, summary: dict) -> None:
        apply_status_label(
            self.lbl_live_status,
            f"Cancelled: {summary.get('experiment_id', '')}",
            level="warning",
        )
        self.btn_cancel.setEnabled(False)
        self.refresh_history()

    def _on_run_failed(self, err: str) -> None:
        apply_status_label(
            self.lbl_live_status,
            f"Failed: {format_user_error(err)}",
            level="error",
        )
        self.btn_cancel.setEnabled(False)

    def refresh_history(self) -> None:
        self._runs_cache = self.state.history_service.list_runs(include_historical=True)
        self.tbl_runs.setRowCount(len(self._runs_cache))
        for r_idx, rec in enumerate(self._runs_cache):
            raw_status = str(rec.get("status", "unknown"))
            status_low = raw_status.lower()
            if status_low == "completed":
                status_text, status_lvl = "Completed", "success"
            elif "readonly" in status_low:
                status_text, status_lvl = "Reference", "info"
            elif status_low == "cancelled":
                status_text, status_lvl = "Cancelled", "warning"
            elif status_low == "failed":
                status_text, status_lvl = "Failed", "error"
            else:
                status_text, status_lvl = raw_status, "neutral"

            exp_id = str(rec.get("experiment_id", ""))
            it_exp = QTableWidgetItem(exp_id)
            it_exp.setToolTip(exp_id)
            it_prof = QTableWidgetItem(str(rec.get("profile_name", "")))
            it_status = make_status_item(status_text, level=status_lvl)

            num_vals = [
                f"{float(rec.get('f1_pct', 0.0)):.2f}",
                f"{float(rec.get('precision_pct', 0.0)):.2f}",
                f"{float(rec.get('recall_pct', 0.0)):.2f}",
                f"{float(rec.get('runtime_s', 0.0)):.2f}",
                str(rec.get("llm_calls", 0)),
                str(rec.get("total_tokens", 0)),
            ]
            self.tbl_runs.setItem(r_idx, 0, it_exp)
            self.tbl_runs.setItem(r_idx, 1, it_prof)
            self.tbl_runs.setItem(r_idx, 2, it_status)
            for offset, val in enumerate(num_vals):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_runs.setItem(r_idx, 3 + offset, it)

        if self._runs_cache and self.tbl_runs.currentRow() < 0:
            self.tbl_runs.selectRow(0)

    def _on_run_selected(self) -> None:
        row = self.tbl_runs.currentRow()
        if row < 0 or row >= len(self._runs_cache):
            return
        rec = self._runs_cache[row]
        exp_id = str(rec.get("experiment_id", ""))
        full_summary = self.state.history_service.load_run_summary(exp_id)
        payload: dict = {
            "normalized_record": {k: v for k, v in rec.items() if k != "raw"},
        }
        if full_summary is not None:
            payload["run_summary"] = full_summary
        run_dir = Path(str(rec.get("run_dir", "")))
        cfg_snap = run_dir / "config_snapshot.json"
        if cfg_snap.is_file():
            try:
                payload["config_snapshot"] = json.loads(cfg_snap.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.txt_detail.setPlainText(json.dumps(payload, indent=2))
