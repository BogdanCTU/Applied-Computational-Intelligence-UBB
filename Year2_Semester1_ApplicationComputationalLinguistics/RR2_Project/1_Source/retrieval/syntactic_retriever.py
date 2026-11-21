"""Syntactic retriever module reproducing Agent-OM syntactic representation generation."""

from __future__ import annotations

from typing import Union
from rdflib import URIRef

from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import OntologyEntity
from ..utils.text_processing import cleaning, uri_to_name


class SyntacticRetriever:
    """
    Retrieves and constructs syntactic representation for ontology entities.
    Reproduces the syntactic() tool function in om_ontology_to_csv.py.
    """

    def __init__(self, ontology_is_code: bool = False):
        self.ontology_is_code = ontology_is_code

    def extract_entity_name(
        self,
        entity: Union[OntologyEntity, str, URIRef],
        ontology: OntologyGraph | None = None,
    ) -> str:
        """
        Derives the entity name to normalize.
        If entity is an OntologyEntity, uses display_name if ontology_is_code else local_name.
        If entity is a string/URIRef and ontology is provided:
        - If ontology_is_code: checks rdfs:label/skos:prefLabel or falls back to uri_to_name.
        - Else: uri_to_name(entity).
        """
        if isinstance(entity, OntologyEntity):
            if self.ontology_is_code:
                return entity.display_name or entity.local_name
            return entity.local_name

        uri_str = str(entity)
        if self.ontology_is_code and ontology is not None:
            label = ontology.get_entity_label(URIRef(uri_str))
            if label:
                return label
        return uri_to_name(uri_str)

    def retrieve_syntactic_representation(
        self,
        entity: Union[OntologyEntity, str, URIRef],
        ontology: OntologyGraph | None = None,
    ) -> str:
        """
        Generates the cleaned syntactic representation string.
        Applies exact Agent-OM normalization:
        - Symbol replacement
        - Snake_case conversion
        - Lowercasing
        - British-to-American translation
        """
        entity_name = self.extract_entity_name(entity, ontology)
        cleaned = cleaning(entity_name)
        return cleaned

