# Local Report SQL Agent

A desktop application that turns natural-language report requests into
validated, **read-only** SQL against a local SQLite database, and produces
PDF or CSV reports. Everything runs on your machine:

* **LLM**: Ollama (`qwen3.5:4b`) via the native HTTP API on `localhost`
* **Tools**: a Python MCP server (official `mcp` SDK, stdio transport)
* **Database**: SQLite (`data/ecommerce.db`), opened read-only by the agent
* **GUI**: PySide6

No cloud services, paid APIs or telemetry are used.

> Status: under incremental development (see *Milestones* below).

## Architecture

```
PySide6 GUI ──► Agent orchestrator ──► Ollama (localhost, qwen3.5:4b)
                     │
                     ▼
                 MCP client ──stdio──► MCP server (subprocess)
                                         ├─ inspect_database_schema
                                         ├─ get_table_sample
                                         ├─ prepare_sql_query
                                         ├─ execute_readonly_sql
                                         ├─ generate_pdf_report
                                         └─ generate_csv_report
```

| Package       | Responsibility                                          |
|---------------|---------------------------------------------------------|
| `config/`     | Settings (JSON + env overrides), paths, logging, prompts |
| `app/`        | PySide6 GUI: main window, views, background workers     |
| `agent/`      | Ollama client, conversation state, tool-calling loop    |
| `mcp_layer/`  | MCP server, MCP client, tool implementations            |
| `database/`   | Connections, importer, schema inspector, query executor |
| `reporting/`  | PDF (ReportLab) and CSV generators, report history      |
| `scripts/`    | Environment verification, dataset import, build scripts |
| `tests/`      | Pytest suite (uses temporary databases only)            |

> The MCP package is named `mcp_layer/` rather than `mcp/` because a local
> `mcp` package would shadow the official `mcp` SDK on import.

## Requirements

* Python **3.13**
* [Ollama](https://ollama.com) running locally, with the model pulled:
  ```
  ollama pull qwen3.5:4b
  ```
* The Kaggle dataset *Synthetic E-commerce Database (7 Tables)*, downloaded
  manually (ZIP or extracted CSVs). Place it in `data/raw/`.

## Setup

macOS / Linux:
```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/verify_environment.py
```

Windows (PowerShell):
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\verify_environment.py
```

## Configuration

Defaults live in `config/settings.py`; the GUI Settings page writes
`settings.json`. Environment overrides are listed in `.env.example`.
The Ollama host must be local (`localhost`/`127.0.0.1`); remote hosts are rejected.

## Milestones

1. Environment and project initialisation ✅
2. Dataset import and SQLite
3. MCP server
4. Ollama agent
5. GUI
6. Integration
7. QA and packaging

