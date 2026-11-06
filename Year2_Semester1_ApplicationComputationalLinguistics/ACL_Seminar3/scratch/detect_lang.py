import pypdf
import re

reader = pypdf.PdfReader("data/raw/Licenta_Todoran_UMF.pdf")
full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

# Check language by stopwords
words = re.findall(r'[a-zà-öø-ÿăâîșț]+', full_text.lower())
ro_stops = {'de', 'în', 'și', 'la', 'cu', 'pentru', 'care', 'este', 'un', 'o', 'să', 'pe', 'din', 'prin'}
en_stops = {'the', 'of', 'and', 'to', 'in', 'is', 'that', 'for', 'it', 'as', 'was', 'with', 'be', 'by'}

ro_count = sum(1 for w in words if w in ro_stops)
en_count = sum(1 for w in words if w in en_stops)

print(f"Total words: {len(words)}")
print(f"Romanian stopwords count: {ro_count}")
print(f"English stopwords count: {en_count}")
if ro_count > en_count:
    print("Detected Language: Romanian (Subject to verification: Primarily Romanian text with English technical terms & abstract)")
else:
    print("Detected Language: English")

