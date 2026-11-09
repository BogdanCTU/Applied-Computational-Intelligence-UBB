"""Unit tests for text preprocessing and tokenization."""

from __future__ import annotations

import unicodedata
import pytest

from src.text_preprocessor import (
    normalize_apostrophes,
    normalize_unicode,
    preprocess_corpus,
    remove_gutenberg_boilerplate,
    sample_tokens,
    tokenize,
)


def test_unicode_normalization_nfc():
    """Verify that decomposed Unicode (NFD) is normalized to NFC."""
    # 'e' + combining acute accent (U+0301)
    decomposed = "e\u0301"
    composed = "é"
    assert decomposed != composed
    norm = normalize_unicode(decomposed)
    assert norm == composed
    assert unicodedata.is_normalized("NFC", norm)


def test_italian_accented_characters_preserved():
    """Verify that all standard Italian accented vowels are preserved in lowercase."""
    text = "Caffè, città, virtù, perché, così, però, À, È, É, Ì, Ò, Ù."
    tokens = tokenize(text)
    expected = ["caffè", "città", "virtù", "perché", "così", "però", "à", "è", "é", "ì", "ò", "ù"]
    assert tokens == expected


def test_apostrophes_within_words_preserved():
    """Verify internal apostrophes are retained in contractions and elisions."""
    # English contractions
    en_text = "It's don't couldn't Mary's o'clock"
    en_tokens = tokenize(en_text)
    assert en_tokens == ["it's", "don't", "couldn't", "mary's", "o'clock"]

    # Italian elisions and contractions with both straight and typographic curly quotes
    it_text = "L’ombra, c'era, d’oro, un'altra, tutt’e, bell’e, sant'antonio"
    it_tokens = tokenize(it_text)
    assert it_tokens == ["l'ombra", "c'era", "d'oro", "un'altra", "tutt'e", "bell'e", "sant'antonio"]


def test_external_punctuation_and_quotes_removed():
    """Verify that quotes and punctuation around words are stripped."""
    text = "“Hello!” he said, ‘Goodbye.’ (Wait: what?!)"
    tokens = tokenize(text)
    assert tokens == ["hello", "he", "said", "goodbye", "wait", "what"]

    # Trailing apostrophe on plurals
    possessive_plural = "the boys' dog"
    assert tokenize(possessive_plural) == ["the", "boys", "dog"]


def test_numbers_removed():
    """Verify numbers and digits are stripped."""
    text = "Chapter 1 in 1818 with 50,000 words and 300 dpi."
    tokens = tokenize(text)
    assert tokens == ["chapter", "in", "with", "words", "and", "dpi"]


def test_stopwords_preserved():
    """Verify stopwords are intentionally not removed."""
    text = "to be or not to be that is the question"
    tokens = tokenize(text)
    assert tokens == ["to", "be", "or", "not", "to", "be", "that", "is", "the", "question"]


def test_no_stemming_or_lemmatization():
    """Verify inflectional forms are maintained as distinct tokens."""
    en_text = "walk walks walked walking"
    assert tokenize(en_text) == ["walk", "walks", "walked", "walking"]

    it_text = "parlo parli parla parliamo parlate parlano"
    assert tokenize(it_text) == ["parlo", "parli", "parla", "parliamo", "parlate", "parlano"]


def test_gutenberg_boilerplate_removal():
    """Verify removal of Project Gutenberg header and footer."""
    raw = (
        "The Project Gutenberg eBook of Frankenstein\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK FRANKENSTEIN ***\n"
        "Letter 1\n"
        "To Mrs. Saville, England.\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK FRANKENSTEIN ***\n"
        "End of Project Gutenberg's Frankenstein\n"
    )
    cleaned = remove_gutenberg_boilerplate(raw)
    assert "The Project Gutenberg eBook" not in cleaned
    assert "START OF THE PROJECT" not in cleaned
    assert "END OF THE PROJECT" not in cleaned
    assert cleaned.strip() == "Letter 1\nTo Mrs. Saville, England."


def test_deterministic_sampling():
    """Verify deterministic token slicing."""
    tokens = [f"word_{i}" for i in range(100)]
    sampled, is_sampled = sample_tokens(tokens, target_size=50)
    assert is_sampled is True
    assert len(sampled) == 50
    assert sampled == tokens[:50]

    # No sampling when target_size is None or larger than len(tokens)
    unsampled, is_sampled2 = sample_tokens(tokens, target_size=None)
    assert is_sampled2 is False
    assert len(unsampled) == 100

