# Development Guide — Extending and Testing Agent-OM

## 1. Source Code Organization (`1_Source/`)

All application code resides in `1_Source/` (with `src/` acting as a transparent Python package bridge so both `from src...` and `1_Source/` lookups resolve identically):

- `1_Source/config.py`: `AppConfig` dataclass, 7 execution profiles, loopback URL/host validators, and environment variable loaders.
- `1_Source/core/` & `1_Source/ontology/`: `OntologyGraph` (`parser.py`) and `EntityExtractor` (`entity_extractor.py`).
- `1_Source/retrieval/`: `SyntacticRetriever`, `LexicalRetriever`, `SemanticRetriever`, and `reciprocal_rank_fusion`.
- `1_Source/matching/`: `MatchingValidator` and `ReciprocalMerger`.
- `1_Source/agents/`: `RetrievalAgent`, `MatchingAgent`, and `LLMJsonToolRouter`.
- `1_Source/llm/`: `OllamaClient`, `ModelRegistry`, `ModelValidator`, `LocalChatProvider`, and `LocalEmbeddingProvider`.
- `1_Source/database/` & `1_Source/db/`: `DatabaseManager` with `agent_om_local` write-protection guard.
- `1_Source/evaluation/`: `metrics.py`, `comparator.py` (17-point comparator), and `charts.py` (5 Matplotlib figure builders).
- `1_Source/gui/` & `1_Source/services/`: 10 PySide6 views and 11 backend services.

---

## 2. Executing the Automated Test Suite (`2_Tests/`)

The test suite is partitioned into three categories under `2_Tests/`:

```bash
# Run all 133 tests (unit + integration + GUI):
.venv/bin/python -m pytest 2_Tests/ -v

# 1. Unit Tests (98 tests in 14 files — no PostgreSQL or Ollama required):
.venv/bin/python -m pytest 2_Tests/unit/ -v

# 2. Integration Tests (28 tests in 3 files — requires local PostgreSQL 16 + pgvector & Ollama):
.venv/bin/python -m pytest 2_Tests/integration/ -v

# 3. GUI Tests (7 tests in 1 file — verifies all 11 services and 10 PySide6 views offscreen):
.venv/bin/python -m pytest 2_Tests/gui/ -v
```

---

## 3. Adding a New Local LLM or Embedding Model

1. **Pull the model in local Ollama:**
   ```bash
   ollama pull <model_tag>
   ```
2. **Inspect its true parameter count and capabilities via `ModelRegistry`:**
   ```bash
   .venv/bin/python -c "from src.llm import ModelRegistry; print(ModelRegistry().inspect_model('<model_tag>').to_dict())"
   ```
3. **If it is a dedicated embedding model:** Register its canonical dimension in `DEFAULT_EMBEDDING_DIMENSIONS` (`1_Source/config.py`) and `DEDICATED_EMBEDDING_MODELS` (`1_Source/llm/model_registry.py`).
4. **If it is a $\le 4.0\text{B}$ chat model:** Verify that `total_parameter_count <= 4_000_000_000`. Pass `--llm-model <model_tag>` to `scripts/run_local_replication.py` or select it in Screen 4 (`ConfigurationView`) of the desktop GUI.

---

## 4. Verifying Historical Integrity

Before and after running any new experiment, verify that the 30 historical Step 4–7D.1 output files remain untouched:

```bash
.venv/bin/python scripts/verify_repo_integrity.py verify \
  --root output \
  --baseline output/replication_runs/manifests/historical_output_baseline_sha256.json
```
Expected result: `"identical": true` (`aggregate_sha256 = eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`).
