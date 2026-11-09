"""Application startup and entrypoint for the Report SQL Agent desktop GUI."""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.main_window import MainWindow
from app.style import APP_STYLESHEET
from config.logging_setup import setup_logging
from config.paths import is_frozen, user_data_root
from config.settings import AppSettings, load_settings

log = logging.getLogger(__name__)


def _show_fatal_error_dialog(
    exc: BaseException | None,
    log_file_path: Path | None = None,
) -> None:
    """Display an immediate graphical modal dialog for fatal startup failures."""
    import os

    # In headless / test / offscreen environments, avoid blocking on modal dialogs
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        sys.stderr.write(f"Startup Error (headless): {exc}\n")
        return

    try:
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.instance() and QGuiApplication.platformName() == "offscreen":
            sys.stderr.write(f"Startup Error (offscreen): {exc}\n")
            return

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv[:1])

        tb_text = traceback.format_exc() if exc is not None else ""
        error_msg = str(exc) if exc is not None else "An unknown fatal startup error occurred."

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Report SQL Agent — Startup Error")
        msg_box.setText("A fatal error prevented the application from starting.")

        info_lines = [f"Error: {error_msg}"]
        if log_file_path:
            info_lines.append(f"\nDetailed logs have been written to:\n{log_file_path}")
        msg_box.setInformativeText("\n".join(info_lines))

        if tb_text and tb_text.strip() != "NoneType: None":
            msg_box.setDetailedText(tb_text)

        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    except Exception as dlg_exc:
        sys.stderr.write(f"Failed to display graphical error dialog: {dlg_exc}\n")


def _install_global_exception_handler(log_file_path: Path | None = None) -> None:
    """Install sys.excepthook to capture uncaught exceptions and log them persistently."""
    def _handle_uncaught_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        log.critical(
            "Uncaught top-level exception in application thread:",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        _show_fatal_error_dialog(exc_value, log_file_path)

    sys.excepthook = _handle_uncaught_exception


def main(argv: list[str] | None = None) -> int:
    """Launch the Report SQL Agent desktop graphical interface or child MCP server."""
    args = sys.argv if argv is None else argv

    # Handle MCP server subprocess execution mode (used when running as packaged app)
    if "--mcp-server" in args:
        from mcp_layer.server import run_stdio_server
        return run_stdio_server()

    log_file_path: Path | None = None
    try:
        # Stage 1: Load application configuration & configure logging
        settings = load_settings()
        log_file_path = setup_logging(settings)
        _install_global_exception_handler(log_file_path)

        log.info("Stage 1/5: Application configuration and logging initialized.")
        log.info("Executable: %s (frozen=%s)", sys.executable, is_frozen())

        # Stage 2: Initialize PySide6 Application
        log.info("Stage 2/5: Initializing PySide6 QApplication...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(args)

        app.setApplicationName("Report SQL Agent")
        app.setApplicationDisplayName("Local Report SQL Agent")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("UBB Advanced Agentic AI")

        # Stage 3: Apply global modern dark theme stylesheet
        log.info("Stage 3/5: Applying global application stylesheet...")
        app.setStyleSheet(APP_STYLESHEET)

        # Stage 4: Construct main window and agent orchestrator
        log.info("Stage 4/5: Constructing main window and initializing agent orchestrator...")
        window = MainWindow(settings)

        # Smoke-test mode: validates that GUI, orchestrator, and database migrations initialize cleanly
        if "--smoke-test" in args:
            log.info("Smoke test requested: MainWindow constructed cleanly. Closing window and exiting.")
            window.close()
            return 0

        # Stage 5: Display main window and run Qt event loop
        log.info("Stage 5/5: Displaying main GUI window and entering Qt event loop.")
        window.show()

        return app.exec()

    except KeyboardInterrupt:
        log.info("Application interrupted by user signal.")
        return 0
    except Exception as exc:
        log.critical("Fatal startup failure: %s", exc, exc_info=True)
        _show_fatal_error_dialog(exc, log_file_path)
        return 1


if __name__ == "__main__":
    sys.exit(main())

