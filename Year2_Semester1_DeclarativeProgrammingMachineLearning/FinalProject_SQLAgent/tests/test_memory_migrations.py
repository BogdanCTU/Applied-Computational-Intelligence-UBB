"""Unit tests for SQLite Memory migrations, version tracking, idempotency, and safety guards."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from config.paths import resolve_path
from memory.migrations import (
    CURRENT_SCHEMA_VERSION,
    MigrationError,
    UnsupportedSchemaVersionError,
    apply_migrations,
)
from memory.repository import SQLiteMemoryRepository


def test_initial_migration_creates_all_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_test.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    with repo.connection() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = {row[0] for row in cur.fetchall()}

    expected_tables = {
        "schema_migrations",
        "task_runs",
        "task_steps",
        "task_plans",
        "task_decisions",
        "task_tool_calls",
        "task_artifacts",
        "semantic_facts",
        "skill_registry",
    }
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not created by migration."


def test_migration_version_tracking(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_version.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    with repo.connection() as conn:
        cur = conn.execute("SELECT version, name FROM schema_migrations;")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["version"] == CURRENT_SCHEMA_VERSION
        assert "001_initial_schema" in rows[0]["name"]


def test_repeated_initialization_is_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_repeat.db"
    repo1 = SQLiteMemoryRepository(db_path=db_file)
    v1 = repo1.initialize_schema()

    # Re-initialize on existing database
    repo2 = SQLiteMemoryRepository(db_path=db_file)
    v2 = repo2.initialize_schema()

    assert v1 == CURRENT_SCHEMA_VERSION
    assert v2 == CURRENT_SCHEMA_VERSION


def test_unsupported_future_version_raises(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_future.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
        );
        """
    )
    conn.execute("INSERT INTO schema_migrations (version, name) VALUES (999, 'future_migration.sql');")
    conn.commit()
    conn.close()

    # Reopening repository on a future schema version must raise UnsupportedSchemaVersionError
    with pytest.raises(UnsupportedSchemaVersionError) as exc_info:
        SQLiteMemoryRepository(db_path=db_file)
    assert "is newer than supported version" in str(exc_info.value)


def test_transaction_rollback_on_error(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_rollback.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    # Attempt a transaction that raises halfway through
    with pytest.raises(RuntimeError):
        with repo.transaction() as conn:
            conn.execute(
                "INSERT INTO task_runs (task_id, user_request, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?);",
                ("t_rollback", "Rollback test", "PENDING", "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
            )
            raise RuntimeError("Intentional error to trigger rollback")

    # Verify task was rolled back
    with repo.connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM task_runs WHERE task_id = 't_rollback';")
        assert cur.fetchone()[0] == 0


def test_cannot_target_ecommerce_db() -> None:
    ecommerce_db = resolve_path("data/ecommerce.db")
    with pytest.raises(ValueError) as exc_info:
        SQLiteMemoryRepository(db_path=ecommerce_db)
    assert "Cannot use" in str(exc_info.value)
    assert "ecommerce database is strictly read-only" in str(exc_info.value)
