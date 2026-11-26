"""Source normalization helpers and deterministic token hashing utilities."""

from __future__ import annotations

import hashlib
import re

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?|==|!=|<=|>=|&&|\|\||\?\?|\?\.|=>|\S")


def normalize_whitespace_hash(source: str) -> str:
    """Compute a deterministic SHA-256 hash after collapsing runs of whitespace."""
    collapsed = _WS_RE.sub(" ", source.strip())
    return hashlib.sha256(collapsed.encode("utf-8", errors="replace")).hexdigest()


def python_fallback_tokenize(source: str) -> list[str]:
    """Lightweight fallback tokenizer used only for text similarity / quick pre-checks."""
    return _TOKEN_RE.findall(source)


def token_jaccard_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Compute Jaccard similarity between two token multisets (unique set overlap)."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
