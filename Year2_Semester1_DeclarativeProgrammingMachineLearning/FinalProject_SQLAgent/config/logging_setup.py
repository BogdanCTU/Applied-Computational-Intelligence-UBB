"""Logging configuration shared by the GUI process and the MCP server process."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .settings import AppSettings

FORMAT = "%(asctime)s | %(levelname)-7s | %(process)d | %(name)s | %(message)s"


def setup_logging(settings: AppSettings, process_name: str = "app", console: bool = True) -> Path:
    """Configure root logging with a rotating file handler.

    The MCP server uses stdio for protocol messages, so it must call this with
    ``console=False`` (or log to stderr only) to avoid corrupting stdout.
    """
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(settings.logging.file_name).stem
    log_file = log_dir / f"{stem}_{process_name}.log"

    level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(FORMAT)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        root.addHandler(stream)

    # Silence chatty third-party loggers
    for noisy in ("httpx", "httpcore", "mcp.server.lowlevel.server", "asyncio"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    logging.getLogger(__name__).info("Logging initialised (%s) -> %s", process_name, log_file)
    return log_file

