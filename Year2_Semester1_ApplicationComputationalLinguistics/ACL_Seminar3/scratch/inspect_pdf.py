import pypdf
from pathlib import Path

pdf_path = Path("data/pdf/Licenta_Todoran_UMF.pdf")
reader = pypdf.PdfReader(pdf_path)
num_pages = len(reader.pages)
print(f"Number of pages: {num_pages}")

extracted_text = []
for i, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    extracted_text.append(txt)

full_text = "\n".join(extracted_text)
print(f"Total extracted chars: {len(full_text):,}")
print("First 500 chars:\n", full_text[:500])
print("\nPage 5 sample:\n", extracted_text[4][:500] if num_pages > 4 else "")

