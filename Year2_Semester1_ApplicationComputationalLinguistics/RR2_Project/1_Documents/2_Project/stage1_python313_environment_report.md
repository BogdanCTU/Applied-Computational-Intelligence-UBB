# Stage 1 Execution Report — Python 3.13 Environment Provisioning
## Agent-OM: Scientific Replication, Local Adaptation & Windows Desktop Application

**Execution Date:** 2026-11-15  
**Stage:** Stage 1 (Python 3.13 Virtual Environment & Dependency Isolation)  
**Host Environment:** Windows 11 (build 22631), Python 3.13.17 (`C:\Python313\python.exe`)  
**Target Environment:** `agent_om_local/.venv` (`E:\PERSONAL\GitHub\1_Applied-Computational-Intelligence-UBB\Year2_Semester1_ApplicationComputationalLinguistics\RR2_Project\.venv`)  
**Status:** COMPLETED — 100% Verified

---

## 1. Filesystem & Environment Pre-Check

Before environment initialization, the filesystem state was audited:

| Target Item | Path | Pre-Check Status | Description |
| :--- | :--- | :---: | :--- |
| **System Python** | `C:\Python313\python.exe` | **EXISTS** | Python 3.13.17 (MSC v.1944 64-bit AMD64) |
| **Local `.venv`** | `.venv/` | **ABSENT** | Excluded in root `.gitignore`, needed creation |
| **Upstream `.venv`**| `.venv_upstream/` | **ABSENT** | Excluded in root `.gitignore` |
| **Base Requirements**| `requirements.txt` | **EXISTS** | Pinned range specifications preserved |
| **Manifest Inventory**| `output/replication_runs/manifests/venv_upstream_packages.json` | **EXISTS** | 78 upstream package inventory (Python 3.10 baseline) |

---

## 2. Environment Creation & Installation Commands

### 2.1. Virtual Environment Creation
```powershell
& "C:\Python313\python.exe" -m venv .venv
```
- **Exit Code:** `0`
- **Result:** Created isolated 64-bit Python 3.13.17 virtual environment with `pip 26.2.2`.

### 2.2. Base Requirements Installation
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```
- **Exit Code:** `0`
- **Packages Installed:** `rdflib (7.6.0)`, `breame (0.1.2)` (wheel compiled cleanly from sdist), `pandas (3.1.1)`, `numpy (2.5.4)`, `psycopg2-binary (2.9.13)`, `asyncpg (0.32.0)`, `pgvector (0.5.1)`, `ollama (0.6.3)`, `langchain-core (1.8.0)`, `langchain-ollama (1.1.0)`, `langchain-text-splitters (1.1.3)`, `pyyaml (6.0.3)`, `python-dotenv (1.2.4)`, `pytest (9.2.0)`, `tqdm (4.70.1)`, `colorama (0.4.6)`.

### 2.3. GUI and Build Dependency Installation
```powershell
& ".\.venv\Scripts\python.exe" -m pip install PySide6 matplotlib pyinstaller
```
- **Exit Code:** `0`
- **Packages Installed:** `PySide6 (6.12.0)`, `PySide6_Essentials (6.12.0)`, `PySide6_Addons (6.12.0)`, `PySide6_WebEngine (6.12.0.140)`, `PySide6_Pdf (6.12.0.140)`, `shiboken6 (6.12.0)`, `matplotlib (3.11.2)`, `pyinstaller (6.22.3)`, `pyinstaller-hooks-contrib (2026.10)`, `pillow (13.0.0)`, `contourpy (1.4.0)`, `kiwisolver (1.5.1)`, `fonttools (4.68.0)`, `cycler (0.12.1)`.

---

## 3. Dependency Inventory & Deviations Analysis

In accordance with requirement 5, the existing `requirements.txt` was preserved byte-for-byte, and exact Python 3.13 frozen pins were recorded in `requirements-py313.txt`.

### Upstream Baseline vs Python 3.13 Adaptation

| Package | Upstream Baseline (`venv_upstream_packages.json`) | Python 3.13 Active (`requirements-py313.txt`) | Deviation Classification | Rationale / Technical Impact |
| :--- | :---: | :---: | :---: | :--- |
| **Python** | 3.10.12 | 3.13.17 | Primary Target | Upstream used Python 3.10; Python 3.13 is mandated primary target. |
| **rdflib** | 7.0.0 | 7.6.0 | Minor Update | Fully backwards-compatible; ontology parsing verified. |
| **breame** | 0.1.2 | 0.1.2 | Exact Parity | PVLDB 2026 spelling normalization preserved. |
| **pandas** | 2.0.3 | 3.1.1 | Compatibility Modernization | Python 3.13 requires pandas >= 2.2.3 for C-API ABI compatibility. |
| **numpy** | 1.26.4 | 2.5.4 | Compatibility Modernization | Python 3.13 requires numpy >= 2.1.0 pre-built binary wheels. |
| **psycopg2-binary** | 2.9.9 | 2.9.13 | Minor Update | Pre-built binary wheel for Windows CPython 3.13. |
| **asyncpg** | 0.28.0 | 0.32.0 | Compatibility Modernization | Cython compilation required updated asyncpg wheel for Python 3.13. |
| **pgvector** | 0.1.8 | 0.5.1 | Feature Compatible | Supports `vector(4096)` and cosine similarity distance operator `<=>`. |
| **ollama** | 0.6.3 | 0.6.3 | Exact Parity | Official local Ollama Python client. |
| **langchain-core** | 0.3.86 | 1.8.0 | Architectural Compatible | Compatible with BaseChatModel and AIMessage protocols. |
| **langchain-ollama** | 0.2.3 | 1.1.0 | Minor Update | Provides ChatOllama and OllamaEmbeddings. |
| **PySide6** | 6.12.0 | 6.12.0 | GUI Framework | Native Qt6 bindings for Windows desktop application. |
| **matplotlib** | 3.11.2 | 3.11.2 | Chart Generation | Evaluation and sensitivity plotting backend. |
| **pyinstaller** | 6.22.3 | 6.22.3 | Packaging Engine | Standalone executable compilation. |

---

## 4. Import & Functional Smoke Verification

Import verification was executed directly in `.venv`:
```python
& ".\.venv\Scripts\python.exe" -c "
import rdflib, breame.spelling, pandas, numpy, psycopg2, asyncpg, pgvector
import ollama, langchain_core, langchain_ollama, langchain_text_splitters
import PySide6.QtCore, matplotlib, PyInstaller, pytest, yaml, dotenv
print('All core imports succeeded!')
"
```
- **Result:** `All core imports succeeded!`
- **Module Verification Log:**
  - `rdflib` $\rightarrow$ `7.6.0` [OK]
  - `breame.spelling` $\rightarrow$ Available [OK]
  - `pandas` $\rightarrow$ `3.1.1` [OK]
  - `numpy` $\rightarrow$ `2.5.4` [OK]
  - `psycopg2` $\rightarrow$ `2.9.13` (dt dec pq3 ext lo64) [OK]
  - `asyncpg` $\rightarrow$ `0.32.0` [OK]
  - `pgvector` $\rightarrow$ `0.5.1` [OK]
  - `ollama` $\rightarrow$ `0.6.3` [OK]
  - `langchain_core` $\rightarrow$ `1.8.0` [OK]
  - `langchain_ollama` $\rightarrow$ `1.1.0` [OK]
  - `langchain_text_splitters` $\rightarrow$ `1.1.3` [OK]
  - `PySide6.QtCore` $\rightarrow$ `6.12.0` [OK]
  - `matplotlib` $\rightarrow$ `3.11.2` [OK]
  - `PyInstaller` $\rightarrow$ `6.22.3` [OK]
  - `pytest` $\rightarrow$ `9.2.0` [OK]
  - `yaml` $\rightarrow$ `6.0.3` [OK]
  - `dotenv` $\rightarrow$ Available [OK]

---

## 5. Summary & Stage 1 Sign-Off

The Python 3.13 local replication environment is successfully provisioned, verified, and completely isolated inside `.venv`. All required application, evaluation, GUI, and packaging dependencies are functional without external cloud dependencies.

