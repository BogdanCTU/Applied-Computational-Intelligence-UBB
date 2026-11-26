"""Dataset construction, validation, deduplication, and provenance tracking."""

from bug_detector.collection.dataset_builder import DatasetBuilder
from bug_detector.collection.deduplicator import deduplicate_and_validate_records
from bug_detector.collection.github_bugfix_collector import GitHubBugFixCollector
from bug_detector.collection.hard_negative_collector import HardNegativeCollector
from bug_detector.collection.inferredbugs_ingestor import InferredBugsIngestor
from bug_detector.collection.models import (
    DatasetAuditReport,
    DatasetSampleRecord,
    ExclusionRecord,
)

__all__ = [
    "DatasetAuditReport",
    "DatasetBuilder",
    "DatasetSampleRecord",
    "ExclusionRecord",
    "GitHubBugFixCollector",
    "HardNegativeCollector",
    "InferredBugsIngestor",
    "deduplicate_and_validate_records",
]
