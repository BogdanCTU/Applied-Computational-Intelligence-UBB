"""Unit tests for SQLite safe execution sandbox and read-only authorizer."""

import sqlite3
from pathlib import Path
from app.database.sqlite_executor import SQLiteExecutor


def test_sqlite_executor_successful_query(tmp_path: Path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');")
    conn.commit()
    conn.close()

    executor = SQLiteExecutor(db_file)
    res = executor.execute("SELECT id, name FROM users ORDER BY id ASC")
    assert res.success is True
    assert res.columns == ["id", "name"]
    assert res.row_count == 2
    assert res.rows == [(1, "Alice"), (2, "Bob")]
    assert res.error is None
    assert res.execution_time_ms >= 0


def test_sqlite_executor_blocks_mutation(tmp_path: Path):
    db_file = tmp_path / "test_mutate.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    conn.commit()
    conn.close()

    executor = SQLiteExecutor(db_file)
    res = executor.execute("INSERT INTO users VALUES (3, 'Mallory')")
    assert res.success is False
    assert "not authorized" in str(res.error).lower() or "operationalerror" in str(res.error).lower()


def test_sqlite_executor_handles_syntax_error(tmp_path: Path):
    db_file = tmp_path / "test_syntax.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (x INT);")
    conn.commit()
    conn.close()

    executor = SQLiteExecutor(db_file)
    res = executor.execute("SELECT FROM WHERE BAD SQL")
    assert res.success is False
    assert res.error is not None
