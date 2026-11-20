"""Ontology parser for loading and managing RDF/OWL/SKOS ontologies using RDFLib."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS


class OntologyParseError(Exception):
    """Raised when an ontology file cannot be parsed or format is unsupported."""
    pass


class OntologyGraph:
    """Encapsulates an RDFLib Graph with ontology-specific metadata and namespace helpers."""

    SUPPORTED_FORMATS: Dict[str, str] = {
        ".xml": "xml",
        ".owl": "xml",
        ".rdf": "xml",
        ".ttl": "turtle",
        ".n3": "n3",
        ".nt": "nt",
        ".jsonld": "json-ld",
    }

    def __init__(self, graph: Optional[Graph] = None, source_path: Optional[str] = None):
        self.graph: Graph = graph if graph is not None else Graph()
        self.source_path: Optional[str] = source_path
        self._namespaces: Dict[str, str] = {}
        self._refresh_namespaces()

    def _refresh_namespaces(self) -> None:
        """Cache all namespace prefixes declared in the graph."""
        self._namespaces = {str(prefix): str(ns) for prefix, ns in self.graph.namespaces()}

    @property
    def namespaces(self) -> Dict[str, str]:
        """Return declared namespace prefixes and URIs."""
        return dict(self._namespaces)

    @property
    def triple_count(self) -> int:
        """Return the number of triples in the graph."""
        return len(self.graph)

    @classmethod
    def from_file(cls, file_path: str | Path, format: Optional[str] = None) -> OntologyGraph:
        """
        Load an ontology from a file with automatic format detection and fallback.
        
        Args:
            file_path: Path to the ontology file.
            format: Optional format string (e.g. 'xml', 'turtle'). If None, inferred from extension.
            
        Returns:
            OntologyGraph instance.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            OntologyParseError: If parsing fails or format is unsupported.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Ontology file not found: {path}")

        # Determine formats to attempt
        ext = path.suffix.lower()
        primary_format = format or cls.SUPPORTED_FORMATS.get(ext, "xml")

        graph = Graph()
        # List of candidate formats to try if primary fails
        candidate_formats = [primary_format]
        for alt_fmt in ["xml", "turtle", "n3"]:
            if alt_fmt not in candidate_formats:
                candidate_formats.append(alt_fmt)

        last_error = None
        for fmt in candidate_formats:
            try:
                graph.parse(location=str(path), format=fmt)
                return cls(graph=graph, source_path=str(path))
            except Exception as e:
                last_error = e
                graph = Graph()  # Reset graph before next attempt

        raise OntologyParseError(
            f"Failed to parse ontology '{path}' with candidate formats {candidate_formats}. "
            f"Last error: {last_error}"
        ) from last_error

    @classmethod
    def from_string(cls, data: str, format: str = "xml") -> OntologyGraph:
        """
        Load an ontology from a string.
        
        Args:
            data: Raw serialization of the ontology.
            format: Format string ('xml', 'turtle', etc.).
            
        Returns:
            OntologyGraph instance.
        """
        graph = Graph()
        try:
            graph.parse(data=data, format=format)
            return cls(graph=graph, source_path=None)
        except Exception as e:
            raise OntologyParseError(f"Failed to parse ontology data as '{format}': {e}") from e

    def find_base_uri(self) -> str:
        """
        Identify the default or base namespace URI of the ontology.
        Reproduces util.find_uri() from original Agent-OM.
        """
        for ns_prefix, namespace in self.graph.namespaces():
            if not ns_prefix:
                return str(namespace)
        # Fallback to source path or first declared namespace
        if self._namespaces:
            return next(iter(self._namespaces.values()))
        return ""

    def get_entity_label(self, entity_uri: str | URIRef) -> str:
        """
        Extract primary label using rdfs:label (priority) or skos:prefLabel deterministically.
        Reproduces om_ontology_to_csv.get_entity_label().
        """
        uri = URIRef(str(entity_uri))
        rdfs_labels = sorted(str(o) for _, _, o in self.graph.triples((uri, RDFS.label, None)) if str(o))
        if rdfs_labels:
            return rdfs_labels[0]
        skos_labels = sorted(str(o) for _, _, o in self.graph.triples((uri, SKOS.prefLabel, None)) if str(o))
        if skos_labels:
            return skos_labels[0]
        return ""

    def resolve_entity_name(self, entity_uri: str | URIRef, ontology_is_code: bool = False) -> str:
        """
        Resolve human-readable entity name: when `ontology_is_code=True`, prefer
        `rdfs:label` -> `skos:prefLabel` -> `uri_to_name`, else `uri_to_name`.
        """
        if ontology_is_code:
            lbl = self.get_entity_label(entity_uri)
            if lbl:
                return lbl
        return self.uri_to_name(entity_uri)

    @staticmethod
    def uri_to_name(uri: str | URIRef) -> str:
        """
        Extract the local entity name from a URI.
        Splits by '#' first if present, otherwise by '/'.
        Reproduces util.uri_to_name() from original Agent-OM.
        """
        uri_str = str(uri)
        if "#" in uri_str:
            return uri_str.rsplit("#", maxsplit=1)[-1]
        return uri_str.rsplit("/", maxsplit=1)[-1]

    @staticmethod
    def uri_to_prefix_name(uri: str | URIRef, prefix: str) -> str:
        """
        Format an entity URI as 'prefix:local_name'.
        Reproduces util.uri_to_prefix_name() from original Agent-OM.
        """
        local_name = OntologyGraph.uri_to_name(uri)
        return f"{prefix}:{local_name}"


def load_ontology(file_path: str | Path, format: Optional[str] = None) -> OntologyGraph:
    """Convenience helper to load an ontology file."""
    return OntologyGraph.from_file(file_path, format=format)
