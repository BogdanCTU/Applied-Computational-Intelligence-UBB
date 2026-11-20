# Feature Specification: Entity Extraction (`OntologyGraph`, `EntityExtractor`)

## 1. Feature Purpose
Parses OWL and RDF/XML ontology files into an in-memory RDF triple graph and extracts all named classes (`owl:Class`, `skos:Concept`) and properties (`owl:ObjectProperty`, `owl:DatatypeProperty`) along with their lexical and structural metadata.

## 2. Input Data
- Raw ontology files (`3_Dataset/original/conference/cmt-confof/source.xml` and `target.xml`) or RDF strings.

## 3. Processing Steps
1. `load_ontology()` loads the RDF graph via `rdflib`, automatically detecting RDF/XML or Turtle syntax.
2. `EntityExtractor.extract_entities()` filters out blank nodes (`BNode`), `owl:Thing`, and built-in OBO metadata exclusions (`DEFAULT_EXCLUSIONS`).
3. Sorts classes alphabetically by URI, followed by properties sorted alphabetically by URI (`combine_properties_sort=True`), preserving punned properties declared as both object and datatype properties.
4. Resolves display names using `rdfs:label` $\to$ `skos:prefLabel` $\to$ `uri_to_name()` when `ontology_is_code=True`.

## 4. Output Data
- Tuple of `(List[OntologyEntity], ExtractionSummary)` serialized to `extracted_entities.json`.

## 5. Main Implementation Files
- `1_Source/ontology/parser.py` (`1_Source/core/parser.py`)
- `1_Source/ontology/entity_extractor.py` (`1_Source/core/entity_extractor.py`)

## 6. Configuration Options
- `o1_is_code` (`bool`), `o2_is_code` (`bool`), `combine_properties_sort` (`bool`, default `True`).

## 7. Dependencies
- `rdflib>=7.0.0`.

## 8. Relevant Tests
- `2_Tests/unit/test_ontology.py` (17 test cases)
- `2_Tests/integration/test_algorithmic_parity.py` (`TestPhase4PropertySortingParity`)

## 9. Known Limitations
- Focuses on named classes and properties (`owl:NamedIndividual` instances are excluded by design, matching upstream Agent-OM).
