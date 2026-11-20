# General Documentation — Agent-OM Local Replication and Lightweight LLM Adaptation

## 1. Project Purpose

This project provides a complete local replication, Python 3.13 modernisation, desktop workbench, and lightweight large language model ($\le 4\text{B}$ total parameters) adaptation of **Agent-OM: Leveraging LLM Agents for Ontology Matching** (Qiang, Wang, and Taylor, PVLDB, Vol. 18, No. 3, pp. 516–529; arXiv:2312.00326).

The system was developed as a university research and software engineering project in Applied Computational Intelligence and Application of Computational Linguistics. It eliminates all dependence on proprietary cloud APIs (such as OpenAI GPT-4o and Ada-002) by executing every language model and vector embedding computation locally through **Ollama** (`http://127.0.0.1:11434`) and **PostgreSQL 16 + `pgvector`** (`127.0.0.1:5432`).

---

## 2. Problem Definition

Scientific, biomedical, and enterprise information systems frequently use independently authored ontologies to describe overlapping domains. Because different ontology engineers select different naming conventions, class hierarchies, and property structures, automated systems cannot integrate data across two ontologies without knowing which entities refer to the same real-world concept.

For example, in academic conference management:
- The **CMT** ontology defines the class `http://cmt#ProgramCommitteeMember` and property `http://cmt#title`.
- The **ConfOf** ontology defines the equivalent class `http://confOf#Member_PC` and property `http://confOf#hasTitle`.
- Conversely, both ontologies define `Paper` (`http://cmt#Paper` and `http://confOf#Paper`), yet in the OAEI ground truth `cmt:Paper` corresponds to `confOf:Contribution`, whereas `cmt:PaperFullVersion` corresponds to `confOf:Paper`.

Resolving these correspondences requires combining surface string similarity, domain-specific lexical definitions, and structural graph context.

---

## 3. Ontology Matching Definition

An ontology $O = (C, P, A)$ consists of a set of classes $C$, a set of properties $P = P_{\text{obj}} \cup P_{\text{data}}$, and a set of logical axioms $A$. Let $E_1 = C_1 \cup P_1$ and $E_2 = C_2 \cup P_2$ be the sets of named entities in a source ontology $O_1$ and a target ontology $O_2$.

**Ontology Matching** is the process of computing an alignment $\mathcal{A}$ consisting of correspondences $(e_1, e_2, r, c)$, where:
- $e_1 \in E_1$ and $e_2 \in E_2$ are entities of the same category ($\text{type}(e_1) = \text{type}(e_2) \in \{\text{Class}, \text{Property}\}$).
- $r$ is a semantic relation, restricted here to equivalence ($\equiv$).
- $c \in [0, 1]$ is a confidence score ($1.0$ for validated matches).

---

## 4. Agent-OM Architecture

Agent-OM uses a **Siamese Agent Design** composed of two cooperating agents that process both the source and target ontologies symmetrically:

1. **Retrieval Agent (`1_Source/agents/retrieval_agent.py`):**
   - Parses raw OWL/RDF ontologies (`OntologyGraph`).
   - Extracts all named classes and properties (`EntityExtractor`).
   - Generates three complementary textual views per entity: **Syntactic**, **Lexical**, and **Semantic**.
   - Splits long descriptions into 500-character chunks and embeds them into a relational-vector database (`PostgreSQL + pgvector`).
   - Retrieves the top-$k$ most similar candidates from the opposing ontology for each view and combines the three rankings using **Reciprocal Rank Fusion (RRF)**.
2. **Matching Agent (`1_Source/agents/matching_agent.py`):**
   - Evaluates the RRF-ranked candidate groups in both directions ($O_1 \to O_2$ and $O_2 \to O_1$).
   - Applies an **exact-name bypass** when normalized entity names are identical, avoiding redundant LLM calls.
   - Invokes a zero-shot LLM equivalence validator (`MatchingValidator`) group-by-group with early stopping once a match is confirmed in the highest-scoring RRF group.
   - Intersects the two directional alignments using a **Reciprocal Siamese Merger** (`ReciprocalMerger`) so that only mutually confirmed correspondences are emitted.

---

## 5. Main Application Components

The source code in `1_Source/` is organized into the following packages:

| Package / Module | Primary Classes / Functions | Responsibility |
| :--- | :--- | :--- |
| `1_Source/config.py` | `AppConfig`, `VALID_PROFILES`, `STRICT_4B_PROFILES` | Central configuration, profile presets, loopback validation, and cloud-model prohibition guards. |
| `1_Source/core/` & `ontology/` | `OntologyGraph`, `EntityExtractor`, `OntologyEntity` | RDF/XML and Turtle parsing via `rdflib`, class/property extraction, punning preservation, and code-IRI label resolution. |
| `1_Source/retrieval/` | `SyntacticRetriever`, `LexicalRetriever`, `SemanticRetriever`, `reciprocal_rank_fusion` | Three-view feature extraction, LLM verbalization of definitions and 18-predicate subgraphs, and RRF ($k=0$) fusion. |
| `1_Source/matching/` | `MatchingValidator`, `ReciprocalMerger` | Exact-name bypass check, zero-shot Yes/No equivalence prompting, and symmetric bidirectional alignment intersection. |
| `1_Source/agents/` | `RetrievalAgent`, `MatchingAgent`, `LLMJsonToolRouter` | High-level agent orchestration supporting both deterministic execution and LLM JSON tool routing. |
| `1_Source/llm/` | `OllamaClient`, `ModelRegistry`, `ModelValidator`, `LocalChatProvider`, `LocalEmbeddingProvider` | Separated chat and embedding providers, runtime `/api/show` inspection, strict $\le 4.0\text{B}$ parameter enforcement, and vector dimension verification. |
| `1_Source/database/` & `db/` | `DatabaseManager` | PostgreSQL connection management, `pgvector` table creation, 500-char text chunking, cosine similarity search (`<=>`), and `agent_om_local` write protection. |
| `1_Source/evaluation/` | `compute_alignment_metrics`, `compare_two_runs_17_points`, `charts.py` | Precision/Recall/$F_1$ calculation, 17-dimension intermediate output comparator, stage attrition analyzer, and Matplotlib chart builders. |
| `1_Source/gui/` & `services/` | `MainWindow`, 10 Views, 11 Services | PySide6 desktop workbench for environment diagnostics, dataset browsing, profile configuration, live experiment execution, and report export. |
| `1_Source/utils/` | `cleaning`, `LlamaEmbeddingBridge` | Acronym repair, snake-case splitting, `breame` British-to-American spelling normalization, and loopback GGUF embedding bridge for causal models. |

---

## 6. Data Processing Workflow

1. **Ontology Loading:** `load_ontology()` parses `source.xml` and `target.xml` into `rdflib.Graph` instances.
2. **Entity Extraction:** `EntityExtractor.extract_entities()` collects all OWL classes (`owl:Class`, `skos:Concept`) and properties (`owl:ObjectProperty`, `owl:DatatypeProperty`), filtering out blank nodes, `owl:Thing`, and built-in OBO metadata terms. Classes are sorted alphabetically by URI, followed by properties sorted alphabetically by URI (`combine_properties_sort=True`).
3. **Feature Generation:** For each of the 162 entities in `CMT–ConfOf` (`88` Source, `74` Target), `RetrievalAgent` produces a row in `ontology_matching` with a canonical 3-digit `entity_id` (`001-Source-Class-Acceptance` through `162-Target-Property-writtenBy`) and its syntactic, lexical, and semantic texts.
4. **Chunking and Embedding:** `DatabaseManager.create_embedding_table()` strips sentinel null sentences (`"Information is not available."`), splits remaining text into 500-character segments, embeds each chunk into an $N$-dimensional float vector, verifies `len(vec) == vector_length`, and inserts the rows into `syntactic_matching`, `lexical_matching`, and `semantic_matching`.
5. **Candidate Retrieval and RRF:** For every source entity, the database queries the target entities of the same type across all three vector tables with cosine similarity threshold $\tau$, and fuses the top-$k$ lists with `reciprocal_rank_fusion(k=0)`. The process repeats symmetrically for every target entity querying source entities.
6. **Validation and Reciprocal Merging:** `MatchingAgent` validates candidate groups in both directions and intersects the validated sets via `ReciprocalMerger.merge_alignments()`.

---

## 7. Retrieval Methods

- **Syntactic Retrieval (`1_Source/retrieval/syntactic_retriever.py`):** Normalizes entity names into lowercase space-separated American English tokens (for example, `ProgramCommitteeMember` $\to$ `program committee member`).
- **Lexical Retrieval (`1_Source/retrieval/lexical_retriever.py`):** Extracts annotations across 10 predicates (`rdfs:comment`, `rdf:value`, `skos:definition`, `skos:notation`, `skos:note`, `skos:scopeNote`, `skos:editorialNote`, `skos:historyNote`, `skos:changeNote`, `skos:example`) and prompts the local LLM to define the entity within the domain context (`conference`).
- **Semantic Retrieval (`1_Source/retrieval/semantic_retriever.py`):** Extracts all incoming and outgoing triples across 18 structural predicates (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `owl:disjointWith`, `rdfs:domain`, `rdfs:range`, `owl:equivalentClass`, `owl:equivalentProperty`, and 11 SKOS relational predicates) plus blank-node OWL restriction closures, and prompts the local LLM to verbalize the subgraph into natural language sentences.
- **Hybrid Fusion (`1_Source/retrieval/rank_fusion.py`):** Combines the three retrieval rankings using $\text{RRF}(c) = \sum_{m} \frac{1}{\text{rank}_m(c)}$ with deterministic lexicographical tie-breaking.

---

## 8. Matching and Alignment Methods

- **Exact-Name Bypass (`MatchingValidator.check_name_bypass`):** If the cleaned syntactic string of the query entity equals that of the candidate entity (for example, `author == author`), the pair is immediately accepted without calling the LLM.
- **Score-Group LLM Validation (`MatchingValidator.validate_pair`):** Non-trivial candidate pairs are formatted into a domain-contextualized prompt asking whether Entity A and Entity B are equivalent in the context of a conference. Candidates are evaluated in descending RRF score groups; once at least one candidate in a group is validated as `"yes"`, lower-ranked groups are skipped.
- **Reciprocal Siamese Merger (`ReciprocalMerger.merge_alignments`):** Computes the set intersection $\mathcal{A}_{S \to T} \cap \mathcal{A}_{T \to S}$ after normalizing pair orientation to `(source_uri, target_uri)`.

---

## 9. LLM Integration and Strict $\le 4\text{B}$ Parameter Enforcement

The `1_Source/llm/` package enforces three core scientific guarantees:
1. **100% Local Loopback Execution:** All HTTP requests target `http://127.0.0.1:11434`. Any configuration referencing a non-loopback host or a cloud model prefix (`gpt-`, `claude-`, `text-embedding-ada`, etc.) raises `PermissionError` or `ValueError`.
2. **Runtime Parameter Verification (`/api/show`):** `ModelRegistry.inspect_model()` queries Ollama's `/api/show` endpoint and reads `model_info["general.parameter_count"]`. In strict $\le 4\text{B}$ profiles (`local_4b_baseline`, `local_4b_optimized`, `local_4b_reasoning`), `ModelValidator.validate_chat_model()` enforces `total_parameter_count <= 4_000_000_000`. Notably, this audit revealed that `qwen3.5:4b` has `4,538,986,496` parameters ($4.54\text{B}$) despite its `:4b` tag, and therefore automatically excludes it from strict $\le 4\text{B}$ runs in favor of verified $\le 4.0\text{B}$ models (`qwen2.5:3b` at $3,085,938,688$ parameters and `deepseek-r1:1.5b` at $1,777,088,000$ parameters).
3. **Separated Chat and Embedding Providers:** `LocalChatProvider` and `LocalEmbeddingProvider` prevent using chat models as embedders or embedding models as chat generators, and validate live vector dimensions before database ingestion.

---

## 10. Database Architecture

PostgreSQL 16 with `pgvector` (`0.8.0`) stores four tables per experiment database:
- `ontology_matching`: Primary metadata table (`entity_id PRIMARY KEY`, `entity_uri`, `source_or_target`, `entity_type`, `syntactic_matching`, `lexical_matching`, `semantic_matching`).
- `syntactic_matching`, `lexical_matching`, `semantic_matching`: Vector chunk tables (`id SERIAL PRIMARY KEY`, `entity_id REFERENCES ontology_matching(entity_id)`, `content TEXT`, `embedding vector(N)`), where $N \in \{768, 1024, 4096\}$ matches the active embedding model.

The historical database `agent_om_local` (`162 / 162 / 206 / 258` rows) is write-protected in `DatabaseManager`. All new experiments use isolated databases (`agent_om_parity`, `agent_om_adapted`, `agent_om_4b_baseline`, `agent_om_4b_mxbai`, `agent_om_test`).

---

## 11. Desktop Application

The PySide6 desktop workbench (`run_gui.py` and `1_Source/gui/`) provides 10 screens:
1. **Dashboard:** Live service health badges and benchmark summary table.
2. **Environment Diagnostics:** Hardware, PostgreSQL database inspector, and 7-column Ollama model table showing exact parameter counts and $\le 4.0\text{B}$ compliance badges.
3. **Dataset Manager:** OAEI and custom OWL/RDF dataset discovery and preview.
4. **Configuration Profiles:** Editor for all 7 replication profiles with safety validation and JSON preset import/export.
5. **Replication Wizard (14 Stages):** Asynchronous background `QThread` runner with live progress and cooperative cancellation.
6. **Pipeline Stage Inspector:** Searchable per-entity table of syntactic, lexical, semantic, RRF, and validation records.
7. **Original vs. Local Comparison:** Interactive 17-dimension intermediate comparator and TP/FP/FN pair diff viewer.
8. **Evaluation & Charts:** Interactive Matplotlib visualization of Precision/Recall/$F_1$, iso-$F_1$ scatter, stage attrition, threshold sensitivity, and runtime/LLM calls.
9. **Live Logs & Run History:** Streaming console and historical run browser.
10. **Report & Artifact Export:** One-click bundle exporter writing CSVs, JSONs, PNG charts, and Markdown reports to `output/replication_runs/exports/`.

---

## 12. Experimental Methodology and Evaluation Metrics

Experiments are evaluated on the OAEI `CMT–ConfOf` benchmark (`88` CMT entities, `74` ConfOf entities, $|\mathcal{G}| = 16$ gold equivalence pairs). Given predicted alignment set $\mathcal{P}$ and gold reference set $\mathcal{G}$:
$$\text{TP} = |\mathcal{P} \cap \mathcal{G}|, \quad \text{FP} = |\mathcal{P} \setminus \mathcal{G}|, \quad \text{FN} = |\mathcal{G} \setminus \mathcal{P}|$$
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

---

## 13. Summary of Scientific Results

| Category | Experiment / Profile | Chat Model (Verified Params) | Embedding Model (Dim) | Pred | TP | FP | FN | Precision | Recall | $F_1$ Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Upstream Cloud Ref** | `ref_upstream_gpt4o_v1` | `gpt-4o-2024-05-13` | `text-embedding-ada-002` (1536) | 9 | 6 | 3 | 10 | 66.67% | 37.50% | **48.00%** |
| **Upstream Lite Ref Table** | `result-om-2025-test.csv` | `llama3:8b` (`8.03B`) | `llama3:8b` (4096) | 7 | 4 | 3 | 12 | 57.14% | 25.00% | **34.78%** |
| **Upstream Lite Executed** | `phase1_cmt_confof_v1` | `llama3:8b` (`8.03B`) | `llama3:8b` (4096) | 12 | 5 | 7 | 11 | 41.67% | 31.25% | **35.71%** |
| **Local 8B Parity (Runs 2–3)** | `phase5_expC_run2..3` | `llama3:8b` (`8.03B`) | `llama3:8b` (4096) | 11 | 6 | 5 | 10 | **54.55%** | **37.50%** | **44.45%** |
| **Local Adapted (>4B Ref)** | `phase5_expD_run2` | `qwen3.5:4b` (`4.54B`) | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | 66.67% | 25.00% | **36.36%** |
| **Strict $\le 4\text{B}$ Baseline (`E1` x3)**| `phase6_E1_run1..3` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** |
| **Strict $\le 4\text{B}$ Opt Prompt (`E2`)**| `phase6_E2_optimized` | `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** |
| **Strict $\le 4\text{B}$ Alt Embed (`E5`)** | `phase6_E5_mxbai_1024d` | `qwen2.5:3b` (`3.09B`) | `mxbai-embed-large` (1024) | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** |
| **Strict $\le 4\text{B}$ $\tau=0.85$ (S2T Val)**| `phase6_E6_tau085` (`4_s2t`)| `qwen2.5:3b` (`3.09B`) | `nomic-embed-text` (768) | 9 | 6 | 3 | 10 | **66.67%** | **37.50%** | **48.00%** |
| **Strict $\le 4\text{B}$ Reasoning (`E7`)** | `phase6_E7_deepseek_15b` | `deepseek-r1:1.5b` (`1.78B`) | `nomic-embed-text` (768) | 6 | 4 | 2 | 12 | **66.67%** | **25.00%** | **36.36%** |

---

## 14. Limitations, Reproducibility, and Technical Requirements

- **Limitations:** While `nomic-embed-text` retrieval + RRF recovers $7/16$ gold pairs ($F_1=48.28\%$ at $\tau=0.875$) and `qwen2.5:3b` validates $6/16$ in `Source -> Target` ($F_1=48.00\%$ at $\tau=0.85$), smaller $\le 4\text{B}$ models exhibit directional sensitivity in `Target -> Source` validation on abbreviated labels (`Member_PC` vs. `ProgramCommitteeMember`), causing the symmetric intersection to drop 2 true positives.
- **Reproducibility:** Setting `temperature=0.0`, `seed=42`, `llm_top_k=1`, `top_p=1.0`, and `repeat_penalty=1.0` produced $100\%$ identical predictions across all 3 repeated runs of `E1` (`qwen2.5:3b`) and Runs 2–3 of `Exp C` (`llama3:8b`).
- **Technical Requirements:** Python `3.13+`, PostgreSQL `16+` with `pgvector 0.8+` on `127.0.0.1:5432`, and Ollama `0.40+` on `127.0.0.1:11434` with `16 GB` RAM recommended.
