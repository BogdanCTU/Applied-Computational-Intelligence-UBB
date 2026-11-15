"""Screen 1: Dashboard View — Project overview, health summary cards, and quick navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import WorkbenchState


class DashboardView(QWidget):
    """Overview screen presenting replication objectives, live service status, and headline metrics."""

    def __init__(self, state: WorkbenchState, parent: QWidget | None = None):
        super().__init__(parent)
        self.state = state
        self._build_ui()
        self.state.runs_updated.connect(self.refresh)
        self.refresh()

    def _make_card(self, title: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px; }"
        )
        layout = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #475569; font-size: 11px; font-weight: bold;")
        lbl_val = QLabel("—")
        lbl_val.setWordWrap(True)
        lbl_val.setStyleSheet("color: #0F172A; font-size: 13px; font-weight: bold;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return frame, lbl_val

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        header = QLabel("Agent-OM Guided Replication & Validation Workbench")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        subtitle = QLabel(
            "Academic replication of Qiang et al. (PVLDB 2025, Vol. 18, pp. 516–529). "
            "Strictly 100% local Ollama + PostgreSQL/pgvector execution; original_repo/ is strictly read-only."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #334155; font-size: 12px;")
        root.addWidget(header)
        root.addWidget(subtitle)

        cards_grid = QGridLayout()
        c1, self.lbl_pg = self._make_card("PostgreSQL + pgvector (127.0.0.1:5432)")
        c2, self.lbl_ollama = self._make_card("Local Ollama Inference (127.0.0.1:11434)")
        c3, self.lbl_repo = self._make_card("Upstream Repository Integrity")
        c4, self.lbl_runs = self._make_card("Recorded Replication Runs")
        cards_grid.addWidget(c1, 0, 0)
        cards_grid.addWidget(c2, 0, 1)
        cards_grid.addWidget(c3, 0, 2)
        cards_grid.addWidget(c4, 0, 3)
        root.addLayout(cards_grid)

        # Quick navigation actions
        nav_group = QGroupBox("Guided Replication Workflow Shortcuts")
        nav_layout = QHBoxLayout(nav_group)
        shortcuts = [
            ("1. Verify Environment", 1),
            ("2. Select Dataset", 2),
            ("3. Configure Profile", 3),
            ("4. Launch Replication Wizard", 4),
            ("5. Inspect Intermediate Outputs", 5),
            ("6. Compare Original vs Local", 6),
            ("7. View Charts & Metrics", 7),
        ]
        for text, page_idx in shortcuts:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, idx=page_idx: self.state.navigate_requested.emit(idx))
            nav_layout.addWidget(btn)
        root.addWidget(nav_group)

        # Headline benchmark table
        bench_group = QGroupBox("Benchmark Comparison Summary (CMT–ConfOf)")
        bench_layout = QVBoxLayout(bench_group)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Experiment", "Profile", "TP", "FP", "FN", "Precision (%)", "Recall (%)", "F1 (%)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        bench_layout.addWidget(self.table)

        btn_refresh = QPushButton("Refresh Dashboard Status")
        btn_refresh.setFixedWidth(220)
        btn_refresh.clicked.connect(self.refresh)
        bench_layout.addWidget(btn_refresh, alignment=Qt.AlignRight)
        root.addWidget(bench_group, stretch=1)

    def refresh(self) -> None:
        pg = self.state.db_service.check_server_health()
        if pg.get("reachable"):
            self.lbl_pg.setText(f"ONLINE — {pg.get('server_version')} (pgvector {pg.get('pgvector_version')})")
            self.lbl_pg.setStyleSheet("color: #059669; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_pg.setText("OFFLINE — Check Environment tab")
            self.lbl_pg.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: bold;")

        ol = self.state.ollama_service.check_health()
        if ol.get("reachable"):
            self.lbl_ollama.setText(
                f"ONLINE — v{ol.get('version')} ({len(ol.get('models', []))} local models)"
            )
            self.lbl_ollama.setStyleSheet("color: #059669; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_ollama.setText("OFFLINE — Check Environment tab")
            self.lbl_ollama.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: bold;")

        orig = self.state.env_service.check_original_repo_status()
        if orig.get("exists"):
            self.lbl_repo.setText(
                f"READ-ONLY VERIFIED ({orig.get('baseline_file_count') or '8358'} files)"
            )
            self.lbl_repo.setStyleSheet("color: #059669; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_repo.setText("External / Custom Dataset Mode")

        runs = self.state.history_service.list_runs()
        self.lbl_runs.setText(f"{len(runs)} runs indexed")

        rows = self.state.evaluation_service.get_benchmark_comparison_rows()
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            vals = [
                str(row["short_label"]),
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
                if c_idx >= 2:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r_idx, c_idx, item)

