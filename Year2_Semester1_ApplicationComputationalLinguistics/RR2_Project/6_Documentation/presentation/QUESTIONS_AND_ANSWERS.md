# Academic Defense Questions and Answers — Agent-OM

**Project:** Agent-OM: Leveraging LLM Agents for Ontology Matching — Scientific Replication, Python 3.13 Modernisation & Local $\le 4\text{B}$ LLM Adaptation  
**Purpose:** Prepared, evidence-backed answers for university committee questions during the project defense.

---

## Q1: Why were local LLMs (via Ollama) selected instead of using the original paper's cloud APIs (`GPT-4o` and `text-embedding-ada-002`)?

**Answer:**  
Three scientific and engineering principles motivated local-only execution:
1. **Scientific Reproducibility & Longitudinal Stability:** Commercial cloud APIs (`gpt-4o-2024-05-13`) undergo silent weight updates, rate-limiting, and eventual deprecation, making cloud-based ontology matching experiments non-reproducible over time. By contrast, local GGUF models served via Ollama (`http://127.0.0.1:11434`) with pinned SHA-256 digests and deterministic decoding parameters (`temperature=0.0, seed=42, top_k=1, top_p=1.0, repeat_penalty=1.0`) produced **$100\%$ identical predictions and token counts** across repeated runs (`E1_run1`, `E1_run2`, `E1_run3`: $F_1 = 36.36\% \pm 0.00\%$).
2. **Data Privacy & Sovereign Knowledge Graphs:** In real-world enterprise, healthcare, and government ontology alignment tasks, proprietary schemas cannot be transmitted to external cloud endpoints. Our implementation enforces a strict loopback guard (`127.0.0.1` / `localhost`) at the socket and client level (`1_Source/llm/ollama_client.py`).
3. **Zero Marginal Cost for High-Call-Volume Agent Workflows:** Full-pipeline Agent-OM execution on a single 162-entity benchmark pair requires over $500$ LLM invocations ($1,627$ calls when upstream's LLM JSON tool-router is active). Local inference on consumer hardware (16 GB unified memory) runs at zero API cost.

---

## Q2: Why were models strictly below 4 billion ($\le 4\text{B}$) parameters used, and how did you verify compliance?

**Answer:**  
1. **Consumer Hardware Accessibility:** In the original paper, the open-weight variant (*Agent-OM-Lite*) required `llama3:8b` ($8.03\text{B}$ parameters) used simultaneously for chat and 4096-dimensional embeddings, which strains standard 8–16 GB student and edge laptops. Investigating strictly $\le 4.0\text{B}$ parameter models (`qwen2.5:3b` at $3.09\text{B}$ and `deepseek-r1:1.5b` at $1.78\text{B}$) tests whether lightweight local agents can perform ontology matching within a 2–3 GB VRAM footprint.
2. **Authoritative Metadata Verification vs. The `:4b` Tag Trap:** Model release tags are often rounded approximations. Rather than trusting string tags, our `ModelValidator` (`1_Source/llm/model_validator.py`) queries Ollama's `POST /api/show` endpoint and inspects `model_info["general.parameter_count"]` against the hard ceiling `STRICT_4B_MAX_PARAMETERS = 4_000_000_000`.
3. **Empirical Discovery:** This check revealed that `qwen3.5:4b` actually contains **$4,538,986,496$ ($4.54\text{B}$) parameters** ($+538.99\text{M}$ over the $4.0\text{B}$ cap). Our validator automatically blocks `qwen3.5:4b` with `ParameterLimitExceededError` in all strict $\le 4\text{B}$ profiles, ensuring complete scientific integrity.

---

## Q3: Why are separate dedicated embedding models (`nomic-embed-text`, `mxbai-embed-large`) necessary instead of using the chat LLM for embeddings?

**Answer:**  
1. **Architectural Mismatch of Causal Decoder Embeddings:** In the upstream repository's `Agent-OM-Lite` configuration, `llama3:8b` is used both as the generative chat model and as a 4096-dimensional embedding model. However, decoder-only causal LLMs are trained with an autoregressive next-token prediction objective, not a contrastive bi-encoder cosine similarity objective. As a result, their hidden-state representations are anisotropic (concentrated in a narrow cone), producing noisy cosine similarities ($\ge 0.90$) between unrelated entities (`45` unvalidated $O_1 \to O_2$ false positives in `Exp C`).
2. **Superior Precision, Speed, and Storage of Contrastive Bi-Encoders:** Dedicated embedding models like `nomic-embed-text` ($136.7\text{M}$ parameters, `768`-dim) and `mxbai-embed-large` ($334.1\text{M}$ parameters, `1024`-dim) are trained specifically with contrastive infoNCE loss so that semantically equivalent descriptions map to nearby unit vectors:
   - `nomic-embed-text` embeds all `833` CMT–ConfOf chunks in **`31.88s` (`37.27 ms/chunk`)** using **$5.3\times$ less vector storage** than 4096-dim `llama3:8b` vectors.
   - At $\tau = 0.875$, `nomic-embed-text` + RRF + Reciprocal Merger *alone* (with zero LLM validation calls) achieves **$F_1 = 48.28\%$ ($P = 53.85\%, R = 43.75\%, \text{TP}=7, \text{FP}=6$)**, outperforming the full validated 8B pipeline!

---

## Q4: How does ontology matching work in Agent-OM end-to-end?

**Answer:**  
Given a source ontology $O_1$ (e.g., `CMT`, $88$ entities) and a target ontology $O_2$ (e.g., `ConfOf`, $74$ entities), Agent-OM finds equivalence pairs $(e_1, e_2)$ where $\text{type}(e_1) = \text{type}(e_2) \in \{\text{Class}, \text{Property}\}$ through two cooperating agents:
1. **Phase 1 — Retrieval Agent & Hybrid Memory Ingestion:**
   - Parses both OWL/RDF graphs and extracts every class and property.
   - Generates three text views per entity: **Syntactic** (normalized label), **Lexical** (LLM domain definition + RDF comments), and **Semantic** (LLM natural-language verbalization of 1-hop RDF triples and OWL blank-node restrictions).
   - Splits views into 500-character chunks and embeds them into three `pgvector` tables (`syntactic_matching`, `lexical_matching`, `semantic_matching`) linked to `ontology_matching`.
2. **Phase 2 — Matching Agent & Reciprocal Siamese Merger:**
   - Performs candidate retrieval, RRF ranking, and score-group LLM validation in **both** directions ($O_1 \to O_2$ and $O_2 \to O_1$).
   - Intersects the two directional alignment sets ($\mathcal{A}_{\text{final}} = \mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) so that only mutually confirmed correspondences are emitted.

---

## Q5: How does candidate retrieval work across the three views?

**Answer:**  
For a query entity $q$ (for instance, `http://cmt#ProgramCommitteeMember`, which is a `Source` `Class`):
1. The Retrieval Agent looks up $q$'s text texts $T_{\text{syn}}(q), T_{\text{lex}}(q), T_{\text{sem}}(q)$ and embeds each into a query vector $\mathbf{v}_m(q)$.
2. For each modality $m \in \{\text{syntactic}, \text{lexical}, \text{semantic}\}$, it queries the corresponding PostgreSQL `pgvector` table for chunks belonging to the **opposing ontology** (`Target`) and the **same entity type** (`Class`) whose cosine similarity satisfies:
   $$\text{sim}(\mathbf{u}, \mathbf{v}_m(q)) = 1 - (\mathbf{u} \Leftrightarrow \mathbf{v}_m(q)) \ge \tau$$
3. It orders matching chunks by descending cosine similarity (`LIMIT 50`) and deduplicates by `entity_id` (keeping the highest-scoring chunk per candidate entity) to produce up to $\text{top\_k} = 3$ ranked candidates $R_m(q) = [c_1, c_2, c_3]$ for that view. If no candidate meets $\tau$, the list contains the sentinel `["Entity-Dummy"]`.

---

## Q6: How does Reciprocal Rank Fusion (RRF) work in Agent-OM?

**Answer:**  
Each query entity $q$ receives three ranked candidate lists $R_{\text{syn}}(q), R_{\text{lex}}(q), R_{\text{sem}}(q)$, each of length at most $\text{top\_k} = 3$. Agent-OM fuses them using **unsmoothed Reciprocal Rank Fusion** with smoothing constant $k_0 = 0$:
$$\text{RRF}(c \mid q) = \sum_{m \in \{\text{syn}, \text{lex}, \text{sem}\}} \mathbb{I}[c \in R_m(q) \land c \ne \text{Entity-Dummy}] \cdot \frac{1}{\text{rank}_m(c)}$$
where $\text{rank}_m(c) \in \{1, 2, 3\}$ is the 1-based position of candidate $c$ in list $R_m(q)$.
- For example, a candidate ranked 1st in all three views receives $\text{RRF} = 1/1 + 1/1 + 1/1 = 3.0$.
- Candidates are grouped by their exact RRF score in descending order: $[(s_1, G_1), (s_2, G_2), \dots]$. Any ties within a score group $G_j$ are ordered deterministically by their 3-digit `entity_id` (`001-...` to `162-...`).

---

## Q7: How does the LLM validate candidate correspondences, and when is the LLM bypassed?

**Answer:**  
For a query entity $q$, the Matching Agent iterates over the top RRF score groups $G_1, G_2, \dots$ (up to $\text{top\_k} = 3$ groups):
1. **Exact-Name Bypass (`check_name_matching`):** Before calling the LLM for a candidate $c \in G_j$, the validator compares their normalized syntactic names:
   $$\text{cleaning}(\text{name}(q)).\text{casefold}() == \text{cleaning}(\text{name}(c)).\text{casefold}()$$
   If they are identical (e.g., `author == author`, `conference == conference`, `administrator == administrator`), the validator immediately returns `True` (`bypass_used = True`), saving an LLM call (`12` directional pairs on `CMT–ConfOf`).
2. **Zero-Shot Equivalence Prompt:** If the names are not identical (e.g., `program committee member` vs. `member pc`), the LLM is prompted:
   > *"Wait a minute, is {query_name} equivalent to {candidate_name} in the context of {context}? Think step-by-step and finish your answer with 'Yes, they are equivalent.' or 'No, they are not equivalent.'"*
   The response is parsed via case-insensitive word-boundary regex `r"\b(?:yes|no)\b"` (taking the final Yes/No decision).
3. **Score-Group Early Stopping:** If **at least one** candidate in score group $G_j$ is accepted (via bypass or LLM `"yes"`), the loop finishes evaluating the remaining candidates in $G_j$ and then **breaks immediately**, never evaluating lower-scoring groups $G_{j+1}, \dots$.

---

## Q8: Why does the local $F_1$-score differ from the original paper's reported `GPT-4o` $F_1$-score?

**Answer:**  
We can pinpoint the exact reason by comparing our 6-stage attrition tables (`5_Results/comparisons/phase5_6variants_all_experiments.csv` and `phase6_E6_qwen25_3b_tau085/metrics_6variants.csv`):
1. **Paper vs. Committed `GPT-4o` CSV ($48.00\%$ vs. $50.00\%$):** The paper / `result-reference.csv` reports $F_1 = 48.00\%$ (`TP=6, FP=3, FN=10`), whereas recalculating directly from the committed `predict.csv` (`8` URI pairs) yields $F_1 = 50.00\%$ (`TP=6, FP=2, FN=10`) because the 9-line CSV includes 1 header line.
2. **Local 8B Parity (`Exp C`, $F_1 = 44.45\%$) vs. Upstream `Agent-OM-Lite` (`llama3:8b`, $F_1 = 34.78\%$ / $35.71\%$):** Our local `llama3:8b` parity pipeline actually **improves** upon the upstream repository's `llama3:8b` score by **$+9.67\%$ $F_1$** (`TP=6, FP=5` vs `TP=4, FP=3`) because we fixed empty placeholder chunk embedding (`DISC-01`) and property ID sorting (`DISC-03`). The remaining difference between local `llama3:8b` ($44.45\%$, `TP=6, FP=5`) and cloud `GPT-4o` ($50.00\%$, `TP=6, FP=2`) is purely `3` extra false positives accepted by `llama3:8b` (`TP=6` is identical!).
3. **Strict $\le 4\text{B}$ (`qwen2.5:3b`, $F_1 = 36.36\%$ Final Merged vs. $F_1 = 48.00\%$ S2T Validated):**
   - At $\tau = 0.85$ (`E6a`), `qwen2.5:3b` achieves **$F_1 = 48.00\%$ (`TP=6, FP=3`)** in $O_1 \to O_2$ validation (`4_s2t_with_validation`), matching the paper's reported `GPT-4o` $F_1$ ($48.00\%$).
   - However, in the reverse $O_2 \to O_1$ direction (`5_t2s_with_validation`), when the abbreviated target name (`confOf:Member_PC` or `confOf:hasTitle`) appears first in the prompt, the $3.09\text{B}$ model conservatively outputs `"no"`. The bidirectional intersection ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) therefore filters out those 2 asymmetric TPs, leaving `TP=4, FP=2` ($P=66.67\%, R=25.00\%, F_1=36.36\%$).

---

## Q9: What has been reproduced from the original paper, and what has not been reproduced?

**Answer:**  
- **What HAS Been Reproduced and Verified:**
  1. **Complete Agent-OM Siamese Architecture:** Three-view representation extraction (`syntactic`, `lexical`, `semantic`), `pgvector` cosine retrieval, unsmoothed RRF ($k_0=0$), score-group validation with exact-name bypass and early stopping, and the Reciprocal Siamese Merger ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$).
  2. **OAEI `CMT–ConfOf` Benchmark Reproduction:** Full local reproduction of `Agent-OM-Lite` (`llama3:8b` `4096`-dim), improving $F_1$ from $34.78\%$ (reported) / $35.71\%$ (raw upstream execution) to $44.45\%$ after parity bug fixes.
  3. **Local $\le 4\text{B}$ Adaptation & Ablation Suite:** 10 controlled experiments (`E1`–`E7`) proving $100\%$ deterministic repeatability (`E1` $\times 3$), $50.6\times$ speedup from deterministic tool routing (`E3` vs. `E4`), embedding comparison (`nomic-embed-text` `768`-d vs. `mxbai-embed-large` `1024`-d), threshold sweep ($\tau \in \{0.85, 0.875, 0.90\}$), and reasoning model evaluation (`deepseek-r1:1.5b`).
- **What Has NOT Been Reproduced (Explicit Limitations):**
  1. **Cloud Commercial Model Runs (`GPT-4o`, `Claude-3.5`, `Gemini-1.5`):** Intentionally not executed due to the strict 100% local loopback policy; evaluated via the read-only committed reference artifacts in `original_repo/`.
  2. **OAEI `Anatomy` (`mouse–human`) and `MSE` Tracks:** Not experimentally evaluated because the raw OWL/RDF ontology files for `Anatomy` and `MSE` are not present in the local repository archive (`3_Dataset/` or `original_repo/data/`), and external downloads/Git operations were prohibited. Therefore, the project is accurately classified as a **Partial Scientific Reproduction** (complete on `CMT–ConfOf`, unverified on `Anatomy` and `MSE`).
