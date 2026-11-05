"""Streaming, transactional dataset importer for SQLite.

Supports importing from:
* A directory containing ``.csv`` files.
* A ``.zip`` archive containing ``.csv`` files (streamed directly from the ZIP
  without extracting copies to disk).
* One or more individual ``.csv`` file paths.
* A compatible ``.sqlite`` / ``.db`` file (copied table-by-table in batches
  through a read-only immutable source connection).

Key guarantees:
* Source files are strictly read-only and never modified.
* Existing target databases are never overwritten unless ``overwrite=True``.
* Schema (columns, SQLite affinities, ``NOT NULL``, primary keys, foreign keys,
  topological load order, and analytical indexes) is discovered dynamically
  without hardcoding table or column names.
* Inserts stream in configurable batches inside explicit transactions/savepoints
  so memory stays bounded and failed imports never leave a partial database.
* Malformed records are never silently discarded: each bad record is logged and
  recorded in ``ImportSummary.rejected_records`` (or aborts the import when
  ``strict=True``).
"""

from __future__ import annotations

import csv
import io
import logging
import math
import os
import re
import sqlite3
import time
import zipfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from .connection import (
    connect_readonly,
    connect_readwrite,
    is_valid_identifier,
    quote_identifier,
)
from .schema_inspector import (
    DatabaseComparison,
    IntegrityReport,
    compare_databases,
    inspect_schema,
    validate_database_integrity,
)

log = logging.getLogger(__name__)

_INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_DEC_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?$")

MAX_CAPTURED_REJECTED_RECORDS = 500


class DatasetImportError(RuntimeError):
    """Raised when dataset discovery, schema creation, or strict import fails."""


# ---------------------------------------------------------------------------
# Specification & reporting dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ColumnSpec:
    name: str
    sql_type: str  # "INTEGER", "NUMERIC", or "TEXT"
    not_null: bool
    is_primary_key: bool = False


@dataclass(frozen=True)
class ForeignKeySpec:
    from_column: str
    to_table: str
    to_column: str


@dataclass
class TableSpec:
    name: str
    columns: list[ColumnSpec]
    foreign_keys: list[ForeignKeySpec] = field(default_factory=list)
    indexes: list[tuple[str, list[str]]] = field(default_factory=list)

    def create_table_sql(self) -> str:
        col_defs: list[str] = []
        for col in self.columns:
            parts = [quote_identifier(col.name), col.sql_type]
            if col.is_primary_key:
                parts.append("PRIMARY KEY")
                if col.sql_type != "INTEGER":
                    parts.append("NOT NULL")
            elif col.not_null:
                parts.append("NOT NULL")
            col_defs.append(" ".join(parts))

        for fk in self.foreign_keys:
            col_defs.append(
                f"FOREIGN KEY ({quote_identifier(fk.from_column)}) "
                f"REFERENCES {quote_identifier(fk.to_table)} "
                f"({quote_identifier(fk.to_column)})"
            )
        joined = ",\n    ".join(col_defs)
        return f"CREATE TABLE {quote_identifier(self.name)} (\n    {joined}\n)"


@dataclass
class RejectedRecord:
    table: str
    line_number: int
    reason: str
    raw_preview: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableImportResult:
    table_name: str
    source_label: str
    imported_rows: int
    rejected_rows: int
    indexes_created: list[str]
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImportSummary:
    source_description: str
    target_database: str
    tables: list[TableImportResult]
    total_imported_rows: int
    total_rejected_rows: int
    rejected_records: list[RejectedRecord]
    rejected_records_truncated: bool
    duration_s: float
    integrity: IntegrityReport
    reference_comparison: DatabaseComparison | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_description": self.source_description,
            "target_database": self.target_database,
            "tables": [t.to_dict() for t in self.tables],
            "total_imported_rows": self.total_imported_rows,
            "total_rejected_rows": self.total_rejected_rows,
            "rejected_records": [r.to_dict() for r in self.rejected_records],
            "rejected_records_truncated": self.rejected_records_truncated,
            "duration_s": self.duration_s,
            "integrity": self.integrity.to_dict(),
            "reference_comparison": (
                self.reference_comparison.to_dict()
                if self.reference_comparison is not None
                else None
            ),
        }

    def format_report(self) -> str:
        """Render a human-readable Milestone 2 import & validation report."""
        lines: list[str] = [
            "============================================================",
            "DATASET IMPORT SUMMARY",
            "============================================================",
            f"Source          : {self.source_description}",
            f"Target database : {self.target_database}",
            f"Duration        : {self.duration_s:.2f}s",
            f"Tables imported : {len(self.tables)}",
            f"Total rows      : {self.total_imported_rows:,}",
            f"Rejected rows   : {self.total_rejected_rows:,}",
            "",
            "Per-table breakdown:",
        ]
        for tbl in self.tables:
            idx_note = (
                f"{len(tbl.indexes_created)} indexes"
                if tbl.indexes_created
                else "no extra indexes"
            )
            lines.append(
                f"  - {tbl.table_name:<15} : {tbl.imported_rows:>9,} imported | "
                f"{tbl.rejected_rows:>4} rejected | {idx_note} | {tbl.duration_s:.2f}s"
            )

        if self.rejected_records:
            lines.append("")
            lines.append("Malformed / rejected records:")
            for rec in self.rejected_records[:20]:
                lines.append(
                    f"  ! {rec.table} line {rec.line_number}: {rec.reason} -> {rec.raw_preview}"
                )
            if len(self.rejected_records) > 20 or self.rejected_records_truncated:
                lines.append(
                    f"  ... ({self.total_rejected_rows} total rejected records; see application log)"
                )

        lines.extend(
            [
                "",
                "Database validation:",
                f"  - SQLite integrity_check   : {'PASS' if self.integrity.integrity_ok else 'FAIL'} "
                f"({', '.join(self.integrity.integrity_messages)})",
                f"  - Foreign key enforcement  : {'PASS (0 violations)' if self.integrity.foreign_keys_ok else f'FAIL ({len(self.integrity.foreign_key_violations)} violations)'}",
            ]
        )

        if self.reference_comparison is not None:
            cmp = self.reference_comparison
            lines.extend(
                [
                    "",
                    f"Reference comparison vs {cmp.reference_path}:",
                    f"  - Structure & row parity   : {'MATCH' if cmp.matches_structure_and_counts else 'DISCREPANCIES FOUND'}",
                    f"  - Target vs Reference rows : {cmp.total_target_rows:,} vs {cmp.total_reference_rows:,}",
                    f"  - Missing tables           : {cmp.missing_tables or 'none'}",
                    f"  - Extra tables             : {cmp.extra_tables or 'none'}",
                    f"  - Row count discrepancies  : {cmp.row_count_differences or 'none'}",
                    f"  - Column/PK discrepancies  : {cmp.column_differences or 'none'}",
                    f"  - Foreign key discrepancies: {cmp.foreign_key_differences or 'none'}",
                ]
            )
            if cmp.declared_type_notes:
                lines.append(
                    f"  - Declared type notes      : {len(cmp.declared_type_notes)} table(s) use generic SQLite affinity names (e.g. NUMERIC vs NUMERIC(p,s))"
                )
            if cmp.target_only_indexes:
                total_added = sum(len(v) for v in cmp.target_only_indexes.values())
                lines.append(
                    f"  - Analytical indexes added : {total_added} index(es) across {len(cmp.target_only_indexes)} table(s)"
                )
            if cmp.reference_only_indexes:
                lines.append(
                    f"  - Reference-only indexes   : {cmp.reference_only_indexes}"
                )

        lines.append("============================================================")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV stream abstraction (uniform over files and ZIP entries)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CSVStreamSource:
    table_name: str
    label: str
    open_reader: Callable[[], Any]  # context manager yielding Iterator[list[str]]


def _sanitize_table_name(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", stem.strip()).strip("_")
    if not cleaned:
        raise DatasetImportError(f"Cannot derive a valid table name from '{stem}'")
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    if not is_valid_identifier(cleaned):
        raise DatasetImportError(f"Derived table name '{cleaned}' is not a valid SQL identifier")
    return cleaned.lower()


def _make_file_csv_source(csv_path: Path) -> _CSVStreamSource:
    table_name = _sanitize_table_name(csv_path.stem)

    @contextmanager
    def _open() -> Iterator[Iterator[list[str]]]:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            yield csv.reader(fh)

    return _CSVStreamSource(
        table_name=table_name,
        label=str(csv_path),
        open_reader=_open,
    )


def _make_zip_csv_source(zip_path: Path, member_name: str) -> _CSVStreamSource:
    table_name = _sanitize_table_name(Path(member_name).stem)

    @contextmanager
    def _open() -> Iterator[Iterator[list[str]]]:
        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open(member_name, "r") as raw_stream:
                with io.TextIOWrapper(raw_stream, encoding="utf-8-sig", newline="") as text_stream:
                    yield csv.reader(text_stream)

    return _CSVStreamSource(
        table_name=table_name,
        label=f"{zip_path}!{member_name}",
        open_reader=_open,
    )


def _discover_sources(
    source: str | Path | Sequence[str | Path],
) -> tuple[str, list[_CSVStreamSource], Path | None]:
    """Return ``(description, csv_sources, sqlite_source_if_no_csvs)``."""
    if isinstance(source, (list, tuple)):
        if not source:
            raise DatasetImportError("Empty CSV file list provided")
        paths = [Path(p) for p in source]
        for p in paths:
            if not p.is_file() or p.suffix.lower() != ".csv":
                raise DatasetImportError(f"Expected an existing .csv file, got: {p}")
        csv_sources = [_make_file_csv_source(p) for p in sorted(paths, key=lambda x: x.name)]
        _ensure_unique_table_names(csv_sources)
        return f"{len(csv_sources)} CSV file(s)", csv_sources, None

    src_path = Path(source)
    if not src_path.exists():
        raise DatasetImportError(f"Dataset source does not exist: {src_path}")

    if src_path.is_dir():
        csv_files = sorted(
            p for p in src_path.iterdir()
            if p.is_file() and p.suffix.lower() == ".csv" and not p.name.startswith(".")
        )
        if csv_files:
            csv_sources = [_make_file_csv_source(p) for p in csv_files]
            _ensure_unique_table_names(csv_sources)
            return f"directory {src_path}", csv_sources, None

        sqlite_files = sorted(
            p for p in src_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".sqlite", ".sqlite3", ".db"}
        )
        if len(sqlite_files) == 1:
            return f"SQLite file {sqlite_files[0]}", [], sqlite_files[0]
        raise DatasetImportError(f"No .csv files found in directory: {src_path}")

    suffix = src_path.suffix.lower()
    if suffix == ".csv":
        return f"CSV file {src_path}", [_make_file_csv_source(src_path)], None

    if suffix == ".zip":
        if not zipfile.is_zipfile(src_path):
            raise DatasetImportError(f"Invalid or corrupted ZIP archive: {src_path}")
        with zipfile.ZipFile(src_path, "r") as zf:
            csv_members = sorted(
                info.filename
                for info in zf.infolist()
                if not info.is_dir()
                and info.filename.lower().endswith(".csv")
                and "__MACOSX" not in info.filename
                and not Path(info.filename).name.startswith(".")
            )
        if not csv_members:
            raise DatasetImportError(f"ZIP archive contains no .csv files: {src_path}")
        csv_sources = [_make_zip_csv_source(src_path, m) for m in csv_members]
        _ensure_unique_table_names(csv_sources)
        return f"ZIP archive {src_path}", csv_sources, None

    if suffix in {".sqlite", ".sqlite3", ".db"}:
        return f"SQLite database {src_path}", [], src_path

    raise DatasetImportError(f"Unsupported dataset source format: {src_path}")


def _ensure_unique_table_names(sources: list[_CSVStreamSource]) -> None:
    seen: set[str] = set()
    for src in sources:
        if src.table_name in seen:
            raise DatasetImportError(
                f"Duplicate table name '{src.table_name}' discovered in dataset sources"
            )
        seen.add(src.table_name)


# ---------------------------------------------------------------------------
# Dynamic CSV schema profiling (types, nullability, PKs, FKs, indexes)
# ---------------------------------------------------------------------------


@dataclass
class _ColProfile:
    name: str
    non_empty: int = 0
    empty: int = 0
    int_count: int = 0
    dec_count: int = 0
    iso_date_count: int = 0
    distinct_sample: set[str] = field(default_factory=set)

    @property
    def num_count(self) -> int:
        return self.int_count + self.dec_count

    def inferred_sql_type(self) -> str:
        if self.non_empty == 0:
            return "TEXT"
        if self.num_count == self.non_empty:
            return "INTEGER" if self.dec_count == 0 else "NUMERIC"
        # Majority-numeric rule (>=80% across >=4 non-empty rows) prevents a single
        # corrupt string cell from silently downgrading a numeric column to TEXT.
        if self.non_empty >= 4 and (self.num_count / self.non_empty) >= 0.8:
            return "INTEGER" if self.dec_count == 0 else "NUMERIC"
        return "TEXT"


@dataclass
class _TableProfile:
    name: str
    source: _CSVStreamSource
    row_count: int
    columns: list[_ColProfile]


def _singular_stems(table_name: str) -> set[str]:
    low = table_name.lower()
    stems = {low}
    if low.endswith("ies") and len(low) > 3:
        stems.add(low[:-3] + "y")
    if (low.endswith("ses") or low.endswith("xes") or low.endswith("zes")) and len(low) > 3:
        stems.add(low[:-2])
    if low.endswith("s") and len(low) > 1:
        stems.add(low[:-1])
    return stems


def _profile_single_csv(src: _CSVStreamSource) -> _TableProfile:
    with src.open_reader() as reader:
        try:
            raw_headers = next(reader)
        except StopIteration as exc:
            raise DatasetImportError(f"CSV source is empty (missing header): {src.label}") from exc

        headers = [h.strip() for h in raw_headers]
        if not headers or any(not h for h in headers):
            raise DatasetImportError(
                f"CSV source '{src.label}' contains empty column header(s): {raw_headers}"
            )
        lower_headers = [h.lower() for h in headers]
        if len(set(lower_headers)) != len(lower_headers):
            raise DatasetImportError(
                f"CSV source '{src.label}' contains duplicate column names: {headers}"
            )

        ncols = len(headers)
        col_profiles = [_ColProfile(name=h) for h in headers]
        valid_rows = 0

        for row in reader:
            if not row:
                continue
            if len(row) != ncols:
                # Malformed width rows do not pollute schema inference; they will be
                # logged and captured during the import pass.
                continue
            valid_rows += 1
            for idx, cell in enumerate(row):
                prof = col_profiles[idx]
                if cell == "":
                    prof.empty += 1
                    continue
                prof.non_empty += 1
                stripped = cell.strip()
                if _INT_RE.match(stripped):
                    prof.int_count += 1
                elif _DEC_RE.match(stripped):
                    prof.dec_count += 1
                elif _ISO_DATE_RE.match(stripped):
                    prof.iso_date_count += 1
                if len(prof.distinct_sample) <= 60:
                    prof.distinct_sample.add(stripped)

    return _TableProfile(
        name=src.table_name,
        source=src,
        row_count=valid_rows,
        columns=col_profiles,
    )


def _infer_table_specs(
    profiles: list[_TableProfile], *, create_indexes: bool = True
) -> list[tuple[TableSpec, _CSVStreamSource]]:
    """Build ``TableSpec`` definitions with PKs, FKs, indexes, and topological order."""
    specs_by_name: dict[str, TableSpec] = {}
    sources_by_name: dict[str, _CSVStreamSource] = {}
    pk_lookup: dict[str, tuple[str, str, str]] = {}  # fk_col_name -> (target_table, pk_col, sql_type)

    # Pass 1: Columns and Primary Keys
    for tprof in profiles:
        candidate_pk_names = {"id"} | {f"{s}_id" for s in _singular_stems(tprof.name)}
        pk_index: int | None = None
        for idx, cprof in enumerate(tprof.columns):
            ctype = cprof.inferred_sql_type()
            if cprof.name.lower() in candidate_pk_names and ctype == "INTEGER":
                pk_index = idx
                break
        if pk_index is None and tprof.columns:
            first = tprof.columns[0]
            if (
                first.name.lower() in candidate_pk_names
                and first.non_empty > 0
                and first.empty == 0
                and len(first.distinct_sample) == min(first.non_empty, 61)
            ):
                pk_index = 0

        col_specs: list[ColumnSpec] = []
        for idx, cprof in enumerate(tprof.columns):
            sql_type = cprof.inferred_sql_type()
            is_pk = idx == pk_index
            not_null = True if is_pk else (cprof.non_empty > 0 and cprof.empty == 0)
            col_specs.append(
                ColumnSpec(
                    name=cprof.name,
                    sql_type=sql_type,
                    not_null=not_null,
                    is_primary_key=is_pk,
                )
            )
            if is_pk:
                low_pk = cprof.name.lower()
                if low_pk != "id":
                    pk_lookup[low_pk] = (tprof.name, cprof.name, sql_type)
                for stem in _singular_stems(tprof.name):
                    pk_lookup.setdefault(f"{stem}_id", (tprof.name, cprof.name, sql_type))

        specs_by_name[tprof.name] = TableSpec(name=tprof.name, columns=col_specs)
        sources_by_name[tprof.name] = tprof.source

    # Pass 2: Foreign Keys and Analytical Indexes
    prof_by_name = {p.name: p for p in profiles}
    for tname, spec in specs_by_name.items():
        tprof = prof_by_name[tname]
        fks: list[ForeignKeySpec] = []
        indexed_cols: set[str] = set()

        for col_spec, col_prof in zip(spec.columns, tprof.columns):
            if col_spec.is_primary_key:
                continue
            target = pk_lookup.get(col_spec.name.lower())
            if target is not None:
                target_table, target_pk, target_type = target
                if target_table != tname and col_spec.sql_type == target_type:
                    fks.append(
                        ForeignKeySpec(
                            from_column=col_spec.name,
                            to_table=target_table,
                            to_column=target_pk,
                        )
                    )
                    indexed_cols.add(col_spec.name)

        spec.foreign_keys = fks

        if create_indexes:
            for col_spec, col_prof in zip(spec.columns, tprof.columns):
                if col_spec.is_primary_key or col_spec.name in indexed_cols:
                    continue
                low_col = col_spec.name.lower()
                is_temporal = low_col.endswith(("_date", "_at")) or low_col in {
                    "date",
                    "timestamp",
                } or (
                    col_spec.sql_type == "TEXT"
                    and col_prof.non_empty > 0
                    and (col_prof.iso_date_count / col_prof.non_empty) >= 0.95
                )
                is_categorical = (
                    col_spec.sql_type == "TEXT"
                    and tprof.row_count >= 50
                    and 2 <= len(col_prof.distinct_sample) <= 50
                )
                if is_temporal or is_categorical:
                    indexed_cols.add(col_spec.name)

            spec.indexes = [
                (f"idx_{tname}_{col}", [col])
                for col in [c.name for c in spec.columns if c.name in indexed_cols]
            ]

    # Pass 3: Topological ordering (parents before children)
    ordered_names = _topological_sort_tables(specs_by_name)
    return [(specs_by_name[name], sources_by_name[name]) for name in ordered_names]


def _topological_sort_tables(specs_by_name: dict[str, TableSpec]) -> list[str]:
    deps: dict[str, set[str]] = {
        name: {
            fk.to_table
            for fk in spec.foreign_keys
            if fk.to_table in specs_by_name and fk.to_table != name
        }
        for name, spec in specs_by_name.items()
    }
    ordered: list[str] = []
    ready = sorted(name for name, d in deps.items() if not d)
    remaining = {name: set(d) for name, d in deps.items() if d}

    while ready:
        current = ready.pop(0)
        ordered.append(current)
        newly_ready: list[str] = []
        for tbl, tbl_deps in list(remaining.items()):
            tbl_deps.discard(current)
            if not tbl_deps:
                newly_ready.append(tbl)
                del remaining[tbl]
        if newly_ready:
            ready = sorted(ready + newly_ready)

    if remaining:
        # Cycle fallback: append remaining deterministically
        ordered.extend(sorted(remaining))
    return ordered


# ---------------------------------------------------------------------------
# Row conversion & batch import engine
# ---------------------------------------------------------------------------


def _convert_csv_row(
    raw_row: list[str], columns: list[ColumnSpec]
) -> tuple[tuple[Any, ...] | None, str | None]:
    if len(raw_row) != len(columns):
        return (
            None,
            f"Column count mismatch: expected {len(columns)}, got {len(raw_row)}",
        )
    values: list[Any] = []
    for raw_val, col in zip(raw_row, columns):
        if raw_val == "":
            if col.is_primary_key or col.not_null:
                return None, f"NULL/empty value in NOT NULL column '{col.name}'"
            values.append(None)
            continue

        if col.sql_type == "INTEGER":
            s = raw_val.strip()
            if not _INT_RE.match(s):
                return None, f"Invalid INTEGER value {raw_val!r} in column '{col.name}'"
            values.append(int(s))
        elif col.sql_type == "NUMERIC":
            s = raw_val.strip()
            if _INT_RE.match(s):
                values.append(int(s))
            elif _DEC_RE.match(s):
                values.append(float(s))
            else:
                try:
                    parsed = float(s)
                except ValueError:
                    return None, f"Invalid NUMERIC value {raw_val!r} in column '{col.name}'"
                if not math.isfinite(parsed):
                    return None, f"Non-finite NUMERIC value {raw_val!r} in column '{col.name}'"
                values.append(parsed)
        else:
            values.append(raw_val)

    return tuple(values), None


def _record_rejection(
    rejected_list: list[RejectedRecord],
    table: str,
    line_number: int,
    reason: str,
    raw_row: Sequence[Any],
    *,
    strict: bool,
) -> bool:
    """Log and capture a rejected record; return True if list was truncated."""
    preview = [str(x)[:80] for x in list(raw_row)[:12]]
    log.warning(
        "Malformed record in table '%s' at CSV line %d: %s | row=%r",
        table,
        line_number,
        reason,
        preview,
    )
    if strict:
        raise DatasetImportError(
            f"Strict import aborted at {table} line {line_number}: {reason}"
        )
    if len(rejected_list) < MAX_CAPTURED_REJECTED_RECORDS:
        rejected_list.append(
            RejectedRecord(
                table=table,
                line_number=line_number,
                reason=reason,
                raw_preview=preview,
            )
        )
        return False
    return True


def _flush_batch(
    con: sqlite3.Connection,
    insert_sql: str,
    table_name: str,
    batch: list[tuple[int, list[str], tuple[Any, ...]]],
    rejected_list: list[RejectedRecord],
    *,
    strict: bool,
) -> tuple[int, int, bool]:
    """Insert ``batch`` using a savepoint; fall back row-by-row if a constraint fails."""
    if not batch:
        return 0, 0, False

    con.execute("SAVEPOINT batch_sp")
    try:
        con.executemany(insert_sql, [item[2] for item in batch])
        con.execute("RELEASE SAVEPOINT batch_sp")
        return len(batch), 0, False
    except sqlite3.DatabaseError as batch_exc:
        con.execute("ROLLBACK TO SAVEPOINT batch_sp")
        con.execute("RELEASE SAVEPOINT batch_sp")
        log.debug(
            "Batch insert into '%s' hit constraint error (%s); isolating offending row(s)",
            table_name,
            batch_exc,
        )

    imported = 0
    rejected = 0
    truncated = False
    for line_no, raw_row, params in batch:
        con.execute("SAVEPOINT row_sp")
        try:
            con.execute(insert_sql, params)
            con.execute("RELEASE SAVEPOINT row_sp")
            imported += 1
        except sqlite3.DatabaseError as row_exc:
            con.execute("ROLLBACK TO SAVEPOINT row_sp")
            con.execute("RELEASE SAVEPOINT row_sp")
            rejected += 1
            if _record_rejection(
                rejected_list,
                table_name,
                line_no,
                f"SQLite constraint/type error: {row_exc}",
                raw_row,
                strict=strict,
            ):
                truncated = True
    return imported, rejected, truncated


def _import_csv_tables(
    con: sqlite3.Connection,
    plan: list[tuple[TableSpec, _CSVStreamSource]],
    *,
    batch_size: int,
    strict: bool,
) -> tuple[list[TableImportResult], list[RejectedRecord], bool]:
    table_results: list[TableImportResult] = []
    rejected_records: list[RejectedRecord] = []
    rejected_truncated = False

    for spec, src in plan:
        t0 = time.perf_counter()
        con.execute(spec.create_table_sql())

        placeholders = ", ".join("?" for _ in spec.columns)
        col_list = ", ".join(quote_identifier(c.name) for c in spec.columns)
        insert_sql = (
            f"INSERT INTO {quote_identifier(spec.name)} ({col_list}) VALUES ({placeholders})"
        )

        imported = 0
        rejected = 0
        batch: list[tuple[int, list[str], tuple[Any, ...]]] = []

        with src.open_reader() as reader:
            _ = next(reader, None)  # skip header (already validated)
            for line_no, raw_row in enumerate(reader, start=2):
                if not raw_row:
                    continue
                converted, err = _convert_csv_row(raw_row, spec.columns)
                if err is not None or converted is None:
                    rejected += 1
                    if _record_rejection(
                        rejected_records,
                        spec.name,
                        line_no,
                        err or "Invalid record",
                        raw_row,
                        strict=strict,
                    ):
                        rejected_truncated = True
                    continue

                batch.append((line_no, raw_row, converted))
                if len(batch) >= batch_size:
                    imp, rej, trunc = _flush_batch(
                        con,
                        insert_sql,
                        spec.name,
                        batch,
                        rejected_records,
                        strict=strict,
                    )
                    imported += imp
                    rejected += rej
                    rejected_truncated = rejected_truncated or trunc
                    batch.clear()

        if batch:
            imp, rej, trunc = _flush_batch(
                con,
                insert_sql,
                spec.name,
                batch,
                rejected_records,
                strict=strict,
            )
            imported += imp
            rejected += rej
            rejected_truncated = rejected_truncated or trunc
            batch.clear()

        created_indexes: list[str] = []
        for idx_name, idx_cols in spec.indexes:
            cols_sql = ", ".join(quote_identifier(c) for c in idx_cols)
            con.execute(
                f"CREATE INDEX IF NOT EXISTS {quote_identifier(idx_name)} "
                f"ON {quote_identifier(spec.name)} ({cols_sql})"
            )
            created_indexes.append(idx_name)

        dt = round(time.perf_counter() - t0, 3)
        log.info(
            "Imported table '%s': %d rows (%d rejected, %d indexes) in %.2fs",
            spec.name,
            imported,
            rejected,
            len(created_indexes),
            dt,
        )
        table_results.append(
            TableImportResult(
                table_name=spec.name,
                source_label=src.label,
                imported_rows=imported,
                rejected_rows=rejected,
                indexes_created=created_indexes,
                duration_s=dt,
            )
        )

    return table_results, rejected_records, rejected_truncated


def _import_from_sqlite_source(
    dst_con: sqlite3.Connection,
    src_sqlite_path: Path,
    *,
    batch_size: int,
    create_indexes: bool,
) -> list[TableImportResult]:
    """Copy schema and batch-stream rows from a read-only SQLite dataset source."""
    if src_sqlite_path.resolve() == Path(dst_con.execute("PRAGMA database_list").fetchone()[2]).resolve():
        raise DatasetImportError("Source and target SQLite database paths must differ")

    src_con = connect_readonly(src_sqlite_path, immutable=True)
    results: list[TableImportResult] = []
    try:
        src_schema = inspect_schema(src_con, include_counts=False)
        specs_for_order: dict[str, TableSpec] = {
            t.name: TableSpec(
                name=t.name,
                columns=[
                    ColumnSpec(
                        name=c.name,
                        sql_type=c.affinity,
                        not_null=c.not_null,
                        is_primary_key=c.is_primary_key,
                    )
                    for c in t.columns
                ],
                foreign_keys=[
                    ForeignKeySpec(
                        from_column=fk.from_column,
                        to_table=fk.to_table,
                        to_column=fk.to_column,
                    )
                    for fk in t.foreign_keys
                ],
            )
            for t in src_schema.tables
        }
        ordered_names = _topological_sort_tables(specs_for_order)
        table_lookup = {t.name: t for t in src_schema.tables}

        for tname in ordered_names:
            t0 = time.perf_counter()
            tbl = table_lookup[tname]
            if not tbl.create_sql:
                raise DatasetImportError(f"Missing CREATE TABLE DDL for '{tname}'")
            dst_con.execute(tbl.create_sql)

            quoted_tbl = quote_identifier(tname)
            col_names = [c.name for c in tbl.columns]
            col_sql = ", ".join(quote_identifier(c) for c in col_names)
            placeholders = ", ".join("?" for _ in col_names)
            insert_sql = f"INSERT INTO {quoted_tbl} ({col_sql}) VALUES ({placeholders})"

            cur = src_con.execute(f"SELECT {col_sql} FROM {quoted_tbl}")
            imported = 0
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                dst_con.executemany(insert_sql, rows)
                imported += len(rows)

            created_indexes: list[str] = []
            # Copy explicit non-auto indexes if any exist
            for idx in tbl.indexes:
                if idx.origin == "c":
                    idx_row = src_con.execute(
                        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                        (idx.name,),
                    ).fetchone()
                    if idx_row and idx_row[0]:
                        dst_con.execute(idx_row[0])
                        created_indexes.append(idx.name)

            if create_indexes:
                existing_single = {
                    idx.columns[0] for idx in tbl.indexes if len(idx.columns) == 1
                }
                for fk in tbl.foreign_keys:
                    if fk.from_column not in existing_single:
                        idx_name = f"idx_{tname}_{fk.from_column}"
                        dst_con.execute(
                            f"CREATE INDEX IF NOT EXISTS {quote_identifier(idx_name)} "
                            f"ON {quoted_tbl} ({quote_identifier(fk.from_column)})"
                        )
                        created_indexes.append(idx_name)
                        existing_single.add(fk.from_column)

            dt = round(time.perf_counter() - t0, 3)
            results.append(
                TableImportResult(
                    table_name=tname,
                    source_label=f"{src_sqlite_path}:{tname}",
                    imported_rows=imported,
                    rejected_rows=0,
                    indexes_created=created_indexes,
                    duration_s=dt,
                )
            )
    finally:
        src_con.close()

    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def import_dataset(
    source: str | Path | Sequence[str | Path],
    target_db_path: str | Path,
    *,
    overwrite: bool = False,
    batch_size: int = 5_000,
    reference_db_path: str | Path | None = None,
    strict: bool = False,
    create_indexes: bool = True,
) -> ImportSummary:
    """Import dataset from ``source`` into ``target_db_path`` transactionally.

    Parameters
    ----------
    source:
        Directory of CSVs, ``.zip`` archive of CSVs, sequence of ``.csv`` paths,
        or a compatible ``.sqlite`` file.
    target_db_path:
        Destination SQLite database path (e.g. ``data/ecommerce.db``).
    overwrite:
        Must be ``True`` to replace an existing ``target_db_path``; otherwise
        raises ``FileExistsError``.
    batch_size:
        Number of records per batch insert (keeps memory usage bounded).
    reference_db_path:
        Optional reference SQLite file (e.g. ``data/raw/ecommerce.sqlite``) for
        post-import table, schema, FK, and row-count parity verification.
    strict:
        If ``True``, abort and roll back on the first malformed record instead
        of logging and continuing.
    create_indexes:
        If ``True``, create analytical indexes on FK, temporal, and categorical
        columns.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    target_path = Path(target_db_path).expanduser().resolve()
    if reference_db_path is not None:
        ref_resolved = Path(reference_db_path).expanduser().resolve()
        if ref_resolved == target_path:
            raise DatasetImportError(
                "target_db_path must not point to the reference database"
            )

    if target_path.exists() and not overwrite:
        raise FileExistsError(
            f"Database already exists at '{target_path}'. "
            "Refusing to overwrite without explicit confirmation (overwrite=True)."
        )

    overall_start = time.perf_counter()
    source_desc, csv_sources, sqlite_source = _discover_sources(source)

    if sqlite_source is not None and sqlite_source.resolve() == target_path:
        raise DatasetImportError("Source SQLite path and target_db_path must differ")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path = target_path.with_name(
        f".{target_path.name}.{os.getpid()}.importing.tmp"
    )
    if staging_path.exists():
        staging_path.unlink()

    con: sqlite3.Connection | None = None
    try:
        if csv_sources:
            log.info("Profiling %d CSV source(s) from %s ...", len(csv_sources), source_desc)
            profiles = [_profile_single_csv(src) for src in csv_sources]
            plan = _infer_table_specs(profiles, create_indexes=create_indexes)

            con = connect_readwrite(staging_path)
            con.execute("BEGIN IMMEDIATE")
            table_results, rejected_records, rejected_truncated = _import_csv_tables(
                con,
                plan,
                batch_size=batch_size,
                strict=strict,
            )
            con.execute("COMMIT")
        else:
            assert sqlite_source is not None
            con = connect_readwrite(staging_path)
            con.execute("BEGIN IMMEDIATE")
            table_results = _import_from_sqlite_source(
                con,
                sqlite_source,
                batch_size=batch_size,
                create_indexes=create_indexes,
            )
            rejected_records = []
            rejected_truncated = False
            con.execute("COMMIT")

        con.execute("ANALYZE")
        integrity = validate_database_integrity(con)
        if not integrity.integrity_ok:
            raise DatasetImportError(
                f"SQLite integrity_check failed: {integrity.integrity_messages}"
            )
        if not integrity.foreign_keys_ok:
            raise DatasetImportError(
                f"SQLite foreign_key_check found {len(integrity.foreign_key_violations)} "
                f"violation(s): {integrity.foreign_key_violations[:5]}"
            )

        con.close()
        con = None

        # Atomically publish the validated staging database to target_path
        staging_path.replace(target_path)

    except BaseException:
        if con is not None:
            try:
                if con.in_transaction:
                    con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            try:
                con.close()
            except sqlite3.Error:
                pass
        for leftover in (
            staging_path,
            Path(f"{staging_path}-journal"),
            Path(f"{staging_path}-wal"),
            Path(f"{staging_path}-shm"),
        ):
            if leftover.exists():
                try:
                    leftover.unlink()
                except OSError:
                    pass
        raise

    comparison: DatabaseComparison | None = None
    if reference_db_path is not None:
        ref_path = Path(reference_db_path)
        if not ref_path.is_file():
            raise DatasetImportError(f"Reference database not found: {ref_path}")
        comparison = compare_databases(target_path, ref_path)

    total_duration = round(time.perf_counter() - overall_start, 3)
    total_imported = sum(t.imported_rows for t in table_results)
    total_rejected = sum(t.rejected_rows for t in table_results)

    summary = ImportSummary(
        source_description=source_desc,
        target_database=str(target_path),
        tables=table_results,
        total_imported_rows=total_imported,
        total_rejected_rows=total_rejected,
        rejected_records=rejected_records,
        rejected_records_truncated=rejected_truncated,
        duration_s=total_duration,
        integrity=integrity,
        reference_comparison=comparison,
    )
    log.info(
        "Dataset import complete -> %s (%d tables, %d rows, %.2fs)",
        target_path,
        len(table_results),
        total_imported,
        total_duration,
    )
    return summary

