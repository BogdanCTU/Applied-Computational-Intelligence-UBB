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
    columns: Sequence[str] | None = None,
    rows: Sequence[Sequence[Any] | Mapping[str, Any]] | None = None,
    output_dir: str | Path,
    description: str = "",
    sql_query: str = "",
    user_request: str = "",
    max_rows: int = 100_000,
    record_history: bool = True,
    datasets: Mapping[str, Any] | None = None,
) -> ReportMetadata:
    """Write a UTF-8 CSV report inside ``output_dir`` and record metadata."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ReportValidationError("Report title must not be empty")
    if max_rows < 1:
        raise ReportValidationError("max_rows must be >= 1")

    now = datetime.now()
    output_path = resolve_safe_report_path(output_dir, clean_title, "csv", now=now)
    tmp_path = output_path.with_suffix(".csv.tmp")

    # Multi-dataset support: ensure no dataset is discarded
    if datasets and len(datasets) > 1:
        total_recs = 0
        all_cols: list[str] = []
        try:
            with tmp_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
                for ds_name, ds_data in datasets.items():
                    ds_cols = list(ds_data.get("columns", []))
                    ds_rows = list(ds_data.get("rows", []))
                    all_cols.extend(ds_cols)
                    total_recs += len(ds_rows)
                    writer.writerow([f"# Dataset: {ds_name}"])
                    if ds_cols:
                        writer.writerow(ds_cols)
                    for r in ds_rows:
                        if isinstance(r, dict):
                            writer.writerow([_format_csv_cell(r.get(c)) for c in ds_cols])
                        else:
                            writer.writerow([_format_csv_cell(v) for v in r])
                    writer.writerow([])
            tmp_path.replace(output_path)
        except BaseException:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
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
            record_count=total_recs,
            total_input_records=total_recs,
            truncated=False,
            column_names=list(dict.fromkeys(all_cols)),
            file_size_bytes=size_bytes,
            created_at=now.isoformat(timespec="seconds"),
            status="completed",
        )
        if record_history:
            ReportHistoryManager(output_dir).record(metadata)
        return metadata

    columns = columns or []
    rows = rows or []
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

