"""Preprocessing module for Seminar 4 IR System (Part 1).

Handles:
- CACM collection parsing and document extraction (.I, .T, .W, etc.)
- Lowercasing and alphabetic tokenization
- Token counting before and after stop-word removal
- Determination of the 7 most frequent words across the corpus
- Stop-word filtering without stemming or lemmatization
- Query validation and preprocessing
"""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union


@dataclass
class Document:
    """Represents an extracted document from the CACM corpus."""
    doc_id: str          # Formatted identifier, e.g. "CACM-001"
    doc_num: int         # Numeric identifier, e.g. 1
    title: str           # Document title (.T section)
    abstract: str        # Document abstract (.W section)

    @property
    def searchable_text(self) -> str:
        """Returns the combined title and abstract used for indexing."""
        parts = []
        if self.title:
            parts.append(self.title.strip())
        if self.abstract:
            parts.append(self.abstract.strip())
        return " ".join(parts).strip()


def format_doc_id(doc_num: int, prefix: str = "CACM-", min_width: int = 3) -> str:
    """Format document number into canonical string identifier.
    
    Examples:
        1 -> "CACM-001"
        15 -> "CACM-015"
        1410 -> "CACM-1410"
    """
    return f"{prefix}{doc_num:0{min_width}d}"


def parse_doc_id(doc_id_str: str) -> int:
    """Extract integer document number from identifier string (e.g. 'CACM-001' -> 1)."""
    m = re.search(r"(\d+)", doc_id_str)
    if not m:
        raise ValueError(f"Cannot parse document number from: {doc_id_str}")
    return int(m.group(1))


def load_cacm_collection(file_path: Union[str, Path]) -> List[Document]:
    """Parse original CACM document collection (.all file).
    
    Extracts document identifiers (.I), titles (.T), and abstracts (.W).
    Gracefully handles malformed or incomplete records.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"CACM dataset file not found at: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Split records by line beginning with .I followed by whitespace
    raw_records = re.split(r"\n(?=\.I\s+)", content)
    documents: List[Document] = []

    for raw in raw_records:
        cleaned_raw = raw.strip()
        if not cleaned_raw.startswith(".I"):
            continue

        lines = cleaned_raw.split("\n")
        first_line = lines[0].strip()
        id_match = re.match(r"^\.I\s+(\d+)", first_line)
        if not id_match:
            continue

        doc_num = int(id_match.group(1))
        doc_id = format_doc_id(doc_num)

        title_lines: List[str] = []
        abstract_lines: List[str] = []
        current_section: Optional[str] = None

        for line in lines[1:]:
            stripped = line.strip()
            # Section headers in CACM start with a dot followed by a single character
            if line.startswith(".") and len(stripped) == 2 and stripped[1] in "TWANXB":
                current_section = stripped
                continue

            if current_section == ".T":
                title_lines.append(line)
            elif current_section == ".W":
                abstract_lines.append(line)

        title = " ".join(l.strip() for l in title_lines if l.strip()).strip()
        abstract = " ".join(l.strip() for l in abstract_lines if l.strip()).strip()

        documents.append(
            Document(
                doc_id=doc_id,
                doc_num=doc_num,
                title=title,
                abstract=abstract,
            )
        )

    return documents


def extract_alphabetic_tokens(text: str) -> List[str]:
    """Extract lowercase alphabetic tokens from raw text.
    
    1. Convert text to lowercase.
    2. Extract sequences of alphabetic characters ([a-z]+).
    """
    if not text:
        return []
    return re.findall(r"[a-z]+", text.lower())


def compute_corpus_stop_words(
    documents: List[Document],
    num_stop_words: int = 7
) -> Tuple[List[str], Dict[str, int], int]:
    """Calculate the N most frequent words across all document titles and abstracts.
    
    Returns:
        stop_words: List of the top N words in descending order of frequency.
        frequencies: Dictionary mapping each stop word to its corpus occurrence count.
        total_tokens_before: Total number of tokens before stop-word removal.
    """
    from collections import Counter

    token_counter: Counter[str] = Counter()
    total_tokens_before = 0

    for doc in documents:
        tokens = extract_alphabetic_tokens(doc.searchable_text)
        total_tokens_before += len(tokens)
        token_counter.update(tokens)

    most_common = token_counter.most_common(num_stop_words)
    stop_words = [w for w, _ in most_common]
    frequencies = {w: count for w, count in most_common}

    return stop_words, frequencies, total_tokens_before


class Preprocessor:
    """Deterministic text preprocessor implementing the Seminar 4 pipeline:
    1. Lowercase conversion
    2. Alphabetic token extraction
    3. Stop-word removal (using top 7 corpus words)
    4. No stemming or lemmatization
    """

    def __init__(self, stop_words: Optional[Iterable[str]] = None) -> None:
        self.stop_words: Set[str] = set(w.lower() for w in stop_words) if stop_words else set()

    def tokenize(self, text: str) -> List[str]:
        """Convert text to lowercase and extract alphabetic tokens."""
        return extract_alphabetic_tokens(text)

    def preprocess_text(self, text: str) -> List[str]:
        """Tokenize and remove stop words (without stemming or lemmatization)."""
        tokens = self.tokenize(text)
        if not self.stop_words:
            return tokens
        return [t for t in tokens if t not in self.stop_words]

    def preprocess_query(self, query: str) -> str:
        """Validate and preprocess a single-word query.
        
        Rules:
        - Must be non-empty.
        - Must extract valid alphabetic tokens.
        - Cannot consist solely of stop words.
        - Cannot contain multiple searchable terms.
        
        Returns:
            The single normalized query term.
        Raises:
            ValueError: If query is empty, multiple words, or a stop word.
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty or whitespace only.")

        raw_tokens = self.tokenize(query)
        if not raw_tokens:
            raise ValueError(f"Query '{query}' contains no alphabetic tokens.")

        # Filter stop words
        searchable_tokens = [t for t in raw_tokens if t not in self.stop_words]

        if not searchable_tokens:
            raise ValueError(
                f"Query '{query}' consists only of stop word(s): {', '.join(raw_tokens)}. "
                "Searchable term must not be a stop word."
            )

        if len(searchable_tokens) > 1:
            raise ValueError(
                f"Only single-word queries are supported. Found {len(searchable_tokens)} "
                f"searchable terms: {searchable_tokens}"
            )

        return searchable_tokens[0]


def save_processed_documents(documents: List[Document], file_path: Union[str, Path]) -> None:
    """Save processed documents to JSON for reproducibility."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(d) for d in documents]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_processed_documents(file_path: Union[str, Path]) -> List[Document]:
    """Load previously saved processed documents from JSON."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Document(**item) for item in data]


def save_stop_words(
    stop_words: List[str],
    frequencies: Dict[str, int],
    file_path: Union[str, Path]
) -> None:
    """Save stop words and their corpus frequencies to JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(stop_words),
        "stop_words": stop_words,
        "frequencies": frequencies,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_stop_words(file_path: Union[str, Path]) -> Tuple[List[str], Dict[str, int]]:
    """Load stop words and frequencies from JSON."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["stop_words"], data["frequencies"]
