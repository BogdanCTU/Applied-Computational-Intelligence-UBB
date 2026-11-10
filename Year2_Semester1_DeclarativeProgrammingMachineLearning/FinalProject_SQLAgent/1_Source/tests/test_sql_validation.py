"""Automated Pytest suite for SQL validation, preparation, and read-only execution."""

from __future__ import annotations

import csv
import time
from pathlib import Path

import pytest

from config.settings import AppSettings
from database import import_dataset
from mcp_layer.tools.sql_tools import (
    SQLValidationError,
    execute_readonly_sql_impl,
    prepare_sql_query_impl,
    validate_and_prepare_sql,
)


@pytest.fixture()
def temp_sql_env(tmp_path: Path) -> tuple[Path, AppSettings]:
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()
    with (csv_dir / "customers.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["customer_id", "first_name", "country"])
        w.writerows([[1, "Alice", "USA"], [2, "Bob", "UK"], [3, "Cara", "USA"]])

    with (csv_dir / "orders.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["order_id", "customer_id", "status", "total_amount"])
        w.writerows(
            [
                [10, 1, "delivered", "120.50"],
                [11, 1, "shipped", "80.00"],
                [12, 2, "delivered", "45.25"],
                [13, 3, "cancelled", "15.00"],
            ]
        )

    db_path = tmp_path / "test.db"
    import_dataset(csv_dir, db_path)

    settings = AppSettings()
    settings.database.path = str(db_path)
    settings.database.max_result_rows = 100
    settings.database.query_timeout_s = 2.0
    settings.reports.output_dir = str(tmp_path / "reports")
    return db_path, settings


def test_valid_select_and_string_literals_with_keywords(
    temp_sql_env: tuple[Path, AppSettings],
) -> None:
    db_path, _ = temp_sql_env
    # String literal contains semicolons and DDL words — lexer must allow it!
    sql = """
    -- Leading comment
    SELECT c.country, COUNT(o.order_id) AS cnt
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.status != 'DROP TABLE; DELETE FROM orders' /* inline comment */
    GROUP BY c.country
    ORDER BY cnt DESC;
    """
    prepared = validate_and_prepare_sql(sql, db_path=db_path)
    assert prepared.valid is True
    assert prepared.statement_type == "SELECT"
    assert not prepared.sql_query.endswith(";")
    assert set(prepared.referenced_tables) == {"customers", "orders"}
    assert "customers.country" in prepared.referenced_columns


def test_valid_cte_and_multi_cte_queries(
    temp_sql_env: tuple[Path, AppSettings],
) -> None:
    db_path, _ = temp_sql_env
    sql = """
    WITH delivered_orders AS (
        SELECT customer_id, total_amount
        FROM orders
        WHERE status = 'delivered'
    ),
    customer_totals (cid, spend) AS NOT MATERIALIZED (
        SELECT customer_id, SUM(total_amount)
        FROM delivered_orders
        GROUP BY customer_id
    )
    SELECT c.first_name, ct.spend
    FROM customer_totals ct
    JOIN customers c ON c.customer_id = ct.cid
    ORDER BY ct.spend DESC
    """
    prepared = validate_and_prepare_sql(sql, db_path=db_path)
    assert prepared.valid is True
    assert prepared.statement_type == "CTE_SELECT"
    assert set(prepared.referenced_tables) == {"orders", "customers"}


def test_prepare_sql_query_does_not_execute_sql(
    temp_sql_env: tuple[Path, AppSettings],
) -> None:
    _, settings = temp_sql_env
    # If this recursive CTE were executed, it would iterate 100M times and time out.
    heavy_cte = """
    WITH RECURSIVE huge(n) AS (
        SELECT 1
        UNION ALL
        SELECT n + 1 FROM huge WHERE n < 100000000
    )
    SELECT COUNT(*) FROM huge
    """
    t0 = time.perf_counter()
    resp = prepare_sql_query_impl(settings, heavy_cte)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert resp["status"] == "ok"
    assert resp["valid"] is True
    assert elapsed_ms < 250.0  # Compiles via EXPLAIN QUERY PLAN in <1ms without running


@pytest.mark.parametrize(
    ("bad_sql", "expected_code"),
    [
        ("", "EMPTY_QUERY"),
        ("   -- just a comment\n /* nothing */ ", "EMPTY_QUERY"),
        ("SELECT 1; SELECT 2", "MULTIPLE_STATEMENTS"),
        ("SELECT * FROM orders; DROP TABLE orders;", "MULTIPLE_STATEMENTS"),
        ("INSERT INTO customers VALUES (9, 'X', 'US')", "FORBIDDEN_STATEMENT"),
        ("UPDATE orders SET total_amount = 0", "FORBIDDEN_STATEMENT"),
        ("DELETE FROM orders WHERE order_id = 10", "FORBIDDEN_STATEMENT"),
        ("DROP TABLE orders", "FORBIDDEN_STATEMENT"),
        ("ALTER TABLE orders ADD COLUMN note TEXT", "FORBIDDEN_STATEMENT"),
        ("CREATE TABLE rogue (id INT)", "FORBIDDEN_STATEMENT"),
        ("REPLACE INTO customers VALUES (1, 'X', 'US')", "FORBIDDEN_STATEMENT"),
        ("ATTACH DATABASE ':memory:' AS aux", "FORBIDDEN_STATEMENT"),
        ("DETACH DATABASE aux", "FORBIDDEN_STATEMENT"),
        ("PRAGMA table_info(orders)", "FORBIDDEN_STATEMENT"),
        ("VACUUM", "FORBIDDEN_STATEMENT"),
        ("BEGIN TRANSACTION", "FORBIDDEN_STATEMENT"),
        ("EXPLAIN SELECT * FROM orders", "FORBIDDEN_STATEMENT"),
        (
            "WITH x AS (SELECT 1) DELETE FROM orders WHERE order_id = 10",
            "FORBIDDEN_STATEMENT",
        ),
        ("SELECT load_extension('evil.so')", "FORBIDDEN_FUNCTION"),
        ("SELECT 'unclosed literal FROM orders", "SYNTAX_ERROR"),
        ('SELECT "unclosed_ident FROM orders', "SYNTAX_ERROR"),
        ("SELECT /* unclosed comment FROM orders", "SYNTAX_ERROR"),
        ("SELECT (1 + 2 FROM orders", "SYNTAX_ERROR"),
        ("SELECT FROM WHERE", "SYNTAX_ERROR"),
        ("SELECT * FROM nonexistent_table", "SCHEMA_ERROR"),
        ("SELECT nonexistent_col FROM orders", "SCHEMA_ERROR"),
        (
            "SELECT customer_id FROM orders JOIN customers ON orders.customer_id = customers.customer_id",
            "SCHEMA_ERROR",
        ),
    ],
)
def test_invalid_and_unsafe_queries_rejected(
    temp_sql_env: tuple[Path, AppSettings],
    bad_sql: str,
    expected_code: str,
) -> None:
    db_path, _ = temp_sql_env
    with pytest.raises(SQLValidationError) as exc_info:
        validate_and_prepare_sql(bad_sql, db_path=db_path)
    assert exc_info.value.error_code == expected_code


def test_complexity_limits_enforced(temp_sql_env: tuple[Path, AppSettings]) -> None:
    db_path, _ = temp_sql_env

    # Excessive JOIN count
    many_joins = "SELECT o0.order_id FROM orders o0 " + " ".join(
        f"JOIN orders o{i} ON o{i}.order_id = o0.order_id" for i in range(1, 15)
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validate_and_prepare_sql(many_joins, db_path=db_path)
    assert exc_info.value.error_code == "COMPLEXITY_LIMIT"

    # Excessive subquery nesting (> MAX_SUBQUERY_DEPTH = 10)
    nested_subq = "SELECT 1"
    for _ in range(12):
        nested_subq = f"SELECT * FROM ({nested_subq})"
    with pytest.raises(SQLValidationError) as exc_info2:
        validate_and_prepare_sql(nested_subq, db_path=db_path)
    assert exc_info2.value.error_code == "COMPLEXITY_LIMIT"

    # Excessive parenthesis depth (> MAX_PAREN_DEPTH = 30)
    deep_parens = "SELECT " + "(" * 35 + "1" + ")" * 35
    with pytest.raises(SQLValidationError) as exc_info3:
        validate_and_prepare_sql(deep_parens, db_path=db_path)
    assert exc_info3.value.error_code == "COMPLEXITY_LIMIT"


def test_execute_readonly_sql_validates_independently_and_enforces_limits(
    temp_sql_env: tuple[Path, AppSettings],
) -> None:
    _, settings = temp_sql_env

    # Unsafe SQL passed directly to execute_readonly_sql without prepare_sql_query
    bad = execute_readonly_sql_impl(settings, "DELETE FROM orders")
    assert bad["status"] == "error"
    assert bad["error_code"] == "FORBIDDEN_STATEMENT"

    # Valid query with row_limit clamping
    settings.database.max_result_rows = 2
    ok = execute_readonly_sql_impl(
        settings,
        "SELECT order_id, total_amount FROM orders ORDER BY order_id",
        row_limit=50,  # exceeds max_result_rows=2, must clamp to 2
    )
    assert ok["status"] == "ok"
    assert ok["effective_row_limit"] == 2
    assert ok["record_count"] == 2
    assert ok["truncated"] is True

    # Timeout enforcement
    settings.database.query_timeout_s = 0.05
    timed_out = execute_readonly_sql_impl(
        settings,
        """
        WITH RECURSIVE spin(n) AS (
            SELECT 1 UNION ALL SELECT n + 1 FROM spin WHERE n < 50000000
        )
        SELECT COUNT(*) FROM spin
        """,
    )
    assert timed_out["status"] == "error"
    assert timed_out["error_code"] == "QUERY_TIMEOUT"
