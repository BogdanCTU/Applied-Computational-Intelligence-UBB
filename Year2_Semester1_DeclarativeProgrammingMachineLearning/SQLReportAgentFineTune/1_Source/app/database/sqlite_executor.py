"""Sandboxed SQLite execution engine with read-only enforcement and timeouts."""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union


@dataclass
class QueryResult:
    """Encapsulates execution result from SQLite."""
    success: bool
    columns: List[str]
    rows: List[Tuple[Any, ...]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None


class SQLiteExecutor:
    """Executes SQL queries against local SQLite database files safely."""

    def __init__(self, db_path: Union[str, Path], timeout_seconds: float = 5.0):
        self.db_path = Path(db_path).resolve()
        self.timeout_seconds = timeout_seconds

    def _authorizer_readonly(self, action: int, arg1: Any, arg2: Any, dbname: Any, source: Any) -> int:
        """Denies any modifying actions (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)."""
        denied_actions = {
            sqlite3.SQLITE_INSERT,
            sqlite3.SQLITE_UPDATE,
            sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_DROP_TABLE,
            sqlite3.SQLITE_DROP_INDEX,
            sqlite3.SQLITE_DROP_VIEW,
            sqlite3.SQLITE_DROP_TRIGGER,
            sqlite3.SQLITE_ALTER_TABLE,
            sqlite3.SQLITE_CREATE_TABLE,
            sqlite3.SQLITE_CREATE_INDEX,
            sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_CREATE_TRIGGER,
        }
        if action in denied_actions:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def execute(self, query: str) -> QueryResult:
        """Executes a single read-only SQL query and returns result or error."""
        if not self.db_path.exists():
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=0.0,
                error=f"Database file not found: {self.db_path}",
            )

        start_time = time.perf_counter()
        uri_path = f"file:{self.db_path.as_posix()}?mode=ro"

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(uri_path, uri=True, timeout=self.timeout_seconds)
            conn.set_authorizer(self._authorizer_readonly)

            # Execution with progress handler for timeout abort
            deadline = time.time() + self.timeout_seconds

            def progress_handler() -> int:
                if time.time() > deadline:
                    return 1  # Abort query
                return 0

            conn.set_progress_handler(progress_handler, 1000)

            cursor = conn.cursor()
            cursor.execute(query)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return QueryResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(elapsed_ms, 2),
                error=None,
            )

        except sqlite3.OperationalError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=round(elapsed_ms, 2),
                error=f"OperationalError: {str(e)}",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=round(elapsed_ms, 2),
                error=f"ExecutionError: {str(e)}",
            )
        finally:
            if conn:
                conn.close()
