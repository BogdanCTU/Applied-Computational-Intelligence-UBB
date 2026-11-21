# Step 7B: Final Threshold Validation & LLM Validator Analysis Report

**Project:** Local Reproduction of Agent-OM (*Agent-OM: Leveraging LLM Agents for Ontology Matching*, PVLDB 2025)  
**Dataset:** OAEI Conference Benchmark — CMT (Source, 88 entities) to ConfOf (Target, 74 entities)  
**Ground Truth:** 16 Reference Correspondences (`reference.xml`)  
**Embedding Model:** `nomic-embed-text` (768-dimensional vectors in PostgreSQL 16 + pgvector)  
**Validation LLM:** `qwen3.5:9b` (Local Ollama, $\text{temperature}=0.0$, $\text{num\_ctx}=2048$, $\text{reasoning}=\text{False}$)  
**Evaluated Thresholds:** $\tau \in \{0.850, 0.875, 0.900\}$  
**Reference Baseline:** $\tau = 0.900$  
**Date:** October 31, 2026  

---

## 1. Executive Summary & Core Findings

In Step 7B, we executed the missing intermediate full-pipeline threshold experiment at **$\tau = 0.875$**, compared it directly against $\tau = 0.850$ and $\tau = 0.900$, and conducted an exhaustive investigation into LLM validation decisions, loss mechanisms, directional asymmetries, and database integrity.

### Key Empirical Findings

1. **$\tau = 0.875$ Fails to Improve Final Matching Quality:**
   - At $\tau = 0.875$, the full pipeline achieves **$\mathbf{P = 66.67\%, R = 25.00\%, F1 = 36.36\%}$** ($\text{TP}=4, \text{FP}=2, \text{FN}=12$), producing the **exact same final correspondences** as the reference configuration at $\tau = 0.900$.
   - However, the LLM validator workload surges from **$8$ to $19$ invocations ($+137.5\%$)**, prompt tokens increase from $354$ to $838$, and latency increases from $42.4$s to $66.1$s, providing **zero additional True Positives**.
   - `ProgramCommitteeMember ↔ Member_PC` is missed at $\tau = 0.875$ because its maximum vector similarity under `nomic-embed-text` is **$0.8525$**, which falls just below the $0.875$ cutoff. Only lowering $\tau$ to **$0.850$** unlocks this true positive, reaching **$F1 = 43.48\%$** with $5$ TPs.

2. **Linguistic Homonym Asymmetry in `Chair_PC`:**
   - We isolated the exact cause of directional asymmetry for `ProgramCommitteeChair ↔ Chair_PC`.
   - In Source $\rightarrow$ Target (`Is program committee chair equivalent to chair pc?`), the LLM anchors on the domain phrase and answers **Yes**.
   - In Target $\rightarrow$ Source (`Is chair pc equivalent to program committee chair?`), because Agent-OM's `cleaning()` function lowercases all strings, the model encounters `"chair pc"` as the subject, associates `"chair"` with computer furniture, and begins with **"No. 'chair pc' (lowercase) could be misinterpreted as referring to a chair of a Personal Computer..."**.
   - Because the reciprocal merger requires both directions to accept the match, this lowercased homonym bias eliminates `ProgramCommitteeChair = Chair_PC` from the final alignment across all thresholds.

3. **Subtle Generalization Rejections by the LLM:**
   - The LLM rejected three ground-truth pairs that were retrieved: `ConferenceMember -> Member` (rejected because "conference member" is a specific hyponym of "member"), `email -> hasEmail` (rejected because "email" is a service while "has email" is an attribute), and `title -> hasTitle` (rejected as noun vs. property assertion).
   - In contrast, the LLM accepted false positive pairs like `ConferenceMember -> Person` and `Participant -> Person`, but the **reciprocal merger successfully eliminated these false positives**.

4. **Lower-Bound Similarity Ceiling for 3 Ground-Truth Pairs:**
   - `hasAuthor ↔ writtenBy` ($\text{max} = 0.7624$), `hasBeenAssigned ↔ reviewes` ($\text{max} = 0.7775$), and `hasSubjectArea ↔ dealsWith` ($\text{max} = 0.7371$) have maximum cosine similarities strictly below $0.780$ across syntactic, lexical, and semantic spaces.
   - Consequently, no threshold $\tau \ge 0.800$ could ever retrieve these three pairs under `nomic-embed-text`.

---

## 2. Part A: Threshold Validation Experiment ($\tau = 0.875$) vs. $\tau = 0.850$ & $\tau = 0.900$

We executed the complete pipeline (RRF $k=0$, `qwen3.5:9b`, `temp=0.0`, reciprocal merger) on $\tau = 0.875$, $\tau = 0.850$, and $\tau = 0.900$.

### Table 2.1: Direct Comparative Performance Matrix

| Metric / Dimension | $\tau = 0.850$ | $\tau = 0.875$ | $\tau = 0.900$ (Reference) | Difference (0.875 vs 0.900) | Difference (0.850 vs 0.900) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Source $\rightarrow$ Target Predictions** | 9 | 7 | 7 | 0 | +2 |
| S $\rightarrow$ T True Positives (TP) | 6 | 5 | 5 | 0 | +1 |
| S $\rightarrow$ T False Positives (FP) | 3 | 2 | 2 | 0 | +1 |
| S $\rightarrow$ T False Negatives (FN) | 10 | 11 | 11 | 0 | -1 |
| S $\rightarrow$ T Precision (%) | 66.67% | 71.43% | 71.43% | 0.00% | -4.76% |
| S $\rightarrow$ T Recall (%) | 37.50% | 31.25% | 31.25% | 0.00% | +6.25% |
| S $\rightarrow$ T F1 Score (%) | 48.00% | 43.48% | 43.48% | 0.00% | +4.52% |
| **Target $\rightarrow$ Source Predictions** | 8 | 6 | 6 | 0 | +2 |
| T $\rightarrow$ S True Positives (TP) | 5 | 4 | 4 | 0 | +1 |
| T $\rightarrow$ S False Positives (FP) | 3 | 2 | 2 | 0 | +1 |
| T $\rightarrow$ S False Negatives (FN) | 11 | 12 | 12 | 0 | -1 |
| T $\rightarrow$ S Precision (%) | 62.50% | 66.67% | 66.67% | 0.00% | -4.17% |
| T $\rightarrow$ S Recall (%) | 31.25% | 25.00% | 25.00% | 0.00% | +6.25% |
| T $\rightarrow$ S F1 Score (%) | 41.67% | 36.36% | 36.36% | 0.00% | +5.31% |
| **Reciprocal Merged Predictions** | **7** | **6** | **6** | **0** | **+1** |
| Reciprocal True Positives (TP) | **5** | **4** | **4** | **0** | **+1** |
| Reciprocal False Positives (FP) | 2 | 2 | 2 | 0 | 0 |
| Reciprocal False Negatives (FN) | 11 | 12 | 12 | 0 | -1 |
| **Reciprocal Precision (%)** | **71.43%** | **66.67%** | **66.67%** | **0.00%** | **+4.76%** |
| **Reciprocal Recall (%)** | **31.25%** | **25.00%** | **25.00%** | **0.00%** | **+6.25%** |
| **Reciprocal F1 Score (%)** | **43.48%** | **36.36%** | **36.36%** | **0.00%** | **+7.12%** |
| **Validator Workload** | | | | | |
| Exact-Name Bypasses | 12 | 12 | 12 | 0 | 0 |
| Actual LLM Validation Calls | 37 | 19 | 8 | **+11 (+137.5%)** | **+29 (+362.5%)** |
| LLM Accepted Decisions | 5 | 1 | 1 | 0 | +4 |
| LLM Rejected Decisions | 32 | 18 | 7 | +11 | +25 |
| Prompt Tokens | 1,639 | 838 | 354 | +484 (+136.7%) | +1,285 (+363.0%) |
| Completion Tokens | 2,202 | 1,137 | 542 | +595 (+109.8%) | +1,660 (+306.3%) |
| Execution Duration (s) | 105.96s | 66.06s | 42.44s | +23.62s (+55.7%) | +63.52s (+149.7%) |

---

### Table 2.2: Final Correspondence-Level Comparison

| Correspondence | Ground Truth? | $\tau = 0.900$ (Ref) | $\tau = 0.875$ | $\tau = 0.850$ | Matching Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `Administrator = Administrator` |  Yes (TP) |  Yes |  Yes |  Yes | Exact-name bypass |
| `Author = Author` |  Yes (TP) |  Yes |  Yes |  Yes | Exact-name bypass |
| `Conference = Conference` |  Yes (TP) |  Yes |  Yes |  Yes | Exact-name bypass |
| `Person = Person` |  Yes (TP) |  Yes |  Yes |  Yes | Exact-name bypass |
| `ProgramCommitteeMember = Member_PC` |  Yes (TP) | ❌ Missed | ❌ Missed |  **Yes** | Below $0.875$ cutoff; unlocked & merged at $\tau=0.850$ |
| `Paper = Paper` | ❌ No (FP) | ⚠️ Yes | ⚠️ Yes | ⚠️ Yes | Exact-name bypass trap (GT is `Paper = Contribution`) |
| `writtenBy = writtenBy` | ❌ No (FP) | ⚠️ Yes | ⚠️ Yes | ⚠️ Yes | Exact-name bypass trap (GT is `hasAuthor = writtenBy`) |
| `ProgramCommitteeChair = Chair_PC` |  Yes (FN) | ❌ Dropped | ❌ Dropped | ❌ Dropped | Accepted in S $\rightarrow$ T, but rejected in T $\rightarrow$ S (`"chair pc"`) |
| `title = hasTitle` |  Yes (FN) | ❌ Dropped | ❌ Dropped | ❌ Dropped | Rejected by LLM as noun vs property predicate |
| `email = hasEmail` |  Yes (FN) | ❌ Not in 0.90 | ❌ Dropped | ❌ Dropped | Rejected by LLM as tool vs state attribute |
| `ConferenceMember = Member` |  Yes (FN) | ❌ Not in 0.90 | ❌ Dropped | ❌ Dropped | Rejected by LLM as specific subtype vs general member |

---

## 3. Part B: Comprehensive LLM Validation Loss Investigation

All 100 validation records across the three runs were logged to [`agent_om_local/output/step7b_validation_decisions.csv`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_validation_decisions.csv). We categorized every validation decision to evaluate the failure modes.

### 3.1. Ground-Truth Correspondences Retrieved but Rejected by Validator (False Negatives)

Four distinct reference correspondences entered candidate score groups but were rejected by the LLM:

#### Case 1: `title ↔ hasTitle` (Evaluated at $\tau \in \{0.850, 0.875, 0.900\}$)
- **Source Entity:** `http://cmt#title` (Property)
- **Target Entity:** `http://confOf#hasTitle` (Property)
- **Retrieval Similarity:** Syntactic = 0.9292, Lexical = 0.8238, Semantic = 0.7351.
- **Direction:** Source $\rightarrow$ Target
- **Exact Prompt:**
  ```text
  Question: Is title equivalent to has title?
  Context: conference
  Answer the question within the context.
  Answer yes or no. Give a short explanation.
  ```
- **Raw LLM Response:**
  ```text
  No. In the context of conferences, "title" typically refers to the name of the event itself (e.g., "International AI Conference"), whereas "has title" is a property or field indicating whether a specific item (like a paper or session) possesses a name. One defines the entity, while the other asserts the existence of that definition for an instance.
  ```
- **Root Cause:** The LLM's prompt contains bare entity names without ontological metadata indicating that both entities are OWL datatype properties. The model interprets bare `"title"` as the conference's title and `"has title"` as an existential predicate.

#### Case 2: `email ↔ hasEmail` (Evaluated at $\tau \in \{0.850, 0.875\}$)
- **Source Entity:** `http://cmt#email` (Property)
- **Target Entity:** `http://confOf#hasEmail` (Property)
- **Retrieval Similarity:** Syntactic = 0.8888, Lexical = 0.7916, Semantic = 0.8380.
- **Direction:** Source $\rightarrow$ Target
- **Exact Prompt:**
  ```text
  Question: Is email equivalent to has email?
  Context: conference
  Answer the question within the context.
  Answer yes or no. Give a short explanation.
  ```
- **Raw LLM Response:**
  ```text
  No. In the context of a conference, "email" refers to the electronic messaging system itself, whereas "has email" describes an attribute indicating that a person or entity possesses an email address or account. One is a tool/service, and the other is a state or capability.
  ```
- **Root Cause:** Same linguistic phenomenon. The model distinguishes the noun concept (system/tool) from the relational attribute (`has email`).

#### Case 3: `ConferenceMember ↔ Member` (Evaluated at $\tau = 0.875$)
- **Source Entity:** `http://cmt#ConferenceMember` (Class)
- **Target Entity:** `http://confOf#Member` (Class)
- **Retrieval Similarity:** Syntactic = 0.7604, Lexical = 0.8896, Semantic = 0.7137.
- **Direction:** Source $\rightarrow$ Target
- **Exact Prompt:**
  ```text
  Question: Is conference member equivalent to member?
  Context: conference
  Answer the question within the context.
  Answer yes or no. Give a short explanation.
  ```
- **Raw LLM Response:**
  ```text
  No. A "conference member" is a specific type of member who participates in a particular conference, whereas "member" is a general term that can apply to any group or organization without specifying the context of a conference.
  ```
- **Root Cause:** Strict taxonomic pedantry. The LLM refuses equivalence because `ConferenceMember` is formally a subtype (hyponym) of generic `Member`, despite the OAEI reference alignment asserting an equivalence correspondence.

---

### 3.2. Directional Asymmetry Analysis: `Chair_PC` vs. `Member_PC`

We compared how the LLM evaluated `ProgramCommitteeChair ↔ Chair_PC` versus `ProgramCommitteeMember ↔ Member_PC` across both directions:

```mermaid
flowchart TD
    subgraph "ProgramCommitteeChair ↔ Chair_PC (Asymmetric Failure)"
        S1["Source -> Target: Is program committee chair equivalent to chair pc?"] --> R1["Response: Yes. Both refer to the same role... (Accepted)"]
        T1["Target -> Source: Is chair pc equivalent to program committee chair?"] --> R2["Response: No. 'chair pc' (lowercase) could be misinterpreted as a chair of a Personal Computer... (Rejected)"]
        R1 & R2 --> M1["Reciprocal Merger: Intersection FAILS -> Dropped"]
    end

    subgraph "ProgramCommitteeMember ↔ Member_PC (Symmetric Success)"
        S2["Source -> Target: Is program committee member equivalent to member pc?"] --> R3["Response: Yes. Both refer to the same role... (Accepted)"]
        T2["Target -> Source: Is member pc equivalent to program committee member?"] --> R4["Response: Yes. PC is standard abbreviation for Program Committee... (Accepted)"]
        R3 & R4 --> M2["Reciprocal Merger: Intersection SUCCEEDS -> Retained"]
    end
```

#### Detailed Comparison:
1. **`ProgramCommitteeChair ↔ Chair_PC`:**
   - **Source $\rightarrow$ Target:** Prompt asks `Is program committee chair equivalent to chair pc?`. Because `"program committee chair"` is the initial subject, the model primes its reasoning with academic conference administration, recognizing `"chair pc"` as an abbreviation. Decision: **Yes**.
   - **Target $\rightarrow$ Source:** Prompt asks `Is chair pc equivalent to program committee chair?`. Here, `"chair pc"` is the initial subject. Because `cleaning()` lowercases all strings, `"Chair_PC"` was transformed to `"chair pc"`. The English word `"chair"` is polysemous (furniture vs. leader). The model literally reasons that `"chair pc"` could denote *furniture for a computer*, issuing a **No** verdict!
   - **Reciprocal Result:** Dropped by the merger because of this directional asymmetry.

2. **`ProgramCommitteeMember ↔ Member_PC`:**
   - **Source $\rightarrow$ Target:** Prompt asks `Is program committee member equivalent to member pc?`. Decision: **Yes**.
   - **Target $\rightarrow$ Source:** Prompt asks `Is member pc equivalent to program committee member?`. Here, `"member"` has no physical furniture homonym. The model immediately parses `"member pc"` as a person holding membership in the PC (Program Committee), noting: *"In the context of academic conferences, 'PC' is the standard abbreviation for 'Program Committee,' so a 'member PC' refers to a Program Committee member..."*. Decision: **Yes**.
   - **Reciprocal Result:** Retained and merged at $\tau = 0.850$.

---

### 3.3. Incorrect Correspondences Accepted by Validator (False Positives)

The LLM accepted three non-reference candidate pairs:
1. `ConferenceMember -> Person` (Accepted in S $\rightarrow$ T at $\tau = 0.850$):
   *LLM Reasoning:* "Yes. A conference member is a specific type of person who participates in a conference, making them equivalent to a person within that context."
2. `Participant -> Person` (Accepted in T $\rightarrow$ S at $\tau = 0.850$):
   *LLM Reasoning:* "Yes. In the context of a conference, a 'participant' is a specific type of 'person' who is actively involved in the event..."
3. `Paper = Paper` and `writtenBy = writtenBy` (Accepted at all thresholds):
   *Accepted by:* Exact-name bypass rule (12 bypass evaluations).

> [!IMPORTANT]
> **Safety Role of the Reciprocal Merger:**
> Although the LLM erroneously accepted `ConferenceMember -> Person` and `Participant -> Person`, **neither pair entered the final alignment**. 
> In CMT, `Person` matched with ConfOf `Person` via exact-name bypass. Because `ConferenceMember` and `Participant` could not achieve reciprocal agreement with `Person`, the reciprocal merger discarded both false positives.

---

## 4. Part C: Analysis of the Three Unretrieved Correspondences

The three correspondences that never entered the candidate pool even at $\tau = 0.800$ were evaluated using exact directional vector similarity queries in PostgreSQL.

### Table 4.1: Directional Strategy Similarity Matrix

| Reference Correspondence | Strategy | Source $\rightarrow$ Target Sim | Target $\rightarrow$ Source Sim | Max Directional Sim | Min Threshold for Eligibility | Retrievable at $\tau \le 0.800$? | Reciprocal Merger Retention? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`hasAuthor ↔ writtenBy`** | Syntactic | 0.6734 | 0.6734 | **0.7624** | **0.7624** | ❌ No | ❌ Impossible ($\tau < 0.800$) |
| | Lexical | 0.7624 | 0.7624 | | | | |
| | Semantic | 0.7598 | 0.7598 | | | | |
| **`hasBeenAssigned ↔ reviewes`** | Syntactic | 0.4892 | 0.4892 | **0.7775** | **0.7775** | ❌ No | ❌ Impossible ($\tau < 0.800$) |
| | Lexical | 0.6397 | 0.6397 | | | | |
| | Semantic | 0.7775 | 0.7775 | | | | |
| **`hasSubjectArea ↔ dealsWith`** | Syntactic | 0.4865 | 0.4865 | **0.7371** | **0.7371** | ❌ No | ❌ Impossible ($\tau < 0.800$) |
| | Lexical | 0.7371 | 0.7371 | | | | |
| | Semantic | 0.7323 | 0.7323 | | | | |

### Structural Retrieval Barriers:
1. **Syntactic Decoupling:** Non-cognate property names share zero normalized tokens (`hasAuthor` vs `writtenBy`, `hasSubjectArea` vs `dealsWith`). Syntactic scores hover between $0.48$ and $0.67$.
2. **Generic Lexical Descriptions:** Without ontology-specific context stating that "deals with" denotes a conference subject area, general language models embed them in disjoint semantic spaces ($\sim 0.73$).
3. **Graph Neighborhood Sparsity:** Semantic triples for properties in CMT and ConfOf lack rich relational constraints, capping semantic similarity at $0.7775$.

---

## 5. Part D: Database Integrity and Safety Audit

We audited the database recovery mechanism (`ensure_database_populated`) and test isolation behaviors:

### Audit Checklist & Empirical Verification

1. **Host and Database Exclusivity:**
   - Verified that `DatabaseManager` connects exclusively to `postgresql://postgres:postgres@127.0.0.1:5432/agent_om_local`.
   - Verified that PostgreSQL is bound exclusively to `127.0.0.1`, with no remote listening interfaces enabled.
2. **Idempotence & Non-Destructive Behavior:**
   - We executed `ensure_database_populated(db)` twice consecutively on the populated database.
   - Record counts before and after:
     - Run 1: Source = 88, Target = 74 (Total = 162). Chunks: syn=162, lex=206, sem=258.
     - Run 2: Source = 88, Target = 74 (Total = 162). Chunks: syn=162, lex=206, sem=258.
     - Difference: **Zero insertions, zero deletions, zero modifications**.
3. **Identification of Test Contamination & Resolution:**
   - *Defect Identified:* Running integration tests in `test_retrieval_agent.py` previously invoked `create_ontology_matching_table` with 4 test dummy entities, dropping and overwriting production tables.
   - *Resolution Applied:* Added a class-level teardown fixture (`TestRetrievalAgent.teardown_class`) that automatically re-ingests the 162 CMT-ConfOf entities whenever the test suite completes.
   - *Verification:* Running the full 94-test pytest suite verified that the database remained fully intact with 162 entities upon test conclusion.
4. **Dataset Integrity:**
   - `original_repo/` remains completely clean and unmodified (`git -C original_repo status -s` returns 0 changes).

---

## 6. Part E: Experimental Accounting Audit

We audited all CSV, JSON, and report metrics to ensure methodological consistency:

1. **Candidate Union Deduplication:**
   Candidate Union counts represent **distinct correspondence pairs**, computed as the mathematical set union of normalized `(source_uri, target_uri)` tuples. They do not represent raw directional row counts.
2. **Consistent Correspondence Orientation:**
   Both Source $\rightarrow$ Target and Target $\rightarrow$ Source directional results are stored and evaluated with normalized `(Source_URI, Target_URI)` orientation, ensuring that reciprocal intersection (`S2T.intersection(T2S)`) evaluates identical semantics.
3. **RRF Top-1 vs. Candidate Union Separation:**
   Candidate Union reflects all pairs exceeding $\tau$ before fusion. RRF Top-1 reflects the highest-ranked candidate per entity after multi-strategy reciprocal rank fusion ($k=0$).
4. **LLM Calls vs. Exact-Name Bypasses:**
   Exact-name bypasses (12 per directional pass) bypass LLM inference entirely and are accounted for separately. LLM call metrics count only genuine Ollama model invocations.
5. **Reference Alignment Invariance:**
   All precision, recall, and F1 calculations across all stages and thresholds strictly use the identical set of **16 reference correspondences** from `reference.xml`.

---

## 7. Part F: Research Interpretation & Trade-Off Analysis

### Comparative Analysis: $\tau = 0.850$, $\tau = 0.875$, and $\tau = 0.900$

```
Threshold:           0.900 (Reference)               0.875                         0.850
Final F1:                 36.36%                     36.36%                        43.48%
Final TPs:                  4                          4                             5
LLM Calls:                  8                          19                           37
Efficiency:         42.4s (354 tok)            66.1s (838 tok)             106.0s (1,639 tok)
Verdict:            [Baseline]             [Workload Penalty]             [Optimal Frontier]
```

1. **Does $\tau = 0.875$ Improve Final Matching?**
   **No.** $\tau = 0.875$ produces identical final matches to $\tau = 0.900$ ($F1 = 36.36\%$). The additional candidate pairs retrieved between $0.875$ and $0.900$ (`ConferenceMember = Member`, `email = hasEmail`) are either rejected by the validator or fail reciprocal agreement. The $137.5\%$ increase in LLM calls represents wasted computation.

2. **Why $\tau = 0.850$ is Superior for CMT–ConfOf:**
   $\tau = 0.850$ crosses the similarity threshold for `ProgramCommitteeMember = Member_PC` ($0.8525$). Because both directional prompts for this correspondence receive unambiguous "Yes" decisions from `qwen3.5:9b`, lowering $\tau$ to $0.850$ directly yields a **$+7.12\%$ boost in final F1**.

3. **Non-Generalizability of Thresholds:**
   $\tau = 0.850$ cannot be treated as a universally optimal threshold across ontology matching benchmarks. 
   - Vector similarities depend on the embedding model's dimensionality and training distribution (`nomic-embed-text` scores lower on abbreviations than `text-embedding-ada-002`).
   - Different ontology pairs (e.g. Conference–Ekaw, Anatomy, Bio-ML) possess vastly different naming conventions, lexical densities, and taxonomic structures.
   - Any fixed threshold $\tau$ must be calibrated per embedding model and domain.

---

## 8. Deliverables & Artifact Index

All generated assets are stored within `agent_om_local/`:

1. **Report:**
   - [`docs/step7b_threshold_validation_report.md`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/docs/step7b_threshold_validation_report.md)
   - Brain Artifact: [step7b_threshold_validation_report.md](file:///C:/Users/bctod/.gemini/antigravity/brain/556e18ff-96e7-42eb-a23c-e14b7fe2ee5a/step7b_threshold_validation_report.md)
2. **Prediction CSV:**
   - [`output/step7b_predictions_tau_875.csv`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_predictions_tau_875.csv)
3. **Threshold Comparison CSV:**
   - [`output/step7b_threshold_comparison.csv`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_threshold_comparison.csv)
4. **Validation Decisions CSV:**
   - [`output/step7b_validation_decisions.csv`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_validation_decisions.csv) (100 evaluated pairs with prompt, raw response, decision, failure type)
5. **Similarity Analysis CSV:**
   - [`output/step7b_similarity_analysis.csv`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_similarity_analysis.csv) (Directional similarity breakdown for all 16 reference pairs)
6. **Summary JSON:**
   - [`output/step7b_summary.json`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/output/step7b_summary.json)
7. **Unit Test Suite:**
   - [`tests/test_threshold_validation_step7b.py`](file:///E:/_3_Master/_9_ACL_Project/agent_om_local/tests/test_threshold_validation_step7b.py)
   - Full test run: **94 / 94 passed** in 13.59s.

