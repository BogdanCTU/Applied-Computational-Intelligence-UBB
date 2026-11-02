"""Ontology entity extractor for extracting classes, properties, and rich metadata."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import rdflib
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .parser import OntologyGraph


class EntityType(str, Enum):
    """Ontology entity types consistent with Agent-OM conventions."""
    CLASS = "Class"
    PROPERTY = "Property"


@dataclass
class OntologyEntity:
    """Represents an ontology entity with all metadata extracted for downstream matching."""
    uri: str
    local_name: str
    display_name: str
    entity_type: EntityType
    source_or_target: str
    property_kind: Optional[str] = None  # "ObjectProperty", "DatatypeProperty", or None
    labels: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    ranges: List[str] = field(default_factory=list)
    super_entities: List[str] = field(default_factory=list)
    sub_entities: List[str] = field(default_factory=list)
    disjoint_with: List[str] = field(default_factory=list)
    equivalent_entities: List[str] = field(default_factory=list)

    @property
    def primary_label(self) -> str:
        """Returns the primary label if available, otherwise the display name."""
        if self.labels:
            return self.labels[0]
        return self.display_name


@dataclass
class ExtractionSummary:
    """Summary of extraction performance, counts, and filtered entities."""
    duration_ms: float
    total_classes: int
    total_object_properties: int
    total_datatype_properties: int
    total_properties: int
    total_entities: int
    excluded_entities: Dict[str, str] = field(default_factory=dict)  # URI -> reason


class EntityExtractor:
    """Extracts entities and metadata from an OntologyGraph according to Agent-OM methodology."""

    # Built-in exclusions from Agent-OM's util.remove_exceptions()
    DEFAULT_EXCLUSIONS: Set[str] = {
        "http://www.geneontology.org/formats/oboInOwl#Subset",
        "http://www.geneontology.org/formats/oboInOwl#Synonym",
        "http://www.geneontology.org/formats/oboInOwl#DbXref",
        "http://www.geneontology.org/formats/oboInOwl#ObsoleteClass",
        "http://www.geneontology.org/formats/oboInOwl#SynonymType",
        "http://www.geneontology.org/formats/oboInOwl#Definition",
        "http://www.geneontology.org/formats/oboInOwl#ObsoleteProperty",
        "http://mouse.owl#UNDEFINED_is_a",
        "http://mouse.owl#UNDEFINED_part_of",
        "http://human.owl#UNDEFINED_part_of",
        "http://www.w3.org/2004/02/skos/core#Concept",
    }

    # Lexical annotation predicates collected in Agent-OM's lexical() retriever
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

    def __init__(self, exclusions: Optional[Set[str]] = None):
        self.exclusions: Set[str] = exclusions if exclusions is not None else set(self.DEFAULT_EXCLUSIONS)

    def extract_entity_label(self, graph: Graph, entity_uri: URIRef) -> str:
        """
        Extract primary label using rdfs:label or skos:prefLabel.
        Reproduces om_ontology_to_csv.get_entity_label().
        """
        results_rdfs = set(graph.triples((entity_uri, RDFS.label, None)))
        results_skos = set(graph.triples((entity_uri, SKOS.prefLabel, None)))
        combined = results_rdfs.union(results_skos)
        for s, p, o in combined:
            return str(o)
        return ""

    def get_entity_display_name(self, graph: Graph, entity_uri: URIRef, ontology_is_code: bool) -> str:
        """
        Derive entity display name based on ontology_is_code setting.
        Reproduces om_ontology_to_csv.get_entity_name().
        """
        if ontology_is_code:
            return self.extract_entity_label(graph, entity_uri) or OntologyGraph.uri_to_name(entity_uri)
        return OntologyGraph.uri_to_name(entity_uri)

    def extract_entities(
        self,
        ontology: OntologyGraph,
        source_or_target: str,
        ontology_is_code: bool = False,
    ) -> Tuple[List[OntologyEntity], ExtractionSummary]:
        """
        Extract classes and properties with metadata from the ontology graph.
        
        Args:
            ontology: The OntologyGraph wrapper.
            source_or_target: String indicator ('Source' or 'Target').
            ontology_is_code: Whether entity names should prioritize rdfs:label over URI.
            
        Returns:
            Tuple of (list of OntologyEntity, ExtractionSummary).
        """
        start_time = time.perf_counter()
        g = ontology.graph

        raw_classes: Set[URIRef] = set()
        raw_obj_props: Set[URIRef] = set()
        raw_data_props: Set[URIRef] = set()
        excluded: Dict[str, str] = {}

        # 1. Extract OWL Classes and SKOS Concepts
        for s in g.subjects(RDF.type, None):
            if isinstance(s, BNode):
                continue
            s_str = str(s)
            if (s, RDF.type, OWL.Class) in g or (s, RDF.type, SKOS.Concept) in g:
                if not ("#" in s_str or "/" in s_str):
                    excluded[s_str] = "Missing '#' or '/' in URI"
                    continue
                if s == OWL.Thing:
                    excluded[s_str] = "Built-in owl:Thing excluded"
                    continue
                if s_str in self.exclusions:
                    excluded[s_str] = "In exclusion list (anatomy/vocabulary)"
                    continue
                raw_classes.add(s)

        # 2. Extract Object Properties
        for s in g.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(s, BNode):
                continue
            s_str = str(s)
            if not ("#" in s_str or "/" in s_str):
                excluded[s_str] = "Missing '#' or '/' in URI"
                continue
            if s_str in self.exclusions:
                excluded[s_str] = "In exclusion list"
                continue
            raw_obj_props.add(s)

        # 3. Extract Datatype Properties
        for s in g.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(s, BNode):
                continue
            s_str = str(s)
            if not ("#" in s_str or "/" in s_str):
                excluded[s_str] = "Missing '#' or '/' in URI"
                continue
            if s_str in self.exclusions:
                excluded[s_str] = "In exclusion list"
                continue
            raw_data_props.add(s)

        # Sort URIs for deterministic order matching original implementation
        sorted_classes = sorted(list(raw_classes), key=str)
        sorted_obj_props = sorted(list(raw_obj_props), key=str)
        sorted_data_props = sorted(list(raw_data_props), key=str)

        entities: List[OntologyEntity] = []

        # Process Classes
        for uri in sorted_classes:
            ent = self._build_entity_metadata(
                graph=g,
                uri=uri,
                entity_type=EntityType.CLASS,
                property_kind=None,
                source_or_target=source_or_target,
                ontology_is_code=ontology_is_code,
            )
            entities.append(ent)

        # Process Object Properties
        for uri in sorted_obj_props:
            ent = self._build_entity_metadata(
                graph=g,
                uri=uri,
                entity_type=EntityType.PROPERTY,
                property_kind="ObjectProperty",
                source_or_target=source_or_target,
                ontology_is_code=ontology_is_code,
            )
            entities.append(ent)

        # Process Datatype Properties
        for uri in sorted_data_props:
            ent = self._build_entity_metadata(
                graph=g,
                uri=uri,
                entity_type=EntityType.PROPERTY,
                property_kind="DatatypeProperty",
                source_or_target=source_or_target,
                ontology_is_code=ontology_is_code,
            )
            entities.append(ent)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        summary = ExtractionSummary(
            duration_ms=elapsed_ms,
            total_classes=len(sorted_classes),
            total_object_properties=len(sorted_obj_props),
            total_datatype_properties=len(sorted_data_props),
            total_properties=len(sorted_obj_props) + len(sorted_data_props),
            total_entities=len(entities),
            excluded_entities=excluded,
        )

        return entities, summary

    def _build_entity_metadata(
        self,
        graph: Graph,
        uri: URIRef,
        entity_type: EntityType,
        property_kind: Optional[str],
        source_or_target: str,
        ontology_is_code: bool,
    ) -> OntologyEntity:
        """Collect all annotation and structural metadata for an entity."""
        uri_str = str(uri)
        local_name = OntologyGraph.uri_to_name(uri)
        display_name = self.get_entity_display_name(graph, uri, ontology_is_code)

        # Labels (rdfs:label, skos:prefLabel)
        labels: List[str] = []
        for _, _, o in graph.triples((uri, RDFS.label, None)):
            labels.append(str(o))
        for _, _, o in graph.triples((uri, SKOS.prefLabel, None)):
            if str(o) not in labels:
                labels.append(str(o))

        # Comments & Lexical definitions
        comments_set: Set[str] = set()
        for pred in self.LEXICAL_PREDICATES:
            for _, _, o in graph.triples((uri, pred, None)):
                if isinstance(o, Literal):
                    val = str(o).strip()
                    if val:
                        comments_set.add(val)
        comments = sorted(list(comments_set))

        # Domains and Ranges (for properties)
        domains: List[str] = []
        ranges: List[str] = []
        for _, _, o in graph.triples((uri, RDFS.domain, None)):
            if not isinstance(o, BNode) and o != OWL.Thing:
                domains.append(str(o))
        for _, _, o in graph.triples((uri, RDFS.range, None)):
            if not isinstance(o, BNode) and o != OWL.Thing:
                ranges.append(str(o))

        # Super/Sub entities
        super_entities: List[str] = []
        sub_entities: List[str] = []
        sub_pred = RDFS.subClassOf if entity_type == EntityType.CLASS else RDFS.subPropertyOf
        for _, _, o in graph.triples((uri, sub_pred, None)):
            if not isinstance(o, BNode) and o != OWL.Thing:
                super_entities.append(str(o))
        for s, _, _ in graph.triples((None, sub_pred, uri)):
            if not isinstance(s, BNode) and s != OWL.Thing:
                sub_entities.append(str(s))

        # Disjointness
        disjoint_with: List[str] = []
        for _, _, o in graph.triples((uri, OWL.disjointWith, None)):
            if not isinstance(o, BNode):
                disjoint_with.append(str(o))

        # Equivalence
        equivalent_entities: List[str] = []
        equiv_pred = OWL.equivalentClass if entity_type == EntityType.CLASS else OWL.equivalentProperty
        for _, _, o in graph.triples((uri, equiv_pred, None)):
            if not isinstance(o, BNode):
                equivalent_entities.append(str(o))

        return OntologyEntity(
            uri=uri_str,
            local_name=local_name,
            display_name=display_name,
            entity_type=entity_type,
            property_kind=property_kind,
            source_or_target=source_or_target,
            labels=labels,
            comments=comments,
            domains=sorted(domains),
            ranges=sorted(ranges),
            super_entities=sorted(super_entities),
            sub_entities=sorted(sub_entities),
            disjoint_with=sorted(disjoint_with),
            equivalent_entities=sorted(equivalent_entities),
        )

