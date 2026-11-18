"""Structured logging setup with console and file output."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: Optional[Path] = None,
    log_file: str = "finetune.log",
    level: int = logging.INFO,
) -> None:
    """Configures application-wide logging."""
    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent.parent.parent / "8_Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_file

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance."""
    return logging.getLogger(name)
