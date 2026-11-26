"""Main application window hosting the 10-screen light-theme sidebar and compact header."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
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
from .styles import PALETTE, apply_light_theme
from .widgets import format_user_error
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
    """Primary desktop GUI window for the Agent-OM Workbench."""

    NAV_ITEMS = [
        "Dashboard",
        "Environment",
        "Datasets",
        "Configuration",
        "Run Pipeline",
        "Inspector",
        "Comparison",
        "Evaluation",
        "Run History",
        "Export",
    ]

    def __init__(self, state: Optional[WorkbenchState] = None, paths: Optional[ProjectPaths] = None):
        super().__init__()
        self.state = state or WorkbenchState(paths=paths, parent=self)
        self.setWindowTitle("Agent-OM Workbench")
        self.resize(1380, 860)
        self.setMinimumSize(1024, 680)

        apply_light_theme(QApplication.instance() or self)
        self._build_ui()
        self._connect_signals()
        self.nav_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Compact top application header
        header = QFrame()
        header.setObjectName("AppHeader")
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(16, 10, 16, 10)
        hdr_lay.setSpacing(12)

        lbl_title = QLabel("Agent-OM Workbench")
        lbl_title.setObjectName("AppTitleLabel")

        sep = QLabel("/")
        sep.setStyleSheet(f"color: {PALETTE.border}; font-size: 16px; background: transparent;")

        self.lbl_current_page = QLabel(self.NAV_ITEMS[0])
        self.lbl_current_page.setObjectName("HeaderPageLabel")

        mode_tag = "Standalone" if self.state.paths.is_frozen else "Python Source"
        self.lbl_header_status = QLabel(
            f"Mode: {mode_tag}  |  Local Loopback (127.0.0.1)  |  Reference Repo: Read-Only"
        )
        self.lbl_header_status.setObjectName("HeaderMetaLabel")

        hdr_lay.addWidget(lbl_title)
        hdr_lay.addWidget(sep)
        hdr_lay.addWidget(self.lbl_current_page)
        hdr_lay.addStretch(1)
        hdr_lay.addWidget(self.lbl_header_status)
        outer.addWidget(header)

        # Body: Left Navigation Sidebar + Stacked 10 Views
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("SidebarNav")
        self.nav_list.setFixedWidth(205)
        self.nav_list.setAccessibleName("Primary Navigation")
        self.nav_list.setFocusPolicy(Qt.StrongFocus)
        for label in self.NAV_ITEMS:
            item = QListWidgetItem(label)
            self.nav_list.addItem(item)

        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")

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
        status_bar.showMessage("Ready")

    def _connect_signals(self) -> None:
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.state.navigate_requested.connect(self.navigate_to)
        r = self.state.runner_service
        r.run_started.connect(
            lambda exp_id: self.statusBar().showMessage(f"Running: {exp_id}")
        )
        r.run_finished.connect(
            lambda s: self.statusBar().showMessage(
                f"Completed: {s.get('experiment_id', '')} ({s.get('total_runtime_s', 0)}s)"
            )
        )
        r.run_cancelled.connect(
            lambda s: self.statusBar().showMessage(f"Cancelled: {s.get('experiment_id', '')}")
        )
        r.run_failed.connect(
            lambda err: self.statusBar().showMessage(f"Failed: {format_user_error(err)}")
        )

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self.lbl_current_page.setText(self.NAV_ITEMS[row])

    def navigate_to(self, page_index: int) -> None:
        if 0 <= page_index < self.nav_list.count():
            self.nav_list.setCurrentRow(page_index)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.state.runner_service.is_running:
            ans = QMessageBox.question(
                self,
                "Active Experiment",
                "An experiment run is currently active.\nCancel the run and close the application?",
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
