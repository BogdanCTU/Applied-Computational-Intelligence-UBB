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
    """Launch the Report SQL Agent desktop graphical interface."""
    args = sys.argv if argv is None else argv

    # 1. Load application configuration
    settings = load_settings()

    # 2. Configure logging
    setup_logging(settings.logging)
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

