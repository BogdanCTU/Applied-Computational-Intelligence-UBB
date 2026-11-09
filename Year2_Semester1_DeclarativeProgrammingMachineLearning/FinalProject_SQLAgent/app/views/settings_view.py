"""Settings dialog allowing inspection and persistence of application configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.workers.agent_worker import OllamaCheckWorker
from config.settings import (
    ALLOWED_CONTEXT_WINDOWS,
    CONTEXT_WINDOW_DISPLAY_LABELS,
    DEFAULT_CONTEXT_WINDOW,
    LOCAL_HOSTS,
    AppSettings,
    save_settings,
)

log = logging.getLogger(__name__)


class SettingsView(QDialog):
    """Configuration management dialog with connection test and local persistence."""

    settings_saved = Signal(object)  # Emits updated AppSettings

    def __init__(
        self,
        settings: AppSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._check_worker: OllamaCheckWorker | None = None

        self.setWindowTitle("Application Settings")
        self.setMinimumSize(660, 560)
        self.resize(700, 720)

        self._init_ui()
        self._load_from_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header banner
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title_lbl = QLabel("⚙️ Application Settings")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        desc_lbl = QLabel("Configure local Ollama connectivity, SQL governance rules, and report storage.")
        desc_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_box.addWidget(title_lbl)
        header_box.addWidget(desc_lbl)
        layout.addLayout(header_box)

        # -------------------------------------------------------------
        # Scrollable Configuration Container
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Local Ollama Settings Group
        # -------------------------------------------------------------
        grp_ollama = QGroupBox("Local Ollama Configuration")
        form_ollama = QFormLayout(grp_ollama)
        form_ollama.setContentsMargins(14, 20, 14, 14)
        form_ollama.setVerticalSpacing(12)
        form_ollama.setHorizontalSpacing(16)
        form_ollama.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Host input
        self.edit_host = QLineEdit()
        self.edit_host.setMinimumHeight(32)
        self.edit_host.setPlaceholderText("http://localhost:11434")
        form_ollama.addRow("Ollama Endpoint:", self.edit_host)

        # Model input & detection
        model_row = QHBoxLayout()
        model_row.setSpacing(8)
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)
        self.combo_model.setMinimumHeight(32)
        self.combo_model.addItem("qwen3.5:4b")
        model_row.addWidget(self.combo_model, stretch=1)

        self.btn_test_conn = QPushButton("Test Connection")
        self.btn_test_conn.setMinimumHeight(32)
        self.btn_test_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_conn.clicked.connect(self._on_test_connection)
        model_row.addWidget(self.btn_test_conn)
        form_ollama.addRow("Model Name:", model_row)

        # Connection status feedback label
        self.lbl_conn_status = QLabel("Click 'Test Connection' to verify local Ollama.")
        self.lbl_conn_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        form_ollama.addRow("", self.lbl_conn_status)

        # Timeout & Keep-alive
        self.spin_request_timeout = QSpinBox()
        self.spin_request_timeout.setMinimumHeight(32)
        self.spin_request_timeout.setRange(5, 600)
        self.spin_request_timeout.setSuffix(" seconds")
        form_ollama.addRow("Request Timeout:", self.spin_request_timeout)

        self.combo_tool_mode = QComboBox()
        self.combo_tool_mode.setMinimumHeight(32)
        self.combo_tool_mode.addItems(["auto", "native", "json"])
        form_ollama.addRow("Tool Mode Protocol:", self.combo_tool_mode)

        # Context window selection (32K, 64K, 128K Default, 256K)
        self.combo_context_window = QComboBox()
        self.combo_context_window.setMinimumHeight(32)
        self.combo_context_window.addItem("32K (32,768 tokens)", 32768)
        self.combo_context_window.addItem("64K (65,536 tokens)", 65536)
        self.combo_context_window.addItem("128K (131,072 tokens) - Default", 131072)
        self.combo_context_window.addItem("256K (262,144 tokens)", 262144)
        form_ollama.addRow("Agent Context Window:", self.combo_context_window)

        content_layout.addWidget(grp_ollama)

        # -------------------------------------------------------------
        # 2. Database & SQL Governance Group
        # -------------------------------------------------------------
        grp_db = QGroupBox("Database && Security Controls")
        form_db = QFormLayout(grp_db)
        form_db.setContentsMargins(14, 20, 14, 14)
        form_db.setVerticalSpacing(12)
        form_db.setHorizontalSpacing(16)
        form_db.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.edit_db_path = QLineEdit()
        self.edit_db_path.setMinimumHeight(32)
        self.edit_db_path.setReadOnly(True)
        form_db.addRow("Database Path:", self.edit_db_path)

        self.spin_query_timeout = QSpinBox()
        self.spin_query_timeout.setMinimumHeight(32)
        self.spin_query_timeout.setRange(1, 120)
        self.spin_query_timeout.setSuffix(" seconds")
        form_db.addRow("Query Timeout:", self.spin_query_timeout)

        self.spin_max_rows = QSpinBox()
        self.spin_max_rows.setMinimumHeight(32)
        self.spin_max_rows.setRange(10, 50000)
        self.spin_max_rows.setSingleStep(50)
        form_db.addRow("Max Query Rows:", self.spin_max_rows)

        self.chk_require_approval = QCheckBox("Mandatory SQL Approval (Prompts user before query execution)")
        self.chk_require_approval.setCursor(Qt.CursorShape.PointingHandCursor)
        form_db.addRow("", self.chk_require_approval)

        self.spin_max_iterations = QSpinBox()
        self.spin_max_iterations.setMinimumHeight(32)
        self.spin_max_iterations.setRange(2, 100)
        form_db.addRow("Max Agent Iterations:", self.spin_max_iterations)

        content_layout.addWidget(grp_db)

        # -------------------------------------------------------------
        # 3. Reports & Storage Group
        # -------------------------------------------------------------
        grp_reports = QGroupBox("Reports Storage")
        form_reports = QFormLayout(grp_reports)
        form_reports.setContentsMargins(14, 20, 14, 14)
        form_reports.setVerticalSpacing(12)
        form_reports.setHorizontalSpacing(16)
        form_reports.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setMinimumHeight(32)
        dir_row.addWidget(self.edit_output_dir, stretch=1)

        btn_browse_dir = QPushButton("Browse...")
        btn_browse_dir.setMinimumHeight(32)
        btn_browse_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_dir.clicked.connect(self._on_browse_output_dir)
        dir_row.addWidget(btn_browse_dir)
        form_reports.addRow("Reports Output Directory:", dir_row)

        self.combo_page_size = QComboBox()
        self.combo_page_size.setMinimumHeight(32)
        self.combo_page_size.addItems(["A4", "LETTER"])
        form_reports.addRow("PDF Page Size:", self.combo_page_size)

        content_layout.addWidget(grp_reports)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # -------------------------------------------------------------
        # 4. Action Buttons
        # -------------------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setObjectName("primary_button")
        self.btn_save.setProperty("primary", True)
        self.btn_save.setMinimumHeight(34)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_row.addWidget(self.btn_save)

        layout.addLayout(btn_row)

    def _load_from_settings(self) -> None:
        """Populate controls from current AppSettings."""
        self.edit_host.setText(self.settings.ollama.host)

        model_name = self.settings.ollama.model
        if self.combo_model.findText(model_name) == -1:
            self.combo_model.addItem(model_name)
        self.combo_model.setCurrentText(model_name)

        self.spin_request_timeout.setValue(int(self.settings.ollama.request_timeout_s))
        self.combo_tool_mode.setCurrentText(self.settings.ollama.tool_mode)

        # Populate context window
        current_ctx = getattr(
            self.settings.agent, "agent_context_window", DEFAULT_CONTEXT_WINDOW
        )
        ctx_idx = self.combo_context_window.findData(current_ctx)
        if ctx_idx != -1:
            self.combo_context_window.setCurrentIndex(ctx_idx)
        else:
            self.combo_context_window.setCurrentIndex(2)  # 128K default

        self.edit_db_path.setText(str(self.settings.database_path))
        self.spin_query_timeout.setValue(int(self.settings.database.query_timeout_s))
        self.spin_max_rows.setValue(int(self.settings.database.max_result_rows))
        self.chk_require_approval.setChecked(self.settings.agent.require_sql_approval)
        self.spin_max_iterations.setValue(int(self.settings.agent.max_iterations))

        self.edit_output_dir.setText(str(self.settings.output_dir))
        self.combo_page_size.setCurrentText(self.settings.reports.page_size.upper())

    def _on_browse_output_dir(self) -> None:
        current_dir = self.edit_output_dir.text().strip() or str(self.settings.output_dir)
        selected = QFileDialog.getExistingDirectory(self, "Select Reports Output Directory", current_dir)
        if selected:
            self.edit_output_dir.setText(selected)

    def _on_test_connection(self) -> None:
        """Run an asynchronous check against Ollama."""
        host = self.edit_host.text().strip()
        parsed = urlparse(host)
        hostname = (parsed.hostname or "").lower()

        if hostname not in LOCAL_HOSTS:
            self.lbl_conn_status.setText("❌ Remote hosts are prohibited. Must be localhost or 127.0.0.1.")
            self.lbl_conn_status.setStyleSheet("color: #ef4444; font-size: 11px;")
            return

        self.btn_test_conn.setEnabled(False)
        self.lbl_conn_status.setText("Checking connection to Ollama...")
        self.lbl_conn_status.setStyleSheet("color: #60a5fa; font-size: 11px;")

        # Clone settings with current input host
        test_settings = AppSettings()
        test_settings.ollama.host = host

        self._check_worker = OllamaCheckWorker(test_settings, parent=self)
        self._check_worker.signals.check_completed.connect(self._on_connection_test_completed)
        self._check_worker.start()

    def _on_connection_test_completed(
        self, is_online: bool, ver_or_err: str, installed_models: list[str]
    ) -> None:
        self.btn_test_conn.setEnabled(True)
        if is_online:
            # Update models list if any found
            current_choice = self.combo_model.currentText().strip()
            self.combo_model.clear()
            for m in installed_models:
                self.combo_model.addItem(m)
            if self.combo_model.findText(current_choice) != -1:
                self.combo_model.setCurrentText(current_choice)
            elif current_choice:
                self.combo_model.addItem(current_choice)
                self.combo_model.setCurrentText(current_choice)

            wanted = self.combo_model.currentText().strip()
            has_wanted = any(wanted in m for m in installed_models)
            model_note = f" (Model '{wanted}' found)" if has_wanted else f" (Model '{wanted}' NOT found in Ollama!)"

            self.lbl_conn_status.setText(f"✅ Connected to Ollama {ver_or_err}{model_note}")
            self.lbl_conn_status.setStyleSheet("color: #10b981; font-size: 11px;")
        else:
            self.lbl_conn_status.setText(f"❌ Failed to connect: {ver_or_err}")
            self.lbl_conn_status.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _on_save_clicked(self) -> None:
        """Validate input values and save updated settings to settings.json."""
        host = self.edit_host.text().strip()
        parsed = urlparse(host)
        hostname = (parsed.hostname or "").lower()

        if hostname not in LOCAL_HOSTS:
            QMessageBox.critical(
                self,
                "Invalid Ollama Host",
                "For security and privacy, only local hosts ('localhost', '127.0.0.1') are allowed.\n"
                "External or remote hosts are strictly forbidden.",
            )
            return

        model = self.combo_model.currentText().strip()
        if not model:
            QMessageBox.warning(self, "Invalid Model", "Model name cannot be empty.")
            return

        output_dir = self.edit_output_dir.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Invalid Directory", "Output directory cannot be empty.")
            return

        selected_ctx = self.combo_context_window.currentData()
        if selected_ctx not in ALLOWED_CONTEXT_WINDOWS:
            selected_ctx = DEFAULT_CONTEXT_WINDOW

        # Update settings object
        self.settings.ollama.host = host
        self.settings.ollama.model = model
        self.settings.ollama.request_timeout_s = float(self.spin_request_timeout.value())
        self.settings.ollama.tool_mode = self.combo_tool_mode.currentText()
        self.settings.agent.agent_context_window = int(selected_ctx)
        self.settings.ollama.num_ctx = int(selected_ctx)

        self.settings.database.query_timeout_s = float(self.spin_query_timeout.value())
        self.settings.database.max_result_rows = int(self.spin_max_rows.value())
        self.settings.agent.require_sql_approval = self.chk_require_approval.isChecked()
        self.settings.agent.max_iterations = int(self.spin_max_iterations.value())

        self.settings.reports.output_dir = output_dir
        self.settings.reports.page_size = self.combo_page_size.currentText()

        # Persist to disk
        try:
            save_settings(self.settings)
            log.info("Settings saved successfully to settings.json")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Failed", f"Failed to save settings: {exc}")
            return

        self.settings_saved.emit(self.settings)
        self.accept()

