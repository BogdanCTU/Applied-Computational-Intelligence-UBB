"""SQLite connection manager and migration runner."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _migrations_dir() -> Path:
    return Path(__file__).resolve().parent / "migrations"


class DatabaseManager:
    """Thread-safe per-call SQLite connection manager with WAL and foreign keys."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def run_migrations(db_path: Path) -> list[str]:
    """Apply pending SQL migrations in deterministic filename order."""
    db = DatabaseManager(db_path)
    migrations_dir = _migrations_dir()
    sql_files = sorted(migrations_dir.glob("*.sql"))
    applied_now: list[str] = []

    with db.transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            );
            """
        )
        existing = {
            row["migration_id"]
            for row in conn.execute("SELECT migration_id FROM schema_migrations").fetchall()
        }
        for sql_file in sql_files:
            mig_id = sql_file.name
            if mig_id in existing:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (migration_id) VALUES (?)",
                (mig_id,),
            )
            applied_now.append(mig_id)
    return applied_now
