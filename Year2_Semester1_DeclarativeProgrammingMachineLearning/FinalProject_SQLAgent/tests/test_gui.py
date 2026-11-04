"""Comprehensive automated test suite for the PySide6 desktop GUI.

All tests run in headless offscreen mode without requiring a visible desktop display.
Mocked agent and MCP objects are used so tests do not depend on external daemons.
"""

from __future__ import annotations

import csv
import os
import queue
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

# Ensure offscreen platform before creating any Qt widget
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from agent import AgentEvent, AgentEventType, AgentOrchestrator, AgentRunResult
from app.dialogs.sql_approval_dialog import SqlApprovalDialog
from app.main_window import MainWindow
from app.models.csv_table_model import CsvTableModel
from app.views.chat_view import ChatView
from app.views.history_view import HistoryView
from app.views.settings_view import SettingsView
from app.widgets.message_widget import MessageWidget
from app.widgets.report_preview_widget import ReportPreviewWidget
from app.widgets.sql_preview_widget import SqlPreviewWidget
from app.workers.agent_worker import AgentWorker, OllamaCheckWorker
from config.settings import AppSettings
from reporting.report_manager import ReportHistoryManager, ReportMetadata


# ---------------------------------------------------------------------------
# Qt Application Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def gui_test_settings(tmp_path: Path) -> AppSettings:
    settings = AppSettings()
    settings.database.path = str(tmp_path / "test.db")
    settings.reports.output_dir = str(tmp_path / "reports")
    settings.ollama.host = "http://localhost:11434"
    settings.ollama.model = "qwen3.5:4b"
    return settings


# ---------------------------------------------------------------------------
# 1. CsvTableModel Tests
# ---------------------------------------------------------------------------


def test_csv_table_model_basic_and_capping(qapp: QApplication, tmp_path: Path) -> None:
    csv_file = tmp_path / "sample.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "revenue"])
        w.writerow([1, "Alpha", "1250.50"])
        w.writerow([2, "Beta", ""])  # Empty value

    model = CsvTableModel()
    ok = model.load_file(csv_file, max_rows=10)
    assert ok is True
    assert model.rowCount() == 2
    assert model.columnCount() == 3
    assert model.headers == ["id", "name", "revenue"]
    assert model.total_file_rows == 2
    assert model.is_truncated is False

    # Check data display
    idx_id = model.index(0, 0)
    assert model.data(idx_id, Qt.ItemDataRole.DisplayRole) == "1"
    # Right-aligned numeric check
    align = model.data(idx_id, Qt.ItemDataRole.TextAlignmentRole)
    assert align & Qt.AlignmentFlag.AlignRight

    # Empty value renders as dash
    idx_empty = model.index(1, 2)
    assert model.data(idx_empty, Qt.ItemDataRole.DisplayRole) == "—"

    # Header check
    assert model.headerData(1, Qt.Orientation.Horizontal) == "name"
    assert model.headerData(0, Qt.Orientation.Vertical) == "1"

    # Row capping test
    ok_capped = model.load_file(csv_file, max_rows=1)
    assert ok_capped is True
    assert model.rowCount() == 1
    assert model.total_file_rows == 2
    assert model.is_truncated is True

    model.clear()
    assert model.rowCount() == 0
    assert model.columnCount() == 0


# ---------------------------------------------------------------------------
# 2. SqlApprovalDialog Tests
# ---------------------------------------------------------------------------


def test_sql_approval_dialog_behavior(qapp: QApplication) -> None:
    sql = "SELECT customer_id, first_name FROM customers WHERE country = 'USA'"
    exp = "Filter customers by country USA"

    dialog = SqlApprovalDialog(sql, exp, database_name="test.db")

    # Default state is NOT approved
    assert dialog.is_approved is False

    # Check contents
    assert dialog.sql_query == sql
    assert dialog.explanation == exp
    assert dialog.database_name == "test.db"
    assert dialog.sql_edit.toPlainText() == sql
    assert dialog.exp_box.toPlainText() == exp

    # Test rejection slot
    dialog._on_reject()
    assert dialog.is_approved is False

    # Test approval slot
    dialog._on_approve()
    assert dialog.is_approved is True

    # Test reject() forces False
    dialog.reject()
    assert dialog.is_approved is False

    # Test copy button
    dialog._copy_sql_to_clipboard()
    cb = QApplication.clipboard()
    if cb:
        assert cb.text() == sql


# ---------------------------------------------------------------------------
# 3. ReportPreviewWidget Tests
# ---------------------------------------------------------------------------


def test_report_preview_widget_empty_pdf_and_csv(
    qapp: QApplication, tmp_path: Path
) -> None:
    widget = ReportPreviewWidget()
    assert widget.stack.currentIndex() == 0  # Placeholder page
    assert widget.current_format == "NONE"

    # Test missing file error
    missing_ok = widget.load_report(tmp_path / "does_not_exist.pdf")
    assert missing_ok is False
    assert widget.stack.currentIndex() == 3  # Error page

    # Test valid CSV load
    csv_file = tmp_path / "report.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as fh:
        fh.write("colA,colB\n1,2\n")

    ok_csv = widget.load_report(csv_file, format_type="CSV")
    assert ok_csv is True
    assert widget.current_format == "CSV"
    assert widget.stack.currentIndex() == 2  # CSV page
    assert widget.csv_controls.isHidden() is False
    assert widget.pdf_controls.isHidden() is True

    # Test valid PDF load (create minimal valid PDF header)
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    ok_pdf = widget.load_report(pdf_file, format_type="PDF")
    assert ok_pdf is True
    assert widget.current_format == "PDF"
    assert widget.stack.currentIndex() == 1  # PDF page
    assert widget.pdf_controls.isHidden() is False
    assert widget.csv_controls.isHidden() is True

    # Test navigation methods do not crash
    widget._prev_page()
    widget._next_page()
    widget._zoom_in()
    widget._zoom_out()
    widget._fit_to_width()
    widget._fit_to_page()

    # Reset to empty state
    widget.set_empty_state()
    assert widget.stack.currentIndex() == 0
    assert widget.current_format == "NONE"


# ---------------------------------------------------------------------------
# 4. MessageWidget and ChatView Tests
# ---------------------------------------------------------------------------


def test_message_widget_rendering(qapp: QApplication) -> None:
    # User message
    u_msg = MessageWidget(role="user", content="Hello world")
    assert u_msg.role == "user"
    assert "Hello world" in u_msg.body_label.text()

    # Assistant message with thinking
    a_msg = MessageWidget(
        role="assistant",
        content="Here is **bold** and `code`",
        thinking="Planning query",
    )
    assert a_msg.role == "assistant"
    assert hasattr(a_msg, "think_btn")
    assert a_msg.think_box.isHidden() is True
    a_msg.think_btn.setChecked(True)
    assert a_msg.think_box.isHidden() is False
    assert "<b>bold</b>" in a_msg.body_label.text()

    # System message
    s_msg = MessageWidget(role="system", content="Notice: reset")
    assert s_msg.role == "system"


def test_chat_view_interactions(qapp: QApplication) -> None:
    chat = ChatView()
    messages_submitted: list[str] = []
    chat.message_submitted.connect(messages_submitted.append)

    # Initial state
    assert chat.is_processing is False

    # Simulate user typing and clicking send
    chat.input_edit.setPlainText("Generate sales report")
    chat._on_send_clicked()
    assert messages_submitted == ["Generate sales report"]
    assert chat.input_edit.toPlainText() == ""

    # Processing state
    chat.set_processing_state(True, "Working...")
    assert chat.is_processing is True
    assert chat.btn_send.isEnabled() is False
    assert chat.progress_frame.isHidden() is False

    # Cancel clicked
    cancelled = False

    def on_cancel() -> None:
        nonlocal cancelled
        cancelled = True

    chat.cancellation_requested.connect(on_cancel)
    chat._on_cancel_clicked()
    assert cancelled is True

    # Clear chat
    chat.clear_chat()
    assert chat.messages_layout.count() == 1  # Only stretch remaining


# ---------------------------------------------------------------------------
# 5. Background AgentWorker Tests
# ---------------------------------------------------------------------------


def test_agent_worker_lifecycle(qapp: QApplication, gui_test_settings: AppSettings) -> None:
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    expected_res = AgentRunResult(
        status="success",
        final_message="Analysis completed.",
        executed_sql="SELECT 1",
    )
    mock_orchestrator.process_message = AsyncMock(return_value=expected_res)

    worker = AgentWorker(mock_orchestrator, "Analyze data")

    finished_results: list[AgentRunResult] = []
    worker.signals.finished.connect(finished_results.append)

    worker.start()
    while worker.isRunning():
        qapp.processEvents()
        QThread.msleep(10)
    qapp.processEvents()

    assert worker.isFinished() is True
    assert len(finished_results) == 1
    assert finished_results[0].final_message == "Analysis completed."
    mock_orchestrator.process_message.assert_called_once()


def test_agent_worker_handles_exception(
    qapp: QApplication, gui_test_settings: AppSettings
) -> None:
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    mock_orchestrator.process_message = AsyncMock(side_effect=RuntimeError("Ollama failed"))

    worker = AgentWorker(mock_orchestrator, "Analyze data")
    error_msg: list[str] = []
    worker.signals.error.connect(error_msg.append)

    worker.start()
    while worker.isRunning():
        qapp.processEvents()
        QThread.msleep(10)
    qapp.processEvents()

    assert worker.isFinished() is True
    assert len(error_msg) == 1
    assert "Ollama failed" in error_msg[0]


def test_worker_sql_approval_bridge(qapp: QApplication) -> None:
    """Verifies synchronous approval callback bridge over worker signals."""
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)

    async def fake_process(msg, approval_callback=None, progress_callback=None, cancel_event=None):
        if approval_callback:
            # Simulate worker pausing for human approval
            approved = approval_callback("SELECT * FROM sensitive", "Audit check")
            return AgentRunResult(
                status="success" if approved else "approval_denied",
                final_message="Approved" if approved else "Denied",
            )
        return AgentRunResult(status="error", final_message="No callback")

    mock_orchestrator.process_message = AsyncMock(side_effect=fake_process)

    worker = AgentWorker(mock_orchestrator, "Run query")

    # Connect approval requested to approve
    def mock_ui_approve(query: str, exp: str, q: queue.Queue):
        assert query == "SELECT * FROM sensitive"
        assert exp == "Audit check"
        q.put(True)  # User approves

    worker.signals.approval_requested.connect(mock_ui_approve)
    finished_results: list[AgentRunResult] = []
    worker.signals.finished.connect(finished_results.append)

    worker.start()
    while worker.isRunning():
        qapp.processEvents()
        QThread.msleep(10)
    qapp.processEvents()

    assert len(finished_results) == 1
    assert finished_results[0].status == "success"


# ---------------------------------------------------------------------------
# 6. HistoryView Tests
# ---------------------------------------------------------------------------


def test_history_view_population_and_actions(
    qapp: QApplication, tmp_path: Path
) -> None:
    hm = ReportHistoryManager(tmp_path / "reports")
    # Write a test report file
    report_file = tmp_path / "reports" / "test_report.pdf"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_bytes(b"%PDF-1.4...")

    meta = ReportMetadata.from_dict({
        "report_id": "rep_1",
        "title": "Revenue Summary",
        "output_format": "PDF",
        "output_path": str(report_file),
        "file_size_bytes": 1024,
        "record_count": 42,
    })
    hm.record(meta)

    dialog = HistoryView(hm)
    assert len(dialog._reports) == 1
    assert dialog.table.rowCount() == 1

    # Select row
    dialog.table.selectRow(0)
    assert dialog.btn_preview.isEnabled() is True
    assert dialog.btn_open_file.isEnabled() is True

    # Test preview signal emission
    preview_signal: list[tuple[str, str]] = []
    dialog.preview_report_requested.connect(
        lambda p, f: preview_signal.append((p, f))
    )
    dialog._on_preview_clicked()
    assert len(preview_signal) == 1
    assert preview_signal[0][0] == str(report_file)
    assert preview_signal[0][1] == "PDF"


# ---------------------------------------------------------------------------
# 7. SettingsView Tests
# ---------------------------------------------------------------------------


def test_settings_view_rejects_remote_hosts_and_persists(
    qapp: QApplication, gui_test_settings: AppSettings, tmp_path: Path
) -> None:
    settings_file = tmp_path / "settings.json"

    with patch("config.settings.settings_file", return_value=settings_file):
        dialog = SettingsView(gui_test_settings)

        # 1. Reject remote host
        dialog.edit_host.setText("http://evil-external-server.com:11434")
        with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit:
            dialog._on_save_clicked()
            mock_crit.assert_called_once()
            assert "Invalid Ollama Host" in mock_crit.call_args[0][1]

        # 2. Accept valid localhost and save
        dialog.edit_host.setText("http://localhost:11434")
        dialog.combo_model.setCurrentText("qwen3.5:4b")
        dialog.spin_max_rows.setValue(150)
        dialog.chk_require_approval.setChecked(True)

        saved_settings: list[AppSettings] = []
        dialog.settings_saved.connect(saved_settings.append)

        dialog._on_save_clicked()
        assert len(saved_settings) == 1
        assert saved_settings[0].database.max_result_rows == 150
        assert saved_settings[0].agent.require_sql_approval is True


# ---------------------------------------------------------------------------
# 8. MainWindow Integration Tests
# ---------------------------------------------------------------------------


def test_main_window_structure_and_safe_shutdown(
    qapp: QApplication, gui_test_settings: AppSettings
) -> None:
    mock_orchestrator = MagicMock(spec=AgentOrchestrator)
    mock_orchestrator.history_manager = ReportHistoryManager(gui_test_settings.output_dir)
    mock_orchestrator.close = AsyncMock()

    window = MainWindow(gui_test_settings, orchestrator=mock_orchestrator)
    assert window.centralWidget() is not None
    assert window.splitter.count() == 2

    # Left: ReportPreviewWidget, Right: ChatView
    assert isinstance(window.report_workspace, ReportPreviewWidget)
    assert isinstance(window.chat_view, ChatView)

    # Test status check handler
    window._on_ollama_status_checked(True, "0.40.14", ["qwen3.5:4b"])
    assert "Online" in window.status_pill.text()

    window._on_ollama_status_checked(False, "Connection refused", [])
    assert "Offline" in window.status_pill.text()

    # Test closing window triggers cleanup
    window.close()
    mock_orchestrator.close.assert_called_once()
