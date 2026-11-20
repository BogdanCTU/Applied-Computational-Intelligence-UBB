# Feature Specification: Semantic Retrieval (`SemanticRetriever`)

## 1. Feature Purpose
Extracts an entity's 1-hop relational RDF subgraph and recursive blank-node restriction closure, and verbalizes those triples into natural language sentences using a local Ollama LLM.

## 2. Input Data
- `OntologyEntity` or entity URI string and `OntologyGraph`.

## 3. Processing Steps
1. `extract_subgraph_18_predicates()` collects outgoing and incoming triples across 18 structural predicates (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `owl:disjointWith`, `rdfs:domain`, `rdfs:range`, `owl:equivalentClass`, `owl:equivalentProperty`, and 11 SKOS relational predicates), excluding `owl:Thing` and blank nodes.
2. If the predicate subgraph is non-empty, serializes it to Turtle and prompts the local LLM with `"Verbalise triples into phrases: {subgraph}"`.
3. `expand_bnode_closure_named()` performs a breadth-first traversal of connected blank nodes (such as OWL property restrictions), sorts the normalized triple tuples deterministically (`sort_bnode_triples=True`), and prompts the LLM with `"Verbalise the subgraph into a natual language description: {subgraph}"`.
4. If both subgraphs are empty, returns `"Information is not available."`.

## 4. Output Data
- Tuple `(semantic_verbalization_str, metadata_dict)` stored in the `semantic_matching` column.

## 5. Main Implementation Files
- `1_Source/retrieval/semantic_retriever.py`

## 6. Configuration Options
- `predicate_scope` (`"head"` vs `"pvl_v1"`), `sort_bnode_triples` (`True`), `semantic_concat_separator` (`"\n"` or `""`), `null_value_sentence` (`"Information is not available."`).

## 7. Dependencies
- `rdflib`, `langchain-core`, `langchain-ollama`.

## 8. Relevant Tests
- `2_Tests/unit/test_semantic_retriever.py`
- `2_Tests/integration/test_algorithmic_parity.py` (`TestPhase4EmptySemanticChunks`)

## 9. Known Limitations
- Structurally isolated entities have no relational triples and produce `0` semantic vector chunks (`skip_empty_chunks=True`).
