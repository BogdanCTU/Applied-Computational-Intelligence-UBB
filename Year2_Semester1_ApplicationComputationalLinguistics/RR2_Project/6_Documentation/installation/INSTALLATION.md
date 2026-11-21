# Installation Guide — Agent-OM Local Environment Setup

## 1. System Requirements

- **Operating System:** macOS 14+ (`arm64` Apple Silicon M1/M2/M3/M4) or Windows 10/11 (64-bit `x86_64`).
- **Memory:** 16 GB RAM recommended (8 GB minimum for $\le 4\text{B}$ models).
- **Python:** Python `3.13.x` (`3.13.16` verified).
- **Database:** PostgreSQL `16.x` with `pgvector` (`0.8.0+`) listening on `127.0.0.1:5432`.
- **LLM Engine:** Ollama `0.40+` listening on `http://127.0.0.1:11434`.

---

## 2. Step-by-Step Installation

### Step 1: Install and Start PostgreSQL 16 + `pgvector`

**On macOS (via Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
/opt/homebrew/opt/postgresql@16/bin/psql -h 127.0.0.1 -p 5432 -d postgres -c "CREATE ROLE postgres WITH SUPERUSER LOGIN;"
```

To compile and install the `pgvector` extension against `postgresql@16`:
```bash
mkdir -p /tmp/pgvec_build && cd /tmp/pgvec_build
curl -sL https://github.com/pgvector/pgvector/archive/refs/tags/v0.8.0.tar.gz -o pgvector.tar.gz
tar -xzf pgvector.tar.gz && cd pgvector-0.8.0
make PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
make install PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
/opt/homebrew/opt/postgresql@16/bin/psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**On Windows (using Portable PostgreSQL):**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_postgres.ps1
```

---

### Step 2: Install Ollama and Pull Verified Local Models

Ensure Ollama is running (`ollama serve`) on `http://127.0.0.1:11434`, then pull the verified $\le 4.0\text{B}$ chat models and dedicated embedding models:

```bash
# Dedicated Embedding Models (768-dim and 1024-dim)
ollama pull nomic-embed-text
ollama pull mxbai-embed-large

# Verified <= 4.0B Parameter Generative Chat Models
ollama pull qwen2.5:3b         # 3,085,938,688 total parameters (3.09B <= 4.0B)
ollama pull deepseek-r1:1.5b   # 1,777,088,000 total parameters (1.78B <= 4.0B)

# Optional: 8B Upstream Agent-OM-Lite Parity Model
ollama pull llama3:8b          # 8,030,261,248 total parameters (4096-dim via LlamaEmbeddingBridge)
```

---

### Step 3: Create the Python 3.13 Virtual Environment

From the project root directory:

```bash
# macOS / Linux:
python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements-dev.txt

# Windows PowerShell:
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

---

### Step 4: Verify the Installation

Run the import check, test suite, and GUI headless self-test:

```bash
# 1. Verify all 17 core imports
.venv/bin/python -c "import rdflib, breame, pandas, numpy, psycopg2, asyncpg, pgvector, ollama, langchain_core, langchain_ollama, langchain_text_splitters, dotenv, yaml, PySide6, matplotlib, pytest, pytestqt, PyInstaller; print('ALL_17_IMPORTS_OK')"

# 2. Run the full 133-test suite
.venv/bin/python -m pytest 2_Tests/ -v

# 3. Verify all 10 GUI screens offscreen
.venv/bin/python run_gui.py --self-test
```
