"""Transaction-managed SQLite persistence manager and backup utility."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateIndex, CreateTable

from source.config.settings import get_project_root
from source.storage.models import Base


class DatabaseManager:
    """Manages SQLite connections, transactions, schema export, and backups."""

    def __init__(self, db_path: Optional[str | Path] = None):
        root = get_project_root()
        if db_path is None:
            self.db_path = root / "5_Data" / "sqlite" / "research.db"
        else:
            p = Path(db_path)
            self.db_path = p if p.is_absolute() else root / p
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()

        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)

    def init_db(self, export_schema: bool = True) -> None:
        """Create all tables and optionally write DDL to 5_Data/schemas/schema.sql."""
        Base.metadata.create_all(self.engine)
        if export_schema:
            schema_path = get_project_root() / "5_Data" / "schemas" / "schema.sql"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            ddl_lines: list[str] = []
            for table in Base.metadata.sorted_tables:
                ddl_lines.append(str(CreateTable(table).compile(self.engine)).strip() + ";")
                for idx in sorted(table.indexes, key=lambda x: x.name or ""):
                    ddl_lines.append(str(CreateIndex(idx).compile(self.engine)).strip() + ";")
            schema_path.write_text("\n\n".join(ddl_lines) + "\n", encoding="utf-8")

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Provide a transactional SQLAlchemy session."""
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def backup(self, backup_dir: Optional[str | Path] = None, label: str = "manual") -> Path:
        """Create a consistent SQLite hot backup using sqlite3 backup API."""
        root = get_project_root()
        target_dir = Path(backup_dir) if backup_dir else root / "5_Data" / "backups"
        if not target_dir.is_absolute():
            target_dir = root / target_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = target_dir / f"research_{label}_{stamp}.db"

        src_conn = sqlite3.connect(str(self.db_path))
        dst_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()
        return dest

    def get_table_counts(self) -> dict[str, int]:
        """Return row counts for every table in the schema."""
        counts: dict[str, int] = {}
        with self.engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}")).scalar_one()
                counts[table.name] = int(res)
        return counts
