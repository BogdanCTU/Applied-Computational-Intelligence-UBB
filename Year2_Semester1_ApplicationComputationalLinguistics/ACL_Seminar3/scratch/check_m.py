import pypdf
import re

reader = pypdf.PdfReader("data/pdf/Licenta_Todoran_UMF.pdf")
full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

# Find occurrences of standalone m
matches = re.findall(r'\b[0-9]+(?:\.[0-9]+)?\s*m\b', full_text, re.IGNORECASE)
print(f"Occurrences of numbers + m: {len(matches)}")
print("Sample matches:", matches[:10])

# Also check "m˘ asur"
matches_masur = re.findall(r'm\s*˘\s*a', full_text)
print(f"Occurrences of m + breve + a: {len(matches_masur)}")

