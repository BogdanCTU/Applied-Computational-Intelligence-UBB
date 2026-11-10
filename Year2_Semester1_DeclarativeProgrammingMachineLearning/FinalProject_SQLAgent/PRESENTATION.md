# Academic Presentation Script: Local Report SQL Agent

> **Course:** Declarative Programming & Machine Learning (Year 2, Semester 1)  
> **Institution:** Faculty of Mathematics and Computer Science, Babeș-Bolyai University (UBB)  
> **Target Audience:** Course Professor, Teaching Assistants, and Master's Degree Peers  
> **Total Target Duration:** Approximately 10 minutes (including live demonstration)  
> **Format:** 10 Slides with Visual Layouts, Exact Speaker Notes, Time Allocations, and Defense Q&A

---

## Slide Overview & Timing Budget

| Slide # | Title | Focus Area | Allocated Time |
|:---:|:---|:---|:---:|
| **1** | Title & Introduction | Project Identity & High-Level Purpose | 0:45 |
| **2** | Problem Statement & Motivation | The Fragility of Cloud LLM SQL Generation | 1:00 |
| **3** | Project Objectives & Architectural Solution | Local Intelligence + Deterministic Reliability | 1:00 |
| **4** | Decoupled System Architecture | PySide6 GUI, FastMCP Subprocess, Ollama | 1:15 |
| **5** | Agent Intelligence & MCP Tool Workflow | DAG Task Planning & Model Context Protocol | 1:15 |
| **6** | Multi-Tier SQL Security & Human Approval | AST Validation, SQLite Authorizer & Guardrails | 1:00 |
| **7** | Deterministic Reporting & Canonical Validation | Reconciled Metrics, Missing Data & 22 Vector Charts | 1:15 |
| **8** | Live Demonstration Scenario | Step-by-Step Prompt Execution & PDF Visuals | 1:45 |
| **9** | Engineering Challenges & Technical Trade-offs | Context Windows, Small Model Reasoning & Reliability | 1:00 |
| **10** | Conclusions, Academic Impact & Future Work | Key Takeaways & Defense Summary | 0:45 |
| **Total** | | | **10:00** |

---

## Slide 1: Title & Project Introduction
**Time Allocation:** 0:45 (0:00 – 0:45)

### Slide Visual Content
- **Title:** Local Report SQL Agent
- **Subtitle:** An Autonomous, Offline Business Intelligence Desktop Agent with Model Context Protocol (MCP) and Multi-Page Vector Report Generation
- **Candidate:** Bogdan Stefan Popa
- **Master's Program:** Applied Computational Intelligence / Advanced Declarative Programming
- **Key Highlights:**
  - 100% Localhost Execution: Zero Cloud APIs, Zero Data Egress
  - Local LLM: `qwen3.5:4b` running via Ollama
  - Decoupled Architecture: PySide6 Desktop GUI + FastMCP Subprocess
  - Primary Database: Relational SQLite (7 tables, 499,385 records)
  - 463 Automated Verification Tests (461 deterministic + 2 live Ollama workflows)

### Speaker Notes
> "Good afternoon, Professor and colleagues. Today I am presenting my final project: the **Local Report SQL Agent**.
> 
> In modern enterprise environments, business intelligence and analytical reporting frequently handle sensitive transactional data that cannot be sent to third-party cloud LLMs due to GDPR, confidentiality, or data sovereignty constraints.
> 
> The Local Report SQL Agent solves this challenge by delivering an autonomous, 100% offline reporting agent. Running completely on a local workstation, it bridges a local 4-billion parameter LLM—Qwen 3.5—with an enterprise-scale relational database using the Model Context Protocol (MCP) and a deterministic ReportLab PDF generation engine.
> 
> Over the next ten minutes, I will walk you through the system's architecture, its multi-tiered security model, the reporting pipeline, and a live demonstration."

---

## Slide 2: Problem Statement & Motivation
**Time Allocation:** 1:00 (0:45 – 1:45)

### Slide Visual Content
- **The Core Flaws of Traditional "Text-to-SQL" Chatbots:**
  1. **Hallucination of Metrics**: LLMs invent numbers, sum averages horizontally, or confuse Gross Sales with Net Revenue.
  2. **Security Vulnerabilities**: Direct query generation risks SQL injection, data exfiltration, or accidental DDL/DML mutations (`DROP TABLE`, `UPDATE`).
  3. **Silent Period Substitution**: When asked for October data and none exists, naive agents silently substitute September without user warning.
  4. **Crude Document Layouts**: Most agents dump raw Markdown tables or unstyled text rather than publication-quality, multi-page executive PDFs.
  5. **Cloud Data Leakage**: Sending relational schemas and query results to remote APIs violates enterprise data compliance.

### Speaker Notes
> "When building LLM-powered analytical tools, the typical naive approach is to give an LLM a database connection string and ask it to write queries and render HTML. In practice, this results in three critical failure modes:
> 
> First, metric hallucination. LLMs are probabilistic language models—not calculators. They frequently average already-averaged ratios, mix up line-item subtotals with net revenues, or fabricate numbers when data is sparse.
> 
> Second, security. Without rigid architectural boundaries, LLMs are vulnerable to prompt injection or catastrophic execution of destructive SQL commands.
> 
> Third, silent substitution. If an executive asks for October 2026 performance, and the database only has records through September, standard agents will quietly substitute September data without making the distinction clear.
> 
> Our objective was to engineer a system where **the LLM is restricted to semantic reasoning and query formulation, while all calculation, validation, and rendering are strictly deterministic**."

---

## Slide 3: Project Objectives & Architectural Solution
**Time Allocation:** 1:00 (1:45 – 2:45)

### Slide Visual Content
- **Core Engineering Principles:**
  - **Localhost Privacy**: Complete independence from cloud services; local Ollama inference on `localhost:11434`.
  - **The Golden Rule of Reliability**:
    $$\text{LLM} = \text{Intent Interpretation & SQL Formulation}$$
    $$\text{Deterministic Python} = \text{Execution, Calculation, Reconciliation & Vector Rendering}$$
  - **Protocol Standardization**: Leveraging the open Model Context Protocol (MCP) to isolate tools into independent subprocesses.
  - **Enterprise Vector Graphics**: Dynamic generation of 22 ReportLab vector chart types with automatic eligibility checks.
  - **Mathematical Integrity**: Canonical reconciliation of Gross Sales, Net Revenue, Orders, Transactions, and vertical Average Order Value (AOV).

### Speaker Notes
> "To address these problems, the project enforces a clean separation of concerns:
> 
> We treat the LLM as an intent interpreter and declarative query generator. It never calculates final KPI numbers, and it never directly touches document drawing canvases.
> 
> Instead, the application implements a deterministic reporting pipeline. When the model selects tools, it invokes them through the Model Context Protocol. Once tabular data is retrieved, deterministic Python algorithms inspect the dates, reconcile the metrics against ground truth relational totals, validate chart eligibility, and format the output.
> 
> If a requested month has no data, the system automatically detects this, renders an explicit Red Notice Banner on page one, and isolates historical comparison data in a dedicated section."

---

## Slide 4: Decoupled System Architecture
**Time Allocation:** 1:15 (2:45 – 4:00)

### Slide Visual Content
```text
+-------------------------------------------------------------------------------+
|                            PySide6 Desktop GUI                                |
|   [Chat Assistant Panel]   [Embedded QtPdf Preview]   [Activity Inspector]    |
+-------------------------------------------------------------------------------+
                                  |  QThread Async Bridge
                                  v
+-------------------------------------------------------------------------------+
|                      Agent Intelligence Layer (In-Process)                    |
|   - TaskPlanner (DAG)      - ContextBuilder (Token Budget)  - SkillManager    |
|   - CheckpointManager      - SQLite Memory Repository       - Ollama Client   |
+-------------------------------------------------------------------------------+
         |                                                    |
         | JSON-RPC over Stdio (MCP Protocol)                 | HTTP REST API
         v                                                    v
+--------------------------------+           +----------------------------------+
| FastMCP Server (Subprocess)    |           | Local Ollama Daemon              |
| - inspect_database_schema      |           | - Model: qwen3.5:4b              |
| - get_table_sample             |           | - Port: http://localhost:11434   |
| - prepare_sql_query            |           +----------------------------------+
| - execute_readonly_sql         |
| - generate_pdf_report          |           +----------------------------------+
| - generate_csv_report          |           | SQLite Relational DB             |
+--------------------------------+           | - ecommerce.db (7 tables, 500k r)|
         |                                   | - Mode: Strictly Read-Only       |
         +---------------------------------> | - SHA-256 Verified Immutable     |
                                             +----------------------------------+
```

### Speaker Notes
> "This slide illustrates the physical and logical architecture of the application.
> 
> At the top is the PySide6 desktop interface. It contains a conversational chat panel, an embedded vector QtPdf viewer, and an Activity Inspector. The GUI runs on the main thread, while all agent activities run inside an asynchronous `AgentWorker` thread, ensuring zero UI freezing.
> 
> In the center is the Agent Intelligence Layer. It manages DAG planning, task decomposition, context window token budgeting, and SQLite working memory.
> 
> Crucially, look at the bottom left: the data tools do not run inside the GUI process. They run inside an independent **FastMCP subprocess** launched via standard input/output pipes. The agent and database communicate strictly via JSON-RPC 2.0 messages defined by the Model Context Protocol.
> 
> Finally, the database itself—`ecommerce.db`—is completely decoupled and locked. It is mounted read-only and verified by SHA-256 hash checks before every execution."

---

## Slide 5: Agent Intelligence & MCP Tool Workflow
**Time Allocation:** 1:15 (4:00 – 5:15)

### Slide Visual Content
- **The Six MCP Tools (Runtime Active Registry):**
  1. `inspect_database_schema`: Introspects table structures, column types, and foreign keys.
  2. `get_table_sample`: Retrieves real data samples to ground value formats.
  3. `prepare_sql_query`: Pre-validates syntax, checks AST, and logs human justification.
  4. `execute_readonly_sql`: Executes read-only query and captures structured results.
  5. `generate_pdf_report`: Invokes canonical data validator and compiles multi-page PDF.
  6. `generate_csv_report`: Exports sanitized tabular datasets.
- **Configurable Context Window (32K / 64K / 128K / 256K):**
  - Dynamic token allocation per stage (`SCHEMA_DISCOVERY`, `SQL_GENERATION`, `DATA_ANALYSIS`, `REPORT_SYNTHESIS`).
  - Strict priority budgeting: `HIGH` (System instructions) protected; `LOW` (Old results) pruned.
- **Automated Crash Recovery**:
  - SHA-256 verified checkpoints saved at every lifecycle milestone (`TASK_CREATED` -> `PLAN_READY` -> `STEP_COMPLETED`).

### Speaker Notes
> "Let's examine how the agent reasons and executes.
> 
> The agent operates through an active runtime registry of six FastMCP tools. Upon receiving a natural language prompt, the `TaskPlanner` generates a Directed Acyclic Graph (DAG) of steps.
> 
> To manage small local models like Qwen 3.5 4B, we built a specialized `ContextBuilder`. Instead of stuffing the entire schema into every prompt, the ContextBuilder tailors the prompt to the current stage. In the Schema Discovery stage, it provides table overviews; in the SQL Generation stage, it injects explicit column definitions and join rules; in the Synthesis stage, it passes tabular datasets.
> 
> We also support configurable context windows from 32K up to 256K tokens, centered on a certified default of 128K tokens.
> 
> Every stage transition is checkpointed with a SHA-256 digest in SQLite working memory. If an unexpected power loss occurs, the agent detects the checkpoint on restart and can resume execution without data loss."

---

## Slide 6: Multi-Tier SQL Security & Human Approval
**Time Allocation:** 1:00 (5:15 – 6:15)

### Slide Visual Content
- **Five Layers of Defense in Depth:**
  1. **Prompt Boundaries**: Explicit system directives forbidding data modification.
  2. **AST SQL Parser**: Verifies single-statement `SELECT` / `WITH`; blocks stacked queries.
  3. **Disallowed Command Filter**: Rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, `PRAGMA`.
  4. **SQLite C-Authorizer**: Engine callback (`sqlite3.set_authorizer`) rejects write opcodes at runtime.
  5. **OS Read-Only File Connection**: Opened with `file:ecommerce.db?mode=ro`.
- **Human-in-the-Loop Approval Modal:**
  - Configurable setting: `require_sql_approval` (enabled via Settings dialog).
  - Displays formatted SQL, execution justification, and estimated row impact.
  - User can click **Approve** or **Reject** (with natural-language feedback passed back to LLM).

### Speaker Notes
> "Security is an absolute prerequisite when deploying LLMs over databases. We implement five independent layers of defense in depth:
> 
> First, prompt-level instructions prohibit modifications.
> Second, an AST parser verifies that queries are strictly read-only `SELECT` or `WITH` queries, and ensures only one statement is present, defeating query stacking injection.
> Third, all data-modifying keywords are strictly blocked.
> Fourth, even if an injection bypassed parsing, our SQLite C-authorizer callback intercepts the database engine itself and refuses to execute write opcodes.
> Fifth, the database file connection is opened with URI parameter `mode=ro`, meaning the operating system kernel blocks writes.
> 
> Additionally, for regulated environments, we provide an optional Human-in-the-Loop approval dialog. The user is presented with the generated query and explanation, and can either approve it or reject it with corrective feedback."

---

## Slide 7: Deterministic Reporting & Canonical Validation
**Time Allocation:** 1:15 (6:15 – 7:30)

### Slide Visual Content
- **The Canonical Reporting Pipeline:**
  - **Period Integrity**: Resolves half-open interval $[T_{\text{start}}, T_{\text{end}})$. Detects zero-record periods and renders Red/Pink Data Availability Notice.
  - **KPI Normalization Contract**:
    - Accepts structured dictionaries, delimited strings (`"Label: Value"`), and plain strings.
    - Automatically reconciles unpopulated KPI values against computed ground-truth metrics.
  - **Strict Mathematical Invariants**:
    - $\text{Vertical AOV} = \frac{\text{Net Revenue}}{\text{Total Orders}}$ (horizontal row averaging strictly forbidden).
    - Gross Sales vs Net Revenue separation (discounts, taxes, and shipping handled accurately).
    - Orders vs Transactions separation (one order may have multiple transaction attempts).
- **Visualization Engine (22 Vector Chart Renderers):**
  - Pure ReportLab vector graphics (no matplotlib, no web engines).
  - Strict chart eligibility: Pie charts require $\ge 2$ categories (suppresses 100% single-slice charts).
  - Two-pass `NumberedCanvas` renders dynamic total page counts ("Page X of Y").

### Speaker Notes
> "Slide seven presents the heart of our deterministic reporting engine.
> 
> When raw SQL results return, they pass into our `CanonicalSQLDataset` engine. Here, the system enforces mathematical invariants:
> 
> First, Average Order Value is computed vertically as total net revenue divided by total distinct orders. Summing or averaging individual rows horizontally is mathematically invalid and blocked.
> 
> Second, our KPI Normalization Contract accepts structured dicts or plain strings from the model and automatically reconciles them against calculated ground-truth figures.
> 
> Third, our visualization engine provides 22 native ReportLab vector chart renderers—including grouped bars, donuts, and matrix heatmaps. Before any chart is drawn, an eligibility validator inspects it. For example, if a pie chart has only one category or sums to zero, it is automatically suppressed with an explanatory warning, preventing deceptive visualizations.
> 
> Finally, multi-page tables are paginated cleanly with repeated headers, and a two-pass canvas calculates dynamic 'Page X of Y' footers."

---

## Slide 8: Live Demonstration Scenario
**Time Allocation:** 1:45 (7:30 – 9:15)

### Slide Visual Content
- **Demonstration Request (The Complex Acceptance Scenario):**
  > *"I want an output report in PDF file, exporting last month orders, sales, revenue, transactions. I want graphical historical bar charts, some distribution pies and matrix graphs. Provide also at the end of the report data in table format."*
- **Observed System Execution:**
  1. **Schema Discovery**: Agent calls `inspect_database_schema(table_name="ALL")`.
  2. **Period Resolution**: Identifies current system date is late 2026; requested month (October 2026) has 0 records; comparison month is September 2026.
  3. **SQL Execution**: Executes multi-table join across `orders`, `order_items`, `payments`, and `products`.
  4. **Validation & Rendering**: PDF generated (7 pages, 62 KB, 22 vector graphics).
  5. **Visual Output**:
     - Page 1: Red Data Availability Notice + Requested (0) vs September KPI Cards.
     - Pages 2–4: Historical Comparison Trends, Revenue by Channel, Payment Distributions.
     - Pages 5–7: Paginated `LongTable` data tables.

### Speaker Notes
> *(Live action or video demonstration)*
> "Now, let us observe the system executing live.
> 
> We submit the exact acceptance scenario: asking for last month's orders, sales, revenue, and transactions, with bar charts, distribution pies, matrix graphs, and data tables.
> 
> Notice what happens in the Activity Inspector:
> The planner creates a 3-step DAG. It calls `inspect_database_schema`, examines the 7 tables, and formulates the SQL queries.
> 
> Now observe the critical period resolution:
> The agent determines that the database has transactions up through September 29, 2026, meaning October 2026 contains zero records.
> 
> Instead of crashing, hallucinating, or silently faking October data, the pipeline:
> 1. Displays October KPIs accurately as 0 orders and $0.00 revenue.
> 2. Flags this immediately with a Red Data Availability Notice banner on page one.
> 3. Automatically uses September 2026 as an explicit historical comparison baseline.
> 
> In less than a minute, the PDF compiles. Notice the embedded viewer on the right: vector bar charts, pie distributions, and multi-page tables with alternating rows and dynamic 'Page 1 of 7' footers. Every single number reconciles with the underlying SQLite database."

---

## Slide 9: Engineering Challenges & Technical Trade-offs
**Time Allocation:** 1:00 (9:15 – 10:15)

### Slide Visual Content
- **Key Engineering Hurdles Overcome:**
  1. **Small Model Hallucinations**:
     - *Issue*: `qwen3.5:4b` originally hallucinated non-existent columns (`o.start_date`, `oi.subtotal`).
     - *Solution*: Dynamic schema injection and automated regex SQL remediation prompts.
  2. **KPI Type Polymorphism**:
     - *Issue*: LLMs emitted string KPIs (`"Total Orders (September 2026)"`) instead of mappings, causing `AttributeError`.
     - *Solution*: Developed universal KPI normalization (`normalize_kpi_entry`) with reconciliation fallback.
  3. **Subprocess Concurrency & PyInstaller Bundling**:
     - *Issue*: Child MCP server crashed if packaged binary attempted to launch duplicate Qt GUI instances.
     - *Solution*: Routed `--mcp-server` flag in `app/main.py` directly to FastMCP stdio loop before `QApplication` instantiation.
  4. **Test Suite Completeness**:
     - Maintained **463 automated tests** across 36 modules with **100% pass rate**.

### Speaker Notes
> "During the engineering of this project, we faced several non-trivial challenges:
> 
> First, small 4-billion parameter models are prone to subtle schema confusions—such as querying `subtotal` on `order_items` rather than `orders`. We solved this by implementing real-time schema remediation in the orchestrator, guiding the model back on track if SQLite returns an error.
> 
> Second, when the model returned KPIs as plain strings rather than key-value dictionaries, it initially triggered validation errors. We solved this by engineering a polymorphic KPI normalization engine that handles structured dicts, delimited strings, and plain labels.
> 
> Third, packaging a dual-mode application with PyInstaller: when the main GUI spawns its child MCP process, running the same binary could accidentally start a second GUI window. We solved this by intercepting the `--mcp-server` flag at the very first line of `app/main.py`, launching pure stdio JSON-RPC without loading Qt libraries.
> 
> Today, the entire suite of 463 automated tests passes with zero failures."

---

## Slide 10: Conclusions, Academic Impact & Future Work
**Time Allocation:** 0:45 (10:15 – 11:00)

### Slide Visual Content
- **Key Achievements:**
  - Delivered a production-grade, 100% offline autonomous reporting desktop application.
  - Successfully bridged modern open standards: **Model Context Protocol (FastMCP)** + **Local Ollama** + **PySide6**.
  - Guaranteed mathematical accuracy and data protection via multi-tiered deterministic verification.
  - Comprehensive documentation: 5 authoritative root guides (`README.md`, `DEPLOY.md`, `STRUCTURE.md`, `FEATURE.md`, `PRESENTATION.md`).
- **Future Enhancements:**
  - Multi-database cross-federation (SQLite + DuckDB for OLAP aggregation).
  - Streaming chart previews during SQL execution.
  - Multi-modal local model support for automated visual quality auditing.

### Speaker Notes
> "In conclusion, the Local Report SQL Agent demonstrates that enterprise-grade, privacy-preserving business intelligence does not require massive cloud infrastructure or proprietary remote LLMs.
> 
> By combining declarative AI planning with the Model Context Protocol and rigorous deterministic validation, we have built a system that is private, secure, mathematically verifiable, and publication-ready.
> 
> The codebase is fully documented across our five root guides, with automated cross-platform packaging and smoke testing.
> 
> Thank you for your time and attention. I am now ready to answer your questions."

---

## Anticipated Defense Q&A (Professor & Examiner Questions)

### Q1: "Why did you use the Model Context Protocol (MCP) instead of simply having the agent call Python functions directly in-process?"
**Candidate Answer:**
> "Using FastMCP provides three vital engineering advantages:
> 1. **Architectural Decoupling**: Database drivers, SQL execution, and ReportLab PDF compilation run in an isolated subprocess. If a complex chart compilation or memory-intensive query crashes, the main PySide6 desktop GUI remains unharmed.
> 2. **Standardization**: MCP is an open standard backed by the industry. Any other MCP-compliant client (such as Claude Code, Cursor, or custom agents) can connect to our `local-report-sql-agent-mcp` server without code changes.
> 3. **Security Boundary**: The child subprocess communicates strictly over standard input/output JSON-RPC. There is no shared memory or direct object mutation between the LLM orchestration layer and database file handles."

### Q2: "How do you guarantee that the local LLM doesn't perform SQL injection or delete the database?"
**Candidate Answer:**
> "We implement five layered security controls:
> First, our `SQLValidator` parses the SQLite Abstract Syntax Tree, strictly permitting only single-statement `SELECT` and `WITH` queries. Stacking queries with semicolons is rejected.
> Second, all data modification keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`) are filtered and rejected.
> Third, we register a C-level SQLite authorizer callback (`set_authorizer`) directly on the connection; if any write opcode is reached, SQLite halts execution immediately.
> Fourth, the database connection itself is opened in read-only URI mode (`file:ecommerce.db?mode=ro`).
> Fifth, we continuously verify the database file's SHA-256 hash before and after test suites, proving it remains immutable."

### Q3: "What happens if a user asks for a date range where no data exists, such as future months or missing periods?"
**Candidate Answer:**
> "That was one of the primary defects we diagnosed and solved. Our `PeriodAvailabilityContext` computes the exact half-open interval $[T_{\text{start}}, T_{\text{end}})$.
> If zero rows are returned for the requested period, the system does not hallucinate or silently substitute old data into current KPI cards.
> Instead, it:
> 1. Renders October KPIs accurately as 0 orders and $0.00 revenue.
> 2. Injects a high-visibility Red 'Data Availability Notice' banner on page one of the PDF.
> 3. Automatically identifies the latest available complete period—September 2026—and displays it in an explicitly labeled 'Historical Comparison' section.
> This guarantees executive transparency without misleading the reader."

### Q4: "How does the ContextBuilder prevent context window overflow on small models like Qwen 3.5 4B?"
**Candidate Answer:**
> "Our `ContextBuilder` implements priority-tiered token budgeting.
> It divides context items into three priority levels: `HIGH` for system safety instructions and active MCP tool schemas; `MEDIUM` for stage-specific templates and domain skills; and `LOW` for prior tool outputs and historical samples.
> Depending on the active execution stage—such as Schema Discovery versus Report Synthesis—it allocates a strict ratio of the total configured context window (such as 128K tokens). If total tokens approach the budget, it drops `LOW` priority items first and truncates `MEDIUM` items, while strictly preserving `HIGH` priority boundaries."

### Q5: "How does your build script ensure reproducibility across different machines?"
**Candidate Answer:**
> "Our `scripts/build_macos.sh` script executes a strict 5-stage pipeline:
> Stage 1 checks the environment: verifying Python 3.13, dependency versions, and the exact SHA-256 checksum of `ecommerce.db`.
> Stage 2 runs our automated test suite (461 deterministic tests) to prevent packaging broken code.
> Stage 3 cleanly purges stale build artifacts.
> Stage 4 bundles the standalone executable and `.app` bundle using PyInstaller with explicit hidden imports for QtPdf and FastMCP.
> Stage 5 executes automated post-packaging smoke tests: confirming that `ReportSQLAgent --mcp-server` answers JSON-RPC queries, verifying bundled migration SQL files, and running a headless GUI startup via `QT_QPA_PLATFORM=offscreen`."

