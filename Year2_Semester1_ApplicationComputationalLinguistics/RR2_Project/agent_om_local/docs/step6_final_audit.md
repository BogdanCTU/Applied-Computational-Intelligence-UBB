# Step 6 Final Audit: Verification & Methodological Accounting

**Date:** October 31, 2026  
**Project:** Local Reproduction of Agent-OM (*Agent-OM: Leveraging LLM Agents for Ontology Matching*, PVLDB 2025)  
**Dataset:** OAEI Conference Benchmark — CMT (Source, 88 entities) to ConfOf (Target, 74 entities)  
**Evaluator:** Agent-OM Local Reproduction Verification Suite  

---

## 1. Executive Summary & Audit Verdict

This audit rigorously inspects the Step 6 implementation, experimental configurations, raw execution logs, and benchmark comparisons to ensure complete scientific integrity before proceeding to multi-model evaluations.

**Audit Status:** **PASS (Methodologically Sound)**  
- No implementation bugs were found in RRF fusion, exact-name bypass, directional retrieval, or reciprocal intersection.
- The experimental distinction between **E1** (single full-pipeline execution) and **E7** (repeatability/determinism suite) is formally verified and clarified.
- The divergence between the published paper baseline ($F1 = 48.00\%$) and committed artifact baseline ($F1 = 50.00\%$) is strictly preserved and attributed to unmerged vs. merged directional outputs.
- A critical qualitative phenomenon in local LLM validation (`qwen3.5:9b`) was uncovered: directional semantic asymmetry caused the rejection of `Chair_PC ↔ ProgramCommitteeChair` in Target $\rightarrow$ Source, leading to its elimination in reciprocal merger.

---

## 2. Detailed Audit Findings by Component

### 2.1. E1 vs. E7 Configuration & Repeatability Accounting
* **Verification Objective:** Verify whether E7 introduces an independent matching architecture or represents repeated runs of E1.
* **Findings:**
  - Code inspection of `agent_om_local/scripts/run_experiments_step6.py` confirms that `E7_Run1`, `E7_Run2`, and `E7_Run3` invoke `agent.run_pipeline(experiment_id, validate=True, reciprocal_merger=True)` with identical parameters ($k=0$, $\tau=0.90$, $\text{top\_k}=3$, `temperature=0.0`, `qwen3.5:9b`).
  - Output metrics across all three runs are 100% identical:
    - Source $\rightarrow$ Target: 7 pairs, $\text{TP}=5, \text{FP}=2, \text{FN}=11$ ($P=71.43\%, R=31.25\%, F1=43.48\%$).
    - Target $\rightarrow$ Source: 6 pairs, $\text{TP}=4, \text{FP}=2, \text{FN}=12$ ($P=66.67\%, R=25.00\%, F1=36.36\%$).
    - Reciprocal Final: 6 pairs, $\text{TP}=4, \text{FP}=2, \text{FN}=12$ ($P=66.67\%, R=25.00\%, F1=36.36\%$).
    - Execution calls: 8 LLM calls, 12 exact-name bypasses, 354 prompt tokens, 542 completion tokens.
* **Audit Verdict & Classification:**
  - **E7 is formally classified as a Repeatability / Determinism Test for E1**, not a separate architectural variant.
  - The documentation and summary files accurately label these as `E7_Run1`, `E7_Run2`, and `E7_Run3`. Universal determinism across all LLMs is not claimed; determinism is reported strictly for this local Ollama `qwen3.5:9b` deployment at `temperature=0.0`.

---

### 2.2. Matching Algorithm & Architectural Fidelity
We verified each algorithmic mechanism against the original repository (`original_repo/om_database_matching.py`):

1. **Reciprocal Rank Fusion (RRF):**
   - Implemented in `src/retrieval/rank_fusion.py` (`reciprocal_rank_fusion`).
   - Uses $k=0$ smoothing constant ($1 / \text{position}$) with 1-indexed ranks, exactly matching lines 249–260 of `om_database_matching.py`.
   - Ties are broken lexicographically by candidate ID, and candidates sharing identical fused scores are grouped via `itertools.groupby`.
   - `Entity-Dummy` and null placeholders are excluded before ranking computation.
2. **Score Group Iteration & `top_k=3`:**
   - In `src/agents/matching_agent.py` (`match_entity`), candidate score groups are sliced by `[: self.top_k]`.
   - In accordance with lines 293–326 of `om_database_matching.py`, the validator evaluates candidates score-group by score-group. If any candidate in a score group is accepted (via bypass or LLM "yes"), the loop breaks immediately, skipping lower score groups.
3. **Exact-Name Bypass Rule:**
   - Lines 306–310 of `om_database_matching.py`: `cleaning(name).casefold() == cleaning(cand_name).casefold()`.
   - Replicated in `src/matching/validator.py` (`check_name_bypass`). Bypassed pairs bypass LLM prompting completely (0 ms latency, 0 tokens), setting `decision="yes"` and `bypassed=True`.
4. **Reciprocal Merger:**
   - Implemented in `src/matching/merger.py` (`merge_alignments`).
   - Normalizes both Source $\rightarrow$ Target and Target $\rightarrow$ Source pairs to canonical `(Source_URI, Target_URI)` tuples, then applies mathematical set intersection:
     $$M = M_{S \rightarrow T} \cap M_{T \rightarrow S}$$
   - Only pairs corroborated in both directions survive.
5. **Candidate Bounding Invariant:**
   - The validation agent only evaluates candidate IDs provided by `retrieve_entity_rankings` from the database. It has no mechanism to propose new entity URIs.
   - **Verified Invariant:** LLM validation cannot introduce any correspondence that was not retrieved by the retrieval agent.

---

### 2.3. LLM Validation & Qualitative Asymmetry Analysis
All 20 validation attempts in E1 (documented in `agent_om_local/output/step6_validation_logs.csv`) were audited:

* **Bypassed Matches (12 entries across both directions):**
  - `Administrator ↔ Administrator` (TP)
  - `Author ↔ Author` (TP)
  - `Conference ↔ Conference` (TP)
  - `Person ↔ Person` (TP)
  - `Paper ↔ Paper` (FP in ground truth, since `cmt#Paper = confOf#Contribution`)
  - `writtenBy ↔ writtenBy` (FP in ground truth, since `cmt#hasAuthor = confOf#writtenBy`)
* **LLM Rejections (7 calls across both directions):**
  - `User -> Person`: Correctly rejected (`decision="no"`). Avoided false positive.
  - `Contribution -> Paper`: Rejected (`decision="no"`). LLM explained that a contribution can be a poster/presentation, not solely a paper.
  - `title ↔ hasTitle` (and `has_title`): Evaluated 4 times (twice in each direction). Consistently rejected (`decision="no"`). LLM ontologically differentiated an event title concept from an instance property.
* **The Asymmetric Rejection of `ProgramCommitteeChair ↔ Chair_PC`:**
  - **Source $\rightarrow$ Target:** Prompt asked: *"Is program committee chair equivalent to chair pc?"*. LLM answered: *"Yes. In the context of a conference, 'program committee chair' and 'chair PC' refer to the same role..."* $\rightarrow$ **Accepted (`decision="yes"`)**.
  - **Target $\rightarrow$ Source:** Prompt asked: *"Is chair pc equivalent to program committee chair?"*. LLM answered: *"No. 'Chair PC' is an abbreviation for Program Committee Chair, but 'chair pc' (lowercase) could be misinterpreted as referring to a chair of a Personal Computer..."* $\rightarrow$ **Rejected (`decision="no"`)**.
  - **Audit Finding:** This is a genuine qualitative behavior of `qwen3.5:9b`, not a prompt parsing failure or malformed output.
  - **Methodological Guardrail:** Per instructions, the prompt is **not** modified to force acceptance of this correspondence. The discrepancy is reported as an empirical finding.

---

### 2.4. Baseline & Benchmark Discrepancy Accounting
* **Published PVLDB Paper Baseline ($F1 = 48.00\%$):**
  - $P = 66.67\%, R = 37.50\%, F1 = 48.00\%$ ($\text{TP}=6, \text{FP}=3, \text{FN}=10$).
  - This corresponds precisely to the unmerged Source $\rightarrow$ Target directional predictions in ablation **E5** (without validation).
* **Original Committed `predict.csv` ($F1 = 50.00\%$):**
  - $P = 75.00\%, R = 37.50\%, F1 = 50.00\%$ ($\text{TP}=6, \text{FP}=2, \text{FN}=10$).
  - This corresponds precisely to the reciprocal merged output in ablation **E5**.
* **Correspondence-Level Differences:**
  - Local E5 and committed `predict.csv` share 5 TPs and 2 FPs, but differ on 1 TP:
    - E5 retrieved and predicted `title = hasTitle` (TP, $\text{sim}=0.9292$).
    - Committed `predict.csv` predicted `ProgramCommitteeMember = Member_PC` (TP).
    - In `nomic-embed-text`, `ProgramCommitteeMember = Member_PC` scored $0.8525$, falling below the $0.90$ threshold.
  - The aggregate score matching ($F1 = 50.00\%$) is verified, but the exact correspondence sets differ due to embedding geometry differences.

---

## 3. Audit Issue Log & Severity Classification

| Issue ID | Description | Severity | Impact on Validity | Resolution |
| :---: | :--- | :---: | :---: | :--- |
| **AUD-01** | E7 could be misinterpreted as an independent matching architecture rather than a repeatability run of E1. | Minor (Labeling) | None | Explicitly classified E7 as a multi-run repeatability verification of E1. |
| **AUD-02** | `nomic-embed-text` produces lower cosine similarities for acronym abbreviations (`Member_PC` = 0.8525) than OpenAI Ada-002, capping retrieval recall at 43.75% under $\tau=0.90$. | Moderate (Embedding Shift) | Explains recall bound | Identified as the primary motivation for Step 7A threshold sensitivity analysis. |
| **AUD-03** | Directional prompt asymmetry in `qwen3.5:9b` drops `ProgramCommitteeChair = Chair_PC` during reciprocal merger. | Minor (LLM Behavior) | None | Preserved faithfully; prompts are not artificially engineered to overfit. |
| **AUD-04** | Qwen 3.5 default thinking mode generated 2000 tokens of internal CoT. | Resolved | Fixed via `reasoning=False` | Solved in Step 6; latency dropped from 65s to 2.5s per query with identical accuracy. |

---

## 4. Final Recommendation

Step 6 has been verified to be methodologically sound, mathematically faithful, and reproducible. The codebase is authorized to proceed to **Step 7A: Similarity Threshold Sensitivity Analysis**.

