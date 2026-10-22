# Study Guide: KROMA — Ontology Matching with Knowledge Retrieval and Large Language Models

*Note: Only one PDF (`Paper1.pdf` — KROMA) was attached to this request. To meet your requirement regarding a second paper, Section 9 explicitly compares KROMA against the primary baseline papers evaluated in the text (MILA, LLM4OM, OLaLa, and LLMap). If you have a specific second PDF, upload it and I will update that section immediately.*

---

## 1. Main Ideas & Motivation

### What is the problem?
* **Ontology:** A structured map of concepts and their relationships within a specific subject area (for example, medicine or materials science).
* **Ontology Matching (OM):** The process of finding concepts in two different ontologies that mean the same thing. This allows different computer systems to share and understand data together, a goal known as **semantic interoperability**.
* **Why existing methods struggle:**
  * *Rule-based and structural methods* rely on fixed, hand-written rules. They fail when encountering new or unfamiliar concepts.
  * *Traditional machine learning methods* require massive amounts of labeled training data, which is expensive and rare in scientific fields.
  * *Direct Large Language Model (LLM) prompting* simply asks an AI model if two words match. Without extra context, the LLM often guesses wrong (**hallucination**), exhibits low confidence, and costs too much time and money when comparing thousands of concepts.

### What is the proposed solution?
The authors introduce **KROMA**, a framework that combines three techniques to make ontology matching accurate and fast:
1. **Knowledge Retrieval:** It looks up extra information (definitions, synonyms, examples) from outside databases before asking the LLM. This process is called **Retrieval-Augmented Generation (RAG)**.
2. **Joint Embeddings:** It turns both the text description and the graph structure of a concept into numbers (**embeddings**) to quickly filter out obvious non-matches.
3. **Bisimilarity-Based Ontology Refinement:** It checks if two matching concepts also have matching parent and child concepts in their respective graphs. This prunes false matches and reduces the number of times the system needs to call the LLM.

---

## 2. Research Objectives & Contributions

### Research Questions
* **RQ1:** How well does KROMA improve upon state-of-the-art baselines across different LLM sizes?
* **RQ2:** How much do knowledge retrieval and ontology refinement individually contribute to matching accuracy?
* **RQ3:** How do alternative LLM reasoning strategies (multi-agent debating, deep chain-of-thought reasoning, and active sampling) affect ontology matching?

### Core Technical Contributions
1. **Mathematical Formulation of Equivalence:** Defines semantic equivalence using **ontological bisimilarity** and proves that for any given setup, there is a single, smallest, unique merged graph (called an optimal **concept graph**).
2. **RAG-Enriched LLM Framework:** Integrates external knowledge bases (via database queries) with joint structural-textual embeddings to build rich, accurate prompts for LLMs.
3. **Offline and Online Refinement Algorithms:** Provides fast algorithms that build the merged concept graph from scratch (**offline mode**) or update it continuously as new data arrives in a stream (**online mode**) in low polynomial time.
4. **Comprehensive Empirical Validation:** Demonstrates an average $F_1$ score improvement of **10.95%** over existing LLM-based matchers across 6 standard benchmark datasets, proving that small, cheap LLMs guided by KROMA can beat massive LLMs used by older systems.

---

## 3. Key Concepts & Terminology

| Term | Plain-Language Definition | Role in KROMA |
| :--- | :--- | :--- |
| **Ontology** $\mathcal{O} = (C, E)$ | A collection of concept names ($C$) connected by directed edges/relationships ($E$). | Treated as a **Directed Acyclic Graph (DAG)** (a graph with one-way arrows and no loops). |
| **Node Rank** $r(c)$ | A number showing how high up a concept is in the hierarchy. | Nodes with no children have rank $0$. Any other node's rank is $1$ plus the highest rank among its children. |
| **Ground Set** $c.\mathcal{I}$ | A list of real-world examples, synonyms, labels, and definitions belonging to concept $c$. | Gathered from external databases to give the LLM concrete context about what a concept actually means. |
| **Equivalence Class** $[c]$ | A group of concepts from the source and target ontologies that all mean the exact same thing. | Forms a single merged node in the final output graph. |
| **Concept Graph** $\mathcal{G_O} = (V_O, E_O)$ | The final, merged graph where each node is an equivalence class $[c]$. | Represents the unified ontology. KROMA proves its output $\mathcal{G_O}$ is minimal and unique. |
| **Concept Similarity** $F(c, c')$ | A score combining mathematical similarity and the LLM's yes/no answer. | Formula: $F(c, c') = \gamma \cdot \text{sim}(c, c') + (1 - \gamma) \cdot q(c, c', \mathcal{M})$. If $F(c, c') \ge \alpha$ (a chosen threshold), the concepts are considered similar. |
| **Ontological Bisimilarity** $R_{\simeq}$ | A strict rule stating two concepts are truly equivalent only if they are similar *and* their parents match *and* their children match. | Used to clean up errors. Even if two words look similar, they are separated if their surrounding graph structures conflict. |
| **SPARQL** | A query language used to search structured knowledge graphs (like SQL for graphs). | Used to fetch the ground set $c.\mathcal{I}$ from external knowledge bases. |

---

## 4. Architecture & Methodology (The 5-Stage Pipeline)

```
+-------------------------------------------------------------------+
| 1. INITIALIZATION                                                 |
|    Combine Source (Os) & Target (Ot) -> Compute Node Ranks r(c)   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 2. KNOWLEDGE RETRIEVAL (RAG)                                      |
|    2-Hop Neighbor Sampling -> Star SPARQL Queries -> Ground Sets  |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 3. EMBEDDING GENERATION & CANDIDATE FILTERING                     |
|    Graph (node2vec) + Text (SciBERT) -> Top-k Candidate Pairs (C) |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 4. PROMPT CONSTRUCTION & LLM INFERENCE                            |
|    Task + Examples + Ground Set Context -> LLM -> Yes/No + Conf.  |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 5. ONTOLOGY REFINEMENT & EXPERT VALIDATION                        |
|    Offline (Batch) / Online (Stream) Bisimilarity Split-Merge     |
|    Low Confidence (< 8.5) or Rank Conflicts -> Expert Validation  |
+-------------------------------------------------------------------+
```

### Step-by-Step Workflow
1. **Concept Graph Initialization:**
   * Takes source ontology $\mathcal{O}_s$ and target ontology $\mathcal{O}_t$, merges their nodes and edges into an initial graph $\mathcal{G_O}$, and calculates the structural rank $r(c)$ for every node from bottom to top.
2. **Knowledge Retrieval:**
   * **Neighborhood Sampling:** For each concept $c$, looks up to 2 steps away in the graph to grab its parents, children, and siblings.
   * **Subgraph Parameterization:** Turns that small local graph into a "star-shaped" **SPARQL** query by replacing specific names with search variables.
   * **Ground Set Curation:** Runs the query against an external knowledge base to fill the concept's ground set $c.\mathcal{I}$ with definitions, synonyms, and example entities (e.g., discovering that "coyote" relates to "siberian husky", helping match it to "wolfdog").
3. **Embedding Generation:**
   * Creates a combined number vector ($z_c$) for each concept using both graph structure (**node2vec**) and text meaning (**SciBERT**):
     $$z_c = \alpha \cdot \text{embd}_{\text{graph}}(c) + (1 - \alpha) \cdot \text{embd}_{\text{text}}(c)$$
   * Calculates similarity scores between all source and target pairs and keeps only the **top-$k$** highest-scoring pairs (set $\mathcal{C}$) so the LLM only has to check the most promising candidates.
4. **Prompt Querying LLMs:**
   * For each candidate pair in $\mathcal{C}$, builds a structured text prompt containing:
     1. *Task Description:* Decide if source and target are semantically equivalent.
     2. *In-Context Examples:* 5 labeled examples (both positive and negative matches).
     3. *Query Context:* Parents, children, synonyms, definitions, and ground sets for both concepts.
     4. *Output Format:* `<ans> Yes/No </ans>`.
     5. *Confidence:* `<conf> 0-10 </conf>`.
   * Accepts LLM answers with confidence $\ge 8.5$.
5. **Ontology Refinement & Active Validation:**
   * Runs the offline or online refinement algorithm to enforce ontological bisimilarity.
   * Routes low-confidence pairs ($< 8.5$) or structural rank conflicts to human domain experts using **active sampling** (prioritizing uncertain cases to minimize human effort).

---

## 5. Algorithms & Complexity Analysis

### Algorithm 1: Offline Refinement (Cold-Start / Batch Mode)
* **Goal:** Build the optimal concept graph $\mathcal{G_O}$ from scratch when both ontologies are fully known.
* **How it works (Bottom-Up Split-Merge):**
  1. Groups all concepts with the same structural rank $i$ into initial buckets $B_0, B_1, \dots, B_\rho$.
  2. Iterates from rank $0$ (bottom leaves) up to the highest rank $\rho$.
  3. Checks if concepts $c$ and $c'$ inside the same bucket $B_i$ are conceptually similar ($F(c, c') \ge \alpha$) and share matching neighbors (bisimilarity).
  4. If they do **not** match, invokes a `collapse` operation: splits $B_i$ into three pieces ($B_i \setminus \{c, c'\}$, $\{c\}$, and $\{c'\}$), checks if $c$ or $c'$ can merge into other existing buckets at that rank, and propagates the split upward to parent buckets at higher ranks ($j > i$).
* **Time Complexity:**
  * Refinement step alone: $O(|\mathcal{O}_s| + |\mathcal{O}_t|)$ (linear in the size of the ontologies).
  * Total KROMA workflow: $O(|C_s||C_t|T_I + (|C_s| + |C_t|)|KG| + (|\mathcal{O}_s| + |\mathcal{O}_t|))$, where $T_I$ is the cost of one LLM call and $|KG|$ is the size of the external knowledge graph.

### Algorithm 2: Online Refinement (Streaming Mode)
* **Goal:** Update $\mathcal{G_O}$ incrementally when new edges/concepts ($\Delta\mathcal{G}$) arrive continuously, avoiding a full rebuild from scratch.
* **How it works:**
  1. Retrieves knowledge for new concepts in $\Delta\mathcal{G}$, checks similarity via LLMs, and inserts them into existing rank buckets.
  2. Runs the bottom-up split-merge check only on affected buckets.
  3. **Conflict Caching:** Caches two types of conflicts into a priority queue $Q$ for human expert review:
     * *Confidence conflict:* Embedding similarity says "match", but the LLM has low confidence.
     * *Structural rank conflict:* A new edge goes from $c$ to $c'$, where $c \in [c_1]$ and $c' \in [c_2]$, but the rank of $[c_1]$ is lower than $[c_2]$ ($r(c_1) < r(c_2)$), which would create an illegal loop/cycle in the hierarchy.
* **Time Complexity:** $O(|\mathcal{G_O}| + |\Delta\mathcal{G}|\log|\Delta\mathcal{G}| + |\Delta\mathcal{G}|\log|V_O|)$ per batch update.

---

## 6. Experimental Setup & Results

### Setup Summary
* **Datasets (5 OAEI Tracks, 6 Pairs):**
  1. *Anatomy:* Mouse-Human (MH)
  2. *Bio-LLM:* NCIT-DOID (ND)
  3. *CommonKG:* Nell-DBpedia (NDB) and YAGO-Wikidata (YW)
  4. *BioDiv:* ENVO-SWEET (ES)
  5. *Materials Science & Engineering (MSE):* MI-MatOnto (MM)
* **LLMs Tested:** Ultra-lightweight to large off-the-shelf models (no fine-tuning of weights): DeepSeek-R1-Distill-Qwen-1.5B, Gemma-2B, Llama-3.2-3B, Mistral-7B, Llama-2-7B, GPT-4o-mini (8B), and Llama-3.3-70B.

### Key Results ($F_1$ Score Comparison)

| Dataset | Full KROMA (KL3.3) | No Refinement (KNR3.3) | No Knowledge Retrieval (KNB3.3 / KNKR3.3) | Best Prior Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Mouse-Human (MH)** | **94.94** | 91.25 | 86.59 | 92.20 (MILA) |
| **NCIT-DOID (ND)** | **98.63** | 95.01 | 90.91 | 94.80 (MILA) |
| **Nell-DBpedia (NDB)** | **97.08** | 94.26 | 93.58 | 96.00 (OLaLa) |
| **YAGO-Wikidata (YW)** | **95.54** | 91.98 | 89.74 | 92.19 (LLM4OM) |
| **ENVO-SWEET (ES)** | **93.18** *(GPT-4o-mini)* | 92.12 | 84.89 | 83.70 (MILA) |
| **MI-MatOnto (MM)** | **61.25** | 59.95 | 55.00 | 32.97 (MILA / LLM4OM) |

### Findings from Ablation & Reasoning Studies (RQ2 & RQ3)
* **Small Models Punch Above Their Weight:** KROMA with a tiny 1.5B model (Qwen-1.5B) beats the best prior baselines on 5 out of 6 datasets.
* **Knowledge Retrieval Impact:** Removing knowledge retrieval drops $F_1$ by **6.65%** on average (up to $-8.35$ points on Mouse-Human), proving external context is critical.
* **Ontology Refinement Impact:** Removing bisimilarity refinement drops $F_1$ by **2.68%** on average (up to $-3.69$ points), showing structural pruning removes false positives.
* **Multi-Agent Debating Fails to Beat Solo KROMA:** Having multiple LLM agents debate each other improves slightly from 3 to 5 rounds with 2 agents ($82.35 \rightarrow 85.06$ on MH), but adding 4 agents lowers accuracy ($80.95$) due to conflicting arguments. A single KROMA pass is much faster and more accurate ($90.78+$).
* **Deep Reasoning (`<think>` tags) Hurts Recall:** Forcing long Chain-of-Thought reasoning (DeepSeek-R1 style) increases output token length by **600%**, barely improves precision ($+0.07\%$), and hurts recall ($-3.38\%$), dropping overall $F_1$ by $1.65\text{--}2.01$ points. The model overthinks and rejects valid matches.
* **Active Sampling Boosts Semi-Supervised Performance:** Selecting low-confidence pairs for few-shot active learning reaches $98.00$ $F_1$ on NCIT-DOID, beating MILA ($94.67$) by $3.33$ points.

---

## 7. Challenges, Limitations & Future Work

### Challenges & Limitations
1. **Domain-Specific Sparsity (Materials Science):** On the MI-MatOnto dataset, KROMA's $F_1$ score is $61.25\%$ (Precision: $45.74\%$, Recall: $92.69\%$). While much better than baselines ($32.97\%$), highly specialized scientific domains lack rich external knowledge bases, causing more false positives.
2. **External Knowledge Base Dependency:** Knowledge retrieval time scales with the size of the external knowledge graph: $O((|C_s| + |C_t|)|KG|)$. If external SPARQL endpoints are slow, incomplete, or unavailable for a niche domain, KROMA loses its primary advantage (+6.65% $F_1$).
3. **Strict DAG Assumption:** KROMA models ontologies strictly as Directed Acyclic Graphs (DAGs). Ontologies with cyclic relationships or complex axiomatic logic must be simplified or handled by human experts when rank conflicts occur in online mode.
4. **Over-Filtering in Reasoning Models:** Verbose self-reflection (Long Chain-of-Thought) causes LLMs to second-guess valid alignments in binary yes/no tasks, reducing recall and inflating API costs by 6x.

### Potential Future Work
* **Better Reasoning Strategies:** Designing concise, structured reasoning prompts that avoid the recall drop and 600% token overhead seen in standard `<think>` models.
* **Broader Ontology Engineering Tasks:** Extending KROMA beyond 1-to-1 equivalence matching to handle ontology completion, taxonomy induction, and complex relation discovery (e.g., `part-of` vs. `subClassOf`).
* **Self-Contained / Fallback Retrieval:** Developing fallback context-generation strategies when external SPARQL knowledge graphs are missing (such as in specialized materials science datasets).
* **Automated Conflict Resolution:** Reducing reliance on human experts during online streaming when structural rank conflicts ($r(c_1) < r(c_2)$) occur.

---

## 8. 5-Slide Preliminary Presentation (RR1) Blueprint

| Slide | Title | Key Bullet Points to Include | Suggested Visual / Diagram |
| :---: | :--- | :--- | :--- |
| **1** | **Problem & Motivation: Ontology Matching at Scale** | • **Goal:** Align equivalent concepts across different ontologies for semantic interoperability.<br>• **Old Limits:** Rule-based systems lack adaptability; ML needs scarce training data.<br>• **LLM Trap:** Direct prompting causes hallucinations, low precision, and high API costs. | Side-by-side diagram showing two small ontologies ($\mathcal{O}_s, \mathcal{O}_t$) failing to align "wolfdog" and "coyote" without extra context. |
| **2** | **KROMA Architecture & Core Concepts** | • **Hybrid Pipeline:** Combines RAG, Joint Embeddings, LLMs, and Graph Bisimilarity.<br>• **Knowledge Retrieval:** 2-hop neighbor sampling + SPARQL queries to build a **Ground Set**.<br>• **Candidate Pruning:** `node2vec` (structure) + `SciBERT` (text) filters top-$k$ pairs before calling the LLM. | The 5-stage KROMA pipeline block diagram (Initialization $\rightarrow$ Retrieval $\rightarrow$ Embedding $\rightarrow$ Prompting $\rightarrow$ Refinement). |
| **3** | **Methodology: Bisimilarity & Refinement** | • **Ontological Bisimilarity:** Two concepts match only if their text/LLM scores match *and* their parent/child neighborhoods match.<br>• **Theoretical Guarantee:** Produces a provably minimal, unique **Concept Graph** ($\mathcal{G_O}$).<br>• **Dual Modes:** Offline (bottom-up rank split-merge in linear time) & Online (streaming updates + expert active sampling). | Visual of Figure 1: Showing how "house pet" and "carnivore" are split into separate nodes once ground sets (*chihuahua* vs. *wolf*) and bisimilarity are applied. |
| **4** | **Experimental Results & Ablation Insights** | • **SOTA Performance:** Beats MILA, OLaLa, and LLM4OM by **10.95%** average $F_1$ across 6 OAEI benchmarks.<br>• **Small LLM Efficiency:** KROMA + 1.5B model beats prior baselines using 7B–70B models.<br>• **Ablation Proof:** Knowledge Retrieval adds **+6.65%** $F_1$; Bisimilarity Refinement adds **+2.68%** $F_1$. | Bar chart or compact table comparing Full KROMA (KL3.3), No-Retrieval (KNKR), No-Refinement (KNR), and MILA across MH, ND, and MM datasets. |
| **5** | **Challenges, Limitations & Project Roadmap** | • **Surprising Finding:** Multi-agent debate and Long CoT (`<think>`) hurt recall and inflate outputs by 600%.<br>• **Key Limitation:** Low precision ($45.7\%$) on niche domains (MI-MatOnto) with sparse external KGs; strict DAG requirement.<br>• **Future Work / Next Steps:** Improve domain-specific retrieval for sparse KGs and automate online rank-conflict resolution. | Summary table contrasting "What Worked" (RAG, Bisimilarity, Active Sampling) vs. "Open Challenges" (Long CoT recall drop, MSE domain gap). |

---

## 9. Comparison with Related / Baseline Papers

*Since a second PDF file was not attached to the prompt, this section explicitly compares KROMA (the main paper) against the four state-of-the-art LLM-based ontology matching papers it directly builds upon and evaluates against. If your course assigns one of these (or another specific paper) as your second reading, use the comparison below.*

### Relationship to the Main Paper
All four baseline papers (**MILA**, **LLM4OM**, **OLaLa**, and **LLMap**) address the exact same core problem as KROMA: using Large Language Models to align concepts between a source and target ontology evaluated on OAEI benchmark tracks. They share a two-step philosophy: (1) use lightweight retrievers or embeddings to find candidate matches, and (2) use LLM prompts to verify the matches.

### Key Differences from KROMA

| Feature / Dimension | Main Paper: KROMA (2025) | Second Paper Candidate A: MILA (Taboada et al., 2025) | Second Paper Candidate B: LLM4OM (Giglou et al., 2024) | Second Paper Candidate C: OLaLa & LLMap (2023) |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Innovation** | External RAG (SPARQL ground sets) + global bisimilarity graph refinement (offline & online). | Prioritized Depth-First Search (DFS) heuristic to confirm easy matches before invoking the LLM. | Retrieval-Augmented pipeline combining TF-IDF and SBERT across 3 local graph representations. | Single-step prompt engineering (binary yes/no or multiple-choice) over SBERT candidates. |
| **Context Source** | **External + Internal:** 2-hop internal neighbors *plus* external Knowledge Bases queried via SPARQL. | **Internal Only:** Relies on internal ontology hierarchy and lexical labels. | **Internal Only:** Uses concept, concept-parent, and concept-children subgraphs within the input ontologies. | **Internal Only:** Uses local concept labels and immediate structural context. |
| **Structural Enforcement** | **Global Bisimilarity:** Enforces a strict mathematical equivalence relation ($R_{\simeq}$) via bottom-up split-merge. | **Search-Based:** Uses prioritized DFS traversal over the taxonomy, without bisimulation guarantees. | **Embedding-Based:** Encodes parent/child text into embeddings, no post-LLM structural refinement. | **None / Local Prompting:** Treats candidate pairs independently during LLM verification. |
| **Streaming / Online Support** | **Yes:** Includes `OnlineRefine` for incremental triple streams ($\Delta\mathcal{G}$) with active expert sampling. | **No:** Designed for static, batch ontology alignment. | **No:** Static batch pipeline. | **No:** Static batch pipeline. |
| **Performance vs. KROMA** | Highest $F_1$ across all 6 datasets (e.g., $94.94$ on MH, $61.25$ on MM). | Second best overall ($92.20$ on MH, $94.80$ on ND), but fails on Materials Science ($32.97$ on MM). | Strong on CommonKG ($94.26$ on NDB), weaker on Bio-LLM ($83.01$) and MSE ($32.97$). | High on NDB ($96.00$), but drops sharply on BioDiv ($51.10$ for OLaLa) and Bio-LLM ($72.10$ for LLMap). |