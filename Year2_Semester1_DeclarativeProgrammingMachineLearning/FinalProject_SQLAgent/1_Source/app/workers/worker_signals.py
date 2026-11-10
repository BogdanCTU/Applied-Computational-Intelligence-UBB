"""Qt Signal definitions for asynchronous agent operations and UI synchronization."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """Signals emitted by the background agent worker thread."""

    started = Signal()
    progress_event = Signal(object)  # AgentEvent
    activity_event = Signal(object)  # ActivityEvent
    thinking_update = Signal(str)  # Reasoning string
    sql_proposed = Signal(str, str)  # (sql_query, explanation)
    approval_requested = Signal(str, str, object)  # (sql_query, explanation, response_queue)
    report_generated = Signal(dict)  # report metadata dict
    finished = Signal(object)  # AgentRunResult
    error = Signal(str)  # error message string
    cancelled = Signal()


class OllamaCheckSignals(QObject):
    """Signals emitted during asynchronous Ollama status verification."""

    check_completed = Signal(bool, str, list)  # (is_online, version_or_error, installed_models)

