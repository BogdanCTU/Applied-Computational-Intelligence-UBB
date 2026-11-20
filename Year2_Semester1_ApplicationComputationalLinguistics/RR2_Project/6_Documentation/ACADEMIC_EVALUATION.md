# Academic Evaluation Report — Agent-OM Scientific Replication, Python 3.13 Modernisation & Local $\le 4\text{B}$ LLM Adaptation

**Project Title:** Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation and Desktop Workbench  
**Course / Program:** Applied Computational Intelligence / Application of Computational Linguistics (`RR2_Project`)  
**Institution:** Babeș-Bolyai University (UBB), Faculty of Mathematics and Computer Science  
**Date:** 2026-11-20  
**Reference Publication:**  
Qiang, Zhangcheng; Wang, Weiqing; Taylor, Kerry (2024/2025). *"Agent-OM: Leveraging LLM Agents for Ontology Matching."* Proceedings of the VLDB Endowment (PVLDB), Vol. 18, Issue 3, pp. 516–529. DOI: [`10.14778/3712221.3712222`](https://doi.org/10.14778/3712221.3712222) · arXiv: [`2312.00326`](https://arxiv.org/abs/2312.00326)  
**Reference Repository:** [`https://github.com/qzc438/ontology-llm`](https://github.com/qzc438/ontology-llm) (Audited Commit `89d0f967a466f17692768e5e370c29b35e5e77e3`, Aggregate SHA-256: `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`)

---

## 1. Introduction

Ontology Matching (OM) is the task of finding semantic correspondences (primarily equivalence relations, $\equiv$) between classes and properties across two independently engineered ontologies, $O_1$ (source) and $O_2$ (target). Classical ontology matching systems rely on handcrafted lexical similarity rules and structural graph propagation, which struggle when two ontologies describe the same domain using different phrasing or naming conventions. Conversely, passing two entire ontologies directly into a Large Language Model (LLM) prompt causes quadratic token scaling ($O(|E_1| \times |E_2|)$), context-window overflow, and hallucinated alignments.

**Agent-OM** (Qiang et al., PVLDB 2025) introduces a two-agent architecture (**Retrieval Agent** + **Matching Agent**) combined with a hybrid relational-vector database (**PostgreSQL + `pgvector`**) to decouple candidate retrieval from LLM equivalence verification.

This academic evaluation report assesses:
1. The **final software verification** of our reorganized Python 3.13 implementation (`1_Source/` through `6_Documentation/`).
2. A **component-by-component scientific comparison** between the original Agent-OM paper/repository and our local implementation.
3. A **consolidated empirical comparison** separating the original paper's reported metrics, the official repository's committed artifacts, our isolated local execution of the unmodified upstream repository, our repaired local 8B parity pipeline, and our strict $\le 4\text{B}$ parameter local Ollama adaptation.
4. An explicit assessment of **benchmark coverage**, **local Ollama telemetry**, **limitations**, and **reproduction classification**.

---

## 2. Original Research Objectives

The original Agent-OM paper (Qiang et al., PVLDB 2025) investigated three primary research goals:
1. **Scalable LLM-Based Ontology Matching:** Overcome LLM context-length limits and positional bias by using a Retrieval-Augmented Generation (RAG) hybrid vector store (`pgvector`) to retrieve only the top-$k$ most relevant candidate entities per query entity.
2. **Multi-View Entity Representation:** Combine three complementary representations for every ontology entity:
   - **Syntactic view:** Normalized local URI or label string.
   - **Lexical view:** LLM-generated domain definition enriched with annotation literals (`rdfs:comment`, `skos:definition`, etc.).
   - **Semantic view:** LLM-verbalized natural-language description of the entity's 1-hop structural RDF neighborhood (`rdfs:subClassOf`, `rdfs:domain`, `rdfs:range`, `owl:disjointWith`, etc.).
3. **Bidirectional Siamese Validation (`Agent-OM-Lite` Feasibility):** Demonstrate that combining Reciprocal Rank Fusion (RRF), score-group LLM validation, and a bidirectional Siamese intersection ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) allows both commercial foundation models (`gpt-4o`) and open-weight models (`llama3:8b`, termed *Agent-OM-Lite*) to perform ontology matching without task-specific fine-tuning.

---

## 3. Original Agent-OM Architecture

The original Agent-OM pipeline executes in three sequential scripts orchestrated by `run_config.py`:

1. **Feature Extraction & Verbalization (`om_ontology_to_csv.py` — Retrieval Agent Part 1):**
   - Loads source ontology $O_1$ and target ontology $O_2$ via `rdflib.Graph().parse()`.
   - Extracts named classes (`owl:Class`, `skos:Concept`, excluding `owl:Thing`) and properties (`owl:ObjectProperty`, `owl:DatatypeProperty`), filtering out 11 reserved vocabulary URIs.
   - For each entity, generates the syntactic string $T_{\text{syn}}(e)$, invokes the chat LLM to generate the lexical definition $T_{\text{lex}}(e)$, and invokes the chat LLM to verbalize the structural Turtle subgraph into $T_{\text{sem}}(e)$.
   - Writes the 162-row feature table to `ontology_matching.csv`.
2. **Chunking, Embedding & Vector Indexing (`om_csv_to_database.py` — Hybrid Memory Database):**
   - Assigns each row a zero-padded identifier (`001-Source-Class-Accept`, etc.).
   - Splits non-empty text via `RecursiveCharacterTextSplitter(separators=[".", "\n"], chunk_size=500, chunk_overlap=0)`.
   - Embeds chunks using `OpenAIEmbeddings("text-embedding-ada-002")` (`1536`-dim) or `OllamaEmbeddings("llama3:8b")` (`4096`-dim) and stores them in four PostgreSQL tables: `ontology_matching`, `syntactic_matching`, `lexical_matching`, and `semantic_matching`.
3. **Bidirectional Retrieval, RRF, Validation & Siamese Merging (`om_database_matching.py` — Matching Agent):**
   - In both directions ($O_1 \to O_2$ and $O_2 \to O_1$), queries each vector table for opposing entities of the same type (`Class` vs. `Property`) with cosine similarity $1 - (\mathbf{u} \Leftrightarrow \mathbf{v}) \ge \tau$ (default $\tau = 0.90$, $\text{top\_k} = 3$).
   - Combines the three ranked lists via unsmoothed Reciprocal Rank Fusion ($k_0 = 0$):
     $$\text{RRF}(c \mid q) = \sum_{m \in \{\text{syn}, \text{lex}, \text{sem}\}} \frac{1}{\text{rank}_m(c)}$$
   - Groups candidates by distinct RRF score in descending order. Within each score group, checks for an exact normalized name match (`check_name_matching`, bypassing the LLM) or queries the LLM with a zero-shot Yes/No equivalence prompt. Stops evaluating lower RRF score groups as soon as at least one candidate in the current group is accepted.
   - Intersects the validated $O_1 \to O_2$ and $O_2 \to O_1$ alignments (`pd.merge(..., on=['Entity1', 'Entity2'])`) and computes Precision, Recall, and $F_1$ against `reference.xml`.

---

## 4. Local Implementation (`1_Source/`)

Our modernized Python 3.13 implementation (`1_Source/`, bridged to `src/` via [`src/__init__.py`](../src/__init__.py)) replaces the monolithic script architecture of `original_repo/` with a modular, object-oriented, testable package hierarchy:

- **[`1_Source/config.py`](../1_Source/config.py):** Defines `AppConfig` and 7 explicit configuration profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`, `local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`) with strict loopback enforcement (`127.0.0.1`) and protected database guards (`PROTECTED_DATABASES = {"agent_om_local"}`).
- **[`1_Source/ontology/`](../1_Source/ontology/):** Multi-format RDFLib parser (`parser.py`) and deterministic entity extractor (`entity_extractor.py`) with combined alphabetical property sorting (`combine_properties_sort=True`) and code-IRI label resolution (`rdfs:label` $\to$ `skos:prefLabel` $\to$ `uri_to_name`).
- **[`1_Source/retrieval/`](../1_Source/retrieval/):** Modular `SyntacticRetriever`, `LexicalRetriever` (supporting both PVLDB `v1.0.0` 2-predicate and `HEAD` 10-predicate scopes), `SemanticRetriever` (supporting both PVLDB `v1.0.0` 7-predicate and `HEAD` 18-predicate + blank-node closure scopes in memory without writing temporary `.ttl` files to disk), and `rank_fusion.py` (`reciprocal_rank_fusion`).
- **[`1_Source/db/`](../1_Source/db/):** Synchronous `psycopg2` + `pgvector` `DatabaseManager` (`database_manager.py`) using bulk `execute_values` inserts, runtime vector-dimension verification, empty-placeholder chunk skipping (`skip_empty_chunks=True`), and write-protection on `agent_om_local`.
- **[`1_Source/matching/`](../1_Source/matching/):** `MatchingValidator` (`validator.py`) with exact-name bypass, regex word-boundary Yes/No extraction (`r"\b(?:yes|no)\b"`), configurable 28-space vs. clean prompt formatting, and `ReciprocalMerger` (`merger.py`).
- **[`1_Source/agents/`](../1_Source/agents/):** `RetrievalAgent` and `MatchingAgent` supporting both deterministic Python tool execution (`tool_routing_mode="deterministic"`) and upstream-compatible LLM JSON tool routing (`tool_routing_mode="llm_json"`).
- **[`1_Source/gui/`](../1_Source/gui/):** 10-screen PySide6 desktop workbench backed by 11 modular service classes and packaged via PyInstaller (`packaging/agent_om.spec`).

---

## 5. Local Ollama Integration & $\le 4\text{B}$ Verification (`1_Source/llm/`)

To eliminate external API dependencies and satisfy the strict $\le 4,000,000,000$ ($4.0\text{B}$) total parameter constraint, we implemented a dedicated local inference layer in [`1_Source/llm/`](../1_Source/llm/):

1. **Separated Chat and Embedding Roles (`AC-07`):**
   - [`LocalChatProvider`](../1_Source/llm/chat_provider.py) handles natural-language generation and equivalence validation via `POST http://127.0.0.1:11434/api/chat` with deterministic decoding (`temperature=0.0, seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0, num_ctx=2048`).
   - [`LocalEmbeddingProvider`](../1_Source/llm/embedding_provider.py) handles dense vector encoding via `POST http://127.0.0.1:11434/api/embed`, completely decoupling vector dimensionality (`768`-dim or `1024`-dim) from the chat model's hidden state dimension.
2. **Authoritative Runtime Parameter Inspection (`AC-06`):**
   - [`ModelRegistry`](../1_Source/llm/model_registry.py) and [`ModelValidator`](../1_Source/llm/model_validator.py) query `POST /api/show` and read `model_info["general.parameter_count"]` directly from the GGUF/Safetensors header rather than trusting the model tag.
   - This inspection exposed a critical metadata discrepancy: **`qwen3.5:4b` actually contains $4,538,986,496$ ($4.54\text{B}$) parameters**, exceeding the $4.00\text{B}$ cap by $+538,986,496$ parameters. When `enforce_4b_limit=True`, `ModelValidator` raises `ParameterLimitExceededError` and blocks `qwen3.5:4b`.

### 5.1. Verified Local Ollama Model Inventory & Request Telemetry

All local models were verified live against `http://127.0.0.1:11434` (`Ollama 0.40.16`) and recorded in [`5_Results/manifests/ollama_model_inventory.json`](../5_Results/manifests/ollama_model_inventory.json):

| Model Tag | Role in Pipeline | Exact `general.parameter_count` | Embedding Dim | $\le 4.00\text{B}$ Compliant? | Measured Requests & Telemetry on `CMT–ConfOf` (`162` entities) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`qwen2.5:3b`** | Chat / Validator (`E1`–`E6`) | **`3,085,938,688` (`3.09B`)** | N/A (Chat) | **YES ($\le 4.0\text{B}$)** | `59` validation calls + `12` exact-name bypasses per run ($\tau=0.90$); `3,828` prompt / `6,425` completion tokens (`490.49s` matching time, `0` failures, `0` retries) |
| **`deepseek-r1:1.5b`** | Reasoning Validator (`E7`) | **`1,777,088,000` (`1.78B`)** | N/A (Chat) | **YES ($\le 4.0\text{B}$)** | `49` validation calls + `12` exact-name bypasses ($\tau=0.90$); `1,708` prompt / `61,555` completion tokens (`2,392.25s` matching time, `0` failures, `0` retries) |
| **`nomic-embed-text:latest`** | Dedicated Embedder (`E1`–`E4`, `E6`, `E7`) | **`136,727,040` (`0.14B`)** | **`768`-dim** | **YES ($\le 4.0\text{B}$)** | `53` batch `/api/embed` requests (`833` text chunks: `162` syn, `367` lex, `304` sem); **`31.88s` total (`37.27 ms/chunk`)**, `0` failures, `0` retries |
| **`mxbai-embed-large:latest`** | Dedicated Embedder (`E5`) | **`334,092,288` (`0.33B`)** | **`1024`-dim** | **YES ($\le 4.0\text{B}$)** | `53` batch `/api/embed` requests (`833` text chunks: `162` syn, `367` lex, `304` sem); **`86.69s` total (`101.86 ms/chunk`)**, `0` failures, `0` retries |
| `qwen3.5:4b` | Out-of-Limit Comparison (`Exp D`) | `4,538,986,496` (`4.54B`) | N/A (Chat) | **NO** ($+539\text{M}$ over) | `8` validation calls + `12` exact-name bypasses (`95.14s` matching time on `agent_om_adapted`, `0` failures) |
| `llama3:8b` | 8B Parity Baseline (`Exp B`, `Exp C`) | `8,030,261,248` (`8.03B`) | `4096`-dim (via Bridge) | **NO** (8B Reference) | `Exp B` (upstream): `1,627` total LLM calls (`2,584.34s`); `Exp C` (local parity): `507` total calls in Run 1 (`1,377.25s`), `128` validation calls + `12` bypasses in Runs 2–3 (`290.84s` mean) |
| `gemma4:12b` | Installed Out-of-Limit Model | `12,382,568,756` (`12.38B`) | N/A | **NO** ($12.38\text{B}$) | Inspected & excluded by `ModelValidator` (`>4.0\text{B}`) |

**Exact-Name Bypass Verification:** Across all local parity (`Exp C`) and local adapted/small-model runs (`Exp D`, `E1`–`E7`) on the full 162-entity `CMT–ConfOf` dataset, **`12` directional candidate pairs** (`6` in $O_1 \to O_2$ and `6` in $O_2 \to O_1$: `Administrator`, `Author`, `Conference`, `Paper`, `Person`, and `email` where normalized strings match) triggered the deterministic exact-name bypass (`check_name_matching`), avoiding redundant LLM calls.

---

## 6. Experimental Methodology

To ensure strict scientific control and protect historical evidence:
1. **Immutable Historical Baseline Protection (`AC-04`, `AC-19`):**
   - The 30 historical files in `output/` (`aggregate_sha256 = eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`), the 14 restored upstream CMT–ConfOf files in `original_repo/`, and the historical PostgreSQL database `agent_om_local` (`162/162/206/258` rows) were verified read-only and never overwritten.
2. **Database Isolation per Embedding Space:**
   - `agent_om_adapted`: `vector(768)` (`nomic-embed-text` for `Exp D`).
   - `agent_om_4b_baseline`: `vector(768)` (`nomic-embed-text` for `Phase 6 E1–E4, E6, E7`, `833` embedded chunks).
   - `agent_om_4b_mxbai`: `vector(1024)` (`mxbai-embed-large` for `Phase 6 E5`, `833` embedded chunks).
   - `agent_om_test` & `agent_om_4b_smoke`: Isolated databases for automated pytest integration and staged smoke tests.
3. **Four-Tier Comparative Design:**
   - **Tier 1:** Original Paper & Committed Upstream Cloud Reference (`gpt-4o-2024-05-13` + `text-embedding-ada-002` `1536`-dim).
   - **Tier 2:** Unmodified Upstream `Agent-OM-Lite` (`llama3:8b` + `llama3:8b` `4096`-dim) — both committed table (`result-om-2025-test.csv`) and isolated local execution (`Exp B`).
   - **Tier 3:** Repaired Local Python 3.13 `Agent-OM-Lite` Parity (`Exp C`, 3 repeatability runs) and Out-of-Limit Local Adapted (`Exp D`, `qwen3.5:4b`).
   - **Tier 4:** Strict $\le 4\text{B}$ Local Adaptation (`Phase 6 E1–E7`, 10 controlled runs covering 3 repeatability runs, prompt indentation ablation, deterministic vs. LLM JSON tool routing, `nomic-embed-text` `768`-dim vs. `mxbai-embed-large` `1024`-dim embedding swap, cosine threshold sweep $\tau \in \{0.85, 0.875, 0.90\}$, and `deepseek-r1:1.5b` reasoning model evaluation).

---

## 7. Benchmark Datasets & OAEI Track Coverage

### 7.1. Tracks Evaluated in the Original Agent-OM Paper
The original PVLDB paper (Qiang et al., 2025) evaluated Agent-OM across three OAEI tracks:
1. **OAEI Conference Track** (specifically highlighted via the `CMT–ConfOf` benchmark pair in the repository's default `run_config.py` and `result-om-2025-test.csv`).
2. **OAEI Anatomy Track** (`mouse–human`, ~2,744 Mouse Anatomy classes vs. ~3,304 NCI Human Anatomy classes; code-based IRIs `MA_...` and `NCI_...` with `o1_is_code=True, o2_is_code=True`).
3. **OAEI MSE (Materials Science & Engineering) Track** (`MaterialInformation–MatOnto` / `EMMO`).

### 7.2. Actual Dataset Availability in This Workspace
A forensic file audit of `3_Dataset/` and `original_repo/` (`output/replication_runs/manifests/original_repo_baseline_sha256.json`) confirms:
- **Available and Fully Evaluated Track:** **OAEI Conference Track — `CMT–ConfOf`** (`source.xml` [$226$ triples, $88$ entities: $29$ classes, $49$ object properties, $10$ datatype properties], `target.xml` [$199$ triples, $74$ entities: $38$ classes, $13$ object properties, $23$ datatype properties], and `reference.xml` [$16$ ground-truth equivalence correspondences]). Both `3_Dataset/original/conference/cmt-confof/` and `original_repo/data/conference/cmt-confof/component/` match the upstream SHA-256 baseline byte-for-byte (`source.xml = e0d55ee6...`, `target.xml = e869c4e7...`, `reference.xml = 3e02f17a...`).
- **Unavailable Tracks in Local Workspace:** The raw OWL/RDF ontology files for the **OAEI Anatomy (`mouse–human`)** and **OAEI MSE** tracks are **not present on disk** in `3_Dataset/` or `original_repo/data/` (only the 14 `cmt-confof` and summary CSV files exist in `original_repo/`). Because our strict execution constraints prohibit external downloads or Git operations, `Anatomy` and `MSE` could not be executed locally.
- **Scientific Scope Statement:** All empirical reproduction claims in this project apply specifically to the **OAEI Conference (`CMT–ConfOf`) benchmark** (`162` entities, `16` gold equivalences). We explicitly classify our scientific reproduction as a **Partial Scientific Reproduction (Single-Benchmark Deep Replication & $\le 4\text{B}$ Ablation Study on `CMT–ConfOf`)**, not a full multi-track reproduction of all three OAEI tracks in the PVLDB paper.

---

## 8. Evaluation Metrics

For any predicted alignment set $\mathcal{A}_{\text{pred}}$ and ground-truth reference alignment $\mathcal{A}_{\text{ref}}$ ($|\mathcal{A}_{\text{ref}}| = 16$ on `CMT–ConfOf`):
- **True Positives ($\text{TP}$):** $|\mathcal{A}_{\text{pred}} \cap \mathcal{A}_{\text{ref}}|$
- **False Positives ($\text{FP}$):** $|\mathcal{A}_{\text{pred}} \setminus \mathcal{A}_{\text{ref}}|$
- **False Negatives ($\text{FN}$):** $|\mathcal{A}_{\text{ref}} \setminus \mathcal{A}_{\text{pred}}|$
- **Precision ($P$):**
  $$P = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
- **Recall ($R$):**
  $$R = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
- **$F_1$-Score ($F_1$):**
  $$F_1 = \frac{2 \cdot P \cdot R}{P + R} = \frac{2 \cdot \text{TP}}{2 \cdot \text{TP} + \text{FP} + \text{FN}}$$

In addition to final merged metrics (`6_final_with_validation_and_merger`), our evaluation pipeline records all **6 intermediate stage variants** (`1_s2t_no_val`, `2_t2s_no_val`, `3_merged_no_val`, `4_s2t_val`, `5_t2s_val`, `6_final_merged`), wall-clock execution time (s), LLM validation call count, router call count, exact-name bypass count, and prompt/completion token counts.

---

## 9. Consolidated Scientific Results

### 9.1. Master Comparison Table on OAEI `CMT–ConfOf` (`162` Entities, `16` Gold Equivalences)

The table below consolidates the original paper/repository benchmarks, our isolated upstream execution, our repaired local 8B parity runs, and our strict $\le 4\text{B}$ local Ollama experiments (from [`5_Results/comparisons/phase5_benchmark_summary.csv`](../5_Results/comparisons/phase5_benchmark_summary.csv) and [`5_Results/comparisons/phase6_small_model_results.csv`](../5_Results/comparisons/phase6_small_model_results.csv)):

| Category / Tier | Experiment ID / Artifact | Chat Model (Verified Params) | Embedding Model (Dim) | $\tau$ | Pred | TP | FP | FN | Precision (%) | Recall (%) | **$F_1$ (%)** | Runtime (s) | LLM Calls (Total / Val) | Bypasses |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Original Paper / v1.0.1 Table** | `result-reference.csv` (Reported) | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 9 | 6 | 3 | 10 | `66.67%` | `37.50%` | **`48.00%`** | N/A | N/A | N/A |
| **1. Official Repo Committed HEAD** | `alignment/.../predict.csv` (Recalculated) | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 8 | 6 | 2 | 10 | `75.00%` | `37.50%` | **`50.00%`** | N/A | N/A | N/A |
| **2. Official Repo Lite Table** | `result-om-2025-test.csv` (Reported) | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 7 | 4 | 3 | 12 | `57.14%` | `25.00%` | **`34.78%`** | N/A | N/A | N/A |
| **2. Official Repo Executed Locally** | `phase1_cmt_confof_agent_om_lite_v1` (`Exp B`) | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 12 | 5 | 7 | 11 | `41.67%` | `31.25%` | **`35.71%`** | `2,584.34` | `1,627` / `760` | `0`* |
| **3. Local 8B Parity (Run 1 Full)** | `phase5_expC_local_parity_run1` (`Exp C1`) | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 12 | 6 | 6 | 10 | `50.00%` | `37.50%` | **`42.86%`** | `1,377.25` | `507` / `130` | `12` |
| **3. Local 8B Parity (Runs 2 & 3)** | `phase5_expC_local_parity_run2..3` (`Exp C2–3`) | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 11 | 6 | 5 | 10 | **`54.55%`** | **`37.50%`** | **`44.45%`** | `290.84`** | `128` / `128` | `12` |
| **3. Local Adapted (>4B Ref)** | `phase5_expD_local_adapted_run2` (`Exp D`) | `qwen3.5:4b` (`4.54B`) | `nomic-embed-text` (`768`) | `0.90` | 6 | 4 | 2 | 12 | `66.67%` | `25.00%` | **`36.36%`** | `95.14`** | `8` / `8` | `12` |
| **4. Strict $\le 4\text{B}$ Baseline (`E1` R1–3)** | `phase6_E1_qwen25_3b_baseline_run1..3` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `491.61`** | `59` / `59` | `12` |
| **4. Strict $\le 4\text{B}$ Clean Prompt (`E2`)** | `phase6_E2_qwen25_3b_optimized_prompt` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `490.09`** | `59` / `59` | `12` |
| **4. Strict $\le 4\text{B}$ Router Det (`E3`, 4-ent)** | `phase6_E3_qwen25_3b_router_det_4ent` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 1 | 1 | 0 | 15 | `100.00%` | `6.25%` | `11.76%` | **`0.57`** | `0` / `0` | `2` |
| **4. Strict $\le 4\text{B}$ Router LLM (`E4`, 4-ent)** | `phase6_E4_qwen25_3b_router_llm_4ent` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 1 | 1 | 0 | 15 | `100.00%` | `6.25%` | `11.76%` | **`28.73`** | `12` (`router`) | `2` |
| **4. Strict $\le 4\text{B}$ Alt Embed (`E5`)** | `phase6_E5_qwen25_3b_mxbai_1024d` | **`qwen2.5:3b` (`3.09B`)** | **`mxbai-embed-large` (`1024`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `449.46`** | `52` / `52` | `12` |
| **4. Strict $\le 4\text{B}$ $\tau=0.85$ (`E6a` Final)** | `phase6_E6_qwen25_3b_tau085` (`6_final`) | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.85` | 6 | 4 | 2 | 12 | `66.67%` | `25.00%` | **`36.36%`** | `2,152.88`** | `274` / `274` | `12` |
| **4. Strict $\le 4\text{B}$ $\tau=0.85$ (`E6a` S2T Val)** | `phase6_E6_qwen25_3b_tau085` (`4_s2t_val`) | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.85` | 9 | 6 | 3 | 10 | **`66.67%`** | **`37.50%`** | **`48.00%`** | — | `135` (S2T) | `6` |
| **4. Strict $\le 4\text{B}$ $\tau=0.875$ (`E6b` Final)** | `phase6_E6_qwen25_3b_tau0875` (`6_final`) | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.875` | 6 | 4 | 2 | 12 | `66.67%` | `25.00%` | **`36.36%`** | `1,268.48`** | `163` / `163` | `12` |
| **4. Strict $\le 4\text{B}$ $\tau=0.875$ (`E6b` No-Val Merger)** | `phase6_E6_qwen25_3b_tau0875` (`3_merge`) | **No LLM Validation (`0B`)** | **`nomic-embed-text` (`768`)** | `0.875` | 13 | 7 | 6 | 9 | **`53.85%`** | **`43.75%`** | **`48.28%`** | `31.88` | `0` | — |
| **4. Strict $\le 4\text{B}$ Reasoner (`E7`)** | `phase6_E7_deepseek_r1_15b_full` | **`deepseek-r1:1.5b` (`1.78B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **`66.67%`** | **`25.00%`** | **`36.36%`** | `2,392.25`** | `49` / `49` | `12` |

*\*Note: Upstream `om_database_matching.py` invokes the LLM tool-router (`ChatPromptTemplate | llm | JsonOutputParser()`) even before checking `check_name_matching`, hence `0` true zero-LLM bypasses in `Exp B`. \*\*Matching-and-validation runtime reusing the indexed hybrid-memory tables (`--skip-retrieval`).*

---

## 10. Comparison with the Original Paper & Repository

### 10.1. Distinguishing Reported Paper Metrics from Independently Recalculated Repository Metrics
A critical finding of our forensic audit is the distinction between **metrics reported in summary tables** and **metrics recalculated directly from the committed alignment CSV files** in `original_repo/`:
1. **Original Paper / `result-reference.csv` vs. Committed `predict.csv` (`GPT-4o` + `text-embedding-ada-002`):**
   - `original_repo/result_csv/result-reference.csv` reports `Precision = 0.67, Recall = 0.38, F1 = 0.48` (corresponding to `9` predictions: `TP=6, FP=3, FN=10`, $P=66.67\%, R=37.50\%, F_1=48.00\%$).
   - However, when we independently recalculate metrics on the actual committed `original_repo/alignment/conference/cmt-confof/component/predict.csv` file against `reference.xml` ($16$ gold pairs), `predict.csv` contains exactly **`8` data rows** (`TP=6, FP=2, FN=10`), yielding **$P = 75.00\%, R = 37.50\%, F_1 = 50.00\%$**!
   - *Why they differ:* `predict.csv` contains 1 header line (`Entity1,Entity2`) plus 8 URI pairs (`9` lines total). An earlier script version that counted raw file lines without skipping the header row counted `9` predicted pairs (`TP=6, FP=3` $\rightarrow$ $F_1=48.00\%$).
2. **Official Repository `Agent-OM-Lite` (`llama3:8b`) Table vs. Isolated Local Execution (`Exp B`):**
   - `original_repo/result_csv/result-om-2025-test.csv` reports `Agent-OM-Lite` (`llama3:8b`) on `CMT–ConfOf` at **$P = 57.14\%, R = 25.00\%, F_1 = 34.78\%$** (`TP=4, FP=3, FN=12`).
   - When we executed the unmodified `original_repo/` code locally in an isolated runner (`Exp B: phase1_cmt_confof_agent_om_lite_v1`), it achieved **$P = 41.67\%, R = 31.25\%, F_1 = 35.71\%$** (`TP=5, FP=7, FN=11` in `2,584.34s` across `1,627` LLM calls).
3. **Why Local Results Differ from the Original Paper:**
   - **Repaired Local 8B Parity (`Exp C`, $F_1 = 44.45\%$) vs. Upstream `Agent-OM-Lite` ($F_1 = 34.78\%$ / $35.71\%$):** Our local `llama3:8b` parity pipeline achieved $+9.67\%$ higher $F_1$ than the upstream table (`TP=6` vs `TP=4`) because Phase 4 fixed `DISC-01` (stripping `"Information is not available."` before chunking so isolated entities do not receive identical placeholder vectors with cosine similarity `1.0`) and `DISC-03` (combined alphabetical property sorting so `entity_id` RRF tie-breaking is deterministic) and replaced fragile LLM JSON tool-routing with deterministic Python orchestration.
   - **Strict $\le 4\text{B}$ Local Adaptation (`E1`–`E7`, $F_1 = 36.36\%$ Final Merged; $F_1 = 48.00\%$ S2T Validated; $F_1 = 48.28\%$ Unvalidated RRF Merger at $\tau=0.875$) vs. Cloud `GPT-4o` ($F_1 = 48.00\%$ / $50.00\%$):**
     - Dedicated contrastive embeddings (`nomic-embed-text` `768`-dim) retrieve **$7/16$ True Positives ($R = 43.75\%, F_1 = 48.28\%$)** at $\tau = 0.875$ before LLM validation — matching the retrieval ceiling of `text-embedding-ada-002` (`1536`-dim)!
     - In the $O_1 \to O_2$ direction at $\tau = 0.85$ (`4_s2t_with_validation`), `qwen2.5:3b` ($3.09\text{B}$) validates **$6/16$ True Positives ($P = 66.67\%, R = 37.50\%, F_1 = 48.00\%$)**, matching the PVLDB paper's reported `GPT-4o` score ($48.00\%$).
     - However, in the reverse $O_2 \to O_1$ direction (`5_t2s_with_validation`), when the prompt places `confOf:Member_PC` or `confOf:hasTitle` first and asks whether it matches `cmt:ProgramCommitteeMember` or `cmt:title`, the $3.09\text{B}$ and $1.78\text{B}$ models answer `"no"`. The strict bidirectional intersection ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) therefore drops those 2 asymmetric pairs, leaving `4` symmetric True Positives (`Administrator`, `Author`, `Conference`, `Person`) and `2` False Positives (`TP=4, FP=2, FN=12`, $P = 66.67\%, R = 25.00\%, F_1 = 36.36\%$).

---

## 11. Component-by-Component Classification & Differences from Original Implementation

Every component is classified using the five required academic categories:
- **Faithfully reproduced**
- **Adapted for local execution**
- **Reimplemented with a different method**
- **Not implemented**
- **Not experimentally verified**

| # | Component | Academic Classification | Original Agent-OM (`original_repo/`) | Local Implementation (`1_Source/`) & Exact Differences |
| :-: | :--- | :---: | :--- | :--- |
| 1 | **Overall Agent-OM Siamese Architecture** | **Faithfully reproduced** | Two-phase Siamese Retrieval Agent + Matching Agent with hybrid vector database, RRF, score-group validation, and reciprocal merger. | Identical two-phase Siamese pipeline structure and mathematical flow; modularized into Python 3.13 classes (`RetrievalAgent`, `MatchingAgent`, `DatabaseManager`, `ReciprocalMerger`). |
| 2 | **Retrieval Agent (Syntactic, Lexical, Semantic Views)** | **Faithfully reproduced** (with memory safety fix) | `om_ontology_to_csv.py`: extracts normalized URI/label (`syntactic`), 10-predicate LLM definition (`lexical`), and 18-predicate + blank-node closure Turtle verbalization (`semantic`), writing temporary `subgraph.ttl` files to CWD. | `1_Source/retrieval/`: uses identical prompt templates (including `"natual"` spelling) and identical 10-predicate lexical / 18-predicate + BNode semantic scopes (`predicate_scope="head"`), plus optional `pvl_v1` (2-lex / 7-sem) mode. Serializes Turtle subgraphs in memory instead of writing `subgraph.ttl` to disk. |
| 3 | **Matching Agent (Score-Group Loop & Early Stopping)** | **Faithfully reproduced** | `om_database_matching.py`: iterates RRF score groups `groups[:top_k]`, validates all candidates in a group, and `break`s after the first group with $\ge 1$ positive match. | `1_Source/agents/matching_agent.py`: identical `itertools.groupby` RRF score-group iteration and early-stopping `break` semantics. |
| 4 | **Hybrid Memory Database (`PostgreSQL + pgvector`)** | **Adapted for local execution** | `om_csv_to_database.py`: uses asynchronous `asyncpg`, drops tables unconditionally, and stores chunks in 4 tables (`ontology_matching`, `syntactic_matching`, `lexical_matching`, `semantic_matching`). | `1_Source/db/database_manager.py`: uses synchronous `psycopg2` `execute_values` bulk inserts on `127.0.0.1:5432`, adds `id SERIAL PRIMARY KEY`, skips empty `"Information is not available."` chunks (`DISC-01` fix), enforces runtime vector dimensions, and write-protects `agent_om_local`. |
| 5 | **LLM Configuration & Tool Routing** | **Adapted for local execution** | `run_config.py`: supports cloud APIs (`OpenAI`, `Anthropic`, `Google`, `HuggingFace`) and wraps every retrieval/matching call in an LLM JSON tool-router (`ChatPromptTemplate \| llm \| JsonOutputParser()`). | `1_Source/config.py` & `1_Source/llm/`: strictly local Ollama loopback (`127.0.0.1:11434`), blocks cloud models, enforces `temperature=0.0, seed=42, top_k=1`, and defaults to deterministic Python tool routing (`0` router calls) while retaining `tool_routing_mode="llm_json"` for ablation parity (`E3` vs. `E4`). |
| 6 | **Embedding Configuration** | **Adapted for local execution** | Couples `gpt-4o` with cloud `text-embedding-ada-002` (`1536`-dim) or couples `llama3:8b` with causal `llama3:8b` embeddings (`4096`-dim). | Decouples chat and embedding providers (`LocalChatProvider` vs. `LocalEmbeddingProvider`), pairing $\le 4\text{B}$ chat models (`qwen2.5:3b`, `deepseek-r1:1.5b`) with dedicated local contrastive embedders (`nomic-embed-text` `768`-dim, `mxbai-embed-large` `1024`-dim) and providing `LlamaEmbeddingBridge` (`4096`-dim) for 8B parity. |
| 7 | **Candidate Retrieval (Cosine Similarity SQL)** | **Faithfully reproduced** | SQL query `1 - (embedding <=> query_vec) >= similarity_threshold` filtered by opposing `source_or_target` and matching `entity_type`, `ORDER BY similarity DESC LIMIT 50`, deduplicated to `top_k = 3`. | Identical `pgvector` `<=>` cosine distance SQL query, entity-type filtering, first-chunk deduplication, and `top_k = 3` selection in `DatabaseManager.search_similar_entities()`. |
| 8 | **Reciprocal Rank Fusion (RRF)** | **Faithfully reproduced** | `om_database_matching.py`: unsmoothed $\sum 1/\text{rank}$ ($k_0 = 0$), ignores `"Entity-Dummy"`, sorts by `(-score, entity_id)`. | `1_Source/retrieval/rank_fusion.py`: identical unsmoothed RRF formula ($k_0 = 0$), `"Entity-Dummy"` filtering, and `(-score, entity_id)` lexicographical tie-breaking. |
| 9 | **LLM Equivalence Validation & Exact-Name Bypass** | **Faithfully reproduced** (with configurable indentation) | `om_database_matching.py`: checks `cleaning(a) == cleaning(b)` bypass, else prompts LLM with 28-space indented equivalence template and extracts Yes/No via `r"\b(?:yes|no)\b"`. | `1_Source/matching/validator.py`: identical exact-name bypass (with `DISC-02` fix so bypass executes *before* any tool router call and resolves code-IRI labels) and identical regex parser; supports both upstream 28-space indentation (`E1`) and clean 0-space indentation (`E2`). |
| 10 | **Bidirectional Matching & Reciprocal Siamese Merger** | **Faithfully reproduced** | Runs $O_1 \to O_2$ (`Entity1, Entity2`) and $O_2 \to O_1$ (`Entity2, Entity1`), then computes inner join `pd.merge(df_source, df_target, on=['Entity1', 'Entity2'])`. | `1_Source/matching/merger.py`: runs $O_1 \to O_2$ and $O_2 \to O_1$, normalizes pair orientation to `(source_uri, target_uri)`, and computes exact set intersection $\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$. |
| 11 | **Local Ollama $\le 4\text{B}$ Parameter Guard & Desktop GUI** | **Reimplemented with a different method** (New Extension) | Upstream repository provides a Flask web wrapper (`web_app.py`) without parameter-count verification or standalone desktop packaging. | Implemented `/api/show` GGUF parameter-count enforcement (`STRICT_4B_MAX_PARAMETERS = 4_000_000_000`) in `1_Source/llm/model_validator.py` and a 10-screen native **PySide6 Desktop Workbench** packaged as a standalone executable via **PyInstaller**. |
| 12 | **OAEI Anatomy & MSE Benchmark Tracks** | **Not experimentally verified** | Evaluated in the PVLDB paper via `generate_anatomy_mse_benchmark.py`. | Pipeline code supports `o1_is_code` / `o2_is_code` and `DEFAULT_EXCLUSIONS` for Anatomy/MSE, but the raw Anatomy and MSE ontology XML files are not included in the local workspace archive and were therefore not experimentally verified. |

---

## 12. Limitations

1. **Single-Track Empirical Benchmark Coverage (`CMT–ConfOf`):** Only the 162-entity OAEI Conference `CMT–ConfOf` dataset ($16$ gold equivalences) is present in `3_Dataset/` and `original_repo/data/`. The OAEI Anatomy and MSE tracks from the original paper are absent from the local workspace and could not be evaluated under the strict no-network/no-Git constraint.
2. **Directional Prompt Asymmetry in $\le 4\text{B}$ Models:** While `nomic-embed-text` (`768`-dim) + RRF + Reciprocal Merger recovers $7/16$ gold pairs ($F_1 = 48.28\%$ at $\tau = 0.875$) without LLM validation and `qwen2.5:3b` ($3.09\text{B}$) validates $6/16$ gold pairs ($F_1 = 48.00\%$ at $\tau = 0.85$) in the $O_1 \to O_2$ direction, the reverse $O_2 \to O_1$ validation prompt rejects `confOf:Member_PC` $\to$ `cmt:ProgramCommitteeMember` and `confOf:hasTitle` $\to$ `cmt:title`. Consequently, the symmetric Siamese intersection drops final validated recall to $25.00\%$ ($\text{TP}=4, \text{FP}=2, F_1 = 36.36\%$).
3. **High Token & Latency Cost of Small Reasoning Models (`deepseek-r1:1.5b`):** In `E7`, `deepseek-r1:1.5b` ($1.78\text{B}$) generated $61,555$ completion tokens across $49$ validation calls ($10.7\times$ more tokens per call and $4.88\times$ slower runtime than `qwen2.5:3b`) without improving final merged $F_1$ ($36.36\%$).
4. **External Service Prerequisite for Live Execution:** The standalone PyInstaller executable (`dist/AgentOM/AgentOM`) bundles Python 3.13, PySide6, and all application modules, but executing a *new* live matching run requires the host's local PostgreSQL (`127.0.0.1:5432`) and local Ollama (`127.0.0.1:11434`) services to be running.

---

## 13. Conclusions

1. **Software Modernisation & Verification Complete:** The Agent-OM architecture has been cleanly modularized under Python 3.13.16 (`1_Source/`), verified by **`133/133` passing automated tests** (`105` unit, `21` integration, `7` GUI), packaged into a standalone 10-screen PySide6 desktop application (`dist/AgentOM/AgentOM --self-test` exit code `0`), and verified to preserve all 30 historical replication outputs (`SHA-256 = eb28e7a7...`, `"identical": true`).
2. **Algorithmic Parity Remediation Outperforms Upstream `Agent-OM-Lite`:** Fixing the nine source-level discrepancies (`DISC-01` through `DISC-09`) raised local `llama3:8b` (`4096`-dim) performance on `CMT–ConfOf` from the upstream repository's $F_1 = 34.78\%$ (reported) / $35.71\%$ (executed in `Exp B`) to **$F_1 = 44.45\%$ ($P = 54.55\%, R = 37.50\%$)** in `Exp C`.
3. **Strict $\le 4\text{B}$ Local Adaptation Matches Upstream Lite & Exposes Key Architectural Insights:**
   - Enforcing `general.parameter_count <= 4_000_000_000` via `/api/show` proved that `qwen3.5:4b` ($4.54\text{B}$) exceeds the $4\text{B}$ limit, whereas `qwen2.5:3b` ($3.09\text{B}$) and `deepseek-r1:1.5b` ($1.78\text{B}$) are strictly compliant.
   - Pairing `qwen2.5:3b` ($3.09\text{B}$) with dedicated `nomic-embed-text` (`137M`, `768`-dim) achieves **$F_1 = 36.36\%$ ($P = 66.67\%, R = 25.00\%$)** with $100\%$ determinism across 3 repeated runs (`E1_run1`..`run3`), outperforming the upstream `Agent-OM-Lite` (`llama3:8b`) baseline ($34.78\%$ / $35.71\%$) using **$61\%$ fewer parameters**.
   - Deterministic Python tool routing (`E3`) is **$50.6\times$ faster** than upstream's LLM JSON tool routing (`E4`) with zero difference in alignment accuracy.

---

## 14. Future Work

1. **Canonical Alphabetical Entity Ordering in Validation Prompts:** Sort the candidate pair `(Entity_A, Entity_B)` alphabetically inside the equivalence prompt before querying $\le 4\text{B}$ validators so that $O_1 \to O_2$ and $O_2 \to O_1$ present identical token sequences, preserving the $F_1 = 48.00\%$ (`TP=6`) alignment achieved in $O_1 \to O_2$ validation (`E6` `4_s2t_with_validation`) through the reciprocal merger.
2. **Confidence-Weighted Reciprocal Merging:** Combine high-similarity RRF reciprocal agreements ($\tau \ge 0.875$, where `nomic-embed-text` alone achieves $F_1 = 48.28\%, \text{TP}=7$) with directional LLM validation confidence rather than hard boolean elimination.
3. **Multi-Track OAEI Evaluation:** Provision the raw OAEI Anatomy (`mouse–human`) and MSE ontology files into `3_Dataset/original/` to evaluate the $\le 4\text{B}$ separated-embedding architecture on large-scale biomedical knowledge graphs.
