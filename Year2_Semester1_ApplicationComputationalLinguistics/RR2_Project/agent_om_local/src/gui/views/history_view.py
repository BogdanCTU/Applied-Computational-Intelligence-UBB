"""Screen 9: Logs & Experiment History View — Live streaming console, Cancel button, and run browser."""

from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class HistoryLogsView(QWidget):
    """Provides real-time execution log monitoring, safe run cancellation, and historical run browsing."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._runs_cache: list[dict] = []
        self._build_ui()
        self._connect_signals()
        self.refresh_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Live Execution Logs & Experiment History")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        # Active run control bar
        grp_live = QGroupBox("Active Execution Monitor")
        live_lay = QHBoxLayout(grp_live)
        self.lbl_live_status = QLabel("Status: IDLE (No active background run)")
        self.lbl_live_status.setStyleSheet("font-weight: bold; color: #334155;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(220)

        self.btn_cancel = QPushButton("Cancel Active Run")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(
            "background-color: #DC2626; color: white; font-weight: bold; padding: 5px 12px;"
        )
        self.btn_cancel.clicked.connect(self.state.runner_service.cancel_active_run)

        self.btn_clear_log = QPushButton("Clear Console")
        self.btn_clear_log.clicked.connect(lambda: self.txt_live_log.clear())

        live_lay.addWidget(self.lbl_live_status, stretch=1)
        live_lay.addWidget(self.progress)
        live_lay.addWidget(self.btn_cancel)
        live_lay.addWidget(self.btn_clear_log)
        root.addWidget(grp_live)

        splitter = QSplitter(Qt.Vertical)

        # Top pane: Live streaming console
        grp_console = QGroupBox("Streaming Execution Log")
        con_lay = QVBoxLayout(grp_console)
        self.txt_live_log = QPlainTextEdit()
        self.txt_live_log.setReadOnly(True)
        self.txt_live_log.setMaximumBlockCount(2000)
        self.txt_live_log.setPlaceholderText("Live stage progress and telemetry appear here during runs...")
        self.txt_live_log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        con_lay.addWidget(self.txt_live_log)
        splitter.addWidget(grp_console)

        # Bottom pane: Experiment History table + JSON detail inspector
        bottom_widget = QWidget()
        bot_lay = QVBoxLayout(bottom_widget)
        bot_lay.setContentsMargins(0, 0, 0, 0)

        hdr_lay = QHBoxLayout()
        hdr_lay.addWidget(QLabel("Indexed Replication & Reference Runs (Read-Only Safe):"))
        btn_refresh = QPushButton("Refresh Run History")
        btn_refresh.clicked.connect(self.refresh_history)
        hdr_lay.addStretch(1)
        hdr_lay.addWidget(btn_refresh)
        bot_lay.addLayout(hdr_lay)

        horiz_split = QSplitter(Qt.Horizontal)

        self.tbl_runs = QTableWidget(0, 9)
        self.tbl_runs.setHorizontalHeaderLabels(
            [
                "Experiment ID",
                "Profile",
                "Status",
                "F1 (%)",
                "P (%)",
                "R (%)",
                "Runtime (s)",
                "LLM Calls",
                "Tokens",
            ]
        )
        self.tbl_runs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 9):
            self.tbl_runs.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.tbl_runs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_runs.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_runs.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_runs.itemSelectionChanged.connect(self._on_run_selected)
        horiz_split.addWidget(self.tbl_runs)

        self.txt_detail = QPlainTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setPlaceholderText("Select a run on the left to inspect its configuration & summary JSON...")
        self.txt_detail.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        horiz_split.addWidget(self.txt_detail)
        horiz_split.setStretchFactor(0, 3)
        horiz_split.setStretchFactor(1, 2)

        bot_lay.addWidget(horiz_split, stretch=1)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

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

    def _on_run_started(self, exp_id: str) -> None:
        self.lbl_live_status.setText(f"Status: RUNNING — {exp_id}")
        self.lbl_live_status.setStyleSheet("font-weight: bold; color: #2563EB;")
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(5)

    def _on_stage_updated(self, stage: str, cur: int, tot: int, msg: str) -> None:
        pct = min(98, max(5, int((cur / max(tot, 1)) * 100)))
        self.progress.setValue(pct)
        self.lbl_live_status.setText(f"Status: RUNNING [{stage}] ({cur}/{tot})")

    def _on_run_finished(self, summary: dict) -> None:
        self.lbl_live_status.setText(f"Status: COMPLETED — {summary.get('experiment_id', '')}")
        self.lbl_live_status.setStyleSheet("font-weight: bold; color: #059669;")
        self.btn_cancel.setEnabled(False)
        self.progress.setValue(100)
        self.refresh_history()

    def _on_run_cancelled(self, summary: dict) -> None:
        self.lbl_live_status.setText(f"Status: CANCELLED — {summary.get('experiment_id', '')}")
        self.lbl_live_status.setStyleSheet("font-weight: bold; color: #D97706;")
        self.btn_cancel.setEnabled(False)
        self.refresh_history()

    def _on_run_failed(self, err: str) -> None:
        self.lbl_live_status.setText(f"Status: FAILED — {err}")
        self.lbl_live_status.setStyleSheet("font-weight: bold; color: #DC2626;")
        self.btn_cancel.setEnabled(False)

    def refresh_history(self) -> None:
        self._runs_cache = self.state.history_service.list_runs(include_historical=True)
        self.tbl_runs.setRowCount(len(self._runs_cache))
        for r_idx, rec in enumerate(self._runs_cache):
            status_str = str(rec.get("status", "unknown"))
            cells = [
                str(rec.get("experiment_id", "")),
                str(rec.get("profile_name", "")),
                status_str,
                f"{float(rec.get('f1_pct', 0.0)):.2f}",
                f"{float(rec.get('precision_pct', 0.0)):.2f}",
                f"{float(rec.get('recall_pct', 0.0)):.2f}",
                f"{float(rec.get('runtime_s', 0.0)):.2f}",
                str(rec.get("llm_calls", 0)),
                str(rec.get("total_tokens", 0)),
            ]
            for c_idx, val in enumerate(cells):
                it = QTableWidgetItem(val)
                if c_idx >= 2:
                    it.setTextAlignment(Qt.AlignCenter)
                if c_idx == 2:
                    if status_str == "completed":
                        it.setBackground(QColor("#DCFCE7"))
                    elif "readonly" in status_str:
                        it.setBackground(QColor("#E0F2FE"))
                    elif status_str in ("cancelled", "failed"):
                        it.setBackground(QColor("#FEE2E2"))
                self.tbl_runs.setItem(r_idx, c_idx, it)
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

