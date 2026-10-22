# Study Guide: Agent-OM (Leveraging LLM Agents for Ontology Matching)

---

## 1. Core Terminology (Defined Simply)

* **Ontology:** A structured digital dictionary that defines concepts (things) and how they relate to each other within a specific topic, such as medicine or conference organization.
* **Entity:** A basic building block inside an ontology. Entities include **Classes** (categories of things, like `Author`), **Properties** (attributes or relationships, like `writesPaper`), and **Individuals** (specific real-world instances, like `John Doe`).
* **TBox (Terminological Box) vs. ABox (Assertional Box):** The **TBox** is the structural blueprint of an ontology (its classes and properties). The **ABox** is the actual data stored inside that blueprint (specific individuals).
* **Ontology Matching (OM):** The process of finding equivalent concepts between two different ontologies that describe the same topic using different words (for example, matching `ProgramCommitteeChair` in one ontology to `Chair_PC` in another).
* **Alignment:** The final list of matched entity pairs produced by an ontology matching system.
* **Large Language Model (LLM):** A computer program trained on massive amounts of text to understand and generate human language (such as GPT-4o or Llama 3).
* **LLM Agent:** A system that uses an LLM as a central controller ("brain"). Instead of just answering a single question, an agent can break down complex goals into steps (**Planning**), call external software programs (**Tools**), and store information for later use (**Memory**).
* **Hallucination:** When an LLM generates an answer that sounds grammatically correct and confident, but is factually wrong.
* **Chain-of-Thought (CoT):** A technique that guides an LLM to solve a complex problem step-by-step rather than guessing the final answer immediately.
* **In-Context Learning (ICL):** Giving an LLM useful background information or examples directly inside the text prompt so it can perform a task without retraining the model.
* **Retrieval-Augmented Generation (RAG):** Looking up relevant facts from an external database first, and then handing those facts to an LLM so it can give an accurate, grounded answer.
* **Vector Database & Embeddings:** An **Embedding** turns words and sentences into a list of numbers (a vector) based on their meaning. A **Vector Database** stores these number lists and quickly finds concepts with similar meanings by measuring how close their numbers are in space.

---

## 2. Main Ideas & Research Objectives

### The Problem
Historically, automated Ontology Matching (OM) systems relied on two approaches, both of which have major drawbacks:
1. **Knowledge-Based Expert Systems (e.g., LogMap, AML):** Rely on hardcoded rules and human domain experts. They are accurate on simple tasks but require massive human effort to build and cannot easily adapt to new domains.
2. **Machine Learning (ML) Predictive Systems (e.g., BERTMap, Matcha):** Train models on sample data to predict matches. However, domain ontologies are usually small (100–200 entities), providing too little data to train or fine-tune massive LLMs (which need 1,000+ samples). Furthermore, sending private data to commercial LLM servers for training risks data leaks.

Early attempts to use LLMs directly for OM asked simple binary ("Yes/No") questions for every possible pair of entities across two ontologies. This fails because:
* **Token Limits & High Cost:** Comparing every entity in Ontology A ($N_s$) with every entity in Ontology B ($N_t$) requires $N_s \times N_t$ queries, which is slow and expensive.
* **LLM Flaws:** Standalone LLMs suffer from hallucinations, lack up-to-date domain knowledge, and struggle with complex multi-step planning.

### Research Objective & Contributions
The authors introduce **Agent-OM**, the first **autonomous LLM-agent framework** for ontology matching. 
* **Goal:** Shift the LLM from a simple question-answering model into a central controller ("brain") that coordinates planning, external OM tools, and hybrid database memory to automate TBox equivalence matching ($=$) without human intervention or model retraining.
* **Key Achievement:** Matches the accuracy of top traditional systems on simple OM tasks while significantly outperforming state-of-the-art systems on complex and few-shot (low-data) OM tasks.

---

## 3. Methodology & System Architecture

Agent-OM divides the matching pipeline into two **Siamese Autonomous Agents**—a **Retrieval Agent** and a **Matching Agent**—that have separate planning and tool modules but share a unified **Memory** (Dialogue + Hybrid Relational/Vector Database).

### System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            INPUT: Source (Os) & Target (Ot)                       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+===================================================================================+
| 1. RETRIEVAL AGENT (Executed for Os and Ot)                                       |
|                                                                                   |
|  [Planning (CoT)] ---> Entity Extraction -> Metadata Retrieval -> Content Retrieval|
|         |                                                                         |
|         v (LLM Invokes Tools)                                                     |
|  [Retrieval Tools]                                                                |
|    * Metadata Retriever: Extracts source/target category & type (Class/Property)  |
|    * Syntactic Retriever: Tokenizes & normalizes names into lowercase words       |
|    * Lexical Retriever: Prompts LLM for meaning using domain context & labels     |
|    * Semantic Retriever: Extracts triples (subclasses) & verbalizes to sentences  |
|    * Content Embedder: Converts syntactic/lexical/semantic text into vectors      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v (Stores via CRUD)
+===================================================================================+
| 2. SHARED MEMORY                                                                  |
|  * Short-Term Memory: Conversational Dialogue (stores intermediate step outputs)  |
|  * Long-Term Memory (Hybrid PostgreSQL + pgvector Database):                      |
|      - Relational DB: Stores exact metadata (entity_id, URI, source/target, type) |
|      - Vector DB: 3 tables storing embeddings (Syntactic, Lexical, Semantic)      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v (Searches via Hybrid DB Search)
+===================================================================================+
| 3. MATCHING AGENT (Executed Bidirectionally: Os -> Ot AND Ot -> Os)               |
|                                                                                   |
|  [Planning (CoT)] ---> Extract -> Match Metadata/Content -> Summarize -> Refine   |
|         |                                                                         |
|         v (LLM Invokes Tools)                                                     |
|  [Matching Tools]                                                                 |
|    * Metadata Matcher: Filters candidates by exact type (e.g., Class to Class)    |
|    * Syntactic, Lexical & Semantic Matchers: Cosine similarity search (Top@k)     |
|    * Matching Summariser: Combines the 3 rankings via Reciprocal Rank Fusion (RRF)|
|    * Matching Validator: LLM self-check ("Yes/No" prompt) to remove hallucinations|
|    * Matching Merger: Keeps only bidirectional matches (Os <=> Ot)                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           OUTPUT: Final Alignment (A)                             |
+-----------------------------------------------------------------------------------+
```

### Handling Naming Conventions
Ontologies use two naming styles: **Type 1** (meaningful names like `ProgramCommitteeChair`) and **Type 2** (opaque biomedical codes like `MA_0000270`). Because LLMs hallucinate meanings for opaque codes, Agent-OM standardizes Type 2 entities by replacing codes with their human-readable `rdfs:label` or `rdfs:comment` (e.g., `eyelid_tarsus`) and prefixes every entity with a unique ID (`023-Source-Class-ProgramCommitteeChair`).

### Key Algorithms & Mathematical Formulas

| Algorithm / Metric | Formula | Purpose in Agent-OM |
| :--- | :--- | :--- |
| **Cosine Similarity** | $S_C(A, B) = \frac{A \cdot B}{\|A\|\|B\|}$ | Measures how similar two text embedding vectors ($A$ and $B$) are in the Vector Database. Candidates must pass a `similarity_threshold` (e.g., $\ge 0.90$). |
| **Reciprocal Rank Fusion (RRF)** | $RRF(d \in D) = \sum_{r \in R} \frac{1}{k + r(d)}$ *(with $k=0$)* | Combines the top candidate rankings ($r$) from the 3 matchers (Syntactic, Lexical, Semantic) into a single score. Avoids mean-score ties and handles missing semantic data gracefully. |
| **Search Complexity Reduction** | $(k + 1)(N_s + N_t) \ll N_s \times N_t$ | By storing entities in a vector database first ($N_s + N_t$) and only validating the top $k$ candidates ($k(N_s + N_t)$), Agent-OM avoids comparing every pair ($N_s \times N_t$), drastically cutting token costs. |
| **Evaluation Metrics** | $\text{Precision} = \frac{|A \cap R|}{|A|}$, $\text{Recall} = \frac{|A \cap R|}{|R|}$, $F_1 = \frac{2}{\text{Precision}^{-1} + \text{Recall}^{-1}}$ | Evaluates predicted alignment ($A$) against expert reference ($R$). **Precision** measures correctness; **Recall** measures completeness; **F1** balances both. |

---

## 4. Experimental Results & Ablation Findings

### Performance Across OAEI Benchmark Tracks (2022 & 2023)
Using `gpt-4o` with optimal hyperparameters (`similarity_threshold = 0.90`, `top@k = 3`):
* **Conference Track (Few-shot, small/medium Type 1 ontologies):** Ranked **3rd/13 (2022)** and **5th/12 (2023)** in F1 score, outperforming most systems despite having almost no training samples.
* **Anatomy Track (Large biomedical Type 2 ontologies):**
  * *Test Case 1 (Trivial matches with identical labels):* Ranked **2nd highest** in F1 score.
  * *Test Case 2 (Non-trivial/complex matches):* Beat 11 out of 12 systems (including LLM-based OLaLa), second only to Matcha (which relied on a massive domain training set).
* **Materials Science & Engineering (MSE) Track:**
  * *Test Case 1 (Complex references with subsumption traps)* & *Test Case 2 (Domain acronyms like `Au` = `Gold`, `Ag` = `Silver`):* Achieved **1st place (best Precision, Recall, and F1)** across all systems, proving LLMs excel at domain abbreviations and context reasoning.
  * *Test Case 3 (Standardized BFO upper ontology):* Tied for best in 2022; 2nd to Matcha in 2023.

### Ablation Study Insights
1. **Architecture (`Agent-OM` vs. `LLM-Only` vs. `LLM-with-Context`):** `LLM-Only` has poor accuracy. `LLM-with-Context` improves accuracy slightly but consumes **~17x more tokens** ($4.7 \times 10^6$ vs. $2.7 \times 10^5$ tokens) because it lacks database candidate filtering.
2. **LLM Backends:** Commercial API models (`gpt-4o`, `claude-3-sonnet`) outperform open-source models (7B–9B). Among open-source models, `gemma-2-9b` performed best.
3. **Embedding Models:** Upgrading from `text-embedding-ada-002` (1536 dims) to `text-embedding-3-large` (3072 dims) yielded no significant accuracy gain.
4. **Hallucination Reducers (Validator & Merger):** Both the LLM self-check Validator and the bidirectional Merger ($O_s \Leftrightarrow O_t$) significantly boost **Precision and F1** at the cost of a tiny drop in Recall.
5. **Hyperparameter Trade-offs:** Optimal range is $T \in [0.90, 0.95]$ and $k \in [3, 4, 5]$. Higher $T$ and lower $k$ increase Precision (fewer false positives); lower $T$ and higher $k$ increase Recall (fewer missed matches).

---

## 5. Challenges, Limitations & Future Work

* **Moravec's Paradox in OM:** "The hard problems are easy and the easy problems are hard." Agent-OM excels at complex, non-trivial matches requiring deep background knowledge, but does not beat simple rule-based matchers on trivial string-matching tasks.
* **Linear Reasoning Limit:** CoT follows a single sequential path. Real human experts use branching, backtracking, and iterative refinement (e.g., Tree of Thoughts or Graph of Thoughts).
* **Hand-Crafted Prompts & Hallucinations:** Prompts must be manually tuned for different LLM families. Furthermore, while RAG and validation reduce hallucinations, they cannot eliminate them completely.
* **Scope Restrictions (TBox Equivalence Only):**
  * Excludes **ABox (instance/individual)** matching due to privacy risks of sending personal data to commercial LLM APIs.
  * Excludes **subsumption ($\subseteq, \supseteq$)** and complex logical axioms in the original prototype.
* **Cost & Latency:** Commercial APIs are expensive and rate-limited by providers; local open-source LLMs require heavy GPU hardware (e.g., RTX 4090) and run much slower than traditional matchers.
* **Future Work Directions:**
  1. **Multimodal OM:** Incorporating ontology diagrams and seminar videos.
  2. **Multilingual OM:** Aligning ontologies across different languages.
  3. **Small Language Models (SLMs):** Adapting 2B-parameter models for edge devices once their tool-calling interfaces mature.
  4. **Hybrid Integration:** Combining fast traditional syntactic matchers with Agent-OM so LLMs are only invoked for hard cases.

---

## 6. Relationship & Differences: Follow-Up OAEI Campaign Papers (2025 & 2026) vs. Main Paper

The provided document bundle includes the main foundation paper (*PVLDB 2024*) alongside its subsequent **OAEI 2025** and **OAEI 2026 Campaign Results papers** (and reproducibility appendices). Understanding how these later papers relate to and differ from the main paper is essential:

### Relationship to the Main Paper
* **From Theoretical Framework to Official Competition:** The main paper proposed the Agent-OM architecture and evaluated it offline against past OAEI 2022/2023 benchmarks. The follow-up papers report Agent-OM's **official participation in the live OAEI 2025 (8 tracks) and OAEI 2026 (5 tracks) campaigns**, testing the system on broader domains (Biodiversity, Digital Humanities, Circular Economy, Archaeology, Multilingualism).
* **Architectural Continuity:** The core Siamese-agent pipeline (Retrieval Agent + Matching Agent + Hybrid PostgreSQL/pgvector Database + RRF + Validator/Merger) remains the foundation across all papers.

### Key Differences & Evolutions Over Time

| Feature / Dimension | Main Paper (PVLDB 2024) | OAEI 2025 Campaign Paper | OAEI 2026 Campaign Paper |
| :--- | :--- | :--- | :--- |
| **Primary Focus** | Architectural design, ablation studies, and proof-of-concept validation on 3 tracks. | Production scaling, cost-effective open-source variant, OWL restrictions, and 8-track live evaluation. | Longitudinal study of **how newer LLM behaviors change OM performance** over a year. |
| **System Variants** | Single proof-of-concept system tested across 10 different LLMs. | Splits into two official variants:<br>1. **Agent-OM (Production):** Commercial (`gpt-4o` / `gpt-4o-mini` + `ada-002`) for small/medium tracks.<br>2. **Agent-OM-Lite:** Free local open-source (`llama-3-8b`/`70b`, 4096-dim embeddings) for large/private tracks. | Retains **Agent-OM** and **Agent-OM-Lite**, adding a new **Web Interface** for local execution and **Agent-OV** for ontology versioning. |
| **LLM Backends** | `gpt-4o`, `claude-3`, `llama-3`, `qwen-2`, `gemma-2`, `glm-4`. | Adds support for `DeepSeek-R1` and OpenAI open models; standardizes on `gpt-4o-2024-05-13` and `llama-3`. | Upgrades to **`gpt-5` / `gpt-5-mini`** (commercial) and **`llama-3.1-8b`** (open-source); deprecates older models. |
| **Semantic & Vocabulary Support** | Basic triple-based relations (`rdfs:subClassOf`) in OWL/RDFS; no complex axioms or blank nodes. | Upgraded to parse **nested OWL Restrictions (blank nodes)** and **SKOS** vocabularies (`skos:Concept`, `skos:broader`). Supports running without a reference alignment (generates a dummy reference). | Same structural support as 2025; identifies need for a **Model Context Protocol (MCP)** layer to integrate cleanly with the MELT evaluation platform. |
| **Reproducibility & Determinism** | Noted slight run-to-run variance due to LLM stochasticity (`temperature=0`). | Enforces strict determinism hyperparameters: `seed=42`, `top_k=1`, `top_p=1.0`, `repeat_penalty=1.0` (`presence/frequency_penalty=0.0`). | Notes that `gpt-5` removed timestamp tags and custom `top_p`/penalty controls, reducing strict reproducibility control on commercial APIs. |
| **Key Experimental Discovery** | Agent-OM beats state-of-the-art on complex/few-shot tasks and cuts token costs vs. naive LLM prompting. | **Multilingual & Domain insights:** Same-language/English pairs work best; RRF beats mean-scoring when semantic data is missing; proposes stopping after syntactic matching on simple biomedical tracks to save time. | **LLM Caution Shift:** Newer LLMs (`gpt-5`) have stricter provider guardrails and treat uppercase vs. lowercase words as distinct. The Validator rejects more uncertain mappings, causing **higher Precision but lower Recall** (e.g., 40 fewer matches in Anatomy). |
| **Evaluation Metrics** | Precision, Recall, F1, and total Token Cost. | Introduces **Normalized Reciprocal Rank ($RR^*$)** and **Mean Reciprocal Rank ($MRR^*$)** to compare rankings across tracks with different participant counts. | Proposes **Unit of Tokens (UoT)**—the average tokens consumed per discovered mapping—to replace wall-clock execution time, which is unfair due to API rate limits and GPU differences. |

---

## 7. 5-Slide Preliminary Project Presentation (RR1) Guide

Use this structured outline to build a clear, impactful 5-slide presentation:

### Slide 1: Problem Statement & Motivation
* **What is Ontology Matching (OM)?** Linking equivalent concepts across different domain dictionaries (ontologies) so computer systems can share data.
* **Limitations of Current Paradigms:**
  * *Expert Systems (LogMap, AML):* Accurate on simple tasks, but require expensive manual rules and domain experts.
  * *Machine Learning (BERTMap, Matcha):* Need large training datasets (1,000+ samples), which rarely exist for small ontologies (100–200 concepts).
* **Why Naive LLMs Fail at OM:** Asking an LLM "Yes/No" for every possible entity pair ($N_s \times N_t$) hits token limits, costs too much money, and suffers from **hallucinations** (made-up facts).
* **Project Goal:** Leverage autonomous **LLM Agents** (Planning + Tools + Hybrid Memory) to achieve accurate, low-cost, zero-training ontology matching.

### Slide 2: Agent-OM Architecture & Methodology
* **The "Siamese" Agent Paradigm:** Uses the LLM as a central controller ("brain") coordinating two agents that share a single hybrid database:
  1. **Retrieval Agent:** Extracts entities, normalizes names (*Syntactic*), prompts the LLM for context-aware definitions (*Lexical*), and turns relationships into sentences (*Semantic*).
  2. **Shared Hybrid Memory (PostgreSQL + pgvector):** Stores exact metadata (Class/Property) in a Relational DB and text embeddings in a Vector DB. Reduces complexity from $N_s \times N_t$ to linear search $(k+1)(N_s + N_t)$.
  3. **Matching Agent:** Runs cosine similarity searches ($T \ge 0.90$, $\text{top@}k = 3$), combines rankings via **Reciprocal Rank Fusion (RRF)**, and filters out hallucinations using an **LLM Self-Check Validator** and **Bidirectional Merger ($O_s \Leftrightarrow O_t$)**.

### Slide 3: Key Experimental Results & Evolution (2024–2026)
* **Breakthrough Performance (PVLDB 2024):**
  * Matches long-standing top systems on simple tasks (2nd in OAEI Anatomy Trivial).
  * **Beats state-of-the-art on complex & few-shot tasks** (1st in Materials Science & Engineering; beats 11/12 systems on Anatomy Non-Trivial).
  * Cuts token consumption by **~94%** compared to context-heavy naive LLM prompting.
* **Evolution in OAEI 2025 & 2026 Campaigns:**
  * Introduced **Agent-OM-Lite** (local `llama-3` / `llama-3.1`) for free, privacy-preserving large-scale matching alongside commercial **Agent-OM** (`gpt-4o` / `gpt-5`).
  * Added support for SKOS and complex OWL restrictions (blank nodes).
  * **2026 Discovery:** Newer LLMs (`gpt-5`) have stricter safety/certainty guardrails, making the validator more cautious—significantly boosting **Precision** while lowering **Recall**.

### Slide 4: Key Challenges & Limitations
* **Moravec's Paradox:** Agent-OM excels at hard semantic reasoning (abbreviations, domain context) but is overkill—and slightly less precise than simple string rules—on trivial exact-label matches.
* **Scope Constraints:** Currently limited to **TBox equivalence ($=$)** matching; ignores **ABox (instance data)** due to API privacy concerns and struggles to separate high-similarity **subsumption ($\subseteq$)** from equivalence.
* **Computational Bottlenecks:** High latency compared to traditional matchers; commercial APIs impose rate limits (RPM/TPM) and financial costs, while local open-source models require high-end GPUs.
* **Unbalanced & Dirty Ontologies:** Bidirectional validation wastes compute when matching a tiny ontology against a massive one; noisy ontology metadata (creator dates, external opaque codes) confuses LLM embeddings.

### Slide 5: Future Work & Project Opportunities
* **Hybrid Early-Stopping Pipeline:** Run fast syntactic matching first; only trigger expensive LLM lexical/semantic agents for unmatched or ambiguous entities.
* **Asymmetric Validation:** Start candidate search from the smaller ontology when aligning unbalanced ontologies to cut validation calls.
* **Advanced Reasoning Topologies:** Upgrade linear Chain-of-Thought (CoT) planning to **Tree-of-Thoughts (ToT)** or **Graph-of-Thoughts (GoT)** so agents can backtrack and use discovered matches in later iterations.
* **Standardized Benchmarking (UoT & MCP):** Adopt the **Unit of Tokens (UoT)** metric (tokens per mapping) for fair cost evaluation, and build a **Model Context Protocol (MCP)** interface for seamless OAEI MELT integration.
* **Multimodal & SLM Expansion:** Feed ontology diagrams into vision-language models and optimize tool-calling for 2B-parameter Small Language Models (SLMs).