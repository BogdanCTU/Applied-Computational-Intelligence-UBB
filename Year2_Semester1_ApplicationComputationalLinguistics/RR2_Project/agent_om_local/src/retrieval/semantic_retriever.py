"""Semantic retriever module reproducing Agent-OM 18-predicate subgraph extraction and verbalization."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Set, Tuple, Union
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDFS, SKOS
from rdflib.term import Node
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel

from ..config import AppConfig, config
from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import OntologyEntity
from ..utils.text_processing import uri_to_name


Triple = Tuple[Node, Node, Node]


class SemanticRetriever:
    """
    Extracts structural subgraphs (18 relevant predicates in HEAD, 7 in PVLDB v1.0.0)
    and blank-node closures, verbalizing them into natural language using local LLMs.
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

    PVL_V1_PREDICATES = [
        RDFS.subClassOf,
        RDFS.subPropertyOf,
        OWL.disjointWith,
        RDFS.domain,
        RDFS.range,
        OWL.equivalentClass,
        OWL.equivalentProperty,
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
        predicate_scope: str = "head",
        concat_separator: str = "\n",
        strip_response: bool = True,
        sort_bnode_triples: bool = True,
        app_config: Optional[AppConfig] = None,
    ):
        self.llm = llm
        self.ontology_is_code = ontology_is_code
        self.null_value_sentence = null_value_sentence
        self.predicate_scope = predicate_scope
        self.concat_separator = concat_separator
        self.strip_response = strip_response
        self.sort_bnode_triples = sort_bnode_triples
        self.app_config = app_config or config

    def _ensure_llm(self) -> BaseChatModel:
        """Instantiate configured local ChatOllama model if not injected."""
        if self.llm is None:
            self.llm = self.app_config.build_chat_llm()
        return self.llm

    def get_entity_name(
        self,
        node: Node,
        ontology_graph: Graph,
    ) -> str:
        """
        Derives entity name for serialization deterministically.
        Reproduces om_ontology_to_csv.get_entity_name().
        """
        if isinstance(node, URIRef):
            if self.ontology_is_code:
                rdfs_labels = sorted(
                    str(o) for _, _, o in ontology_graph.triples((node, RDFS.label, None)) if str(o)
                )
                if rdfs_labels:
                    return rdfs_labels[0]
                skos_labels = sorted(
                    str(o) for _, _, o in ontology_graph.triples((node, SKOS.prefLabel, None)) if str(o)
                )
                if skos_labels:
                    return skos_labels[0]
            return uri_to_name(node)
        return str(node)

    def extract_subgraph_18_predicates(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> Graph:
        """
        Extracts triples touching entity over relevant predicates (18 in HEAD, 7 in PVLDB v1.0.0),
        resolving entity URIs to names. Reproduces lines 201-224 of om_ontology_to_csv.py.
        """
        entity = URIRef(str(entity_uri))
        subgraph = Graph()
        predicates = (
            self.PVL_V1_PREDICATES
            if self.predicate_scope == "pvl_v1"
            else self.RELEVANT_PREDICATES
        )

        for predicate in predicates:
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

        parts: list[str] = []
        llm_calls = 0
        prompt_tokens = 0
        completion_tokens = 0
        metadata: Dict[str, Any] = {
            "entity_uri": uri,
            "has_predicate_triples": False,
            "predicate_triple_count": 0,
            "has_complex_bnode": False,
            "complex_bnode_count": 0,
            "llm_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "duration_ms": 0.0,
        }

        t0 = time.perf_counter()

        # 1. Predicate subgraph (18 predicates in HEAD, 7 in PVLDB v1.0.0)
        subgraph = self.extract_subgraph_18_predicates(uri, graph)
        if len(subgraph) > 0:
            llm = self._ensure_llm()
            metadata["has_predicate_triples"] = True
            metadata["predicate_triple_count"] = len(subgraph)
            serialized_subgraph = subgraph.serialize(format="turtle")
            prompt_text = self.PROMPT_TRIPLES.format(subgraph=serialized_subgraph)
            resp = llm.invoke(prompt_text)
            llm_calls += 1
            resp_meta = getattr(resp, "response_metadata", {}) or {}
            prompt_tokens += int(resp_meta.get("prompt_eval_count", 0) or 0)
            completion_tokens += int(resp_meta.get("eval_count", 0) or 0)
            text = str(resp.content).strip() if self.strip_response else str(resp.content)
            parts.append(text)

        # 2. Blank-node complex closure (enabled in HEAD; absent in PVLDB v1.0.0)
        if self.predicate_scope != "pvl_v1":
            complex_triples = self.expand_bnode_closure_named(uri, graph)
            if complex_triples:
                llm = self._ensure_llm()
                metadata["has_complex_bnode"] = True
                metadata["complex_bnode_count"] = len(complex_triples)
                formatted_complex: Any = (
                    "{" + ", ".join(repr(t) for t in sorted(complex_triples)) + "}"
                    if self.sort_bnode_triples
                    else complex_triples
                )
                prompt_text = self.PROMPT_COMPLEX.format(subgraph=formatted_complex)
                resp = llm.invoke(prompt_text)
                llm_calls += 1
                resp_meta = getattr(resp, "response_metadata", {}) or {}
                prompt_tokens += int(resp_meta.get("prompt_eval_count", 0) or 0)
                completion_tokens += int(resp_meta.get("eval_count", 0) or 0)
                text = str(resp.content).strip() if self.strip_response else str(resp.content)
                parts.append(text)

        if parts:
            answer = self.concat_separator.join(parts)
            if self.strip_response:
                answer = answer.strip()
        else:
            answer = ""

        # Fallback if no verbalization generated
        if not answer.strip():
            answer = self.null_value_sentence

        metadata["llm_calls"] = llm_calls
        metadata["prompt_tokens"] = prompt_tokens
        metadata["completion_tokens"] = completion_tokens
        metadata["duration_ms"] = (time.perf_counter() - t0) * 1000.0
        return answer, metadata
