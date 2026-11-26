"""Database connection and lifecycle management."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from database.schema import CREATE_TABLES_SQL


class Database:
    """SQLite database manager with WAL mode, transaction helper, and safe migrations."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with foreign keys enabled and row factory."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing a transactional connection."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Execute schema creation statements and apply non-destructive column additions."""
        with self.session() as conn:
            self._apply_migrations(conn)
            conn.executescript(CREATE_TABLES_SQL)
            self._apply_migrations(conn)

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        """Safely add new columns to existing tables if missing."""
        migrations = [
            ("repositories", "description", "TEXT"),
            ("repositories", "license", "TEXT"),
            ("repositories", "language", "TEXT DEFAULT 'C#'"),
            ("repositories", "default_branch", "TEXT DEFAULT 'main'"),
            ("repositories", "stars", "INTEGER DEFAULT 0"),
            ("repositories", "forks", "INTEGER DEFAULT 0"),
            ("repositories", "size_kb", "INTEGER DEFAULT 0"),
            ("repositories", "is_cloned", "INTEGER DEFAULT 0"),
            ("repositories", "local_path", "TEXT"),
            ("repositories", "status", "TEXT DEFAULT 'registered'"),
            ("repositories", "last_sync_at", "TIMESTAMP"),
            ("repositories", "collected_at", "TIMESTAMP"),
            ("repositories", "updated_at", "TIMESTAMP"),
            ("repositories", "selection_score", "REAL DEFAULT 0.0"),
            ("repositories", "selection_rank", "INTEGER"),
            ("repositories", "selection_reason", "TEXT"),
            ("repositories", "exclusion_reason", "TEXT"),
            ("repositories", "is_selected", "INTEGER DEFAULT 1"),
            ("repositories", "is_fork", "INTEGER DEFAULT 0"),
            ("repositories", "is_archived", "INTEGER DEFAULT 0"),
            ("repositories", "pushed_at", "TEXT"),
            ("repositories", "created_at_gh", "TEXT"),
            ("repositories", "production_cs_files_count", "INTEGER DEFAULT 0"),
            ("repositories", "commits_mined_count", "INTEGER DEFAULT 0"),
            ("repositories", "bug_fixes_count", "INTEGER DEFAULT 0"),
            ("repositories", "szz_traces_count", "INTEGER DEFAULT 0"),
            ("repositories", "class_observations_count", "INTEGER DEFAULT 0"),
            ("repositories", "processing_error", "TEXT"),
            ("repositories", "collection_run_id", "TEXT"),
            ("commits", "parent_shas", "TEXT"),
            ("commits", "committer_date", "TIMESTAMP"),
            ("commits", "files_changed_count", "INTEGER DEFAULT 0"),
            ("commits", "insertions", "INTEGER DEFAULT 0"),
            ("commits", "deletions", "INTEGER DEFAULT 0"),
            ("commits", "modifies_csharp", "INTEGER DEFAULT 0"),
            ("commits", "review_status", "TEXT DEFAULT 'unreviewed'"),
            ("observations", "review_status", "TEXT DEFAULT 'unreviewed'"),
            ("features", "logical_loc", "INTEGER DEFAULT 0"),
            ("features", "parameter_count", "INTEGER DEFAULT 0"),
            ("features", "local_variable_count", "INTEGER DEFAULT 0"),
            ("features", "statement_count", "INTEGER DEFAULT 0"),
            ("features", "return_count", "INTEGER DEFAULT 0"),
            ("features", "boolean_operator_count", "INTEGER DEFAULT 0"),
            ("features", "logical_operator_count", "INTEGER DEFAULT 0"),
            ("features", "conditional_expression_count", "INTEGER DEFAULT 0"),
            ("features", "if_count", "INTEGER DEFAULT 0"),
            ("features", "switch_count", "INTEGER DEFAULT 0"),
            ("features", "loop_count", "INTEGER DEFAULT 0"),
            ("features", "try_catch_count", "INTEGER DEFAULT 0"),
            ("features", "throw_count", "INTEGER DEFAULT 0"),
            ("features", "break_continue_count", "INTEGER DEFAULT 0"),
            ("features", "method_call_count", "INTEGER DEFAULT 0"),
            ("features", "field_access_count", "INTEGER DEFAULT 0"),
            ("features", "property_access_count", "INTEGER DEFAULT 0"),
            ("features", "assignment_count", "INTEGER DEFAULT 0"),
            ("features", "object_creation_count", "INTEGER DEFAULT 0"),
            ("features", "status", "TEXT DEFAULT 'success'"),
            ("features", "error_message", "TEXT"),
            ("features", "analyzer_version", "TEXT DEFAULT '1.0.0'"),
            ("datasets", "granularity", "TEXT DEFAULT 'method'"),
            ("datasets", "repository_count", "INTEGER DEFAULT 0"),
            ("datasets", "feature_schema_version", "TEXT DEFAULT '1.0.0'"),
            ("datasets", "manifest_path", "TEXT"),
            ("datasets", "sha256_checksum", "TEXT"),
            ("models", "version", "TEXT DEFAULT '1.0.0'"),
            ("models", "granularity", "TEXT DEFAULT 'method'"),
            ("models", "decision_threshold", "REAL DEFAULT 0.50"),
            ("models", "dataset_version", "TEXT"),
            ("models", "threshold_selection_criterion", "TEXT"),
            ("predictions", "model_id", "INTEGER"),
            ("predictions", "created_at", "TIMESTAMP"),
            ("predictions", "granularity", "TEXT DEFAULT 'method'"),
            ("predictions", "dataset_version", "TEXT"),
            ("predictions", "decision_threshold", "REAL DEFAULT 0.50"),
            ("predictions", "namespace_name", "TEXT"),
            ("predictions", "start_line", "INTEGER"),
            ("predictions", "end_line", "INTEGER"),
            ("predictions", "method_count", "INTEGER"),
            ("predictions", "loc", "INTEGER"),
            ("predictions", "cyclomatic_complexity", "INTEGER"),
            ("predictions", "file_summary_json", "TEXT"),
            ("predictions", "classification_label", "TEXT"),
            ("predictions", "localization_json", "TEXT"),
            ("class_observations", "localization_status", "TEXT DEFAULT 'unavailable'"),
            ("class_observations", "affected_methods_json", "TEXT"),
            ("class_observations", "affected_line_ranges_json", "TEXT"),
        ]
        for table, col, col_type in migrations:
            try:
                rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
                if not rows:
                    continue
                cols = [row["name"] for row in rows]
                if col not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
            except Exception:
                pass
