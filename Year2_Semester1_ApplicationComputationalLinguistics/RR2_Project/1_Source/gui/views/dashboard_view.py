"""Screen 1: Dashboard View — Operational status overview, quick actions, and benchmark summary."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState
from ..styles import PALETTE, SPACE_MD, SPACE_SM
from ..widgets import apply_status_label, configure_table, create_button, create_page_header


class DashboardView(QWidget):
    """Overview screen presenting service status, workflow actions, and benchmark metrics."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh)
        self.refresh()

    def _make_status_panel(self, title: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("MetricPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(SPACE_MD, 10, SPACE_MD, 10)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setProperty("labelRole", "meta")
        lbl_val = QLabel("-")
        lbl_val.setWordWrap(True)
        lbl_val.setStyleSheet(
            f"color: {PALETTE.text_primary}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return frame, lbl_val

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        btn_refresh = create_button(
            "Refresh",
            role="secondary",
            tooltip="Refresh database, Ollama, repository, and benchmark status",
            accessible_name="Refresh Dashboard",
        )
        btn_refresh.clicked.connect(self.refresh)
        header_w, _ = create_page_header(
            "Dashboard",
            "System status, active configuration, and benchmark results summary.",
            right_widget=btn_refresh,
        )
        root.addWidget(header_w)

        # System Status summary panels
        status_grid = QGridLayout()
        status_grid.setSpacing(SPACE_MD)
        p1, self.lbl_pg = self._make_status_panel("PostgreSQL + pgvector")
        p2, self.lbl_ollama = self._make_status_panel("Ollama Inference")
        p3, self.lbl_repo = self._make_status_panel("Reference Repository")
        p4, self.lbl_runs = self._make_status_panel("Recorded Runs")
        status_grid.addWidget(p1, 0, 0)
        status_grid.addWidget(p2, 0, 1)
        status_grid.addWidget(p3, 0, 2)
        status_grid.addWidget(p4, 0, 3)
        for col in range(4):
            status_grid.setColumnStretch(col, 1)
        root.addLayout(status_grid)

        # Quick Actions
        nav_group = QGroupBox("Quick Actions")
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setSpacing(SPACE_SM)
        shortcuts = [
            ("Check Environment", 1, "secondary", "Open environment diagnostics and model policy verification"),
            ("Select Dataset", 2, "secondary", "Browse OAEI benchmarks or select local ontology files"),
            ("Model Profile", 3, "secondary", "Select model profile and matching parameters"),
            ("Run Matching", 4, "primary", "Open pipeline runner to execute ontology matching"),
            ("Compare Runs", 6, "secondary", "Compare baseline and adapted experiment results"),
            ("Export Results", 9, "secondary", "Export CSV, JSON, charts, and alignment files"),
        ]
        for text, page_idx, role, tip in shortcuts:
            btn = create_button(text, role=role, tooltip=tip, accessible_name=text)
            btn.clicked.connect(lambda _=False, idx=page_idx: self.state.navigate_requested.emit(idx))
            nav_layout.addWidget(btn)
        root.addWidget(nav_group)

        # Benchmark Summary Table
        bench_group = QGroupBox("Benchmark Results (CMT-ConfOf)")
        bench_layout = QVBoxLayout(bench_group)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Experiment", "Profile", "TP", "FP", "FN", "Precision (%)", "Recall (%)", "F1 (%)"]
        )
        configure_table(self.table, stretch_last=False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for c in range(2, 8):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        bench_layout.addWidget(self.table)
        root.addWidget(bench_group, stretch=1)

    def refresh(self) -> None:
        pg = self.state.db_service.check_server_health()
        if pg.get("reachable"):
            pgvec = f"pgvector {pg.get('pgvector_version')}" if pg.get("pgvector_version") else "pgvector"
            apply_status_label(
                self.lbl_pg,
                f"Connected ({pg.get('server_version')}, {pgvec})",
                level="success",
            )
        else:
            apply_status_label(self.lbl_pg, "Disconnected (Check Environment)", level="error")

        ol = self.state.ollama_service.check_health()
        if ol.get("reachable"):
            apply_status_label(
                self.lbl_ollama,
                f"Connected (v{ol.get('version')}, {len(ol.get('models', []))} models)",
                level="success",
            )
        else:
            apply_status_label(self.lbl_ollama, "Disconnected (Check Environment)", level="error")

        orig = self.state.env_service.check_original_repo_status()
        if orig.get("exists"):
            apply_status_label(
                self.lbl_repo,
                f"Read-Only Verified ({orig.get('baseline_file_count') or '8358'} files)",
                level="success",
            )
        else:
            apply_status_label(self.lbl_repo, "Custom Dataset Mode", level="neutral")

        runs = self.state.history_service.list_runs()
        self.lbl_runs.setText(f"{len(runs)} runs available")

        rows = self.state.evaluation_service.get_benchmark_comparison_rows()
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            exp_id = str(row.get("experiment_id", ""))
            short_lbl = str(row.get("short_label", ""))
            display_exp = exp_id if (exp_id and short_lbl == exp_id[:28] and len(exp_id) > 28) else (short_lbl or exp_id)
            vals = [
                display_exp,
                str(row["profile"]),
                str(row["tp"]),
                str(row["fp"]),
                str(row["fn"]),
                f"{float(row['precision_pct']):.2f}",
                f"{float(row['recall_pct']):.2f}",
                f"{float(row['f1_pct']):.2f}",
            ]
            for c_idx, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if c_idx in (0, 1):
                    item.setToolTip(val)
                if c_idx >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c_idx, item)
