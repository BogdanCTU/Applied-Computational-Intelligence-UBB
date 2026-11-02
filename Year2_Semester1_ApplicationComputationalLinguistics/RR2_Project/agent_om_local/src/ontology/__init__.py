"""Ontology parsing and metadata extraction module."""
from .parser import OntologyGraph, load_ontology
from .entity_extractor import EntityExtractor, OntologyEntity, EntityType

__all__ = ["OntologyGraph", "load_ontology", "EntityExtractor", "OntologyEntity", "EntityType"]

