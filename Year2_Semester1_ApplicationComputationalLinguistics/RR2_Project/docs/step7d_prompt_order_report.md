# Step 7D — Experiment A2: Directional Prompt Sensitivity Report

**Date:** 2026-10-31  
**Project:** Local Reproduction of Agent-OM (PVLDB 2025)  
**Dataset:** OAEI Conference Benchmark — CMT (Source, 88 entities) to ConfOf (Target, 74 entities)  
**Reference Correspondences:** 16 standard ground truth correspondences  
**Baseline Model:** Ollama `qwen3.5:9b` (Temperature = 0)  
**Vector Configuration:** Native PostgreSQL 16 + pgvector, `nomic-embed-text` (768-dim), $\tau = 0.850$  
**Evaluation Script:** [`scripts/run_step7d_prompt_order_ablation.py`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/scripts/run_step7d_prompt_order_ablation.py)  
**Output Files:**
- [`output/step7d_prompt_order_comparison.csv`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_prompt_order_comparison.csv)
- [`output/step7d_validation_decisions.csv`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_validation_decisions.csv)
- [`output/step7d_summary.json`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_summary.json)
- Unit Tests: [`tests/test_prompt_order_ablation.py`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/tests/test_prompt_order_ablation.py)

---

## 1. Executive Summary

In Step 7B, the LLM validation loss audit revealed that the correspondence `ProgramCommitteeChair ↔ Chair_PC` was retrieved in both Source $\rightarrow$ Target and Target $\rightarrow$ Source directions at $\tau = 0.850$, yet failed to appear in final predictions because the LLM validator accepted it in the forward direction (`Source -> Target`) but rejected it in the reverse direction (`Target -> Source`).

As formulated in the Step 7C Master Ablation Design (`docs/step7c_ablation_plan.md`), **Experiment A2 (Directional Prompt Sensitivity)** systematically investigated whether this failure was driven by asymmetric entity positioning in the validation prompt:
$$\text{Is } \{E_1\} \text{ equivalent to } \{E_2\}\text{?}$$

We evaluated three strictly controlled variants using the frozen candidate set snapshot at $\tau = 0.850$:
1. **A2.1 (Original Ordering):** `Is {query_entity} equivalent to {candidate_entity}?` (Original Agent-OM behavior).
2. **A2.2 (Reversed Ordering):** `Is {candidate_entity} equivalent to {query_entity}?`.
3. **A2.3 (Canonical Ordering):** `Is {source_entity} equivalent to {target_entity}?` (Enforces direction-invariant prompt syntax).

### Key Empirical Findings:
1. **Asymmetry Decoupled:** In A2.1, the forward prompt `Is program committee chair equivalent to chair pc?` answered **Yes**, while the reverse prompt `Is chair pc equivalent to program committee chair?` answered **No**. Reversing the ordering (A2.2) perfectly mirrored this behavior: forward answered **No** and reverse answered **Yes**. In both A2.1 and A2.2, the reciprocal merger dropped the pair due to asymmetric decisions ($F_1 = 43.48\%$).
2. **Canonical Ordering Recovers True Positive:** In A2.3, by anchoring the prompt canonically (`Is program committee chair equivalent to chair pc?` in both directions), the LLM answered **Yes** symmetrically. The reciprocal merger retained the correspondence, increasing True Positives from **5 to 6** and raising reciprocal $F_1$ from **43.48% to 50.00%**.
3. **Hyponym/Hypernym Asymmetry:** The LLM consistently exhibited directional bias on hierarchical concept pairs (e.g., `Is conference member equivalent to person?` $\rightarrow$ **Yes**, but `Is person equivalent to conference member?` $\rightarrow$ **No**). The reciprocal merger functioned effectively as a directional safety filter, blocking these unilateral false positives.
4. **Methodological Caveat:** The performance gain of A2.3 ($+6.52\% F_1$) represents a **direction-invariance intervention** rather than an increase in semantic capability. Canonicalization ensures identical prompt semantics across both merger legs, preventing artificial omission caused by token-order sensitivity.

---

## 2. Comparative Performance Metrics

All experiments were evaluated on the 16 reference correspondences under identical retrieval candidates ($\tau = 0.850$), exact-name bypass rules, and zero temperature.

### Table 1: Performance Across Prompt Ordering Variants ($\tau = 0.850$)

| Variant | Prompt Formulation (S $\rightarrow$ T / T $\rightarrow$ S) | Direction | Pred | TP | FP | FN | Precision | Recall | $F_1$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A2.1 Original** | S $\rightarrow$ T: `Is {query} eq to {cand}?`<br>T $\rightarrow$ S: `Is {query} eq to {cand}?` | Source $\rightarrow$ Target<br>Target $\rightarrow$ Source<br>**Reciprocal** | 9<br>8<br>**7** | 6<br>5<br>**5** | 3<br>3<br>**2** | 10<br>11<br>**11** | 66.67%<br>62.50%<br>**71.43%** | 37.50%<br>31.25%<br>**31.25%** | 48.00%<br>41.67%<br>**43.48%** |
| **A2.2 Reversed** | S $\rightarrow$ T: `Is {cand} eq to {query}?`<br>T $\rightarrow$ S: `Is {cand} eq to {query}?` | Source $\rightarrow$ Target<br>Target $\rightarrow$ Source<br>**Reciprocal** | 7<br>8<br>**7** | 5<br>6<br>**5** | 2<br>2<br>**2** | 11<br>10<br>**11** | 71.43%<br>75.00%<br>**71.43%** | 31.25%<br>37.50%<br>**37.50%** | 43.48%<br>50.00%<br>**43.48%** |
| **A2.3 Canonical**| S $\rightarrow$ T: `Is {source} eq to {target}?`<br>T $\rightarrow$ S: `Is {source} eq to {target}?` | Source $\rightarrow$ Target<br>Target $\rightarrow$ Source<br>**Reciprocal** | 9<br>8<br>**8** | 6<br>6<br>**6** | 3<br>2<br>**2** | 10<br>10<br>**10** | 66.67%<br>75.00%<br>**75.00%** | 37.50%<br>37.50%<br>**37.50%** | 48.00%<br>50.00%<br>**50.00%** |

### Table 2: Computational and Validation Accounting

| Metric | A2.1 (Original) | A2.2 (Reversed) | A2.3 (Canonical) | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Total Validation Records** | 49 | 53 | 49 | Includes bypassed & LLM pairs |
| **Exact-Name Bypasses** | 12 | 12 | 12 | Identical across all variants |
| **Actual LLM Invocations** | 37 | 41 | 37 | A2.2 evaluated extra candidates in score group 2 |
| **LLM Decisions (Yes / No)**| 5 Yes / 32 No | 3 Yes / 38 No | 5 Yes / 32 No | Stricter rejection in reversed framing |
| **Prompt Tokens** | 1,639 | 1,816 | 1,639 | Zero-overhead canonicalization |
| **Completion Tokens** | 2,202 | 2,486 | 2,239 | Detailed natural language reasoning |
| **Total Wall-Clock Time** | 82.3 s | 93.0 s | 82.4 s | ~2.2 s per LLM inference |

---

## 3. Deep-Dive: ProgramCommitteeChair ↔ Chair_PC Asymmetry

The central motivating question of Experiment A2 was whether `ProgramCommitteeChair` (CMT) and `Chair_PC` (ConfOf) failed reciprocal matching due to an inherent semantic limitation of `qwen3.5:9b` or due to prompt ordering sensitivity.

### Table 3: Exact Prompts and Raw LLM Outputs for ProgramCommitteeChair ↔ Chair_PC

| Variant | Direction | Prompt Text | LLM Decision | Raw Response Reasoning |
| :--- | :--- | :--- | :---: | :--- |
| **A2.1** | S $\rightarrow$ T | `Question: Is program committee chair equivalent to chair pc?`<br>`Context: conference` | **Yes** | *"Yes. In the context of a conference, 'program committee chair' and 'chair PC' refer to the same role; both titles denote the individual responsible for leading the Program Committee (PC) in managing submissions, reviews, and final acceptance decisions."* |
| **A2.1** | T $\rightarrow$ S | `Question: Is chair pc equivalent to program committee chair?`<br>`Context: conference` | **No** | *"No. 'Chair PC' is an abbreviation for Program Committee Chair, but 'chair pc' (lowercase) could be misinterpreted as referring to a chair of a Personal Computer or another unrelated entity; however, in the specific context of academic conferences, they refer to the same role if capitalized correctly. Strictly speaking, the lowercase version is not standard terminology for the role."* |
| **A2.2** | S $\rightarrow$ T | `Question: Is chair pc equivalent to program committee chair?`<br>`Context: conference` | **No** | *"No. 'Chair PC' is an abbreviation for Program Committee Chair, but 'chair pc' (lowercase) could be misinterpreted as referring to a chair of a Personal Computer... Strictly speaking, the lowercase version is not standard terminology for the role."* |
| **A2.2** | T $\rightarrow$ S | `Question: Is program committee chair equivalent to chair pc?`<br>`Context: conference` | **Yes** | *"Yes. In the context of a conference, 'program committee chair' and 'chair PC' refer to the same role..."* |
| **A2.3** | S $\rightarrow$ T | `Question: Is program committee chair equivalent to chair pc?`<br>`Context: conference` | **Yes** | *"Yes. In the context of a conference, 'program committee chair' and 'chair PC' refer to the same role..."* |
| **A2.3** | T $\rightarrow$ S | `Question: Is program committee chair equivalent to chair pc?`<br>`Context: conference` | **Yes** | *"Yes. In the context of a conference, 'program committee chair' and 'chair PC' refer to the same role..."* |

### Root Cause Analysis:
1. **Token Priming and Semantic Scaffolding:**  
   When the prompt begins with `"program committee chair"`, the semantic domain of conference organization and academic peer review is primed before the model encounters `"chair pc"`. As a result, the abbreviation `"pc"` is immediately decoded as *Program Committee*, and the equivalence is affirmed.
2. **Abbreviation Ambiguity in Subject Position:**  
   When `"chair pc"` is placed in the subject position, the lowercased surface string `"chair pc"` lacks capitalization cues. Without leading academic context, the autoregressive model evaluates the literal tokens `"chair"` and `"pc"` (personal computer) first, flagging ambiguity and concluding that lowercased `"chair pc"` is non-standard.
3. **The Reciprocal Merger Trap:**  
   Under the original Agent-OM architecture (A2.1), the reciprocal merger computes the intersection of $S \rightarrow T$ and $T \rightarrow S$. Because $S \rightarrow T$ produces $\{\text{ProgramCommitteeChair} \leftrightarrow \text{Chair\_PC}\}$ but $T \rightarrow S$ rejects it, the intersection discards the true positive. The exact same drop occurs in A2.2 in reverse order.
4. **Resolution via Canonical Ordering:**  
   A2.3 decouples prompt structure from retrieval direction. Because both directions query the canonical question (`Is source equivalent to target?`), both pipelines receive the robustly primed prompt, both decide **Yes**, and the reciprocal merger preserves the alignment.

---

## 4. Analysis of Hyponym / Hypernym Asymmetry

The prompt-order ablation revealed an equally critical dynamic regarding non-equivalent ontological pairs, specifically subsumption and subclass relationships.

### Observation: Directional Asymmetry on Subsumption
In zero-shot natural language validation, LLMs frequently confound equivalence ($A \equiv B$) with subsumption ($A \subseteq B$) depending on syntactic ordering:

1. **`ConferenceMember` (CMT) vs. `Person` (ConfOf):**
   - **Prompt:** `Is conference member equivalent to person?`
   - **Response:** *"Yes. A conference member is a specific type of person who participates in a conference, making them equivalent to a person within that context."* (Incorrect: subsumption treated as equivalence).
   - **Prompt:** `Is person equivalent to conference member?`
   - **Response:** *"No. In the context of a conference, 'person' is a general term for any individual, whereas 'conference member' specifically denotes someone registered to attend... The terms are not equivalent."* (Correct).

2. **`Participant` (ConfOf) vs. `Person` (CMT):**
   - **Prompt:** `Is participant equivalent to person?`
   - **Response:** *"Yes. In the context of a conference, a participant is a person who attends or engages in the event..."* (Incorrect).
   - **Prompt:** `Is person equivalent to participant?`
   - **Response:** *"No. In the context of a conference, 'person' is a general term... Not every person present at a venue is necessarily a participant."* (Correct).

### Role of the Reciprocal Merger:
These observations illustrate why Agent-OM introduced the reciprocal merger:
- An LLM validator querying in a single direction is prone to accepting hyponyms as synonyms when the narrower term is placed in the subject position.
- In the original pipeline (A2.1), the reverse direction queries `Is person equivalent to conference member?`, which prompts a **No**.
- The reciprocal merger calculates:
  $$\mathcal{A}_{\text{reciprocal}} = \mathcal{A}_{S \rightarrow T} \cap \mathcal{A}_{T \rightarrow S}^{-1}$$
  Consequently, `ConferenceMember ↔ Person` and `Person ↔ Participant` are eliminated from final predictions, preventing severe precision degradation.

---

## 5. Methodological Analysis: Reasoning vs. Direction-Invariance

It is essential to maintain methodological rigor regarding what Experiment A2 demonstrates:

```
+-----------------------------------------------------------------------------------+
|                            METHODOLOGICAL DISTINCTION                             |
+-----------------------------------------------------------------------------------+
| 1. Did Canonical Ordering (A2.3) improve the LLM's semantic reasoning capability? |
|    --> NO. The underlying model (qwen3.5:9b) is identical across all runs.        |
|                                                                                   |
| 2. Does A2.3 represent a genuine architectural improvement?                       |
|    --> YES. It eliminates an artificial source of variance (directional prompt    |
|        inversion) while retaining the structural safety of the reciprocal merger. |
|                                                                                   |
| 3. Does A2.3 alter the semantics of the reciprocal check?                         |
|    --> YES. In A2.1, the two validation passes evaluated two distinct semantic    |
|        questions: Q(A, B) and Q(B, A). In A2.3, both passes evaluate Q_canon(A, B).|
|        The reciprocal check in A2.3 verifies whether candidate A retrieves B      |
|        AND candidate B retrieves A in vector space, before applying the identical |
|        canonical LLM verification to both.                                        |
+-----------------------------------------------------------------------------------+
```

### Key Analytical Conclusions:
1. **Vector-Space Symmetry vs. Validation Symmetry:**  
   In Agent-OM, reciprocal filtering serves two distinct purposes:
   - **Retrieval filtering:** Ensuring both entities consider each other among their top-$K$ semantic neighbors.
   - **Validation filtering:** Checking whether the LLM considers the relationship bidirectional.
2. **The Fragility of Q(B, A):**  
   Testing whether an LLM considers equivalence bidirectional by literally swapping token order ($Q(B, A)$) conflates logical symmetry with prompt token sensitivity. LLMs are non-commutative prompt processors.
3. **Canonical Alignment as Best Practice:**  
   Canonical ordering (A2.3) preserves the bidirectional vector retrieval requirement while shielding the pipeline from prompt-order artifacts. This achieves the optimal tradeoff: maximal recall of true positives ($F_1 = 50.00\%$) while retaining the reciprocal merger's ability to prune asymmetric retrieval false positives.

---

## 6. Next Steps

Step 7D is complete. Empirical results and validation traces are fully archived in:
- [`agent_om_local/output/step7d_prompt_order_comparison.csv`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_prompt_order_comparison.csv)
- [`agent_om_local/output/step7d_validation_decisions.csv`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_validation_decisions.csv)
- [`agent_om_local/output/step7d_summary.json`](file:///e:/_3_Master/_9_ACL_Project/agent_om_local/output/step7d_summary.json)
- Unit tests: 99/99 passing.

As specified by the research constraints, no further experiments (such as Ablation A3 or embedding model comparisons) will be executed without explicit user instruction.

