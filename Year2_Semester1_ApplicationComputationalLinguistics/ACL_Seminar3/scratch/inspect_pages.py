import pypdf
from pathlib import Path

pdf_path = Path("data/pdf/Licenta_Todoran_UMF.pdf")
reader = pypdf.PdfReader(pdf_path)

for p_num in [10, 20, 30, 40]:
    txt = reader.pages[p_num].extract_text() or ""
    print(f"=== PAGE {p_num+1} ===")
    print(txt[:400])
    print("-" * 50)

