"""Structured file and console logging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from source.config.settings import get_project_root

_CONFIGURED = False


def setup_logging(log_file: Optional[str | Path] = None, level: int = logging.INFO) -> logging.Logger:
    """Configure root logger for the research platform."""
    global _CONFIGURED
    root_logger = logging.getLogger("safety_research")
    root_logger.setLevel(level)

    if not _CONFIGURED:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        target = Path(log_file) if log_file else get_project_root() / "8_Build" / "logs" / "platform.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        _CONFIGURED = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a module-scoped child logger."""
    setup_logging()
    return logging.getLogger(f"safety_research.{name}")
