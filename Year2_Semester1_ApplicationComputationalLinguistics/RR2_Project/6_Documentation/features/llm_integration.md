# Feature Documentation — Separated Local LLM Integration (`src/llm/`)

## 1. Feature Purpose
The separated local LLM integration subsystem decouples **generative chat/reasoning models** from **dense vector embedding models** while enforcing a strict **100% local loopback boundary** (`http://127.0.0.1:11434`). This separation allows Agent-OM to pair any local ≤4B chat model (`qwen2.5:3b` at $3.09\text{B}$ parameters or `deepseek-r1:1.5b` at $1.78\text{B}$ parameters) with dedicated dense embedding encoders (`nomic-embed-text:latest` at $768$-dim or `mxbai-embed-large:latest` at $1024$-dim) without invoking cloud APIs or coupling both tasks to a single monolithic model.

---

## 2. Input Data
- **Chat Generation Inputs:**
  - `prompt` (`str`): Natural-language prompt (either an entity metadata description prompt for semantic enrichment or a structured Yes/No binary verification prompt).
  - `system_prompt` (`Optional[str]`): System role instruction.
  - `temperature` (`float`, default `0.0`): Deterministic greedy decoding temperature.
- **Embedding Generation Inputs:**
  - `text` (`str`): Natural-language entity label or enriched semantic description to encode into a dense floating-point vector.

---

## 3. Processing Steps
1. **Profile Selection (`1_Source/config.py`):**
   - Resolves the active profile (`local_4b_default`, `local_4b_baseline`, `local_4b_mxbai`, `local_4b_reasoner`, `local_qwen35_comparison`, `historical_8b`, or `historical_12b`) and sets `LLM`, `CHAT_LLM`, `EMBEDDING_MODEL`, and `EMBEDDING_DIM`.
2. **Loopback Security Check (`1_Source/llm/ollama_provider.py`):**
   - Verifies that `OLLAMA_HOST` resolves strictly to `127.0.0.1` or `localhost` (`assert_loopback_url()`). Any non-loopback hostname raises a `ValueError` before any socket connection is opened.
3. **Chat Completion (`OllamaChatProvider.generate()`):**
   - Sends a POST request to `http://127.0.0.1:11434/api/chat` (or invokes `ollama.chat()`) with `temperature=0.0` and `seed=42`.
   - For reasoning models that emit `<think>...</think>` blocks (such as `deepseek-r1:1.5b` or `qwen3.5:4b`), strips thinking traces before passing the final response to the binary `Yes/No` parser.
4. **Vector Embedding (`OllamaEmbeddingProvider.embed()`):**
   - Sends an embedding request to `http://127.0.0.1:11434/api/embeddings` using `EMBEDDING_MODEL`.
   - Validates that the returned vector matches the configured `EMBEDDING_DIM` ($768$ for `nomic-embed-text:latest`, $1024$ for `mxbai-embed-large:latest`, or $4096$ for `llama3:8b`) and normalizes or pads/truncates when storing in a fixed-dimension `pgvector` schema.
5. **Telemetry Recording:**
   - Records prompt tokens, completion tokens, wall-clock latency (`ms`), and call counts per pipeline stage.

---

## 4. Output Data
- **Chat Response (`ChatResult` / `str`):** Raw text response plus token and latency metadata.
- **Embedding Vector (`List[float]`):** Dense floating-point vector of length `EMBEDDING_DIM`.
- **Stage Telemetry (`dict`):** Aggregated call counts, prompt/completion token totals, and stage timings saved in `manifest.json`.

---

## 5. Main Implementation Files
- [`1_Source/llm/base.py`](../../1_Source/llm/base.py) — Abstract base interfaces (`BaseChatProvider`, `BaseEmbeddingProvider`) and response dataclasses.
- [`1_Source/llm/ollama_provider.py`](../../1_Source/llm/ollama_provider.py) — Concrete Ollama loopback chat and embedding providers, loopback URL enforcement, and retry/timeout handling.
- [`1_Source/llm/prompt_templates.py`](../../1_Source/llm/prompt_templates.py) — Upstream and compact ≤4B prompt templates plus reasoning-trace stripping and binary Yes/No parsing.
- [`1_Source/utils/llm.py`](../../1_Source/utils/llm.py) — Unified facade bridging legacy `get_llm_response()` and `get_embedding()` calls to the separated provider classes.

---

## 6. Configuration Options
Configured in [`1_Source/config.py`](../../1_Source/config.py):
- `OLLAMA_BASE_URL`: `"http://127.0.0.1:11434"` (loopback enforced).
- `CHAT_LLM`: Active generative model tag (e.g., `"qwen2.5:3b"`).
- `EMBEDDING_MODEL`: Active embedding model tag (e.g., `"nomic-embed-text:latest"`).
- `EMBEDDING_DIM`: Vector dimensionality (`768`, `1024`, or `4096`).
- `PROMPT_MODE`: `"upstream"` (verbose reference prompt) or `"compact_4b"` (structured compact prompt for ≤4B models).
- `LLM_TEMPERATURE`: `0.0` (deterministic inference).

---

## 7. Dependencies
- `ollama` Python client (`0.4.7`) and `httpx` (`0.28.1`).
- Local Ollama daemon (`0.40.16`) listening on `127.0.0.1:11434`.

---

## 8. Relevant Tests
- [`2_Tests/integration/test_llm_providers.py`](../../2_Tests/integration/test_llm_providers.py) — Tests separated chat and embedding providers, compact prompt parsing, reasoning-tag stripping, and loopback URL enforcement.
- [`2_Tests/unit/test_model_Policy.py`](../../2_Tests/unit/test_model_Policy.py) — Verifies profile definitions and chat/embedding model pairings.

---

## 9. Known Limitations
- Small reasoning models (`deepseek-r1:1.5b`) generate extended `<think>` blocks that increase per-pair latency (~$4.2\times$ slower than `qwen2.5:3b`) without outperforming `qwen2.5:3b` on zero-shot ontology matching.
- Requires the local Ollama service to be running on `127.0.0.1:11434` for live inference.
