"""Database migrations for SQLite Agent Memory."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1
MIGRATIONS_DIR = Path(__file__).resolve().parent


class MigrationError(RuntimeError):
    """Base exception for migration failures."""


class UnsupportedSchemaVersionError(MigrationError):
    """Raised when the database has a newer schema version than supported."""


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply all pending migrations to the database in order.

    Ensures foreign keys are enabled and runs each migration in an atomic transaction.
    Returns the final applied schema version.
    """
    conn.execute("PRAGMA foreign_keys = ON;")

    # 1. Ensure schema_migrations table exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
        );
        """
    )

    # 2. Get currently applied max version
    cursor = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations;")
    row = cursor.fetchone()
    current_version = row[0] if row else 0

    if current_version > CURRENT_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            f"Database schema version {current_version} is newer than supported version {CURRENT_SCHEMA_VERSION}. "
            "Please upgrade the application."
        )

    # 3. Apply pending migrations
    for version in range(current_version + 1, CURRENT_SCHEMA_VERSION + 1):
        migration_file = MIGRATIONS_DIR / f"{version:03d}_initial_schema.sql"
        if not migration_file.exists():
            # Fallback pattern search
            candidates = list(MIGRATIONS_DIR.glob(f"{version:03d}_*.sql"))
            if candidates:
                migration_file = candidates[0]
            else:
                raise MigrationError(f"Migration file for version {version} not found in {MIGRATIONS_DIR}")

        log.info("Applying migration %s...", migration_file.name)
        sql_script = migration_file.read_text(encoding="utf-8")

        # executescript handles transaction boundaries automatically in sqlite3
        safe_name = migration_file.name.replace("'", "''")
        full_script = f"{sql_script}\nINSERT INTO schema_migrations (version, name) VALUES ({version}, '{safe_name}');\n"

        try:
            conn.executescript(full_script)
            log.info("Migration %s applied successfully (version=%d).", migration_file.name, version)
        except Exception as exc:
            log.error("Migration %s failed: %s", migration_file.name, exc)
            raise MigrationError(f"Failed to apply migration {migration_file.name}: {exc}") from exc

    return CURRENT_SCHEMA_VERSION
