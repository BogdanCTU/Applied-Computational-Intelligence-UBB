# Project Structure & Directory Blueprint

**Project**: Local Report SQL Agent  
**Language**: Python 3.11+ / PySide6 / SQLite / FastMCP  
**Target Environment**: 100% Local (macOS / Windows / Linux)  
**Parent Document**: [COMPLETE_SYSTEM_REFERENCE.md](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/docs/COMPLETE_SYSTEM_REFERENCE.md)

---

## 1. Directory Tree Overview

```text
FinalProject_SQLAgent/
├── run_app.py                          # Application entry point and crash logger
├── ReportSQLAgent.spec                 # PyInstaller standalone & bundle packaging spec
├── requirements.txt                    # Pinned Python package dependencies
├── pytest.ini                         # Pytest configuration and test filters
├── README.md                          # Repository overview and quickstart
├── BUILD.md                           # Packaging and multi-platform compilation guide
├── PHASE_6_INTEGRATION_REPORT.md      # Phase 6 verification & audit deliverable
├── Manual_Prompts_Sample.md           # Sample test prompts for natural language queries
│
├── agent/                             # Core Agent Intelligence & Orchestration Layer
│   ├── __init__.py                    # Module export definitions
│   ├── orchestrator.py                # Central workflow coordinator & event dispatcher
│   ├── task_models.py                 # Task, TaskStep, TaskPlan, and status enums
│   ├── task_manager.py                # Structured task execution state & SQLite sync
│   ├── task_planner.py                # Goal decomposition & reusable step generation
│   ├── context_models.py              # ContextSection, priorities, and token reports
│   ├── context_builder.py             # Context window allocation (32K-256K) & packing
│   ├── checkpoint_models.py           # Checkpoint metadata, types, and recovery policies
│   ├── checkpoint_manager.py          # State persistence, rollback, and recovery
│   ├── skill_models.py                # Skill metadata schema, YAML parser, token estimator
│   ├── skill_manager.py               # Deterministic skill discovery & Kahn cycle resolution
│   ├── ollama_client.py               # Local Ollama HTTP client & context validator
│   ├── tool_handler.py                # MCP tool execution, parameter coercion & retry
│   ├── conversation.py                # Chat history management & tool output compactor
│   ├── events.py                      # Activity events, categories, and PII masking
│   └── system_prompt.py               # Dynamic system prompt & operating guidelines
│
├── app/                               # PySide6 Desktop GUI Presentation Layer
│   ├── __init__.py                    # App package initialization
│   ├── main.py                        # GUI startup, 5-stage initialization & fatal dialog
│   ├── main_window.py                 # Primary split-view window & workspace controller
│   ├── style.py                       # Modern dark-theme stylesheet definitions
│   ├── dialogs/                       # Modal dialog windows
│   │   ├── __init__.py                # Dialogs initialization
│   │   └── sql_approval_dialog.py     # Human-in-the-loop SQL security confirmation dialog
│   ├── models/                        # Qt data view models
│   │   ├── __init__.py                # Models initialization
│   │   └── csv_table_model.py         # QAbstractTableModel for tabular CSV preview
│   ├── views/                         # Primary application view panels
│   │   ├── __init__.py                # Views initialization
│   │   ├── chat_view.py               # Lateral conversation feed & prompt input bar
│   │   ├── history_view.py            # Generated reports history browser & open action
│   │   └── settings_view.py           # Centralized configuration dialog (context/Ollama)
│   ├── widgets/                       # Custom modular GUI components
│   │   ├── __init__.py                # Widgets initialization
│   │   ├── activity_inspector_widget.py# Live token context bar & agent activity inspector
│   │   ├── message_widget.py          # Chat message bubbles with Markdown & tool cards
│   │   ├── report_preview_widget.py   # Multi-tab native PDF (QPdfView) & CSV viewer
│   │   ├── sql_highlighter.py         # PySide6 syntax highlighter for SQL queries
│   │   └── sql_preview_widget.py      # Formatted SQL preview box with copy actions
│   └── workers/                       # Qt concurrency & background threads
│       ├── __init__.py                # Workers initialization
│       ├── agent_worker.py            # QThread runner for non-blocking agent tasks
│       └── worker_signals.py          # Qt signals bridging async asyncio and GUI threads
│
├── config/                            # Global Configuration & Environment Settings
│   ├── __init__.py                    # Config package initialization
│   ├── settings.py                    # Pydantic v2 settings (Agent, DB, UI, Ollama)
│   ├── paths.py                       # Cross-platform path resolution & frozen bundle detection
│   ├── logging_setup.py               # Rotating file logging & stderr formatter
│   └── prompts.py                     # Static prompt templates & instruction blocks
│
├── database/                          # Relational Storage & SQLite Engine
│   ├── __init__.py                    # Database package initialization
│   ├── connection.py                  # Read-only URI connection & C-authorizer hooks
│   ├── query_executor.py              # AST inspection, timeout watchdog & row caps
│   ├── schema_inspector.py            # SQLite table, column, and foreign key introspector
│   └── importer.py                    # CSV to SQLite relational schema import engine
│
├── data/                              # Local Datastores & Raw Datasets
│   ├── ecommerce.db                   # Authoritative business database (499,385 records)
│   ├── agent_memory.db                # Agent memory store (episodes, facts, checkpoints)
│   └── raw/                           # Source CSV data files for database creation
│       ├── customers.csv              # Customer demographics & account records
│       ├── products.csv               # Product catalog, categories, and unit pricing
│       ├── orders.csv                 # Order headers, dates, and order statuses
│       ├── order_items.csv            # Line-item details, quantities, and discounts
│       ├── payments.csv               # Payment transactions, payment methods & statuses
│       ├── shipments.csv              # Delivery logistics, tracking, and carrier info
│       ├── returns.csv                # Product returns, return reasons, and refunds
│       ├── ecommerce.sqlite           # Reference raw SQLite database
│       └── archive.zip                # Compressed raw archive backup
│
├── mcp_layer/                         # Model Context Protocol (FastMCP) Layer
│   ├── __init__.py                    # MCP layer initialization
│   ├── server.py                      # FastMCP stdio server exposing 6 local tools
│   ├── client.py                      # Async stdio MCP client communicating with server
│   └── tools/                         # MCP Tool Implementations
│       ├── __init__.py                # Tools initialization
│       ├── database_tools.py          # Schema inspection and table sampling tools
│       ├── sql_tools.py               # SQL syntax validation and read-only execution tools
│       └── reporting_tools.py         # PDF and CSV export generation tools
│
├── memory/                            # Persistent Agent Memory & Schema Migrations
│   ├── __init__.py                    # Memory package initialization
│   ├── repository.py                  # SQLite memory repository for episodic/semantic items
│   ├── models.py                      # Memory records, facts, and tool execution traces
│   └── migrations/                    # Atomic database migration scripts
│       ├── __init__.py                # Migration runner and frozen directory resolver
│       ├── 001_initial_schema.sql     # Initial schema (episodes, facts, execution traces)
│       ├── 002_checkpoint_recovery.sql# Checkpoint storage, step states, and recovery logs
│       └── 003_skill_registry_enhancements.sql # Skill registry, dependencies & stats
│
├── reporting/                         # Deterministic Report Generation Engines
│   ├── __init__.py                    # Reporting package initialization
│   ├── canonical_data.py              # Single source of truth dataset & KPI calculator
│   ├── report_spec.py                 # Structured report specification dataclasses
│   ├── dynamic_pdf_composer.py        # ReportLab Platypus multi-component document composer
│   ├── pdf_generator.py               # PDF page templates, canvas numbering & styles
│   ├── csv_generator.py               # RFC-4180 compliant CSV export engine
│   ├── chart_builder.py               # 22 vector chart renderers (ReportLab graphics)
│   ├── chart_registry.py              # Chart type registry and capability validator
│   ├── report_manager.py              # Report metadata tracking & directory manager
│   └── date_utils.py                  # Financial calendar calculations & date helpers
│
├── skills/                            # Markdown & YAML Domain Skill Definitions
│   ├── sql/                           # SQL query generation best practices
│   │   ├── metadata.yaml              # Skill metadata, semver, and tags
│   │   └── SKILL.md                   # SQLite idioms, join patterns, and date math
│   ├── reporting/                     # Business report design standards
│   │   ├── metadata.yaml              # Skill metadata, semver, and tags
│   │   └── SKILL.md                   # Chart selection, KPI cards, and narrative layout
│   ├── data_analysis/                 # Exploratory data analysis guidelines
│   │   ├── metadata.yaml              # Skill metadata, semver, and tags
│   │   └── SKILL.md                   # Distribution, correlation, and anomaly analysis
│   └── data_validation/               # Data verification & sanity checks
│       ├── metadata.yaml              # Skill metadata, semver, and tags
│       └── SKILL.md                   # Null checks, boundary tests, and revenue reconciliation
│
├── scripts/                           # Build, Deployment & Acceptance Scripts
│   ├── build_macos.sh                 # macOS PyInstaller build script & bundle verifier
│   ├── build_windows.ps1              # Windows PowerShell packaging script
│   ├── verify_environment.py          # Pre-build & runtime environment verifier
│   ├── import_dataset.py              # Command-line CSV to SQLite data importer
│   ├── verify_milestone8_acceptance.py# Acceptance validation for Milestone 8 (SQL Security)
│   ├── verify_milestone9_acceptance.py# Acceptance validation for Milestone 9 (Reporting)
│   └── verify_milestone10_acceptance.py# Acceptance validation for Milestone 10 (Charts)
│
├── tests/                             # Comprehensive Automated Test Suite (431 tests)
│   ├── __init__.py                    # Test suite initialization
│   ├── test_agent.py                  # Orchestrator & conversation lifecycle tests
│   ├── test_agent_intelligence_integration.py # End-to-end intelligence layer integration
│   ├── test_approval_config.py        # Human approval gate & configuration modes
│   ├── test_checkpoint_manager.py     # Checkpoint rollback and recovery tests
│   ├── test_checkpoint_models.py      # Checkpoint data models & serialization
│   ├── test_checkpoint_repository.py  # Checkpoint persistence in SQLite
│   ├── test_context_builder.py        # Dynamic context packing & reservation tests
│   ├── test_context_models.py         # Context models and priority scoring
│   ├── test_context_relevance.py      # Semantic relevance filtering & pruning
│   ├── test_context_security.py       # PII masking & injection prevention in context
│   ├── test_context_window.py         # 32K-256K window tiering & Ollama num_ctx tests
│   ├── test_database.py               # Read-only SQLite enforcement & query execution
│   ├── test_database_discovery_reporting.py # Schema discovery & summary generation
│   ├── test_dynamic_pdf_milestone9.py # Platypus PDF dynamic composing tests
│   ├── test_e2e_workflows.py          # Full prompt-to-PDF workflow tests
│   ├── test_gui.py                    # PySide6 UI components and widget tests
│   ├── test_macos_startup.py          # Packaged bundle startup & frozen path tests
│   ├── test_mcp_reliability.py        # Stdio connection resilience & timeouts
│   ├── test_mcp_tools.py              # All 6 MCP tools functionality tests
│   ├── test_memory_migrations.py      # Atomic SQLite migration execution tests
│   ├── test_memory_repository.py      # Episodic & semantic memory repository tests
│   ├── test_reporting.py              # PDF and CSV generator output verification
│   ├── test_reporting_accuracy.py     # Numeric calculation & deterministic KPI accuracy
│   ├── test_skill_manager.py          # Domain skill discovery & Kahn cycle detection
│   ├── test_skill_models.py           # Skill YAML parser & token estimator tests
│   ├── test_skill_security.py         # Path traversal & symlink escape prevention
│   ├── test_skill_selection.py        # Selective stage-based skill loading tests
│   ├── test_sql_validation.py         # SQL AST parsing & forbidden keyword filtering
│   ├── test_task_manager.py           # Structured task state & step transitions
│   ├── test_task_manager_sqlite.py    # Persistent task state synchronization
│   ├── test_task_models.py            # Task data models & serialization
│   ├── test_task_planner.py           # Task plan generation & goal decomposition
│   └── test_task_recovery.py          # Automatic task failure recovery & replanning
│
└── docs/                              # Project Documentation Corpus
    ├── COMPLETE_SYSTEM_REFERENCE.md   # Unified master system architecture reference
    ├── PROJECT_STRUCTURE_AND_DIRECTORIES.md # This document
    ├── COMPONENTS_AND_CLASSES.md      # Detailed classes, methods & contracts
    ├── TOOLS_AND_MCP_SPECIFICATION.md # Complete FastMCP tools specification
    ├── KNOWLEDGE_GRAPH_AND_FLOWS.md   # Visual Mermaid knowledge graphs & sequence diagrams
    ├── TERMINOLOGY_AND_DEFINITIONS.md # Comprehensive glossary, enums & error taxonomy
    ├── HOW_IT_WORKS_LIFECYCLE.md      # Step-by-step prompt-to-report execution lifecycle
    ├── ARCHITECTURE.md                # System architectural design & concurrency
    ├── AGENT_INTELLIGENCE_LAYER.md    # Agent intelligence layer & context windows
    ├── DATABASE.md                    # Database schema, indexing & read-only security
    ├── SECURITY.md                    # Multi-layer defensive security implementation
    ├── TESTING.md                     # Test strategy, fixtures & verification results
    ├── DEMO_GUIDE.md                  # Interactive demonstration & evaluation script
    ├── MACOS_STARTUP_FIX_REPORT.md    # macOS packaging root cause & fix audit report
    └── PROJECT_SUMMARY.md             # Academic evaluation summary & compliance matrix
```

---

## 2. Directory Responsibilities & Invariants

### 1. `agent/` — Intermediate Agent Intelligence Layer
- **Role**: Sits directly between the user interface, the local Ollama LLM (`qwen3.5:4b`), and MCP tools.
- **Key Files**:
  - [`orchestrator.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/orchestrator.py): Central conductor coordinating task state, checkpoints, LLM calls, and approval flows.
  - [`context_builder.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/context_builder.py): Allocates the 128K context window into priority tiers; prevents silent truncation.
  - [`task_planner.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/task_planner.py): Decomposes natural language queries into explicit, machine-decidable execution steps.
  - [`checkpoint_manager.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/checkpoint_manager.py): Captures state at critical transitions (`TASK_CREATED`, `PLAN_READY`, `TOOL_EXECUTION`).
  - [`skill_manager.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/skill_manager.py): Discovers, resolves, and loads Markdown domain skills with Kahn's algorithm cycle detection.
- **Invariants**:
  - Never bypasses security validation or human approval gates.
  - Never uses cloud LLMs; interacts strictly with local Ollama over HTTP loopback (`127.0.0.1:11434`).

### 2. `app/` — Desktop Presentation Layer (PySide6)
- **Role**: Provides a modern split-view desktop GUI with a lateral conversation view, native PDF viewer (`QPdfView`), tabular CSV preview (`QTableView`), activity inspector, and modal security dialogs.
- **Key Files**:
  - [`main_window.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/main_window.py): Top-level window hosting the report workspace and coordinating child views.
  - [`dialogs/sql_approval_dialog.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/dialogs/sql_approval_dialog.py): Modal human-in-the-loop review dialog presenting formatted SQL, affected tables, and risk level.
  - [`workers/agent_worker.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/app/workers/agent_worker.py): Executes async agent tasks on a secondary `QThread` without freezing the Qt GUI event loop.
- **Invariants**:
  - GUI interactions remain responsive at all times via asynchronous thread isolation.
  - No database or LLM network operations are executed on the main GUI thread.

### 3. `mcp_layer/` — Model Context Protocol Layer
- **Role**: Isolates tool execution in a standalone subprocess communicating via standard input/output (stdio) over JSON-RPC.
- **Key Files**:
  - [`server.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/server.py): FastMCP server instance registering the 6 authorized tools.
  - [`client.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/mcp_layer/client.py): Async stdio client handling handshake, tool discovery, and execution calls.
- **Invariants**:
  - Child MCP server operates with zero network listening sockets; only stdio transport is permitted.
  - Only registered tools can be invoked; arbitrary code execution is strictly prohibited.

### 4. `database/` — Relational Storage & Security Engine
- **Role**: Manages SQLite connections, query execution, and multi-layer read-only security.
- **Key Files**:
  - [`connection.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/database/connection.py): Opens database connections using percent-encoded `file:...mode=ro` URIs with `PRAGMA query_only = ON`.
  - [`query_executor.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/database/query_executor.py): Enforces low-level C-authorizer callbacks (`SQLITE_SELECT`, `SQLITE_READ` only), opcode watchdog timeouts, and strict row limits.
- **Invariants**:
  - Under no circumstances can database tables be mutated, created, or dropped.
  - Hash integrity of `data/ecommerce.db` must match `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`.

### 5. `reporting/` — Deterministic Reporting Engines
- **Role**: Generates professional PDF business documents (via ReportLab Platypus) and CSV files directly from validated SQL query results.
- **Key Files**:
  - [`canonical_data.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/canonical_data.py): Canonical dataset representing the single source of truth; calculates deterministic KPIs.
  - [`dynamic_pdf_composer.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/dynamic_pdf_composer.py): Assembles header, KPI summary cards, vector charts, tabular data, narrative findings, and optional SQL query appendix.
  - [`chart_builder.py`](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/reporting/chart_builder.py): Renders 22 distinct chart types (bars, lines, heatmaps, box plots, treemaps) as vector graphics.
- **Invariants**:
  - The LLM never invents numbers for reports; all metrics and chart series are computed deterministically in Python from the SQL result set.

