"""Safe read-only SQLite query execution with authorizer, timeout, and row cap.

Security layers enforced on every query:
1. ``file:...mode=ro`` URI connection (OS/SQLite VFS read-only mode).
2. ``PRAGMA query_only = ON``.
3. ``sqlite3`` authorizer callback permitting ONLY ``SELECT``, ``READ``,
   safe SQL ``FUNCTION`` calls, and ``RECURSIVE`` CTEs.
4. ``set_progress_handler`` VM opcode watchdog enforcing ``timeout_s`` and
   optional cooperative cancellation.
5. ``fetchmany(max_rows + 1)`` enforcing bounded memory and row count limits.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .connection import connect_readonly


class QueryExecutionError(RuntimeError):
    """Raised when a SQL query fails validation, authorization, or execution."""


class QueryTimeoutError(QueryExecutionError):
    """Raised when a SQL query exceeds its configured execution timeout."""


class QueryCancelledError(QueryExecutionError):
    """Raised when a running SQL query is cancelled by the caller."""


_ALLOWED_ACTIONS: frozenset[int] = frozenset(
    {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        getattr(sqlite3, "SQLITE_RECURSIVE", 33),
    }
)

_BLOCKED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "load_extension",
        "fts3_tokenizer",
    }
)


def _readonly_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    dbname: str | None,
    source: str | None,
) -> int:
    """SQLite C-engine authorizer allowing strictly read-only SELECT operations."""
    if action not in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and arg1:
        if arg1.lower() in _BLOCKED_FUNCTIONS:
            return sqlite3.SQLITE_DENY
    # Block direct reads from sqlite_temp_master or internal shadow manipulation
    if action == sqlite3.SQLITE_READ and arg1:
        lower_tbl = arg1.lower()
        if lower_tbl.startswith("sqlite_") and lower_tbl not in {
            "sqlite_master",
            "sqlite_schema",
        }:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    max_rows: int
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [dict(zip(self.columns, row)) for row in self.rows]


def execute_readonly_query(
    db_path: str | Path,
    sql: str,
    params: tuple[Any, ...] | list[Any] = (),
    *,
    max_rows: int = 1000,
    timeout_s: float = 15.0,
    cancel_event: threading.Event | None = None,
) -> QueryResult:
    """Execute a single read-only SQL query against ``db_path`` safely."""
    if max_rows < 1:
        raise ValueError("max_rows must be >= 1")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")

    cleaned_sql = (sql or "").strip()
    if not cleaned_sql:
        raise QueryExecutionError("SQL query must not be empty")

    con = connect_readonly(db_path)
    timed_out = False
    cancelled = False
    start = time.perf_counter()
    deadline = start + float(timeout_s)

    def _progress_watchdog() -> int:
        nonlocal timed_out, cancelled
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            return 1
        if time.perf_counter() >= deadline:
            timed_out = True
            return 1
        return 0

    try:
        con.set_authorizer(_readonly_authorizer)
        con.set_progress_handler(_progress_watchdog, 5_000)

        cursor = con.cursor()
        cursor.execute(cleaned_sql, tuple(params))
        if cursor.description is None:
            raise QueryExecutionError("Query did not return a result set")

        columns = [desc[0] for desc in cursor.description]
        fetched = cursor.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        if truncated:
            fetched = fetched[:max_rows]
        rows = [list(r) for r in fetched]
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return QueryResult(
            sql=cleaned_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            max_rows=max_rows,
            duration_ms=duration_ms,
        )
    except sqlite3.OperationalError as exc:
        if cancelled:
            raise QueryCancelledError("SQL query execution was cancelled") from exc
        if timed_out or "interrupted" in str(exc).lower():
            raise QueryTimeoutError(
                f"SQL query exceeded timeout of {timeout_s:.2f}s"
            ) from exc
        raise QueryExecutionError(f"SQL execution error: {exc}") from exc
    except sqlite3.DatabaseError as exc:
        if "not authorized" in str(exc).lower():
            raise QueryExecutionError(
                f"Operation blocked by read-only security policy: {exc}"
            ) from exc
        raise QueryExecutionError(f"Database error: {exc}") from exc
    finally:
        con.set_progress_handler(None, 0)
        con.close()

