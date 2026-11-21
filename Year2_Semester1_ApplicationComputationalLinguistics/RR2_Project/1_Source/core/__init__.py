"""Core domain logic: ontology parsing, entity extraction, evaluation metrics, and configuration."""
from ..config import AppConfig, VALID_PROFILES, STRICT_4B_PROFILES, PROTECTED_DATABASES, config
from ..ontology.parser import OntologyGraph, OntologyParseError, load_ontology
from ..ontology.entity_extractor import EntityExtractor, EntityType, ExtractionSummary, OntologyEntity
from ..evaluation.metrics import compute_alignment_metrics, compute_stage_attrition, load_reference_pairs
from ..evaluation.comparator import compare_two_runs_17_points, load_features_csv
