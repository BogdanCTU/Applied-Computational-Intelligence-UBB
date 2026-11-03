"""UTF-8 CSV report generator.

Consumes structured column names and tabular rows only — never accesses SQLite
or executes SQL queries directly.
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .report_manager import (
    ReportHistoryManager,
    ReportMetadata,
    ReportValidationError,
    normalize_tabular_data,
    resolve_safe_report_path,
)


def _format_csv_cell(value: Any) -> Any:
    """Convert SQL NULL (``None``) to empty CSV cell while preserving primitives."""
    if value is None:
        return ""
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def generate_csv_file(
    *,
    title: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    output_dir: str | Path,
    description: str = "",
    sql_query: str = "",
    user_request: str = "",
    max_rows: int = 100_000,
    record_history: bool = True,
) -> ReportMetadata:
    """Write a UTF-8 CSV report inside ``output_dir`` and record metadata."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ReportValidationError("Report title must not be empty")
    if max_rows < 1:
        raise ReportValidationError("max_rows must be >= 1")

    total_input = len(rows) if isinstance(rows, (list, tuple)) else 0
    clean_cols, norm_rows, truncated = normalize_tabular_data(
        columns, rows, max_rows=max_rows
    )

    now = datetime.now()
    output_path = resolve_safe_report_path(output_dir, clean_title, "csv", now=now)
    tmp_path = output_path.with_suffix(".csv.tmp")

    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(
                fh,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            writer.writerow(clean_cols)
            for row in norm_rows:
                writer.writerow([_format_csv_cell(v) for v in row])
        tmp_path.replace(output_path)
    except BaseException:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    size_bytes = output_path.stat().st_size
    metadata = ReportMetadata(
        report_id=uuid.uuid4().hex,
        title=clean_title,
        description=(description or "").strip(),
        user_request=(user_request or description or clean_title).strip(),
        sql_query=(sql_query or "").strip(),
        output_format="CSV",
        file_name=output_path.name,
        output_path=str(output_path),
        record_count=len(norm_rows),
        total_input_records=total_input,
        truncated=truncated,
        column_names=clean_cols,
        file_size_bytes=size_bytes,
        created_at=now.isoformat(timespec="seconds"),
        status="completed",
    )

    if record_history:
        ReportHistoryManager(output_dir).record(metadata)

    return metadata

