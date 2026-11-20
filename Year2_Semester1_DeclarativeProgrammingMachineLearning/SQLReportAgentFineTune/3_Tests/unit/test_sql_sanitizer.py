"""Unit tests for SQL sanitization, codeblock extraction, and normalization."""

from app.utils.sql_sanitizer import (
    clean_sql_query,
    extract_sql_from_response,
    is_valid_sql_syntax,
    normalize_sql,
)


def test_extract_sql_from_markdown():
    resp = "Here is your SQL query:\n```sql\nSELECT * FROM orders WHERE status = 'delivered';\n```\nHope that helps!"
    extracted = extract_sql_from_response(resp)
    assert extracted == "SELECT * FROM orders WHERE status = 'delivered'"


def test_extract_sql_from_plain_text():
    resp = "Sure! SELECT customer_id, SUM(amount) FROM payments GROUP BY customer_id;"
    extracted = extract_sql_from_response(resp)
    assert extracted == "SELECT customer_id, SUM(amount) FROM payments GROUP BY customer_id"


def test_clean_sql_query_removes_comments():
    raw = "-- Get all orders\nSELECT order_id /* inline comment */ FROM orders; -- end"
    cleaned = clean_sql_query(raw)
    assert cleaned == "SELECT order_id FROM orders"


def test_normalize_sql():
    q1 = "select id, name from users where age > 20"
    q2 = "SELECT id,   name\nFROM users\nWHERE age > 20;"
    assert normalize_sql(q1) == normalize_sql(q2)


def test_is_valid_sql_syntax():
    assert is_valid_sql_syntax("SELECT * FROM users") is True
    assert is_valid_sql_syntax("WITH cte AS (SELECT 1) SELECT * FROM cte") is True
    assert is_valid_sql_syntax("This is random English text.") is False
    assert is_valid_sql_syntax("") is False
