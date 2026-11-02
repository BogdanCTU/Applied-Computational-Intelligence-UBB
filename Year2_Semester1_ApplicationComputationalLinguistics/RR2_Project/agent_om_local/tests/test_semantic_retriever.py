"""Unit tests for SemanticRetriever."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from rdflib.namespace import RDFS
from langchain_core.messages import AIMessage

from src.ontology.parser import OntologyGraph, load_ontology
from src.retrieval.semantic_retriever import SemanticRetriever

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


class TestSemanticRetriever:
    """Test suite for SemanticRetriever."""

    @pytest.fixture
    def cmt_ontology(self):
        return load_ontology(CMT_PATH)

    @pytest.fixture
    def confof_ontology(self):
        return load_ontology(CONFOF_PATH)

    def test_subgraph_18_predicates_extraction(self):
        """Verify extraction of relevant predicates and exclusion of owl:Thing."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:Parent a owl:Class .
        ex:Child a owl:Class ;
            rdfs:subClassOf ex:Parent ;
            rdfs:subClassOf owl:Thing ;
            owl:disjointWith ex:Other .
        ex:Other a owl:Class .

        ex:hasChild a owl:ObjectProperty ;
            rdfs:domain ex:Parent ;
            rdfs:range ex:Child .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        retriever = SemanticRetriever()

        # Child should have: subClassOf Parent, disjointWith Other, range of hasChild
        subgraph = retriever.extract_subgraph_18_predicates("http://example.org/#Child", ont.graph)
        assert len(subgraph) >= 3

        # Convert triples to strings for verification
        triples_str = [(str(s), str(p), str(o)) for s, p, o in subgraph]
        # owl:Thing must NOT be in subgraph
        for s, p, o in triples_str:
            assert "Thing" not in o
            assert "Thing" not in s

        # Check subClassOf Parent is present with normalized names
        assert ("Child", str(RDFS.subClassOf), "Parent") in triples_str

    def test_expand_bnode_closure_named_cmt(self, cmt_ontology):
        """Verify that blank-node closures are extracted for complex entities in CMT."""
        retriever = SemanticRetriever()
        # In CMT, Reviewer and Person have complex OWL restrictions involving blank nodes
        bnode_triples = retriever.expand_bnode_closure_named(
            "http://cmt#Reviewer", cmt_ontology.graph
        )
        assert len(bnode_triples) > 0
        # Verify elements are normalized triples
        for s, p, o in bnode_triples:
            assert isinstance(s, str)
            assert isinstance(p, str)
            assert isinstance(o, str)

    def test_expand_bnode_closure_named_confof(self, confof_ontology):
        """Verify blank-node closure extraction in ConfOf."""
        retriever = SemanticRetriever()
        bnode_triples = retriever.expand_bnode_closure_named(
            "http://confOf#Contribution", confof_ontology.graph
        )
        assert len(bnode_triples) > 0

    def test_null_value_fallback(self):
        """Verify fallback to null_value_sentence when no structural triples exist."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <http://example.org/#> .

        ex:IsolatedClass a owl:Class .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        retriever = SemanticRetriever(null_value_sentence="Information is not available.")
        answer, meta = retriever.retrieve_semantic_representation("http://example.org/#IsolatedClass", ont)

        assert answer == "Information is not available."
        assert meta["has_predicate_triples"] is False
        assert meta["has_complex_bnode"] is False

    def test_retrieve_semantic_with_mock_llm(self):
        """Verify end-to-end verbalization invocation with mock LLM."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:Paper a owl:Class .
        ex:Conference a owl:Class .
        ex:isSubmittedTo a owl:ObjectProperty ;
            rdfs:domain ex:Paper ;
            rdfs:range ex:Conference .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(
            content="A Paper is submitted to a Conference."
        )

        retriever = SemanticRetriever(llm=mock_llm)
        answer, meta = retriever.retrieve_semantic_representation("http://example.org/#Paper", ont)

        assert "A Paper is submitted to a Conference." in answer
        assert meta["has_predicate_triples"] is True
        assert mock_llm.invoke.called
