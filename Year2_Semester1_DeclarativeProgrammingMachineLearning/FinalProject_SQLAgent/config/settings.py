"""Centralised application configuration.

Configuration is loaded in three layers (later layers win):

1. Built-in defaults (the dataclasses below).
2. ``settings.json`` in the application root.
3. Environment variables (``REPORT_AGENT_*``), useful for CI and packaging.

Settings modified in the GUI are persisted back to ``settings.json``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .paths import app_root, is_frozen, resolve_path, user_data_root

log = logging.getLogger(__name__)

SETTINGS_FILENAME = "settings.json"

# Hosts considered "local". The application refuses to talk to any other host
# so that prompts and database content never leave the machine.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


@dataclass
class OllamaSettings:
    host: str = "http://localhost:11434"
    model: str = "qwen3.5:4b"
    temperature: float = 0.1
    top_p: float = 0.9
    num_ctx: int = 8192
    request_timeout_s: float = 600.0
    stream: bool = True
    keep_alive: str = "10m"
    # "auto" = probe native tool calling and fall back to JSON protocol,
    # "native" = always native, "json" = always JSON fallback protocol.
    tool_mode: str = "auto"


@dataclass
class DatabaseSettings:
    path: str = "data/ecommerce.db"
    max_result_rows: int = 1000
    llm_preview_rows: int = 50
    query_timeout_s: float = 120.0


@dataclass
class AgentSettings:
    max_iterations: int = 12
    max_tool_calls: int = 24
    max_sql_retries: int = 3
    max_history_messages: int = 30
    require_sql_approval: bool = True
    system_prompt_override: str = ""


@dataclass
class ReportSettings:
    output_dir: str = "reports"
    page_size: str = "A4"  # "A4" or "LETTER"
    max_pdf_rows: int = 5000
    max_report_rows: int = 100000
    include_sql_in_pdf: bool = True


@dataclass
class LoggingSettings:
    level: str = "INFO"
    directory: str = "logs"
    file_name: str = "report_agent.log"


@dataclass
class AppSettings:
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    reports: ReportSettings = field(default_factory=ReportSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    # ------------------------------------------------------------------ paths
    @property
    def database_path(self) -> Path:
        return resolve_path(self.database.path)

    @property
    def output_dir(self) -> Path:
        return resolve_path(self.reports.output_dir)

    @property
    def log_dir(self) -> Path:
        return resolve_path(self.logging.directory)

    # ---------------------------------------------------------- serialisation
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        settings = cls()
        _merge_into(settings, data or {})
        return settings

    # -------------------------------------------------------------- validation
    def validate(self) -> list[str]:
        """Return a list of human-readable validation errors (empty = valid)."""
        errors: list[str] = []
        parsed = urlparse(self.ollama.host)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            errors.append("Ollama host must be a URL such as http://localhost:11434")
        elif parsed.hostname not in LOCAL_HOSTS:
            errors.append("Ollama host must be local (localhost / 127.0.0.1) for data privacy")
        if not self.ollama.model.strip():
            errors.append("Model name must not be empty")
        if self.ollama.tool_mode not in {"auto", "native", "json"}:
            errors.append("Tool mode must be 'auto', 'native' or 'json'")
        if not self.database.path.strip():
            errors.append("Database path must not be empty")
        if not 1 <= self.database.max_result_rows <= 100_000:
            errors.append("Maximum SQL result rows must be between 1 and 100000")
        if not 0.5 <= self.database.query_timeout_s <= 600:
            errors.append("SQL execution timeout must be between 0.5 and 600 seconds")
        if not 1 <= self.agent.max_iterations <= 50:
            errors.append("Maximum agent iterations must be between 1 and 50")
        if not self.reports.output_dir.strip():
            errors.append("Reports output directory must not be empty")
        if self.reports.page_size.upper() not in {"A4", "LETTER"}:
            errors.append("Page size must be A4 or LETTER")
        return errors


# Environment variable overrides: VAR -> (section, key)
ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "REPORT_AGENT_OLLAMA_HOST": ("ollama", "host"),
    "REPORT_AGENT_OLLAMA_MODEL": ("ollama", "model"),
    "REPORT_AGENT_TOOL_MODE": ("ollama", "tool_mode"),
    "REPORT_AGENT_REQUEST_TIMEOUT": ("ollama", "request_timeout_s"),
    "REPORT_AGENT_DB_PATH": ("database", "path"),
    "REPORT_AGENT_OUTPUT_DIR": ("reports", "output_dir"),
    "REPORT_AGENT_MAX_ROWS": ("database", "max_result_rows"),
    "REPORT_AGENT_QUERY_TIMEOUT": ("database", "query_timeout_s"),
    "REPORT_AGENT_MAX_ITERATIONS": ("agent", "max_iterations"),
    "REPORT_AGENT_REQUIRE_APPROVAL": ("agent", "require_sql_approval"),
    "REPORT_AGENT_LOG_LEVEL": ("logging", "level"),
}


def _coerce(value: Any, current: Any) -> Any:
    """Coerce ``value`` to the type of ``current`` (bool/int/float/str)."""
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if isinstance(current, int):
        return int(value)
    if isinstance(current, float):
        return float(value)
    if isinstance(current, str):
        return str(value)
    return value


def _merge_into(target: Any, data: dict[str, Any]) -> None:
    """Recursively merge ``data`` into dataclass ``target`` ignoring unknown keys."""
    names = {f.name for f in fields(target)}
    for key, value in data.items():
        if key not in names:
            log.warning("Ignoring unknown setting '%s'", key)
            continue
        current = getattr(target, key)
        if is_dataclass(current) and isinstance(value, dict):
            _merge_into(current, value)
        else:
            try:
                setattr(target, key, _coerce(value, current))
            except (TypeError, ValueError):
                log.warning("Invalid value for setting '%s': %r (keeping %r)", key, value, current)


def _apply_env(settings: AppSettings) -> None:
    for var, (section, key) in ENV_OVERRIDES.items():
        if var in os.environ:
            _merge_into(getattr(settings, section), {key: os.environ[var]})


def settings_file() -> Path:
    if is_frozen():
        return user_data_root() / SETTINGS_FILENAME
    return app_root() / SETTINGS_FILENAME


_lock = threading.Lock()


def load_settings(path: Path | None = None, apply_env: bool = True) -> AppSettings:
    """Load settings from JSON (if present) and apply environment overrides."""
    path = path or settings_file()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("Could not read %s (%s); using defaults", path, exc)
    settings = AppSettings.from_dict(data)
    if apply_env:
        _apply_env(settings)
    return settings


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    """Validate and persist settings to JSON atomically.

    Raises ``ValueError`` with all validation messages if settings are invalid.
    """
    errors = settings.validate()
    if errors:
        raise ValueError("; ".join(errors))
    path = path or settings_file()
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)
    log.info("Settings saved to %s", path)
    return path

