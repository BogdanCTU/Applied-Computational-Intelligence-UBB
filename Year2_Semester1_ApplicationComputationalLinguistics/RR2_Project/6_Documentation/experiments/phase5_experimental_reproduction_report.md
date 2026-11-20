# Phase 5 Report — Controlled Experimental Reproduction & Attrition Analysis
## Agent-OM: Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Report Date:** 2026-11-20  
**Status:** `COMPLETED` (`AC-10`, `AC-12` SATISFIED)  
**Benchmark Dataset:** OAEI Conference Track — `CMT–ConfOf` (`88` CMT entities, `74` ConfOf entities, `16` Gold Equivalences)  
**Artifacts Directory:** `output/replication_runs/` & `output/replication_runs/comparisons/`

---

## 1. Experimental Matrix Overview (`Experiments A, B, C, D`)

Phase 5 conducts a controlled reproduction comparing four distinct architectural tiers on the 162-entity `CMT–ConfOf` benchmark:
- **Experiment A (`upstream_product_reference`):** Published/committed upstream Agent-OM reference using cloud `gpt-4o-2024-05-13` + `text-embedding-ada-002` (`1536`-dim) (Read-only reference; zero cloud calls executed).
- **Experiment B (`phase1_cmt_confof_agent_om_lite_v1`):** Isolated execution of the unmodified upstream repository (`original_repo/`) in `Agent-OM-Lite` mode using local `llama3:8b` + `llama3:8b` (`4096`-dim via `LlamaEmbeddingBridge`).
- **Experiment C (`phase5_expC_local_parity_run1`..`run3`):** Our independent Python 3.13 implementation (`src/`) running the `upstream_lite_parity` profile (`llama3:8b` + `llama3:8b` `4096`-dim) across **3 repeated runs**, plus a deterministic vs. LLM JSON tool-router ablation (`phase5_expC_router_det_4ent` vs. `phase5_expC_router_llm_4ent`).
- **Experiment D (`phase5_expD_local_adapted_run2`):** Completion of the `local_adapted` profile using dedicated 768-dim `nomic-embed-text` embeddings in isolated database `agent_om_adapted` (preserving the incomplete `phase5_expD_local_adapted_run1` untouched).

---

## 2. Master Benchmark Results (`Experiments A–D`)

| Experiment Group | Run ID | Chat Model | Embedding Model (Dim) | Pred | TP | FP | FN | Precision (%) | Recall (%) | $F_1$ (%) | Runtime (s) | LLM Calls |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exp A (Paper / v1.0.1 Table)** | `ref_upstream_gpt4o_v1` | `gpt-4o-2024-05-13` | `text-embedding-ada-002` (1536) | 9 | 6 | 3 | 10 | 66.67% | 37.50% | **48.00%** | — | — |
| **Exp A (Committed HEAD CSV)** | `ref_upstream_gpt4o_head` | `gpt-4o-2024-05-13` | `text-embedding-ada-002` (1536) | 8* | 6 | 2 | 10 | 75.00% | 37.50% | **50.00%** | — | — |
| **Upstream Lite (Committed Table)** | `result-om-2025-test.csv` | `llama3:8b` | `llama3:8b` (4096) | 7 | 4 | 3 | 12 | 57.14% | 25.00% | **34.78%** | — | — |
| **Exp B (Upstream Lite Executed)** | `phase1_cmt_confof_v1` | `llama3:8b` | `llama3:8b` (4096) | 12 | 5 | 7 | 11 | 41.67% | 31.25% | **35.71%** | 2,584.34 s | 1,627 |
| **Exp C (Local Parity — Run 1)** | `phase5_expC_local_parity_run1` | `llama3:8b` | `llama3:8b` (4096) | 12 | 6 | 6 | 10 | 50.00% | 37.50% | **42.86%** | 1,377.25 s | 507 |
| **Exp C (Local Parity — Run 2)** | `phase5_expC_local_parity_run2` | `llama3:8b` | `llama3:8b` (4096) | 11 | 6 | 5 | 10 | **54.55%** | **37.50%** | **44.45%** | 323.68 s** | 128** |
| **Exp C (Local Parity — Run 3)** | `phase5_expC_local_parity_run3` | `llama3:8b` | `llama3:8b` (4096) | 11 | 6 | 5 | 10 | **54.55%** | **37.50%** | **44.45%** | 257.99 s** | 128** |
| **Exp C Mean $\pm$ Std ($n=3$)** | `run1`..`run3` | `llama3:8b` | `llama3:8b` (4096) | 11.33 | 6.0 | 5.33 | 10.0 | $53.03\% \pm 2.14\%$ | $37.50\% \pm 0.00\%$ | **$43.92\% \pm 0.75\%$** | — | — |
| **Exp D (Local Adapted — Step 6 E1)** | `historical_step6_E1` | `qwen3.5:9b` | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | 66.67% | 25.00% | **36.36%** | 42.83 s** | 8** |
| **Exp D (Local Adapted — Run 2)** | `phase5_expD_local_adapted_run2` | `qwen3.5:4b` (4.54B) | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 95.14 s** | 8** |

*\*Note: Committed `predict.csv` contains 8 real URI pairs plus a header row `(Entity1, Entity2)`. **Runs reusing populated hybrid-memory vector tables (`--skip-retrieval`).*

---

## 3. Six-Variant Stage Attrition Analysis Across Experiments

From `output/replication_runs/comparisons/phase5_6variants_all_experiments.csv`, we trace how candidate correspondences evolve across the 6 canonical Agent-OM alignment stages:

1. `s2t_no_val`: Source $\to$ Target RRF Top-1 before LLM validation.
2. `t2s_no_val`: Target $\to$ Source RRF Top-1 before LLM validation.
3. `merged_no_val`: Reciprocal Merger ($\mathcal{A}_{S \to T}^{\text{raw}} \cap \mathcal{A}_{T \to S}^{\text{raw}}$) without LLM validation (`E5` ablation).
4. `s2t_val`: Source $\to$ Target after score-group LLM validation (`E6` ablation).
5. `t2s_val`: Target $\to$ Source after score-group LLM validation.
6. `final_merged`: Full Agent-OM pipeline (LLM validation + Reciprocal Siamese Merger).

| Experiment | Stage Variant | Predicted | TP | FP | FN | Precision (%) | Recall (%) | $F_1$ (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exp A: GPT-4o (HEAD CSV)** | `1_s2t_no_val` | 36 | 7 | 29 | 9 | 19.44% | 43.75% | 26.92% |
| | `2_t2s_no_val` | 44 | 10 | 34 | 6 | 22.73% | 62.50% | 33.33% |
| | `3_merged_no_val` | 17 | 7 | 10 | 9 | 41.18% | 43.75% | 42.42% |
| | `4_s2t_val` | 11 | 7 | 4 | 9 | 63.64% | 43.75% | 51.85% |
| | `5_t2s_val` | 12 | 6 | 6 | 10 | 50.00% | 37.50% | 42.86% |
| | **`6_final_merged`** | **8** | **6** | **2** | **10** | **75.00%** | **37.50%** | **50.00%** |
| **Exp B: Upstream Lite (`llama3:8b`)** | `1_s2t_no_val` | 47 | 7 | 40 | 9 | 14.89% | 43.75% | 22.22% |
| | `2_t2s_no_val` | 46 | 7 | 39 | 9 | 15.22% | 43.75% | 22.58% |
| | `3_merged_no_val` | 21 | 6 | 15 | 10 | 28.57% | 37.50% | 32.43% |
| | `4_s2t_val` | 26 | 7 | 19 | 9 | 26.92% | 43.75% | 33.33% |
| | `5_t2s_val` | 27 | 6 | 21 | 10 | 22.22% | 37.50% | 27.91% |
| | **`6_final_merged`** | **12** | **5** | **7** | **11** | **41.67%** | **31.25%** | **35.71%** |
| **Exp C: Local Parity (`llama3:8b`)** | `1_s2t_no_val` | 52 | 7 | 45 | 9 | 13.46% | 43.75% | 20.59% |
| | `2_t2s_no_val` | 47 | 7 | 40 | 9 | 14.89% | 43.75% | 22.22% |
| | `3_merged_no_val` | 20 | 7 | 13 | 9 | 35.00% | 43.75% | 38.89% |
| | `4_s2t_val` | 27 | 7 | 20 | 9 | 25.93% | 43.75% | 32.56% |
| | `5_t2s_val` | 27 | 6 | 21 | 10 | 22.22% | 37.50% | 27.91% |
| | **`6_final_merged` (Runs 2–3)** | **11** | **6** | **5** | **10** | **54.55%** | **37.50%** | **44.45%** |
| **Exp D: Local Adapted (`nomic` 768d)** | `1_s2t_no_val` | 9 | 6 | 3 | 10 | 66.67% | 37.50% | 48.00% |
| | `2_t2s_no_val` | 10 | 7 | 3 | 9 | 70.00% | 43.75% | 53.85% |
| | `3_merged_no_val` | 8 | 6 | 2 | 10 | **75.00%** | **37.50%** | **50.00%** |
| | `4_s2t_val` | 8 | 5 | 3 | 11 | 62.50% | 31.25% | 41.67% |
| | `5_t2s_val` | 8 | 5 | 3 | 11 | 62.50% | 31.25% | 41.67% |
| | **`6_final_merged`** | **6** | **4** | **2** | **12** | **66.67%** | **25.00%** | **36.36%** |

---

## 4. Tool-Router Ablation (`Deterministic` vs. `LLM JSON Router`)

In `phase5_expC_router_det_4ent` vs. `phase5_expC_router_llm_4ent`:
- **Alignment Equivalence:** Both produced identical final predictions (`TP=1, FP=0, FN=7`, $P=100.0\%, R=12.50\%, F_1=22.22\%$) on the 4-entity slice.
- **Computational Overhead:** `tool_routing_mode="llm_json"` required **40 additional LLM calls** (`28` router calls + `12` feature/validation calls) and increased runtime from `34.11s` to `62.47s` ($+83.1\%$ latency overhead) while yielding zero change in alignment output because every entity deterministically invokes the same three retrieval tools (`syntactic`, `lexical`, `semantic`) followed by `validate`.

---

## 5. Key Findings from Phase 5

1. **Local Parity Outperforms Upstream Agent-OM-Lite Baseline:** Resolving `DISC-01` (skipping empty semantic chunks) and `DISC-03` (combined alphabetical property sorting) enabled our local `llama3:8b` parity pipeline (`Exp C`) to achieve **$F_1 = 44.45\%$** ($P=54.55\%, R=37.50\%$), outperforming both the committed `result-om-2025-test.csv` baseline ($F_1 = 34.78\%$) and the raw upstream execution (`Exp B`, $F_1 = 35.71\%$).
2. **Contrastive Embeddings (`nomic-embed-text`) Eliminate Retrieval Noise:** In `Exp D`, replacing causal `llama3:8b` 4096-dim embeddings with dedicated 768-dim `nomic-embed-text` embeddings at $\tau = 0.90$ reduced unvalidated false positives from `45` (S2T) / `40` (T2S) down to just `3` (S2T) / `3` (T2S), achieving **$F_1 = 50.00\%$ ($P=75.00\%, R=37.50\%$)** directly via RRF + Reciprocal Merger (`3_merged_no_val`), matching the committed GPT-4o + `text-embedding-ada-002` headline score!
3. **Validator False-Negative Attrition on Non-Trivial Lexical Pairs:** In `Exp D`, the unvalidated reciprocal merger (`3_merged_no_val`) correctly recovered 6 TPs (`Administrator`, `Author`, `Conference`, `Person`, `ProgramCommitteeChair/Chair_PC`, and `title/hasTitle`). However, the zero-shot LLM validation prompt rejected `ProgramCommitteeChair` $\leftrightarrow$ `Chair_PC` and `title` $\leftrightarrow$ `hasTitle` in one direction, reducing final validated $F_1$ from $50.00\%$ to $36.36\%$. This motivates the Phase 6 investigation of prompt optimization and threshold calibration on $\le 4\text{B}$ models.
