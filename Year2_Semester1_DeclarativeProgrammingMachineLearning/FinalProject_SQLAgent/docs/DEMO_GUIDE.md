# Academic Demonstration Guide (10–15 Minutes)

This document provides a repeatable, step-by-step presentation script for university defense and academic evaluation of the **Local Report SQL Agent**.

---

## 1. Demonstration Session Overview

| Phase | Duration | Core Capability Demonstrated | Key Evaluator Takeaway |
| :---: | :---: | :--- | :--- |
| **Phase 1** | 1.5 min | Application startup, local health checks, and architecture overview | 100% offline localhost boundary (`127.0.0.1:11434`), zero cloud exposure. |
| **Phase 2** | 1.5 min | Conversational capability discovery & FastMCP dynamic schema introspection | No hardcoded schemas; genuine MCP tool calling over stdio subprocess. |
| **Phase 3** | 2.5 min | Complex SQL synthesis, syntax inspection, and mandatory user rejection | Human-in-the-loop security gate blocks execution; default action is Reject. |
| **Phase 4** | 3.5 min | SQL approval, multi-step execution, and embedded native PDF report preview | ReportLab PDF compilation, Page X of Y canvas, dual KPI grids, vector charts. |
| **Phase 5** | 2.5 min | Edge-period reporting (October 2026) & Data Availability Notice banner | PeriodAvailabilityContext prevents silent substitution; explicit notice rendered. |
| **Phase 6** | 2.0 min | Explicit CSV export request and virtualized tabular viewer | Seamless format steering; high-density tabular view with $O(1)$ memory. |
| **Phase 7** | 1.5 min | Historical report catalog, settings management, and clean shutdown | Persistent report history, configurable parameters, clean thread termination. |

---

## 2. Step-by-Step Demonstration Procedure

### Phase 1: Launch & Architectural Overview (0:00 – 1:30)

**Action:**
Open the macOS terminal or command prompt in the workspace directory and execute:
```bash
.venv/bin/python run_app.py
```
*(Alternatively, on macOS double-click `dist/ReportSQLAgent.app` or run `open dist/ReportSQLAgent.app`)*

**Presenter Talking Points:**
* *"Good morning, esteemed committee members. This is the Local Report SQL Agent, an enterprise-grade, 100% offline desktop application built for private relational analytics."*
* Point to the **Header Status Pill**: *"Notice the green indicator `● Ollama Online (qwen3.5:4b)`. Health checks run asynchronously in a background thread to prevent UI freezing."*
* Point to the **Asymmetric Workspace**: *"On the left (~65%) is the native Report Workspace featuring embedded PDF and CSV viewers; on the right (~35%) is the AI Assistant and Activity Inspector."*
* Emphasize: *"Prompts, schema metadata, query results, and generated reports never leave this machine. All network traffic is strictly confined to 127.0.0.1."*

---

### Phase 2: Conversational Discovery & MCP Schema Introspection (1:30 – 3:00)

**Prompt to Send:**
```text
Hello! What can you do, and what database do you have access to?
```

**Expected Result:**
* The agent replies conversationally explaining its capabilities: querying the relational database, running analytical aggregations, and compiling publication-grade PDF and CSV reports.

**Next Prompt to Send:**
```text
Please inspect the database and show me all available tables and their record counts.
```

**Expected Result:**
* A progress card appears: `⏳ Inspecting database schema...`
* The agent invokes the FastMCP tool `inspect_database_schema` over stdio pipes.
* The agent displays the 7 relational tables: `customers`, `products`, `orders`, `order_items`, `payments`, `shipments`, and `returns` (499,385 total records).

**Presenter Talking Points:**
* *"The model does not rely on pre-baked prompt assumptions. It discovers the database structure dynamically using the official Model Context Protocol (FastMCP) running in an isolated background subprocess."*

---

### Phase 3: Complex SQL Synthesis & Rejection Gate (3:00 – 5:30)

**Prompt to Send:**
```text
Generate a report showing total revenue grouped by payment method.
```

**Expected Result:**
1. The agent decomposes the request, calls `prepare_sql_query`, and displays the syntax-highlighted SQL card:
   ```sql
   SELECT payment_method, SUM(amount) AS total_revenue
   FROM payments
   WHERE payment_status = 'Captured'
   GROUP BY payment_method
   ORDER BY total_revenue DESC;
   ```
2. When the agent attempts to execute `execute_readonly_sql`, the **Modal SQL Approval Dialog** pops up automatically.

**Action:**
* Point out dialog features: formatted SQL syntax highlighting, database target label (`data/ecommerce.db`), and default focus on **Reject Query**.
* **Click "Reject Query"** (or hit `Esc`).

**Expected Result:**
* Query execution is **blocked**. The agent surfaces:  
  *“SQL query execution was denied by user. Query was not run.”*

**Presenter Talking Points:**
* *"This demonstrates our mandatory human-in-the-loop security gate. Even if the LLM produces valid SQL, it cannot touch the database without explicit user consent. The default button is strictly Reject."*

---

### Phase 4: Query Approval & Embedded PDF Report Preview (5:30 – 9:00)

**Prompt to Send:**
```text
Please execute the query and generate the revenue report as a PDF.
```

**Expected Result:**
1. The SQL Approval Dialog appears again.
2. **Click "Approve Query"**.
3. Status indicators update in real-time:
   - `⏳ Executing read-only SQL query...`
   - `⏳ Validating data via 4-stage ReportDataValidator...`
   - `⏳ Compiling PDF report via ReportLab Platypus...`
4. **The left workspace immediately renders the generated PDF document.**

**Action in Workspace:**
* Demonstrate the embedded **native Qt PDF Viewer (`QPdfView`)**:
  - Click `▶` to navigate pages.
  - Demonstrate `+` and `-` zoom controls, **Fit to Width**, and **Fit to Page**.
  - Show the ReportLab document structure: Header banner, KPI cards, vector chart, styled table grid, executed SQL block, and `Page X of Y` footer.

**Presenter Talking Points:**
* *"Notice how Qt 6's native QPdfView renders the PDF directly inside the workspace without launching external viewer processes. The numerical values on the KPI cards and tables are guaranteed accurate by our CanonicalSQLDataset architecture."*

---

### Phase 5: Edge-Period Reporting & Data Availability Notice (9:00 – 11:30)

**Prompt to Send:**
```text
I want an output report in PDF file, exporting last month orders, sales, revenue, transactions. I want graphical historical bar charts, some distribution pies and matrix graphs. Provide also at the end of the report data in table format.
```

**Expected Result:**
1. The agent resolves the calendar period (October 2026).
2. The database ends at September 2026.
3. The agent invokes `PeriodAvailabilityContext` and generates the report.
4. The generated PDF renders:
   - **Red/Pink Data Availability Notice Banner**: Clearly states that October 2026 data is not yet recorded and designates September 2026 as the comparison baseline.
   - **Dual KPI Grids**: October 2026 displays 0s, while September 2026 displays validated actuals.
   - **Distribution Pie Charts & Operational Matrix**: Multi-category distribution and multi-dimensional performance crosstabs.
   - **LongTable Data Tables**: High-density tabular rows paginated cleanly across pages.

**Presenter Talking Points:**
* *"Previously, LLM reporting pipelines silently hallucinated or substituted September data as if it were October. Our canonical architecture explicitly separates requested vs available periods and renders a clear Data Availability Notice."*

---

### Phase 6: Tabular CSV Export & Virtualized Viewer (11:30 – 13:30)

**Prompt to Send:**
```text
Export the top 10 products by price as a CSV report.
```

**Expected Result:**
1. Intent steering detects `"as a CSV report"` and selects RFC-4180 CSV export mode.
2. Proposes query against `products`:
   ```sql
   SELECT product_name, category, price, stock_quantity
   FROM products
   ORDER BY price DESC
   LIMIT 10;
   ```
3. SQL Approval Dialog appears. **Click "Approve Query"**.
4. The FastMCP server compiles an RFC-4180 UTF-8 CSV report.
5. **The left workspace automatically flips to the Tabular CSV Viewer (`QTableView`).**

**Presenter Talking Points:**
* *"Format steering operates seamlessly: narrative summaries default to PDF, while explicit tabular requests switch the workspace to a virtualized QTableView."*

---

### Phase 7: Historical Catalog, Settings & Clean Shutdown (13:30 – 15:00)

**Action:**
1. Click the **History** button in the top navigation bar:
   - Show the catalog of generated PDF and CSV reports with timestamps and file sizes.
   - Click **Preview** on any past report: the workspace instantly switches and renders that document.
   - Click **Close**.
2. Click the **⚙ (Settings)** button:
   - Show configurable local parameters (Ollama model, timeouts, row limits, approval requirements).
   - Click **Test Connection**: displays active Ollama version and model availability.
   - Click **Close**.
3. Close the main application window (`X`).

**Presenter Talking Points:**
* *"When closing the application, background threads and child MCP subprocesses are terminated cleanly without orphaned processes or segmentation faults. Everything operated locally on localhost, with zero cloud APIs and zero data transmission."*

---

## 3. Academic Defense Q&A Cheat-Sheet

| Topic | Committee Question | Rigorous Defense Response |
| :--- | :--- | :--- |
| **Model Context Protocol** | *Why FastMCP over standard function calling?* | FastMCP standardizes tool schemas, decouples tools into an isolated subprocess, and prevents UI thread blocking through async stdio pipes. |
| **SQL Security** | *How is SQL injection prevented?* | Six defense layers: regex scanner, AST verification, EXPLAIN QUERY PLAN validation, human approval modal, read-only SQLite URI, and low-level SQLite C-authorizer blocking write bytecodes. |
| **Numerical Truth** | *How do you prevent LLM math hallucinations?* | The LLM never computes numbers. The `CanonicalSQLDataset` and Python aggregation engine compute all metrics deterministically; the LLM only writes qualitative text. |
| **Data Integrity** | *How do you ensure the database was not modified?* | SHA-256 hash `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934` is verified before and after runs. In PyInstaller frozen mode, the DB is opened `mode=ro`. |
| **Testing Scope** | *What is the automated test coverage?* | 457 tests across 36 modules covering the entire stack: database, SQL security, MCP tools, 25 chart types, context budgeting, memory migrations, and headless GUI. |
