from collections import Counter
import numpy as np
from scipy import stats
import pypdf, re, unicodedata

def extract_and_clean_pdf(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
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
    text = unicodedata.normalize('NFC', text)
    text = text.replace('’', "'").replace('‘', "'").lower()
    return text

text = extract_and_clean_pdf("data/pdf/Licenta_Todoran_UMF.pdf")
tokens = re.findall(r"[a-zà-öø-ÿăâîșț]+(?:'[a-zà-öø-ÿăâîșț]+)*", text)
counts = Counter(tokens)
sorted_counts = sorted(counts.values(), reverse=True)

ranks = np.arange(1, len(sorted_counts) + 1)
log_r = np.log10(ranks)
log_f = np.log10(sorted_counts)

reg = stats.linregress(log_r, log_f)
print(f"Full fit: slope={reg.slope:.4f}, s={abs(reg.slope):.4f}, R²={reg.rvalue**2:.4f}, r={reg.rvalue:.4f}")

reg100 = stats.linregress(log_r[:100], log_f[:100])
print(f"Top 100 fit: slope={reg100.slope:.4f}, s={abs(reg100.slope):.4f}, R²={reg100.rvalue**2:.4f}")

