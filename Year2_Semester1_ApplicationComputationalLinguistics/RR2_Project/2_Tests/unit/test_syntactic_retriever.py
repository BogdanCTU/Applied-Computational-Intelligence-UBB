"""Unit tests for SyntacticRetriever."""

from pathlib import Path
import pytest

from src.ontology.parser import load_ontology
from src.ontology.entity_extractor import EntityType, OntologyEntity
from src.retrieval.syntactic_retriever import SyntacticRetriever

DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "original_repo"
    / "data"
    / "conference"
    / "cmt-confof"
    / "component"
)
CMT_PATH = DATA_DIR / "source.xml"
CONFOF_PATH = DATA_DIR / "target.xml"


class TestSyntacticRetriever:
    """Test suite for SyntacticRetriever."""

    @pytest.fixture
    def cmt_ontology(self):
        return load_ontology(CMT_PATH)

    @pytest.fixture
    def confof_ontology(self):
        return load_ontology(CONFOF_PATH)

    def test_syntactic_extraction_on_cmt_entities(self, cmt_ontology):
        """Verify syntactic representation of canonical CMT entities."""
        retriever = SyntacticRetriever(ontology_is_code=False)

        author_ent = OntologyEntity(
            uri="http://cmt#Author",
            local_name="Author",
            display_name="Author",
            entity_type=EntityType.CLASS,
            source_or_target="Source",
        )
        assert retriever.retrieve_syntactic_representation(author_ent) == "author"

        pc_member = OntologyEntity(
            uri="http://cmt#ProgramCommitteeMember",
            local_name="ProgramCommitteeMember",
            display_name="ProgramCommitteeMember",
            entity_type=EntityType.CLASS,
            source_or_target="Source",
        )
        assert (
            retriever.retrieve_syntactic_representation(pc_member)
            == "program committee member"
        )

        has_author = OntologyEntity(
            uri="http://cmt#hasAuthor",
            local_name="hasAuthor",
            display_name="hasAuthor",
            entity_type=EntityType.PROPERTY,
            source_or_target="Source",
        )
        assert retriever.retrieve_syntactic_representation(has_author) == "has author"

    def test_syntactic_extraction_on_confof_entities(self, confof_ontology):
        """Verify syntactic representation of canonical ConfOf entities."""
        retriever = SyntacticRetriever(ontology_is_code=False)

        chair_pc = OntologyEntity(
            uri="http://confOf#Chair_PC",
            local_name="Chair_PC",
            display_name="Chair_PC",
            entity_type=EntityType.CLASS,
            source_or_target="Target",
        )
        assert retriever.retrieve_syntactic_representation(chair_pc) == "chair pc"

        written_by = OntologyEntity(
            uri="http://confOf#writtenBy",
            local_name="writtenBy",
            display_name="writtenBy",
            entity_type=EntityType.PROPERTY,
            source_or_target="Target",
        )
        assert retriever.retrieve_syntactic_representation(written_by) == "written by"

    def test_string_uri_direct_retrieval(self, cmt_ontology):
        """Verify direct URI string passing works."""
        retriever = SyntacticRetriever(ontology_is_code=False)
        res = retriever.retrieve_syntactic_representation("http://cmt#PaperFullVersion", cmt_ontology)
        assert res == "paper full version"

    def test_ontology_is_code_priority(self):
        """Verify that when ontology_is_code=True, rdfs:label takes precedence over URI."""
        from src.ontology.parser import OntologyGraph

        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:c_101 a owl:Class ;
            rdfs:label "ConferenceChair" .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        retriever_code = SyntacticRetriever(ontology_is_code=True)
        retriever_nocode = SyntacticRetriever(ontology_is_code=False)

        # With ontology_is_code=True: label "ConferenceChair" -> "conference chair"
        res_code = retriever_code.retrieve_syntactic_representation("http://example.org/#c_101", ont)
        assert res_code == "conference chair"

        # With ontology_is_code=False: local name "c_101" -> "c 101"
        res_nocode = retriever_nocode.retrieve_syntactic_representation("http://example.org/#c_101", ont)
        assert res_nocode == "c 101"
