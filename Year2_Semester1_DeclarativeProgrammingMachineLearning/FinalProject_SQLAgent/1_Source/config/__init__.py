"""Local Report SQL Agent - a local-first natural-language reporting agent for SQLite."""

from .settings import (
    ALLOWED_CONTEXT_WINDOWS,
    CONTEXT_WINDOW_DISPLAY_LABELS,
    DEFAULT_CONTEXT_WINDOW,
    AppSettings,
    load_settings,
    save_settings,
)

__version__ = "1.0.0"
APP_NAME = "Local Report SQL Agent"

__all__ = [
    "ALLOWED_CONTEXT_WINDOWS",
    "CONTEXT_WINDOW_DISPLAY_LABELS",
    "DEFAULT_CONTEXT_WINDOW",
    "AppSettings",
    "load_settings",
    "save_settings",
]

