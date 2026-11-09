import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.section import WD_ORIENTATION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = docx.Document()
section = doc.sections[0]
section.orientation = WD_ORIENTATION.LANDSCAPE
# Swap width and height for landscape
new_width, new_height = section.page_height, section.page_width
section.page_width = new_width
section.page_height = new_height
section.left_margin = Inches(0.5)
section.right_margin = Inches(0.5)
section.top_margin = Inches(0.5)
section.bottom_margin = Inches(0.5)

p = doc.add_paragraph("ACL Seminar 3 – Results Table")
table = doc.add_table(rows=2, cols=7)
table.alignment = WD_TABLE_ALIGNMENT.CENTER

headers = [
    "#", "Student", "Corpus source /\nCorpus dimension",
    "Zipf graph\n(top 200 words)", "Most frequent\n7 words",
    "Percentage of tokens\ncovered by top 7 words",
    "Percentage of words\nappearing once"
]
for col_idx, h in enumerate(headers):
    cell = table.cell(0, col_idx)
    cell.text = h

doc.save("scratch/test_table.docx")
print("Saved scratch/test_table.docx successfully!")

