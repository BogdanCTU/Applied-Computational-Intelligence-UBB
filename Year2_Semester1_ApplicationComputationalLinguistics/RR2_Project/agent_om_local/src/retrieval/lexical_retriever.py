"""Lexical retriever module reproducing Agent-OM lexical feature extraction and LLM prompting."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Union
import rdflib
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from ..config import config
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
    ):
        self.llm = llm
        self.context = context
        self.ontology_is_code = ontology_is_code
        self.prompt_with_extra = PromptTemplate(
            input_variables=["entity_name", "context", "extra_information"],
            template=self.TEMPLATE_WITH_EXTRA,
        )
        self.prompt_without_extra = PromptTemplate(
            input_variables=["entity_name", "context"],
            template=self.TEMPLATE_WITHOUT_EXTRA,
        )

    def _ensure_llm(self) -> BaseChatModel:
        """Instantiate default ChatOllama model if not injected."""
        if self.llm is None:
            self.llm = ChatOllama(
                model=config.default_llm,
                temperature=config.temperature,
                num_ctx=config.num_ctx,
            )
        return self.llm

    def extract_extra_information(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> str:
        """
        Collects all lexical annotations from the 10 predicates.
        Reproduces lines 135-157 of om_ontology_to_csv.py.
        """
        uri = URIRef(str(entity_uri))
        extra_set: Set[str] = set()

        for pred in self.LEXICAL_PREDICATES:
            for s, p, o in ontology_graph.triples((uri, pred, None)):
                extra_set.add(str(o))

        # Join unique non-empty comments
        extra_info = " ".join(sorted(list(extra_set)))
        return extra_info

    def get_entity_name(
        self,
        entity_uri: Union[str, URIRef],
        ontology_graph: Graph,
    ) -> str:
        """Extracts display name based on ontology_is_code flag."""
        uri = URIRef(str(entity_uri))
        if self.ontology_is_code:
            # Check rdfs:label and skos:prefLabel
            for _, _, o in ontology_graph.triples((uri, RDFS.label, None)):
                return str(o)
            for _, _, o in ontology_graph.triples((uri, SKOS.prefLabel, None)):
                return str(o)
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

        content = str(response.content).strip()
        metadata = {
            "entity_uri": uri,
            "entity_name": entity_name,
            "has_extra_info": bool(extra_info),
            "extra_info": extra_info,
            "prompt_text": prompt_text,
            "duration_ms": duration_ms,
            "response_metadata": getattr(response, "response_metadata", {}),
        }

        return content, metadata

