"""Lexical retriever module reproducing Agent-OM lexical feature extraction and LLM prompting."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Set, Tuple, Union
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel

from ..config import AppConfig, config
from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import OntologyEntity
from ..utils.text_processing import uri_to_name


class LexicalRetriever:
    """
    Retrieves annotations and constructs lexical explanations for ontology entities.
    Reproduces the lexical() tool function in om_ontology_to_csv.py.
    """

    LEXICAL_PREDICATES = [
        RDFS.comment,
        RDF.value,
        SKOS.definition,
        SKOS.notation,
        SKOS.note,
        SKOS.scopeNote,
        SKOS.editorialNote,
        SKOS.historyNote,
        SKOS.changeNote,
        SKOS.example,
    ]

    PVL_V1_LEXICAL_PREDICATES = [
        RDFS.comment,
        RDF.value,
    ]

    TEMPLATE_WITH_EXTRA = (
        "Question: What is the meaning of {entity_name}?\n"
        "Context: {context}\n"
        "Extra Information: {extra_information}\n"
        "Answer the question within the context and using the extra information.\n"
    )

    TEMPLATE_WITHOUT_EXTRA = (
        "Question: What is the meaning of {entity_name}?\n"
        "Context: {context}\n"
        "Answer the question within the context.\n"
    )

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        context: str = "conference",
        ontology_is_code: bool = False,
        predicate_scope: str = "head",
        sort_annotations: bool = True,
        strip_response: bool = True,
        app_config: Optional[AppConfig] = None,
    ):
        self.llm = llm
        self.context = context
        self.ontology_is_code = ontology_is_code
        self.predicate_scope = predicate_scope
        self.sort_annotations = sort_annotations
        self.strip_response = strip_response
        self.app_config = app_config or config
        self.prompt_with_extra = PromptTemplate(
            input_variables=["entity_name", "context", "extra_information"],
            template=self.TEMPLATE_WITH_EXTRA,
        )
        self.prompt_without_extra = PromptTemplate(
            input_variables=["entity_name", "context"],
            template=self.TEMPLATE_WITHOUT_EXTRA,
        )

    def _ensure_llm(self) -> BaseChatModel:
        """Instantiate configured local ChatOllama model if not injected."""
        if self.llm is None:
            self.llm = self.app_config.build_chat_llm()
        return self.llm

    def extract_extra_information(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> str:
        """
        Collects lexical annotations from configured predicates (10 in HEAD, 2 in PVLDB v1.0.0).
        Reproduces lines 135-157 of om_ontology_to_csv.py.
        """
        uri = URIRef(str(entity_uri))
        predicates = (
            self.PVL_V1_LEXICAL_PREDICATES
            if self.predicate_scope == "pvl_v1"
            else self.LEXICAL_PREDICATES
        )

        if self.sort_annotations:
            extra_set: Set[str] = set()
            for pred in predicates:
                for _, _, o in ontology_graph.triples((uri, pred, None)):
                    extra_set.add(str(o))
            return " ".join(sorted(list(extra_set)))

        seen: list[str] = []
        for pred in predicates:
            for _, _, o in ontology_graph.triples((uri, pred, None)):
                val = str(o)
                if val not in seen:
                    seen.append(val)
        return " ".join(seen)

    def get_entity_name(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> str:
        """Extracts display name based on ontology_is_code flag deterministically."""
        uri = URIRef(str(entity_uri))
        if self.ontology_is_code:
            rdfs_labels = sorted(str(o) for _, _, o in ontology_graph.triples((uri, RDFS.label, None)) if str(o))
            if rdfs_labels:
                return rdfs_labels[0]
            skos_labels = sorted(str(o) for _, _, o in ontology_graph.triples((uri, SKOS.prefLabel, None)) if str(o))
            if skos_labels:
                return skos_labels[0]
        return uri_to_name(uri)

    def build_prompt_text(
        self,
        entity_name: str,
        extra_information: str,
    ) -> str:
        """Constructs the prompt string to send to the LLM."""
        if extra_information:
            return self.prompt_with_extra.format(
                entity_name=entity_name,
                context=self.context,
                extra_information=extra_information,
            )
        return self.prompt_without_extra.format(
            entity_name=entity_name,
            context=self.context,
        )

    def retrieve_lexical_representation(
        self,
        entity: Union[OntologyEntity, str, URIRef],
        ontology: Union[OntologyGraph, Graph],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generates lexical meaning explanation using local LLM via Ollama.
        
        Returns:
            Tuple of (response_text, metadata_dict).
        """
        graph = ontology.graph if isinstance(ontology, OntologyGraph) else ontology
        uri = entity.uri if isinstance(entity, OntologyEntity) else str(entity)

        entity_name = self.get_entity_name(uri, graph)
        extra_info = self.extract_extra_information(uri, graph)
        prompt_text = self.build_prompt_text(entity_name, extra_info)

        llm = self._ensure_llm()
        t0 = time.perf_counter()
        response = llm.invoke(prompt_text)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        raw_content = str(response.content)
        content = raw_content.strip() if self.strip_response else raw_content
        resp_meta = getattr(response, "response_metadata", {}) or {}
        prompt_tokens = int(resp_meta.get("prompt_eval_count", 0) or 0)
        completion_tokens = int(resp_meta.get("eval_count", 0) or 0)

        metadata = {
            "entity_uri": uri,
            "entity_name": entity_name,
            "has_extra_info": bool(extra_info),
            "extra_info": extra_info,
            "prompt_text": prompt_text,
            "duration_ms": duration_ms,
            "llm_calls": 1,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "response_metadata": resp_meta,
        }

        return content, metadata
