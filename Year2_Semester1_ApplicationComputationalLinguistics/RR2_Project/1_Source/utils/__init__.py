"""Utility functions for Agent-OM Local reproduction."""

from .text_processing import (
    uri_to_name,
    uri_to_prefix_name,
    repair_acronyms,
    change_to_snake_case,
    change_british_to_american,
    change_phrase_british_to_american,
    cleaning,
)

__all__ = [
    "uri_to_name",
    "uri_to_prefix_name",
    "repair_acronyms",
    "change_to_snake_case",
    "change_british_to_american",
    "change_phrase_british_to_american",
    "cleaning",
]

