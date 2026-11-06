import pypdf
import re
import unicodedata
from collections import Counter

reader = pypdf.PdfReader("data/pdf/Licenta_Todoran_UMF.pdf")
full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

# Check total characters
print("Extracted chars:", len(full_text))

# Let's inspect Romanian LaTeX artifacts
# E.g.: "s, i" -> "și", "t, i" -> "ți", "˘ a" -> "ă", "ˆ ın" -> "în"
def clean_pdf_text(text: str) -> str:
    # Handle LaTeX PDF diacritic extraction quirks
    text = re.sub(r's,\s*', 'ș', text)
    text = re.sub(r'S,\s*', 'Ș', text)
    text = re.sub(r't,\s*', 'ț', text)
    text = re.sub(r'T,\s*', 'Ț', text)
    text = re.sub(r'˘\s*a', 'ă', text)
    text = re.sub(r'˘\s*A', 'Ă', text)
    text = re.sub(r'ˆ\s*ı', 'î', text)
    text = re.sub(r'ˆ\s*i', 'î', text)
    text = re.sub(r'ˆ\s*a', 'â', text)
    text = re.sub(r'ˆ\s*I', 'Î', text)
    text = re.sub(r'ˆ\s*A', 'Â', text)
    
    # Normalize unicode NFC
    text = unicodedata.normalize('NFC', text)
    text = text.replace('’', "'").replace('‘', "'").lower()
    return text

cleaned = clean_pdf_text(full_text)
print("\nSample cleaned text around Page 11:")
idx = cleaned.find("aspecte teoretice")
print(cleaned[idx:idx+400])

# Tokenize using Latin pattern that supports Romanian diacritics: ă, â, î, ș, ț, etc.
# In Latin range, [a-zà-öø-ÿșțăîâ]
tokens = re.findall(r"[a-zà-öø-ÿșțăîâ]+(?:'[a-zà-öø-ÿșțăîâ]+)*", cleaned)
print(f"\nTotal tokens: {len(tokens):,}, Unique types: {len(set(tokens)):,}")
c = Counter(tokens)
print("Top 25 tokens:", c.most_common(25))

