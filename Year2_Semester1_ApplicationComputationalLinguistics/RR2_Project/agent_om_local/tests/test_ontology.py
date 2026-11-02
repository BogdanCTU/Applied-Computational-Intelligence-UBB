"""Comprehensive unit tests for ontology parser and entity extractor."""

from pathlib import Path
import pytest

from src.ontology.parser import OntologyGraph, OntologyParseError, load_ontology
from src.ontology.entity_extractor import EntityExtractor, EntityType, OntologyEntity


# Workspace-relative paths to original read-only benchmark datasets
ORIGINAL_DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "original_repo"
    / "data"
    / "conference"
    / "cmt-confof"
    / "component"
)
CMT_PATH = ORIGINAL_DATA_DIR / "source.xml"
CONFOF_PATH = ORIGINAL_DATA_DIR / "target.xml"


class TestOntologyParser:
    """Test suite for OntologyGraph and load_ontology."""

    def test_load_cmt_source_exists(self):
        """Ensure CMT source file can be parsed into an OntologyGraph."""
        assert CMT_PATH.exists(), f"CMT ontology not found at {CMT_PATH}"
        ont = load_ontology(CMT_PATH)
        assert ont.triple_count > 0
        assert len(ont.namespaces) > 0

    def test_load_confof_target_exists(self):
        """Ensure ConfOf target file can be parsed into an OntologyGraph."""
        assert CONFOF_PATH.exists(), f"ConfOf ontology not found at {CONFOF_PATH}"
        ont = load_ontology(CONFOF_PATH)
        assert ont.triple_count > 0
        assert len(ont.namespaces) > 0

    def test_file_not_found(self):
        """Ensure FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError):
            load_ontology("non_existent_ontology.xml")

    def test_malformed_xml_handling(self, tmp_path):
        """Ensure OntologyParseError is raised for corrupted/malformed input."""
        bad_file = tmp_path / "corrupt.xml"
        bad_file.write_text("<rdf:RDF><unclosed_tag>", encoding="utf-8")
        with pytest.raises(OntologyParseError):
            load_ontology(bad_file)

    def test_string_loading(self):
        """Ensure ontologies can be parsed directly from strings."""
        ttl_data = """
        @prefix ex: <http://example.org/#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:Person a owl:Class ;
            rdfs:label "Person"@en .
        """
        ont = OntologyGraph.from_string(ttl_data, format="turtle")
        assert ont.triple_count == 2
        assert "ex" in ont.namespaces or any("example.org" in ns for ns in ont.namespaces.values())

    def test_uri_to_name(self):
        """Verify uri_to_name matches original Agent-OM logic for '#' and '/' delimiters."""
        assert OntologyGraph.uri_to_name("http://cmt#ProgramCommitteeMember") == "ProgramCommitteeMember"
        assert OntologyGraph.uri_to_name("http://confOf/Chair_PC") == "Chair_PC"
        assert OntologyGraph.uri_to_name("http://example.org/path#TestEntity") == "TestEntity"

    def test_uri_to_prefix_name(self):
        """Verify uri_to_prefix_name matches original Agent-OM formatting."""
        assert OntologyGraph.uri_to_prefix_name("http://cmt#Author", "source") == "source:Author"
        assert OntologyGraph.uri_to_prefix_name("http://confOf#Member", "target") == "target:Member"


class TestEntityExtractorCMT:
    """Test suite validating CMT extraction matches original Agent-OM entity counts."""

    @pytest.fixture
    def cmt_extraction(self):
        ont = load_ontology(CMT_PATH)
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source", ontology_is_code=False)
        return entities, summary

    def test_cmt_counts(self, cmt_extraction):
        """
        Original Agent-OM CMT Counts:
        - Classes: 29
        - Object Properties: 49
        - Data Properties: 10
        - Total Properties: 59
        - Total Entities: 88
        """
        entities, summary = cmt_extraction
        assert summary.total_classes == 29
        assert summary.total_object_properties == 49
        assert summary.total_datatype_properties == 10
        assert summary.total_properties == 59
        assert summary.total_entities == 88
        assert len(entities) == 88

    def test_cmt_uri_preservation(self, cmt_extraction):
        """Verify that canonical CMT URIs are strictly preserved."""
        entities, _ = cmt_extraction
        uris = {e.uri for e in entities}
        expected_sample_uris = {
            "http://cmt#Administrator",
            "http://cmt#Author",
            "http://cmt#Conference",
            "http://cmt#ConferenceMember",
            "http://cmt#Paper",
            "http://cmt#PaperFullVersion",
            "http://cmt#Person",
            "http://cmt#ProgramCommitteeChair",
            "http://cmt#ProgramCommitteeMember",
            "http://cmt#SubjectArea",
            "http://cmt#email",
            "http://cmt#hasAuthor",
            "http://cmt#writePaper",
        }
        for expected in expected_sample_uris:
            assert expected in uris, f"Expected URI '{expected}' missing from extracted CMT entities"

    def test_cmt_entity_types(self, cmt_extraction):
        """Verify that Class vs Property types are correctly classified."""
        entities, _ = cmt_extraction
        entity_map = {e.uri: e for e in entities}
        assert entity_map["http://cmt#Author"].entity_type == EntityType.CLASS
        assert entity_map["http://cmt#hasAuthor"].entity_type == EntityType.PROPERTY
        assert entity_map["http://cmt#hasAuthor"].property_kind == "ObjectProperty"
        assert entity_map["http://cmt#email"].entity_type == EntityType.PROPERTY
        assert entity_map["http://cmt#email"].property_kind == "DatatypeProperty"


class TestEntityExtractorConfOf:
    """Test suite validating ConfOf extraction matches original Agent-OM entity counts."""

    @pytest.fixture
    def confof_extraction(self):
        ont = load_ontology(CONFOF_PATH)
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Target", ontology_is_code=False)
        return entities, summary

    def test_confof_counts(self, confof_extraction):
        """
        Original Agent-OM ConfOf Counts:
        - Classes: 38
        - Object Properties: 13
        - Data Properties: 23
        - Total Properties: 36
        - Total Entities: 74
        """
        entities, summary = confof_extraction
        assert summary.total_classes == 38
        assert summary.total_object_properties == 13
        assert summary.total_datatype_properties == 23
        assert summary.total_properties == 36
        assert summary.total_entities == 74
        assert len(entities) == 74

    def test_confof_uri_preservation(self, confof_extraction):
        """Verify that canonical ConfOf URIs are strictly preserved."""
        entities, _ = confof_extraction
        uris = {e.uri for e in entities}
        expected_sample_uris = {
            "http://confOf#Administrator",
            "http://confOf#Author",
            "http://confOf#Conference",
            "http://confOf#Member",
            "http://confOf#Paper",
            "http://confOf#Contribution",
            "http://confOf#Person",
            "http://confOf#Chair_PC",
            "http://confOf#Member_PC",
            "http://confOf#Topic",
            "http://confOf#hasEmail",
            "http://confOf#writtenBy",
            "http://confOf#writes",
        }
        for expected in expected_sample_uris:
            assert expected in uris, f"Expected URI '{expected}' missing from extracted ConfOf entities"


class TestEntityExtractorEdgeCases:
    """Test suite for edge cases: missing labels, anonymous/blank nodes, and exclusion rules."""

    def test_anonymous_blank_nodes_ignored(self):
        """Ensure blank nodes (anonymous classes/restrictions) are not returned as named entities."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix ex: <http://example.org/#> .

        ex:NamedClass a owl:Class .
        [ a owl:Class ; owl:intersectionOf ( ex:NamedClass ) ] .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        assert entities[0].uri == "http://example.org/#NamedClass"

    def test_owl_thing_excluded(self):
        """Ensure built-in owl:Thing is excluded."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        owl:Thing a owl:Class .
        ex:MyClass a owl:Class .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        assert entities[0].uri == "http://example.org/#MyClass"
        assert "http://www.w3.org/2002/07/owl#Thing" in summary.excluded_entities

    def test_missing_label_fallback(self):
        """Ensure display_name falls back gracefully to local name when labels are absent."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:UnlabeledEntity a owl:Class .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, _ = extractor.extract_entities(ont, source_or_target="Source", ontology_is_code=True)
        assert len(entities) == 1
        assert entities[0].display_name == "UnlabeledEntity"
        assert entities[0].labels == []

    def test_custom_exclusions(self):
        """Ensure custom exclusion lists are properly enforced."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:Allowed a owl:Class .
        ex:Blocked a owl:Class .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor(exclusions={"http://example.org/#Blocked"})
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        assert entities[0].uri == "http://example.org/#Allowed"
        assert "http://example.org/#Blocked" in summary.excluded_entities


class TestStep4CorrectionsAndEdgeCases:
    """Targeted tests covering edge cases requested in Step 4 review:
    1. Language-tagged labels
    2. Multiple annotations
    3. Missing domains/ranges
    4. Inherited relationships
    5. Duplicate declarations
    6. Entities declared as both object and datatype properties (punning)
    7. skos:Concept extracted as class matching original implementation
    """

    def test_language_tagged_labels(self):
        """Verify handling of multiple labels with different language tags (@en, @fr, @de)."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:MultilingualPerson a owl:Class ;
            rdfs:label "Person"@en ;
            rdfs:label "Personne"@fr ;
            rdfs:label "Mensch"@de .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, _ = extractor.extract_entities(ont, source_or_target="Source", ontology_is_code=True)
        assert len(entities) == 1
        ent = entities[0]
        # Labels should contain all language tagged string literals
        assert len(ent.labels) == 3
        assert "Person" in ent.labels
        assert "Personne" in ent.labels
        assert "Mensch" in ent.labels
        # Primary display name should resolve cleanly to a string without language tag artifacts
        assert ent.display_name in ["Person", "Personne", "Mensch"]

    def test_multiple_annotations_collected(self):
        """Verify that multiple comments, definitions, and notes are collected and deduplicated."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ex: <http://example.org/#> .

        ex:AnnotatedClass a owl:Class ;
            rdfs:comment "First comment describing the class." ;
            rdfs:comment "Second comment providing operational details." ;
            skos:definition "Standard definition of the concept." ;
            skos:note "Editorial note regarding usage." .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, _ = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        ent = entities[0]
        assert len(ent.comments) == 4
        assert "First comment describing the class." in ent.comments
        assert "Second comment providing operational details." in ent.comments
        assert "Standard definition of the concept." in ent.comments
        assert "Editorial note regarding usage." in ent.comments

    def test_missing_domains_and_ranges(self):
        """Verify that properties lacking domain and range declarations are safely handled."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:freeFloatingProperty a owl:ObjectProperty .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, _ = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        ent = entities[0]
        assert ent.entity_type == EntityType.PROPERTY
        assert ent.domains == []
        assert ent.ranges == []

    def test_inherited_class_hierarchy(self):
        """Verify that direct superclasses and subclasses are correctly mapped."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:Animal a owl:Class .
        ex:Mammal a owl:Class ;
            rdfs:subClassOf ex:Animal .
        ex:Dog a owl:Class ;
            rdfs:subClassOf ex:Mammal .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, _ = extractor.extract_entities(ont, source_or_target="Source")
        entity_map = {e.uri: e for e in entities}
        assert len(entity_map) == 3
        mammal = entity_map["http://example.org/#Mammal"]
        assert "http://example.org/#Animal" in mammal.super_entities
        assert "http://example.org/#Dog" in mammal.sub_entities

    def test_duplicate_declarations_handled(self):
        """Verify that repeated RDF triples or duplicate declarations do not cause duplicate entities."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:DuplicateClass a owl:Class .
        ex:DuplicateClass a owl:Class .
        ex:DuplicateClass a owl:Class .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        assert len(entities) == 1
        assert summary.total_classes == 1
        assert entities[0].uri == "http://example.org/#DuplicateClass"

    def test_punning_property_both_object_and_datatype(self):
        """Verify handling when an entity is declared as both ObjectProperty and DatatypeProperty."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:punnedProperty a owl:ObjectProperty, owl:DatatypeProperty .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        # In original Agent-OM logic, looping through ObjectProperty then DatatypeProperty creates entries for both
        assert summary.total_object_properties == 1
        assert summary.total_datatype_properties == 1
        assert summary.total_properties == 2
        assert len(entities) == 2
        kinds = {e.property_kind for e in entities}
        assert kinds == {"ObjectProperty", "DatatypeProperty"}

    def test_skos_concept_extracted_as_class(self):
        """Verify that skos:Concept entities are extracted as Class, reproducing line 261 of om_ontology_to_csv.py."""
        ttl = """
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ex: <http://example.org/#> .

        ex:TaxonomyNode a skos:Concept .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        extractor = EntityExtractor()
        entities, summary = extractor.extract_entities(ont, source_or_target="Source")
        assert summary.total_classes == 1
        assert len(entities) == 1
        assert entities[0].entity_type == EntityType.CLASS
        assert entities[0].uri == "http://example.org/#TaxonomyNode"
