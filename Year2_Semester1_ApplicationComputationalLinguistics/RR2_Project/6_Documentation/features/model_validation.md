# Feature Documentation — Model Parameter Validation & ≤4B Compliance Guard (`src/llm/model_validator.py`)

## 1. Feature Purpose
A core scientific requirement of this replication project is evaluating Agent-OM under a strict **≤4 billion ($4,000,000,000$) total parameter ceiling** for small-model compliance. Because model release tags can be misleading (for example, `qwen3.5:4b` is tagged `"4b"` but actually contains **$4,538,986,496$ ($4.54\text{B}$) parameters** in its GGUF metadata), the Model Validation subsystem inspects exact GGUF tensor parameter counts via the local Ollama `/api/show` endpoint and blocks non-compliant models whenever `STRICT_4B_CAP=True`.

---

## 2. Input Data
- **Model Tag (`str`):** Local Ollama model identifier (e.g., `"qwen2.5:3b"`, `"deepseek-r1:1.5b"`, `"qwen3.5:4b"`, `"nomic-embed-text:latest"`, `"mxbai-embed-large:latest"`).
- **Strict Cap Flag (`bool`):** `STRICT_4B_CAP` configuration flag (`True` for all `local_4b_*` profiles; `False` only for explicit non-compliant comparison profiles such as `local_qwen35_comparison`).
- **Parameter Limit (`int`):** `MAX_MODEL_PARAMETERS = 4_000_000_000`.

---

## 3. Processing Steps
1. **Live Metadata Query (`inspect_ollama_model()`):**
   - Queries `POST http://127.0.0.1:11434/api/show` with `{"name": model_tag}`.
2. **Exact Parameter Extraction:**
   - Extracts `model_info["general.parameter_count"]` (exact integer parameter count from the GGUF header) alongside architecture, quantization level (`Q4_K_M`, `F16`, etc.), context length, and embedding dimensionality.
   - Falls back to the verified static registry (`VERIFIED_MODEL_REGISTRY`) only during offline unit tests when queried in mock mode.
3. **Compliance Classification:**
   - Compares `parameter_count <= 4_000_000_000`.
   - Classifies the model into one of three categories:
     - `COMPLIANT_4B_CHAT` (e.g., `qwen2.5:3b` at $3,085,938,688$ params; `deepseek-r1:1.5b` at $1,777,088,000$ params)
     - `COMPLIANT_4B_EMBEDDING` (e.g., `nomic-embed-text:latest` at $136,731,648$ params; `mxbai-embed-large:latest` at $334,090,240$ params)
     - `NON_COMPLIANT_COMPARISON` (e.g., `qwen3.5:4b` at $4,538,986,496$ params — exceeds cap by $+538,986,496$ params; `gemma4:12b` at $12,378,022,416$ params; `llama3:8b` at $8,030,261,248$ params).
4. **Runtime Enforcement (`assert_model_compliance()`):**
   - If `STRICT_4B_CAP=True` and either `CHAT_LLM` or `EMBEDDING_MODEL` has `parameter_count > 4_000_000_000`, raises `ModelComplianceError` immediately before pipeline execution can start.

---

## 4. Output Data
- **`ModelValidationReport` (`dataclass` / JSON):**
  - `model_name`: Model tag
  - `parameter_count`: Exact integer parameter count
  - `is_compliant_4b`: Boolean (`parameter_count <= 4_000_000_000`)
  - `quantization_level`: e.g., `"Q4_K_M"`, `"F16"`
  - `architecture`: e.g., `"qwen2"`, `"nomic-bert"`, `"bert"`, `"qwen35"`
  - `embedding_length`: Integer vector dimension
  - `classification`: Compliance tier label
- **Persisted Inventory Artifact:** [`5_Results/manifests/model_inventory.json`](../../5_Results/manifests/model_inventory.json).

---

## 5. Main Implementation Files
- [`1_Source/llm/model_validator.py`](../../1_Source/llm/model_validator.py) — GGUF metadata inspector, `ModelComplianceError`, `validate_model_parameters()`, and `assert_profile_compliance()`.
- [`1_Source/config.py`](../../1_Source/config.py) — Defines `MAX_MODEL_PARAMETERS = 4_000_000_000`, `STRICT_4B_CAP`, and per-profile compliance flags.

---

## 6. Configuration Options
- `MAX_MODEL_PARAMETERS`: `4_000_000_000` (hard ceiling for ≤4B compliance).
- `STRICT_4B_CAP`: `True` (enforces pre-flight parameter validation) or `False` (allows non-compliant comparison baselines with explicit warning banners).

---

## 7. Dependencies
- Local Ollama HTTP API (`http://127.0.0.1:11434/api/show`).
- Python standard library (` dataclasses`, `json`, `urllib.request`) + `httpx`.

---

## 8. Relevant Tests
- [`2_Tests/unit/test_model_Policy.py`](../../2_Tests/unit/test_model_Policy.py) — Verifies that `qwen2.5:3b` ($3.09\text{B}$), `deepseek-r1:1.5b` ($1.78\text{B}$), `nomic-embed-text:latest` ($137\text{M}$), and `mxbai-embed-large:latest` ($334\text{M}$) pass strict ≤4B validation, and that `qwen3.5:4b` ($4.54\text{B}$), `llama3:8b` ($8.03\text{B}$), and `gemma4:12b` ($12.38\text{B}$) raise `ModelComplianceError` when `STRICT_4B_CAP=True`.

---

## 9. Known Limitations
- Relies on the `general.parameter_count` field reported by Ollama's GGUF parser (`/api/show`). If a custom GGUF file lacks `general.parameter_count`, the validator rejects it under `STRICT_4B_CAP=True` rather than guessing from the model tag.
