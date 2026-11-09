"""Persistent Memory Package for Local Report SQL Agent.

Provides Working, Episodic, and Semantic memory subsystems backed by
a standalone SQLite database (`data/agent_memory.db`).
"""

from .migrations import (
    CURRENT_SCHEMA_VERSION,
    MigrationError,
    UnsupportedSchemaVersionError,
    apply_migrations,
)
from .models import (
    SemanticFact,
    TaskArtifactRecord,
    TaskDecision,
    TaskHistoryItem,
    TaskToolCallRecord,
)
from .repository import SQLiteMemoryRepository

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "MigrationError",
    "SQLiteMemoryRepository",
    "SemanticFact",
    "TaskArtifactRecord",
    "TaskDecision",
    "TaskHistoryItem",
    "TaskToolCallRecord",
    "UnsupportedSchemaVersionError",
    "apply_migrations",
]

