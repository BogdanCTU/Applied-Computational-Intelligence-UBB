# Appendix B — MCP Tools Reference

The MCP server (`mcp_layer/server.py`) exposes **six authoritative tools** (`EXPECTED_MCP_TOOLS` in `agent/tool_handler.py`). All responses are serialized as deterministic UTF-8 JSON strings via `mcp_layer/server.py:_json_response()`.

---

## 1. `inspect_database_schema`

- **Source Module**: `mcp_layer/tools/database_tools.py` → `inspect_database_schema()`
- **Underlying Engine**: `database/schema_inspector.py` → `inspect_schema()`
- **Purpose**: Dynamically inspect tables, columns, SQLite type affinities, `NOT NULL` flags, primary keys, foreign key relationships, indexes, and row counts in `data/ecommerce.db`.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `table_name` | `string \| null` | No | `None` | Optional specific table name (case-insensitive). If omitted, inspects all 7 tables. |
| `include_row_counts` | `boolean` | No | `True` | Whether to run `SELECT COUNT(*)` on each inspected table. |

- **Success Return Payload (`status == "ok"`)**:
  ```json
  {
    "status": "ok",
    "database_path": "/.../data/ecommerce.db",
    "table_count": 7,
    "total_rows": 499385,
    "tables": [
      {
        "name": "customers",
        "row_count": 26000,
        "primary_keys": ["customer_id"],
        "columns": [
          {"name": "customer_id", "data_type": "INTEGER", "affinity": "INTEGER", "not_null": true, "default_value": null, "is_primary_key": true, "pk_position": 1}
        ],
        "foreign_keys": [],
        "indexes": [{"name": "idx_customers_country", "unique": false, "origin": "c", "partial": false, "columns": ["country"]}],
        "create_sql": "CREATE TABLE \"customers\" (...)"
      }
    ],
    "relationships": [
      {"from_table": "orders", "from_column": "customer_id", "to_table": "customers", "to_column": "customer_id", "cardinality": "many-to-one"}
    ],
    "prompt_summary": "Table customers (26,000 rows):\n  - customer_id: INTEGER PK\n..."
  }
  ```

---

## 2. `get_table_sample`

- **Source Module**: `mcp_layer/tools/database_tools.py` → `get_table_sample()`
- **Underlying Engine**: `database/schema_inspector.py` → `get_table_sample()`
- **Purpose**: Retrieve sample rows and column metadata from a single table to inspect date formats, status codes, and categorical values.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `table_name` | `string` | **Yes** | — | Name of the table to sample (`customers`, `products`, `orders`, `order_items`, `payments`, `shipments`, `returns`). |
| `limit` | `integer` | No | `10` | Number of rows to fetch (`1` to `100`). |

- **Success Return Payload (`status == "ok"`)**:
  ```json
  {
    "status": "ok",
    "table_name": "orders",
    "total_row_count": 90000,
    "requested_limit": 5,
    "effective_limit": 5,
    "returned_count": 5,
    "columns": [...],
    "records": [{"order_id": 1, "customer_id": 12901, "order_date": "2025-11-18 17:04:00", "status": "delivered", ...}]
  }
  ```

---

## 3. `prepare_sql_query`

- **Source Module**: `mcp_layer/tools/sql_tools.py` → `prepare_sql_query()`
- **Underlying Engine**: `database/query_executor.py` → `validate_readonly_sql()` + `EXPLAIN QUERY PLAN` under `_readonly_authorizer`
- **Purpose**: Validate a candidate SQL statement for read-only safety and SQLite syntax/schema validity before execution.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sql_query` | `string` | **Yes** | — | Candidate `SELECT` or `WITH ... SELECT` query. |
| `explanation` | `string` | No | `""` | Concise explanation of what the query calculates. |

- **Success Return Payload (`status == "valid"`)**:
  ```json
  {
    "status": "valid",
    "is_valid": true,
    "read_only": true,
    "requires_user_approval": true,
    "sql_query": "SELECT category, COUNT(*) FROM products GROUP BY category",
    "explanation": "Count products by category",
    "query_plan": ["SCAN products USING COVERING INDEX idx_products_category"]
  }
  ```

---

## 4. `execute_readonly_sql`

- **Source Module**: `mcp_layer/tools/sql_tools.py` → `execute_readonly_sql()`
- **Underlying Engine**: `database/query_executor.py` → `execute_readonly_query()`
- **Purpose**: Execute a validated read-only SQL query against `data/ecommerce.db` with timeout protection (`120.0s`) and bounded row fetching.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sql_query` | `string` | **Yes** | — | Single read-only `SELECT` or `WITH` statement. |
| `max_rows` | `integer \| null` | No | `None` | Optional row cap (defaults to `DatabaseSettings.max_result_rows = 1000`, capped at `ReportSettings.max_report_rows = 100,000`). |

- **Success Return Payload (`status == "ok"`)**:
  - Returns `columns`, `rows` (capped at `llm_preview_rows = 50` for LLM context), `records` (dict preview), `full_rows` (untruncated rows cached by `ToolHandler` for report generation), `row_count`, `preview_row_count`, `preview_truncated`, `truncated`, `max_rows`, and `duration_ms`.

---

## 5. `generate_pdf_report`

- **Source Module**: `mcp_layer/tools/reporting_tools.py` → `generate_pdf_report()`
- **Underlying Engine**: `reporting/pdf_generator.py` → `generate_pdf_file()` & `reporting/dynamic_pdf_composer.py` → `compose_dynamic_pdf()`
- **Purpose**: Generate a publication-quality, multi-page PDF report inside `reports/` containing executive summary, deterministic KPI cards, key findings, 25-renderer vector charts, and formatted tables.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `title` | `string` | **Yes** | — | Report title. |
| `columns` | `array[string] \| null` | No | `None` | Column names (auto-populated from cached SQL result if omitted). |
| `rows` | `array[array \| object] \| null` | No | `None` | Tabular rows (auto-populated with full untruncated rows from `ToolHandler._latest_sql_result`). |
| `description` | `string` | No | `""` | Subtitle or scope description. |
| `summary` | `string \| null` | No | `None` | Narrative executive summary paragraph. |
| `sql_query` | `string` | No | `""` | SQL query used to produce the dataset. |
| `user_request` | `string` | No | `""` | Original user prompt. |
| `include_sql` | `boolean \| null` | No | `None` | Whether to include an SQL appendix. |
| `report_spec` | `object \| null` | No | `None` | Full `ReportSpecification` dict for multi-section layouts. |
| `charts` | `array[object \| string] \| null` | No | `None` | List of chart configurations (`chart_type`, `title`, `x_axis`, `y_axis`, `series`, `aggregation`, `sorting`, `format`). |
| `sections` | `array[object] \| null` | No | `None` | Topical report sections (`ReportSection`). |
| `datasets` | `object \| null` | No | `None` | Named multi-query datasets (`{"primary": {"columns": [...], "rows": [...]}}`). |
| `kpis` | `array[object \| string] \| null` | No | `None` | KPI card definitions (validated/reconciled against `CanonicalSQLDataset.compute_deterministic_kpis()`). |
| `findings` | `array[string] \| null` | No | `None` | Bullet-point analytical findings. |

---

## 6. `generate_csv_report`

- **Source Module**: `mcp_layer/tools/reporting_tools.py` → `generate_csv_report()`
- **Underlying Engine**: `reporting/csv_generator.py` → `generate_csv_file()`
- **Purpose**: Export structured query results (single or multi-dataset) to a UTF-8 CSV file inside `reports/` and record metadata in `reports/report_history.json`.
- **Input Schema**:

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `title` | `string` | **Yes** | — | Report title used for sanitized filename generation. |
| `columns` | `array[string]` | **Yes** | — | Ordered list of column header strings. |
| `rows` | `array[array \| object]` | **Yes** | — | Tabular data rows (auto-enriched with full cached SQL rows by `ToolHandler`). |
| `description` | `string` | No | `""` | Optional description stored in `report_history.json`. |
| `sql_query` | `string` | No | `""` | SQL query that produced the dataset. |
| `user_request` | `string` | No | `""` | Original user request. |
| `datasets` | `object \| null` | No | `None` | Optional dictionary of multiple named datasets to export sequentially. |

