"""CLI utility to build and validate the local SQLite database ``data/ecommerce.db``.

Examples (macOS / Linux):
    .venv/bin/python scripts/import_dataset.py
    .venv/bin/python scripts/import_dataset.py --source data/raw/archive.zip --overwrite
    .venv/bin/python scripts/import_dataset.py --run-validation-queries

Examples (Windows PowerShell):
    .\\.venv\\Scripts\\python.exe scripts\\import_dataset.py --run-validation-queries
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_setup import setup_logging  # noqa: E402
from config.paths import resolve_path  # noqa: E402
from config.settings import load_settings  # noqa: E402
from database.importer import DatasetImportError, import_dataset  # noqa: E402
from database.query_executor import execute_readonly_query  # noqa: E402
from database.schema_inspector import inspect_schema  # noqa: E402


REPRESENTATIVE_ANALYTICAL_QUERIES: list[tuple[str, str]] = [
    (
        "1. Monthly captured revenue by payment method (orders JOIN payments)",
        """
        SELECT
            STRFTIME('%Y-%m', o.order_date) AS order_month,
            p.method AS payment_method,
            COUNT(DISTINCT o.order_id) AS orders_count,
            ROUND(SUM(p.amount), 2) AS captured_revenue
        FROM orders o
        JOIN payments p ON p.order_id = o.order_id
        WHERE p.status = 'captured'
        GROUP BY order_month, payment_method
        ORDER BY order_month DESC, captured_revenue DESC
        LIMIT 10
        """,
    ),
    (
        "2. Top product categories by net item revenue & gross margin (products + order_items + orders)",
        """
        SELECT
            pr.category,
            COUNT(DISTINCT oi.order_id) AS orders_with_category,
            SUM(oi.quantity) AS units_sold,
            ROUND(SUM(oi.line_total), 2) AS gross_item_sales,
            ROUND(SUM(oi.line_total - (oi.quantity * pr.unit_cost)), 2) AS estimated_gross_profit
        FROM order_items oi
        JOIN products pr ON pr.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        WHERE o.status NOT IN ('cancelled')
        GROUP BY pr.category
        ORDER BY gross_item_sales DESC
        LIMIT 10
        """,
    ),
    (
        "3. Customer loyalty tier performance & return rate (4-table CTE: customers + orders + order_items + returns)",
        """
        WITH tier_items AS (
            SELECT
                c.loyalty_tier,
                c.customer_id,
                o.order_id,
                o.total_amount,
                oi.order_item_id,
                r.return_id,
                COALESCE(r.refund_amount, 0.0) AS refund_amount
            FROM customers c
            JOIN orders o ON o.customer_id = c.customer_id
            JOIN order_items oi ON oi.order_id = o.order_id
            LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
        )
        SELECT
            loyalty_tier,
            COUNT(DISTINCT customer_id) AS active_customers,
            COUNT(DISTINCT order_id) AS total_orders,
            COUNT(order_item_id) AS items_purchased,
            COUNT(return_id) AS items_returned,
            ROUND(100.0 * COUNT(return_id) / COUNT(order_item_id), 2) AS item_return_rate_pct,
            ROUND(SUM(refund_amount), 2) AS total_refund_requested
        FROM tier_items
        GROUP BY loyalty_tier
        ORDER BY total_orders DESC
        """,
    ),
    (
        "4. Carrier fulfillment SLA & transit days by sales channel (orders + shipments)",
        """
        SELECT
            s.carrier,
            o.channel,
            COUNT(*) AS shipments_count,
            SUM(CASE WHEN s.status = 'delivered' THEN 1 ELSE 0 END) AS delivered_count,
            SUM(CASE WHEN s.status = 'lost' THEN 1 ELSE 0 END) AS lost_count,
            ROUND(
                AVG(
                    CASE
                        WHEN s.delivered_at IS NOT NULL
                        THEN JULIANDAY(s.delivered_at) - JULIANDAY(s.shipped_at)
                    END
                ),
                2
            ) AS avg_transit_days
        FROM shipments s
        JOIN orders o ON o.order_id = s.order_id
        GROUP BY s.carrier, o.channel
        ORDER BY s.carrier, shipments_count DESC
        LIMIT 12
        """,
    ),
    (
        "5. Full 7-table order lifecycle reconciliation summary",
        """
        SELECT
            c.country,
            COUNT(DISTINCT o.order_id) AS orders_count,
            ROUND(SUM(DISTINCT o.total_amount), 2) AS sum_distinct_totals_sample,
            COUNT(DISTINCT oi.order_item_id) AS line_items,
            COUNT(DISTINCT pr.product_id) AS distinct_products,
            COUNT(DISTINCT p.payment_id) AS payment_records,
            COUNT(DISTINCT s.shipment_id) AS shipment_records,
            COUNT(DISTINCT r.return_id) AS return_records
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products pr ON pr.product_id = oi.product_id
        LEFT JOIN payments p ON p.order_id = o.order_id
        LEFT JOIN shipments s ON s.order_id = o.order_id
        LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
        GROUP BY c.country
        ORDER BY orders_count DESC
        LIMIT 8
        """,
    ),
]


def _confirm_overwrite(target: Path) -> bool:
    if not sys.stdin.isatty():
        print(
            f"[ABORT] Target database already exists: {target}\n"
            "        Pass --overwrite to confirm replacing it.",
            file=sys.stderr,
        )
        return False
    reply = input(f"Target database '{target}' already exists. Overwrite? [y/N]: ").strip().lower()
    return reply in {"y", "yes"}


def _run_validation_queries(db_path: Path) -> None:
    print("\n== Representative Analytical SQL Queries (Read-Only Execution) ==")
    for title, sql in REPRESENTATIVE_ANALYTICAL_QUERIES:
        res = execute_readonly_query(db_path, sql, max_rows=20, timeout_s=15.0)
        print(f"\n{title} [{res.row_count} row(s), {res.duration_ms:.2f} ms]")
        print("  Columns:", ", ".join(res.columns))
        for row in res.rows[:5]:
            print("   ", row)
        if res.row_count > 5:
            print(f"    ... ({res.row_count - 5} more row(s))")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the e-commerce dataset into the local SQLite database."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="data/raw",
        help="Path to CSV directory, .zip archive, .csv file, or .sqlite file (default: data/raw)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Destination SQLite path (default: configured database path, data/ecommerce.db)",
    )
    parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help="Optional reference SQLite file for parity check (auto-detects data/raw/ecommerce.sqlite)",
    )
    parser.add_argument(
        "--no-reference",
        action="store_true",
        help="Skip comparison against data/raw/ecommerce.sqlite",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5_000,
        help="Batch insert size (default: 5000)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite target database if it already exists",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Abort and roll back on any malformed CSV record",
    )
    parser.add_argument(
        "--run-validation-queries",
        action="store_true",
        help="Run representative multi-table analytical SQL queries after import",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional file path to write JSON import summary",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    setup_logging(settings, process_name="import", console=True)

    source_path = resolve_path(args.source)
    target_path = resolve_path(args.target) if args.target else settings.database_path
    raw_dir = resolve_path("data/raw")

    # Safety rail: never write inside data/raw/
    try:
        target_path.resolve().relative_to(raw_dir.resolve())
        print(
            f"[ERROR] Refusing to write target database inside read-only source directory: {raw_dir}",
            file=sys.stderr,
        )
        return 1
    except ValueError:
        pass

    overwrite = args.overwrite
    if target_path.exists() and not overwrite:
        if not _confirm_overwrite(target_path):
            return 2
        overwrite = True

    ref_path: Path | None = None
    if not args.no_reference:
        if args.reference:
            ref_path = resolve_path(args.reference)
        else:
            default_ref = raw_dir / "ecommerce.sqlite"
            if default_ref.is_file():
                ref_path = default_ref

    try:
        summary = import_dataset(
            source=source_path,
            target_db_path=target_path,
            overwrite=overwrite,
            batch_size=args.batch_size,
            reference_db_path=ref_path,
            strict=args.strict,
        )
    except (DatasetImportError, FileExistsError, ValueError) as exc:
        print(f"[FAIL] Dataset import failed: {exc}", file=sys.stderr)
        return 1

    print(summary.format_report())

    schema = inspect_schema(target_path, include_counts=True)
    print("\n== Discovered Relational Schema ==")
    print(schema.format_for_prompt())

    if args.run_validation_queries:
        _run_validation_queries(target_path)

    if args.json_out:
        out_file = resolve_path(args.json_out)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
        print(f"\nJSON import summary written to: {out_file}")

    if not summary.integrity.integrity_ok or not summary.integrity.foreign_keys_ok:
        return 1
    if summary.reference_comparison and not summary.reference_comparison.matches_structure_and_counts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

