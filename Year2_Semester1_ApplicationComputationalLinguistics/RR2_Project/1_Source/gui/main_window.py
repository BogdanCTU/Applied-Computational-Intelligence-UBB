"""Main application window hosting the 10-screen sidebar and safety banner."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .paths import ProjectPaths
from .state import WorkbenchState
from .views import (
    ComparisonView,
    ConfigurationView,
    DashboardView,
    DatasetView,
    EnvironmentView,
    EvaluationView,
    HistoryLogsView,
    PipelineInspectorView,
    ReplicationWizardView,
    ReportExportView,
)


class MainWindow(QMainWindow):
    """Primary Windows Desktop GUI window for the Agent-OM Guided Replication Workbench."""

    NAV_ITEMS = [
        "1. Dashboard",
        "2. Environment Diagnostics",
        "3. Dataset Manager",
        "4. Configuration Profiles",
        "5. Replication Wizard (14 Stages)",
        "6. Pipeline Stage Inspector",
        "7. Original vs Local Comparison",
        "8. Evaluation & Charts",
        "9. Live Logs & Run History",
        "10. Report & Artifact Export",
    ]

    def __init__(self, state: Optional[WorkbenchState] = None, paths: Optional[ProjectPaths] = None):
        super().__init__()
        self.state = state or WorkbenchState(paths=paths, parent=self)
        self.setWindowTitle("Agent-OM Guided Replication & Validation Workbench (Local-Only)")
        self.resize(1380, 860)

        self._build_ui()
        self._connect_signals()
        self.nav_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Top strict safety banner
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background-color: #0F172A; color: #F8FAFC; padding: 6px 14px; }"
        )
        ban_lay = QHBoxLayout(banner)
        ban_lay.setContentsMargins(12, 6, 12, 6)
        lbl_title = QLabel("Agent-OM Replication Workbench")
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        mode_tag = "Packaged .exe" if self.state.paths.is_frozen else "Python Source"
        lbl_guards = QLabel(
            f"Mode: {mode_tag}  |  original_repo/: STRICTLY READ-ONLY  |  "
            "Inference: Local Ollama (127.0.0.1)  |  Hybrid Memory: PostgreSQL + pgvector (127.0.0.1)"
        )
        lbl_guards.setStyleSheet("color: #93C5FD; font-size: 11px; font-weight: bold;")
        ban_lay.addWidget(lbl_title)
        ban_lay.addStretch(1)
        ban_lay.addWidget(lbl_guards)
        outer.addWidget(banner)

        # Body: Sidebar + Stacked 10 Views
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(255)
        self.nav_list.setStyleSheet(
            """
            QListWidget {
                background-color: #1E293B;
                color: #E2E8F0;
                border: none;
                font-size: 12px;
                padding-top: 6px;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid #334155;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
            """
        )
        for label in self.NAV_ITEMS:
            self.nav_list.addItem(QListWidgetItem(label))

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background-color: #F8FAFC; padding: 10px; }")

        self.dashboard_view = DashboardView(self.state)
        self.environment_view = EnvironmentView(self.state)
        self.dataset_view = DatasetView(self.state)
        self.configuration_view = ConfigurationView(self.state)
        self.wizard_view = ReplicationWizardView(self.state)
        self.inspector_view = PipelineInspectorView(self.state)
        self.comparison_view = ComparisonView(self.state)
        self.evaluation_view = EvaluationView(self.state)
        self.history_view = HistoryLogsView(self.state)
        self.export_view = ReportExportView(self.state)

        self.views = [
            self.dashboard_view,
            self.environment_view,
            self.dataset_view,
            self.configuration_view,
            self.wizard_view,
            self.inspector_view,
            self.comparison_view,
            self.evaluation_view,
            self.history_view,
            self.export_view,
        ]
        for view in self.views:
            self.stack.addWidget(view)

        body.addWidget(self.nav_list)
        body.addWidget(self.stack, stretch=1)
        outer.addLayout(body, stretch=1)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage(f"Workspace ready — Project root: {self.state.paths.project_root}")

    def _connect_signals(self) -> None:
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.state.navigate_requested.connect(self.navigate_to)
        r = self.state.runner_service
        r.run_started.connect(
            lambda exp_id: self.statusBar().showMessage(f"Running experiment: {exp_id}")
        )
        r.run_finished.connect(
            lambda s: self.statusBar().showMessage(
                f"Completed experiment: {s.get('experiment_id', '')} in {s.get('total_runtime_s', 0)}s"
            )
        )
        r.run_cancelled.connect(
            lambda s: self.statusBar().showMessage(f"Cancelled experiment: {s.get('experiment_id', '')}")
        )
        r.run_failed.connect(lambda err: self.statusBar().showMessage(f"Experiment failed: {err}"))

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def navigate_to(self, page_index: int) -> None:
        if 0 <= page_index < self.nav_list.count():
            self.nav_list.setCurrentRow(page_index)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.state.runner_service.is_running:
            ans = QMessageBox.question(
                self,
                "Active Experiment Running",
                "An experiment is currently running in the background.\n"
                "Cancel it cleanly and close the application?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                event.ignore()
                return
            self.state.runner_service.cancel_active_run()
            if self.state.runner_service._thread is not None:
                self.state.runner_service._thread.wait(5000)
        event.accept()

