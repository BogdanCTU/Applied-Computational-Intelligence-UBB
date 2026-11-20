# Feature Specification: Lexical Retrieval (`LexicalRetriever`)

## 1. Feature Purpose
Extracts literal annotations from an ontology entity and generates a domain-contextualized natural language definition using a local Ollama LLM.

## 2. Input Data
- `OntologyEntity` or entity URI string, `OntologyGraph`, and domain `context` string (e.g., `"conference"`).

## 3. Processing Steps
1. `extract_extra_information()` queries the RDF graph across 10 annotation predicates in `head` mode (`rdfs:comment`, `rdf:value`, `skos:definition`, `skos:notation`, `skos:note`, `skos:scopeNote`, `skos:editorialNote`, `skos:historyNote`, `skos:changeNote`, `skos:example`) or 2 predicates in `pvl_v1` mode, sorting deduplicated values deterministically.
2. `build_prompt_text()` formats either `TEMPLATE_WITH_EXTRA` or `TEMPLATE_WITHOUT_EXTRA`.
3. Invokes the configured local `ChatOllama` model and returns the cleaned explanation along with token and duration telemetry.

## 4. Output Data
- Tuple `(lexical_description_str, metadata_dict)` stored in the `lexical_matching` column of `ontology_matching`.

## 5. Main Implementation Files
- `1_Source/retrieval/lexical_retriever.py`

## 6. Configuration Options
- `context` (default `"conference"`), `predicate_scope` (`"head"` or `"pvl_v1"`), `sort_lexical_annotations` (`True`), `strip_llm_responses` (`True`).

## 7. Dependencies
- `rdflib`, `langchain-core`, `langchain-ollama`.

## 8. Relevant Tests
- `2_Tests/unit/test_lexical_retriever.py`

## 9. Known Limitations
- Requires one LLM generation call per entity during initial feature extraction (162 calls total for CMT–ConfOf).
