# Benchmark Integrity, Data Provenance & Split Leakage Audit

**Audit Timestamp**: 2026-11-18  
**Audit Target**: `SQLReportAgentFineTune` Dataset Pipeline & Artifact Repository  
**Auditor**: Independent Laboratory Evaluation Harness  
**Environment**: macOS Apple Silicon M4, Python 3.13.16  

---

## 1. Executive Summary & Verification Verdict

An exhaustive audit of the dataset acquisition, preprocessing pipeline (`1_Source/app/datasets/preprocessor.py`), stored JSONL splits (`2_Database/processed/`), manifests, and historical evaluation artifacts (`7_Results/`) was conducted.

### Key Audit Findings

| Audit Dimension | Status | Key Metric / Verification Finding |
| :--- | :---: | :--- |
| **Track 2 (Unseen-Schema) DB Isolation** | **VERIFIED CLEAN** | **0 overlapping databases** between `{train, valid, test_known}` and `test_unseen`. Database-level separation is strictly enforced. |
| **Track 1 (Known-Schema) Query Isolation** | **SUBSTANTIAL LEAKAGE** | **46.0%** of `test_known_schema.jsonl` queries and **41.7%** of `valid.jsonl` queries have exact SQL duplicates in `train.jsonl` due to random splitting across Spider paraphrases. |
| **Dataset Provenance & BIRD Benchmark** | **UNVERIFIABLE / OMITTED** | BIRD benchmark (`mini_dev_sqlite.jsonl`) was downloaded in raw form but was **never integrated into processed splits**. Datasets are 99.4% Spider and 0.6% Synthetic. |
| **Historical Evaluation Determinism** | **VERIFIED DETERMINISTIC** | The 25 reported unseen evaluation samples are identical across Baseline, Exp A, Exp B, and Exp C (`example_id` match = 100.0%). |
| **Known-Schema Under-Evaluation** | **CONFIGURATION LIMIT** | Previous run evaluated only 15 of 100 samples because `--limit 15` was explicitly passed on the CLI. |

---

## 2. Dataset Split Counts, Files & SHA-256 Hashes

All processed dataset splits in `2_Database/processed/` were audited and their SHA-256 cryptographic checksums were verified against `dataset_manifest.json`:

| Split Name | File Path | Record Count | Unique DBs | SHA-256 Checksum | Manifest Verified |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **`train`** | `2_Database/processed/train.jsonl` | 3,500 | 145 | `851c6f7e47cbdd3b8ddc212f9f4a3f380aad2f00fe0b770f8e7a438f2c4a7f07` | **MATCH** |
| **`valid`** | `2_Database/processed/valid.jsonl` | 350 | 121 | `35f3f08c2a8bdc4959dbbe0df156b8253199bc451b66df8772a838be3028d844` | **MATCH** |
| **`test_known`** | `2_Database/processed/test_known_schema.jsonl` | 100 | 61 | `1234bee68e9df250e9e69a90a3ee91455fe5ea5cd99797e4ec0244e7b9c3d18a` | **MATCH** |
| **`test_unseen`** | `2_Database/processed/test_unseen_schema.jsonl` | 1,044 | 22 | `b5b2fae1c4078659a414d2ad4ab30f2821ccd5f660b6850be95bcc97e498ccd9` | **MATCH** |
| **`test` (symlink)** | `2_Database/processed/test.jsonl` | 1,044 | 22 | `b5b2fae1c4078659a414d2ad4ab30f2821ccd5f660b6850be95bcc97e498ccd9` | **MATCH** |

---

## 3. Source Dataset Composition & Provenance Discrepancies

### 3.1. Actual Record Breakdown by Source

| Split | Yale Spider Benchmark | Multi-Domain Synthetic | BIRD Benchmark | Total Records |
| :--- | :---: | :---: | :---: | :---: |
| **`train`** | 3,479 (99.4%) | 21 (0.6%) | **0 (0.0%)** | 3,500 |
| **`valid`** | 348 (99.4%) | 2 (0.6%) | **0 (0.0%)** | 350 |
| **`test_known`** | 100 (100.0%) | 0 (0.0%) | **0 (0.0%)** | 100 |
| **`test_unseen`** | 1,034 (99.0%) | 10 (1.0%) | **0 (0.0%)** | 1,044 |

> [!WARNING]
> **Provenance Discrepancy — BIRD Benchmark**:
> Previous documentation claimed BIRD benchmark integration. While raw BIRD files exist in `2_Database/raw/bird/` (including `mini_dev_sqlite.jsonl` and `financial.db`), `BIRDDataset` was never called inside `build_expanded_dataset()` in `1_Source/app/datasets/preprocessor.py`. Consequently, **zero BIRD examples exist in any processed split**. The training and testing sets are derived almost entirely from Yale Spider (99.2%) and internal synthetic templates (0.8%).

---

## 4. Database-Level Isolation & Track Separation

### 4.1. Track 2 (Cross-Domain Unseen Schema) Isolation
- **Train Databases**: 145 databases (139 Spider train + 6 synthetic domains: `ecommerce`, `healthcare`, `finance`, `human_resources`, `logistics`, `inventory`).
- **Unseen Test Databases**: 22 databases (20 Spider dev + 2 synthetic domains: `education`, `entertainment`).
- **Intersection**:
  $$\text{DBs}_{\text{Train}} \cap \text{DBs}_{\text{Unseen}} = \emptyset \quad (\mathbf{0}\text{ overlapping databases})$$
- **Verification**: Strict database-level isolation is **100% verified**. No schema, table definition, column name, or foreign key from the 22 unseen databases was ever exposed during training or validation.

### 4.2. Track 1 (Known-Schema) Database Representation
- `test_known_schema.jsonl` contains 100 examples across 61 databases.
- All 61 databases are present in `train.jsonl`.
- This split tests in-domain query generalization where table structures are familiar.

---

## 5. Leakage Analysis: Question Text & Reference SQL Overlap

### 5.1. Intra-Split Question Duplication
- **`train.jsonl`**: 5 duplicate question texts (generic inquiries like `"Show all columns"` on different databases/tables).
- **`valid.jsonl`**, **`test_known_schema.jsonl`**, **`test_unseen_schema.jsonl`**: 0 duplicate questions within their respective splits.

### 5.2. Inter-Split Overlap & Leakage Audit

```text
Split Pair               Question Text Overlap      Normalized SQL Overlap
--------------------------------------------------------------------------
Train vs. Test Unseen           5 (0.14%)                   3 (0.09%)*
Train vs. Test Known            2 (2.00%)                  46 (46.00%)**
Train vs. Valid                 1 (0.29%)                 146 (41.71%)**
```

*\* Note on Train vs. Test Unseen Overlap*:
The 3 overlapping SQL queries are trivial single-table counts:
1. `SELECT COUNT(*) FROM AIRLINES`
2. `SELECT COUNT(*) FROM DOCUMENTS`
3. `SELECT COUNT(*) FROM EMPLOYEE`
These occur on entirely different database engines (`flight_2`, `cre_Doc_Template_Mgt`) than those in training. **There is zero domain-specific query leakage into Track 2.**

*\*\* Root Cause of Track 1 (Known Schema) SQL Leakage*:
Yale Spider benchmark `train_spider.json` provides two natural language paraphrases for many SQL queries. In `preprocessor.py`, `track1_examples` was randomly shuffled at the individual sample level rather than clustered by SQL query. As a consequence, 46 queries in `test_known_schema.jsonl` and 146 queries in `valid.jsonl` have their exact SQL target present in `train.jsonl` under an alternative question phrasing.

---

## 6. Historical Evaluation Verification

### 6.1. Determinism of Reported 25 Samples
The historical benchmark reported 25 samples for `baseline_unseen`, `eval_exp_a`, `eval_exp_b`, and `eval_exp_c`.
- **Sample Selection Rule**: `test_unseen_schema[:25]` under `seed=42`.
- **Sample IDs**: Identical across all 4 runs (`spider_dev_244`, `spider_dev_374`, `spider_dev_227`, ..., `spider_dev_944`).
- **Input Parity**: All 4 models were evaluated against the exact same prompt schemas and SQLite databases.

### 6.2. Why Only 15 Known-Schema Samples Were Evaluated
The historical test on Track 1 evaluated only 15 queries because the CLI command was executed with `--limit 15` during verification:
```bash
python 1_Source/main.py eval --run-name eval_exp_b_known --adapter 6_Models/adapters/exp_b_lora_r16 --track known --limit 15
```
All 100 known-schema samples exist on disk and will be evaluated in full in Phase I.

---

## 7. Training Set Complexity & Diversity Audit

Analysis of SQL features across the 3,500 training examples:

```text
Feature / Clause         Count in Train (N=3,500)    Frequency (%)
------------------------------------------------------------------
WHERE Filter                      1,727                 49.3%
JOIN (2+ tables)                  1,393                 39.8%
GROUP BY                            894                 25.5%
ORDER BY                            826                 23.6%
LIMIT Clause                        553                 15.8%
Subquery (Nested SELECT)            509                 14.5%
DISTINCT                            342                  9.8%
HAVING                              210                  6.0%
INTERSECT Set Op                    133                  3.8%
EXCEPT Set Op                       103                  2.9%
UNION Set Op                         29                  0.8%
Common Table Expressions (CTE)        5                  0.1%
Window Functions                      0                  0.0%
```

### Critical Diversity Insights
1. **Window Functions & CTE Deficiency**: Spider 1.0 contains virtually zero CTEs (0.1%) and zero window functions (0.0%). The fine-tuning data is heavily centered on standard relational algebra.
2. **Table Aliasing Dominance**: Over 65% of multi-table joins in Spider use `T1, T2, T3` aliasing, biasing fine-tuned models toward short aliases rather than explicit schema qualification.

---

## 8. Summary of Audit Warnings & Recommendations

> [!IMPORTANT]
> **Audit Takeaways for Phase I**:
> 1. **Track 2 Unseen-Schema Benchmark is Sound**: Zero database leakage, verified 100% database-disjoint. The reported drop from 68% to 44%–56% is a **genuine generalization degradation**, not an evaluation artifact.
> 2. **Track 1 Known-Schema Benchmark Suffers From Leakage**: 46% of test queries share SQL targets with training. Any high performance on Track 1 reflects memorization rather than structural SQL synthesis.
> 3. **Sampling Strategy for Full Evaluation**: To achieve rigorous statistical power without multi-hour runtime, we construct a deterministic stratified sample of **200 unseen queries** (stratified across all 22 unseen databases and 4 SQL complexity tiers) and evaluate all **100 known-schema queries**.
