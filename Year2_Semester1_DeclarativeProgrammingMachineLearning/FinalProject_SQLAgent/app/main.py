"""Application startup and entrypoint for the Report SQL Agent desktop GUI."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.style import APP_STYLESHEET
from config.logging_setup import setup_logging
from config.settings import AppSettings, load_settings

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Launch the Report SQL Agent desktop graphical interface or child MCP server."""
    args = sys.argv if argv is None else argv

    # Handle MCP server subprocess execution mode (used when running as packaged app)
    if "--mcp-server" in args:
        from mcp_layer.server import run_stdio_server
        return run_stdio_server()

    # 1. Load application configuration
    settings = load_settings()

    # 2. Configure logging
    setup_logging(settings)
    log.info("Starting Report SQL Agent Desktop Application...")

    # 3. Initialize PySide6 Application
    # High-DPI scaling is enabled by default in Qt 6
    app = QApplication.instance()
    if app is None:
        app = QApplication(args)

    app.setApplicationName("Report SQL Agent")
    app.setApplicationDisplayName("Local Report SQL Agent")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("UBB Advanced Agentic AI")

    # Apply global modern dark theme stylesheet
    app.setStyleSheet(APP_STYLESHEET)

    # 4. Construct and display main window
    window = MainWindow(settings)
    window.show()

    # 5. Run event loop
    try:
        return app.exec()
    except KeyboardInterrupt:
        log.info("Application interrupted by user signal.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

