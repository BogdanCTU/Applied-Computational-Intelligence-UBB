# Python 3.13 Compatibility & Dependency Modernisation Guide
## Agent-OM: Scientific Replication, Local Adaptation & Desktop Application

**Last Updated:** 2026-11-20  
**Target Interpreter:** Python 3.13.16 (`arm64` / `x86_64`)  
**Upstream Reference Baseline:** Python 3.10.12 (`qzc438/ontology-llm`)

---

## 1. Architectural Strategy for Python 3.13 Compatibility

The original Agent-OM upstream repository (`qzc438/ontology-llm`) targeted Python 3.10 and relied on older pinned versions of C-extension libraries (`pandas==2.0.3`, `numpy==1.26.4`, `asyncpg==0.28.0`, `psycopg2-binary==2.9.9`) and heavyweight transitive dependencies (`torch`, `transformers`, `openai`).

Under Python 3.13 (which finalized PEP 594 dead-battery removals, updated the CPython C-API for `PyLong` and frame evaluation, and requires updated Cython/pybind11 wheels), installing the historical pins from source fails compilation. Our modernisation preserves 100% of Agent-OM's algorithmic behavior while selecting binary-wheel-compatible versions without installing PyTorch.

---

## 2. Package-by-Package Compatibility Matrix

| Package | Upstream (Py 3.10) | Modernised (Py 3.13) | Binary Wheel Status | Compatibility & Algorithmic Parity Notes |
| :--- | :---: | :---: | :---: | :--- |
| `rdflib` | `7.0.0` | `7.6.0` | Pure Python (`py3-none-any`) | Identical RDF/XML & OWL triple parsing, blank-node handling, and SPARQL evaluation. |
| `breame` | `0.1.2` | `0.1.2` | Pure Python (`sdist` -> wheel) | Exact parity for British-to-American spelling normalization (`DISC-02`). |
| `pandas` | `2.0.3` | `3.1.1` | Native Python 3.13 Wheel | CPython 3.13 C-API support; DataFrame sorting and CSV serialization verified identical. |
| `numpy` | `1.26.4` | `2.5.5` | Native Python 3.13 Wheel | Pre-built binary wheel; cosine distance and vector operations verified. |
| `psycopg2-binary` | `2.9.9` | `2.9.13` | Native Python 3.13 Wheel | libpq binary bindings for synchronous PostgreSQL 16 + `pgvector` operations. |
| `asyncpg` | `0.28.0` | `0.32.0` | Native Python 3.13 Wheel | Updated Cython build compatible with Python 3.13 C-API. |
| `pgvector` | `0.1.8` | `0.5.1` | Pure Python (`py3-none-any`) | Full support for `vector(N)` (`768`, `1024`, `4096`) and `<=>` cosine distance. |
| `ollama` | `0.6.3` | `0.6.3` | Pure Python (`py3-none-any`) | Official Ollama HTTP client supporting `/api/tags`, `/api/show`, `/api/chat`, `/api/embed`. |
| `langchain-core` | `0.3.86` | `1.8.4` | Pure Python (`py3-none-any`) | Provides `BaseChatModel`, `Embeddings`, and prompt message abstractions without bloat. |
| `langchain-ollama` | `0.2.3` | `1.1.0` | Pure Python (`py3-none-any`) | Local-only `ChatOllama` and `OllamaEmbeddings` adapters. |
| `langchain-text-splitters` | `0.3.x` | `1.1.3` | Pure Python (`py3-none-any`) | `RecursiveCharacterTextSplitter` with `chunk_size=500, chunk_overlap=0`. |
| `python-dotenv` | `1.0.0` | `1.2.4` | Pure Python (`py3-none-any`) | Deterministic `.env` loading via `dotenv_values`. |
| `PyYAML` | `6.0.1` | `6.0.3` | Native Python 3.13 Wheel | LibYAML C-extension wheel for Python 3.13. |
| `PySide6` | `6.12.0` | `6.12.0` | Universal2 / x64 `abi3` Wheel | Qt6 bindings using stable CPython `cp310-abi3` ABI; works natively on Python 3.13. |
| `matplotlib` | `3.11.2` | `3.11.2` | Native Python 3.13 Wheel | Headless `Agg` and Qt6Agg backends for publication-grade charts. |
| `pytest` | `8.x` | `9.2.0` | Pure Python (`py3-none-any`) | Test discovery and fixture runner. |
| `pytest-qt` | — | `4.5.0` | Pure Python (`py3-none-any`) | Qt6 signal/slot and widget testing plugin for `PySide6`. |
| `pyinstaller` | `6.22.3` | `6.22.3` | Native Python 3.13 Wheel | Supports Python 3.13 bytecode freezing (`--onedir`). |

---

## 3. Zero-PyTorch & Minimal LangChain Footprint

1. **No PyTorch (`torch`) Required:** All LLM inference and embedding calculations execute inside the local Ollama server (`http://127.0.0.1:11434`) or via `LlamaEmbeddingBridge` (`src/utils/llama_embed_bridge.py`). Avoiding PyTorch saves $>2.5\text{ GB}$ of virtual environment footprint and eliminates DLL/dylib packaging issues in PyInstaller.
2. **Minimal LangChain Surface:** Only `langchain-core`, `langchain-ollama`, and `langchain-text-splitters` are installed. Legacy monolithic `langchain` and `langchain-community` packages are excluded.
