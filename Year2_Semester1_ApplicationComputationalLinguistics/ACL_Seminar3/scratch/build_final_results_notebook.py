"""Builds and executes notebooks/ACL_Seminar_3_Zipf_Analysis_Final.ipynb and notebooks/ACL_Seminar_3_Final_Results.ipynb.
"""

from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

nb = nbf.v4.new_notebook()
cells = []

# ==============================================================================
# Cell 1: Overview & Professor Requirements (Markdown)
# ==============================================================================
c1_md = """# ACL Seminar 3: Final Zipf Results & Seminar Table Generator
**Course:** Applied Computational Linguistics (ACL) – Seminar 3  
**Student:** Todoran Ciprian Bogdan  
**Objective:** Compute exact empirical corpus metrics and generate the professor's required results table, 300 DPI Zipf frequency curves, and DOCX seminar submission table.

---

### Professor's Required Results Table Structure
| # | Student | Corpus source / Corpus dimension | Zipf graph (top 200 words) | Most frequent 7 words | Percentage of tokens covered by top 7 words | Percentage of words appearing once |
|---|---|---|---|---|---|---|

* **Language A (Romanian):** Configurable text corpus (e.g. *Baltagul* by Mihail Sadoveanu). If not locally available in `data/raw/`, clearly marked as **PENDING**.
* **Language B (English / Thesis):** Bachelor's Degree Thesis PDF (`Licenta_Todoran_UMF.pdf`), automatically extracted, preprocessed, and analyzed.
* **Core Calculations:** Total tokens, unique types, absolute frequency top 200 line graph, top 7 words formatted as `("word":freq)`, top 7 token coverage %, and hapax legomena count (% of tokens and % of types)."""
cells.append(nbf.v4.new_markdown_cell(c1_md))

# ==============================================================================
# Cell 2: Setup & Environment (Code)
# ==============================================================================
c2_code = """import os, sys, re, json, unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import pypdf
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.section import WD_ORIENTATION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from IPython.display import display, HTML, Markdown

%matplotlib inline
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 300, "font.size": 10})

# Base paths
BASE_DIR = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PDF = BASE_DIR / "data" / "pdf"
RESULTS_FINAL = BASE_DIR / "results" / "final_results"
RESULTS_FINAL_GRAPHS = RESULTS_FINAL / "graphs"

for p in [DATA_RAW, DATA_PDF, RESULTS_FINAL, RESULTS_FINAL_GRAPHS]:
    p.mkdir(parents=True, exist_ok=True)

# Configuration variables
STUDENT_NAME = "Todoran Ciprian Bogdan"
ROMANIAN_CORPUS_FILE = DATA_RAW / "baltagul.txt"
ROMANIAN_TITLE = "Baltagul"
ROMANIAN_AUTHOR = "Mihail Sadoveanu"

print(f"Environment initialized | Python {sys.version.split()[0]} | Student: {STUDENT_NAME}")"""
cells.append(nbf.v4.new_code_cell(c2_code))

# ==============================================================================
# Cell 3: PDF Discovery & Selection (Code)
# ==============================================================================
c3_code = """# Discover candidate PDF thesis files in data/raw and data/pdf
pdf_candidates = sorted(list(DATA_RAW.glob("*.pdf")) + list(DATA_PDF.glob("*.pdf")))
# Deduplicate by filename
pdf_dict = {p.name: p for p in pdf_candidates}

if not pdf_dict:
    raise FileNotFoundError("No thesis PDF found in data/raw/ or data/pdf/.")

# Default to Licenta_Todoran_UMF.pdf if present, else first found
default_pdf_name = "Licenta_Todoran_UMF.pdf" if "Licenta_Todoran_UMF.pdf" in pdf_dict else list(pdf_dict.keys())[0]
SELECTED_PDF_PATH = pdf_dict[default_pdf_name]

print(f"Discovered {len(pdf_dict)} candidate PDF(s): {list(pdf_dict.keys())}")
print(f"Selected Thesis PDF: {SELECTED_PDF_PATH.resolve()}")

# Optional interactive widget (works in active Jupyter session)
try:
    import ipywidgets as widgets
    dropdown = widgets.Dropdown(
        options=list(pdf_dict.keys()),
        value=default_pdf_name,
        description="Thesis PDF:",
        disabled=False,
    )
    display(dropdown)
except Exception:
    pass"""
cells.append(nbf.v4.new_code_cell(c3_code))

# ==============================================================================
# Cell 4: Corpus Acquisition & Page-by-Page Extraction (Code)
# ==============================================================================
c4_code = """# 1. Acquire & Extract English / Thesis PDF page-by-page
print(f"Extracting text from: {SELECTED_PDF_PATH.name} ...")
reader = pypdf.PdfReader(str(SELECTED_PDF_PATH))
num_pages = len(reader.pages)

pages_data = []
all_extracted_text = []

for page_idx, page in enumerate(reader.pages):
    page_txt = page.extract_text() or ""
    pages_data.append({
        "page_number": page_idx + 1,
        "char_count": len(page_txt),
        "text": page_txt
    })
    all_extracted_text.append(page_txt)

raw_thesis_text = "\\n".join(all_extracted_text)
cached_thesis_path = DATA_RAW / "licenta_todoran.txt"
cached_thesis_path.write_text(raw_thesis_text, encoding="utf-8")

print(f"[Corpus B] Extracted {num_pages} pages ({len(raw_thesis_text):,} characters) -> Cached to {cached_thesis_path.name}")

# Language Verification for Thesis PDF
words_check = re.findall(r'[a-zà-öø-ÿăâîșț]+', raw_thesis_text.lower())
ro_stop_set = {'de', 'în', 'și', 'la', 'cu', 'pentru', 'care', 'este', 'un', 'o', 'să', 'pe', 'din'}
en_stop_set = {'the', 'of', 'and', 'to', 'in', 'is', 'that', 'for', 'it', 'as', 'was', 'with', 'by'}

ro_stop_count = sum(1 for w in words_check if w in ro_stop_set)
en_stop_count = sum(1 for w in words_check if w in en_stop_set)
ro_ratio = (ro_stop_count / (ro_stop_count + en_stop_count)) * 100 if (ro_stop_count + en_stop_count) > 0 else 0

print(f"Language Check: Romanian stopwords = {ro_stop_count:,} ({ro_ratio:.1f}%), English stopwords = {en_stop_count:,} ({100-ro_ratio:.1f}%)")
if ro_stop_count > en_stop_count:
    THESIS_LANG_DETECTED = "Romanian (Technical Thesis with English Abstract)"
else:
    THESIS_LANG_DETECTED = "English"
print(f"Detected Thesis Language: {THESIS_LANG_DETECTED}")

# 2. Check Romanian Corpus (Corpus A - Baltagul)
if ROMANIAN_CORPUS_FILE.exists() and ROMANIAN_CORPUS_FILE.stat().st_size > 0:
    raw_romanian_text = ROMANIAN_CORPUS_FILE.read_text(encoding="utf-8", errors="replace")
    RO_AVAILABLE = True
    print(f"[Corpus A] Loaded Romanian corpus from {ROMANIAN_CORPUS_FILE.name} ({len(raw_romanian_text):,} chars)")
else:
    raw_romanian_text = None
    RO_AVAILABLE = False
    print(f"[Corpus A] Romanian file not found at: {ROMANIAN_CORPUS_FILE.resolve()}")
    print("           >>> Status: Romanian results are marked as PENDING.")
    print("           >>> To populate RO results, place 'baltagul.txt' in data/raw/ and re-run all cells.")"""
cells.append(nbf.v4.new_code_cell(c4_code))

# ==============================================================================
# Cell 5: Tokenization & Preprocessing (Code)
# ==============================================================================
c5_code = """TOKEN_REGEX = re.compile(r"[a-zà-öø-ÿăâîșț]+(?:'[a-zà-öø-ÿăâîșț]+)*")

def clean_and_tokenize(text: str, is_pdf: bool = False) -> list[str]:
    \"\"\"Unified preprocessing pipeline:
    1. Standardize PDF/LaTeX diacritics (if PDF).
    2. Normalize Unicode to NFC.
    3. Standardize single quotes (’, ‘ -> ').
    4. Lowercase.
    5. Tokenize using Latin+Romanian regex (preserves internal apostrophes).
    6. Exclude numbers and standalone punctuation.
    7. Retain all stopwords. No stemming or lemmatization.
    \"\"\"
    if is_pdf:
        # Standardize LaTeX font diacritics
        text = re.sub(r'˘\\s*a', 'ă', text)
        text = re.sub(r'˘\\s*A', 'Ă', text)
        text = re.sub(r'ˆ\\s*ı', 'î', text)
        text = re.sub(r'ˆ\\s*i', 'î', text)
        text = re.sub(r'ˆ\\s*I', 'Î', text)
        text = re.sub(r'ˆ\\s*a', 'â', text)
        text = re.sub(r'ˆ\\s*A', 'Â', text)
        text = re.sub(r's,\\s*', 'ș', text)
        text = re.sub(r'S,\\s*', 'Ș', text)
        text = re.sub(r't,\\s*', 'ț', text)
        text = re.sub(r'T,\\s*', 'Ț', text)
    
    text = unicodedata.normalize("NFC", text)
    text = text.replace("’", "'").replace("‘", "'").lower()
    return TOKEN_REGEX.findall(text)

# Tokenize Thesis PDF
tokens_thesis = clean_and_tokenize(raw_thesis_text, is_pdf=True)
print(f"Thesis PDF Tokens: {len(tokens_thesis):,} | Unique Types: {len(set(tokens_thesis)):,}")
print("Sample first 20 tokens:", tokens_thesis[:20])

# Tokenize Romanian if available
if RO_AVAILABLE:
    tokens_ro = clean_and_tokenize(raw_romanian_text, is_pdf=False)
    print(f"Romanian Corpus Tokens: {len(tokens_ro):,} | Unique Types: {len(set(tokens_ro)):,}")
else:
    tokens_ro = None"""
cells.append(nbf.v4.new_code_cell(c5_code))

# ==============================================================================
# Cell 6: Corpus Dimension & Size Validation (Code)
# ==============================================================================
c6_code = """dim_data = []

# Thesis PDF
n_tokens_thesis = len(tokens_thesis)
n_types_thesis = len(set(tokens_thesis))
ttr_thesis = n_types_thesis / n_tokens_thesis if n_tokens_thesis > 0 else 0

dim_data.append({
    "Corpus": "Bachelor Thesis PDF",
    "Language": THESIS_LANG_DETECTED,
    "Tokens (N)": f"{n_tokens_thesis:,}",
    "Types (V)": f"{n_types_thesis:,}",
    "TTR": round(ttr_thesis, 4),
    "Dimension Note": "Authentic full thesis text processed without artificial padding"
})

if n_tokens_thesis < 50000:
    print(f"[NOTICE] Bachelor Thesis contains {n_tokens_thesis:,} tokens (< 50,000 target). Using authentic unpadded count.")

# Romanian Corpus
if RO_AVAILABLE:
    n_tokens_ro = len(tokens_ro)
    n_types_ro = len(set(tokens_ro))
    ttr_ro = n_types_ro / n_tokens_ro if n_tokens_ro > 0 else 0
    dim_data.append({
        "Corpus": f"{ROMANIAN_TITLE} ({ROMANIAN_AUTHOR})",
        "Language": "Romanian",
        "Tokens (N)": f"{n_tokens_ro:,}",
        "Types (V)": f"{n_types_ro:,}",
        "TTR": round(ttr_ro, 4),
        "Dimension Note": "Full text analyzed"
    })
else:
    dim_data.append({
        "Corpus": f"{ROMANIAN_TITLE} ({ROMANIAN_AUTHOR})",
        "Language": "Romanian",
        "Tokens (N)": "[PENDING]",
        "Types (V)": "[PENDING]",
        "TTR": "[PENDING]",
        "Dimension Note": f"File not found at {ROMANIAN_CORPUS_FILE.name}"
    })

display(HTML("<h3>Corpus Dimension Summary</h3>"))
dim_df = pd.DataFrame(dim_data)
dim_df.to_csv(RESULTS_FINAL / "corpus_statistics.csv", index=False)
display(dim_df)"""
cells.append(nbf.v4.new_code_cell(c6_code))

# ==============================================================================
# Cell 7: Frequency Calculation & Deterministic Ranking (Code)
# ==============================================================================
c7_code = """def compute_ranked_frequencies(token_list: list[str]) -> pd.DataFrame:
    \"\"\"Deterministic sorting: descending frequency (-frequency), ascending alphabetical (word).\"\"\"
    counts = Counter(token_list)
    total_tokens = len(token_list)
    sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    
    rows = []
    cum = 0
    for r, (w, f) in enumerate(sorted_items, 1):
        cum += f
        rows.append({
            "rank": r,
            "word": w,
            "frequency": f,
            "relative_frequency": f / total_tokens,
            "cumulative_frequency": cum,
        })
    return pd.DataFrame(rows)

freq_thesis_df = compute_ranked_frequencies(tokens_thesis)
csv_en_freq = RESULTS_FINAL / "english_frequencies.csv"
freq_thesis_df.to_csv(csv_en_freq, index=False)
print(f"Exported Thesis Frequencies ({len(freq_thesis_df):,} types) -> {csv_en_freq.name}")

if RO_AVAILABLE:
    freq_ro_df = compute_ranked_frequencies(tokens_ro)
    csv_ro_freq = RESULTS_FINAL / "romanian_frequencies.csv"
    freq_ro_df.to_csv(csv_ro_freq, index=False)
    print(f"Exported Romanian Frequencies ({len(freq_ro_df):,} types) -> {csv_ro_freq.name}")
else:
    freq_ro_df = None

display(HTML("<h4>Top 15 Most Frequent Words in Bachelor's Thesis</h4>"))
display(freq_thesis_df.head(15))"""
cells.append(nbf.v4.new_code_cell(c7_code))

# ==============================================================================
# Cell 8: Most Frequent 7 Words (Code)
# ==============================================================================
c8_code = """def format_top7_string(freq_df: pd.DataFrame) -> str:
    top7_tuples = [(row.word, row.frequency) for row in freq_df.iloc[:7].itertuples()]
    return ", ".join(f'("{w}":{f})' for w, f in top7_tuples)

top7_str_thesis = format_top7_string(freq_thesis_df)
top7_thesis_items = [(row.word, row.frequency) for row in freq_thesis_df.iloc[:7].itertuples()]

print("MOST FREQUENT 7 WORDS:")
print(f"EN / Thesis:\\n  {top7_str_thesis}")

if RO_AVAILABLE:
    top7_str_ro = format_top7_string(freq_ro_df)
    top7_ro_items = [(row.word, row.frequency) for row in freq_ro_df.iloc[:7].itertuples()]
    print(f"RO / Baltagul:\\n  {top7_str_ro}")
else:
    top7_str_ro = "[PENDING - Romanian corpus file not provided]"
    top7_ro_items = []
    print(f"RO / Baltagul:\\n  {top7_str_ro}")

# Save top 7 words to CSV
top7_csv_data = []
for r, (w, f) in enumerate(top7_thesis_items, 1):
    top7_csv_data.append({"corpus": "Bachelor Thesis", "rank": r, "word": w, "frequency": f})
if RO_AVAILABLE:
    for r, (w, f) in enumerate(top7_ro_items, 1):
        top7_csv_data.append({"corpus": "Baltagul", "rank": r, "word": w, "frequency": f})

pd.DataFrame(top7_csv_data).to_csv(RESULTS_FINAL / "top7_words.csv", index=False)"""
cells.append(nbf.v4.new_code_cell(c8_code))

# ==============================================================================
# Cell 9: Percentage Covered by Top 7 Words (Code)
# ==============================================================================
c9_code = """sum_top7_thesis = sum(f for _, f in top7_thesis_items)
cov_top7_thesis = (sum_top7_thesis / n_tokens_thesis) * 100

print(f"Top 7 Coverage (Thesis):")
print(f"  Sum of top 7 frequencies: {sum_top7_thesis:,}")
print(f"  Total tokens:             {n_tokens_thesis:,}")
print(f"  Coverage:                 {cov_top7_thesis:.2f}%")

if RO_AVAILABLE:
    sum_top7_ro = sum(f for _, f in top7_ro_items)
    cov_top7_ro = (sum_top7_ro / n_tokens_ro) * 100
    cov_top7_ro_str = f"{cov_top7_ro:.2f}%"
    print(f"Top 7 Coverage (Romanian):\\n  {cov_top7_ro_str}")
else:
    sum_top7_ro = 0
    cov_top7_ro = 0.0
    cov_top7_ro_str = "[PENDING]"

top7_cov_table = pd.DataFrame([
    {
        "Corpus": "Bachelor Thesis PDF",
        "Top 7 Frequency Sum": f"{sum_top7_thesis:,}",
        "Total Tokens": f"{n_tokens_thesis:,}",
        "Top 7 Coverage": f"{cov_top7_thesis:.2f}%",
    },
    {
        "Corpus": f"{ROMANIAN_TITLE} ({ROMANIAN_AUTHOR})",
        "Top 7 Frequency Sum": f"{sum_top7_ro:,}" if RO_AVAILABLE else "[PENDING]",
        "Total Tokens": f"{n_tokens_ro:,}" if RO_AVAILABLE else "[PENDING]",
        "Top 7 Coverage": cov_top7_ro_str,
    }
])
display(HTML("<h4>Percentage of Tokens Covered by Top 7 Words</h4>"))
display(top7_cov_table)"""
cells.append(nbf.v4.new_code_cell(c9_code))

# ==============================================================================
# Cell 10: Hapax Legomena Analysis (Words Appearing Once) (Code)
# ==============================================================================
c10_code = """def compute_hapax_metrics(freq_df: pd.DataFrame, total_tokens: int) -> dict:
    hapax_df = freq_df[freq_df["frequency"] == 1]
    hapax_types = len(hapax_df)
    hapax_tokens = hapax_types  # each token appears exactly once
    total_types = len(freq_df)
    
    pct_tokens = (hapax_tokens / total_tokens) * 100 if total_tokens > 0 else 0.0
    pct_types = (hapax_types / total_types) * 100 if total_types > 0 else 0.0
    
    return {
        "hapax_types": hapax_types,
        "hapax_tokens": hapax_tokens,
        "pct_tokens": pct_tokens,
        "pct_types": pct_types,
        "formatted_display": f"{hapax_types}\\n{pct_tokens:.2f}% of tokens\\n{pct_types:.2f}% of types"
    }

hapax_thesis = compute_hapax_metrics(freq_thesis_df, n_tokens_thesis)

print("WORDS APPEARING ONCE (HAPAX LEGOMENA) - THESIS:")
print(f"  Count:       {hapax_thesis['hapax_types']:,}")
print(f"  % of tokens: {hapax_thesis['pct_tokens']:.2f}%")
print(f"  % of types:  {hapax_thesis['pct_types']:.2f}%")

if RO_AVAILABLE:
    hapax_ro = compute_hapax_metrics(freq_ro_df, n_tokens_ro)
    print(f"\\nWORDS APPEARING ONCE (HAPAX LEGOMENA) - ROMANIAN:")
    print(f"  Count:       {hapax_ro['hapax_types']:,}")
    print(f"  % of tokens: {hapax_ro['pct_tokens']:.2f}%")
    print(f"  % of types:  {hapax_ro['pct_types']:.2f}%")
else:
    hapax_ro = {
        "hapax_types": 0, "hapax_tokens": 0, "pct_tokens": 0.0, "pct_types": 0.0,
        "formatted_display": "[PENDING]"
    }

hapax_df = pd.DataFrame([
    {
        "Corpus": "Bachelor Thesis PDF",
        "Hapax Types": f"{hapax_thesis['hapax_types']:,}",
        "Hapax Tokens": f"{hapax_thesis['hapax_tokens']:,}",
        "% of Tokens": f"{hapax_thesis['pct_tokens']:.2f}%",
        "% of Types": f"{hapax_thesis['pct_types']:.2f}%",
    },
    {
        "Corpus": f"{ROMANIAN_TITLE} ({ROMANIAN_AUTHOR})",
        "Hapax Types": f"{hapax_ro['hapax_types']:,}" if RO_AVAILABLE else "[PENDING]",
        "Hapax Tokens": f"{hapax_ro['hapax_tokens']:,}" if RO_AVAILABLE else "[PENDING]",
        "% of Tokens": f"{hapax_ro['pct_tokens']:.2f}%" if RO_AVAILABLE else "[PENDING]",
        "% of Types": f"{hapax_ro['pct_types']:.2f}%" if RO_AVAILABLE else "[PENDING]",
    }
])
hapax_df.to_csv(RESULTS_FINAL / "hapax_analysis.csv", index=False)
display(HTML("<h4>Hapax Legomena Statistical Summary</h4>"))
display(hapax_df)"""
cells.append(nbf.v4.new_code_cell(c10_code))

# ==============================================================================
# Cell 11: Zipf Graph – Top 200 Most Frequent Words (Code)
# ==============================================================================
c11_code = """# Generate Top 200 Zipf Graph: Linear Absolute Frequency vs Rank 1..200 (Professor Requirement)

# 1. Thesis Top 200 Graph
top200_thesis = freq_thesis_df.iloc[:200]
fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=150)

ax.plot(
    top200_thesis["rank"].values,
    top200_thesis["frequency"].values,
    color="#1f77b4",
    linewidth=2.0,
    marker="o",
    markersize=3,
    alpha=0.85,
    label=f"Thesis ({top200_thesis.iloc[0]['word']}: {top200_thesis.iloc[0]['frequency']:,})"
)

ax.set_title("Zipf's Law: Top 200 Most Frequent Words – Bachelor's Thesis", fontweight="bold", pad=10)
ax.set_xlabel("Word Rank (1 to 200)", labelpad=8)
ax.set_ylabel("Absolute Word Frequency", labelpad=8)
ax.set_xlim(1, 200)
ax.set_ylim(0, top200_thesis["frequency"].max() * 1.05)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(loc="upper right", framealpha=0.95)

plt.tight_layout()
graph_en_path = RESULTS_FINAL_GRAPHS / "zipf_english_top200.png"
fig.savefig(graph_en_path, dpi=300)
plt.show()
print(f"Saved Thesis Top 200 Graph -> {graph_en_path.resolve()}")

# 2. Romanian Top 200 Graph (if available)
if RO_AVAILABLE:
    top200_ro = freq_ro_df.iloc[:200]
    fig_ro, ax_ro = plt.subplots(figsize=(8.5, 5.0), dpi=150)
    ax_ro.plot(top200_ro["rank"].values, top200_ro["frequency"].values, color="#d62728", linewidth=2.0, marker="o", markersize=3, alpha=0.85)
    ax_ro.set_title(f"Zipf's Law: Top 200 Words – {ROMANIAN_TITLE}", fontweight="bold", pad=10)
    ax_ro.set_xlabel("Word Rank (1 to 200)", labelpad=8)
    ax_ro.set_ylabel("Absolute Word Frequency", labelpad=8)
    ax_ro.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    graph_ro_path = RESULTS_FINAL_GRAPHS / "zipf_romanian_top200.png"
    fig_ro.savefig(graph_ro_path, dpi=300)
    plt.show()
    print(f"Saved Romanian Top 200 Graph -> {graph_ro_path.resolve()}")
else:
    graph_ro_path = None
    print("[Romanian Top 200 Graph: PENDING - file not found]")"""
cells.append(nbf.v4.new_code_cell(c11_code))

# ==============================================================================
# Cell 12: Final Results Dashboard (Code)
# ==============================================================================
c12_code = """# Combined Final Comparison Table
dashboard_summary = pd.DataFrame([
    {
        "Language": "EN (Thesis)",
        "Corpus Source": "Bachelor Thesis PDF",
        "Tokens": f"{n_tokens_thesis:,}",
        "Types": f"{n_types_thesis:,}",
        "TTR": round(ttr_thesis, 4),
        "Top Word": f"'{freq_thesis_df.iloc[0]['word']}' ({freq_thesis_df.iloc[0]['frequency']:,})",
        "Top 7 Coverage": f"{cov_top7_thesis:.2f}%",
        "Hapax Count": f"{hapax_thesis['hapax_types']:,}",
        "Hapax % of Tokens": f"{hapax_thesis['pct_tokens']:.2f}%",
        "Hapax % of Types": f"{hapax_thesis['pct_types']:.2f}%",
    },
    {
        "Language": "RO (Baltagul)",
        "Corpus Source": f"{ROMANIAN_TITLE} ({ROMANIAN_AUTHOR})",
        "Tokens": f"{n_tokens_ro:,}" if RO_AVAILABLE else "[PENDING]",
        "Types": f"{n_types_ro:,}" if RO_AVAILABLE else "[PENDING]",
        "TTR": round(ttr_ro, 4) if RO_AVAILABLE else "[PENDING]",
        "Top Word": f"'{freq_ro_df.iloc[0]['word']}' ({freq_ro_df.iloc[0]['frequency']:,})" if RO_AVAILABLE else "[PENDING]",
        "Top 7 Coverage": cov_top7_ro_str,
        "Hapax Count": f"{hapax_ro['hapax_types']:,}" if RO_AVAILABLE else "[PENDING]",
        "Hapax % of Tokens": f"{hapax_ro['pct_tokens']:.2f}%" if RO_AVAILABLE else "[PENDING]",
        "Hapax % of Types": f"{hapax_ro['pct_types']:.2f}%" if RO_AVAILABLE else "[PENDING]",
    }
])
dashboard_summary.to_csv(RESULTS_FINAL / "final_comparison.csv", index=False)

display(HTML("<h3>Final Statistical Results Dashboard</h3>"))
display(dashboard_summary)"""
cells.append(nbf.v4.new_code_cell(c12_code))

# ==============================================================================
# Cell 13: Professor's Required Results Table (Markdown/HTML Display) (Code)
# ==============================================================================
c13_code = """# Build Professor's exact table representation

html_table = f\"\"\"
<div style="font-family: Arial, sans-serif; overflow-x: auto; margin: 15px 0;">
    <h3 style="color: #1a2b49; border-bottom: 2px solid #1a2b49; padding-bottom: 4px;">
        ACL Seminar 3 – Official Professor Results Table
    </h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left; background: white;">
        <thead>
            <tr style="background-color: #1a2b49; color: white;">
                <th style="border: 1px solid #ddd; padding: 6px;">#</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Student</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Corpus source /<br/>Corpus dimension</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Zipf graph<br/>(top 200 words)</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Most frequent 7 words</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Percentage of tokens covered by top 7 words</th>
                <th style="border: 1px solid #ddd; padding: 6px;">Percentage of words appearing once</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="border: 1px solid #ddd; padding: 6px; font-weight: bold; text-align: center;">1</td>
                <td style="border: 1px solid #ddd; padding: 6px; font-weight: bold;">{STUDENT_NAME}</td>
                <td style="border: 1px solid #ddd; padding: 6px; white-space: pre-line;">
                    <b>RO:</b><br/>{ROMANIAN_TITLE}:<br/>{f"{n_tokens_ro:,} tokens, {n_types_ro:,} types." if RO_AVAILABLE else "[PENDING]"}<br/><br/>
                    <b>EN:</b><br/>Bachelor Thesis:<br/>{n_tokens_thesis:,} tokens, {n_types_thesis:,} types.
                </td>
                <td style="border: 1px solid #ddd; padding: 6px; text-align: center;">
                    <b>RO:</b><br/>{"[Graph embedded]" if RO_AVAILABLE else "[PENDING]"}<br/><br/>
                    <b>EN:</b><br/>[Top 200 Curve Embedded]
                </td>
                <td style="border: 1px solid #ddd; padding: 6px;">
                    <b>RO:</b><br/>{top7_str_ro}<br/><br/>
                    <b>EN:</b><br/>{top7_str_thesis}
                </td>
                <td style="border: 1px solid #ddd; padding: 6px;">
                    <b>RO:</b> {cov_top7_ro_str}<br/><br/>
                    <b>EN:</b> {cov_top7_thesis:.2f}%
                </td>
                <td style="border: 1px solid #ddd; padding: 6px; white-space: pre-line;">
                    <b>RO:</b><br/>{hapax_ro['formatted_display']}<br/><br/>
                    <b>EN:</b><br/>{hapax_thesis['formatted_display']}
                </td>
            </tr>
        </tbody>
    </table>
</div>
\"\"\"

display(HTML(html_table))"""
cells.append(nbf.v4.new_code_cell(c13_code))

# ==============================================================================
# Cell 14: Automated Validation (Code)
# ==============================================================================
c14_code = """# Automated Validation Suite (Section 14)
print("=== AUTOMATED STATISTICAL VALIDATION ===")

checks = []

# 1. Total tokens == sum of frequencies
token_sum_thesis = freq_thesis_df["frequency"].sum()
assert token_sum_thesis == n_tokens_thesis, f"Token mismatch: {token_sum_thesis} != {n_tokens_thesis}"
checks.append(("Total tokens == sum of word frequencies", True, f"{token_sum_thesis:,} == {n_tokens_thesis:,}"))

# 2. Total types == count of unique words
assert len(freq_thesis_df) == n_types_thesis, "Unique types mismatch"
checks.append(("Total types == number of unique words", True, f"{len(freq_thesis_df):,} == {n_types_thesis:,}"))

# 3. Top 7 frequencies sorted descending
top7_freqs_thesis = [f for _, f in top7_thesis_items]
is_sorted_desc = all(top7_freqs_thesis[i] >= top7_freqs_thesis[i+1] for i in range(len(top7_freqs_thesis)-1))
assert is_sorted_desc, "Top 7 frequencies not sorted descending"
checks.append(("Top 7 frequencies sorted descending", True, str(top7_freqs_thesis)))

# 4. Top 7 frequency sum <= total tokens
assert sum_top7_thesis <= n_tokens_thesis, "Top 7 sum exceeds total tokens"
checks.append(("Top 7 sum <= total tokens", True, f"{sum_top7_thesis:,} <= {n_tokens_thesis:,}"))

# 5. Hapax tokens == hapax types
assert hapax_thesis["hapax_tokens"] == hapax_thesis["hapax_types"], "Hapax tokens != hapax types"
checks.append(("Hapax tokens == hapax types", True, f"{hapax_thesis['hapax_tokens']:,} == {hapax_thesis['hapax_types']:,}"))

# 6. Hapax types <= total types
assert hapax_thesis["hapax_types"] <= n_types_thesis, "Hapax types exceed total types"
checks.append(("Hapax types <= total types", True, f"{hapax_thesis['hapax_types']:,} <= {n_types_thesis:,}"))

# 7. Coverage percentages within [0, 100]
assert 0 <= cov_top7_thesis <= 100, "Coverage percentage out of bounds"
assert 0 <= hapax_thesis["pct_tokens"] <= 100, "Hapax % tokens out of bounds"
assert 0 <= hapax_thesis["pct_types"] <= 100, "Hapax % types out of bounds"
checks.append(("All percentages strictly within [0, 100]%", True, f"{cov_top7_thesis:.2f}%, {hapax_thesis['pct_tokens']:.2f}%"))

# 8. Top 200 graph points <= 200
assert len(top200_thesis) <= 200, "Top 200 graph has > 200 points"
checks.append(("Zipf graph points <= 200", True, f"{len(top200_thesis)} points"))

for name, status, detail in checks:
    print(f"  [PASS] {name:<45} : {detail}")

print("\\nAll 8 automated statistical validation checks passed successfully!")"""
cells.append(nbf.v4.new_code_cell(c14_code))

# ==============================================================================
# Cell 15: Export CSV, JSON & DOCX Document (Code)
# ==============================================================================
c15_code = """# 1. Export JSON Experiment Results
experiment_json_payload = {
    "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "student": STUDENT_NAME,
    "english_corpus": {
        "source": SELECTED_PDF_PATH.name,
        "language_detected": THESIS_LANG_DETECTED,
        "total_tokens": n_tokens_thesis,
        "total_unique_types": n_types_thesis,
        "ttr": ttr_thesis,
        "top_7_words": top7_thesis_items,
        "top_7_coverage_pct": cov_top7_thesis,
        "hapax_legomena": hapax_thesis,
        "zipf_graph": str(graph_en_path.relative_to(BASE_DIR)),
    },
    "romanian_corpus": {
        "source": ROMANIAN_TITLE,
        "status": "Available" if RO_AVAILABLE else "Pending (file not found in data/raw/)",
        "total_tokens": n_tokens_ro if RO_AVAILABLE else None,
        "total_unique_types": n_types_ro if RO_AVAILABLE else None,
        "ttr": ttr_ro if RO_AVAILABLE else None,
        "top_7_words": top7_ro_items if RO_AVAILABLE else None,
        "top_7_coverage_pct": cov_top7_ro if RO_AVAILABLE else None,
        "hapax_legomena": hapax_ro if RO_AVAILABLE else None,
    }
}

json_path = RESULTS_FINAL / "experiment_results.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(experiment_json_payload, f, indent=2, ensure_ascii=False)
print(f"Exported JSON Results -> {json_path.resolve()}")

# 2. Generate Landscape DOCX Results Table
docx_out_path = RESULTS_FINAL / "ACL_Seminar_3_Results.docx"
doc = docx.Document()

# Configure Landscape Orientation & 0.5-inch margins
section = doc.sections[0]
section.orientation = WD_ORIENTATION.LANDSCAPE
section.page_width, section.page_height = Inches(11.0), Inches(8.5)
section.left_margin = Inches(0.5)
section.right_margin = Inches(0.5)
section.top_margin = Inches(0.5)
section.bottom_margin = Inches(0.5)

# Document Header
title_p = doc.add_paragraph()
title_run = title_p.add_run("ACL Seminar 3 – Zipf's Law Corpus Experiment Results")
title_run.bold = True
title_run.font.size = Pt(14)
title_run.font.color.rgb = RGBColor(0x1a, 0x2b, 0x49)

sub_p = doc.add_paragraph()
sub_run = sub_p.add_run(f"Student: {STUDENT_NAME} | Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}")
sub_run.font.size = Pt(9.5)
sub_run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

# Build 7-column Table matching Professor's Structure
table = doc.add_table(rows=2, cols=7)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.autofit = False

headers = [
    "#",
    "Student",
    "Corpus source /\\nCorpus dimension",
    "Zipf graph\\n(top 200 words)",
    "Most frequent 7 words",
    "Percentage of tokens covered by top 7 words",
    "Percentage of words appearing once"
]

# Set specific column widths (total = 10.0 inches)
col_widths = [Inches(0.4), Inches(1.2), Inches(1.4), Inches(2.5), Inches(2.1), Inches(1.1), Inches(1.3)]

for col_idx, width in enumerate(col_widths):
    table.columns[col_idx].width = width

# Style Header Row
header_row = table.rows[0]
for col_idx, h_text in enumerate(headers):
    cell = header_row.cells[col_idx]
    cell.width = col_widths[col_idx]
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(h_text)
    run.bold = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
    # Dark Navy shading
    shading = docx.oxml.parse_xml(r'<w:shd {} w:fill="1A2B49"/>'.format(docx.oxml.ns.nsdecls('w')))
    cell._tc.get_or_add_tcPr().append(shading)

# Populate Data Row
data_row = table.rows[1]

# Col 1: #
c1 = data_row.cells[0]
p1 = c1.paragraphs[0]
p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
r1 = p1.add_run("1")
r1.bold = True
r1.font.size = Pt(8.5)

# Col 2: Student
c2 = data_row.cells[1]
p2 = c2.paragraphs[0]
r2 = p2.add_run(STUDENT_NAME)
r2.bold = True
r2.font.size = Pt(8.5)

# Col 3: Corpus source / Corpus dimension
c3 = data_row.cells[2]
p3 = c3.paragraphs[0]
p3.paragraph_format.line_spacing = 1.15
r3_ro = p3.add_run(f"RO:\\n{ROMANIAN_TITLE}:\\n{f'{n_tokens_ro:,} tokens, {n_types_ro:,} types.' if RO_AVAILABLE else '[PENDING]'}\\n\\n")
r3_ro.font.size = Pt(8.0)
r3_en = p3.add_run(f"EN:\\nBachelor Thesis:\\n{n_tokens_thesis:,} tokens, {n_types_thesis:,} types.")
r3_en.font.size = Pt(8.0)

# Col 4: Zipf graph (top 200 words)
c4 = data_row.cells[3]
p4 = c4.paragraphs[0]
p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
if RO_AVAILABLE and graph_ro_path and graph_ro_path.exists():
    p4.add_run("RO Top 200:\\n").font.size = Pt(7.5)
    p4.add_run().add_picture(str(graph_ro_path), width=Inches(2.2))
    p4.add_run("\\nEN Top 200:\\n").font.size = Pt(7.5)
else:
    r_pend = p4.add_run("RO: [PENDING]\\n\\nEN Top 200:\\n")
    r_pend.font.size = Pt(7.5)

if graph_en_path.exists():
    p4.add_run().add_picture(str(graph_en_path), width=Inches(2.2))

# Col 5: Most frequent 7 words
c5 = data_row.cells[4]
p5 = c5.paragraphs[0]
p5.paragraph_format.line_spacing = 1.15
r5_ro = p5.add_run(f"RO:\\n{top7_str_ro}\\n\\n")
r5_ro.font.size = Pt(7.5)
r5_en = p5.add_run(f"EN:\\n{top7_str_thesis}")
r5_en.font.size = Pt(7.5)

# Col 6: Percentage of tokens covered by top 7 words
c6 = data_row.cells[5]
p6 = c6.paragraphs[0]
p6.paragraph_format.line_spacing = 1.2
r6 = p6.add_run(f"RO:\\n{cov_top7_ro_str}\\n\\nEN:\\n{cov_top7_thesis:.2f}%")
r6.font.size = Pt(8.0)
r6.bold = True

# Col 7: Percentage of words appearing once
c7 = data_row.cells[6]
p7 = c7.paragraphs[0]
p7.paragraph_format.line_spacing = 1.2
r7_ro = p7.add_run(f"RO:\\n{hapax_ro['formatted_display']}\\n\\n")
r7_ro.font.size = Pt(7.5)
r7_en = p7.add_run(f"EN:\\n{hapax_thesis['formatted_display']}")
r7_en.font.size = Pt(7.5)

# Save Document
doc.save(str(docx_out_path))
print(f"Generated Landscape DOCX Results Table -> {docx_out_path.resolve()} ({docx_out_path.stat().st_size:,} bytes)")"""
cells.append(nbf.v4.new_code_cell(c15_code))

# ==============================================================================
# Cell 16: Final Completion Summary (Code)
# ==============================================================================
c16_code = """summary_banner = f\"\"\"
<div style="border: 2px solid #2b6cb0; border-radius: 8px; padding: 16px; background-color: #ebf8ff; font-family: Arial, sans-serif;">
    <h3 style="color: #2b6cb0; margin-top: 0;">ACL Seminar 3 – Final Zipf Results Execution Complete</h3>
    <p><b>Student:</b> {STUDENT_NAME}</p>
    <p><b>Status:</b> All statistical metrics, graphs, CSV tables, and the professor's DOCX table have been generated.</p>
    
    <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; background: white;">
        <tr style="background: #2b6cb0; color: white;">
            <th style="padding: 6px; border: 1px solid #cbd5e0;">Metric</th>
            <th style="padding: 6px; border: 1px solid #cbd5e0;">Bachelor Thesis (EN)</th>
            <th style="padding: 6px; border: 1px solid #cbd5e0;">Baltagul (RO)</th>
        </tr>
        <tr>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>Corpus Tokens / Types</b></td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{n_tokens_thesis:,} tokens, {n_types_thesis:,} types</td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{f"{n_tokens_ro:,} tokens, {n_types_ro:,} types" if RO_AVAILABLE else "[PENDING]"}</td>
        </tr>
        <tr>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>Most Frequent 7 Words</b></td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{top7_str_thesis}</td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{top7_str_ro}</td>
        </tr>
        <tr>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>Top 7 Token Coverage</b></td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>{cov_top7_thesis:.2f}%</b></td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>{cov_top7_ro_str}</b></td>
        </tr>
        <tr>
            <td style="padding: 6px; border: 1px solid #cbd5e0;"><b>Words Appearing Once (Hapax)</b></td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{hapax_thesis['hapax_types']:,} ({hapax_thesis['pct_tokens']:.2f}% tokens, {hapax_thesis['pct_types']:.2f}% types)</td>
            <td style="padding: 6px; border: 1px solid #cbd5e0;">{f"{hapax_ro['hapax_types']:,} ({hapax_ro['pct_tokens']:.2f}% tokens, {hapax_ro['pct_types']:.2f}% types)" if RO_AVAILABLE else "[PENDING]"}</td>
        </tr>
    </table>
    
    <h4 style="margin-bottom: 4px; color: #2d3748;">Generated Artifacts:</h4>
    <ul style="margin-top: 4px; font-size: 12px;">
        <li><b>DOCX Results Table:</b> <code>results/final_results/ACL_Seminar_3_Results.docx</code></li>
        <li><b>Zipf Top 200 Graph:</b> <code>results/final_results/graphs/zipf_english_top200.png</code></li>
        <li><b>JSON Metadata & Results:</b> <code>results/final_results/experiment_results.json</code></li>
        <li><b>CSVs:</b> <code>corpus_statistics.csv</code>, <code>top7_words.csv</code>, <code>hapax_analysis.csv</code>, <code>final_comparison.csv</code></li>
    </ul>
</div>
\"\"\"

display(HTML(summary_banner))"""
cells.append(nbf.v4.new_code_cell(c16_code))

nb.cells = cells

# Save and execute notebooks for both requested names
nb_path_final = Path("notebooks/ACL_Seminar_3_Zipf_Analysis_Final.ipynb")
nb_path_results = Path("notebooks/ACL_Seminar_3_Final_Results.ipynb")

for p in [nb_path_final, nb_path_results]:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        nbf.write(nb, f)

print(f"Executing notebook {nb_path_final.resolve()}...")
client = NotebookClient(nb, timeout=300, kernel_name="python3", allow_errors=False)
client.execute()

# Save executed state to both files
for p in [nb_path_final, nb_path_results]:
    with open(p, "w", encoding="utf-8") as f:
        nbf.write(nb, f)

print(f"Successfully generated and executed {nb_path_final.name} ({nb_path_final.stat().st_size:,} bytes)")
print(f"Successfully generated and executed {nb_path_results.name} ({nb_path_results.stat().st_size:,} bytes)")
