# ACL Seminar 3: Zipf's Law Corpus Experiment

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 18 passed](https://img.shields.io/badge/tests-18%20passed-success.svg)](#running-unit-tests)

A reproducible Computational Linguistics research project investigating **Zipf's Law** across English and Italian corpora for Applied Computational Linguistics (ACL) Seminar 3.

---

## Table of Contents

1. [Project Objective](#project-objective)
2. [Corpora Investigated](#corpora-investigated)
3. [Methodology](#methodology)
4. [Statistical & Linguistic Interpretation](#statistical--linguistic-interpretation)
5. [Project Architecture](#project-architecture)
6. [Prerequisites & Installation](#prerequisites--installation)
7. [Execution Guide](#execution-guide)
8. [Generated Artifacts & Output Description](#generated-artifacts--output-description)
9. [Running Unit Tests](#running-unit-tests)
10. [Reproducibility & Metadata](#reproducibility--metadata)
11. [References](#references)

---

## Project Objective

Zipf's Law is a foundational empirical law in quantitative linguistics asserting that in any natural language text, the frequency $f(r)$ of a word is inversely proportional to its frequency rank $r$:

$$f(r) = \frac{C}{r^s} \iff \log_{10}(f(r)) = \log_{10}(C) - s \cdot \log_{10}(r)$$

where $r$ is the word rank (1 for the most frequent token), $f(r)$ is the observed frequency, $C$ is a scaling constant, and $s$ is the Zipf exponent (the negative of the linear slope on a log-log plot).

This project:
1. Obtains balanced, authentic English and Italian corpora (~40,000–50,000 words).
2. Performs unified, cross-linguistically fair preprocessing without stopword removal or lemmatization.
3. Computes rank-frequency distributions, cumulative frequencies, and Type-Token Ratios (TTR).
4. Models Zipf's Law using Ordinary Least Squares (OLS) regression over both the full distribution and the top 100 ranks.
5. Compares English vs. Italian (typological differences: analytic syntax vs. inflected Romance morphology).
6. Compares 19th-century single-author gothic fiction (*Frankenstein*) with modern multi-genre American English (*Brown Corpus*).
7. Generates 300 DPI publication-quality visualizations, CSV tables, reproducibility metadata, and an academic PDF report.

---

## Corpora Investigated

| Corpus ID | Title | Author | Language | Publication | Source | Target Size | Actual Tokens Analyzed | Unique Types | TTR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frankenstein` | *Frankenstein; or, The Modern Prometheus* | Mary Shelley | English | 1818 | [Project Gutenberg #84](https://www.gutenberg.org/ebooks/84) | 50,000 | **50,000** | 5,849 | 0.1170 |
| `pinocchio` | *Le avventure di Pinocchio* | Carlo Collodi | Italian | 1883 | [Project Gutenberg #52484](https://www.gutenberg.org/ebooks/52484) | Full (~40k–50k) | **41,525** | 6,215 | 0.1497 |
| `brown` | *Brown Corpus* (Sample ca01–ca26) | Francis & Kučera | American English | 1961 | Brown Univ. / NLTK | 50,000 | **50,000** | 8,246 | 0.1649 |

---

## Methodology

### 1. Preprocessing Pipeline
- **Boilerplate Stripping**: Standardized Project Gutenberg headers and legal license footers are systematically identified and removed.
- **Unicode Normalization**: Canonical decomposition followed by canonical composition (`NFC`).
- **Apostrophe Standardizing**: Typographic curly single quotes (`’`, `‘`) are converted to standard ASCII `'`.
- **Lowercasing**: Uniform case-folding across all languages.
- **Unified Tokenization**: Extracted via regular expression:
  ```python
  r"[a-zà-öø-ÿ]+(?:'[a-zà-öø-ÿ]+)*"
  ```
  - Preserves internal contractions/elisions in English (`don't`, `it's`, `father's`) and Italian (`l'ombra`, `c'era`, `d'oro`, `un'altra`).
  - Strips surrounding quotes, punctuation marks, and numbers.
- **Integrity**: Stopwords are **strictly preserved**; no stemming or lemmatization is applied, maintaining genuine surface lexical distributions.
- **Deterministic Sampling**: Exactly the first 50,000 tokens are taken for *Frankenstein* and *Brown Corpus*; *Pinocchio* uses the complete cleaned text (41,525 tokens).

### 2. Frequency & Rank Assignment
- Word tokens are aggregated using hash counters.
- **Deterministic Tie-Breaking**: Descending frequency primary sort, ascending alphabetical secondary sort:
  ```python
  sorted(counts.items(), key=lambda item: (-item[1], item[0]))
  ```
- Ranks $r \in [1, V]$ are sequentially assigned. Relative frequency ($f / N$) and cumulative integer frequency are computed.

### 3. Zipf Regression
- OLS linear regression is performed using `scipy.stats.linregress` on $(\log_{10}(r), \log_{10}(f(r)))$:
  - **Primary Model**: Full rank-frequency distribution.
  - **Auxiliary Model**: Top 100 ranks.
- Empirical slope, Zipf exponent $s = |\text{slope}|$, log-intercept, theoretical constant $C = 10^{\text{intercept}}$, Pearson correlation $r$, coefficient of determination $R^2$, standard error, and two-tailed p-value are reported.

---

## Statistical & Linguistic Interpretation

### Summary of Experimental Results

| Corpus | Zipf Slope (Full) | Exponent $s$ | $R^2$ (Full) | Zipf Slope (Top 100) | $R^2$ (Top 100) | Top Word (Count, % of Corpus) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Frankenstein** | **-1.0774** | 1.0774 | 0.9762 | **-1.0117** | 0.9835 | `"the"` (2,821 / 5.64%) |
| **Pinocchio** | **-1.0290** | 1.0290 | 0.9695 | **-0.8653** | 0.9860 | `"e"` (1,788 / 4.31%) |
| **Brown Corpus** | **-0.9795** | 0.9795 | 0.9693 | **-0.9799** | 0.9914 | `"the"` (3,633 / 7.27%) |

### Linguistic & Quantitative Findings
1. **Adherence to Zipf's Law**: All three corpora strongly conform to Zipf's power law across their entire rank spectrum ($R^2 \ge 0.969$, Pearson $r \le -0.984$, $p \approx 0$).
2. **Empirical vs. Theoretical Slope**: None of the empirical slopes strictly equal $-1.0000$. Forcing $s = 1.0$ would ignore real corpus dynamics. *Frankenstein* has a steeper slope (-1.0774) due to higher concentration in top function words; *Brown* has a flatter slope (-0.9795) due to multi-genre lexical dispersion.
3. **English vs. Italian Morphology**: Despite having ~8,500 fewer tokens, Italian (*Pinocchio*) exhibits **higher vocabulary richness** ($\text{TTR} = 0.1497$ vs. $0.1170$ for *Frankenstein*). Italian's rich verbal conjugations (e.g., *disse*, *diceva*, *dirò*) and grammatical gender/number inflections multiply distinct surface word forms compared to English's analytic structure.
4. **Single-Author vs. Multi-Genre English**: At identical 50,000-token sizes, the *Brown Corpus* contains **41% more unique types** (8,246 vs. 5,849) and a significantly higher TTR (0.1649 vs. 0.1170) than *Frankenstein*. The thematic uniformity of a single gothic novel contrasts sharply with the lexical diversity of journalism, essays, and academic prose.
5. **Head and Tail Deviations**: Empirical distributions display slight downward curvature at very top ranks (function word saturation) and discrete horizontal plateaus at the tail (hapax legomena with frequency = 1).

---

## Project Architecture

```text
ACL_Seminar_3/
├── data/
│   ├── raw/                              # Downloaded raw text files
│   │   ├── frankenstein.txt              # Project Gutenberg eBook #84
│   │   ├── pinocchio.txt                 # Project Gutenberg eBook #52484
│   │   └── brown_sample.txt              # NLTK Brown Corpus sample
│   └── processed/                        # Preprocessed token lists
│       ├── frankenstein_tokens.txt
│       ├── pinocchio_tokens.txt
│       └── brown_tokens.txt
├── notebooks/
│   └── ACL_Seminar_3_Zipf_Analysis.ipynb # Self-contained Jupyter Notebook
├── results/
│   ├── csv/                              # Quantitative CSV outputs
│   │   ├── corpus_comparison.csv         # Consolidated statistical summary
│   │   ├── top20_english_italian_comparison.csv
│   │   ├── frankenstein_word_frequencies.csv
│   │   ├── pinocchio_word_frequencies.csv
│   │   └── brown_word_frequencies.csv
│   ├── graphs/                           # High-resolution PNG plots (300 DPI)
│   │   ├── graph1_english_vs_italian.png
│   │   ├── graph2_english_comparison.png
│   │   ├── graph3_individual_frankenstein.png
│   │   ├── graph3_individual_pinocchio.png
│   │   ├── graph3_individual_brown.png
│   │   └── graph4_top20_words.png
│   └── reports/                          # Academic reports & metadata
│       ├── ACL_Seminar_3_Report.pdf      # Professional academic PDF report
│       └── experiment_metadata.json      # Complete execution metadata
├── src/                                  # Modular source code
│   ├── __init__.py
│   ├── corpus_loader.py                  # Downloading, caching, and fallback handling
│   ├── text_preprocessor.py              # NFC, lowercase, apostrophes, tokenization
│   ├── frequency_analyzer.py             # Frequency counts, ranks, TTR, CSV export
│   ├── zipf_analyzer.py                  # OLS regression, log-log modeling
│   ├── visualizer.py                     # Matplotlib 300 DPI graphics
│   ├── report_generator.py               # ReportLab PDF & metadata generation
│   └── experiment.py                     # Pipeline orchestration
├── tests/                                # Comprehensive test suite (18 unit tests)
│   ├── __init__.py
│   ├── test_preprocessing.py             # Preprocessing & tokenization tests
│   ├── test_frequency.py                 # Frequency calculation & rank tests
│   └── test_zipf.py                      # Regression & edge cases tests
├── main.py                               # CLI entry point
├── requirements.txt                      # Project dependencies
├── README.md                             # Documentation
└── .gitignore
```

---

## Prerequisites & Installation

### Prerequisites
- Python 3.10 or higher
- Internet connection (for initial corpus download from Gutenberg and NLTK)

### Setup in Windows PowerShell

```powershell
# 1. Clone or navigate to the repository directory
cd ACL_Seminar3

# 2. Create a virtual environment (optional but recommended)
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install required dependencies
pip install -r requirements.txt
```

---

## Execution Guide

The project provides two independent, fully supported execution methods:
1. **Command-Line Interface (Modular Application)**: `main.py`
2. **Interactive Jupyter Notebook**: `notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb`

Both methods are completely reproducible and generate identical statistical tables, 300 DPI visualizations, and academic PDF reports.

---

### Method 1: Modular Application (CLI)

#### Full End-to-End Pipeline
Run the complete pipeline (download, preprocess, analyze, graphs, CSVs, PDF report):

```powershell
python main.py
```

#### Command-Line Options

```powershell
# Download and cache corpora only
python main.py --download-only

# Run preprocessing, frequency calculation, and Zipf regression (save CSVs)
python main.py --analyze-only

# Bypass cache and re-download all texts
python main.py --force-download

# Enable detailed verbose logging
python main.py --verbose
```

---

### Method 2: Self-Contained Jupyter Notebook

The notebook `notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb` contains the entire computational workflow from end to end without any dependencies on `src/`.

#### Interactive Execution (Jupyter or VS Code / Antigravity IDE)
1. Open `notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb` in your IDE or launch Jupyter:
   ```powershell
   jupyter lab
   ```
2. Select the `.venv` Python kernel.
3. Click **Run All Cells**.

#### Headless Execution from Terminal
To execute and validate the entire notebook from the command line:

```powershell
python -m nbclient notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb
# or
jupyter nbconvert --to notebook --execute --inplace notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb
```

---

## Generated Artifacts & Output Description

### 1. CSV Distributions & Comparisons (`results/csv/`)
- `corpus_comparison.csv`: Consolidated table with corpus names, authors, sources, token counts, unique words, TTR, top words, Zipf slopes, exponents, and $R^2$ values.
- `top20_english_italian_comparison.csv`: Side-by-side table comparing the top 20 words, frequencies, and relative frequencies between English and Italian.
- `frankenstein_word_frequencies.csv`: Complete ranked frequency distribution for *Frankenstein* (`rank`, `word`, `frequency`, `relative_frequency`, `cumulative_frequency`).
- `pinocchio_word_frequencies.csv`: Complete ranked frequency distribution for *Pinocchio*.
- `brown_word_frequencies.csv`: Complete ranked frequency distribution for *Brown Corpus*.

### 2. High-Resolution Graphics (`results/graphs/`, 300 DPI)
- `graph1_english_vs_italian.png`: Log-log rank-frequency plot comparing *Frankenstein* (slope = -1.0774) and *Pinocchio* (slope = -1.0290).
- `graph2_english_comparison.png`: Log-log rank-frequency plot comparing *Frankenstein* with *Brown Corpus* (slope = -0.9795).
- `graph3_individual_frankenstein.png`: Individual scatter plot and fitted regression line for *Frankenstein*.
- `graph3_individual_pinocchio.png`: Individual scatter plot and fitted regression line for *Pinocchio*.
- `graph3_individual_brown.png`: Individual scatter plot and fitted regression line for *Brown Corpus*.
- `graph4_top20_words.png`: Side-by-side 3-panel horizontal bar chart visualizing the top 20 words for all three corpora.

### 3. Academic PDF Report (`results/reports/`)
- `ACL_Seminar_3_Report.pdf`: Multi-page formal academic report generated automatically using ReportLab. Includes:
  - Section 1: Introduction & Mathematical Foundations of Zipf's Law
  - Section 2: Corpus Selection & Metadata
  - Section 3: Preprocessing & Statistical Methodology
  - Section 4: Experimental Results (Tables 1 and 2, Figure 1)
  - Section 5: Comparative Analysis & Visualizations (Figures 2, 3, 4)
  - Section 6: Discussion (Adherence, Linguistic Typology, Limitations)
  - Section 7: Conclusions
  - Section 8: Academic References

### 4. Reproducibility Metadata (`results/reports/`)
- `experiment_metadata.json`: Machine-readable audit file containing execution timestamp, Python and package versions, exact URLs, token counts, preprocessing configs, and statistical results.

---

## Running Unit Tests

Execute the comprehensive test suite with `pytest`:

```powershell
pytest -v
```

### Test Coverage Highlights
- **Preprocessing**: Unicode NFC normalization, Italian accented characters preservation (`à, è, é, ì, ò, ù`), apostrophe preservation within words (`don't`, `l'ombra`, `c'era`, `un'altra`), punctuation removal, digit removal, stopword preservation, deterministic sampling.
- **Frequency**: Frequency counts, TTR calculation, sequential rank assignment starting at 1, deterministic tie-breaking (alphabetical ascending order for equal frequencies), cumulative frequency tracking, top N extraction, empty input handling.
- **Zipf Analysis**: Ideal power-law recovery ($s = 1.0$), non-unity exponent fitting ($s = 1.25$), full vs. top-100 comparisons, insufficient data protection.

---

## Reproducibility & Metadata

To ensure complete scientific reproducibility:
1. All random variations are eliminated; corpus sampling is deterministic.
2. The exact same regular expression tokenization is applied across all corpora.
3. Raw texts are locally cached in `data/raw/` to avoid network flakiness.
4. Exact execution metadata (OS, dependencies, timestamps, and parameters) is recorded in `results/reports/experiment_metadata.json`.

---

## References

- Collodi, C. (1883). *Le avventure di Pinocchio: Storia di un burattino*. Project Gutenberg eBook #52484.
- Francis, W. N., & Kučera, H. (1964). *A Standard Corpus of Present-Day Edited American English*. Brown University, Providence, RI.
- Mandelbrot, B. (1953). An informational theory of the statistical structure of language. *Communication Theory*, 486–502.
- NLTK Project. (2026). *Natural Language Toolkit Documentation and Brown Corpus Distribution*. https://www.nltk.org/
- Project Gutenberg. (2026). *Free eBooks by Project Gutenberg*. https://www.gutenberg.org/
- Shelley, M. W. (1818). *Frankenstein; or, The Modern Prometheus*. Project Gutenberg eBook #84.
- Zipf, G. K. (1935). *The Psycho-Biology of Language: An Introduction to Dynamic Philology*. Houghton Mifflin.
- Zipf, G. K. (1949). *Human Behavior and the Principle of Least Effort: An Introduction to Human Ecology*. Addison-Wesley.

