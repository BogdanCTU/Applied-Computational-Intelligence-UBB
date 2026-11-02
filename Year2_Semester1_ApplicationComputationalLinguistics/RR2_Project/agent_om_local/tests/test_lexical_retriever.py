"""Unit tests for LexicalRetriever."""

from unittest.mock import MagicMock
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from langchain_core.messages import AIMessage

from src.ontology.parser import OntologyGraph
from src.retrieval.lexical_retriever import LexicalRetriever


class TestLexicalRetriever:
    """Test suite for LexicalRetriever."""

    def test_extract_all_10_predicates(self):
        """Verify that annotations across all 10 lexical predicates are extracted."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ex: <http://example.org/#> .

        ex:RichEntity a owl:Class ;
            rdfs:comment "RDFS Comment" ;
            rdf:value "RDF Value" ;
            skos:definition "SKOS Definition" ;
            skos:notation "SKOS Notation" ;
            skos:note "SKOS Note" ;
            skos:scopeNote "SKOS ScopeNote" ;
            skos:editorialNote "SKOS EditorialNote" ;
            skos:historyNote "SKOS HistoryNote" ;
            skos:changeNote "SKOS ChangeNote" ;
            skos:example "SKOS Example" .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        retriever = LexicalRetriever(llm=None, context="conference")
        extra_info = retriever.extract_extra_information("http://example.org/#RichEntity", ont.graph)

        expected_elements = [
            "RDFS Comment",
            "RDF Value",
            "SKOS Definition",
            "SKOS Notation",
            "SKOS Note",
            "SKOS ScopeNote",
            "SKOS EditorialNote",
            "SKOS HistoryNote",
            "SKOS ChangeNote",
            "SKOS Example",
        ]
        for elem in expected_elements:
            assert elem in extra_info, f"Missing annotation: {elem}"

    def test_prompt_template_without_extra_info(self):
        """Verify prompt template generated when no annotations exist."""
        retriever = LexicalRetriever(llm=None, context="conference")
        prompt = retriever.build_prompt_text(entity_name="Administrator", extra_information="")
        expected = (
            "Question: What is the meaning of Administrator?\n"
            "Context: conference\n"
            "Answer the question within the context.\n"
        )
        assert prompt == expected

    def test_prompt_template_with_extra_info(self):
        """Verify prompt template generated when annotations exist."""
        retriever = LexicalRetriever(llm=None, context="conference")
        prompt = retriever.build_prompt_text(
            entity_name="Administrator",
            extra_information="A person who manages the system.",
        )
        expected = (
            "Question: What is the meaning of Administrator?\n"
            "Context: conference\n"
            "Extra Information: A person who manages the system.\n"
            "Answer the question within the context and using the extra information.\n"
        )
        assert prompt == expected

    def test_retrieve_lexical_with_mock_llm(self):
        """Verify complete lexical retrieval flow with a mock LLM."""
        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/#> .

        ex:Author a owl:Class ;
            rdfs:comment "A writer of a paper." .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(
            content="In the context of a conference, an Author is someone who submits a manuscript."
        )

        retriever = LexicalRetriever(llm=mock_llm, context="conference")
        content, meta = retriever.retrieve_lexical_representation("http://example.org/#Author", ont)

        assert "Author is someone who submits a manuscript" in content
        assert meta["has_extra_info"] is True
        assert meta["entity_name"] == "Author"
        assert mock_llm.invoke.called

