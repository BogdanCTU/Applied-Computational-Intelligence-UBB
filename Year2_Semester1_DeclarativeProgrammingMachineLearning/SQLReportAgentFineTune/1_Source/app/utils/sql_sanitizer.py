"""SQL sanitization, markdown extraction, and query normalization."""

import re
from typing import Optional
import sqlparse


def extract_sql_from_response(response: str) -> str:
    """Extracts raw SQL query from LLM generated text.
    
    Handles markdown code blocks (```sql ... ``` or ``` ... ```),
    preceding conversational phrases, and trailing commentary.
    """
    if not response:
        return ""

    text = response.strip()

    # Match ```sql ... ``` or ```SQL ... ```
    match = re.search(r"```(?:sql|SQL)?\s*([\s\S]*?)\s*```", text)
    if match:
        extracted = match.group(1).strip()
        return clean_sql_query(extracted)

    # If no markdown block found, look for SELECT / WITH statements
    match = re.search(r"\b(SELECT\b[\s\S]*?)(?:;|\Z)", text, re.IGNORECASE)
    if match:
        return clean_sql_query(match.group(1).strip())

    match_with = re.search(r"\b(WITH\b[\s\S]*?)(?:;|\Z)", text, re.IGNORECASE)
    if match_with:
        return clean_sql_query(match_with.group(1).strip())

    return clean_sql_query(text)


def clean_sql_query(query: str) -> str:
    """Strips comments, excess whitespace, and trailing semicolons."""
    if not query:
        return ""

    # Remove single-line comments (-- ...)
    lines = []
    for line in query.splitlines():
        line_clean = re.sub(r"--.*$", "", line)
        if line_clean.strip():
            lines.append(line_clean)
    cleaned = " ".join(lines)

    # Remove multi-line comments (/* ... */)
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove trailing semicolon
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    return cleaned


def normalize_sql(query: str) -> str:
    """Normalizes SQL syntax and keyword casing for structural comparison."""
    cleaned = clean_sql_query(query)
    if not cleaned:
        return ""
    try:
        formatted = sqlparse.format(
            cleaned,
            keyword_case="upper",
            identifier_case="lower",
            strip_comments=True,
            reindent=False,
        )
        return re.sub(r"\s+", " ", formatted).strip()
    except Exception:
        return cleaned


def is_valid_sql_syntax(query: str) -> bool:
    """Validates whether the string parses into a recognized SQL statement."""
    cleaned = clean_sql_query(query)
    if not cleaned:
        return False
    try:
        parsed = sqlparse.parse(cleaned)
        if not parsed:
            return False
        stmt = parsed[0]
        # Must start with SELECT or WITH
        first_token = None
        for tok in stmt.tokens:
            if not tok.is_whitespace:
                first_token = tok
                break
        if first_token and first_token.value.upper() in ("SELECT", "WITH"):
            return True
        return False
    except Exception:
        return False
