"""Report filename sanitization, path-traversal protection, and history persistence.

All report files are constrained strictly inside the configured ``output_dir``.
Metadata for every generated report is persisted atomically to
``<output_dir>/report_history.json`` so both the MCP server subprocess and the
desktop GUI share a consistent, durable history.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

log = logging.getLogger(__name__)

HISTORY_FILENAME = "report_history.json"

# Windows & POSIX reserved names and unsafe filename characters
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


class ReportValidationError(ValueError):
    """Raised when report inputs (title, columns, rows, format) are invalid."""


class ReportSecurityError(PermissionError):
    """Raised when an output path attempts directory traversal or unsafe access."""


def sanitize_filename_stem(title: str, *, max_length: int = 60) -> str:
    """Convert an arbitrary report ``title`` into a safe cross-platform filename stem."""
    if "\x00" in (title or ""):
        raise ReportSecurityError("Report title must not contain NUL bytes")

    # Strip any path components or traversal tokens aggressively
    cleaned = (title or "").strip()
    cleaned = cleaned.replace("/", "_").replace("\\", "_").replace("..", "_")
    cleaned = _UNSAFE_CHARS_RE.sub("_", cleaned)
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned).strip("._-")

    if not cleaned:
        cleaned = "report"

    if cleaned.upper().split(".")[0] in _WINDOWS_RESERVED:
        cleaned = f"report_{cleaned}"

    cleaned = cleaned[:max_length].rstrip("._-")
    return cleaned.lower() or "report"


def resolve_safe_report_path(
    output_dir: str | Path,
    title: str,
    extension: str,
    *,
    now: datetime | None = None,
) -> Path:
    """Build a unique, sanitized path strictly inside ``output_dir``."""
    if "\x00" in str(output_dir):
        raise ReportSecurityError("Output directory contains NUL byte")

    ext = extension.lower().lstrip(".")
    if ext not in {"pdf", "csv"}:
        raise ReportValidationError(f"Unsupported report extension: '{extension}'")

    base_dir = Path(output_dir).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    stem = sanitize_filename_stem(title)
    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:6]
    filename = f"{stem}_{ts}_{short_id}.{ext}"

    candidate = (base_dir / filename).resolve()
    if not candidate.is_relative_to(base_dir):
        raise ReportSecurityError(
            f"Resolved path '{candidate}' escapes output directory '{base_dir}'"
        )
    return candidate


def normalize_tabular_data(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    *,
    max_rows: int = 100_000,
) -> tuple[list[str], list[list[Any]], bool]:
    """Validate and normalize ``columns`` and ``rows`` into ``(cols, list_of_lists, truncated)``."""
    if not isinstance(columns, (list, tuple)) or len(columns) == 0:
        raise ReportValidationError("columns must be a non-empty list of column names")

    clean_cols: list[str] = []
    for idx, col in enumerate(columns):
        if not isinstance(col, str) or not col.strip():
            raise ReportValidationError(
                f"Column name at index {idx} must be a non-empty string"
            )
        clean_cols.append(col.strip())

    if not isinstance(rows, (list, tuple)):
        raise ReportValidationError("rows must be a list of row records")

    ncols = len(clean_cols)
    truncated = len(rows) > max_rows
    effective_rows = rows[:max_rows] if truncated else rows

    normalized: list[list[Any]] = []
    for r_idx, row in enumerate(effective_rows):
        if isinstance(row, Mapping):
            normalized.append([row.get(col) for col in clean_cols])
        elif isinstance(row, (list, tuple)):
            if len(row) != ncols:
                raise ReportValidationError(
                    f"Row {r_idx} has {len(row)} value(s), expected {ncols} matching columns {clean_cols}"
                )
            normalized.append(list(row))
        else:
            raise ReportValidationError(
                f"Row {r_idx} must be a list, tuple, or object/dict; got {type(row).__name__}"
            )

    return clean_cols, normalized, truncated


# ---------------------------------------------------------------------------
# Metadata & persistent report history
# ---------------------------------------------------------------------------


@dataclass
class ReportMetadata:
    report_id: str
    title: str
    description: str
    user_request: str
    sql_query: str
    output_format: str  # "PDF" or "CSV"
    file_name: str
    output_path: str
    record_count: int
    total_input_records: int
    truncated: bool
    column_names: list[str]
    file_size_bytes: int
    created_at: str
    status: str  # "completed" or "failed"
    error_message: str | None = None
    page_count: int = 1
    sections_count: int = 1
    charts_requested: int = 0
    charts_rendered: int = 0
    tables_requested: int = 1
    tables_rendered: int = 1
    datasets_count: int = 1
    dataset_details: dict[str, int] = field(default_factory=dict)
    failed_components: list[dict[str, str]] = field(default_factory=list)
    completion_status: str = "complete"  # "complete" or "incomplete"
    warnings: list[str] = field(default_factory=list)
    requested_period: str = ""
    actual_data_period: str = ""
    historical_comparison_period: str = ""
    requested_period_has_data: bool = True
    available_data_range: dict[str, str] = field(default_factory=dict)
    kpis: list[dict[str, Any]] = field(default_factory=list)
    comparison_kpis: list[dict[str, Any]] = field(default_factory=list)
    omitted_analyses: list[str] = field(default_factory=list)
    executive_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        p = Path(self.output_path) if self.output_path else None
        exists = p.is_file() if p else False
        if not exists and self.file_name:
            # Fallback search in 5_Reports/generated/ or user data reports/
            from config.paths import resolve_path
            for cand in [
                resolve_path(f"5_Reports/generated/{self.file_name}"),
                resolve_path(f"reports/{self.file_name}"),
            ]:
                if cand.is_file():
                    exists = True
                    data["output_path"] = str(cand)
                    break
        data["file_exists"] = exists
        return data

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ReportMetadata":
        return cls(
            report_id=str(raw.get("report_id") or uuid.uuid4().hex),
            title=str(raw.get("title") or "Untitled Report"),
            description=str(raw.get("description") or ""),
            user_request=str(raw.get("user_request") or ""),
            sql_query=str(raw.get("sql_query") or ""),
            output_format=str(raw.get("output_format") or "PDF").upper(),
            file_name=str(raw.get("file_name") or ""),
            output_path=str(raw.get("output_path") or ""),
            record_count=int(raw.get("record_count") or 0),
            total_input_records=int(
                raw.get("total_input_records", raw.get("record_count") or 0)
            ),
            truncated=bool(raw.get("truncated", False)),
            column_names=[str(c) for c in (raw.get("column_names") or [])],
            file_size_bytes=int(raw.get("file_size_bytes") or 0),
            created_at=str(raw.get("created_at") or ""),
            status=str(raw.get("status") or "completed"),
            error_message=(
                str(raw["error_message"])
                if raw.get("error_message") is not None
                else None
            ),
            page_count=int(raw.get("page_count") or 1),
            sections_count=int(raw.get("sections_count") or 1),
            charts_requested=int(raw.get("charts_requested") or 0),
            charts_rendered=int(raw.get("charts_rendered") or 0),
            tables_requested=int(raw.get("tables_requested") or 1),
            tables_rendered=int(raw.get("tables_rendered") or 1),
            datasets_count=int(raw.get("datasets_count") or 1),
            dataset_details=dict(raw.get("dataset_details") or {}),
            failed_components=list(raw.get("failed_components") or []),
            completion_status=str(raw.get("completion_status") or "complete"),
            warnings=[str(w) for w in (raw.get("warnings") or [])],
            requested_period=str(raw.get("requested_period") or ""),
            actual_data_period=str(raw.get("actual_data_period") or ""),
            historical_comparison_period=str(raw.get("historical_comparison_period") or ""),
            requested_period_has_data=bool(raw.get("requested_period_has_data", True)),
            available_data_range=dict(raw.get("available_data_range") or {}),
            kpis=list(raw.get("kpis") or []),
            comparison_kpis=list(raw.get("comparison_kpis") or []),
            omitted_analyses=[str(o) for o in (raw.get("omitted_analyses") or [])],
            executive_summary=str(raw.get("executive_summary") or ""),
        )


_history_lock = threading.Lock()


class ReportHistoryManager:
    """Thread-safe, atomic JSON history store located in ``output_dir`` or parent ``5_Reports``."""

    def __init__(
        self,
        output_dir: str | Path,
        history_file: str | Path | None = None,
    ) -> None:
        self.output_dir = Path(output_dir).expanduser().resolve()
        if history_file is not None:
            self.history_file = Path(history_file).expanduser().resolve()
        elif (self.output_dir.parent / HISTORY_FILENAME).exists():
            # e.g., output_dir is 5_Reports/generated and 5_Reports/report_history.json exists
            self.history_file = self.output_dir.parent / HISTORY_FILENAME
        elif self.output_dir.name == "generated":
            self.history_file = self.output_dir.parent / HISTORY_FILENAME
        else:
            self.history_file = self.output_dir / HISTORY_FILENAME

    def record(self, entry: ReportMetadata) -> ReportMetadata:
        with _history_lock:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            entries = self._read_unlocked()
            entries.insert(0, entry)  # newest first
            self._write_unlocked(entries)
        log.info(
            "Recorded %s report '%s' (%d rows) -> %s",
            entry.output_format,
            entry.title,
            entry.record_count,
            entry.output_path,
        )
        return entry

    def list_reports(self, *, limit: int | None = None) -> list[ReportMetadata]:
        with _history_lock:
            entries = self._read_unlocked()
        return entries[:limit] if limit is not None else entries

    def get_report(self, report_id: str) -> ReportMetadata | None:
        for entry in self.list_reports():
            if entry.report_id == report_id:
                return entry
        return None

    def _read_unlocked(self) -> list[ReportMetadata]:
        if not self.history_file.is_file():
            return []
        try:
            payload = json.loads(self.history_file.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return []
            return [ReportMetadata.from_dict(item) for item in payload if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not read report history %s (%s)", self.history_file, exc)
            return []

    def _write_unlocked(self, entries: list[ReportMetadata]) -> None:
        tmp = self.history_file.with_suffix(".json.tmp")
        serialised = [asdict(e) for e in entries]
        tmp.write_text(json.dumps(serialised, indent=2), encoding="utf-8")
        tmp.replace(self.history_file)

