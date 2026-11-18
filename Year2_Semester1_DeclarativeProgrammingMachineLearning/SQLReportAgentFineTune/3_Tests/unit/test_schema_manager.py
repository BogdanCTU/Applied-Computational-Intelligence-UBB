"""Unit tests for schema extraction, DDL generation, and prompt schema rendering."""

from pathlib import Path
from app.database.schema_manager import SchemaManager


def test_schema_manager_extract_and_format(tmp_path: Path):
    db_file = tmp_path / "company.db"
    ddl = """
    CREATE TABLE depts (dept_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE emps (emp_id INTEGER PRIMARY KEY, dept_id INTEGER, name TEXT, FOREIGN KEY (dept_id) REFERENCES depts(dept_id));
    """
    SchemaManager.create_database_from_ddl(db_file, ddl)

    schema = SchemaManager.extract_schema_from_sqlite(db_file, db_id="company")
    assert "depts" in schema.tables
    assert "emps" in schema.tables
    assert len(schema.tables["emps"].foreign_keys) == 1
    assert schema.tables["emps"].foreign_keys[0].ref_table == "depts"

    prompt_str = schema.to_prompt_schema()
    assert "Database Schema [company]:" in prompt_str
    assert "Table `emps`" in prompt_str
    assert "FK: emps.dept_id -> depts.dept_id" in prompt_str
