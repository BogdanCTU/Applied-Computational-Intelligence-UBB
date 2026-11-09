import pypdf
import re

reader = pypdf.PdfReader("data/pdf/Licenta_Todoran_UMF.pdf")
full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

# Find samples with combining or floating accents
print("Breve samples:")
for m in re.finditer(r'(\w{0,4}\s*˘\s*\w{0,4})', full_text):
    print("  ", repr(m.group(1)))
    if m.start() > 3000:
        break

print("\nCircumflex samples:")
for m in re.finditer(r'(\w{0,4}\s*ˆ\s*\w{0,4})', full_text):
    print("  ", repr(m.group(1)))
    if m.start() > 3000:
        break

