# Academic Demonstration Guide (5–10 Minutes)

This guide provides a repeatable, step-by-step demonstration script for university presentation and evaluation of the **Local Report SQL Agent**.

---

## Demonstration Script Overview

| Phase | Duration | Core Capability Demonstrated |
| :---: | :---: | :--- |
| **Part 1** | 1 min | Application launch, architecture introduction, and Ollama status |
| **Part 2** | 1 min | Conversational capabilities and dynamic database schema inspection |
| **Part 3** | 2 min | Complex SQL generation, explanation, and query rejection safety |
| **Part 4** | 2 min | Query approval, execution, and embedded native PDF report preview |
| **Part 5** | 2 min | Explicit CSV export request and embedded tabular CSV preview |
| **Part 6** | 1 min | Persistent report history, settings inspection, and clean shutdown |

---

## Step-by-Step Demonstration Procedure

### Step 1: Launch the Application (0:00 – 1:00)

**Action:**  
Open your terminal in the project directory and launch the application:
```bash
.venv/bin/python run_app.py
```
*(Alternatively, on macOS: `open dist/ReportSQLAgent.app`)*

**Presenter Talking Points:**
* *"This is the Local Report SQL Agent, an offline desktop AI system built with PySide6, Python 3.13, local Ollama, and SQLite."*
* Point out the **Header Status Pill**: Notice the green indicator `● Ollama Online (qwen3.5:4b)`. Mention that this health check runs asynchronously in a background thread to prevent UI freezing.
* Highlight the **Asymmetric Split Layout**: ~65% on the left is the dynamic **Report Workspace** (currently showing an empty placeholder), and ~35% on the right is the **AI Report Assistant** chat interface.

---

### Step 2: Introduce the Agent & Discover Capabilities (1:00 – 2:00)

**Prompt to Send:**
```text
Hello! What can you do, and what database do you have access to?
```

**Expected Result:**
* The agent responds conversationally without invoking database tools.
* It explains that it can analyze the local e-commerce database, write SQL queries, and generate downloadable reports in PDF format by default, or CSV upon request.

**Presenter Talking Points:**
* *"Notice how general questions are handled conversationally without unnecessary database queries or file generation."*

---

### Step 3: Inspect the Relational Database Schema (2:00 – 3:00)

**Prompt to Send:**
```text
Please inspect the database and show me all available tables and their relationships.
```

**Expected Result:**
* A status indicator appears: `⏳ Inspecting database schema...`
* The agent invokes the FastMCP tool `inspect_database_schema` over stdio.
* The agent summarizes the 7 relational tables: `customers`, `products`, `orders`, `order_items`, `payments`, `reviews`, and `returns` (499,385 total records).

**Presenter Talking Points:**
* *"The LLM does not rely on hardcoded assumptions. It dynamically queries the schema using genuine Model Context Protocol (MCP) tools running in an isolated subprocess."*

---

### Step 4: Request a Business Report & Demonstrate Rejection (3:00 – 5:00)

**Prompt to Send:**
```text
Generate a report showing total revenue grouped by payment method.
```

**Expected Result:**
1. The agent first calls `prepare_sql_query` to validate syntax and check the query plan via `EXPLAIN QUERY PLAN`.
2. An inline SQL card appears in the chat showing the proposed query:
   ```sql
   SELECT payment_method, SUM(amount) AS total_revenue
   FROM payments
   WHERE payment_status = 'Captured'
   GROUP BY payment_method
   ORDER BY total_revenue DESC;
   ```
3. When the agent attempts to execute the query via `execute_readonly_sql`, the **Modal SQL Approval Dialog** pops up automatically.

**Action:**
* Point out the dialog features:
  - Formatted SQL code block.
  - Target database label (`ecommerce.db`).
  - Security indicator: Notice the button focused by default is **Reject Query**.
* **Click "Reject Query"** (or press `Esc`).

**Expected Result:**
* The query is **not executed**.
* The agent receives an `APPROVAL_DENIED` notice and reports:  
  *“SQL query execution was denied by user. Query was not run.”*

**Presenter Talking Points:**
* *"This demonstrates our mandatory human-in-the-loop security gate. Even if the LLM produces valid SQL, it cannot touch the database without explicit user consent. The default action is strictly Reject."*

---

### Step 5: Approve Query & Generate PDF Report (5:00 – 7:00)

**Prompt to Send:**
```text
Please run the query and generate the revenue report as a PDF.
```

**Expected Result:**
1. The SQL Approval Dialog appears again.
2. **Click "Approve Query"**.
3. Status indicators update:
   - `⏳ Executing read-only SQL query...`
   - `⏳ Compiling PDF report via ReportLab...`
4. The FastMCP server compiles a styled ReportLab PDF.
5. **The left workspace immediately loads the generated PDF document.**

**Action in Workspace:**
* Demonstrate the embedded **native Qt PDF Viewer (`QPdfView`)**:
  - Click `▶` to navigate pages (or use page controls).
  - Use `+` and `-` zoom buttons.
  - Click **Fit to Width** and **Fit to Page**.
  - Show the ReportLab styling: KPI header cards, executive summary, formatted table grid, executed SQL block, and `Page X of Y` footer.

**Presenter Talking Points:**
* *"The user does not need to open an external PDF viewer. Qt 6's native QPdfView renders the report directly within the application workspace."*

---

### Step 6: Generate & Preview a CSV Report (7:00 – 8:30)

**Prompt to Send:**
```text
Export the top 10 products by price as a CSV report.
```

**Expected Result:**
1. Intent steering detects `"as a CSV report"` and configures CSV output mode.
2. The agent proposes a query against `products`:
   ```sql
   SELECT product_name, category, price, stock_quantity
   FROM products
   ORDER BY price DESC
   LIMIT 10;
   ```
3. The SQL Approval Dialog appears. **Click "Approve Query"**.
4. The FastMCP server compiles an RFC-4180 UTF-8 CSV report.
5. **The left workspace automatically flips to the Tabular CSV Viewer (`QTableView`).**

**Action in Workspace:**
* Show the tabular grid: column headers (`product_name`, `category`, `price`, `stock_quantity`), formatted numeric alignment, and row count indicators.

**Presenter Talking Points:**
* *"Notice how format steering operates seamlessly: PDF is the default for business summaries, while explicit CSV requests switch the workspace to a tabular data view."*

---

### Step 7: Report History & Clean Shutdown (8:30 – 10:00)

**Action:**
1. Click the **History** button in the top navigation bar.
2. The **Report History Dialog** opens, displaying a catalog of all generated reports:
   - Timestamps, report titles, formats (PDF/CSV), and file sizes.
   - Click **Preview** on any past report: the workspace instantly switches and renders that historical document.
   - Click **Close**.
3. Click the **⚙ (Settings)** button:
   - Show configurable local parameters (Ollama model, timeouts, row caps, approval requirements).
   - Click **Test Connection**: shows active Ollama version and installed models.
   - Click **Close**.
4. Close the main application window (`X`).

**Presenter Talking Points:**
* *"When closing the application, background threads and child MCP subprocesses are terminated cleanly without orphaned processes or segmentation faults. Everything operated locally on localhost, with zero cloud APIs and zero data transmission."*

---

## Demonstration Checklist Summary

- [ ] Application launches with clean dark theme
- [ ] Header shows `● Ollama Online (qwen3.5:4b)`
- [ ] Conversational greeting succeeds without tools
- [ ] Dynamic schema inspection lists 7 tables
- [ ] Complex SQL query generated with syntax highlighting
- [ ] SQL rejection halts workflow safely
- [ ] SQL approval executes query over `mode=ro` SQLite connection
- [ ] PDF report generated and rendered in native `QPdfView`
- [ ] Explicit CSV request generated and rendered in `QTableView`
- [ ] Historical catalog lists all reports with instant workspace preview
- [ ] Application closes cleanly with exit code 0

