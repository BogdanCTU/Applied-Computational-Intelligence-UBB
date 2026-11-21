# Seminar 4 – Solution Results Table

## Official Seminar Results Table

| Student | Time: index build and system answer time | Stop words (source – number of words) / Preprocessing | Index size vs corpus size / Vocabulary / Tokens | 3 Test data |
|---|---|---|---|---|
| Popa Bogdan-Stefan | **Index build time**:<br>49.76 ms<br><br>**Average answer time**:<br>0.0867 ms<br>*(Median: 0.0710 ms)* | **Stop words** (CACM top 7):<br>the, of, a, and, to, is, in<br><br>**Preprocessing**:<br>1. Lowercase<br>2. Alphabetic tokens [a-z]+<br>3. 7 most frequent stop words removed<br>4. No stemming / lemmatization | **Index size**: 1,851,078 B (1.77 MB)<br>**Corpus size**: 2,187,734 B (2.09 MB)<br>**Ratio**: 84.61%<br><br>**Vocabulary**: 8,791 terms<br>*(Before: 8,798)*<br><br>**Tokens**: 131,141<br>*(Before: 172,680)* | **database**:<br>&nbsp;&nbsp;Matching documents: 14<br>&nbsp;&nbsp;Top 3: CACM-2876, CACM-2816, CACM-2817<br>&nbsp;&nbsp;Top 7: CACM-2876, CACM-2816, CACM-2817, CACM-2882, CACM-2957, CACM-3087, CACM-3164<br>&nbsp;&nbsp;P@3: 1.0000<br>&nbsp;&nbsp;P@7: 1.0000<br><br>**compiler**:<br>&nbsp;&nbsp;Matching documents: 84<br>&nbsp;&nbsp;Top 3: CACM-1647, CACM-2534, CACM-1215<br>&nbsp;&nbsp;Top 7: CACM-1647, CACM-2534, CACM-1215, CACM-1496, CACM-2897, CACM-637, CACM-799<br>&nbsp;&nbsp;P@3: 1.0000<br>&nbsp;&nbsp;P@7: 1.0000<br><br>**algorithm**:<br>&nbsp;&nbsp;Matching documents: 1194<br>&nbsp;&nbsp;Top 3: CACM-2916, CACM-2030, CACM-2031<br>&nbsp;&nbsp;Top 7: CACM-2916, CACM-2030, CACM-2031, CACM-2657, CACM-2701, CACM-3069, CACM-1350<br>&nbsp;&nbsp;P@3: 1.0000<br>&nbsp;&nbsp;P@7: 1.0000 |

---

## Detailed Experimental Data

### 1. Stop Words Frequency Breakdown (Corpus Top 7)

| Rank | Term | Corpus Frequency | Cumulative % of All Corpus Tokens |
|---|---|---|---|
| 1 | `the` | 11,014 | 6.38% |
| 2 | `of` | 9,029 | 11.61% |
| 3 | `a` | 6,017 | 15.09% |
| 4 | `and` | 4,536 | 17.72% |
| 5 | `to` | 3,770 | 19.90% |
| 6 | `is` | 3,727 | 22.06% |
| 7 | `in` | 3,446 | 24.06% |

### 2. Comprehensive Test Data Analysis

#### Query: `database`
- **Total Matching Documents**: 14
- **Precision@3**: 1.0000 (3/3 relevant)
- **Precision@7**: 1.0000 (7/7 relevant)
- **Average Execution Time**: 0.0030 ms (Median: 0.0030 ms)

| Rank | Document ID | Term Frequency (TF) | Relevant (Topical Ground Truth) |
|---|---|---|---|
| 1 | `CACM-2876` | 7 | Yes |
| 2 | `CACM-2816` | 4 | Yes |
| 3 | `CACM-2817` | 3 | Yes |
| 4 | `CACM-2882` | 3 | Yes |
| 5 | `CACM-2957` | 3 | Yes |
| 6 | `CACM-3087` | 3 | Yes |
| 7 | `CACM-3164` | 2 | Yes |

#### Query: `compiler`
- **Total Matching Documents**: 84
- **Precision@3**: 1.0000 (3/3 relevant)
- **Precision@7**: 1.0000 (7/7 relevant)
- **Average Execution Time**: 0.0168 ms (Median: 0.0145 ms)

| Rank | Document ID | Term Frequency (TF) | Relevant (Topical Ground Truth) |
|---|---|---|---|
| 1 | `CACM-1647` | 5 | Yes |
| 2 | `CACM-2534` | 5 | Yes |
| 3 | `CACM-1215` | 4 | Yes |
| 4 | `CACM-1496` | 4 | Yes |
| 5 | `CACM-2897` | 4 | Yes |
| 6 | `CACM-637` | 4 | Yes |
| 7 | `CACM-799` | 4 | Yes |

#### Query: `algorithm`
- **Total Matching Documents**: 1194
- **Precision@3**: 1.0000 (3/3 relevant)
- **Precision@7**: 1.0000 (7/7 relevant)
- **Average Execution Time**: 0.2404 ms (Median: 0.1955 ms)

| Rank | Document ID | Term Frequency (TF) | Relevant (Topical Ground Truth) |
|---|---|---|---|
| 1 | `CACM-2916` | 8 | Yes |
| 2 | `CACM-2030` | 6 | Yes |
| 3 | `CACM-2031` | 6 | Yes |
| 4 | `CACM-2657` | 6 | Yes |
| 5 | `CACM-2701` | 6 | Yes |
| 6 | `CACM-3069` | 6 | Yes |
| 7 | `CACM-1350` | 5 | Yes |

### 3. Relevance Judgment Methodology
The evaluation applies transparent, evidence-based topical relevance:
- **`database`**: Evaluated against documents specifically discussing database management systems, relational databases, consistency locks, and disk file reorganization. Documents retrieved are cross-checked with CACM Benchmark Query 60 ('Hardware and software relating to database management systems').
- **`compiler`**: Evaluated against documents presenting concrete compiler implementations (WATFOR, PL/C, ALCOR, NELIAC, COBOL) and code generation algorithms.
- **`algorithm`**: Evaluated against documents presenting and mathematically analyzing concrete algorithms (string matching, parsing, flow analysis, GCD).

Denominator convention: When evaluating Precision@k, the denominator is strictly `k` (standard TREC / Cranfield evaluation paradigm).
