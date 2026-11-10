"""Reusable SQLite schema discovery, sampling, integrity, and comparison tools.

This module makes zero assumptions about table or column names. All metadata
is discovered dynamically from ``sqlite_master`` and SQLite ``PRAGMA`` queries,
and returned as structured dataclasses with ``.to_dict()`` serialisation ready
for MCP tools and the PySide6 GUI.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .connection import connect_readonly, quote_identifier


class TableNotFoundError(LookupError):
    """Raised when a requested table does not exist in the database."""


# ---------------------------------------------------------------------------
# Metadata dataclasses
# ---------------------------------------------------------------------------


def sqlite_type_affinity(declared_type: str) -> str:
    """Return SQLite's canonical type affinity (SQLite docs section 3.1)."""
    upper = (declared_type or "").upper()
    if "INT" in upper:
        return "INTEGER"
    if any(tok in upper for tok in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if "BLOB" in upper or not upper.strip():
        return "BLOB"
    if any(tok in upper for tok in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    affinity: str
    not_null: bool
    default_value: Any
    is_primary_key: bool
    pk_position: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForeignKeyInfo:
    id: int
    seq: int
    from_column: str
    to_table: str
    to_column: str
    on_update: str
    on_delete: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndexInfo:
    name: str
    unique: bool
    origin: str  # "c" = CREATE INDEX, "u" = UNIQUE, "pk" = PRIMARY KEY
    partial: bool
    columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipInfo:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str  # "many-to-one" or "one-to-one"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableSchema:
    name: str
    columns: list[ColumnInfo]
    primary_keys: list[str]
    foreign_keys: list[ForeignKeyInfo]
    indexes: list[IndexInfo]
    row_count: int | None = None
    create_sql: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "primary_keys": list(self.primary_keys),
            "columns": [c.to_dict() for c in self.columns],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "indexes": [idx.to_dict() for idx in self.indexes],
            "create_sql": self.create_sql,
        }

    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


@dataclass
class DatabaseSchema:
    database_path: str | None
    table_count: int
    total_rows: int | None
    tables: list[TableSchema]
    relationships: list[RelationshipInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_path": self.database_path,
            "table_count": self.table_count,
            "total_rows": self.total_rows,
            "tables": [t.to_dict() for t in self.tables],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    def table_map(self) -> dict[str, TableSchema]:
        """Case-insensitive mapping of ``table_name.lower() -> TableSchema``."""
        return {t.name.lower(): t for t in self.tables}

    def format_for_prompt(self) -> str:
        """Render a compact, readable schema summary suitable for LLM prompts."""
        lines: list[str] = []
        for t in self.tables:
            cnt = f" ({t.row_count:,} rows)" if t.row_count is not None else ""
            lines.append(f"Table {t.name}{cnt}:")
            for c in t.columns:
                flags: list[str] = [c.data_type or c.affinity]
                if c.is_primary_key:
                    flags.append("PK")
                elif c.not_null:
                    flags.append("NOT NULL")
                lines.append(f"  - {c.name}: {' '.join(flags)}")
            for fk in t.foreign_keys:
                lines.append(f"  FK: {t.name}.{fk.from_column} -> {fk.to_table}.{fk.to_column}")
        return "\n".join(lines)


@dataclass
class IntegrityReport:
    integrity_ok: bool
    integrity_messages: list[str]
    foreign_keys_ok: bool
    foreign_key_violations: list[dict[str, Any]]
    row_counts: dict[str, int]
    total_rows: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DatabaseComparison:
    target_path: str
    reference_path: str
    matches_structure_and_counts: bool
    missing_tables: list[str]
    extra_tables: list[str]
    common_tables: list[str]
    row_count_differences: dict[str, dict[str, int]]
    total_target_rows: int
    total_reference_rows: int
    column_differences: dict[str, list[str]]
    declared_type_notes: dict[str, list[str]]
    foreign_key_differences: dict[str, list[str]]
    target_only_indexes: dict[str, list[str]]
    reference_only_indexes: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal connection context helper
# ---------------------------------------------------------------------------


@contextmanager
def _open_db(
    db: str | Path | sqlite3.Connection, *, immutable: bool = False
) -> Iterator[tuple[sqlite3.Connection, str | None]]:
    if isinstance(db, sqlite3.Connection):
        yield db, None
        return
    path = Path(db)
    con = connect_readonly(path, immutable=immutable)
    try:
        yield con, str(path.resolve())
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Core inspection functions
# ---------------------------------------------------------------------------


def list_user_tables(con: sqlite3.Connection) -> list[str]:
    """Return user table names in creation/catalogue order (excluding sqlite_*)."""
    rows = con.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _inspect_single_table(
    con: sqlite3.Connection, table_name: str, *, include_count: bool = True
) -> TableSchema:
    quoted = quote_identifier(table_name)

    sql_row = con.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    create_sql = sql_row[0] if sql_row else None

    raw_cols = con.execute(f"PRAGMA table_info({quoted})").fetchall()
    columns: list[ColumnInfo] = []
    pk_pairs: list[tuple[int, str]] = []
    for _cid, col_name, col_type, notnull, dflt_val, pk_pos in raw_cols:
        declared = col_type or "TEXT"
        is_pk = pk_pos > 0
        if is_pk:
            pk_pairs.append((pk_pos, col_name))
        columns.append(
            ColumnInfo(
                name=col_name,
                data_type=declared,
                affinity=sqlite_type_affinity(declared),
                not_null=bool(notnull or is_pk),
                default_value=dflt_val,
                is_primary_key=is_pk,
                pk_position=pk_pos,
            )
        )
    pk_pairs.sort(key=lambda item: item[0])
    primary_keys = [name for _, name in pk_pairs]

    raw_fks = con.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()
    foreign_keys = [
        ForeignKeyInfo(
            id=fk_id,
            seq=seq,
            from_column=from_col,
            to_table=to_table,
            to_column=to_col,
            on_update=on_upd,
            on_delete=on_del,
        )
        for fk_id, seq, to_table, from_col, to_col, on_upd, on_del, _match in raw_fks
    ]
    foreign_keys.sort(key=lambda fk: (fk.from_column, fk.to_table, fk.to_column))

    raw_indexes = con.execute(f"PRAGMA index_list({quoted})").fetchall()
    indexes: list[IndexInfo] = []
    for _seq, idx_name, unique, origin, partial in raw_indexes:
        quoted_idx = quote_identifier(idx_name)
        idx_cols = [
            r[2]
            for r in con.execute(f"PRAGMA index_info({quoted_idx})").fetchall()
            if r[2] is not None
        ]
        indexes.append(
            IndexInfo(
                name=idx_name,
                unique=bool(unique),
                origin=origin,
                partial=bool(partial),
                columns=idx_cols,
            )
        )

    row_count: int | None = None
    if include_count:
        row_count = int(con.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])

    return TableSchema(
        name=table_name,
        columns=columns,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        indexes=indexes,
        row_count=row_count,
        create_sql=create_sql,
    )


def _derive_relationships(tables: list[TableSchema]) -> list[RelationshipInfo]:
    relationships: list[RelationshipInfo] = []
    for tbl in tables:
        unique_single_cols: set[str] = set()
        if len(tbl.primary_keys) == 1:
            unique_single_cols.add(tbl.primary_keys[0])
        for idx in tbl.indexes:
            if idx.unique and not idx.partial and len(idx.columns) == 1:
                unique_single_cols.add(idx.columns[0])

        for fk in tbl.foreign_keys:
            cardinality = (
                "one-to-one" if fk.from_column in unique_single_cols else "many-to-one"
            )
            relationships.append(
                RelationshipInfo(
                    from_table=tbl.name,
                    from_column=fk.from_column,
                    to_table=fk.to_table,
                    to_column=fk.to_column,
                    cardinality=cardinality,
                )
            )
    return relationships


def inspect_schema(
    db: str | Path | sqlite3.Connection,
    table_name: str | None = None,
    *,
    include_counts: bool = True,
) -> DatabaseSchema:
    """Inspect all tables (or one ``table_name``) in ``db`` dynamically."""
    with _open_db(db) as (con, db_path):
        all_tables = list_user_tables(con)
        if table_name is not None:
            lookup = {t.lower(): t for t in all_tables}
            resolved = lookup.get(table_name.strip().lower())
            if resolved is None:
                raise TableNotFoundError(
                    f"Table '{table_name}' does not exist. Available tables: {all_tables}"
                )
            target_names = [resolved]
        else:
            target_names = all_tables

        inspected = [
            _inspect_single_table(con, name, include_count=include_counts)
            for name in target_names
        ]
        relationships = _derive_relationships(inspected)
        total_rows = (
            sum(t.row_count or 0 for t in inspected) if include_counts else None
        )
        return DatabaseSchema(
            database_path=db_path,
            table_count=len(inspected),
            total_rows=total_rows,
            tables=inspected,
            relationships=relationships,
        )


def get_table_sample(
    db: str | Path | sqlite3.Connection,
    table_name: str,
    limit: int = 10,
    *,
    max_limit: int = 100,
) -> dict[str, Any]:
    """Return up to ``limit`` (capped at ``max_limit``) sample rows and column metadata."""
    if limit < 1:
        raise ValueError("Sample limit must be at least 1")
    effective_limit = min(int(limit), int(max_limit))

    with _open_db(db) as (con, _):
        all_tables = list_user_tables(con)
        lookup = {t.lower(): t for t in all_tables}
        resolved = lookup.get((table_name or "").strip().lower())
        if resolved is None:
            raise TableNotFoundError(
                f"Table '{table_name}' does not exist. Available tables: {all_tables}"
            )
        tbl_schema = _inspect_single_table(con, resolved, include_count=True)
        quoted = quote_identifier(resolved)
        cursor = con.execute(f"SELECT * FROM {quoted} LIMIT ?", (effective_limit,))
        col_names = [desc[0] for desc in cursor.description]
        rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]

    return {
        "table_name": resolved,
        "total_row_count": tbl_schema.row_count,
        "requested_limit": limit,
        "effective_limit": effective_limit,
        "returned_count": len(rows),
        "columns": [c.to_dict() for c in tbl_schema.columns],
        "records": rows,
    }


def validate_database_integrity(
    db: str | Path | sqlite3.Connection,
) -> IntegrityReport:
    """Run ``PRAGMA integrity_check``, ``PRAGMA foreign_key_check``, and row counts."""
    with _open_db(db) as (con, _):
        integrity_rows = [r[0] for r in con.execute("PRAGMA integrity_check").fetchall()]
        integrity_ok = integrity_rows == ["ok"]

        fk_rows = con.execute("PRAGMA foreign_key_check").fetchall()
        fk_violations = [
            {
                "table": r[0],
                "rowid": r[1],
                "parent": r[2],
                "fkid": r[3],
            }
            for r in fk_rows
        ]

        row_counts: dict[str, int] = {}
        for t in list_user_tables(con):
            row_counts[t] = int(
                con.execute(f"SELECT COUNT(*) FROM {quote_identifier(t)}").fetchone()[0]
            )

    return IntegrityReport(
        integrity_ok=integrity_ok,
        integrity_messages=integrity_rows,
        foreign_keys_ok=len(fk_violations) == 0,
        foreign_key_violations=fk_violations,
        row_counts=row_counts,
        total_rows=sum(row_counts.values()),
    )


def compare_databases(
    target_db: str | Path,
    reference_db: str | Path,
) -> DatabaseComparison:
    """Compare ``target_db`` against ``reference_db`` (opened immutable read-only).

    Reports any differences in table names, row counts, columns/affinities/PKs,
    foreign keys, and indexes without modifying either database.
    """
    with _open_db(target_db, immutable=False) as (t_con, t_path):
        t_schema = inspect_schema(t_con, include_counts=True)
    with _open_db(reference_db, immutable=True) as (r_con, r_path):
        r_schema = inspect_schema(r_con, include_counts=True)

    t_map = {t.name: t for t in t_schema.tables}
    r_map = {t.name: t for t in r_schema.tables}

    t_names = set(t_map)
    r_names = set(r_map)
    missing_tables = sorted(r_names - t_names)
    extra_tables = sorted(t_names - r_names)
    common_tables = sorted(t_names & r_names)

    row_count_diffs: dict[str, dict[str, int]] = {}
    col_diffs: dict[str, list[str]] = {}
    type_notes: dict[str, list[str]] = {}
    fk_diffs: dict[str, list[str]] = {}
    target_only_idx: dict[str, list[str]] = {}
    ref_only_idx: dict[str, list[str]] = {}

    for name in common_tables:
        tt = t_map[name]
        rt = r_map[name]

        if tt.row_count != rt.row_count:
            row_count_diffs[name] = {
                "target": tt.row_count or 0,
                "reference": rt.row_count or 0,
                "delta": (tt.row_count or 0) - (rt.row_count or 0),
            }

        t_cols = {c.name: c for c in tt.columns}
        r_cols = {c.name: c for c in rt.columns}
        table_col_issues: list[str] = []
        table_type_notes: list[str] = []

        for missing_col in sorted(set(r_cols) - set(t_cols)):
            table_col_issues.append(f"Missing column '{missing_col}'")
        for extra_col in sorted(set(t_cols) - set(r_cols)):
            table_col_issues.append(f"Extra column '{extra_col}'")

        for col_name in [c.name for c in rt.columns if c.name in t_cols]:
            tc = t_cols[col_name]
            rc = r_cols[col_name]
            if tc.affinity != rc.affinity:
                table_col_issues.append(
                    f"Column '{col_name}' affinity mismatch: target={tc.affinity}, reference={rc.affinity}"
                )
            elif tc.data_type.upper() != rc.data_type.upper():
                table_type_notes.append(
                    f"Column '{col_name}' declared type target='{tc.data_type}' vs reference='{rc.data_type}' (same {tc.affinity} affinity)"
                )
            if tc.not_null != rc.not_null:
                table_col_issues.append(
                    f"Column '{col_name}' NOT NULL mismatch: target={tc.not_null}, reference={rc.not_null}"
                )
            if tc.is_primary_key != rc.is_primary_key:
                table_col_issues.append(
                    f"Column '{col_name}' PRIMARY KEY mismatch: target={tc.is_primary_key}, reference={rc.is_primary_key}"
                )

        if table_col_issues:
            col_diffs[name] = table_col_issues
        if table_type_notes:
            type_notes[name] = table_type_notes

        t_fks = {(fk.from_column, fk.to_table, fk.to_column) for fk in tt.foreign_keys}
        r_fks = {(fk.from_column, fk.to_table, fk.to_column) for fk in rt.foreign_keys}
        table_fk_issues: list[str] = []
        for fk_tuple in sorted(r_fks - t_fks):
            table_fk_issues.append(
                f"Missing FK {name}.{fk_tuple[0]} -> {fk_tuple[1]}.{fk_tuple[2]}"
            )
        for fk_tuple in sorted(t_fks - r_fks):
            table_fk_issues.append(
                f"Extra FK {name}.{fk_tuple[0]} -> {fk_tuple[1]}.{fk_tuple[2]}"
            )
        if table_fk_issues:
            fk_diffs[name] = table_fk_issues

        t_idx_cols = {tuple(idx.columns): idx.name for idx in tt.indexes}
        r_idx_cols = {tuple(idx.columns): idx.name for idx in rt.indexes}
        t_extra = [
            f"{t_idx_cols[cols]} ({', '.join(cols)})"
            for cols in sorted(set(t_idx_cols) - set(r_idx_cols))
        ]
        r_extra = [
            f"{r_idx_cols[cols]} ({', '.join(cols)})"
            for cols in sorted(set(r_idx_cols) - set(t_idx_cols))
        ]
        if t_extra:
            target_only_idx[name] = t_extra
        if r_extra:
            ref_only_idx[name] = r_extra

    matches = (
        not missing_tables
        and not extra_tables
        and not row_count_diffs
        and not col_diffs
        and not fk_diffs
    )

    return DatabaseComparison(
        target_path=t_path or str(target_db),
        reference_path=r_path or str(reference_db),
        matches_structure_and_counts=matches,
        missing_tables=missing_tables,
        extra_tables=extra_tables,
        common_tables=common_tables,
        row_count_differences=row_count_diffs,
        total_target_rows=t_schema.total_rows or 0,
        total_reference_rows=r_schema.total_rows or 0,
        column_differences=col_diffs,
        declared_type_notes=type_notes,
        foreign_key_differences=fk_diffs,
        target_only_indexes=target_only_idx,
        reference_only_indexes=ref_only_idx,
    )

