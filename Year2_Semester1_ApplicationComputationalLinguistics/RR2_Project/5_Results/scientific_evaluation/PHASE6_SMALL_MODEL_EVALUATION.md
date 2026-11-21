# Phase 6 Report — Scientific Evaluation of Local $\le 4\text{B}$ LLM Adaptation
## Agent-OM: Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Report Date:** 2026-11-20  
**Status:** `COMPLETED` (`AC-06`, `AC-07`, `AC-08`, `AC-13`, `AC-14`, `AC-15` SATISFIED)  
**Host Platform:** macOS 27.0.1 (`Darwin 27.0.0 arm64`, Apple M4, 16 GB Unified Memory)  
**Benchmark Dataset:** OAEI Conference Track — `CMT–ConfOf` (`162` entities: `88` CMT, `74` ConfOf; `16` Gold Equivalences)  
**Generated Artifacts:**
- `output/replication_runs/manifests/ollama_model_inventory.json`
- `output/replication_runs/comparisons/phase6_small_model_results.csv`
- `output/replication_runs/comparisons/phase6_small_model_results.json`
- `output/replication_runs/phase6_smoke_1ent_qwen25_3b/`
- `output/replication_runs/phase6_integ_4ent_qwen25_3b/`
- `output/replication_runs/phase6_E1_qwen25_3b_baseline_run1`..`run3/`
- `output/replication_runs/phase6_E2_qwen25_3b_optimized_prompt/`
- `output/replication_runs/phase6_E3_qwen25_3b_router_det_4ent/`
- `output/replication_runs/phase6_E4_qwen25_3b_router_llm_4ent/`
- `output/replication_runs/phase6_E5_qwen25_3b_mxbai_1024d/`
- `output/replication_runs/phase6_E6_qwen25_3b_tau085/`
- `output/replication_runs/phase6_E6_qwen25_3b_tau0875/`
- `output/replication_runs/phase6_E7_deepseek_r1_15b_full/`

---

## 1. Strict $\le 4.0\text{B}$ Parameter Verification & Model Selection Methodology

Per Section 6.1 and Section 3 (Model Selection Policy), **parameter count is never inferred from the model tag alone**. Every installed Ollama model was queried live via `POST /api/show` (`ModelRegistry.inspect_model` and `ModelValidator.validate_chat_model`) against the strict ceiling:
$$\text{STRICT\_4B\_MAX\_PARAMETERS} = 4,000,000,000 \text{ total parameters}$$

### 1.1. Runtime Metadata Inventory (`ollama_model_inventory.json`)

| Model Identifier | Role | Architecture / Format | Runner / Quant | Tag Size Label | Authoritative `general.parameter_count` | Strict $\le 4.00\text{B}$ Compliance Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`qwen2.5:3b`** | Chat Generator | `qwen2` (`gguf`) | `ggml` (`Q4_K_M`) | `3.1B` | **`3,085,938,688` (`3.09B`)** | **COMPLIANT ($\le 4.00\text{B}$)** — Principal Phase 6 Model |
| **`deepseek-r1:1.5b`** | Reasoning Chat | `qwen2` (`gguf`) | `ggml` (`Q4_K_M`) | `1.8B` | **`1,777,088,000` (`1.78B`)** | **COMPLIANT ($\le 4.00\text{B}$)** — Reasoning Phase 6 Model |
| **`nomic-embed-text:latest`** | Dedicated Embedding | `nomic-bert` (`gguf`) | `ggml` (`F16`) | `137M` | **`136,727,040` (`0.14B`)** | **COMPLIANT (`768`-dim verified live)** |
| **`mxbai-embed-large:latest`** | Dedicated Embedding | `bert` (`gguf`) | `ggml` (`F16`) | `334M` | **`334,092,288` (`0.33B`)** | **COMPLIANT (`1024`-dim verified live)** |
| `qwen3.5:4b` | Out-of-Limit Ref | `qwen3_5` (`safetensors`) | `mlx` (`nvfp4`) | `4.5B` | `4,538,986,496` (`4.54B`) | **EXCLUDED FROM $\le 4\text{B}$** ($+538,986,496$ over limit) |
| `llama3:8b` (Historical) | 8B Baseline Ref | `llama` (`gguf`) | `ggml` (`Q4_0`) | `8.0B` | `8,030,261,248` (`8.03B`) | **EXCLUDED** (Historical 8B reference baseline) |
| `gemma4:12b` | Out-of-Limit | `gemma4_unified` | `mlx` (`nvfp4`) | `12.4B` | `12,382,568,756` (`12.38B`) | **EXCLUDED** ($>12.38\text{B}$ parameters) |

### 1.2. Empirical Proof of the `:4b` Tag Trap
Querying `POST /api/show` for `qwen3.5:4b` proved that its actual parameter count is **$4,538,986,496$ ($4.54\text{B}$)**. Our `ModelValidator.validate_chat_model("qwen3.5:4b", enforce_4b_limit=True)` raises `ParameterLimitExceededError` at runtime and blocks `qwen3.5:4b` from executing under `local_4b_baseline`, `local_4b_optimized`, or `local_4b_reasoning`.

---

## 2. Dedicated Embedding Model Comparison (`nomic-embed-text` vs. `mxbai-embed-large` vs. `llama3:8b`)

Before executing the matching experiments, all `833` text chunks (`162` syntactic, `367` lexical, `304` semantic) of the 162 CMT–ConfOf entities were embedded into isolated PostgreSQL `pgvector` databases:

| Embedding Model | Parameter Count | Vector Dimension | Isolated Database | Total Chunks Embedded | Ingestion Time (s) | Mean Latency per Chunk (ms) | Unvalidated S2T / T2S Pairs ($\tau=0.90$) | Unvalidated Merged $F_1$ (`3_merged_no_val`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`nomic-embed-text`** | `136.7M` | `vector(768)` | `agent_om_4b_baseline` | `833` (`53` batches) | **`31.88 s`** | **`37.27 ms`** | `30` S2T / `17` T2S | **`41.67%`** (`TP=5, FP=3`) |
| **`mxbai-embed-large`** | `334.1M` | `vector(1024)` | `agent_om_4b_mxbai` | `833` (`53` batches) | **`86.69 s`** | **`101.86 ms`** | `24` S2T / `23` T2S | **`30.77%`** (`TP=4, FP=6`) |
| **`llama3:8b` (Bridge Ref)** | `8,030.3M` | `vector(4096)` | `agent_om_parity` | `833` (`53` batches) | `59.55 s` | `71.49 ms` | `52` S2T / `47` T2S | `38.89%` (`TP=7, FP=13`) |

**Embedding Analysis:**
- `nomic-embed-text` (`768`-dim) is **$2.72\times$ faster** than `mxbai-embed-large` (`1024`-dim) (`37.27 ms` vs `101.86 ms` per chunk) and achieves higher unvalidated reciprocal merger precision ($62.50\%$ vs $40.00\%$) and recall ($31.25\%$ vs $25.00\%$, $F_1 = 41.67\%$ vs $30.77\%$) at $\tau = 0.90$.
- After downstream LLM validation and reciprocal merging (`6_final_with_validation_and_merger`), both `nomic-embed-text` (`E2`) and `mxbai-embed-large` (`E5`) converge to the exact same final alignment ($P=66.67\%, R=25.00\%, F_1=36.36\%$), proving that the LLM validator + reciprocal merger filters out the extra false positives introduced by `mxbai-embed-large`.

---

## 3. Staged Validation & Full 162-Entity Experimental Results (`E1`–`E7`)

In accordance with Section 15 (Resource Management) and Section 9.2 (Experimental Groups), we first executed staged 1-entity (`phase6_smoke_1ent_qwen25_3b`, `54.22s`) and 4-entity (`phase6_integ_4ent_qwen25_3b`, `92.69s`, $P=100.0\%$) end-to-end retrieval-and-matching tests from raw XML before executing the 10 controlled experimental runs below.

### 3.1. Complete Phase 6 Experimental Table (`phase6_small_model_results.csv`)

| Exp Group | Experiment ID | Chat Model (Total Params) | Embedding Model (Dim) | $\tau$ | Prompt Indent | Routing | Pred | TP | FP | FN | Precision (%) | Recall (%) | $F_1$ (%) | Runtime (s) | Val Calls | Bypasses | Prompt / Comp Tokens (Measured) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ref (8B Upstream)** | `phase1_cmt_confof_v1` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 28-sp | `det`* | 12 | 5 | 7 | 11 | 41.67% | 31.25% | **35.71%** | 2,584.34 | 760 | 0 | 235,043 / 106,605 |
| **Ref (8B Parity R2–3)** | `phase5_expC_run2..3` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 28-sp | `det` | 11 | 6 | 5 | 10 | 54.55% | 37.50% | **44.45%** | 290.84 | 128 | 12 | 48,665 / 58,338 |
| **E1 (Run 1)** | `phase6_E1_qwen25_3b_baseline_run1` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | 28-sp | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 589.46 | 59 | 12 | 3,828 / 6,514 |
| **E1 (Run 2)** | `phase6_E1_qwen25_3b_baseline_run2` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | 28-sp | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 492.73 | 59 | 12 | 3,828 / 6,425 |
| **E1 (Run 3)** | `phase6_E1_qwen25_3b_baseline_run3` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | 28-sp | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 490.49 | 59 | 12 | 3,828 / 6,425 |
| **E2 (Opt Prompt)** | `phase6_E2_qwen25_3b_optimized_prompt` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | Clean | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 490.09 | 59 | 12 | 3,592 / 6,247 |
| **E3 (Router Det 4e)** | `phase6_E3_qwen25_3b_router_det_4ent` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | Clean | `det` | 1 | 1 | 0 | 15 | 100.0% | 6.25% | 11.76% | **0.57** | 0 | 2 | 0 / 0 (`0` router calls) |
| **E4 (Router LLM 4e)** | `phase6_E4_qwen25_3b_router_llm_4ent` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.90` | Clean | `llm_json` | 1 | 1 | 0 | 15 | 100.0% | 6.25% | 11.76% | **28.73** | 0 | 2 | 2,028 / 336 (`12` router calls) |
| **E5 (Alt Embed)** | `phase6_E5_qwen25_3b_mxbai_1024d` | `qwen2.5:3b` (`3.09B`) | `mxbai-embed-large` (`1024`) | `0.90` | Clean | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 449.46 | 52 | 12 | 3,115 / 5,759 |
| **E6 ($\tau = 0.850$)** | `phase6_E6_qwen25_3b_tau085` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.85` | Clean | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 2,152.88 | 274 | 12 | 16,492 / 29,786 |
| **E6 ($\tau = 0.875$)** | `phase6_E6_qwen25_3b_tau0875` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (`768`) | `0.875`| Clean | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 1,268.48 | 163 | 12 | 9,833 / 17,473 |
| **E7 (Reasoning 1.5B)**| `phase6_E7_deepseek_r1_15b_full` | `deepseek-r1:1.5b` (`1.78B`) | `nomic-embed-text` (`768`) | `0.90` | Clean | `det` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 2,392.25 | 49 | 12 | 1,708 / 61,555 |

---

## 4. Scientific Interpretation & Ablation Analysis (Section 9.4)

### 4.1. Repeatability & Determinism Analysis (`E1_run1` vs. `E1_run2` vs. `E1_run3` — `AC-14`, `AC-15`)
- Across all 3 repeated runs of the principal $\le 4\text{B}$ configuration (`qwen2.5:3b` with `temperature=0.0, seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0`), `E1_run1`, `E1_run2`, and `E1_run3` achieved **100% identical alignment metrics and predicted pairs**:
  - $\text{Precision} = 66.67\% \pm 0.00\%$
  - $\text{Recall} = 25.00\% \pm 0.00\%$
  - $F_1 = 36.36\% \pm 0.00\%$ (`TP=4, FP=2, FN=12`, `59` LLM validation calls, `12` exact-name bypasses).
  - Runs 2 and 3 achieved identical token counts (`3,828` prompt tokens, `6,425` completion tokens, `10,253` total tokens) and near-identical execution times (`492.73s` and `490.49s` after model warmup in Run 1 at `589.46s`).

### 4.2. Accuracy Relative to the 8B Reference Baseline (`qwen2.5:3b` vs. `llama3:8b`)
- **Comparison vs. Committed Upstream `Agent-OM-Lite` (`llama3:8b`):** The 3.09B `qwen2.5:3b` + `nomic-embed-text` configuration achieves **$F_1 = 36.36\%$ ($P=66.67\%, R=25.00\%$)**, which slightly exceeds the committed upstream `Agent-OM-Lite` table benchmark ($F_1 = 34.78\%, P=57.14\%, R=25.00\%$) and the raw upstream execution (`Exp B`, $F_1 = 35.71\%, P=41.67\%, R=31.25\%$) because `nomic-embed-text` + reciprocal merging suppresses false positives (`FP=2` vs `FP=7`).
- **Comparison vs. Phase 4 Repaired `Local Parity` (`llama3:8b` 4096-dim):** Our repaired `llama3:8b` parity pipeline (`Exp C`, $F_1 = 44.45\%, P=54.55\%, R=37.50\%, \text{TP}=6$) outperforms all $\le 4\text{B}$ configurations by **$+8.09$ percentage points in $F_1$** ($+12.50$ percentage points in Recall).
- **Root Cause of the 2-TP Gap ($\text{TP}=4$ vs. $\text{TP}=6$):**
  - Inspecting the 6-variant stage attrition tables reveals that in `E6` ($\tau = 0.85$), `nomic-embed-text` retrieval + RRF + Reciprocal Merger **without LLM validation** (`3_merge_without_validation`) recovers **`7` True Positives ($R = 43.75\%, P = 46.67\%, F_1 = 45.16\%$)**, and at $\tau = 0.875$ achieves **$F_1 = 48.28\%$ ($P = 53.85\%, R = 43.75\%, \text{TP}=7, \text{FP}=6$)**!
  - Furthermore, in `E6` ($\tau = 0.85$), `qwen2.5:3b` **Source $\to$ Target validation (`4_s2t_with_validation`) achieves $F_1 = 48.00\%$ ($P = 66.67\%, R = 37.50\%, \text{TP}=6, \text{FP}=3$)**, successfully validating `ProgramCommitteeMember` $\leftrightarrow$ `Member_PC` and `title` $\leftrightarrow$ `hasTitle` in the `Source -> Target` direction.
  - However, in the reverse `Target -> Source` direction (`5_t2s_with_validation`), when the prompt asks whether `confOf:hasTitle` / `confOf:Member_PC` is equivalent to `cmt:title` / `cmt:ProgramCommitteeMember`, the smaller 3.09B and 1.78B models answer conservatively (`"no"`), causing the symmetric Reciprocal Merger ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) to drop those two true positives (`TP` drops from `6` in `4_s2t_with_validation` to `4` in `6_final_with_validation_and_merger`).
  - This confirms the **prompt-order asymmetry hypothesis** identified in Step 7D: smaller $\le 4\text{B}$ models exhibit higher directional sensitivity on abbreviated (`Member_PC` vs `ProgramCommitteeMember`) and prefix-asymmetric (`hasTitle` vs `title`) ontology labels than 8B+ models.

### 4.3. Effect of Prompt Optimization (`E1` vs. `E2`)
- Removing the upstream 28-space prompt indentation (`E2`, `indent_validation_prompt=False`) reduced total prompt token consumption by **$6.17\%$** (`3,592` vs `3,828` prompt tokens) and total tokens by **$4.04\%$** (`9,839` vs `10,253`) while producing the exact same validation decisions and final alignment ($F_1 = 36.36\%$).

### 4.4. Effect of Deterministic vs. LLM JSON Tool Routing (`E3` vs. `E4`)
- On the 4-entity benchmark slice, `E3` (`tool_routing_mode="deterministic"`) and `E4` (`tool_routing_mode="llm_json"`) produced **identical alignment outputs** ($P=100.0\%, \text{TP}=1$).
- However, `llm_json` routing (`E4`) required `12` extra LLM router invocations (`2,364` tokens) and took **`28.73s` vs. `0.57s` ($50.6\times$ slower)** during matching when exact-name bypasses were present. Deterministic routing eliminates $100\%$ of router latency and JSON parsing fragility with zero loss in accuracy.

### 4.5. Effect of Reasoning-Distilled $\le 4\text{B}$ Architecture (`E7`: `deepseek-r1:1.5b` vs. `E2`: `qwen2.5:3b`)
- `deepseek-r1:1.5b` (`1,777,088,000` parameters) generates explicit chain-of-thought reasoning traces (`61,555` completion tokens across `49` validation calls — **$10.7\times$ more completion tokens per call** than `qwen2.5:3b`), increasing runtime from `490.09s` to `2,392.25s` ($4.88\times$ slower).
- In directional validation (`4_s2t_with_validation`), `deepseek-r1:1.5b` accepted more candidates (`14` S2T pairs, `TP=5, FP=9`, $F_1=33.33\%$; `10` T2S pairs, `TP=4, FP=6`, $F_1=30.77\%$) than `qwen2.5:3b` (`7` S2T pairs, `TP=4, FP=3`), demonstrating higher directional recall on S2T (`5` TPs vs `4` TPs) at the cost of lower directional precision (`35.71%` vs `57.14%`).
- Remarkably, after the Reciprocal Siamese Merger (`6_final_with_validation_and_merger`), all asymmetric false positives accepted by `deepseek-r1:1.5b`'s chain-of-thought reasoning were intersected out, converging to the exact same 6 reciprocal pairs (`TP=4, FP=2`, $P=66.67\%, R=25.00\%, F_1=36.36\%$).
