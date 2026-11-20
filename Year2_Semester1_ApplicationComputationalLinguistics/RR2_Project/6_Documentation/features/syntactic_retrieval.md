# Feature Specification: Syntactic Retrieval (`SyntacticRetriever`, `text_processing`)

## 1. Feature Purpose
Produces a normalized surface-form string representation of each ontology entity by cleaning symbols, repairing uppercase acronyms, splitting `camelCase` and `snake_case` identifiers, lowercasing, and normalizing British English spelling to American English.

## 2. Input Data
- `OntologyEntity` or entity URI string and optional `OntologyGraph`.

## 3. Processing Steps
1. Extract local name via `uri_to_name()` (or primary label when `ontology_is_code=True`).
2. `repair_acronyms()` converts contiguous uppercase acronyms (such as `Chair_PC` or `PCMember`) into title case so word boundaries are preserved.
3. `change_to_snake_case()` and symbol replacement convert camelCase/underscores/hyphens into space-separated lowercase words.
4. `change_phrase_british_to_american()` normalizes British spellings via `breame`.

## 4. Output Data
- Normalized lowercase string (e.g., `"program committee member"`) stored in the `syntactic_matching` column.

## 5. Main Implementation Files
- `1_Source/retrieval/syntactic_retriever.py`
- `1_Source/utils/text_processing.py`

## 6. Configuration Options
- `o1_is_code` / `o2_is_code` (`bool`).

## 7. Dependencies
- `breame>=0.1.2`, `rdflib`.

## 8. Relevant Tests
- `2_Tests/unit/test_syntactic_retriever.py`
- `2_Tests/unit/test_text_processing.py` (21 test cases)

## 9. Known Limitations
- Purely surface-lexical; cannot align synonyms without overlapping root tokens (handled by Lexical and Semantic retrieval).
