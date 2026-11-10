# Local Report SQL Agent

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%206.10-green.svg)](https://doc.qt.io/qtforpython/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20qwen3.5%3A4b-orange.svg)](https://ollama.com/)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(FastMCP)-purple.svg)](https://modelcontextprotocol.io/)
[![ReportLab](https://img.shields.io/badge/Reporting-ReportLab%205.1-red.svg)](https://www.reportlab.com/)
[![Tests](https://img.shields.io/badge/Tests-463%20Passed-brightgreen.svg)]()

A production-grade, 100% offline desktop application that empowers users to query relational databases and synthesize publication-quality executive reports using natural language. 

Powered by a locally hosted Large Language Model (**Ollama `qwen3.5:4b`**), the official Python **Model Context Protocol (FastMCP)** stdio SDK, an immutable read-only **SQLite** data engine, an advanced **22-chart vector visualization engine**, and an asynchronous **PySide6** desktop interface with an integrated vector PDF previewer.

---

## Authoritative Documentation Suite

This repository is fully documented across five core root guides:

1. [**`README.md`**](README.md) — System overview, quick start, architecture, and primary entry point (this file).
2. [**`DEPLOY.md`**](DEPLOY.md) — End-to-end deployment instructions for macOS and Windows, packaging scripts, and troubleshooting.
3. [**`STRUCTURE.md`**](STRUCTURE.md) — Complete repository layout, Python package responsibilities, and module mappings.
4. [**`FEATURE.md`**](FEATURE.md) — Exhaustive technical specification of all system features, security controls, and pipelines.
5. [**`PRESENTATION.md`**](../4_Presentation/PRESENTATION.md) — 10-minute slide script for university evaluation with demonstration walkthrough and defense Q&A.

---

## 1. Problem Statement

In enterprise environments, operational databases contain sensitive transactional records that cannot be exposed to third-party cloud LLM APIs due to privacy regulations (GDPR), proprietary business secrets, or data sovereignty constraints. 

Furthermore, generic LLM "text-to-SQL" interfaces suffer from severe operational risks:
- **Hallucinated Metrics**: Small language models frequently fabricate numbers or calculate mathematically invalid ratios (e.g. averaging row-level averages).
- **Security Vulnerabilities**: Naive database connections expose data to SQL injection or destructive `DROP`/`UPDATE` mutations.
- **Silent Data Substitution**: If asked for October data and none exists, naive tools often substitute September without alerting the user.
- **Poor Output Formats**: Most AI agents return plain text or raw tables rather than styled, executive-ready multi-page documents.

---

## 2. Project Objectives & Solution

The **Local Report SQL Agent** addresses these challenges by enforcing a strict division of responsibilities:

> **The LLM interprets user intent and formulates SQL queries.**  
> **Deterministic Python executes queries, reconciles numbers, verifies chart eligibility, and renders vector PDF/CSV reports.**

### Core Capabilities
- **100% Offline & Private**: Zero external network requests. Prompts, schemas, queries, and reports never leave your local workstation.
- **Model Context Protocol (FastMCP)**: Decoupled database and reporting tools executing in an isolated subprocess over standard input/output (`stdio`).
- **Defense-in-Depth SQL Security**: AST syntax parsing, single-statement verification, keyword blacklisting, SQLite C-authorizer callbacks, and read-only connection handles (`mode=ro`).
- **Deterministic Reporting Engine**: Canonical reconciliation of Gross Sales, Net Revenue, Orders, Transactions, and vertical Average Order Value (AOV).
- **Data Availability Protection**: Detects zero-record periods and displays verified zeros alongside an explicit Red Data Availability Notice banner, promoting comparison months to dedicated historical sections.
- **22 ReportLab Vector Chart Renderers**: Native vector graphics (bars, lines, areas, pies, donuts, matrix heatmaps, scatter plots) with automatic single-category suppression.
- **Desktop Concurrency & Preview**: Responsive PySide6 interface featuring live chat, an Activity Inspector with DAG execution tracking, and an embedded `QPdfView` previewer.

---

## 3. Technology Stack

- **GUI Framework**: PySide6 6.10 (Qt6 Widgets, QtPdf, QThread concurrency)
- **Local Inference Engine**: Ollama (`http://localhost:11434`) running `qwen3.5:4b`
- **Tool Protocol**: Official Model Context Protocol SDK (`mcp` 1.30.0 / FastMCP)
- **Database Engine**: SQLite 3.x (Relational schema: 7 tables, 499,385 records; immutable)
- **Reporting Engine**: ReportLab 5.1 (Platypus flowables, `LongTable` pagination, vector graphics)
- **Testing & Verification**: Pytest 9.2 (463 automated tests: 461 deterministic + 2 live Ollama workflows)
- **Packaging**: PyInstaller 6.22 (Standalone macOS `.app` bundle and Windows `.exe`)

---

## 4. System Architecture

```mermaid
flowchart TD
    User([User Prompt]) --> GUI[PySide6 GUI: Chat & Activity Inspector]
    
    subgraph DesktopApp["Main Application Process (1_Source/run_app.py)"]
        GUI <--> Worker[AgentWorker QThread Bridge]
        Worker <--> Orch[AgentOrchestrator Loop]
        Orch <--> Planner[TaskPlanner & DAG Manager]
        Orch <--> CB[ContextBuilder: 128K Token Budget]
        Orch <--> Memory[(SQLite Agent Memory WAL)]
        Orch <--> Client[MCPStdioClient]
    end
    
    subgraph LocalOllama["Local Inference (localhost:11434)"]
        Orch <== "Async HTTP (/api/chat)" ==> OllamaModel[Ollama Daemon: qwen3.5:4b]
    end
    
    subgraph MCPProcess["Isolated Subprocess (mcp_layer.server)"]
        Client <== "JSON-RPC 2.0 (stdio)" ==> Server[FastMCP Server]
        Server --- DBTools[Database Tools: inspect_schema, get_sample]
        Server --- SQLTools[SQL Tools: prepare_sql, execute_sql]
        Server --- RepTools[Reporting Tools: generate_pdf, generate_csv]
    end
    
    DBTools --> SQLiteDB[(2_Database/ecommerce.db [Read-Only])]
    SQLTools --> SQLiteDB
    RepTools --> RepEngine[Deterministic Report Engine & Validator]
    RepEngine --> OutputFiles[5_Reports/generated/*.pdf & *.csv]
    OutputFiles --> EmbeddedViewer[Embedded QtPdf Previewer]
```

---

## 5. Prerequisites

1. **Operating System**: macOS 12+ (Apple Silicon or Intel) or Windows 10/11 (64-bit).
2. **Python**: Python 3.10 to 3.13 (Python 3.13 certified).
3. **Local Ollama Daemon**: Download and install from [ollama.com](https://ollama.com).
4. **Certified Model**:
   ```bash
   ollama pull qwen3.5:4b
   ```

---

## 6. Quick Start

### 6.1 Running in Development Mode
```bash
# 1. Clone repository and navigate to root
cd FinalProject_SQLAgent

# 2. Activate virtual environment
source .venv/bin/activate        # macOS / Linux
# .\.venv\Scripts\Activate.ps1    # Windows PowerShell

# 3. Verify environment and database integrity
python 1_Source/scripts/verify_environment.py

# 4. Launch the desktop GUI
python 1_Source/run_app.py
```

### 6.2 Packaging Standalone Executables
```bash
# macOS Build (.app bundle in 6_Builds/macOS/)
./1_Source/scripts/build_macos.sh

# Windows Build (.exe standalone in 6_Builds\Windows\)
.\1_Source\scripts\build_windows.ps1
```
For detailed packaging flags (`--with-live-tests`, `--skip-tests`), consult [**`DEPLOY.md`**](DEPLOY.md).

---

## 7. Example Natural-Language Requests

The agent accepts conversational, reporting, and analytical prompts:

- **Executive Reporting (Full Pipeline)**:
  > *"I want an output report in PDF file, exporting last month orders, sales, revenue, transactions. I want graphical historical bar charts, some distribution pies and matrix graphs. Provide also at the end of the report data in table format."*
- **Rankings & Comparison**:
  > *"Retrieve the most profitable 10 Orders of all time and present them on an output PDF with bar charts, distribution pies, and a data table."*
- **Category & Channel Analysis**:
  > *"Analyze our monthly sales trends for the past year and visualize revenue growth by product category with a line chart and matrix heatmap."*
- **Raw CSV Data Export**:
  > *"Export the monthly captured revenue by payment method to a CSV file."*

---

## 8. Current System Limitations

- **Local Inference Latency**: On CPUs without GPU or Metal hardware acceleration, local generation with `qwen3.5:4b` may take 30–90 seconds per multi-step analytical turn.
- **Database Immutability**: `ecommerce.db` is strictly read-only. The system does not support writing analytical results back to transactional tables.
- **Complex Multi-Way Joins**: When joining 4 or more tables (`orders`, `order_items`, `products`, `payments`), small local models require explicit schema reminders to avoid column misattributions. The built-in `ContextBuilder` dynamically injects these definitions.

For in-depth architectural details, see [**`FEATURE.md`**](FEATURE.md).
