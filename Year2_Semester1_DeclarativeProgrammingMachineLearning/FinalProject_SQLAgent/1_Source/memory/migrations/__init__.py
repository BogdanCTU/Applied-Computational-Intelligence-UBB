"""Database migrations for SQLite Agent Memory."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 3
MIGRATIONS_DIR = Path(__file__).resolve().parent


def get_default_migrations_dir() -> Path:
    """Resolve directory containing SQL migration files, handling both source and frozen apps."""
    try:
        from config.paths import app_root, is_frozen, resource_root

        if is_frozen():
            for alt in [
                resource_root() / "memory" / "migrations",
                resource_root() / "migrations",
                app_root() / "memory" / "migrations",
            ]:
                if alt.exists() and any(alt.glob("*.sql")):
                    return alt
    except Exception:
        pass

    cand = Path(__file__).resolve().parent
    if cand.exists() and any(cand.glob("*.sql")):
        return cand
    return cand


class MigrationError(RuntimeError):
    """Base exception for migration failures."""


class UnsupportedSchemaVersionError(MigrationError):
    """Raised when the database has a newer schema version than supported."""


def apply_migrations(
    conn: sqlite3.Connection,
    *,
    migrations_dir: Path | None = None,
    target_version: int | None = None,
) -> int:
    """Apply all pending migrations to the database in order.

    Ensures foreign keys are enabled and runs each migration in an atomic transaction.
    Returns the final applied schema version.
    """
    target_dir = migrations_dir or get_default_migrations_dir()
    max_target = target_version if target_version is not None else CURRENT_SCHEMA_VERSION

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

    if current_version > max_target:
        raise UnsupportedSchemaVersionError(
            f"Database schema version {current_version} is newer than supported version {max_target}. "
            "Please upgrade the application."
        )

    # 3. Apply pending migrations
    for version in range(current_version + 1, max_target + 1):
        candidates = list(target_dir.glob(f"{version:03d}_*.sql"))
        if candidates:
            migration_file = candidates[0]
        else:
            raise MigrationError(f"Migration file for version {version} not found in {target_dir}")

        log.info("Applying migration %s...", migration_file.name)
        sql_script = migration_file.read_text(encoding="utf-8")

        # Guarantee atomic DDL execution: wrap in explicit BEGIN TRANSACTION / COMMIT block.
        # If any DDL or DML statement fails halfway through, the entire script rolls back cleanly,
        # leaving zero partial tables and zero recorded migration versions.
        safe_name = migration_file.name.replace("'", "''")
        full_script = (
            f"BEGIN TRANSACTION;\n"
            f"{sql_script}\n"
            f"INSERT INTO schema_migrations (version, name) VALUES ({version}, '{safe_name}');\n"
            f"COMMIT;\n"
        )

        try:
            conn.executescript(full_script)
            log.info("Migration %s applied successfully (version=%d).", migration_file.name, version)
        except Exception as exc:
            try:
                conn.execute("ROLLBACK;")
            except sqlite3.OperationalError:
                pass
            log.error("Migration %s failed: %s", migration_file.name, exc)
            raise MigrationError(f"Failed to apply migration {migration_file.name}: {exc}") from exc

    cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations;")
    row = cur.fetchone()
    return int(row[0]) if row else 0
