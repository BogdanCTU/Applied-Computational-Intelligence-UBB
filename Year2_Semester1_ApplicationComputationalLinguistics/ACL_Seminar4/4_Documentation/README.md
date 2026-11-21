# Information Retrieval System (Seminar 4 - Part 1)

**Course**: Applied Computational Linguistics  
**Institution**: Babeș-Bolyai University  
**Student**: Popa Bogdan-Stefan  
**Environment**: Python 3.13  

---

## 1. Overview

This project implements a complete Information Retrieval (IR) system over the CACM (Communications of the ACM) document collection of 3,204 computer science articles.

### Key Capabilities
- **CACM Record Parser**: Extracts document identifiers, titles, and abstracts from original `.all` files.
- **Deterministic Preprocessor**: Lowercases text, extracts alphabetic tokens (`[a-z]+`), automatically identifies the 7 most frequent corpus words as stop words, and removes them without stemming or lemmatization.
- **Inverted Index**: Maps unique vocabulary terms to unique document IDs (`{ "algorithm": ["CACM-001", "CACM-015"] }`), with persistent JSON serialization.
- **Single-Word Retrieval Engine**: Validates single-term queries, performs $O(1)$ postings lookup via the inverted index (no corpus scans), and ranks results deterministically by Term Frequency (TF) descending, with Document ID ascending as tie-breaker.
- **Cranfield-Style Evaluation**: Measures Precision@3 and Precision@7 against transparent ground-truth judgments.
- **High-Precision Benchmarking**: Evaluates index build time and query latency using `time.perf_counter_ns()`.

---

## 2. Project Structure

```text
.
├── 1_Solution/
│   ├── src/
│   │   ├── __init__.py          # Package initialization
│   │   ├── preprocessing.py     # Parser, tokenizer, stop-word filter
│   │   ├── indexer.py           # Inverted index construction & JSON I/O
│   │   ├── retrieval.py         # TF-ranked retrieval engine
│   │   ├── evaluation.py        # Precision@k & benchmark harness
│   │   ├── report_generator.py  # Markdown and PDF generation
│   │   └── main.py              # End-to-end execution pipeline
│   ├── data/
│   │   ├── raw/                 # Original cacm.all, qrels.text, query.text
│   │   └── processed/           # Processed docs, stop words, ground truth
│   └── config.py                # Global configurations and paths
│
├── 2_Tests/
│   ├── test_preprocessing.py    # Unit tests for parsing and tokenization
│   ├── test_indexer.py          # Unit tests for inverted index
│   ├── test_retrieval.py        # Unit tests for retrieval & ranking
│   └── test_evaluation.py       # Unit tests for precision calculation
│
├── 3_Output/
│   ├── results.json             # Structured query evaluation metrics
│   ├── test_results.csv         # Tabular CSV export of test queries
│   ├── performance.json         # Complete runtime & corpus statistics
│   └── inverted_index.json      # Serialized inverted index
│
├── 4_Documentation/
│   ├── README.md                # This project guide
│   ├── implementation.md        # Technical architecture documentation
│   ├── results.md               # Seminar solution table & analysis
│   └── seminar_report.pdf       # Compiled publication-grade PDF report
│
├── requirements.txt             # Python dependencies
└── run.py                       # Root convenience entrypoint
```

---

## 3. Quick Start & Execution

### Running the End-to-End Pipeline

Run using the local virtual environment:

```bash
.venv/bin/python 1_Solution/src/main.py
```

Or via the root runner:

```bash
.venv/bin/python run.py
```

### Running the Automated Test Suite

```bash
.venv/bin/pytest 2_Tests -v
```

Or via standard library unittest:

```bash
.venv/bin/python -m unittest discover -s 2_Tests -p "test_*.py" -v
```

---

## 4. Key Experimental Findings

- **Corpus**: 3,204 CACM documents, 2,187,734 bytes (2.09 MB).
- **Stop Words (7 most frequent)**: `the`, `of`, `a`, `and`, `to`, `is`, `in` (accounting for 41,539 tokens / 24.06% of the corpus).
- **Vocabulary**: 8,791 unique terms after stop-word removal (8,798 before).
- **Tokens**: 131,141 tokens after stop-word removal (172,680 before).
- **Index Build Time**: ~47 ms.
- **Query Answer Time**: ~0.015 - 0.035 ms per query.
- **Precision**: P@3 = 1.0000, P@7 = 1.0000 across `database`, `compiler`, and `algorithm`.
