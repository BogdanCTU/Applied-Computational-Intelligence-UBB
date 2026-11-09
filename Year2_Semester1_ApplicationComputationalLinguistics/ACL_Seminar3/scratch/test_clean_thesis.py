import pypdf
import re
import unicodedata
from collections import Counter

def extract_and_clean_pdf(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    
    # Normalize LaTeX PDF diacritic quirks
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
    
    # Standardize unicode and quotes
    text = unicodedata.normalize('NFC', text)
    text = text.replace('’', "'").replace('‘', "'").lower()
    return text

text = extract_and_clean_pdf("data/pdf/Licenta_Todoran_UMF.pdf")
tokens = re.findall(r"[a-zà-öø-ÿăâîșț]+(?:'[a-zà-öø-ÿăâîșț]+)*", text)

print(f"Total tokens: {len(tokens):,}")
print(f"Unique types: {len(set(tokens)):,}")
print(f"TTR: {len(set(tokens)) / len(tokens):.4f}")

counts = Counter(tokens)
print("\nTop 30 words:")
for r, (w, c) in enumerate(counts.most_common(30), 1):
    print(f"  {r:2d}. {w:15} : {c:4d} ({c/len(tokens)*100:.2f}%)")

