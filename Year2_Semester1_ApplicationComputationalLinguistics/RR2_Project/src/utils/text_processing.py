"""Text normalization and preprocessing utilities reproducing Agent-OM conventions."""

from __future__ import annotations

import re
from typing import Union
from breame.spelling import get_american_spelling
from rdflib import URIRef


def uri_to_name(uri: Union[str, URIRef]) -> str:
    """
    Extract the local name of an entity URI.
    Matches util.uri_to_name in original Agent-OM.
    """
    uri_str = str(uri)
    if "#" in uri_str:
        return uri_str.rsplit("#", maxsplit=1)[-1]
    return uri_str.rsplit("/", maxsplit=1)[-1]


def uri_to_prefix_name(uri: Union[str, URIRef], prefix: str) -> str:
    """Format an entity URI with prefix (e.g. source:Author)."""
    return f"{prefix}:{uri_to_name(uri)}"


def repair_acronyms(name: str) -> str:
    """
    Reconstruct acronyms from split single-character words.
    Reproduces util.repair_acronyms from original Agent-OM.
    Example: 'site U R L' -> 'site URL'
    """
    words = name.split(" ")
    result = []
    temp = ""
    for word in words:
        if len(word) == 1:
            temp += word
        else:
            if temp:
                result.append(temp)
                temp = ""
            result.append(word)
    if temp:
        result.append(temp)
    return " ".join(result)


def change_to_snake_case(name: str) -> str:
    """
    Convert CamelCase or PascalCase to space-separated words, repairing acronyms.
    Reproduces util.change_to_snake_case from original Agent-OM.
    """
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    name = pattern.sub(" ", name)
    name = repair_acronyms(name)
    return name


def change_british_to_american(word: str) -> str:
    """Convert British spelling to American spelling via breame."""
    return get_american_spelling(word)


def change_phrase_british_to_american(phrase: str) -> str:
    """Convert all British spelling words in a phrase to American spelling."""
    return " ".join(get_american_spelling(word) for word in phrase.split())


def cleaning(name: str) -> str:
    """
    Reproduces util.cleaning from original Agent-OM exactly:
    1. Replace all non-alphanumeric characters with spaces: re.sub(r'[^A-Za-z0-9]+', ' ', str(name))
    2. If no spaces present (i.e. was a single word / camelCase):
       - Convert CamelCase via change_to_snake_case()
    3. Lowercase.
    4. Convert British spelling to American spelling via breame.
    5. Strip whitespace.
    6. Return cleaned_name if non-empty, otherwise original name.
    """
    cleaned_name = re.sub(r"[^A-Za-z0-9]+", " ", str(name))
    if " " not in cleaned_name:
        cleaned_name = change_to_snake_case(cleaned_name)
    cleaned_name = cleaned_name.lower()
    cleaned_name = change_phrase_british_to_american(cleaned_name)
    cleaned_name = cleaned_name.strip()
    if cleaned_name:
        return cleaned_name
    return str(name)

