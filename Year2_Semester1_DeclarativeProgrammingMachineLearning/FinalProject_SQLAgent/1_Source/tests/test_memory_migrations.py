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
        "task_checkpoints",
        "recovery_attempts",
        "interrupted_operations",
    }
    for t in expected_tables:
        assert t in tables, f"Expected table '{t}' was not created by migration."


def test_migration_version_tracking(tmp_path: Path) -> None:
    db_file = tmp_path / "memory_version.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    with repo.connection() as conn:
        cur = conn.execute("SELECT version, name FROM schema_migrations ORDER BY version ASC;")
        rows = cur.fetchall()
        assert len(rows) == 3
        assert rows[0]["version"] == 1
        assert "001_initial_schema" in rows[0]["name"]
        assert rows[1]["version"] == 2
        assert "002_checkpoint_recovery" in rows[1]["name"]
        assert rows[2]["version"] == 3
        assert "003_skill_registry_enhancements" in rows[2]["name"]
        assert rows[-1]["version"] == CURRENT_SCHEMA_VERSION


def test_upgrade_from_v2_to_v3_preserves_data(tmp_path: Path) -> None:
    db_file = tmp_path / "upgrade_v2_to_v3.db"
    conn = sqlite3.connect(str(db_file), isolation_level=None)

    # 1. Apply up to version 2
    v2 = apply_migrations(conn, target_version=2)
    assert v2 == 2

    # 2. Seed v2 data in skill_registry
    conn.execute(
        """
        INSERT INTO skill_registry (skill_id, name, domain, version, file_path, created_at, updated_at)
        VALUES ('v2_skill', 'V2 Skill', 'sql', '1.0.0', 'skills/sql/v2.md', '2026-01-01T00:00:00', '2026-01-01T00:00:00');
        """
    )
    conn.close()

    # 3. Upgrade to v3 via SQLiteMemoryRepository
    repo = SQLiteMemoryRepository(db_path=db_file)
    with repo.connection() as c:
        cur = c.execute("SELECT MAX(version) FROM schema_migrations;")
        assert cur.fetchone()[0] == 3

        # Verify new column is_enabled exists and defaulted to 1
        cur = c.execute("SELECT skill_id, is_enabled FROM skill_registry WHERE skill_id = 'v2_skill';")
        row = cur.fetchone()
        assert row is not None
        assert row["skill_id"] == "v2_skill"
        assert row["is_enabled"] == 1


def test_upgrade_from_v1_to_v2_preserves_data(tmp_path: Path) -> None:
    db_file = tmp_path / "upgrade_v1_to_v2.db"
    conn = sqlite3.connect(str(db_file), isolation_level=None)

    # 1. Apply only version 1
    v1 = apply_migrations(conn, target_version=1)
    assert v1 == 1

    # 2. Seed v1 data
    conn.execute(
        """
        INSERT INTO task_runs (task_id, user_request, status, created_at, updated_at)
        VALUES ('task_v1', 'Legacy v1 request', 'RUNNING', '2026-01-01T00:00:00', '2026-01-01T00:00:00');
        """
    )
    conn.execute(
        """
        INSERT INTO task_decisions (decision_id, task_id, decision_type, summary, created_at)
        VALUES ('dec_v1', 'task_v1', 'sql_choice', 'Use index', '2026-01-01T00:00:00');
        """
    )
    conn.close()

    # 3. Reopen via SQLiteMemoryRepository which auto-migrates to CURRENT_SCHEMA_VERSION
    repo = SQLiteMemoryRepository(db_path=db_file)
    with repo.connection() as c:
        cur = c.execute("SELECT MAX(version) FROM schema_migrations;")
        assert cur.fetchone()[0] == CURRENT_SCHEMA_VERSION

        # Check new tables exist
        cur = c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {r[0] for r in cur.fetchall()}
        assert "task_checkpoints" in tables
        assert "recovery_attempts" in tables
        assert "interrupted_operations" in tables

    # 4. Verify existing v1 records are preserved
    task = repo.get("task_v1")
    assert task is not None
    assert task.user_request == "Legacy v1 request"
    decisions = repo.get_decisions("task_v1")
    assert len(decisions) == 1
    assert decisions[0].summary == "Use index"


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


def test_migration_failure_leaves_no_partial_tables(tmp_path: Path) -> None:
    mig_dir = tmp_path / "custom_migrations"
    mig_dir.mkdir()

    # Create a broken migration that creates table_alpha then fails on syntax error
    broken_sql = mig_dir / "001_broken_migration.sql"
    broken_sql.write_text(
        """
        CREATE TABLE table_alpha (id INTEGER PRIMARY KEY, name TEXT);
        THIS IS INVALID SQL STATEMENT SYNTAX ERROR;
        CREATE TABLE table_beta (id INTEGER PRIMARY KEY, name TEXT);
        """,
        encoding="utf-8",
    )

    db_file = tmp_path / "mig_fail.db"
    conn = sqlite3.connect(str(db_file), isolation_level=None)

    with pytest.raises(MigrationError) as exc_info:
        apply_migrations(conn, migrations_dir=mig_dir, target_version=1)
    assert "Failed to apply migration" in str(exc_info.value)

    # Verify that table_alpha was NOT created (rolled back completely)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    assert "table_alpha" not in tables
    assert "table_beta" not in tables

    # Verify schema_migrations contains 0 records
    cur = conn.execute("SELECT COUNT(*) FROM schema_migrations;")
    assert cur.fetchone()[0] == 0

    # Fix migration file and verify retry succeeds cleanly
    fixed_sql = mig_dir / "001_broken_migration.sql"
    fixed_sql.write_text(
        """
        CREATE TABLE table_alpha (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE table_beta (id INTEGER PRIMARY KEY, name TEXT);
        """,
        encoding="utf-8",
    )

    applied_version = apply_migrations(conn, migrations_dir=mig_dir, target_version=1)
    assert applied_version == 1

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    assert "table_alpha" in tables
    assert "table_beta" in tables

    cur = conn.execute("SELECT COUNT(*) FROM schema_migrations;")
    assert cur.fetchone()[0] == 1

    conn.close()
