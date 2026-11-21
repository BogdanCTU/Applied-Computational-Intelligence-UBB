# Master Scientific Replication & Technical Report
## Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Authors / Replication Researchers:** Applied Computational Intelligence / Application of Computational Linguistics Replication Team  
**Academic Affiliation:** Babeș-Bolyai University (UBB), Faculty of Mathematics and Computer Science — Master's in Applied Computational Intelligence (Year 2, Semester 1, `RR2_Project`)  
**Date:** 2026-11-20  
**Original Publication Cited:**  
Qiang, Zhangcheng; Wang, Weiqing; Taylor, Kerry (2024). *Agent-OM: Leveraging LLM Agents for Ontology Matching*. Proceedings of the VLDB Endowment (PVLDB), Volume 18, Issue 3, Pages 516–529. DOI: `10.14778/3712221.3712222`. arXiv: `2312.00326`.  
**Reference Upstream Repository Cited:** `https://github.com/qzc438/ontology-llm` (Audited Commit `89d0f967a466f17692768e5e370c29b35e5e77e3`, Aggregate SHA-256: `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`).

---

## 1. Executive Summary & Abstract

This report documents the complete end-to-end scientific replication, source-level forensic audit, Python 3.13 modernisation, algorithmic parity remediation, controlled experimental reproduction, and lightweight $\le 4\text{B}$ parameter local LLM adaptation of **Agent-OM** (Qiang et al., PVLDB 2024).

To ensure 100% data privacy, zero external API cost, and strict scientific reproducibility, our implementation replaces proprietary cloud endpoints (`gpt-4o`, `text-embedding-ada-002`) with local-only loopback inference via **Ollama** (`http://127.0.0.1:11434`) and local hybrid vector memory backed by **PostgreSQL 16 + `pgvector` 0.8.0** (`127.0.0.1:5432`). Through a 22-component source-level parity audit and a 17-dimension intermediate output comparator, we identified and resolved nine subtle implementation discrepancies (`DISC-01` through `DISC-09`), increasing local `Agent-OM-Lite` (`llama3:8b`, 4096-dim) alignment performance on the OAEI `CMT–ConfOf` benchmark ($162$ entities, $16$ gold equivalences) from the committed upstream baseline of **$F_1 = 34.78\%$** ($P=57.14\%, R=25.00\%$) and raw isolated upstream execution of **$F_1 = 35.71\%$** ($P=41.67\%, R=31.25\%$) to **$F_1 = 44.45\%$** ($P=54.55\%, R=37.50\%$) with $100\%$ deterministic repeatability across repeated runs.

Furthermore, we designed and implemented a separated local LLM and embedding provider architecture (`src/llm/`) enforcing a strict runtime ceiling of $\le 4,000,000,000$ ($4.0\text{B}$) total parameters verified directly via Ollama `/api/show` metadata (`general.parameter_count`). Using this architecture, we exposed a critical metadata trap (`qwen3.5:4b` actually contains $4,538,986,496$ parameters and was excluded from the strict $\le 4\text{B}$ group) and evaluated two verified $\le 4.0\text{B}$ generative models (`qwen2.5:3b` at $3.09\text{B}$ parameters and `deepseek-r1:1.5b` at $1.78\text{B}$ parameters) paired with two dedicated contrastive embedding models (`nomic-embed-text` at $768$-dim and `mxbai-embed-large` at $1024$-dim) across 12 controlled experiments (`E1`–`E7` plus staged smoke/integration tests). Finally, the entire pipeline is packaged into a 10-screen **PySide6 Desktop Workbench** compiled via **PyInstaller (`--onedir`)** and verified by **`133/133` passing automated tests (`100%`)**.

---

## 2. Introduction & Research Motivation

Ontology Matching (OM) resolves semantic heterogeneity across independently developed knowledge graphs by identifying equivalence correspondences ($\equiv$) between concepts and properties. Traditional OM systems (e.g., AgreementMakerLight, LogMap) rely on handcrafted lexical heuristics and structural graph propagations that struggle with complex domain paraphrases, while early zero-shot LLM approaches suffer from quadratic context-window scaling ($O(|E_1| \times |E_2|)$) and hallucinated correspondences.

**Agent-OM** (Qiang et al., PVLDB 2024) addresses these challenges by decomposing ontology matching into a **Siamese Agent Architecture** consisting of:
1. A **Retrieval Agent** that extracts syntactic, lexical, and structural-semantic representations of every entity in the source ontology $O_1$ and target ontology $O_2$, chunks and embeds them into a hybrid relational-vector database (`PostgreSQL + pgvector`), and retrieves top-$k$ candidate correspondences via Reciprocal Rank Fusion (RRF).
2. A **Matching Agent** that validates candidate correspondences group-by-group in both directions ($O_1 \to O_2$ and $O_2 \to O_1$) using exact-name bypasses and zero-shot LLM equivalence prompts, and intersects the directional alignments via a **Reciprocal Siamese Merger** ($\mathcal{A}_{\text{final}} = \mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$).

### Research Questions Addressed in This Replication
1. **RQ1 (Reproducibility & Parity):** Can the upstream `Agent-OM-Lite` (`llama3:8b`) benchmark on OAEI `CMT–ConfOf` be reproduced 100% locally under Python 3.13, and what source-level discrepancies exist between the published PVLDB methodology and the upstream repository?
2. **RQ2 (Strict $\le 4\text{B}$ Small-Model Viability):** Can strictly verified $\le 4.0\text{B}$ parameter local LLMs (`qwen2.5:3b` [$3.09\text{B}$], `deepseek-r1:1.5b` [$1.78\text{B}$]) paired with dedicated lightweight contrastive embedding models (`nomic-embed-text` [$137\text{M}$, $768$-dim], `mxbai-embed-large` [$334\text{M}$, $1024$-dim]) achieve competitive ontology matching quality on consumer hardware (16 GB unified memory)?
3. **RQ3 (Ablation of Agent-OM Components):** What are the isolated contributions of LLM JSON tool routing vs. deterministic orchestration, 28-space prompt formatting, cosine similarity thresholds ($\tau$), and the Reciprocal Siamese Merger?

---

## 3. Original Agent-OM Architecture & Paper Methodology

Given two ontologies $O_1 = (C_1, P_1, A_1)$ and $O_2 = (C_2, P_2, A_2)$, the alignment task seeks a set of correspondences:
$$\mathcal{A} = \{ (e_1, e_2, \equiv, c) \mid e_1 \in E_1, \, e_2 \in E_2, \, \text{type}(e_1) = \text{type}(e_2) \}$$
where $E_i = C_i \cup P_i$ denotes named classes and properties (excluding `owl:Thing`, blank nodes, and vocabulary exceptions).

### 3.1. Three-View Information Retrieval
For each entity $e \in E_1 \cup E_2$, Agent-OM constructs three textual representations:
1. **Syntactic Representation ($T_{\text{syn}}(e)$):** The local URI name (or `rdfs:label` / `skos:prefLabel` when `ontology_is_code=True`) normalized via acronym repair, `camelCase` $\to$ `snake_case` splitting, lowercasing, and British-to-American spelling normalization (`breame`).
2. **Lexical Representation ($T_{\text{lex}}(e)$):** An LLM-generated domain-contextualized definition prompted with *"Question: What is the meaning of {entity_name}? Context: {context}"* supplemented by any literal annotations across 10 lexical predicates (`rdfs:comment`, `skos:definition`, `skos:note`, etc.).
3. **Semantic Representation ($T_{\text{sem}}(e)$):** An LLM-generated natural language verbalization of the entity's 1-hop structural RDF subgraph across 18 structural predicates (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `owl:disjointWith`, `rdfs:domain`, `rdfs:range`, `owl:equivalentClass`, `skos:broader`, etc.) plus its recursive blank-node restriction closure (`expand_bnode_closure_named`). If an entity has zero structural triples, it receives the sentinel placeholder `"Information is not available."`.

### 3.2. Hybrid Vector Memory & Reciprocal Rank Fusion (RRF)
Each representation $m \in \{\text{syntactic}, \text{lexical}, \text{semantic}\}$ is split using `RecursiveCharacterTextSplitter(separators=[".", "\n"], chunk_size=500, chunk_overlap=0)` and embedded into a dedicated `pgvector` table. For a query entity $q$, each strategy $m$ retrieves up to $\text{top\_k} = 3$ opposing entities of the same entity type whose chunk cosine similarity satisfies:
$$\text{sim}(u, v) = 1 - (u \Leftrightarrow v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2} \ge \tau$$
The three strategy rankings $R_{\text{syn}}(q), R_{\text{lex}}(q), R_{\text{sem}}(q)$ are fused using Reciprocal Rank Fusion with constant $k_0 = 0$:
$$\text{RRF}(c \mid q) = \sum_{m \in \{\text{syn}, \text{lex}, \text{sem}\}} \mathbb{I}[c \in R_m(q)] \cdot \frac{1}{\text{rank}_m(c) + k_0}$$
Candidates are grouped by distinct RRF score in descending order: $[(s_1, G_1), (s_2, G_2), \dots]$, with ties inside each group $G_j$ ordered lexicographically by `entity_id`.

### 3.3. Score-Group Validation & Reciprocal Siamese Merger
For each score group $G_j$ in descending order of RRF score:
- Every candidate $c \in G_j$ is checked for an **exact syntactic name bypass** ($T_{\text{syn}}(q) == T_{\text{syn}}(c)$) or validated via a zero-shot Yes/No equivalence prompt.
- **Score-Group Early Stopping:** If one or more candidates in group $G_j$ are accepted (`True`), the loop terminates immediately after finishing group $G_j$ without evaluating lower-scoring groups $G_{j+1}, \dots$.
- **Reciprocal Siamese Merger:** Only pairs validated in **both** $O_1 \to O_2$ and $O_2 \to O_1$ survive:
$$\mathcal{A}_{\text{final}} = \mathcal{A}_{S \to T}^{\text{val}} \cap \left\{ (e_1, e_2) \mid (e_2, e_1) \in \mathcal{A}_{T \to S}^{\text{val}} \right\}$$

---

## 4. Reference Implementation Analysis & Forensic Baseline (Phase 0)

Our forensic audit inspected the upstream repository `qzc438/ontology-llm` at commit `89d0f967a466f17692768e5e370c29b35e5e77e3` (`8,358` files, aggregate SHA-256 `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`) and the 30 historical experimental outputs (`aggregate_sha256 = eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`).

### 4.1. Upstream Evolution (`v1.0.0` vs. `v1.0.2` vs. `HEAD`)
- **`v1.0.0` / `v1.0.1` (`2025-04-19`):** Extracted only 2 lexical predicates (`rdfs:comment`, `rdf:value`) and 7 semantic predicates without blank-node expansion (`predicate_scope="pvl_v1"`).
- **`v1.0.2` & `HEAD` (`2025-12-09` / `2026-10-01`):** Expanded lexical extraction to 10 predicates, semantic extraction to 18 predicates + blank-node closure (`predicate_scope="head"`), replaced `enchant` with `breame==0.1.2`, and committed `result_csv/result-om-2025-test.csv` reporting `Agent-OM-Lite` (`llama3:8b`) on `CMT–ConfOf` at **$P=57.14\%, R=25.00\%, F_1=34.78\%$**.

---

## 5. Python 3.13 Environment Recovery & Modernisation (Phase 1)

On the macOS 27.0.1 (`Darwin 27.0.0 arm64`, Apple M4, 16 GB unified memory) host, we provisioned an isolated Python 3.13.16 virtual environment (`.venv/`) with `72` locked distributions (`requirements-lock.txt`), avoiding PyTorch entirely:
- **Core Scientific & RDF Stack:** `rdflib==7.6.0`, `breame==0.1.2`, `pandas==3.1.1`, `numpy==2.5.5`.
- **Database & Vector Stack:** `psycopg2-binary==2.9.13`, `asyncpg==0.32.0`, `pgvector==0.5.1`.
- **Local Inference Stack:** `ollama==0.6.3`, `langchain-core==1.8.4`, `langchain-ollama==1.1.0`, `langchain-text-splitters==1.1.3`.
- **GUI, Charts, Testing & Packaging:** `PySide6==6.12.0`, `matplotlib==3.11.2`, `pytest==9.2.0`, `pytest-qt==4.5.0`, `pyinstaller==6.22.3`.
- **Historical SHA-256 Verification (`AC-19`):** Restored baseline `CRLF` line endings on the 30 historical files in `output/` without altering content, achieving `"identical": true` (`eb28e7a70fe1bcdae1b0bb9098df06b6a4c35dc0d2d412f67d072b35c8dc8798`) via `scripts/verify_repo_integrity.py`.

---

## 6. Database Architecture & Local Service Restoration (Phase 2)

1. **PostgreSQL 16.16 + `pgvector` 0.8.0 (`127.0.0.1:5432`):** Installed and bound strictly to loopback (`127.0.0.1:5432`). Compiled `pgvector 0.8.0` natively for `arm64` against `postgresql@16`.
2. **Protected Historical Database (`agent_om_local` — `AC-04`):** Restored the 4 canonical tables (`ontology_matching=162`, `syntactic_matching=162`, `lexical_matching=206`, `semantic_matching=258` rows, `vector(768)`) and verified that `DatabaseManager._assert_writable()` raises `PermissionError` on any attempt to `DROP` or overwrite `agent_om_local`.
3. **Isolated Experiment Databases:** All experimental runs use dedicated isolated databases (`agent_om_test`, `agent_om_adapted`, `agent_om_4b_smoke`, `agent_om_4b_baseline` [`vector(768)`], `agent_om_4b_mxbai` [`vector(1024)`]).
4. **Read-Only Upstream Benchmark Files (`original_repo/`):** Restored the exact CMT–ConfOf ontology and reference alignment files from upstream commit `89d0f967a466f17692768e5e370c29b35e5e77e3` and verified 100% SHA-256 identity against `original_repo_baseline_sha256.json` (`source.xml = e0d55ee6...`, `target.xml = e869c4e7...`, `reference.xml = 3e02f17a...`).

---

## 7. Local $\le 4\text{B}$ LLM & Embedding Architecture (`src/llm/` — Phase 3)

To satisfy `AC-06`, `AC-07`, and `AC-08`, we engineered a dedicated `src/llm/` package separating chat generation from vector embeddings:
- `src/llm/ollama_client.py` (`OllamaClient`): Loopback-enforced REST client (`GET /api/version`, `GET /api/tags`, `GET /api/ps`, `POST /api/show`, `POST /api/chat`, `POST /api/embed`, `keep_alive=0` model unloading) with configurable timeouts, retries, and per-call latency telemetry.
- `src/llm/model_registry.py` (`ModelRegistry`, `ModelMetadata`): Queries `/api/show` to extract authoritative `general.parameter_count`, architecture, quantization, context length, embedding dimension, and capabilities.
- `src/llm/model_validator.py` (`ModelValidator`):
  - Enforces `STRICT_4B_MAX_PARAMETERS = 4_000_000_000` ($4.0\text{B}$) on `general.parameter_count`, raising `ParameterLimitExceededError` when a model exceeds $4.0 \times 10^9$ parameters.
  - Prevents role confusion (`ModelValidationError` if a dedicated embedding model is used for chat or if a causal chat model without embedding capability is used as an embedder).
  - Performs live `/api/embed` vector probes to raise `EmbeddingDimensionMismatchError` if actual vector dimensions differ from the configured database schema.
- `src/llm/chat_provider.py` (`LocalChatProvider`) & `src/llm/embedding_provider.py` (`LocalEmbeddingProvider`): Separated runtime providers with token and latency telemetry.
- **Seven Explicit Configuration Profiles in `src/config.py`:**
  1. `upstream_product_reference` (Read-only GPT-4o + Ada-002 reference; raises `PermissionError` if executed)
  2. `upstream_lite_parity` (`llama3:8b` + `llama3:8b` `4096`-dim via `LlamaBridgeEmbeddings`)
  3. `local_adapted` (`qwen3.5:9b`/`4b` + `nomic-embed-text` `768`-dim)
  4. `experimental` (Customizable ablation profile)
  5. `local_4b_baseline` (`qwen2.5:3b` [$3.09\text{B}$] + `nomic-embed-text` `768`-dim, 28-space prompt, `enforce_4b_limit=True`)
  6. `local_4b_optimized` (`qwen2.5:3b` [$3.09\text{B}$] + `nomic-embed-text` `768`-dim, clean prompt, `enforce_4b_limit=True`)
  7. `local_4b_reasoning` (`deepseek-r1:1.5b` [$1.78\text{B}$] + `nomic-embed-text` `768`-dim, `enforce_4b_limit=True`)

---

## 8. Algorithmic Parity Analysis & Discrepancy Resolution (Phase 4)

All nine discrepancies (`DISC-01` through `DISC-09`) between the original codebase and upstream Agent-OM were resolved and verified by `tests/test_algorithmic_parity.py`:
1. **`DISC-01` (Empty Semantic Chunks):** Stripped `"Information is not available."` prior to chunking (`skip_empty_chunks=True`), producing `0` vector rows for isolated entities instead of identical placeholder vectors that caused false `1.0000` cosine matches.
2. **`DISC-02` (Code-IRI Label Resolution):** Implemented symmetric `rdfs:label` $\to$ `skos:prefLabel` $\to$ `uri_to_name` resolution across `EntityExtractor`, `RetrievalAgent`, and `MatchingAgent`.
3. **`DISC-03` (Combined Alphabetical Property Sorting):** Sorted `ObjectProperty` and `DatatypeProperty` URIs in a single combined alphabetical sequence (`combine_properties_sort=True`), achieving `100.0%` (`162/162`) exact 3-digit `entity_id` parity with upstream `om_ontology_to_csv.py`.
4. **`DISC-04` (Vector Dimension Enforcement & `LlamaEmbeddingBridge`):** Eliminated silent `768`-dim fallback and built `LlamaEmbeddingBridge` for 4096-dim `llama3:8b` embeddings on Ollama $\ge 0.40$.
5. **`DISC-05`–`DISC-07` (Deterministic Sampling & `.env` Harmonization):** Unified `temperature=0.0, seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0, num_ctx=2048, reasoning=False` across all LLM invocations.
6. **`DISC-08`–`DISC-09` (Database Protection & Test Isolation):** Guarded `agent_om_local` against destructive writes and isolated all DB tests to `agent_om_test`.

---

## 9. Multi-Tier Experimental Results: Paper vs. Upstream Repo vs. Local 8B vs. Local $\le 4\text{B}$ (Phases 5 & 6)

Per Section 13 of the Master Prompt, the table below **strictly separates** the four benchmark categories on the OAEI `CMT–ConfOf` dataset (`162` entities, `16` gold equivalences):

| Category | Experiment ID / Source | Generative LLM (Verified Params) | Embedding Model (Dim) | $\tau$ | Pred | TP | FP | FN | Precision (%) | Recall (%) | $F_1$ (%) | Runtime (s) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Original Paper / Upstream Cloud Ref** | PVLDB Table / `result-reference.csv` | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 9 | 6 | 3 | 10 | 66.67% | 37.50% | **48.00%** | — |
| **1. Upstream Committed HEAD CSV** | `alignment/.../predict.csv` | `gpt-4o-2024-05-13` (Cloud) | `text-embedding-ada-002` (`1536`) | `0.90` | 8 | 6 | 2 | 10 | 75.00% | 37.50% | **50.00%** | — |
| **2. Upstream Repo Lite Table** | `result-om-2025-test.csv` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 7 | 4 | 3 | 12 | 57.14% | 25.00% | **34.78%** | — |
| **2. Upstream Repo Executed Locally** | `phase1_cmt_confof_agent_om_lite_v1` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 12 | 5 | 7 | 11 | 41.67% | 31.25% | **35.71%** | 2,584.34 s |
| **3. Local 8B Parity (Run 1)** | `phase5_expC_local_parity_run1` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 12 | 6 | 6 | 10 | 50.00% | 37.50% | **42.86%** | 1,377.25 s |
| **3. Local 8B Parity (Runs 2 & 3)** | `phase5_expC_local_parity_run2..3` | `llama3:8b` (`8.03B`) | `llama3:8b` (`4096`) | `0.90` | 11 | 6 | 5 | 10 | **54.55%** | **37.50%** | **44.45%** | 290.84 s* |
| **3. Local Adapted (Out-of-Limit >4B)** | `phase5_expD_local_adapted_run2` | `qwen3.5:4b` (`4.54B`) | `nomic-embed-text` (`768`) | `0.90` | 6 | 4 | 2 | 12 | 66.67% | 25.00% | **36.36%** | 95.14 s* |
| **4. Strict $\le 4\text{B}$ Adaptation (`E1` R1–3)** | `phase6_E1_qwen25_3b_baseline_run1..3` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 491.61 s* |
| **4. Strict $\le 4\text{B}$ Optimized Prompt (`E2`)** | `phase6_E2_qwen25_3b_optimized_prompt` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 490.09 s* |
| **4. Strict $\le 4\text{B}$ Alt Embedding (`E5`)** | `phase6_E5_qwen25_3b_mxbai_1024d` | **`qwen2.5:3b` (`3.09B`)** | **`mxbai-embed-large` (`1024`)**| `0.90` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 449.46 s* |
| **4. Strict $\le 4\text{B}$ Threshold $\tau=0.85$ (`E6`)**| `phase6_E6_qwen25_3b_tau085` | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.85` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 2,152.88 s* |
| **4. Strict $\le 4\text{B}$ Threshold $\tau=0.85$ (S2T Val)**| `phase6_E6_qwen25_3b_tau085` (`4_s2t`) | **`qwen2.5:3b` (`3.09B`)** | **`nomic-embed-text` (`768`)** | `0.85` | 9 | 6 | 3 | 10 | **66.67%** | **37.50%** | **48.00%** | — |
| **4. Strict $\le 4\text{B}$ Threshold $\tau=0.875$ (RRF Merger)**| `phase6_E6_qwen25_3b_tau0875` (`3_merge`)| **No LLM Val (`0B`)** | **`nomic-embed-text` (`768`)** | `0.875`| 13 | 7 | 6 | 9 | **53.85%** | **43.75%** | **48.28%** | 31.88 s |
| **4. Strict $\le 4\text{B}$ Reasoning (`E7`)** | `phase6_E7_deepseek_r1_15b_full` | **`deepseek-r1:1.5b` (`1.78B`)**| **`nomic-embed-text` (`768`)** | `0.90` | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** | 2,392.25 s* |

*\*Matching-and-validation runtime reusing indexed hybrid-memory tables (`--skip-retrieval`).*

---

## 10. Desktop GUI, Automated Testing & Standalone Packaging (Phases 7, 8, 9)

1. **PySide6 Desktop Workbench (10 Screens, 11 Services):**
   - Integrated all 7 configuration profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`, `local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`) and live `/api/show` parameter count + strict $\le 4.0\text{B}$ compliance badges into `EnvironmentView` and `ConfigurationView`.
2. **Automated Test Suite (`133/133` Passing — Phase 8):**
   - Executed `.venv/bin/python -m pytest tests/ -q` across all 18 test modules (including unit and live integration tests in `tests/test_llm_providers.py` and `tests/test_algorithmic_parity.py`): **`133 passed, 0 failed, 0 errors` (`100%`)**.
3. **Standalone PyInstaller `--onedir` Application (`dist/AgentOM/` — Phase 9):**
   - Built via `agent_om.spec` and verified standalone execution outside the IDE:
     `./dist/AgentOM/AgentOM --self-test --export-bundle-name phase9_exe_verify_bundle` $\rightarrow$ `is_frozen: true`, `screens_verified: 10`, `postgresql_reachable: true`, `ollama_reachable: true`, `datasets_discovered: 1`, `export_bundle.file_count: 8`.

---

## 11. Limitations, Threats to Validity & Future Work

1. **Directional Prompt Asymmetry in Sub-4B Validators:** While `nomic-embed-text` retrieval at $\tau \in [0.85, 0.875]$ recovers $7/16$ gold correspondences ($R=43.75\%, F_1=48.28\%$ without validation) and `qwen2.5:3b` validates $6/16$ in the `Source -> Target` direction ($F_1=48.00\%$), the reverse `Target -> Source` validation rejects `confOf:Member_PC` $\to$ `cmt:ProgramCommitteeMember` and `confOf:hasTitle` $\to$ `cmt:title`. Future work should combine **canonical alphabetical entity ordering inside the validation prompt** (validated in Step 7D to eliminate directional flip noise) with confidence-weighted reciprocal merging.
2. **Complex & Multi-Hop OAEI Tracks:** Our primary evaluation focused on the canonical 162-entity `CMT–ConfOf` benchmark to maintain longitudinal comparability across all historical and new runs. Extending the $\le 4\text{B}$ evaluation to larger biomedical tracks (`Anatomy`, `Bio-ML`) is directly supported by the workbench's `DatasetService` and `o1_is_code`/`o2_is_code` flags.
