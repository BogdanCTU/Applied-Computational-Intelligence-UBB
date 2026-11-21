# Academic Presentation Outline — Agent-OM Scientific Replication & Local $\le 4\text{B}$ LLM Adaptation

**Presentation Title:** Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation, and Local $\le 4\text{B}$ LLM Adaptation  
**Target Duration:** 15–20 Minutes (12 Slides + 5-Minute Live Desktop Workbench Demonstration + Q&A)  
**Course:** Applied Computational Intelligence / Application of Computational Linguistics (Babeș-Bolyai University)

---

## Slide-by-Slide Presentation Structure

### Slide 1 — Title & Research Context (1 min)
- **Title:** Scientific Replication and Local $\le 4\text{B}$ LLM Adaptation of *Agent-OM: Leveraging LLM Agents for Ontology Matching*
- **Original Paper:** Qiang, Wang, & Taylor (PVLDB 2025, Vol. 18, Issue 3, pp. 516–529; arXiv:`2312.00326`; GitHub: `qzc438/ontology-llm`).
- **Replication Objectives:**
  1. Audit and reproduce the reference Agent-OM architecture 100% locally under Python 3.13.
  2. Replace proprietary cloud APIs (`GPT-4o`, `text-embedding-ada-002`) with local loopback inference (`Ollama` + `PostgreSQL 16 / pgvector`).
  3. Design, enforce, and benchmark a strict **$\le 4\text{B}$ total parameter** local model architecture.
  4. Package a reproducible 10-screen **PySide6 Desktop Workbench**.

---

### Slide 2 — The Ontology Matching Problem & Why LLMs Struggle (1.5 min)
- **Problem Definition:** Given source ontology $O_1$ and target ontology $O_2$, identify equivalence correspondences $\mathcal{A} = \{(e_1, e_2, \equiv)\}$ between classes and properties.
- **Why Classical Matchers Fail:** Lexical heuristics miss structural and domain paraphrases (e.g., `cmt:ProgramCommitteeMember` $\equiv$ `confOf:Member_PC`, `cmt:writePaper` $\equiv$ `confOf:writes`).
- **Why Naive Zero-Shot LLMs Fail:**
  - Passing two full ontologies into one prompt scales quadratically ($O(|E_1| \times |E_2|)$), overflowing context windows.
  - Small open-weight LLMs suffer from positional bias and high false-positive rates when asked to match raw URI lists.

---

### Slide 3 — Original Agent-OM Siamese Architecture (2 min)
- **Two-Agent Decomposition:**
  1. **Retrieval Agent (`om_ontology_to_csv.py` + `om_csv_to_database.py`):**
     - Constructs three complementary views for every entity:
       - *Syntactic ($T_{\text{syn}}$):* Normalized URI/label string (`camelCase` $\to$ words, acronym repair, US spelling via `breame`).
       - *Lexical ($T_{\text{lex}}$):* LLM-generated domain definition + RDF annotation comments.
       - *Semantic ($T_{\text{sem}}$):* LLM-verbalized 1-hop RDF structural subgraph (parents, domain, range, disjoints, blank-node restrictions).
     - Chunks and embeds all three views into **PostgreSQL + `pgvector`**.
  2. **Matching Agent (`om_database_matching.py`):**
     - Retrieves top-$k=3$ candidates per view with cosine similarity $\ge \tau$ ($\tau=0.90$).
     - Fuses rankings via **Reciprocal Rank Fusion (RRF, $k_0=0$)**: $\text{RRF}(c \mid q) = \sum_{m} \frac{1}{\text{rank}_m(c)}$.
     - Validates candidates group-by-group in both directions ($O_1 \to O_2$ and $O_2 \to O_1$) with exact-name bypass + zero-shot Yes/No prompt.
     - Intersects directional predictions via the **Reciprocal Siamese Merger** ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$).

---

### Slide 4 — Source-Level Forensic Audit & Nine Resolved Discrepancies (1.5 min)
- Audited all 22 architectural components of `original_repo/` (`v1.0.0` PVLDB release vs. `v1.0.2`/`HEAD`).
- Identified and resolved 9 implementation discrepancies (`DISC-01` to `DISC-09`), notably:
  - **`DISC-01` (Empty Semantic Placeholder Vectors):** Upstream stripped `"Information is not available."` to `0` chunks; embedding the placeholder text created artificial `1.0000` cosine similarity matches between unrelated isolated entities.
  - **`DISC-03` (Combined Alphabetical Property Sorting):** Sorting `ObjectProperty` and `DatatypeProperty` together restored 100% (`162/162`) 3-digit `entity_id` parity and deterministic RRF tie-breaking.
  - **`DISC-04` (`LlamaEmbeddingBridge`):** Built a local 4096-dim mean-pooled GGUF embedding bridge for `llama3:8b` on modern Ollama (`0.40.16`).

---

### Slide 5 — Local $\le 4\text{B}$ LLM Architecture & The `:4b` Parameter Trap (2 min)
- **Strict Role Separation (`1_Source/llm/`):**
  - Decoupled `LocalChatProvider` (`/api/chat`) from `LocalEmbeddingProvider` (`/api/embed`).
  - Why? Causal chat LLMs (`llama3:8b`, `qwen2.5:3b`) are not trained with a contrastive cosine objective; dedicated bi-encoders (`nomic-embed-text` at `137M` params, `768`-dim; `mxbai-embed-large` at `334M` params, `1024`-dim) produce far cleaner cosine similarity neighborhoods.
- **Runtime Parameter Verification (`POST /api/show` $\to$ `general.parameter_count`):**
  - Enforced `STRICT_4B_MAX_PARAMETERS = 4_000_000_000` ($4.00\text{B}$).
  - **Discovery:** `qwen3.5:4b` actually contains **$4,538,986,496$ ($4.54\text{B}$) parameters** ($+539\text{M}$ over the ceiling) and is automatically blocked by `ModelValidator` in strict $\le 4\text{B}$ profiles!
  - **Verified Compliant Models:** `qwen2.5:3b` (**$3,085,938,688$ params = $3.09\text{B}$**) and `deepseek-r1:1.5b` (**$1,777,088,000$ params = $1.78\text{B}$**).

---

### Slide 6 — Experimental Methodology & Benchmark Scope (1 min)
- **Benchmark Dataset:** OAEI Conference Track — `CMT–ConfOf` (`88` CMT entities, `74` ConfOf entities, `162` total entities, `16` gold-standard equivalences).
- **Benchmark Scope Transparency:** Only `CMT–ConfOf` is present in the local repository archive (`3_Dataset/` and `original_repo/data/`). The OAEI Anatomy and MSE tracks from the original paper are absent from disk and documented as out-of-archive limitations.
- **Database Isolation:** Protected historical DB `agent_om_local` (`162/162/206/258` rows, write-guarded) + isolated databases `agent_om_adapted` (`768`-d), `agent_om_4b_baseline` (`768`-d), and `agent_om_4b_mxbai` (`1024`-d).

---

### Slide 7 — Consolidated Results: Original Paper vs. Upstream Repo vs. Local 8B vs. Local $\le 4\text{B}$ (2.5 min)
- Present the 4-tier results table on `CMT–ConfOf`:
  1. **Original Paper / Cloud `GPT-4o` + `ada-002` (`1536`-d):**
     - Reported in paper / `result-reference.csv`: `TP=6, FP=3, FN=10` $\rightarrow$ $P=66.67\%, R=37.50\%, F_1=48.00\%$.
     - Recalculated from committed `predict.csv` (`8` pairs): `TP=6, FP=2, FN=10` $\rightarrow$ $P=75.00\%, R=37.50\%, F_1=50.00\%$.
  2. **Official Repo `Agent-OM-Lite` (`llama3:8b` `4096`-d):**
     - Reported in `result-om-2025-test.csv`: `TP=4, FP=3, FN=12` $\rightarrow$ $P=57.14\%, R=25.00\%, F_1=34.78\%$.
     - Isolated local execution (`Exp B`): `TP=5, FP=7, FN=11` $\rightarrow$ $P=41.67\%, R=31.25\%, F_1=35.71\%$ (`2,584s`, `1,627` LLM calls).
  3. **Repaired Local 8B Parity (`Exp C`, `llama3:8b` `4096`-d):**
     - Runs 2–3: `TP=6, FP=5, FN=10` $\rightarrow$ **$P=54.55\%, R=37.50\%, F_1=44.45\%$** (`+9.67%` $F_1$ over upstream table!).
  4. **Strict $\le 4\text{B}$ Local Adaptation (`Phase 6 E1–E7`, `qwen2.5:3b` [$3.09\text{B}$] + `nomic-embed-text` [$768$-d]):**
     - Final Validated + Merged (`E1` R1–R3, `E2`, `E5`, `E7`): `TP=4, FP=2, FN=12` $\rightarrow$ **$P=66.67\%, R=25.00\%, F_1=36.36\%$** ($100\%$ deterministic across 3 runs; outperforms upstream `llama3:8b` $34.78\%$ / $35.71\%$ with $61\%$ fewer parameters).
     - Directional $O_1 \to O_2$ Validated at $\tau=0.85$ (`E6a` `4_s2t_val`): `TP=6, FP=3, FN=10` $\rightarrow$ **$P=66.67\%, R=37.50\%, F_1=48.00\%$** (matches paper's `GPT-4o` $48.00\%$!).
     - Pure `nomic-embed-text` RRF + Reciprocal Merger without LLM validation at $\tau=0.875$ (`E6b` `3_merge`): `TP=7, FP=6, FN=9` $\rightarrow$ **$P=53.85\%, R=43.75\%, F_1=48.28\%$** in `31.88s`!

---

### Slide 8 — Phase 6 Ablation Insights (`E1` through `E7`) (2 min)
- **Determinism (`E1` Run 1, 2, 3):** $\sigma_{F_1} = 0.00\%$ (`TP=4, FP=2, FN=12`, identical `59` LLM calls and `12` exact-name bypasses).
- **Prompt Formatting (`E1` 28-space vs. `E2` Clean):** Identical $F_1 = 36.36\%$, saving $6.17\%$ prompt tokens.
- **Tool Routing (`E3` Deterministic vs. `E4` LLM JSON Router):** Identical accuracy, **$50.6\times$ faster** (`0.57s` vs `28.73s`).
- **Embedding Model (`E2` `nomic-embed-text` `768`-d vs. `E5` `mxbai-embed-large` `1024`-d):** `nomic-embed-text` embeds `833` chunks **$2.72\times$ faster** (`31.88s` vs `86.69s`) with higher unvalidated $F_1$ ($41.67\%$ vs $30.77\%$), while both converge to $F_1 = 36.36\%$ after LLM validation + merging.
- **Reasoning Model (`E7` `deepseek-r1:1.5b` [$1.78\text{B}$]):** Emits $10.7\times$ more completion tokens (`61,555` tokens, `2,392s`) and accepts more directional candidates, which the Reciprocal Merger filters to the same 6 symmetric pairs ($F_1 = 36.36\%$).

---

### Slide 9 — Root Cause Analysis: Why Local $F_1$ Differs from Cloud `GPT-4o` (1.5 min)
- **Stage Attrition Breakdown (`1_s2t_no_val` $\to$ `6_final_merged`):**
  - Retrieval is **not** the bottleneck: `nomic-embed-text` retrieves $7/16$ gold pairs in `3_merge_without_validation` at $\tau=0.875$ ($F_1=48.28\%$), compared to $7/16$ for `GPT-4o + ada-002` ($F_1=42.42\%$).
  - The bottleneck is **directional prompt-order asymmetry in sub-4B validators**:
    - When asked `"Is cmt:ProgramCommitteeMember equivalent to confOf:Member_PC?"` ($O_1 \to O_2$), `qwen2.5:3b` answers **`"yes"`** (`TP=6`, $F_1=48.00\%$).
    - When asked `"Is confOf:Member_PC equivalent to cmt:ProgramCommitteeMember?"` ($O_2 \to O_1$), `qwen2.5:3b` answers **`"no"`** due to the abbreviated token `Member_PC` appearing in the subject position.
    - The strict intersection $\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$ drops any pair validated in only one direction (`TP` drops $6 \to 4$).

---

### Slide 10 — Software Architecture, 133-Test Suite & Standalone PySide6 Workbench (1 min)
- **Clean 6-Directory Project Structure:** `1_Source/`, `2_Tests/`, `3_Dataset/`, `4_Temporary/`, `5_Results/`, `6_Documentation/`.
- **Verification Metrics:**
  - `133/133` passing automated tests (`105` unit, `21` integration with live PostgreSQL + Ollama, `7` GUI tests).
  - Standalone `--onedir` desktop bundle (`dist/AgentOM/AgentOM`) verified via headless `--self-test`.
  - `30/30` historical artifacts verified byte-identical (`SHA-256 = eb28e7a7...`).

---

### Slide 11 — Live Demonstration Transition (5 min)
- Transition to the live demonstration following [`DEMO_GUIDE.md`](DEMO_GUIDE.md):
  1. Show live environment diagnostics (`PostgreSQL 16.16 + pgvector 0.8.0` and `Ollama 0.40.16` with $\le 4\text{B}$ compliance badges).
  2. Inspect the 7 configuration profiles and demonstrate the `qwen3.5:4b` ($4.54\text{B}$) parameter guard.
  3. Run a live 4-entity matching experiment and inspect the 6-stage attrition table, TP/FP/FN alignments, and high-DPI charts.

---

### Slide 12 — Conclusions, Limitations & Future Work (1 min)
- **Reproduction Verdict:**
  - **Software Implementation:** Complete (`100%`).
  - **Local Ollama $\le 4\text{B}$ Adaptation:** Complete (`100%`).
  - **Scientific Reproduction Status:** **Partial Scientific Reproduction** (Full architectural reproduction and deep ablation on OAEI `CMT–ConfOf`; OAEI `Anatomy` and `MSE` tracks not evaluated due to absence of raw ontology XMLs in the local workspace).
- **Future Work:** Canonical alphabetical prompt entity ordering (eliminating directional flip noise to retain $F_1 = 48.00\%$) and multi-track biomedical evaluation.
