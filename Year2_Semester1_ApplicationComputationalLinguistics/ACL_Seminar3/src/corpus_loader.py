"""Corpus acquisition and management module for ACL Seminar 3.

Handles downloading, local caching, and deterministic loading of:
- Mary Shelley's Frankenstein (Project Gutenberg #84)
- Carlo Collodi's Le avventure di Pinocchio (Project Gutenberg #52484)
- Brown Corpus (NLTK American English sample)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CorpusMetadata:
    """Metadata describing a text corpus."""

    corpus_id: str
    title: str
    author: str
    language: str
    original_publication: str
    source: str
    source_url: str
    local_file: str
    target_tokens: Optional[int]
    is_gutenberg: bool
    access_date: str

    def to_dict(self) -> dict:
        """Convert metadata to dictionary representation."""
        return asdict(self)


# Default corpus configurations
DEFAULT_CORPORA: Dict[str, dict] = {
    "frankenstein": {
        "corpus_id": "frankenstein",
        "title": "Frankenstein; or, The Modern Prometheus",
        "author": "Mary Shelley",
        "language": "English",
        "original_publication": "1818",
        "source": "Project Gutenberg (eBook #84)",
        "source_url": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
        "fallback_url": "https://www.gutenberg.org/files/84/84-0.txt",
        "local_file": "frankenstein.txt",
        "target_tokens": 50000,
        "is_gutenberg": True,
    },
    "pinocchio": {
        "corpus_id": "pinocchio",
        "title": "Le avventure di Pinocchio",
        "author": "Carlo Collodi",
        "language": "Italian",
        "original_publication": "1883",
        "source": "Project Gutenberg (eBook #52484)",
        "source_url": "https://www.gutenberg.org/cache/epub/52484/pg52484.txt",
        "fallback_url": "https://www.gutenberg.org/files/52484/52484-0.txt",
        "local_file": "pinocchio.txt",
        "target_tokens": None,  # Full cleaned text (~40,000-50,000 tokens)
        "is_gutenberg": True,
    },
    "brown": {
        "corpus_id": "brown",
        "title": "Brown Corpus (American English Sample)",
        "author": "W. N. Francis and H. Kučera (Compilers)",
        "language": "American English",
        "original_publication": "1961 (compiled 1963-1964)",
        "source": "Brown University / NLTK",
        "source_url": "https://www.nltk.org/nltk_data/",
        "fallback_url": "",
        "local_file": "brown_sample.txt",
        "target_tokens": 50000,
        "is_gutenberg": False,
    },
}


def download_text_file(
    url: str,
    dest_path: Path,
    fallback_url: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Download plain text file from URL with caching and fallback support.

    Parameters
    ----------
    url : str
        Primary download URL.
    dest_path : Path
        Local file path where text will be saved.
    fallback_url : Optional[str]
        Alternative URL if primary fails.
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    str
        The downloaded or cached text content.

    Raises
    ------
    RuntimeError
        If download fails and file is not already present locally.
    """
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info("Using cached file: %s", dest_path)
        return dest_path.read_text(encoding="utf-8", errors="replace")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 (ZipfLawExperiment/1.0)"
        )
    }

    urls_to_try = [url]
    if fallback_url:
        urls_to_try.append(fallback_url)

    last_error: Optional[Exception] = None
    for target_url in urls_to_try:
        try:
            logger.info("Downloading corpus from %s ...", target_url)
            response = requests.get(target_url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Ensure proper text decoding
            text = response.text
            if not text.strip():
                raise ValueError("Downloaded file is empty.")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(text, encoding="utf-8")
            logger.info("Saved %d characters to %s", len(text), dest_path)
            return text

        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to download from %s: %s", target_url, exc)
            last_error = exc

    error_msg = (
        f"Unable to download corpus from {urls_to_try}.\n"
        f"Error details: {last_error}\n"
        f"Please manually download the plain text file and place it at:\n"
        f"  {dest_path.resolve()}"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg) from last_error


def load_brown_corpus_sample(
    dest_path: Path,
    target_raw_words: int = 65000,
) -> str:
    """Acquire and locally cache a deterministic sample of the Brown Corpus via NLTK.

    Parameters
    ----------
    dest_path : Path
        Local file path where the extracted sample will be saved.
    target_raw_words : int
        Approximate raw word threshold to extract from sequential files.

    Returns
    -------
    str
        The sampled Brown text.

    Raises
    ------
    RuntimeError
        If NLTK Brown corpus cannot be loaded.
    """
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info("Using cached Brown corpus sample: %s", dest_path)
        return dest_path.read_text(encoding="utf-8", errors="replace")

    import nltk

    try:
        logger.info("Ensuring NLTK Brown corpus is available...")
        nltk.download("brown", quiet=True)
        from nltk.corpus import brown

        fileids: List[str] = brown.fileids()
        if not fileids:
            raise ValueError("No files found in NLTK Brown corpus.")

        extracted_words: List[str] = []
        for fid in fileids:
            words = brown.words(fileids=fid)
            extracted_words.extend(words)
            if len(extracted_words) >= target_raw_words:
                break

        # Brown words are untagged; join with space to form prose for consistent preprocessing
        text = " ".join(extracted_words)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(text, encoding="utf-8")
        logger.info(
            "Extracted and cached Brown sample (%d raw tokens) to %s",
            len(extracted_words),
            dest_path,
        )
        return text

    except Exception as exc:  # noqa: BLE001
        error_msg = (
            "Failed to load Brown Corpus via NLTK.\n"
            f"Error details: {exc}\n"
            f"Please run `python -m nltk.downloader brown` or provide a text file at:\n"
            f"  {dest_path.resolve()}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from exc


def load_corpus(
    corpus_id: str,
    raw_dir: Path,
    force_download: bool = False,
) -> Tuple[str, CorpusMetadata]:
    """Load a specific corpus by identifier, downloading if necessary.

    Parameters
    ----------
    corpus_id : str
        Identifier ('frankenstein', 'pinocchio', or 'brown').
    raw_dir : Path
        Directory storing raw text files.
    force_download : bool
        If True, ignore cache and re-download.

    Returns
    -------
    Tuple[str, CorpusMetadata]
        Raw text content and corresponding CorpusMetadata.
    """
    if corpus_id not in DEFAULT_CORPORA:
        raise ValueError(
            f"Unknown corpus_id: '{corpus_id}'. Available: {list(DEFAULT_CORPORA.keys())}"
        )

    cfg = DEFAULT_CORPORA[corpus_id]
    dest_path = raw_dir / cfg["local_file"]

    if force_download and dest_path.exists():
        dest_path.unlink()

    now_iso = datetime.now(timezone.utc).isoformat()

    if corpus_id == "brown":
        text = load_brown_corpus_sample(dest_path=dest_path)
    else:
        text = download_text_file(
            url=cfg["source_url"],
            dest_path=dest_path,
            fallback_url=cfg.get("fallback_url"),
        )

    metadata = CorpusMetadata(
        corpus_id=cfg["corpus_id"],
        title=cfg["title"],
        author=cfg["author"],
        language=cfg["language"],
        original_publication=cfg["original_publication"],
        source=cfg["source"],
        source_url=cfg["source_url"],
        local_file=str(dest_path),
        target_tokens=cfg["target_tokens"],
        is_gutenberg=cfg["is_gutenberg"],
        access_date=now_iso,
    )

    return text, metadata


def load_all_corpora(
    raw_dir: Path,
    force_download: bool = False,
) -> Dict[str, Tuple[str, CorpusMetadata]]:
    """Load all required corpora for the experiment.

    Parameters
    ----------
    raw_dir : Path
        Directory storing raw text files.
    force_download : bool
        If True, re-download all corpora.

    Returns
    -------
    Dict[str, Tuple[str, CorpusMetadata]]
        Dictionary mapping corpus_id to (raw_text, metadata).
    """
    corpora: Dict[str, Tuple[str, CorpusMetadata]] = {}
    for corpus_id in DEFAULT_CORPORA:
        logger.info("Loading corpus: %s", corpus_id)
        raw_text, metadata = load_corpus(
            corpus_id=corpus_id,
            raw_dir=raw_dir,
            force_download=force_download,
        )
        corpora[corpus_id] = (raw_text, metadata)
    return corpora

