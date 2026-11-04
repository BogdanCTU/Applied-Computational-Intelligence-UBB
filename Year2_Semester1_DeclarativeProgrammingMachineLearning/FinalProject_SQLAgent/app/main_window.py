"""Main application window implementing the split-view Report Workspace and lateral Chat."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from agent import AgentEvent, AgentEventType, AgentOrchestrator, AgentRunResult
from app.dialogs.sql_approval_dialog import SqlApprovalDialog
from app.views.chat_view import ChatView
from app.views.history_view import HistoryView
from app.views.settings_view import SettingsView
from app.widgets.report_preview_widget import ReportPreviewWidget
from app.workers.agent_worker import AgentWorker, OllamaCheckWorker
from config.settings import AppSettings

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary window hosting the central Report Workspace, Chat view, and management dialogs."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        orchestrator: AgentOrchestrator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.orchestrator = orchestrator or AgentOrchestrator(settings)
        self.active_worker: AgentWorker | None = None
        self._check_worker: OllamaCheckWorker | None = None

        self.setWindowTitle("Local Report SQL Agent")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        self._init_ui()
        self._connect_signals()

        # Trigger non-blocking asynchronous Ollama health check on startup
        QTimer.singleShot(100, self._check_ollama_status)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. Top Application Header
        # -------------------------------------------------------------
        self.header_bar = QFrame()
        self.header_bar.setObjectName("header_bar")
        self.header_bar.setFixedHeight(54)

        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)

        # Title & database info
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("Report SQL Agent")
        title_lbl.setObjectName("app_title")
        title_box.addWidget(title_lbl)

        db_name = Path(self.settings.database_path).name
        sub_lbl = QLabel(f"Local SQLite Database: {db_name} (Read-Only Mode)")
        sub_lbl.setObjectName("app_subtitle")
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Status indicator pill
        self.status_pill = QLabel("Checking Ollama...")
        self.status_pill.setObjectName("status_pill_offline")
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.status_pill)

        # Action Buttons
        self.btn_history = QPushButton("Report History")
        self.btn_history.setToolTip("View and export previously generated reports")
        header_layout.addWidget(self.btn_history)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setToolTip("Configure local Ollama, database query limits, and reports")
        header_layout.addWidget(self.btn_settings)

        root_layout.addWidget(self.header_bar)

        # -------------------------------------------------------------
        # 2. Split Workspace Layout (Left: Report, Right: Chat)
        # -------------------------------------------------------------
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setContentsMargins(8, 8, 8, 8)

        # Left Pane: Report Workspace
        self.report_workspace = ReportPreviewWidget(parent=self.splitter)
        self.splitter.addWidget(self.report_workspace)

        # Right Pane: Lateral Chat Interface
        self.chat_view = ChatView(parent=self.splitter)
        self.splitter.addWidget(self.chat_view)

        # Set stretch factors (~65% workspace, ~35% chat)
        self.splitter.setStretchFactor(0, 65)
        self.splitter.setStretchFactor(1, 35)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        root_layout.addWidget(self.splitter, stretch=1)

    def _connect_signals(self) -> None:
        self.btn_history.clicked.connect(self._open_history_dialog)
        self.btn_settings.clicked.connect(self._open_settings_dialog)

        self.chat_view.message_submitted.connect(self._handle_user_message)
        self.chat_view.cancellation_requested.connect(self._cancel_active_worker)
        self.chat_view.clear_requested.connect(self._clear_conversation)

    # -----------------------------------------------------------------
    # Ollama Health & Status Checking
    # -----------------------------------------------------------------

    def _check_ollama_status(self) -> None:
        """Asynchronously verify local Ollama presence without blocking the GUI."""
        self._check_worker = OllamaCheckWorker(self.settings, parent=self)
        self._check_worker.signals.check_completed.connect(self._on_ollama_status_checked)
        self._check_worker.start()

    def _on_ollama_status_checked(
        self, is_online: bool, ver_or_err: str, installed_models: list[str]
    ) -> None:
        target_model = self.settings.ollama.model
        if is_online:
            has_target = any(target_model in m for m in installed_models)
            if has_target:
                self.status_pill.setText(f"● Ollama Online ({target_model})")
                self.status_pill.setObjectName("status_pill_online")
                self.status_pill.setToolTip(
                    f"Ollama daemon running locally (v{ver_or_err})\nModel '{target_model}' is ready."
                )
            else:
                self.status_pill.setText(f"● Ollama Online (Model missing)")
                self.status_pill.setObjectName("status_pill_offline")
                self.status_pill.setToolTip(
                    f"Ollama is online, but model '{target_model}' is not installed.\n"
                    f"Installed models: {installed_models}"
                )
        else:
            self.status_pill.setText("● Ollama Offline")
            self.status_pill.setObjectName("status_pill_offline")
            self.status_pill.setToolTip(
                f"Cannot connect to Ollama at {self.settings.ollama.host}.\n"
                f"Details: {ver_or_err}\n"
                "Please ensure the Ollama application is running locally."
            )

        # Force Qt stylesheet refresh for the dynamic objectName
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    # -----------------------------------------------------------------
    # Agent Workflow Orchestration & Thread Management
    # -----------------------------------------------------------------

    def _handle_user_message(self, message: str) -> None:
        """Launch background AgentWorker to process user request asynchronously."""
        if self.active_worker and self.active_worker.isRunning():
            QMessageBox.information(
                self,
                "Request in Progress",
                "The agent is currently processing another request. Please wait or cancel the running task.",
            )
            return

        self.chat_view.set_processing_state(True, "Starting agent workflow...")

        self.active_worker = AgentWorker(self.orchestrator, message, parent=self)
        self.active_worker.signals.started.connect(
            lambda: self.chat_view.update_status_message("Analyzing request with Ollama...")
        )
        self.active_worker.signals.progress_event.connect(self._on_agent_progress_event)
        self.active_worker.signals.approval_requested.connect(self._on_sql_approval_requested)
        self.active_worker.signals.report_generated.connect(self._on_report_generated)
        self.active_worker.signals.finished.connect(self._on_agent_finished)
        self.active_worker.signals.error.connect(self._on_agent_error)
        self.active_worker.signals.cancelled.connect(self._on_agent_cancelled)
        self.active_worker.start()

    def _on_agent_progress_event(self, event: AgentEvent) -> None:
        """Update live status labels in chat based on orchestrator event type."""
        t = event.event_type
        if t == AgentEventType.TOOL_CALL_PROPOSED:
            tool_name = event.data.get("tool", "")
            self.chat_view.update_status_message(f"Running tool: {tool_name}...")

        elif t == AgentEventType.SQL_PROPOSED:
            sql = event.data.get("sql_query", "")
            exp = event.data.get("explanation", "")
            self.chat_view.add_sql_preview(sql, title="Proposed SQL Query", status="Validated", explanation=exp)
            self.chat_view.update_status_message("Awaiting user SQL approval...")

        elif t == AgentEventType.SQL_APPROVED:
            self.chat_view.update_status_message("Executing approved SQL query...")

        elif t == AgentEventType.SQL_DENIED:
            self.chat_view.update_status_message("SQL execution was rejected.")

        elif t == AgentEventType.REPORT_GENERATED:
            self.chat_view.update_status_message("Report generated successfully.")

    def _on_sql_approval_requested(
        self, sql_query: str, explanation: str, response_queue: Any
    ) -> None:
        """Present modal SQL Approval Dialog on GUI thread and send choice back to worker."""
        log.info("Displaying SQL approval dialog for query: %s", sql_query[:60])
        approved = SqlApprovalDialog.ask_approval(
            parent=self,
            sql_query=sql_query,
            explanation=explanation,
            database_name=Path(self.settings.database_path).name,
        )
        log.info("SQL approval result from user: %s", approved)
        response_queue.put(approved)

    def _on_report_generated(self, report_data: dict[str, Any]) -> None:
        """Automatically preview the newly generated report in the workspace."""
        path = report_data.get("output_path")
        fmt = report_data.get("output_format", "PDF")
        if path:
            log.info("Loading newly generated report into workspace: %s", path)
            self.report_workspace.load_report(path, format_type=fmt)

    def _on_agent_finished(self, result: AgentRunResult) -> None:
        self.chat_view.set_processing_state(False)
        self.active_worker = None

        if result.final_message and result.status == "success":
            self.chat_view.add_assistant_message(result.final_message)
        elif result.status == "approval_denied":
            self.chat_view.add_system_message("🚫 SQL query execution was denied by the user. Report generation halted.")
        elif result.status == "cancelled":
            self.chat_view.add_system_message("⏹️ Workflow was cancelled by user.")
        elif result.status == "error":
            err = result.error or result.final_message or "An unexpected error occurred."
            self.chat_view.add_system_message(f"❌ <b>Error:</b> {err}")

    def _on_agent_error(self, err_msg: str) -> None:
        self.chat_view.set_processing_state(False)
        self.active_worker = None
        lower = err_msg.lower()
        if "cannot connect to ollama" in lower or "connection refused" in lower or "connecterror" in lower:
            friendly = "Cannot connect to Ollama. Please ensure Ollama is running (<code>ollama serve</code>)."
        elif "timed out" in lower:
            friendly = "The request timed out. Please try again or simplify your query."
        else:
            friendly = err_msg
        self.chat_view.add_system_message(f"❌ <b>Error:</b> {friendly}")

    def _on_agent_cancelled(self) -> None:
        self.chat_view.set_processing_state(False)
        self.active_worker = None

    def _cancel_active_worker(self) -> None:
        if self.active_worker and self.active_worker.isRunning():
            log.info("User requested cancellation of active worker thread.")
            self.active_worker.cancel()

    def _clear_conversation(self) -> None:
        log.info("Resetting conversation history in orchestrator.")
        self.orchestrator.reset_conversation()

    # -----------------------------------------------------------------
    # Dialog Openers
    # -----------------------------------------------------------------

    def _open_history_dialog(self) -> None:
        dialog = HistoryView(self.orchestrator.history_manager, parent=self)
        dialog.preview_report_requested.connect(
            lambda path, fmt: self.report_workspace.load_report(path, format_type=fmt)
        )
        dialog.exec()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsView(self.settings, parent=self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self, updated_settings: AppSettings) -> None:
        self.settings = updated_settings
        self._check_ollama_status()

    # -----------------------------------------------------------------
    # Lifecycle and Safe Shutdown
    # -----------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Ensure background threads and MCP subprocesses are cleanly terminated on exit."""
        if self.active_worker and self.active_worker.isRunning():
            log.info("Terminating active agent worker on application close...")
            self.active_worker.cancel()
            self.active_worker.wait(2000)

        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.wait(1000)

        # Cleanly close MCP client in background loop
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.orchestrator.close())
            loop.close()
        except Exception as exc:  # noqa: BLE001
            log.debug("Error during orchestrator close on shutdown: %s", exc)

        event.accept()
