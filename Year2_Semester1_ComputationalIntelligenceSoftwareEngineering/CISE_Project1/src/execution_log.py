"""Execution logging component for tracking training, inference, and rule evaluation.

Records events with timestamps, event categories, severity levels, and descriptive messages.
Can be rendered in the Streamlit UI or printed in console logs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
import time


@dataclass
class LogEvent:
    timestamp: float
    iso_time: str
    category: str  # e.g., DATA, PREPROCESSING, SPLIT, STRUCTURE, PARAMETERS, INFERENCE, EVALUATION, RULES, CLASSIFICATION
    level: str     # INFO, WARNING, ERROR, SUCCESS
    message: str
    details: Optional[dict[str, Any]] = None

    def format_line(self) -> str:
        return f"[{self.iso_time}] [{self.category}] [{self.level}] {self.message}"


class ExecutionLogger:
    """In-memory logger that tracks execution stages with timestamps and categories."""

    def __init__(self):
        self.events: List[LogEvent] = []
        self._start_time = time.time()

    def log(self, category: str, message: str, level: str = "INFO", details: Optional[dict[str, Any]] = None) -> LogEvent:
        now = time.time()
        iso = datetime.now().strftime("%H:%M:%S")
        event = LogEvent(
            timestamp=now,
            iso_time=iso,
            category=category.upper(),
            level=level.upper(),
            message=message,
            details=details,
        )
        self.events.append(event)
        return event

    def info(self, category: str, message: str, details: Optional[dict[str, Any]] = None) -> LogEvent:
        return self.log(category, message, level="INFO", details=details)

    def success(self, category: str, message: str, details: Optional[dict[str, Any]] = None) -> LogEvent:
        return self.log(category, message, level="SUCCESS", details=details)

    def warning(self, category: str, message: str, details: Optional[dict[str, Any]] = None) -> LogEvent:
        return self.log(category, message, level="WARNING", details=details)

    def error(self, category: str, message: str, details: Optional[dict[str, Any]] = None) -> LogEvent:
        return self.log(category, message, level="ERROR", details=details)

    def clear(self) -> None:
        self.events.clear()
        self._start_time = time.time()

    def to_text(self) -> str:
        return "\n".join(e.format_line() for e in self.events)

    def get_events(self, category: Optional[str] = None) -> List[LogEvent]:
        if category:
            cat_upper = category.upper()
            return [e for e in self.events if e.category == cat_upper]
        return list(self.events)


# Global default logger instance for shared use
global_logger = ExecutionLogger()
