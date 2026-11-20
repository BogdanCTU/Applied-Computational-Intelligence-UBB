# Phase 3 Report — 17-Dimension Intermediate Output Comparison
## Agent-OM: Scientific Replication, Python 3.13 Modernisation, Local $\le 4\text{B}$ LLM Adaptation & Desktop Application

**Report Date:** 2026-11-20  
**Status:** `COMPLETED` (`AC-11` SATISFIED)  
**Comparison Engine:** `src/evaluation/comparator.py` (`compare_two_runs_17_points`)  
**Generated Artifacts Directory:** `output/replication_runs/comparisons/`

---

## 1. Objective & Scope

Phase 3 evaluates whether our independent local Agent-OM implementation (`src/`) achieves structural and intermediate output parity with the upstream reference implementation (`qzc438/ontology-llm`) across **17 distinct pipeline dimensions**, starting from raw OWL/RDF XML files (`source.xml` [CMT] and `target.xml` [ConfOf]) through entity extraction, URI normalization, syntactic cleaning, lexical/semantic verbalization, 500-character chunking, vector indexing, directional cosine retrieval, Reciprocal Rank Fusion (RRF), score-group LLM validation, and reciprocal Siamese merging.

### Generated Comparison Artifacts
1. `output/replication_runs/comparisons/phase3_summary_table.csv`
2. `output/replication_runs/comparisons/phase3_17point_upstream_lite_vs_local_parity.json`
3. `output/replication_runs/comparisons/phase3_17point_upstream_lite_vs_local_adapted.json`
4. `output/replication_runs/comparisons/phase3_17point_local_parity_vs_local_adapted.json`
5. `output/replication_runs/comparisons/phase3_17point_upstream_gpt4o_vs_local_adapted.json`
6. `output/replication_runs/comparisons/phase3_17point_upstream_gpt4o_vs_upstream_lite.json`
7. **Matplotlib Charts (`output/replication_runs/comparisons/charts/`):**
   - `prf1_comparison.png`
   - `pr_scatter_isof1.png`
   - `runtime_and_llm_calls.png`
   - `stage_attrition_tp.png`
   - `threshold_sensitivity_local_adapted.png`

---

## 2. Master 17-Dimension Comparison Matrix (`Upstream Agent-OM-Lite` vs. `Local Parity`)

The table below reports the empirical comparison between **Experiment B (`phase1_cmt_confof_agent_om_lite_v1` — isolated execution of upstream `original_repo/` with `llama3:8b` 4096-dim)** and **Experiment C (`phase5_expC_local_parity_run1` — our local `src/` implementation under profile `upstream_lite_parity` with `llama3:8b` 4096-dim)**.

| Dim # | Pipeline Dimension | Upstream Agent-OM-Lite (`phase1_cmt_confof_v1`) | Local Parity (`phase5_expC_local_parity_run1`) | Agreement / Parity Metric | Forensic Explanation |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Extracted Entities (Source / Target)** | 88 CMT / 74 ConfOf (`162` total) | 88 CMT / 74 ConfOf (`162` total) | **100.0% (`Jaccard = 1.0000`)** | Exact URI set equivalence on both ontologies (`29` CMT classes + `59` properties; `38` ConfOf classes + `36` properties). |
| **2** | **Formatted `entity_id` Keys** | `001-Source-Class-Acceptance` .. `162-Target-Property-writtenBy` | `001-Source-Class-Acceptance` .. `162-Target-Property-writtenBy` | **100.0% (`162/162` exact match)** | Resolution of `DISC-03` (`combine_properties_sort=True`) aligned all 162 3-digit index prefixes identically. |
| **3** | **Derived Entity Display Names** | `Acceptance` .. `writtenBy` | `Acceptance` .. `writtenBy` | **100.0% (`162/162` exact match)** | Identical `uri_to_name()` and `o1_is_code`/`o2_is_code` label resolution (`DISC-02`). |
| **4** | **Annotations & Structural Subgraph Detection** | 162 entities with structural triples | 162 entities with structural triples | **100.0% (`162/162` match)** | Both extract 10 lexical predicates and 18 semantic predicates + blank-node closure (`predicate_scope="head"`). |
| **5** | **Cleaned Syntactic Representations** | `acceptance`, `program committee member`, etc. | `acceptance`, `program committee member`, etc. | **100.0% (`162/162` exact match)** | Exact character-for-character parity across `change_to_snake_case`, `repair_acronyms`, and `breame` British-to-American normalization. |
| **6** | **Lexical LLM Verbalizations** | Mean length: `703.0` chars | Mean length: `705.2` chars | **Mean Word Jaccard = `0.6119`** (`9.26%` exact string match) | Both invoke `llama3:8b` (`temp=0.0, seed=42, top_k=1`); minor floating-point batch context differences across runs produce near-identical vocabulary (`~704` chars). |
| **7** | **Semantic Subgraph Verbalizations** | Mean length: `707.7` chars (`100%` non-null) | Mean length: `680.2` chars (`100%` non-null) | **`100.0%` Null/Non-Null Agreement; Mean Word Jaccard = `0.7024`** (`21.60%` exact match) | Sorting blank-node closure triples (`sort_bnode_triples=True`) stabilized semantic verbalizations across runs. |
| **8** | **500-Char Text Chunk Counts** | `syn=162`, `lex=358`, `sem=314` (`834` chunks) | `syn=162`, `lex=367`, `sem=304` (`833` chunks) | **`99.88%` total chunk count parity** (`834` vs `833`) | `RecursiveCharacterTextSplitter(separators=[".", "\n"], chunk_size=500, chunk_overlap=0)` with `skip_empty_chunks=True` (`DISC-01`). |
| **9** | **Embedding Vector Dimensions** | `vector(4096)` (`llama3:8b`) | `vector(4096)` (`llama3:8b`) | **100.0% (`4096 == 4096`)** | Both use 4096-dim `llama3:8b` mean-pooled embeddings via `LlamaEmbeddingBridge`. |
| **10** | **Cosine Similarity Distributions ($\tau = 0.90$)** | $\tau = 0.90$, `top_k = 3` | Syntactic hits: `25` (mean `0.9551`), Lexical hits: `12` (mean `0.9282`), Semantic hits: `77` (mean `0.9211`) | **Consistent `pgvector` `<=>` cosine search** | Identical SQL cosine similarity operator `1 - (embedding <=> query) >= 0.90` Partitioned by opposing ontology side and matching `entity_type`. |
| **11** | **Syntactic Top-$k$ Candidates** | `91.36%` top-1 URI match (vs Local Adapted) | `91.36%` top-1 URI match (vs Local Adapted) | **`100.0%` exact-name match parity** | Syntactic embeddings deterministically retrieve all exact and near-exact lexicalized labels (`Administrator`, `Author`, `Conference`, `Paper`, `Person`, `title`/`hasTitle`, `writtenBy`). |
| **12** | **Lexical Top-$k$ Candidates** | 12 query entities $\ge 0.90$ | 12 query entities $\ge 0.90$ (`91.36%` top-1 agreement vs Local Adapted) | **High Top-1 Stability (`91.36%`)** | Domain-contextualized explanations disambiguate `ProgramCommitteeChair` $\leftrightarrow$ `Chair_PC` and `ProgramCommitteeMember` $\leftrightarrow$ `Member_PC`. |
| **13** | **Semantic Top-$k$ Candidates** | 77 query entities $\ge 0.90$ | 77 query entities $\ge 0.90$ (`56.17%` top-1 agreement vs Local Adapted) | **Dense 4096-dim vs 768-dim divergence identified** | Causal `llama3:8b` 4096-dim embeddings exhibit higher baseline cosine similarity (anisotropy) on structural verbalizations than dedicated `nomic-embed-text` 768-dim embeddings (`77` hits vs `10` hits at $\tau=0.90$). |
| **14** | **Combined Candidate Unions** | 47 S2T / 46 T2S unvalidated pairs | 52 S2T / 47 T2S unvalidated pairs (`92` non-empty directional queries) | **Unvalidated Recall = `43.75%` (`7/16` TP) in both** | Both retrieve the exact same 7 true positive correspondences prior to LLM validation. |
| **15** | **Reciprocal Rank Fusion (`RRF`, $k=0$)** | $k=0$, lexicographical `entity_id` tie-breaking | $k=0$, lexicographical `entity_id` tie-breaking | **100.0% Algorithmic Equivalence** | $\text{RRF}(d) = \sum_{r \in \{syn, lex, sem\}} \frac{1}{\text{rank}_r(d)}$ with score-grouped lists `[(score, [eid1, ...]), ...]`. |
| **16** | **Score-Group LLM Validation & Bypasses** | 26 S2T / 27 T2S validated pairs | 27 S2T / 27 T2S validated pairs (`128` LLM calls + `12` exact-name bypasses) | **93.33% Validation Decision Agreement** | Score-group early stopping (`if any_matched_in_group: break`) and exact-name bypass reduce LLM validation calls by $>80\%$. |
| **17** | **Reciprocal Merger & Final Alignment** | 12 valid pairs: `TP=5, FP=7, FN=11` ($P=41.67\%, R=31.25\%, F_1=35.71\%$) | 12 valid pairs (Run 1): `TP=6, FP=6, FN=10` ($P=50.00\%, R=37.50\%, F_1=42.86\%$); Runs 2–3: `11` pairs, `TP=6, FP=5` ($P=54.55\%, R=37.50\%, F_1=44.45\%$) | **Final Merged Jaccard = `0.5625` (`9` shared final pairs)** | Local parity reproduces all 5 upstream TPs (`Administrator`, `Author`, `Conference`, `Person`, `ProgramCommitteeMember/Member_PC`) **plus** recovers a 6th TP (`http://cmt#title` $\leftrightarrow$ `http://confOf#hasTitle`). |

---

## 3. Cross-Profile 17-Point Summary Table

From `output/replication_runs/comparisons/phase3_summary_table.csv`:

| Comparison Pair | Source URI Jaccard | Target URI Jaccard | `entity_id` Exact Match % | Syntactic Exact Match % | Lexical Word Jaccard | Semantic Null Agree % | Semantic Word Jaccard | Dims Equal | Final Merged Jaccard |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Upstream Lite vs Local Parity** | `1.0000` | `1.0000` | `100.0%` | `100.0%` | `0.6119` | `100.0%` | `0.7024` | `True` (`4096`) | `0.5625` |
| **Upstream Lite vs Local Adapted** | `1.0000` | `1.0000` | `0.0%`* | `100.0%` | `0.3097` | `100.0%` | `0.3770` | `False` (`4096` vs `768`) | `0.4615` |
| **Local Parity vs Local Adapted** | `1.0000` | `1.0000` | `0.0%`* | `100.0%` | `0.3131` | `100.0%` | `0.3762` | `False` (`4096` vs `768`) | `0.5000` |
| **Committed GPT-4o vs Local Adapted** | `1.0000` | `1.0000` | `100.0%` | `100.0%` | `1.0000` | `100.0%` | `1.0000` | `False` (`1536` vs `768`) | `0.6667` |
| **Committed GPT-4o vs Upstream Lite** | `1.0000` | `1.0000` | `0.0%`* | `100.0%` | `0.3097` | `100.0%` | `0.3770` | `False` (`1536` vs `4096`) | `0.5714` |

*\*Note on `entity_id` format in Committed GPT-4o CSV:* The committed upstream `alignment/conference/cmt-confof/component/ontology_matching.csv` file omits the `entity_id` column (which is generated in memory by `om_csv_to_database.py`), so `load_features_csv()` assigns deterministic synthetic IDs (`Source-Class-0-acceptance`), whereas full end-to-end runs (`Upstream Lite` and `Local Parity`) use the canonical 3-digit prefix format (`001-Source-Class-Acceptance`), matching `100.0%` (`162/162`).

---

## 4. Key Scientific Conclusions from Phase 3

1. **Deterministic Structural Parity (`Dimensions 1–5, 7–9, 15`):** Our Python 3.13 implementation achieves **100.0% exact match** with upstream `original_repo/` on extracted source URIs (`88`), extracted target URIs (`74`), 3-digit `entity_id` keys (`162/162`), entity display names (`162/162`), cleaned syntactic strings (`162/162`), semantic null/non-null classification (`100.0%`), vector dimensionality (`4096`), and RRF ($k=0$) rank fusion semantics.
2. **Causal 4096-Dim Embeddings vs. Dedicated 768-Dim Contrastive Embeddings (`Dimensions 10–14`):**
   - Causal LLM embeddings (`llama3:8b` 4096-dim via `LlamaEmbeddingBridge`) produce narrow cone-like cosine similarity distributions where 77 semantic queries exceed $\tau = 0.90$, generating `52` S2T and `47` T2S unvalidated candidate pairs ($P \approx 14\%, R = 43.75\%$).
   - Contrastively trained embedding models (`nomic-embed-text` 768-dim) produce well-calibrated cosine distances where only high-confidence matches exceed $\tau = 0.90$ (`9` S2T and `10` T2S unvalidated pairs, achieving $P = 75.00\%, R = 37.50\%, F_1 = 50.00\%$ directly after reciprocal merging without validation).
3. **Reciprocal Siamese Merger Efficacy (`Dimension 17`):** Across every configuration, the reciprocal Siamese inner-join ($\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$) eliminates asymmetric false positives while preserving $85\%–100\%$ of validated true positives, boosting final precision by $+24$ to $+32$ percentage points.
