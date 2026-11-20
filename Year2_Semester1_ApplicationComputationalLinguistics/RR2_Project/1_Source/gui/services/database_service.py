"""PostgreSQL + pgvector inspection, isolated DB provisioning, and write-mutex service."""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2 import sql as pgsql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ...config import PROTECTED_DATABASES, validate_loopback_host
from ...db.database_manager import DatabaseManager


class DatabaseService:
    """Manages loopback PostgreSQL health checks, table inspection, and concurrency locks."""

    _locks_guard = threading.Lock()
    _db_locks: Dict[str, threading.Lock] = {}

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5432,
        user: str = "postgres",
        password: str = "",
    ):
        self.host = validate_loopback_host(host)
        self.port = int(port)
        self.user = user
        self.password = password

    def dsn_for(self, db_name: str) -> str:
        validate_loopback_host(self.host)
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{db_name}"

    @classmethod
    def acquire_db_lock(cls, db_name: str, blocking: bool = False) -> bool:
        """Acquire an exclusive process-wide lock for writing to `db_name`."""
        with cls._locks_guard:
            if db_name not in cls._db_locks:
                cls._db_locks[db_name] = threading.Lock()
            lock = cls._db_locks[db_name]
        return lock.acquire(blocking=blocking)

    @classmethod
    def release_db_lock(cls, db_name: str) -> None:
        """Release the write lock for `db_name` if held."""
        with cls._locks_guard:
            lock = cls._db_locks.get(db_name)
        if lock is not None and lock.locked():
            try:
                lock.release()
            except RuntimeError:
                pass

    def check_server_health(self) -> Dict[str, Any]:
        """Connect to `postgres` maintenance DB on 127.0.0.1 and inspect databases + pgvector."""
        try:
            conn = psycopg2.connect(self.dsn_for("postgres"), connect_timeout=3)
            try:
                with conn.cursor() as cur:
                    cur.execute("SHOW server_version;")
                    server_ver = str(cur.fetchone()[0])
                    cur.execute("SHOW listen_addresses;")
                    listen_addr = str(cur.fetchone()[0])
                    cur.execute(
                        "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
                    )
                    dbs = [str(r[0]) for r in cur.fetchall()]
                    cur.execute(
                        "SELECT default_version FROM pg_available_extensions WHERE name = 'vector';"
                    )
                    ext_row = cur.fetchone()
                    pgvec_ver = str(ext_row[0]) if ext_row else None
                return {
                    "reachable": True,
                    "host": self.host,
                    "port": self.port,
                    "server_version": f"PostgreSQL {server_ver}",
                    "listen_addresses": listen_addr,
                    "pgvector_available": pgvec_ver is not None,
                    "pgvector_version": pgvec_ver,
                    "databases": dbs,
                    "protected_databases": sorted(PROTECTED_DATABASES),
                }
            finally:
                conn.close()
        except Exception as exc:
            return {
                "reachable": False,
                "host": self.host,
                "port": self.port,
                "error": str(exc),
                "databases": [],
                "protected_databases": sorted(PROTECTED_DATABASES),
            }

    def inspect_database(self, db_name: str) -> Dict[str, Any]:
        """Return row counts and vector dimensions for an Agent-OM database."""
        is_protected = db_name in PROTECTED_DATABASES
        try:
            mgr = DatabaseManager(self.dsn_for(db_name))
            counts = mgr.get_table_row_counts()
            dims: Dict[str, Optional[str]] = {}
            conn = psycopg2.connect(self.dsn_for(db_name), connect_timeout=3)
            try:
                with conn.cursor() as cur:
                    for tbl in ("syntactic_matching", "lexical_matching", "semantic_matching"):
                        cur.execute(
                            """
                            SELECT format_type(a.atttypid, a.atttypmod)
                            FROM pg_attribute a
                            JOIN pg_class c ON a.attrelid = c.oid
                            JOIN pg_namespace n ON c.relnamespace = n.oid
                            WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = 'embedding';
                            """,
                            (tbl,),
                        )
                        row = cur.fetchone()
                        dims[tbl] = str(row[0]) if row else None
            finally:
                conn.close()
            return {
                "database": db_name,
                "reachable": True,
                "protected": is_protected,
                "row_counts": counts,
                "vector_types": dims,
            }
        except Exception as exc:
            return {
                "database": db_name,
                "reachable": False,
                "protected": is_protected,
                "error": str(exc),
                "row_counts": {},
                "vector_types": {},
            }

    def create_isolated_database(self, db_name: str) -> Dict[str, Any]:
        """Safely create a new isolated database and enable `pgvector`."""
        cleaned = str(db_name).strip()
        if not cleaned or not cleaned.replace("_", "").isalnum():
            raise ValueError(f"Invalid database identifier '{cleaned}'. Use alphanumeric and underscores.")
        if cleaned in PROTECTED_DATABASES:
            raise PermissionError(f"Database '{cleaned}' is protected and already exists.")
        mgr = DatabaseManager(self.dsn_for(cleaned))
        mgr.ensure_database_exists()
        mgr.init_extensions()
        return self.inspect_database(cleaned)

