"""Semantic retriever module reproducing Agent-OM 18-predicate subgraph extraction and verbalization."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import rdflib
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from rdflib.term import Node
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from ..config import config
from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import OntologyEntity
from ..utils.text_processing import uri_to_name


Triple = Tuple[Node, Node, Node]


class SemanticRetriever:
    """
    Extracts structural subgraphs (18 relevant predicates) and blank-node closures,
    and verbalizes them into natural language representations using local LLMs.
    Reproduces the semantic() tool function in om_ontology_to_csv.py.
    """

    RELEVANT_PREDICATES = [
        RDFS.subClassOf,
        RDFS.subPropertyOf,
        OWL.disjointWith,
        RDFS.domain,
        RDFS.range,
        OWL.equivalentClass,
        OWL.equivalentProperty,
        SKOS.broader,
        SKOS.narrower,
        SKOS.hasTopConcept,
        SKOS.topConceptOf,
        SKOS.exactMatch,
        SKOS.closeMatch,
        SKOS.broadMatch,
        SKOS.narrowMatch,
        SKOS.relatedMatch,
        SKOS.related,
        SKOS.semanticRelation,
    ]

    PROMPT_TRIPLES = PromptTemplate(
        input_variables=["subgraph"],
        template="Verbalise triples into phrases: {subgraph}",
    )

    PROMPT_COMPLEX = PromptTemplate(
        input_variables=["subgraph"],
        template="Verbalise the subgraph into a natual language description: {subgraph}",
    )

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        ontology_is_code: bool = False,
        null_value_sentence: str = config.null_value_sentence,
    ):
        self.llm = llm
        self.ontology_is_code = ontology_is_code
        self.null_value_sentence = null_value_sentence

    def _ensure_llm(self) -> BaseChatModel:
        """Instantiate default ChatOllama model if not injected."""
        if self.llm is None:
            self.llm = ChatOllama(
                model=config.default_llm,
                temperature=config.temperature,
                num_ctx=config.num_ctx,
            )
        return self.llm

    def get_entity_name(
        self,
        node: Node,
        ontology_graph: Graph,
    ) -> str:
        """
        Derives entity name for serialization.
        Reproduces om_ontology_to_csv.get_entity_name().
        """
        if isinstance(node, URIRef):
            if self.ontology_is_code:
                for _, _, o in ontology_graph.triples((node, RDFS.label, None)):
                    return str(o)
                for _, _, o in ontology_graph.triples((node, SKOS.prefLabel, None)):
                    return str(o)
            return uri_to_name(node)
        return str(node)

    def extract_subgraph_18_predicates(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> Graph:
        """
        Extracts triples touching entity over 18 predicates, resolving entity URIs to names.
        Reproduces lines 201-224 of om_ontology_to_csv.py.
        """
        entity = URIRef(str(entity_uri))
        subgraph = Graph()

        for predicate in self.RELEVANT_PREDICATES:
            # Outgoing triples
            for s, p, o in ontology_graph.triples((entity, predicate, None)):
                if o != OWL.Thing and not isinstance(o, BNode):
                    sub = Literal(self.get_entity_name(s, ontology_graph))
                    obj = Literal(self.get_entity_name(o, ontology_graph))
                    subgraph.add((sub, p, obj))

            # Incoming triples
            for s, p, o in ontology_graph.triples((None, predicate, entity)):
                if s != OWL.Thing:
                    sub = Literal(self.get_entity_name(s, ontology_graph))
                    obj = Literal(self.get_entity_name(o, ontology_graph))
                    subgraph.add((sub, p, obj))

        return subgraph

    def expand_bnode_closure_named(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
        seed_only_if_has_bnode: bool = True,
        max_triples: Optional[int] = None,
    ) -> Set[Tuple[str, str, str]]:
        """
        Expands blank nodes connected to entity and normalizes node names.
        Reproduces expand_bnode_closure_named from om_ontology_to_csv.py.
        """
        entity = URIRef(str(entity_uri))

        def has_bnode(t: Triple) -> bool:
            return any(isinstance(n, BNode) for n in t)

        def iter_touching(node: Node):
            yield from ontology_graph.triples((node, None, None))
            yield from ontology_graph.triples((None, node, None))
            yield from ontology_graph.triples((None, None, node))

        def normalize(node: Node) -> str:
            if isinstance(node, URIRef):
                return self.get_entity_name(node, ontology_graph)
            elif isinstance(node, BNode):
                return f"_:{str(node)}"
            return str(node)

        results: Set[Triple] = set()
        seen_bnodes: Set[BNode] = set()
        frontier: Set[BNode] = set()

        # Seed phase
        seeded_any = False
        for t in iter_touching(entity):
            if seed_only_if_has_bnode and not has_bnode(t):
                continue
            results.add(t)
            seeded_any = True
            for n in t:
                if isinstance(n, BNode):
                    frontier.add(n)
            if max_triples is not None and len(results) >= max_triples:
                break

        if not seeded_any and not seed_only_if_has_bnode:
            for t in iter_touching(entity):
                results.add(t)
                for n in t:
                    if isinstance(n, BNode):
                        frontier.add(n)
                if max_triples is not None and len(results) >= max_triples:
                    break

        # Expansion phase
        while frontier:
            b = frontier.pop()
            if b in seen_bnodes:
                continue
            seen_bnodes.add(b)

            for t in iter_touching(b):
                if t in results:
                    continue
                results.add(t)
                for n in t:
                    if isinstance(n, BNode) and n not in seen_bnodes:
                        frontier.add(n)
                if max_triples is not None and len(results) >= max_triples:
                    frontier.clear()
                    break

        named_triples: Set[Tuple[str, str, str]] = set()
        for s, p, o in results:
            named_triples.add((normalize(s), normalize(p), normalize(o)))

        return named_triples

    def retrieve_semantic_representation(
        self,
        entity: Union[OntologyEntity, str, URIRef],
        ontology: Union[OntologyGraph, Graph],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extracts subgraphs, executes verbalization chains, and combines answers.
        
        Returns:
            Tuple of (semantic_representation_text, metadata_dict).
        """
        graph = ontology.graph if isinstance(ontology, OntologyGraph) else ontology
        uri = entity.uri if isinstance(entity, OntologyEntity) else str(entity)

        answer = ""
        metadata: Dict[str, Any] = {
            "entity_uri": uri,
            "has_predicate_triples": False,
            "predicate_triple_count": 0,
            "has_complex_bnode": False,
            "complex_bnode_count": 0,
            "duration_ms": 0.0,
        }

        t0 = time.perf_counter()
        llm = self._ensure_llm()

        # 1. 18-predicate subgraph
        subgraph = self.extract_subgraph_18_predicates(uri, graph)
        if len(subgraph) > 0:
            metadata["has_predicate_triples"] = True
            metadata["predicate_triple_count"] = len(subgraph)
            serialized_subgraph = subgraph.serialize(format="turtle")
            prompt_text = self.PROMPT_TRIPLES.format(subgraph=serialized_subgraph)
            resp = llm.invoke(prompt_text)
            answer += str(resp.content).strip() + "\n"

        # 2. Blank-node complex closure
        complex_triples = self.expand_bnode_closure_named(uri, graph)
        if complex_triples:
            metadata["has_complex_bnode"] = True
            metadata["complex_bnode_count"] = len(complex_triples)
            # Format complex triples string matching original invocation
            prompt_text = self.PROMPT_COMPLEX.format(subgraph=complex_triples)
            resp = llm.invoke(prompt_text)
            answer += str(resp.content).strip()

        # Fallback if no verbalization generated
        answer = answer.strip()
        if not answer:
            answer = self.null_value_sentence

        metadata["duration_ms"] = (time.perf_counter() - t0) * 1000.0
        return answer, metadata

