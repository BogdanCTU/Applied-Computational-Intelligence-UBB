"""Automated Pytest suite for Milestone 2: SQLite connections, importer, schema inspector, and read-only queries.

All mutating tests operate exclusively on temporary directories (``tmp_path``).
Files under ``data/raw/`` are never modified.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
import zipfile
from pathlib import Path

import pytest

from config.paths import resolve_path
from database import (
    DatabaseNotFoundError,
    DatasetImportError,
    QueryExecutionError,
    QueryTimeoutError,
    TableNotFoundError,
    compare_databases,
    connect_readonly,
    connect_readwrite,
    execute_readonly_query,
    get_table_sample,
    import_dataset,
    inspect_schema,
    is_valid_identifier,
    quote_identifier,
    validate_database_integrity,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic relational e-commerce dataset in tmp_path
# ---------------------------------------------------------------------------


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return path


@pytest.fixture()
def synthetic_csv_dir(tmp_path: Path) -> Path:
    """Create a 4-table relational CSV dataset in a temporary folder."""
    csv_dir = tmp_path / "raw_csvs"
    csv_dir.mkdir()

    _write_csv(
        csv_dir / "customers.csv",
        ["customer_id", "first_name", "email", "phone", "country", "signup_date"],
        [
            [1, "Alice", "alice@example.com", "+1-555-0100", "USA", "2025-01-10"],
            [2, "Bob", "bob@example.com", "", "Canada", "2025-02-15"],
            [3, "Cara", "cara@example.com", "+44-7700-900", "UK", "2025-03-20"],
            [4, "Dan", "dan@example.com", "", "USA", "2025-04-01"],
            [5, "Eva", "eva@example.com", "+33-1-2345", "France", "2025-04-12"],
        ],
    )

    _write_csv(
        csv_dir / "products.csv",
        ["product_id", "sku", "product_name", "category", "unit_price", "weight_kg"],
        [
            [10, "SKU-10", "Trail Tent", "Tents", "249.99", "3.20"],
            [20, "SKU-20", "Camp Stove", "Cooking", "79.50", ""],
            [30, "SKU-30", "Wool Socks", "Apparel", "18.00", "0.15"],
            [40, "SKU-40", "Headlamp", "Lighting", "45.25", "0.12"],
            [50, "SKU-50", "Daypack", "Backpacks", "110.00", "0.85"],
        ],
    )

    _write_csv(
        csv_dir / "orders.csv",
        ["order_id", "customer_id", "order_date", "status", "total_amount"],
        [
            [100, 1, "2025-05-01 10:00:00", "delivered", "267.99"],
            [101, 2, "2025-05-03 14:30:00", "shipped", "79.50"],
            [102, 1, "2025-06-11 09:15:00", "delivered", "155.25"],
            [103, 3, "2025-06-15 18:45:00", "cancelled", "18.00"],
            [104, 5, "2025-07-02 12:00:00", "delivered", "110.00"],
        ],
    )

    _write_csv(
        csv_dir / "order_items.csv",
        ["order_item_id", "order_id", "product_id", "quantity", "line_total"],
        [
            [1000, 100, 10, 1, "249.99"],
            [1001, 100, 30, 1, "18.00"],
            [1002, 101, 20, 1, "79.50"],
            [1003, 102, 40, 1, "45.25"],
            [1004, 102, 50, 1, "110.00"],
            [1005, 103, 30, 1, "18.00"],
            [1006, 104, 50, 1, "110.00"],
        ],
    )
    return csv_dir


@pytest.fixture()
def synthetic_db(tmp_path: Path, synthetic_csv_dir: Path) -> Path:
    db_path = tmp_path / "synthetic.db"
    import_dataset(synthetic_csv_dir, db_path, batch_size=2)
    return db_path


# ---------------------------------------------------------------------------
# 1. Connection & identifier tests
# ---------------------------------------------------------------------------


def test_connect_readonly_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(DatabaseNotFoundError):
        connect_readonly(tmp_path / "does_not_exist.db")


def test_connect_readonly_blocks_writes(synthetic_db: Path) -> None:
    con = connect_readonly(synthetic_db)
    try:
        rows = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        assert rows == 5
        with pytest.raises(sqlite3.OperationalError):
            con.execute(
                "INSERT INTO customers VALUES (99, 'X', 'x@e.com', NULL, 'US', '2025-01-01')"
            )
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DROP TABLE customers")
    finally:
        con.close()


def test_special_characters_in_path_supported(
    tmp_path: Path, synthetic_csv_dir: Path
) -> None:
    tricky_dir = tmp_path / "8) FOLDER WITH SPACES & #1"
    tricky_dir.mkdir()
    db_path = tricky_dir / "my ecommerce.db"
    summary = import_dataset(synthetic_csv_dir, db_path)
    assert summary.total_imported_rows == 22

    con = connect_readonly(db_path, immutable=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 5
    finally:
        con.close()


def test_identifier_helpers() -> None:
    assert is_valid_identifier("order_items")
    assert not is_valid_identifier("order-items")
    assert not is_valid_identifier("123bad")
    assert quote_identifier('weird"name') == '"weird""name"'
    with pytest.raises(ValueError):
        quote_identifier("bad\x00name")


# ---------------------------------------------------------------------------
# 2. Importer tests (CSV folder, ZIP, CSV list, SQLite source, malformed, rollback)
# ---------------------------------------------------------------------------


def test_import_from_csv_directory_discovers_schema_and_fks(
    tmp_path: Path, synthetic_csv_dir: Path
) -> None:
    db_path = tmp_path / "imported.db"
    summary = import_dataset(synthetic_csv_dir, db_path, batch_size=2)

    assert summary.total_imported_rows == 22
    assert summary.total_rejected_rows == 0
    assert summary.integrity.integrity_ok is True
    assert summary.integrity.foreign_keys_ok is True
    assert summary.integrity.row_counts == {
        "customers": 5,
        "order_items": 7,
        "orders": 5,
        "products": 5,
    }

    # Verify NULL handling (empty string -> SQL NULL, not '')
    con = connect_readonly(db_path)
    try:
        null_phones = con.execute(
            "SELECT COUNT(*) FROM customers WHERE phone IS NULL"
        ).fetchone()[0]
        assert null_phones == 2
        null_weights = con.execute(
            "SELECT COUNT(*) FROM products WHERE weight_kg IS NULL"
        ).fetchone()[0]
        assert null_weights == 1
    finally:
        con.close()

    # Verify foreign key enforcement is active on read-write connections
    rw = connect_readwrite(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            rw.execute(
                "INSERT INTO orders VALUES (999, 99999, '2025-01-01', 'new', 10.0)"
            )
    finally:
        rw.close()


def test_import_from_zip_archive(tmp_path: Path, synthetic_csv_dir: Path) -> None:
    zip_path = tmp_path / "dataset_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for csv_file in synthetic_csv_dir.glob("*.csv"):
            zf.write(csv_file, arcname=f"nested/{csv_file.name}")
        # Add macOS metadata noise to verify importer ignores it cleanly
        zf.writestr("__MACOSX/._customers.csv", "ignored")

    zip_db = tmp_path / "from_zip.db"
    dir_db = tmp_path / "from_dir.db"
    import_dataset(synthetic_csv_dir, dir_db)
    summary = import_dataset(zip_path, zip_db, reference_db_path=dir_db)

    assert summary.total_imported_rows == 22
    assert summary.reference_comparison is not None
    assert summary.reference_comparison.matches_structure_and_counts is True


def test_import_from_individual_csv_files(
    tmp_path: Path, synthetic_csv_dir: Path
) -> None:
    db_path = tmp_path / "subset.db"
    summary = import_dataset(
        [synthetic_csv_dir / "customers.csv", synthetic_csv_dir / "orders.csv"],
        db_path,
    )
    assert summary.integrity.row_counts == {"customers": 5, "orders": 5}
    schema = inspect_schema(db_path)
    assert len(schema.relationships) == 1
    assert schema.relationships[0].from_table == "orders"
    assert schema.relationships[0].to_table == "customers"


def test_import_from_sqlite_source(tmp_path: Path, synthetic_db: Path) -> None:
    cloned_db = tmp_path / "cloned_from_sqlite.db"
    summary = import_dataset(
        synthetic_db, cloned_db, batch_size=3, reference_db_path=synthetic_db
    )
    assert summary.total_imported_rows == 22
    assert summary.reference_comparison is not None
    assert summary.reference_comparison.matches_structure_and_counts is True


def test_overwrite_protection(tmp_path: Path, synthetic_csv_dir: Path) -> None:
    db_path = tmp_path / "protected.db"
    import_dataset(synthetic_csv_dir, db_path)

    with pytest.raises(FileExistsError):
        import_dataset(synthetic_csv_dir, db_path, overwrite=False)

    # Explicit overwrite=True succeeds
    summary = import_dataset(synthetic_csv_dir, db_path, overwrite=True)
    assert summary.total_imported_rows == 22


def test_malformed_records_handled_gracefully_and_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad_dir = tmp_path / "dirty_csvs"
    bad_dir.mkdir()

    _write_csv(
        bad_dir / "customers.csv",
        ["customer_id", "name"],
        [
            [1, "Valid One"],
            [2, "Valid Two"],
            [3, "Valid Three"],
            [4, "Valid Four"],
            [2, "Duplicate PK"],  # SQLite PK constraint error
        ],
    )
    _write_csv(
        bad_dir / "orders.csv",
        ["order_id", "customer_id", "amount"],
        [
            [10, 1, "50.25"],
            [11, 2, "19.99"],
            [12, 3, "100.00"],
            [13, 4, "42.50"],
            [14, 1],  # Wrong column count
            [15, "not_an_int", "10.00"],  # Bad INTEGER
            [16, 1, "not_a_number"],  # Bad NUMERIC
            ["", 1, "12.00"],  # Empty in PRIMARY KEY (NOT NULL) column
            [18, 9999, "25.00"],  # Foreign key violation
        ],
    )

    db_path = tmp_path / "dirty_imported.db"
    with caplog.at_level(logging.WARNING):
        summary = import_dataset(bad_dir, db_path, batch_size=3, strict=False)

    assert summary.integrity.row_counts == {"customers": 4, "orders": 4}
    assert summary.total_imported_rows == 8
    assert summary.total_rejected_rows == 6
    assert len(summary.rejected_records) == 6
    assert summary.integrity.integrity_ok is True
    assert summary.integrity.foreign_keys_ok is True
    assert "Malformed record" in caplog.text


def test_strict_mode_rolls_back_leaving_no_partial_db(tmp_path: Path) -> None:
    bad_dir = tmp_path / "strict_csvs"
    bad_dir.mkdir()
    _write_csv(
        bad_dir / "customers.csv",
        ["customer_id", "amount"],
        [
            [1, "10.0"],
            [2, "20.0"],
            [3, "30.0"],
            [4, "40.0"],
            [5, "CORRUPT_NUM"],
        ],
    )

    target = tmp_path / "should_not_exist.db"
    with pytest.raises(DatasetImportError):
        import_dataset(bad_dir, target, strict=True)

    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_failed_overwrite_preserves_existing_database(
    tmp_path: Path, synthetic_db: Path
) -> None:
    corrupt_dir = tmp_path / "corrupt_csvs"
    corrupt_dir.mkdir()
    _write_csv(
        corrupt_dir / "customers.csv",
        ["customer_id", "amount"],
        [[1, "1.0"], [2, "2.0"], [3, "3.0"], [4, "4.0"], [5, "BAD"]],
    )

    with pytest.raises(DatasetImportError):
        import_dataset(corrupt_dir, synthetic_db, overwrite=True, strict=True)

    # Original synthetic_db must still be intact with all 4 tables and 22 rows
    integrity = validate_database_integrity(synthetic_db)
    assert integrity.integrity_ok
    assert integrity.total_rows == 22


# ---------------------------------------------------------------------------
# 3. Schema inspector, sampling, integrity & database comparison tests
# ---------------------------------------------------------------------------


def test_inspect_schema_and_serialisation(synthetic_db: Path) -> None:
    schema = inspect_schema(synthetic_db)
    assert schema.table_count == 4
    assert schema.total_rows == 22

    tmap = schema.table_map()
    assert set(tmap) == {"customers", "products", "orders", "order_items"}
    assert tmap["orders"].primary_keys == ["order_id"]
    assert len(tmap["order_items"].foreign_keys) == 2

    rel_triples = {
        (r.from_table, r.from_column, r.to_table, r.to_column)
        for r in schema.relationships
    }
    assert ("orders", "customer_id", "customers", "customer_id") in rel_triples
    assert ("order_items", "order_id", "orders", "order_id") in rel_triples
    assert ("order_items", "product_id", "products", "product_id") in rel_triples

    # Must be cleanly JSON-serialisable for MCP tools
    payload = json.dumps(schema.to_dict())
    assert "order_items" in payload

    # Single-table case-insensitive lookup
    single = inspect_schema(synthetic_db, table_name="ORDERS")
    assert single.table_count == 1
    assert single.tables[0].name == "orders"

    with pytest.raises(TableNotFoundError):
        inspect_schema(synthetic_db, table_name="nonexistent_table")


def test_get_table_sample_enforces_limits_and_table_validation(
    synthetic_db: Path,
) -> None:
    sample = get_table_sample(synthetic_db, "order_items", limit=50, max_limit=3)
    assert sample["effective_limit"] == 3
    assert sample["returned_count"] == 3
    assert sample["total_row_count"] == 7
    assert len(sample["columns"]) == 5

    with pytest.raises(ValueError):
        get_table_sample(synthetic_db, "orders", limit=0)

    with pytest.raises(TableNotFoundError):
        get_table_sample(synthetic_db, "orders; DROP TABLE customers;--", limit=5)


def test_compare_databases_reports_discrepancies(
    tmp_path: Path, synthetic_db: Path
) -> None:
    modified_db = tmp_path / "modified.db"
    import_dataset(synthetic_db, modified_db)

    # Mutate the temporary copy to introduce deliberate discrepancies
    con = connect_readwrite(modified_db)
    try:
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("DELETE FROM order_items WHERE order_item_id = 1006")
        con.execute("CREATE TABLE extra_audit (id INTEGER PRIMARY KEY)")
    finally:
        con.close()

    cmp = compare_databases(modified_db, synthetic_db)
    assert cmp.matches_structure_and_counts is False
    assert cmp.extra_tables == ["extra_audit"]
    assert "order_items" in cmp.row_count_differences
    assert cmp.row_count_differences["order_items"]["delta"] == -1


# ---------------------------------------------------------------------------
# 4. Read-only query executor tests (JOINs, CTEs, authorizer, limits, timeout)
# ---------------------------------------------------------------------------


def test_execute_readonly_join_and_cte(synthetic_db: Path) -> None:
    sql = """
    WITH customer_spend AS (
        SELECT c.country, SUM(o.total_amount) AS spend
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE o.status != 'cancelled'
        GROUP BY c.country
    )
    SELECT country, ROUND(spend, 2) AS total_spend
    FROM customer_spend
    ORDER BY total_spend DESC
    """
    res = execute_readonly_query(synthetic_db, sql)
    assert res.columns == ["country", "total_spend"]
    assert res.rows[0] == ["USA", 423.24]
    assert res.truncated is False


@pytest.mark.parametrize(
    "unsafe_sql",
    [
        "INSERT INTO customers VALUES (99, 'X', 'x@e.com', NULL, 'US', '2025-01-01')",
        "UPDATE customers SET country = 'Mars'",
        "DELETE FROM order_items",
        "DROP TABLE returns",
        "CREATE TABLE hacked (x INT)",
        "PRAGMA foreign_keys = OFF",
        "ATTACH DATABASE ':memory:' AS aux",
    ],
)
def test_execute_readonly_blocks_unsafe_sql(
    synthetic_db: Path, unsafe_sql: str
) -> None:
    with pytest.raises(QueryExecutionError):
        execute_readonly_query(synthetic_db, unsafe_sql)


def test_execute_readonly_row_limit_truncation(synthetic_db: Path) -> None:
    res = execute_readonly_query(
        synthetic_db, "SELECT * FROM order_items ORDER BY order_item_id", max_rows=3
    )
    assert res.row_count == 3
    assert res.truncated is True


def test_execute_readonly_timeout(synthetic_db: Path) -> None:
    infinite_cte = """
    WITH RECURSIVE spin(n) AS (
        SELECT 1
        UNION ALL
        SELECT n + 1 FROM spin WHERE n < 50000000
    )
    SELECT COUNT(*) FROM spin
    """
    with pytest.raises(QueryTimeoutError):
        execute_readonly_query(synthetic_db, infinite_cte, timeout_s=0.05)


# ---------------------------------------------------------------------------
# 5. Read-only parity check on built application DB (when present)
# ---------------------------------------------------------------------------


def test_application_database_parity_with_reference_readonly() -> None:
    app_db = resolve_path("data/ecommerce.db")
    ref_db = resolve_path("data/raw/ecommerce.sqlite")
    if not app_db.is_file() or not ref_db.is_file():
        pytest.skip("Application or reference database not present")

    integrity = validate_database_integrity(app_db)
    assert integrity.integrity_ok is True
    assert integrity.foreign_keys_ok is True
    assert len(integrity.row_counts) == 7
    assert integrity.total_rows == 499_385

    cmp = compare_databases(app_db, ref_db)
    assert cmp.matches_structure_and_counts is True
    assert cmp.total_target_rows == 499_385
    assert cmp.total_reference_rows == 499_385
