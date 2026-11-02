# Phase 4 Report — Algorithmic Parity Fixes (`4.1`–`4.11`)

**Date:** 2026-11-02  
**Status:** `COMPLETED`  
**Verification Suite:** `pytest tests/` — **118 passed, 0 failed (`14.33s`)**

---

## 1. Objective

Phase 4 resolved every source-level discrepancy identified in the Phase 0 Audit (`docs/phase0_audit_report.md`) and Phase 2 Parity Matrix (`docs/replication_parity_matrix.md`) between upstream Agent-OM (`original_repo/` — strictly read-only) and the independent local implementation (`agent_om_local/`), while preserving all historical Step 4–7D.1 results and protecting the `agent_om_local` PostgreSQL database.

---

## 2. Implemented Fixes (`4.1`–`4.11`)

### 4.1 Empty Semantic Feature Handling (`src/db/database_manager.py`)
- **Defect (`DISC-01`):** Previously, `DatabaseManager.create_embedding_table()` replaced empty strings with `config.null_value_sentence` (`"Information is not available."`), generating identical vector rows for structurally isolated entities and causing false `1.0000` cosine similarity matches.
- **Fix:** Added `skip_empty_chunks: bool = True` (default) and `null_value_sentence` stripping (`matching_text.replace(null_value_sentence, "")`), reproducing `om_csv_to_database.py:40-41, 89`. Entities without structural axioms now produce **0 chunks** in `semantic_matching` and return `["Entity-Dummy"]` on query. Guarded empty batch `execute_values` when a table has `0` total chunks.

### 4.2 `MatchingAgent` Code-IRI Label Resolution (`src/agents/matching_agent.py`, `src/ontology/parser.py`)
- **Defect (`DISC-02`):** `MatchingAgent` previously derived candidate and query names exclusively via `uri_to_name()`, ignoring `o1_is_code` / `o2_is_code` on coded ontologies (e.g., Anatomy/Biodiv/Phenotype tracks).
- **Fix:** Added `source_ontology`, `target_ontology`, `o1_is_code`, and `o2_is_code` to `MatchingAgent`, implementing symmetric `resolve_entity_display_name(uri, side)` (`rdfs:label` priority -> `skos:prefLabel` -> `uri_to_name` fallback) in both `Source->Target` and `Target->Source` directions for both exact-name bypass and LLM validation prompts. Also updated `RetrievalAgent.build_features_dataframe()` to format `entity_id` suffixes with resolved labels when `o1_is_code` / `o2_is_code` is enabled.

### 4.3 Combined Alphabetical Property Ordering & Punning Preservation (`src/ontology/entity_extractor.py`)
- **Defect (`DISC-03`):** `EntityExtractor` previously emitted all `ObjectProperty` entities before `DatatypeProperty` entities, shifting 3-digit `entity_id` prefixes relative to `om_ontology_to_csv.py:286` (`sorted(properties)`) and altering lexicographic RRF tie-breaking.
- **Fix:** Added `combine_properties_sort: bool = True` (default), sorting `(uri, property_kind)` pairs by `(str(uri), kind_rank)` so `ObjectProperty` and `DatatypeProperty` follow upstream's single alphabetical URI sequence while still preserving punned properties declared as both `ObjectProperty` and `DatatypeProperty`. Deterministic sorting was also added to `extract_entity_label()`.

### 4.4 Embedding Dimension Registry & Runtime Validation (`src/config.py`, `src/db/database_manager.py`, `src/utils/llama_embed_bridge.py`)
- **Defect (`DISC-04`):** `AppConfig.vector_length` lacked `"llama3:8b": 4096` and silently defaulted unknown models to `768`.
- **Fix:** Registered `"llama3:8b": 4096` and `"llama3:latest": 4096`, removed the silent `768` fallback (raising `ValueError` unless `embedding_dim` is explicitly supplied), added `LlamaBridgeEmbeddings` (releasing GPU VRAM automatically after ingestion), and enforced runtime `len(vec) == v_len` checks on every batch in `DatabaseManager.create_embedding_table()`.

### 4.5 Explicit LLM Sampling & Reasoning Parameters (`src/config.py`, `src/retrieval/lexical_retriever.py`, `src/retrieval/semantic_retriever.py`, `src/matching/validator.py`)
- **Defect (`DISC-06`, `DISC-07`):** `seed`, `top_k`, `top_p`, and `repeat_penalty` were not passed to `ChatOllama`, and `reasoning=False` was set on `MatchingValidator` (`validator.py:67`) but missing on `LexicalRetriever` and `SemanticRetriever`.
- **Fix:** Centralized `AppConfig.build_chat_llm()` passing `temperature`, `seed`, `top_k`, `top_p`, `repeat_penalty`, `num_ctx`, and `reasoning` consistently across all retrieval and validation LLMs, verified against `langchain-ollama` and Ollama `0.40.13`.

### 4.6 Prompt Formatting & Deterministic Set Ordering (`src/matching/validator.py`, `src/retrieval/lexical_retriever.py`, `src/retrieval/semantic_retriever.py`)
- **Fix:** Added `MatchingValidator.UPSTREAM_PROMPT_TEMPLATE` reproducing upstream's exact 28-space indentation (`indent_prompt=True` in `upstream_lite_parity`; `False` in `local_adapted`), `predicate_scope` (`"head"` 10-lexical / 18-semantic + sorted blank-node closure vs `"pvl_v1"` 2-lexical / 7-semantic), `concat_separator` (`""` vs `"\n"`), and `strip_response` (`False` vs `True`).

### 4.7 Environment & Configuration Harmonization (`src/config.py`, `.env.example`)
- **Defect (`DISC-05`):** `.env.example` used `DB_*` / `DEFAULT_*` keys while `AppConfig` read `PG*` / `AGENT_OM_*` without invoking `python-dotenv`.
- **Fix:** Implemented `load_env_values()` via `dotenv.dotenv_values`, harmonized `DB_*` / `PG*` and `DEFAULT_*` / `AGENT_OM_*` keys, and enforced loopback-only validation (`127.0.0.1` / `localhost`) on both `db_host` and `ollama_host`.

### 4.8 Test Suite Isolation & Stale Path Removal (`tests/test_*.py`, `src/db/database_manager.py`)
- **Defect (`DISC-08`, `DISC-09`):** Three test files hardcoded `E:\_3_Master\_9_ACL_Project\...` and `tests/test_retrieval_agent.py` executed `DROP TABLE` against `agent_om_local`.
- **Fix:** Replaced stale paths with workspace-relative resolution (`Path(__file__).resolve().parents[2] / "original_repo" / ...`), isolated `tests/test_retrieval_agent.py` to `postgresql://postgres@127.0.0.1:5432/agent_om_test`, and added a runtime write-protection guard in `DatabaseManager` blocking `DROP TABLE` on `agent_om_local` unless `allow_protected_db_write=True`.

### 4.9 Optional LLM JSON Tool-Routing Parity Mode (`src/agents/tool_router.py`, `src/agents/retrieval_agent.py`, `src/agents/matching_agent.py`)
- **Fix:** Implemented `LLMJsonToolRouter` reproducing upstream's `ChatPromptTemplate | llm | JsonOutputParser()` tool routing (`tool_routing_mode="llm_json"` alongside default `"deterministic"`), recording router call count, latency, token usage, and schema errors.

### 4.10 Explicit Configuration Profiles (`src/config.py`)
- **Fix:** Implemented `AppConfig.from_profile()` for all four required profiles:
  1. `upstream_product_reference` (`gpt-4o-2024-05-13` + `text-embedding-ada-002` `1536`-dim, `reference_only=True`, raises `PermissionError` if execution is attempted)
  2. `upstream_lite_parity` (`llama3:8b` + `llama3:8b` `4096`-dim, `temp=0.0, seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0`, `db_name="agent_om_parity"`)
  3. `local_adapted` (`qwen3.5:9b` `reasoning=False` + `nomic-embed-text` `768`-dim, `db_name="agent_om_adapted"`)
  4. `experimental` (customizable thresholds, `rrf_k`, `predicate_scope`, and `tool_routing_mode`, `db_name="agent_om_experimental"`).

### 4.11 Full Regression & Mini-Ontology Verification (`tests/test_algorithmic_parity.py`)
- Added `tests/test_algorithmic_parity.py` covering every defect fix (`4.1`–`4.10`) plus an end-to-end mini-ontology retrieval + pgvector + validation + reciprocal merger comparison between `"deterministic"` and `"llm_json"` modes.
- Executed full test suite: **118 passed, 0 failed (`14.33s`)**.
- Verified protected `agent_om_local` database row counts remain unchanged: `ontology_matching=162`, `syntactic_matching=162`, `lexical_matching=206`, `semantic_matching=258`.

