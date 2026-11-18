"""Schema extraction, DDL generation, and schema formatting."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_pk: bool = False
    not_null: bool = False
    default_value: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    column: str
    ref_table: str
    ref_column: str


@dataclass
class TableSchema:
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    sample_rows: List[Tuple] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    db_id: str
    tables: Dict[str, TableSchema] = field(default_factory=dict)

    def to_ddl(self) -> str:
        """Renders standard SQL DDL statements for all tables."""
        ddl_parts = []
        for t_name, table in self.tables.items():
            cols = []
            for col in table.columns:
                col_def = f"  {col.name} {col.data_type}"
                if col.is_pk:
                    col_def += " PRIMARY KEY"
                if col.not_null and not col.is_pk:
                    col_def += " NOT NULL"
                cols.append(col_def)

            for fk in table.foreign_keys:
                cols.append(f"  FOREIGN KEY ({fk.column}) REFERENCES {fk.ref_table}({fk.ref_column})")

            table_ddl = f"CREATE TABLE {t_name} (\n" + ",\n".join(cols) + "\n);"
            ddl_parts.append(table_ddl)
        return "\n\n".join(ddl_parts)

    def to_prompt_schema(self, include_samples: bool = False) -> str:
        """Renders a concise, prompt-optimized schema description."""
        lines = [f"Database Schema [{self.db_id}]:"]
        for t_name, table in self.tables.items():
            col_strs = []
            for col in table.columns:
                pk_marker = " [PK]" if col.is_pk else ""
                col_strs.append(f"{col.name} ({col.data_type}{pk_marker})")
            lines.append(f"- Table `{t_name}`: " + ", ".join(col_strs))
            for fk in table.foreign_keys:
                lines.append(f"  * FK: {t_name}.{fk.column} -> {fk.ref_table}.{fk.ref_column}")
        return "\n".join(lines)


class SchemaManager:
    """Manages schema extraction from SQLite files and synthetic DB creation."""

    @staticmethod
    def extract_schema_from_sqlite(db_path: Union[str, Path], db_id: Optional[str] = None) -> DatabaseSchema:
        """Connects to SQLite DB and inspects table definitions and foreign keys."""
        path = Path(db_path)
        identifier = db_id or path.stem

        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Get all table names (excluding sqlite internal tables)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        db_schema = DatabaseSchema(db_id=identifier)

        for table in tables:
            # Get columns
            cursor.execute(f"PRAGMA table_info({table});")
            col_info_rows = cursor.fetchall()
            columns = [
                ColumnInfo(
                    name=r[1],
                    data_type=r[2].upper() if r[2] else "TEXT",
                    not_null=bool(r[3]),
                    default_value=r[4],
                    is_pk=bool(r[5]),
                )
                for r in col_info_rows
            ]

            # Get Foreign Keys
            cursor.execute(f"PRAGMA foreign_key_list({table});")
            fk_rows = cursor.fetchall()
            foreign_keys = [
                ForeignKeyInfo(
                    column=r[3],
                    ref_table=r[2],
                    ref_column=r[4],
                )
                for r in fk_rows
            ]

            db_schema.tables[table] = TableSchema(
                name=table,
                columns=columns,
                foreign_keys=foreign_keys,
            )

        conn.close()
        return db_schema

    @staticmethod
    def create_database_from_ddl(db_path: Union[str, Path], ddl_script: str, initial_data: Optional[str] = None) -> Path:
        """Initializes a new standalone SQLite database with tables and sample data."""
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()

        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.executescript(ddl_script)
        if initial_data:
            cursor.executescript(initial_data)
        conn.commit()
        conn.close()
        return path
