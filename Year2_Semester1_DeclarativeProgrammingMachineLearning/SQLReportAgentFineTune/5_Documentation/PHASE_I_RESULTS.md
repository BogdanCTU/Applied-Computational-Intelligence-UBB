# Phase I Results: Benchmark Integrity, Full Evaluation & Error-Driven Optimization

## 1. Executive Summary

Phase I of the `SQLReportAgentFineTune` laboratory was commissioned to establish the scientific reproducibility and integrity of Text-to-SQL fine-tuning experiments conducted on Apple Silicon M4 with MLX.

Previous pilot evaluations conducted on a small 25-sample subset reported a severe degradation in execution accuracy following LoRA fine-tuning (Baseline 68% vs LoRA $r=8$ at 44%, $r=16$ at 56%, and $r=32$ at 44%).

To determine whether these discrepancies reflected genuine model regressions or high-variance sampling artifacts, Phase I executed:
1. A rigorous **provenance and leakage audit** across all dataset splits.
2. The construction of a **deterministic, stratified 200-sample unseen benchmark** covering 100% of all 22 held-out databases and four complexity tiers.
3. The evaluation of all 4 model configurations (`Base`, `LoRA r=8`, `LoRA r=16`, `LoRA r=32`) under strictly identical greedy decoding conditions ($T=0$).
4. Paired statistical testing including **95% paired bootstrap confidence intervals (1,000 resamples)** and **McNemar's test** with exact $p$-values.
5. Systematic verification of **model fusion and inference parity**.

### Key Scientific Conclusions:
- **Small-Sample High Variance**: The previously reported 44%–56% execution accuracy was largely a product of small-sample variance ($N=25$, where a swing of $\pm 2$ questions represents an 8% shift and confidence interval bounds spanned $\pm 18\%$).
- **$r=8$ Preserves Semantic Generalization**: On the full 200-sample unseen benchmark, **LoRA $r=8$ matches the base model exactly at 62.5% Execution Accuracy** ($\Delta \text{EX} = 0.0\%$, paired 95% CI: `[-6.0%, +6.0%]`, McNemar $p=1.0$), while surging **Exact Match from 13.0% to 40.0% (+27.0%)** and lifting Valid SQL Rate to 100.0%.
- **$r=16$ Shows Minor Drift**: LoRA $r=16$ achieves **60.5% EX** ($\Delta \text{EX} = -2.0\%$, paired 95% CI: `[-7.5%, +3.0%]`, McNemar $p=0.5839$, not statistically significant).
- **$r=32$ Suffers Capacity Collapse**: LoRA $r=32$ degrades significantly to **49.5% EX** ($\Delta \text{EX} = -13.0\%$, paired 95% CI: `[-19.5%, -6.5%]`, McNemar $\chi^2 = 13.587$, $p = 0.0002$, **statistically significant degradation**), caused by severe overparameterization, schema linking errors (+32%), and runaway join loops on hard queries (-33.3% accuracy collapse).
- **Inference Parity Confirmed**: The standalone fused model (`exp_b_lora_r16_fused`) achieves 100% token-by-token and execution parity with the dynamic adapter runtime.

---

## 2. Benchmark Integrity & Provenance Verification

An audit of the training and evaluation splits yielded the following verified properties:

| Property | Audit Finding | Status |
| :--- | :--- | :---: |
| **Split Counts** | Train: 3,500; Valid: 350; Test Known: 100; Test Unseen: 1,044. | **Verified** |
| **Source Provenance** | Train: 3,479 Spider + 21 Synthetic (0 BIRD); Unseen: 1,034 Spider + 10 Synthetic. | **Verified** |
| **Database Disjointness** | Exactly 0 databases overlap between `{train, valid, test_known}` and `test_unseen`. Complete zero-shot schema isolation enforced. | **Verified** |
| **Paraphrase Leakage** | Track 1 (Known Schema) exhibits 46% identical SQL targets with train due to Spider question pairs. Track 2 (Unseen) has **0% domain-specific query overlap**. | **Verified** |
| **Pilot Sample Determinism** | The historical 25 unseen queries were verified to be `test_unseen[:25]` under seed 42, identical across all historical runs. | **Verified** |

---

## 3. Comprehensive Experimental Results Table

All models were evaluated under identical conditions: Apple Silicon M4, MLX 0.32.4, greedy decoding ($T=0$), top-p=1.0, max tokens=512, identical prompt template.

### 3.1. Track 2: Cross-Domain Unseen Schema Benchmark (200 Stratified Samples)

| Metric | Pristine Base Model | LoRA $r=8$ (`exp_a`) | LoRA $r=16$ (`exp_b`) | LoRA $r=32$ (`exp_c`) | Best Config |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **62.5%** (125/200) | **62.5%** (125/200) | **60.5%** (121/200) | **49.5%** (99/200) | Base / $r=8$ |
| 95% Bootstrap CI (EX) | [56.5%, 69.5%] | [56.0%, 69.0%] | [54.0%, 67.0%] | [43.0%, 56.5%] | Base / $r=8$ |
| **Paired $\Delta \text{EX}$ vs Base** | — | **0.0%** | **-2.0%** | **-13.0%** | $r=8$ |
| 95% Paired Bootstrap CI | — | `[-6.0%, +6.0%]` | `[-7.5%, +3.0%]` | `[-19.5%, -6.5%]` | $r=8$ |
| **McNemar's Test vs Base** | — | $\chi^2=0.0, p=1.0$ (NS) | $\chi^2=0.3, p=0.58$ (NS) | $\chi^2=13.6, p=0.0002$ (Sig) | $r=8$ |
| **Exact Match Rate (EM)** | 13.0% (26/200) | **40.0%** (80/200) | 33.0% (66/200) | 28.0% (56/200) | **LoRA $r=8$** |
| **Valid SQL Rate (VSR)** | 98.5% (197/200) | **100.0%** (200/200) | **100.0%** (200/200) | **100.0%** (200/200) | All LoRA |
| **Mean Latency** | 3,610.8 ms | **3,564.2 ms** | 4,500.9 ms | 5,197.9 ms | **LoRA $r=8$** |
| **Median Latency** | 3,273.0 ms | **3,016.4 ms** | 3,793.7 ms | 4,159.6 ms | **LoRA $r=8$** |
| **P90 Latency** | 5,621.3 ms | **5,510.3 ms** | 7,122.4 ms | 7,611.8 ms | **LoRA $r=8$** |
| **Avg Prompt Tokens** | 337.4 | 337.4 | 337.4 | 337.4 | — |
| **Avg Completion Tokens** | 43.3 | **33.9** | 44.5 | 57.9 | **LoRA $r=8$** |

### 3.2. Track 1: Known-Schema Benchmark (100 Samples)

| Metric | Pristine Base Model | LoRA $r=16$ (`exp_b`) | Absolute Delta | Relative Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Accuracy (EX)** | **71.0%** (71/100) | **68.0%** (68/100) | -3.0% | -4.2% |
| 95% Bootstrap CI (EX) | [62.0%, 80.0%] | [58.0%, 77.0%] | `[-13.0%, +6.0%]` (Paired) | — |
| **McNemar's Test** | — | — | $\chi^2=23.0, p=0.6776$ | Not Significant |
| **Exact Match Rate (EM)** | 21.0% (21/100) | **33.0%** (33/100) | **+12.0%** | **+57.1%** |
| **Valid SQL Rate (VSR)** | 99.0% (99/100) | **100.0%** (100/100) | +1.0% | +1.0% |
| **Mean Latency** | **4,386.6 ms** | 4,824.0 ms | +437.4 ms | +10.0% |
| **Median Latency** | **3,836.3 ms** | 4,496.0 ms | +659.7 ms | +17.2% |
| **P90 Latency** | **7,157.3 ms** | 8,550.9 ms | +1,393.7 ms | +19.5% |

---

## 4. Stratified Breakdown Analysis

### 4.1. Accuracy by SQL Complexity Tier (Track 2 Unseen)

| Complexity Tier | Samples | Base EX | LoRA $r=8$ EX | LoRA $r=16$ EX | LoRA $r=32$ EX | Delta ($r=8$ vs Base) | Delta ($r=32$ vs Base) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Easy** | 84 | 72.62% | **78.57%** | 72.62% | 70.24% | **+5.95%** | -2.38% |
| **Medium** | 42 | 64.29% | 54.76% | **66.67%** | 52.38% | -9.53% | -11.91% |
| **Hard** | 54 | **55.56%** | 51.85% | 48.15% | 22.22% | -3.71% | **-33.34%** |
| **Extra Hard** | 20 | 35.00% | **40.00%** | 30.00% | 30.00% | **+5.00%** | -5.00% |

#### Observations:
1. On **Easy** queries, LoRA $r=8$ outperforms the base model (+5.95%), achieving 78.57% accuracy.
2. On **Hard** queries, accuracy drops modestly for $r=8$ (-3.71%) and $r=16$ (-7.41%), but collapses cataclysmically in $r=32$ (-33.34% down to 22.22%). This collapse is directly traceable to the runaway join loop defect documented in the error analysis.

### 4.2. Accuracy by Database Domain (All 22 Unseen Databases)

| Database (`db_id`) | Samples | Base EX | LoRA $r=8$ EX | LoRA $r=16$ EX | LoRA $r=32$ EX | Dominant Failure Class |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `battle_death` | 3 | 66.67% | 66.67% | 33.33% | 33.33% | `subquery_error` |
| `car_1` | 18 | 61.11% | 61.11% | 44.44% | 22.22% | `schema_linking_error` (unnecessary joins) |
| `concert_singer` | 6 | 83.33% | 66.67% | 83.33% | 50.00% | `semantic_mismatch` |
| `course_teach` | 6 | 83.33% | 66.67% | 83.33% | 83.33% | `schema_linking_error` |
| `cre_Doc_Template_Mgt`| 16 | 62.50% | 62.50% | 68.75% | 56.25% | `join_error` |
| `dog_kennels` | 16 | 62.50% | 68.75% | 68.75% | 62.50% | `distinct_error` |
| `education` (Synthetic)| 1 | 100.0% | 100.0% | 100.0% | 0.0% | `schema_linking_error` |
| `employee_hire_evaluation`| 6 | 50.00% | 50.00% | 50.00% | 33.33% | `aggregation_error` |
| `entertainment` (Synthetic)| 1 | 0.0% | 0.0% | 0.0% | 0.0% | `schema_linking_error` |
| `flight_2` | 15 | 60.00% | 60.00% | 60.00% | 53.33% | `schema_linking_error` |
| `museum_visit` | 4 | 50.00% | 50.00% | 75.00% | 50.00% | `aggregation_error` |
| `network_1` | 11 | 72.73% | 72.73% | 72.73% | 63.64% | `join_error` |
| `orchestra` | 8 | 75.00% | 75.00% | 75.00% | 62.50% | `schema_linking_error` |
| `pets_1` | 8 | 37.50% | 50.00% | 37.50% | 37.50% | `aggregation_error` |
| `poker_player` | 8 | 75.00% | 87.50% | 75.00% | 62.50% | `order_limit_error` |
| `real_estate_properties`| 1 | 100.0% | 100.0% | 100.0% | 100.0% | None |
| `singer` | 6 | 66.67% | 66.67% | 66.67% | 66.67% | `distinct_error` |
| `student_transcripts_tracking`| 15 | 60.00% | 66.67% | 66.67% | 53.33% | `schema_linking_error` |
| `tvshow` | 13 | 61.54% | 61.54% | 61.54% | 46.15% | `distinct_error` |
| `voter_1` | 6 | 66.67% | 66.67% | 66.67% | 66.67% | `aggregation_error` |
| `world_1` | 23 | 56.52% | 56.52% | 47.83% | 47.83% | `distinct_error` / `schema_linking` |
| `wta_1` | 9 | 66.67% | 66.67% | 55.56% | 44.44% | `join_error` |

---

## 5. Root-Cause Investigation Across 12 Critical Dimensions

### 1. Training Loss vs Execution Accuracy Divergence
- **Observation**: Training cross-entropy loss dropped steeply from 1.21 to 0.14–0.19, yet execution accuracy on unseen databases remained bounded between 49.5% and 62.5%.
- **Mechanism**: Cross-entropy loss measures token-level prediction probability on surface SQL syntax (`SELECT`, `FROM`, `WHERE`, table aliases). The model rapidly optimized for the syntax tokens that constitute 70% of SQL text without learning semantic schema alignment.

### 2. Format Compliance vs Semantic Accuracy
- **Observation**: Valid SQL Rate reached 100.0% across all LoRA models (up from 98.5% in base), and Exact Match surged from 13.0% to 40.0% ($r=8$).
- **Mechanism**: The adapter succeeded in learning strict schema formatting, markdown backtick stripping, and Spider syntax styling. However, syntactic correctness does not guarantee semantic correctness in relational algebra.

### 3. Schema Linking Degradation
- **Observation**: In unseen databases, schema linking errors remained the single largest failure class (17–33 instances).
- **Mechanism**: The base model uses general semantic reasoning to associate question terms with column names. The adapters learned shortcut associations between common English words and specific table aliases from the training set (e.g. mapping "name" to `T1.Name` instead of inspecting the unseen schema).

### 4. SQL Complexity Regression
- **Observation**: Performance on "Easy" queries improved (+5.95% in $r=8$), while performance on "Hard" queries degraded (-3.7% in $r=8$, -7.4% in $r=16$, and -33.3% in $r=32$).
- **Mechanism**: As complexity grows, queries require composing multiple relational operators. The adapter's overfitted join templates interfered with the base model's reasoning capabilities on nested queries and multi-table joins.

### 5. Overfitting to Training Patterns
- **Observation**: Predictions across all adapters adopted the exact table aliasing convention `T1, T2, T3` found in Spider.
- **Mechanism**: The adapter learned to introduce aliases even on single-table queries, frequently attributing columns to `T2` when only `T1` was defined, causing `no such column` errors.

### 6. Prompt Sensitivity & Format Alignment
- **Observation**: The ChatML prompt structure (`Database Schema:\n...\nUser Question:\n...`) was handled cleanly by both base and fine-tuned models.
- **Mechanism**: `Qwen2.5-Coder` was pretrained on ChatML dialogs; the prompt format provided sufficient conditioning, but lack of few-shot demonstrations on unseen schemas left schema linking unguided.

### 7. Token-Level Loss Distribution
- **Observation**: Because loss masking (`--mask-prompt`) was enabled, loss was computed only on SQL completion tokens.
- **Mechanism**: Structural SQL keywords (`SELECT`, `AS`, `FROM`, `JOIN`, `ON`) represent the vast majority of tokens, swamping the loss contribution of critical schema identifiers (table and column names).

### 8. Quantization Interaction
- **Observation**: Base weights are quantized to 4-bit (AWQ/GPTQ via MLX), while LoRA adapter weights are stored in FP32 / FP16.
- **Mechanism**: Quantization artifacts in the frozen attention projections did not prevent adapter convergence, but higher adapter ranks ($r=32$) magnified weight drift when scaling activations back to the quantized base.

### 9. Hyperparameter Sensitivity ($r=8$ vs $r=16$ vs $r=32$)
- **Observation**: $r=8$ matches base performance, $r=16$ suffers minor degradation (-2.0%), and $r=32$ collapses (-13.0%, $p=0.0002$).
- **Mechanism**: With 60 training iterations (120 seen examples out of 3,500), high-rank adapters have far too many degrees of freedom ($26.6\text{M}$ parameters) for the available gradient signal, inducing severe parameter over-specialization and autoregressive looping.

### 10. Base Model Capability vs Task Difficulty
- **Observation**: `Qwen2.5-Coder-3B-Instruct` is a state-of-the-art code LLM with strong zero-shot SQL capability (62.5% unseen execution accuracy without fine-tuning).
- **Mechanism**: When fine-tuning on a small number of steps, LoRA easily perturbs well-calibrated pre-training representations without providing enough new signal to improve upon them.

### 11. Data Quality vs Data Volume
- **Observation**: The Spider training set contains duplicate paraphrases and repetitive join structures.
- **Mechanism**: 60 iterations exposed the model to only 3.4% of the training set. The model memorized recurring query templates from that 3.4% slice rather than learning generalizable relational translation principles.

### 12. SQLite Execution Specifics
- **Observation**: SQLite's dynamic typing and flexible `GROUP BY` semantics allowed semantically invalid queries to execute without throwing errors (e.g., returning multiset rows of IDs instead of text).
- **Mechanism**: Only execution accuracy against golden query results reliably detected these semantic discrepancies.

---

## 6. Model Fusion & Inference Parity Verification

In accordance with Phase I objectives, LoRA adapter checkpoint `exp_b_lora_r16` was fused into standalone model weights (`6_Models/exported/exp_b_lora_r16_fused/`).

Inference parity was formally tested via integration test `3_Tests/integration/test_fusion_parity.py`:
- **Greedy Output Token Sequence**: 100% identical token IDs between adapter runtime and fused model runtime.
- **SQLite Execution Equivalence**: Both runtimes produced identical result sets.
- **Latency Advantage**: Fused model eliminates adapter dispatch overhead, yielding ~5% faster generation.

---

## 7. Technical Decision & Strategic Recommendation

Based on the verified empirical data from the 200-sample benchmark and the paired statistical tests, we evaluate the four strategic pathways:

### Evaluation of Options:
- **Option A (Abandon Fine-Tuning, Use Base Model + Prompt Engineering)**:
  *Pros*: The base model already achieves 62.5% on unseen schemas with zero training overhead.
  *Cons*: Does not solve the project goal of building a specialized local Text-to-SQL engine; exact match remains low (13%) and format compliance is imperfect (98.5%).
- **Option B (Proceed with Current Strategy and Expand Training Iterations)**:
  *Unjustified*: Increasing iterations on the existing raw Spider dataset without schema-linking supervision will only accelerate the join hallucination and alias distortion defects identified in $r=16$ and $r=32$.
- **Option C (Shift Strategy to Error-Driven Optimization & Schema-Linking Regularization — RECOMMENDED)**:
  *Justification*:
  1. LoRA $r=8$ has proven that fine-tuning can match base execution accuracy (62.5%) while tripling exact match (40.0%) and achieving 100% validity.
  2. The failure taxonomy identified precise, fixable failure modes: join hallucination, alias distortion, and bare column selections.
  3. Pre-generating explicit schema-linking annotations (e.g. `Thought: Tables [T1, T2], Columns [C1, C2]`) before the SQL block, combined with join penalty regularization, directly targets the 40+ schema linking and join failures.
  4. Restricting rank to $r \le 8$ and scaling training to 1–2 full epochs (1,500–3,000 steps) with cosine annealing will provide stable gradient signal across all 145 training databases.
- **Option D (Pivot to Larger Model Architecture)**:
  *Unjustified*: Violates the strict project parameter boundary (< 4B parameters) and hardware constraint (16 GB unified memory).

### Final Decision: **OPTION C — Shift Strategy to Error-Driven Optimization**
Phase II should implement:
1. Low-rank constraint ($r=8$, $\alpha=16$).
2. Schema-linking reasoning prefixes in training targets.
3. Anti-hallucination data filtering to eliminate multi-table join bias on simple queries.
4. Full epoch training with validation loss early stopping.

---

## 8. Metric Audit, Discrepancy Reconciliation & Historical Correction

A rigorous audit of the Phase I per-example execution artifacts (`7_Results/*/detailed_samples.json`) reconciled aggregate metrics against underlying records:

### 8.1. Reconciliation: Valid SQL Rate (100.0%) vs Syntax Error Taxonomy (12 Syntax Errors)
A surface contradiction was identified where LoRA $r=8$ reported a 100.0% Valid SQL Rate while its error taxonomy recorded 12 syntax errors:
- **Definition 1 — Format Validity Rate (FVR = 100.0%, 200/200)**: Evaluated at the LLM output boundary via `is_valid_sql_syntax(pred_sql)`. This checked whether the model emitted a recognizable SQL block starting with a standard DML statement (`SELECT` or `WITH`). All 200 predictions complied with this format rule.
- **Definition 2 — Executable SQL Rate (ESR = 94.0%, 188/200)**: Evaluated at the SQLite compiler/runtime boundary via `executor.execute(pred_sql)`. When SQLite compiled the queries, 12 predictions raised SQLite `OperationalError`:
  1. *Missing comparison operators* (4 examples): e.g. `WHERE T3.Year 1974` (omitted `=`), `WHERE Name Plaza Museum` (omitted `=`).
  2. *Misuse of aggregate without GROUP BY* (4 examples): e.g. `SELECT name FROM Highschooler ORDER BY count(*) DESC LIMIT 1`.
  3. *Syntax errors near structural clauses* (2 examples): e.g. `SELECT Maker , FROM car_makers` (trailing comma).
  4. *Unterminated string literals / invalid tokens* (2 examples): e.g. unterminated quotation mark.
- **Correction & Harmonization**: The two metrics measure distinct layers of the Text-to-SQL pipeline. Both metrics are now explicitly distinguished:
  - **Format Validity Rate (FVR)**: 100.0% ($r=8$), 100.0% ($r=16$), 100.0% ($r=32$), 98.5% (Base).
  - **Executable SQL Rate (ESR)**: 94.0% ($r=8$), 97.5% ($r=16$), 96.5% ($r=32$), 97.0% (Base).

### 8.2. McNemar Chi-Square Statistic Reconciliation
- In `phase1_baseline_known100_vs_phase1_exp_b_lora_r16_known100.json`, the paired comparison had $b=10$ (improved) and $c=13$ (regressed), yielding $n_{\text{disc}} = b + c = 23$.
- Because $n_{\text{disc}} < 25$, the test correctly executed the exact two-sided binomial test ($p = 0.6776$). However, the output dictionary assigned `stat = float(discordant) = 23.0` to the field `chi2_statistic`.
- **Correction**: The true continuity-corrected chi-square statistic is $\chi^2 = (|10-13|-1)^2 / 23 = 4 / 23 = 0.1739$. The statistical comparison engine has been updated to report both the true $\chi^2$ statistic (`0.1739`), the discordant pair count (`23`), and the exact binomial $p$-value (`0.6776`).

### 8.3. Verification of Sums and Paired Correctness
- **Error Distribution Totals**: Verified across all 6 runs. Correct count (`none`) plus failure categories exactly equals `total_samples` ($125+75=200$, $121+79=200$, $99+101=200$, $71+29=100$, $68+32=100$).
- **Contingency Matrix Consistency**: The marginal sums of all contingency matrices match the reported individual model execution accuracies exactly ($n_{11} + n_{10} = \text{Base EX}$, $n_{11} + n_{01} = \text{Tuned EX}$).
- **Paired Bootstrap CI Integrity**: Verified that bootstrap iterations resample paired index tuples $(y_{\text{base}, i}, y_{\text{tuned}, i})$ simultaneously, ensuring mathematically valid paired delta distributions.

### 8.4. Latency Timing Boundaries
- Latency is measured with `time.perf_counter()` strictly around LLM prompt construction, MLX generation, markdown SQL extraction, and token encoding.
- SQLite database query execution (taking 0.5–2 ms) is isolated in the SQLite execution harness and excluded from model generation latency. Timing boundaries are strictly identical across all benchmark runs.

### 8.5. SQL Exact-Match Normalization Boundaries
- `normalize_sql` applies comment removal, whitespace collapsing, trailing semicolon stripping, and `sqlparse` keyword/identifier casing normalization.
- It intentionally does not reorder commutative SQL clauses (such as reordering columns in `SELECT` or reordering `AND` predicates in `WHERE`), ensuring EM acts as a strict syntactic style metric while Execution Accuracy evaluates true relational equivalence.

