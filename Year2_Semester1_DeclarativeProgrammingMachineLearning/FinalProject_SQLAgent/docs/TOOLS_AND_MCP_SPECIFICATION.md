# Model Context Protocol (FastMCP) Tools Specification

**Project**: Local Report SQL Agent  
**Standard**: FastMCP Python SDK (JSON-RPC 2.0 over Stdio)  
**Parent Document**: [COMPLETE_SYSTEM_REFERENCE.md](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/docs/COMPLETE_SYSTEM_REFERENCE.md)

---

## 1. Overview & Transport Protocol

The Local Report SQL Agent leverages the official Python **Model Context Protocol (MCP)** SDK to decouple tool execution from LLM reasoning. Tools are executed inside an isolated child subprocess managed by [`mcp_layer/server.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/server.py), communicating with the primary GUI application over standard I/O (`stdio`).

```
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│     Parent Application Process  │                 │    Child MCP Subprocess (stdio) │
│                                 │                 │                                 │
│  AgentOrchestrator              │                 │  FastMCP Server                 │
│         │                       │                 │         │                       │
│  ToolHandler                    │  JSON-RPC 2.0   │         ├─ inspect_database_schema
│         │                       │  stdin / stdout │         ├─ get_table_sample
│  MCPStdioClient ────────────────┼────────────────►│         ├─ prepare_sql_query
│         │                       │                 │         ├─ execute_readonly_sql
│         ◄───────────────────────┼─────────────────┤         ├─ generate_pdf_report
│  (Result Unpacking & Audit)     │                 │         └─ generate_csv_report  │
└─────────────────────────────────┘                 └─────────────────────────────────┘
```

### Protocol Lifecycle
1. **Spawn**: Parent process invokes `sys.executable -m mcp_layer.server` (or `ReportSQLAgent --mcp-server` when packaged).
2. **Handshake**: Parent sends `initialize` request; child server advertises its capabilities and tool manifest.
3. **Acknowledgment**: Parent confirms readiness with `notifications/initialized`.
4. **Execution**: Parent dispatches `tools/call` with tool name and arguments; child executes the tool and replies with structured content.

---

## 2. Authorized Tool Manifest

The FastMCP server exposes exactly six authorized tools:

| Tool Name | Module | Domain | Purpose |
|---|---|---|---|
| `inspect_database_schema` | [`database_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/database_tools.py) | Database | Schema discovery and table introspection |
| `get_table_sample` | [`database_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/database_tools.py) | Database | Bounded preview of real table data |
| `prepare_sql_query` | [`sql_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/sql_tools.py) | SQL Engine | AST validation, query plan analysis, formatting |
| `execute_readonly_sql` | [`sql_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/sql_tools.py) | SQL Engine | Secure, bounded, authorizer-gated query execution |
| `generate_pdf_report` | [`reporting_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/reporting_tools.py) | Reporting | Platypus multi-component PDF document composer |
| `generate_csv_report` | [`reporting_tools.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/tools/reporting_tools.py) | Reporting | RFC-4180 compliant CSV export engine |

---

## 3. Tool Specifications

### 3.1 `inspect_database_schema`

Introspects the relational database schema, returning table names, column specifications, datatypes, primary keys, foreign key relations, and estimated table sizes.

#### Parameters
* `table_name` (`string`, optional): Specific table to inspect. If omitted (`None`), inspects and returns all tables in the database.

#### Output Schema
```json
{
  "database_name": "ecommerce.db",
  "table_count": 7,
  "tables": [
    {
      "name": "orders",
      "row_count": 100000,
      "columns": [
        {"name": "order_id", "type": "INTEGER", "primary_key": true, "nullable": false},
        {"name": "customer_id", "type": "INTEGER", "primary_key": false, "nullable": false},
        {"name": "order_date", "type": "TEXT", "primary_key": false, "nullable": false},
        {"name": "order_status", "type": "TEXT", "primary_key": false, "nullable": false},
        {"name": "total_amount", "type": "REAL", "primary_key": false, "nullable": false}
      ],
      "foreign_keys": [
        {"column": "customer_id", "references_table": "customers", "references_column": "customer_id"}
      ]
    }
  ]
}
```

#### Security Controls
* Executes strictly against a read-only SQLite URI (`mode=ro`).
* Result sets are cached in memory to minimize I/O overhead.

---

### 3.2 `get_table_sample`

Fetches a small sample of rows from a specified table to verify value formats (such as ISO date strings, status codes, or currency representations).

#### Parameters
* `table_name` (`string`, required): Name of the table to sample.
* `limit` (`integer`, optional, default `5`): Number of rows to return. Capped at a maximum of `50`.

#### Output Schema
```json
{
  "table_name": "orders",
  "sample_count": 3,
  "columns": ["order_id", "customer_id", "order_date", "order_status", "total_amount"],
  "rows": [
    [1001, 452, "2024-03-15", "delivered", 149.99],
    [1002, 118, "2024-03-15", "shipped", 89.50],
    [1003, 891, "2024-03-16", "delivered", 312.00]
  ]
}
```

#### Security Controls
* Validates `table_name` with strict identifier regex (`^[A-Za-z_][A-Za-z0-9_]*$`).
* Rejects any attempt at SQL injection in table identifiers.

---

### 3.3 `prepare_sql_query`

Validates, standardizes, and evaluates a proposed SQL query before execution. Extracts the query execution plan and affected tables.

#### Parameters
* `query` (`string`, required): Raw SQL query to analyze.

#### Output Schema
```json
{
  "valid": true,
  "normalized_sql": "SELECT order_status, COUNT(*) AS count FROM orders GROUP BY order_status;",
  "tables_referenced": ["orders"],
  "estimated_row_scan": 100000,
  "query_plan": [
    "SCAN orders USING COVERING INDEX idx_orders_status"
  ],
  "syntax_error": null
}
```

#### Validation & Guardrails
* AST inspection: Rejects forbidden keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, `PRAGMA`).
* Runs `EXPLAIN QUERY PLAN` in SQLite to ensure valid syntax and detect unindexed full-table scans.
* Formats SQL with consistent indentation and uppercase keywords.

---

### 3.4 `execute_readonly_sql`

Executes an authorized SQL query against the database with strict multi-layer security enforcement.

#### Parameters
* `query` (`string`, required): The validated SQL query to execute.
* `max_rows` (`integer`, optional, default `5000`): Maximum rows to return to protect memory.

#### Output Schema
```json
{
  "columns": ["product_category", "total_revenue"],
  "rows": [
    ["Electronics", 452100.50],
    ["Home & Kitchen", 298400.00],
    ["Apparel", 185200.75]
  ],
  "row_count": 3,
  "duration_ms": 14.2,
  "truncated": false
}
```

#### Defensive Security Enforcements
1. **URI Read-Only Mode**: Opened with `file:...mode=ro`.
2. **SQLite Query-Only Pragma**: `PRAGMA query_only = ON`.
3. **C-Authorizer Callback**: Low-level callback permits only `SQLITE_SELECT`, `SQLITE_READ`, safe functions, and recursive CTEs. Blocks `load_extension` and `fts3_tokenizer`.
4. **Opcode Watchdog Timeout**: `sqlite3_progress_handler` cancels queries exceeding `30.0` seconds.
5. **Memory-Bounded Fetch**: Executes `cursor.fetchmany(max_rows + 1)` to prevent out-of-memory denial-of-service.

---

### 3.5 `generate_pdf_report`

Generates an executive, publication-grade multi-page PDF document based on the executed SQL query result set.

#### Parameters
* `title` (`string`, required): Report title.
* `subtitle` (`string`, optional): Subtitle or reporting period description.
* `sql_query` (`string`, required): The executed SQL query providing data for the report.
* `columns` (`list[string]`, required): Column headers.
* `rows` (`list[list[Any]]`, required): Table data rows.
* `summary_findings` (`list[string]`, optional): Key analytical takeaways and bullet points.
* `kpi_cards` (`list[dict]`, optional): Metric cards with title, value, unit, and subtitle.
* `charts` (`list[dict]`, optional): List of vector chart specifications to render.
* `include_sql_appendix` (`boolean`, optional, default `true`): Appends formatted SQL at document end.

#### Output Schema
```json
{
  "report_path": "/.../reports/monthly_revenue_report_20261108_220324.pdf",
  "filename": "monthly_revenue_report_20261108_220324.pdf",
  "page_count": 3,
  "file_size_bytes": 142850,
  "format": "PDF",
  "kpi_count": 4,
  "chart_count": 2
}
```

#### Platypus Flowables & Layout
* **Header Banner**: Corporate dark-blue header with timestamp and title.
* **KPI Metrics Grid**: Side-by-side cards with formatted numbers and trend indicators.
* **Vector Charts**: Auto-scaled charts (ReportLab Graphics) rendered without external image files.
* **Paginated Tables**: Dynamic column auto-width calculation, alternate row shading (`#F8F9FA` / `#FFFFFF`), and repeating table header on page breaks.
* **Canvas Numbering**: Two-pass `NumberedCanvas` emitting `"Page X of Y"`.

---

### 3.6 `generate_csv_report`

Exports tabular query results directly to an RFC-4180 compliant CSV file.

#### Parameters
* `title` (`string`, required): Report title used for naming and metadata headers.
* `columns` (`list[string]`, required): List of column names.
* `rows` (`list[list[Any]]`, required): List of row data records.
* `filename` (`string`, optional): Target filename. If omitted, generates a timestamped name.

#### Output Schema
```json
{
  "report_path": "/.../reports/monthly_orders_20261108_220325.csv",
  "filename": "monthly_orders_20261108_220325.csv",
  "row_count": 250,
  "file_size_bytes": 18450,
  "format": "CSV"
}
```

#### Standards Compliance
* Adheres strictly to **RFC-4180**: comma delimiters, double-quote escaping for embedded commas and linebreaks.
* Encoded with **UTF-8-SIG** (BOM) for out-of-the-box compatibility with Microsoft Excel and desktop spreadsheet software.

---

## 4. Parameter Coercion & ToolHandler Safeguards

[`ToolHandler`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/tool_handler.py) acts as a protective shield between the LLM and the FastMCP client:

1. **Parameter Coercion**: Small local models (such as `qwen3.5:4b`) frequently pass numeric values as strings (e.g., `"limit": "5"` instead of `5`) or serialize lists as JSON strings. `ToolHandler` inspects the expected schema and safely converts arguments.
2. **Result Compaction**: Tool outputs returned from MCP may contain large data payloads. `ToolHandler` compacts results before they are passed into the LLM context, summarizing large row sets while keeping full records available for report generation.
3. **Dual-Mode Fallback**: If Ollama's native tool calling encounters XML grammar parse errors, `ToolHandler` coordinates with `OllamaClient` to automatically fall back to structured JSON extraction without failing the user's task.

