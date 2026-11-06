from collections import Counter
import pypdf, re, unicodedata

def clean_pdf(pdf_path):
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

text = clean_pdf("data/raw/Licenta_Todoran_UMF.pdf")
tokens = re.findall(r"[a-zà-öø-ÿăâîșț]+(?:'[a-zà-öø-ÿăâîșț]+)*", text)
counts = Counter(tokens)
total_tokens = len(tokens)
total_types = len(counts)

sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
top7 = sorted_items[:7]
top7_sum = sum(f for w, f in top7)
top7_cov = (top7_sum / total_tokens) * 100

hapax_types = sum(1 for w, f in counts.items() if f == 1)
hapax_tokens = hapax_types
hapax_pct_tokens = (hapax_tokens / total_tokens) * 100
hapax_pct_types = (hapax_types / total_types) * 100

print(f"Total tokens: {total_tokens}")
print(f"Total types: {total_types}")
print(f"Top 7: {top7}")
print(f"Top 7 sum: {top7_sum}")
print(f"Top 7 coverage: {top7_cov:.2f}%")
print(f"Hapax types: {hapax_types}")
print(f"Hapax % of tokens: {hapax_pct_tokens:.2f}%")
print(f"Hapax % of types: {hapax_pct_types:.2f}%")

