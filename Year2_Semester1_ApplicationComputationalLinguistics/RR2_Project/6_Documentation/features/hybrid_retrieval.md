# Feature Specification: Hybrid Retrieval and Reciprocal Rank Fusion (`RetrievalAgent`, `rank_fusion`)

## 1. Feature Purpose
Combines candidate rankings from Syntactic, Lexical, and Semantic vector searches into a unified, score-grouped candidate ranking using Reciprocal Rank Fusion (RRF).

## 2. Input Data
- Per-strategy top-$k$ candidate `entity_id` lists from `DatabaseManager.query_strategy_with_scores()` (`syntactic_matching`, `lexical_matching`, `semantic_matching`).

## 3. Processing Steps
1. For a query entity $q$, query each of the three `pgvector` tables for the top-$k$ ($k=3$) opposing entities of the same type with cosine similarity $\ge \tau$.
2. Pass the three ranked lists to `reciprocal_rank_fusion(*rankings, k=0, exclude_items={"Entity-Dummy"})`.
3. Accumulate $\text{RRF}(c) = \sum_{m} \frac{1}{\text{rank}_m(c) + k_0}$ for every non-dummy candidate $c$.
4. Group candidates by identical RRF score in descending order `[(score, [eid1, eid2, ...]), ...]`, sorting ties lexicographically by `entity_id`.

## 4. Output Data
- Score-grouped RRF rankings and flat `candidate_uris` lists saved to `candidates_s2t.json` and `candidates_t2s.json`.

## 5. Main Implementation Files
- `1_Source/retrieval/rank_fusion.py`
- `1_Source/agents/retrieval_agent.py`

## 6. Configuration Options
- `similarity_threshold` (default `0.90`), `top_k` (default `3`), `num_matches` (default `50`), `rrf_k` (default `0`).

## 7. Dependencies
- `numpy`, `pandas`, `psycopg2-binary`, `pgvector`.

## 8. Relevant Tests
- `2_Tests/unit/test_rank_fusion.py` (6 test cases)
- `2_Tests/integration/test_retrieval_agent.py` (4 test cases)

## 9. Known Limitations
- Recall is bounded by the union of candidates exceeding cosine threshold $\tau$ across the three vector tables.
