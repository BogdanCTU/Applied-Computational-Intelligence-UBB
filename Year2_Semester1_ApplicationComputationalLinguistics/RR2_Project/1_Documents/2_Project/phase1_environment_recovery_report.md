# Phase 1 Execution Report — Python 3.13 Environment Recovery
## Agent-OM: Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Execution Date:** 2026-11-20T11:05:34+02:00  
**Phase:** Phase 1 (Python 3.13 Environment Recovery & Historical Integrity Verification)  
**Host Environment:** macOS 27.0.1 (`Darwin 27.0.0 arm64`, Apple M4, 16 GB Unified Memory)  
**Interpreter:** `.venv/bin/python` (`Python 3.13.16`, 64-bit Mach-O)  
**Status:** **COMPLETED — 100% Verified (`AC-01`, `AC-02`, `AC-19` SATISFIED)**

---

## 1. Dependencies Installed & Verified (`AC-01`, `AC-02`)

The missing GUI, plotting, testing, and packaging dependencies were installed into `.venv/`:
```bash
.venv/bin/pip install PySide6 matplotlib pytest-qt pyinstaller
```

### Individual Import Verification
All 17 required packages were imported and verified under Python 3.13.16:
- `rdflib==7.6.0`
- `breame==0.1.2`
- `pandas==3.1.1`
- `numpy==2.5.5`
- `psycopg2-binary==2.9.13`
- `asyncpg==0.32.0`
- `pgvector==0.5.1`
- `ollama==0.6.3`
- `langchain-core==1.8.4`
- `langchain-ollama==1.1.0`
- `langchain-text-splitters==1.1.3`
- `python-dotenv==1.2.4`
- `PyYAML==6.0.3`
- `PySide6==6.12.0`
- `matplotlib==3.11.2`
- `pytest==9.2.0`
- `pytest-qt==4.5.0`
- `pyinstaller==6.22.3`

**Verification Result:** `ALL_17_IMPORTS_OK` (Exit Code `0`, `72` total locked packages written to `requirements-lock.txt`).

---

## 2. Historical Output SHA-256 Integrity Restoration (`AC-19`)

Without altering a single character of content, line endings on the 30 historical files in `output/` (`e1_predictions.csv` .. `step7d1_validation_decisions.csv`) were restored from `LF` to their original baseline `CRLF` representation and verified via `scripts/verify_repo_integrity.py`:

```json
{
  "checked_at_utc": "2026-11-20T09:04:47.680096+00:00",
  "identical": true,
  "baseline_aggregate_sha256": "eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798",
  "current_aggregate_sha256": "eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798",
  "baseline_file_count": 30,
  "current_file_count": 30,
  "added_directories": [],
  "removed_directories": [],
  "added_files": [],
  "removed_files": [],
  "modified_files": []
}
```

---

## 3. Documentation Path Resolution Repair

Updated `src/gui/paths.py` (`resolve_project_paths()`) so `docs_dir` falls back cleanly to `project_root / "1_Documents" / "2_Project"` when `project_root / "docs"` is absent, and `.venv_upstream` checks both `Scripts/python.exe` and `bin/python`.

---

## 4. Phase 1 Deliverables Created / Updated

1. `requirements-dev.txt` (Created)
2. `requirements-lock.txt` (Created — 72 locked Python 3.13.16 distributions)
3. `1_Documents/2_Project/PYTHON_313_COMPATIBILITY.md` (Created)
4. `1_Documents/2_Project/phase1_environment_recovery_report.md` (Created)
5. `src/gui/paths.py` (Updated with `1_Documents/2_Project` fallback)
