# Implementation Details – Information Retrieval System (Seminar 4)

## 1. Architectural Design

The IR system follows a layered, modular architecture:

```
[Raw CACM Files] (.all, .text)
       │
       ▼
[preprocessing.py] ──> Extracts (.I, .T, .W), lowercases, tokenizes [a-z]+
       │                Calculates top-7 stop words, applies filtering
       ▼
  [indexer.py]     ──> InvertedIndex: term -> [doc_id, ...] + TF tracking
       │                Serializes to 3_Output/inverted_index.json
       ▼
 [retrieval.py]    ──> Validates query, O(1) postings lookup,
       │                Deterministic ranking: (-TF, doc_id)
       ▼
 [evaluation.py]   ──> Precision@k (P@3, P@7), benchmarking via time.perf_counter_ns()
       │                Exports to results.json & test_results.csv
       ▼
[report_generator] ──> Results table (results.md), PDF report (seminar_report.pdf)
```

---

## 2. Module Specifications

### 2.1 Preprocessing (`1_Solution/src/preprocessing.py`)
- **Document Model**: `Document(doc_id, doc_num, title, abstract)` where `doc_id` follows canonical `CACM-{num:03d}` format (e.g. `CACM-001`, `CACM-015`, `CACM-1410`).
- **Tokenization**: Lowercases raw string and extracts alphabetic words via `re.findall(r'[a-z]+', text.lower())`.
- **Stop Words Discovery**: Calculates global token frequencies across all document titles and abstracts before filtering. The top 7 words are:
  1. `the` (11,014 occurrences)
  2. `of` (9,029 occurrences)
  3. `a` (6,017 occurrences)
  4. `and` (4,536 occurrences)
  5. `to` (3,770 occurrences)
  6. `is` (3,727 occurrences)
  7. `in` (3,446 occurrences)
- **Stemming / Lemmatization**: Explicitly omitted to maintain exact surface lexical forms.

### 2.2 Indexer (`1_Solution/src/indexer.py`)
- **Index Data Structure**: In-memory hash map `Dict[str, List[str]]` mapping each term to a sorted, deduplicated list of document IDs.
- **Term Frequency Tracking**: Maintains `term_doc_tf[term][doc_id]` to enable fast, exact TF ranking during retrieval without scanning document bodies.
- **Persistence**: Persists directly into `3_Output/inverted_index.json` matching the exact seminar schema:
```json
{
  "algorithm": ["CACM-001", "CACM-015"],
  "database": ["CACM-003", "CACM-012"]
}
```

### 2.3 Retrieval Engine (`1_Solution/src/retrieval.py`)
- **Query Processing**: Normalizes input query through the preprocessor. Rejects empty queries, pure stop words, and queries containing multiple words.
- **Index Lookup**: Retrieves matching postings in $O(1)$ time via `index.get_postings(query_term)`.
- **Deterministic Ranking**: Sorts candidate documents with:
  - Primary criterion: `doc_tfs[did]` descending.
  - Secondary criterion: `did` ascending (e.g., `CACM-001` < `CACM-015`).
- **Timing**: Measures execution time using high-resolution monotonic timer `time.perf_counter_ns()`.

### 2.4 Evaluation & Benchmarking (`1_Solution/src/evaluation.py`)
- **Precision@k**: Computes $P@k = \frac{|\text{Relevant} \cap \text{Retrieved}_{1..k}|}{k}$.
- **Denominator Convention**: Strictly $k$, adhering to standard Cranfield and TREC conventions.
- **Measurement Methodology**:
  - 50 initial warm-up iterations to prime caches and instruction pipelines.
  - 500 benchmarking iterations per test query.
  - Calculation and reporting of both mean and median query latencies.

---

## 3. Complexity Analysis

- **Document Parsing**: $O(N \cdot L)$ where $N$ is document count (3,204) and $L$ is average document length in characters.
- **Index Construction**: $O(T)$ where $T$ is total token count (172,680), executing in ~47 ms.
- **Query Lookup**: $O(1)$ dictionary lookup for postings list of size $D_t$.
- **Ranking**: $O(D_t \log D_t)$ for sorting matching postings by TF. For $D_t \le 1,194$, execution finishes in $< 0.05$ ms.
- **Memory Footprint**: Inverted index occupies ~1.85 MB in JSON and ~1.2 MB in active RAM.
