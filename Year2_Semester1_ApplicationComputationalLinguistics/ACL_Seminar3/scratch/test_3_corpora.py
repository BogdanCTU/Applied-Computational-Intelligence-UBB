import re
import unicodedata
from collections import Counter
from pathlib import Path

def remove_gutenberg_boilerplate(text: str) -> str:
    start_match = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", text, re.IGNORECASE)
    end_match = re.search(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*|End of (?:the )?Project Gutenberg", text, re.IGNORECASE)
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    return text[start_idx:end_idx]

def clean_and_tokenize(text: str, is_gutenberg: bool = False, is_thesis: bool = False) -> list[str]:
    if is_gutenberg:
        text = remove_gutenberg_boilerplate(text)
    if is_thesis:
        text = re.sub(r'˘\s*a', 'ă', text)
        text = re.sub(r'˘\s*A', 'Ă', text)
        text = re.sub(r'ˆ\s*ı', 'î', text)
        text = re.sub(r'ˆ\s*i', 'î', text)
        text = re.sub(r'ˆ\s*I', 'Î', text)
        text = re.sub(r'ˆ\s*a', 'â', text)
        text = re.sub(r'ˆ\s*A', 'Â', text)
        text = re.sub(r's,\s*', 'ș', text)
        text = re.sub(r'S,\s*', 'Ș', text)
        text = re.sub(r't,\s*', 'ț', text)
        text = re.sub(r'T,\s*', 'Ț', text)
    
    text = unicodedata.normalize("NFC", text)
    text = text.replace("’", "'").replace("‘", "'").lower()
    token_regex = re.compile(r"[a-zà-öø-ÿăâîșț]+(?:'[a-zà-öø-ÿăâîșț]+)*")
    return token_regex.findall(text)

files = {
    'Corpus 1 - Frankenstein (EN)': ('data/raw/frankenstein.txt', True, False),
    'Corpus 2 - Pinocchio (IT)': ('data/raw/pinocchio.txt', True, False),
    'Corpus 3 - Bachelor Thesis (RO)': ('data/raw/licenta_todoran.txt', False, True)
}

for name, (path, is_gut, is_thes) in files.items():
    raw = Path(path).read_text(encoding='utf-8', errors='replace')
    tokens = clean_and_tokenize(raw, is_gutenberg=is_gut, is_thesis=is_thes)
    counts = Counter(tokens)
    types = len(counts)
    top7 = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:7]
    top7_sum = sum(f for _, f in top7)
    cov7 = (top7_sum / len(tokens) * 100) if tokens else 0
    hapax = sum(1 for _, f in counts.items() if f == 1)
    hapax_tok_pct = (hapax / len(tokens) * 100) if tokens else 0
    hapax_type_pct = (hapax / types * 100) if types else 0
    print(f"=== {name} ===")
    print(f"Tokens: {len(tokens):,}, Types: {types:,}")
    print("Top 7:", ", ".join(f'("{w}":{f})' for w, f in top7))
    print(f"Top 7 Coverage: {cov7:.2f}%")
    print(f"Hapax: {hapax:,}, {hapax_tok_pct:.2f}% of the tokens, {hapax_type_pct:.2f}% of the types\n")
