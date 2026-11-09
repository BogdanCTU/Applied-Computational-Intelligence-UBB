"""Text preprocessing module for ACL Seminar 3.

Implements a unified, reproducible text normalization and tokenization pipeline:
1. Stripping Project Gutenberg header/footer boilerplate.
2. Unicode normalization (NFC).
3. Standardizing curly apostrophes/quotes to ASCII single quote.
4. Lowercasing.
5. Word tokenization preserving internal apostrophes and accented Latin characters
   (e.g., Italian à, è, é, ì, ò, ù).
6. Stripping punctuation and numeric digits.
7. Preserving stopwords without stemming or lemmatization.
8. Deterministic slice sampling to target size.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard Project Gutenberg boilerplate regex patterns
GUTENBERG_START_REGEX = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*",
    re.IGNORECASE,
)
GUTENBERG_END_REGEX = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*|"
    r"End of (?:the )?Project Gutenberg['\u2019]s[^\n]*",
    re.IGNORECASE,
)

# Unified word tokenization pattern:
# Matches sequences of lowercase alphabetic characters including Latin-1 accented vowels,
# with optional internal apostrophe(s) followed by letters.
# Punctuation, standalone quotes, and numbers are excluded.
TOKEN_REGEX = re.compile(r"[a-zà-öø-ÿ]+(?:'[a-zà-öø-ÿ]+)*")


@dataclass(frozen=True)
class PreprocessingSummary:
    """Summary statistics for text preprocessing."""

    raw_char_count: int
    cleaned_char_count: int
    total_tokens_extracted: int
    sampled_tokens_count: int
    is_sampled: bool


def remove_gutenberg_boilerplate(text: str) -> str:
    """Strip Project Gutenberg header and footer from the text.

    Parameters
    ----------
    text : str
        Raw Gutenberg text including headers and license footers.

    Returns
    -------
    str
        Cleaned text content between start and end markers.
    """
    start_match = GUTENBERG_START_REGEX.search(text)
    end_match = GUTENBERG_END_REGEX.search(text)

    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)

    if start_match and end_match and end_idx < start_idx:
        # Fallback if markers match out of expected order
        end_idx = len(text)

    cleaned = text[start_idx:end_idx].strip()
    logger.debug(
        "Gutenberg boilerplate removed: %d chars -> %d chars",
        len(text),
        len(cleaned),
    )
    return cleaned


def normalize_unicode(text: str) -> str:
    """Normalize text to Unicode NFC form.

    Parameters
    ----------
    text : str
        Input string.

    Returns
    -------
    str
        NFC normalized string.
    """
    return unicodedata.normalize("NFC", text)


def normalize_apostrophes(text: str) -> str:
    """Standardize typographically varied single quotation marks to ASCII single quote.

    Converts right single quote (\u2019) and left single quote (\u2018) to ASCII (').
    This ensures internal contractions (e.g. don't, l'ombra) are uniformly parsed.

    Parameters
    ----------
    text : str
        Input string.

    Returns
    -------
    str
        String with standardized apostrophes.
    """
    return text.replace("\u2019", "'").replace("\u2018", "'")


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words adhering to the assignment requirements.

    Decisions:
    - Unicode NFC normalization is applied first.
    - Smart curly apostrophes are mapped to ASCII single quote.
    - Text is lowercased.
    - Words with internal apostrophes (e.g. 'it\'s', 'don\'t', 'l\'ombra', 'c\'era')
      are kept intact as single lexical units.
    - External punctuation, surrounding quotation marks, numbers, and symbols are excluded.
    - Stopwords are intentionally preserved.
    - No stemming, lemmatization, or cross-language translation is performed.

    Parameters
    ----------
    text : str
        Raw or pre-cleaned text string.

    Returns
    -------
    List[str]
        List of lowercase word tokens.
    """
    if not text:
        return []

    norm_text = normalize_unicode(text)
    norm_text = normalize_apostrophes(norm_text)
    norm_text = norm_text.lower()

    tokens = TOKEN_REGEX.findall(norm_text)
    return tokens


def sample_tokens(
    tokens: List[str],
    target_size: Optional[int],
) -> Tuple[List[str], bool]:
    """Deterministically slice the token list to target_size if requested.

    Parameters
    ----------
    tokens : List[str]
        Full tokenized text.
    target_size : Optional[int]
        Desired number of tokens. If None or target_size >= len(tokens), returns all.

    Returns
    -------
    Tuple[List[str], bool]
        Sampled tokens and a boolean indicating whether truncation occurred.
    """
    if target_size is not None and len(tokens) >= target_size:
        return tokens[:target_size], True
    return tokens, False


def preprocess_corpus(
    raw_text: str,
    is_gutenberg: bool = False,
    target_tokens: Optional[int] = None,
) -> Tuple[List[str], PreprocessingSummary]:
    """Run the complete end-to-end preprocessing pipeline for a corpus.

    Parameters
    ----------
    raw_text : str
        The raw text from disk.
    is_gutenberg : bool
        Whether to strip Project Gutenberg headers/footers.
    target_tokens : Optional[int]
        Target size in tokens (50,000 for Frankenstein and Brown; None for Pinocchio).

    Returns
    -------
    Tuple[List[str], PreprocessingSummary]
        The final token list and the preprocessing metadata summary.
    """
    raw_len = len(raw_text)

    cleaned_text = (
        remove_gutenberg_boilerplate(raw_text) if is_gutenberg else raw_text
    )
    cleaned_len = len(cleaned_text)

    all_tokens = tokenize(cleaned_text)
    total_tokens_count = len(all_tokens)

    final_tokens, is_sampled = sample_tokens(all_tokens, target_size=target_tokens)

    summary = PreprocessingSummary(
        raw_char_count=raw_len,
        cleaned_char_count=cleaned_len,
        total_tokens_extracted=total_tokens_count,
        sampled_tokens_count=len(final_tokens),
        is_sampled=is_sampled,
    )

    logger.info(
        "Preprocessed: %d chars -> %d tokens (sampled: %d tokens, target: %s)",
        raw_len,
        total_tokens_count,
        len(final_tokens),
        str(target_tokens),
    )

    return final_tokens, summary

