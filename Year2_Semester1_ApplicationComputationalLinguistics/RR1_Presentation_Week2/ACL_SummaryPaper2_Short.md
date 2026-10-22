# Concise Study Guide: Agent-OM (Leveraging LLM Agents for Ontology Matching)

## 1. Core Concepts & Problem Statement
* **Ontology & Entities:** An **Ontology** is a structured digital dictionary defining concepts and relationships in a domain. Its building blocks (**Entities**) include **Classes** (categories), **Properties** (attributes/relations), and **Individuals** (real-world instances). **TBox** refers to the schema (classes/properties), while **ABox** refers to the instances.
* **Ontology Matching (OM) & Alignment:** Finding equivalent concepts ($=$) between a source ontology ($O_s$) and target ontology ($O_t$) to produce a list of matched pairs called an **Alignment ($A$)**.
* **Limitations of Existing OM Paradigms:**
  1. *Knowledge-Based Expert Systems (e.g., LogMap, AML):* Use hardcoded logic rules. They are precise on simple tasks but require heavy human expert effort.
  2. *Machine Learning (ML) Systems (e.g., BERTMap, Matcha):* Predict matches by training models on sample data. However, domain ontologies are small (100–200 entities), providing too little data to fine-tune massive **Large Language Models (LLMs)** (which need ~1,000+ samples). Sending private data to web APIs for training also risks data leaks.
* **Why Naive LLM Prompting Fails:** Asking an LLM a binary ("Yes/No") question for every entity pair requires $N_s \times N_t$ comparisons. This exceeds LLM token limits, costs too much, and suffers from **hallucinations** (factually wrong answers) and poor multi-step planning.
* **Research Objective:** Introduce **Agent-OM**, an autonomous **LLM Agent** framework where the LLM acts as a central "brain" coordinating **Planning** (via **Chain-of-Thought / CoT** step-by-step decomposition), **Tools** (external functions), and **Memory** (via **In-Context Learning / ICL** prompt context and **Retrieval-Augmented Generation / RAG** database lookup) to automate TBox equivalence matching without model retraining.

---

## 2. Methodology & Architecture

Agent-OM splits OM into two **Siamese Autonomous Agents**—a **Retrieval Agent** and a **Matching Agent**—that have separate planning and tool modules but share a unified **Memory**. To prevent LLM hallucinations on opaque biomedical codes (**Type 2** naming like `MA_0000270` vs. **Type 1** meaningful names like `Chair_PC`), Agent-OM replaces codes with their human-readable labels (`rdfs:label`) and adds a unique prefix (`023-Source-Class-...`).

```
[Source (Os) & Target (Ot)]
       |
       v
+-------------------------------------------------------------------------------+
| 1. RETRIEVAL AGENT: Extracts entities & stores context in Shared Memory       |
|  * Metadata Retriever: Extracts source/target category & type (Class/Property)|
|  * Syntactic Retriever: Tokenizes & normalizes names into lowercase words     |
|  * Lexical Retriever: Prompts LLM for meaning using domain context & labels   |
|  * Semantic Retriever: Verbalizes ontology triples (subclasses) into sentences|
|  * Content Embedder: Converts text into number vectors (embeddings)           |
+-------------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------------+
| 2. SHARED MEMORY: Dialogue (Short-Term) + Hybrid PostgreSQL DB (Long-Term)    |
|  * Relational DB: Stores exact metadata | Vector DB (pgvector): 3 vector      |
|    (entity_id, URI, source/target, type)| tables (Syntactic, Lexical,Semantic)|
+-------------------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------------------+
| 3. MATCHING AGENT: Bidirectional search (Os -> Ot AND Ot -> Os)               |
|  * Metadata & Content Matchers: Filters by type; runs Cosine Similarity search|
|  * Matching Summariser: Combines top@k rankings via Reciprocal Rank Fusion    |
|  * Matching Validator: LLM self-check ("Yes/No") removes false positives      |
|  * Matching Merger: Keeps only bidirectional matches (Os <=> Ot) -> [Output A]|
+-------------------------------------------------------------------------------+
```

### Key Algorithms & Complexity
* **Cosine Similarity:** Measures vector closeness between entities $A$ and $B$: $S_C(A, B) = \frac{A \cdot B}{\Vert{}A\Vert{}\Vert{}B\Vert{}}$. Candidates must pass a `similarity_threshold` ($T \ge 0.90$) and rank in the `top@k` ($k=3$).
* **Reciprocal Rank Fusion (RRF):** Combines rankings $r(d)$ from the 3 matchers (Syntactic, Lexical, Semantic): $RRF(d \in D) = \sum_{r \in R} \frac{1}{k + r(d)}$ (with $k=0$). RRF breaks mean-score ties and prevents missing semantic data from ruining an entity's overall score.
* **Search Complexity Reduction:** Storing entities in a vector database reduces LLM calls from $N_s \times N_t$ to $(k+1)(N_s + N_t)$, cutting token usage by **~94%** ($2.7 \times 10^5$ vs. $4.7 \times 10^6$ tokens in `LLM-with-Context`).
* **Evaluation Metrics:** $\text{Precision} = \frac{|A \cap R|}{|A|}$ (correctness), $\text{Recall} = \frac{|A \cap R|}{|R|}$ (completeness), and $F_1 = \frac{2}{\text{Precision}^{-1} + \text{Recall}^{-1}}$ against expert reference $R$.

---

## 3. Experimental Results & Ablation Insights

* **OAEI Benchmark Performance (2022 & 2023 using `gpt-4o`, $T=0.90, k=3$):**
  * **Conference Track (Few-shot, Type 1):** Ranked **3rd/13 (2022)** and **5th/12 (2023)** in F1 with zero training data.
  * **Anatomy Track (Biomedical, Type 2):** Ranked **2nd** on Trivial matches; beat **11/12 systems** on Non-Trivial complex matches (second only to supervised DL system Matcha).
  * **MSE Track (Materials Science):** Ranked **1st overall** in Test Cases 1 & 2, easily resolving domain abbreviations (`Au` = `Gold`) and avoiding subsumption traps.
* **Ablation Findings:**
  * *Models:* Commercial LLMs (`gpt-4o`, `claude-3-sonnet`) beat 7B–9B open-source models (`gemma-2-9b` led open-source). Larger embeddings (`text-embedding-3-large`) gave no gain over `ada-002`.
  * *Refinement:* Both the **Validator** and **Merger** boost Precision and F1 by filtering hallucinations, with a minor Recall drop.
  * *Hyperparameters:* Optimal settings are $T \in [0.90, 0.95]$ and $k \in [3, 4, 5]$. Higher $T$ / lower $k$ favors Precision; lower $T$ / higher $k$ favors Recall.

---

## 4. Relationship & Differences: Follow-Up OAEI Papers (2025 & 2026) vs. Main Paper

While the main paper (*PVLDB 2024*) introduced the core Agent-OM architecture and evaluated it offline on 3 tracks, the subsequent **OAEI 2025** and **OAEI 2026** papers test the system in live OAEI campaigns across diverse domains (Biodiversity, Digital Humanities, Circular Economy, Multilingualism) and track LLM evolution:

| Dimension | Main Paper (PVLDB 2024) | OAEI 2025 Campaign Paper | OAEI 2026 Campaign Paper |
| :--- | :--- | :--- | :--- |
| **System Variants** | Single proof-of-concept system. | Splits into **Agent-OM** (commercial `gpt-4o` for accuracy) and **Agent-OM-Lite** (free local `llama-3` for large/private tracks). | Adds a **Web Interface** for local execution and **Agent-OV** for ontology versioning. |
| **LLM & Structural Support** | `gpt-4o` / `llama-3`; basic OWL/RDFS triples (`rdfs:subClassOf`). | Adds `DeepSeek-R1`; parses **SKOS** and complex **OWL Restrictions (blank nodes)**; supports dummy references. | Upgrades to **`gpt-5`** and **`llama-3.1-8b`**; proposes a **Model Context Protocol (MCP)** layer for MELT compatibility. |
| **Determinism & Metrics** | Noted minor stochastic variance; used Precision, Recall, F1, Token Cost. | Enforces strict determinism (`seed=42, top_k=1, repeat_penalty=1.0`); introduces **Normalized Reciprocal Rank ($RR^*, MRR^*$)**. | Notes `gpt-5` removed timestamp/penalty controls; proposes **Unit of Tokens (UoT)** (tokens per mapping) to replace unfair wall-clock runtime. |
| **Key Findings** | Agent-OM beats SOTA on complex/few-shot OM and cuts token costs. | Same-language/English pairs perform best in multilingual OM; suggests stopping after syntactic matching on simple bio tracks. | **LLM Caution Shift:** Stricter `gpt-5` guardrails and case sensitivity cause the Validator to reject uncertain matches, **raising Precision but lowering Recall**. |

---

## 5. Challenges, Limitations & 5-Slide RR1 Presentation Guide

* **Slide 1: Problem & Motivation:** Traditional OM requires costly experts or unavailable training data; naive LLM prompting costs $N_s \times N_t$ tokens and hallucinates. *Goal:* Autonomous LLM agents for zero-shot OM.
* **Slide 2: Siamese Architecture:** Retrieval Agent + Shared Hybrid DB (PostgreSQL + `pgvector`) + Matching Agent (Cosine Similarity $\to$ RRF $\to$ Self-Check Validator $\to$ Bidirectional Merger).
* **Slide 3: Results & Evolution (2024–2026):** SOTA results on complex/non-trivial tracks; 94% token reduction; evolution into commercial **Agent-OM** vs. open-source **Agent-OM-Lite**; 2026 shift showing `gpt-5` prioritizes Precision over Recall.
* **Slide 4: Challenges & Limitations:**
  * *Moravec's Paradox:* Excels at hard semantic tasks, but doesn't beat simple string rules on trivial matches.
  * *Scope & Reasoning:* Limited to TBox equivalence ($=$); excludes ABox instances due to privacy; struggles with subsumption ($\subseteq$); uses linear CoT rather than branching reasoning.
  * *Cost & Unbalanced Data:* High API cost/latency; bidirectional validation wastes compute when matching a small ontology against a massive one; noisy ontology metadata confuses embeddings.
* **Slide 5: Future Work:** Early-stopping hybrid pipeline (stop after syntactic match if score is high); asymmetric validation starting from the smaller ontology; **Tree/Graph-of-Thoughts (ToT/GoT)** reasoning; **Unit of Tokens (UoT)** benchmarking; Multimodal OM (diagrams) and Small Language Models (SLMs).