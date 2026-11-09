# Skill: SQL Generation & Schema Analysis

## Objective
Guide the agent in generating safe, read-only, accurate, and optimized SQLite queries for analytical e-commerce reporting.

---

## 1. Non-Negotiable Security Boundaries
- **Strict Read-Only Enforcement**: Only `SELECT` statements (and Common Table Expressions using `WITH ... SELECT`) are permitted.
- **Forbidden Operations**:
  - Absolutely NO Data Definition Language (`CREATE`, `ALTER`, `DROP`, `TRUNCATE`).
  - Absolutely NO Data Manipulation Language (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`).
  - Absolutely NO Transaction Control (`BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`).
  - Absolutely NO Database Attachment (`ATTACH DATABASE`, `DETACH DATABASE`).
  - Absolutely NO PRAGMA manipulation (`PRAGMA writable_schema`, `PRAGMA foreign_keys = OFF`).
- **Python-Side Authority**: Python-side AST and regex SQL validation is strictly authoritative. Any attempt to obfuscate queries, inject commands, or bypass human SQL approval will be intercepted and terminated.

---

## 2. Schema Discovery Before Query Generation
1. Always verify existing table names and column names before crafting complex joins:
   - Primary e-commerce tables: `orders`, `order_items`, `customers`, `payments`, `products`, `shipments`, `returns`.
2. Do not invent columns or speculate on table relationships. If column names are uncertain, invoke `inspect_database_schema`.

---

## 3. Join Cardinality & Fan-Out Prevention
- **Orders vs. Order Items (1:N)**: An order contains multiple items. Aggregating order counts from a join with `order_items` without `DISTINCT` will multiply counts by item lines!
  - Correct: `COUNT(DISTINCT orders.order_id)`
  - Dangerous: `COUNT(orders.order_id)` when joined with `order_items`
- **Avoid Cartesian Products**: Every join MUST have explicit `ON` conditions matching keys:
  - `orders.order_id = order_items.order_id`
  - `orders.customer_id = customers.customer_id`
  - `order_items.product_id = products.product_id`

---

## 4. SQLite Syntax & Dialect Rules
- **No FULL OUTER JOIN**: SQLite does not support `FULL OUTER JOIN`. Use `LEFT JOIN` (with primary driving table on the left) or union of directed joins if necessary.
- **Date Filtering & Formatting**:
  - Dates in the database are stored as ISO-8601 strings (e.g. `'2023-10-15 14:32:00'`).
  - Filter using standard ISO strings: `order_purchase_timestamp >= '2023-01-01' AND order_purchase_timestamp < '2024-01-01'`.
  - Extract month / year using SQLite date functions: `strftime('%Y-%m', order_purchase_timestamp)`.
- **NULL Handling**:
  - Use `COALESCE(val, 0)` when aggregating fields that may contain NULLs.
  - Check for missing values explicitly: `WHERE delivery_date IS NOT NULL`.

---

## 5. Aggregation & Performance
- **Common Table Expressions (CTEs)**: For multi-stage analytical queries (e.g. calculating customer lifetime value or monthly cohorts), use readable `WITH` blocks.
- **Indexing & Filtering**: Place filters (`WHERE`) on indexed columns (`order_purchase_timestamp`, `order_id`, `customer_id`) before grouping.
- **Ordering & Limits**: Always specify deterministic `ORDER BY` clauses when applying `LIMIT` to report top records.

