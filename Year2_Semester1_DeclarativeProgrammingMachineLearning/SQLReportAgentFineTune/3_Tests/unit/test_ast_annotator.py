"""Unit tests for AST Schema Annotator, alias resolution, relationship validation, and parsing."""

from app.database.schema_manager import ColumnInfo, DatabaseSchema, ForeignKeyInfo, TableSchema
from app.datasets.ast_annotator import ASTSchemaAnnotator


def _create_mock_schema() -> DatabaseSchema:
    schema = DatabaseSchema(db_id="test_company")
    schema.tables["departments"] = TableSchema(
        name="departments",
        columns=[
            ColumnInfo(name="dept_id", data_type="INTEGER", is_pk=True),
            ColumnInfo(name="dept_name", data_type="TEXT"),
        ],
    )
    schema.tables["employees"] = TableSchema(
        name="employees",
        columns=[
            ColumnInfo(name="emp_id", data_type="INTEGER", is_pk=True),
            ColumnInfo(name="first_name", data_type="TEXT"),
            ColumnInfo(name="last_name", data_type="TEXT"),
            ColumnInfo(name="dept_id", data_type="INTEGER"),
            ColumnInfo(name="salary", data_type="REAL"),
        ],
        foreign_keys=[
            ForeignKeyInfo(column="dept_id", ref_table="departments", ref_column="dept_id"),
        ],
    )
    schema.tables["salaries"] = TableSchema(
        name="salaries",
        columns=[
            ColumnInfo(name="salary_id", data_type="INTEGER", is_pk=True),
            ColumnInfo(name="emp_id", data_type="INTEGER"),
            ColumnInfo(name="amount", data_type="REAL"),
        ],
        foreign_keys=[
            ForeignKeyInfo(column="emp_id", ref_table="employees", ref_column="emp_id"),
        ],
    )
    return schema


def test_ast_annotator_alias_and_relationship_resolution():
    schema = _create_mock_schema()
    annotator = ASTSchemaAnnotator()

    sql = (
        "SELECT T1.first_name, T2.dept_name FROM employees AS T1 "
        "JOIN departments AS T2 ON T1.dept_id = T2.dept_id WHERE T1.salary > 80000;"
    )

    res = annotator.annotate(sql, schema)
    assert res.status == "success"
    assert res.tables == ["departments", "employees"]
    assert "departments.dept_name" in res.columns
    assert "employees.first_name" in res.columns
    assert "employees.salary" in res.columns
    assert "employees.dept_id" in res.columns
    assert "departments.dept_id = employees.dept_id" in res.relationships
    assert res.foreign_key_validated_count >= 1


def test_ast_annotator_unqualified_column_resolution():
    schema = _create_mock_schema()
    annotator = ASTSchemaAnnotator()

    sql = "SELECT first_name, salary FROM employees WHERE salary > 50000;"
    res = annotator.annotate(sql, schema)
    assert res.status == "success"
    assert res.tables == ["employees"]
    assert "employees.first_name" in res.columns
    assert "employees.salary" in res.columns
    assert res.relationships == []


def test_ast_annotator_ambiguous_column_detection():
    schema = _create_mock_schema()
    annotator = ASTSchemaAnnotator()

    # dept_id is in both employees and departments without table qualifier
    sql = "SELECT dept_id FROM employees JOIN departments;"
    res = annotator.annotate(sql, schema)
    # Ambiguous reference should be flagged in unresolved columns
    assert any("AMBIGUOUS:dept_id" in c for c in res.unresolved_columns)
    assert res.status == "partial"


def test_structured_target_serialization_and_parsing_roundtrip():
    tables = ["departments", "employees"]
    cols = ["departments.dept_name", "employees.first_name"]
    rels = ["departments.dept_id = employees.dept_id"]
    sql = "SELECT T1.first_name FROM employees T1 JOIN departments T2 ON T1.dept_id = T2.dept_id;"

    serialized = ASTSchemaAnnotator.serialize_target(tables, cols, rels, sql)
    assert "<SCHEMA_SELECTION>" in serialized
    assert "TABLES: departments, employees" in serialized
    assert "COLUMNS: departments.dept_name, employees.first_name" in serialized
    assert "RELATIONSHIPS: departments.dept_id = employees.dept_id" in serialized
    assert "<SQL>" in serialized

    t_out, c_out, r_out, sql_out = ASTSchemaAnnotator.parse_structured_output(serialized)
    assert t_out == tables
    assert c_out == cols
    assert r_out == rels
    assert sql_out.strip() == sql.strip()
