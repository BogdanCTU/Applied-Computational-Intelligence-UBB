# Feature Specification: Ontology Matching (`MatchingAgent`, `MatchingValidator`, `ReciprocalMerger`)

## 1. Feature Purpose
Aligns classes and properties between a source ontology ($O_1$) and a target ontology ($O_2$) by validating RRF-fused candidate groups in both directions ($O_1 \to O_2$ and $O_2 \to O_1$) and intersecting the validated correspondences using a symmetric Reciprocal Siamese Merger.

## 2. Input Data
- Directional RRF candidate rankings from `RetrievalAgent.retrieve_directional_candidates()` (`Source` and `Target`).
- Source and target `OntologyGraph` instances (used when `o1_is_code` or `o2_is_code` is enabled).

## 3. Processing Steps
1. For each query entity, retrieve its score-grouped RRF candidate list `[(score_1, [eid_a, ...]), ...]`.
2. Iterate through score groups in descending order:
   - Check `MatchingValidator.check_name_bypass(source_name, target_name)`. If normalized names match exactly, accept (`decision="yes"`, `bypassed=True`).
   - Otherwise, format the zero-shot validation prompt and invoke the local LLM (`MatchingValidator.validate_pair()`).
   - If any candidate in the current RRF score group is accepted, stop evaluating lower-ranked groups (`score_group_break`).
3. Normalize both directional sets to `(source_uri, target_uri)` orientation and compute their intersection via `ReciprocalMerger.merge_alignments()`.

## 4. Output Data
- `PipelineResult` containing `source_to_target`, `target_to_source`, `final_predictions`, 6 alignment CSV variants, OAEI Alignment API RDF/XML (`alignment.rdf`), and `validation_records.json`.

## 5. Main Implementation Files
- `1_Source/agents/matching_agent.py`
- `1_Source/matching/validator.py`
- `1_Source/matching/merger.py`

## 6. Configuration Options
- `similarity_threshold` (default `0.90`), `top_k` (default `3`), `rrf_k` (default `0`), `indent_validation_prompt` (`True` or `False`), `tool_routing_mode` (`"deterministic"` or `"llm_json"`).

## 7. Dependencies
- `langchain-core`, `langchain-ollama`, `rdflib`, `psycopg2-binary`.

## 8. Relevant Tests
- `2_Tests/unit/test_matching_agent.py`
- `2_Tests/unit/test_validator.py`
- `2_Tests/unit/test_merger.py`
- `2_Tests/integration/test_algorithmic_parity.py`

## 9. Known Limitations
- Zero-shot LLM validation prompts can exhibit directional order sensitivity on abbreviated labels in sub-4B models (`confOf:Member_PC` vs `cmt:ProgramCommitteeMember`).
