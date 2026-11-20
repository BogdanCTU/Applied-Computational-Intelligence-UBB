# Feature Documentation — Experimental Evaluation, Ablation Engine & Telemetry (`src/evaluation/`)

## 1. Feature Purpose
The Experimental Evaluation subsystem computes standard OAEI ontology alignment metrics (**Precision**, **Recall**, **$F_1$-Score**) alongside information retrieval ranking metrics (**MRR**, **Hits@$1$**, **Hits@$3$**, **Hits@$5$**), full confusion-matrix error classifications (**TP**, **FP**, **FN**), and stage-level execution telemetry (latency, token usage, and LLM call counts). It also powers the **17-point multi-tier comparison comparator** and generates the publication-grade Matplotlib charts in `5_Results/figures/`.

---

## 2. Input Data
- **Predicted Alignments:** List of matched `(source_entity, target_entity, confidence_score)` tuples produced by the post-processing pipeline (`om_matches.csv` / `predictions.csv`).
- **Ranked Retrieval Candidates:** Top-$k$ candidate lists per query entity from lexical, syntactic, semantic, and hybrid reciprocal-rank stages.
- **Ground-Truth Reference Alignment:** [`3_Dataset/references/cmt-confof-reference.xml`](../../3_Dataset/references/cmt-confof-reference.xml) and [`3_Dataset/references/cmt-confof-true.csv`](../../3_Dataset/references/cmt-confof-true.csv) containing the **$16$ OAEI CMT–ConfOf ground-truth equivalences**.
- **Run Telemetry Logs:** Per-stage execution timestamps, prompt/completion token counters, and GGUF model metadata.

---

## 3. Processing Steps
1. **Entity Normalization & Equivalence Matching (`1_Source/evaluation/metrics.py`):**
   - Normalizes predicted `(source, target)` entity names using the identical snake_case conversion applied to reference alignments.
   - Partitions pairs into:
     - **True Positives ($\text{TP}$):** Predicted pairs present in the 16 ground-truth reference alignments.
     - **False Positives ($\text{FP}$):** Predicted pairs absent from the reference alignments.
     - **False Negatives ($\text{FN}$):** Reference alignments missed by the predictor.
2. **Alignment Quality Metrics:**
   $$\text{Precision} = \frac{|\text{TP}|}{|\text{TP}| + |\text{FP}|}, \quad \text{Recall} = \frac{|\text{TP}|}{|\text{TP}| + |\text{FN}|}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
3. **Retrieval Ranking Metrics (`MRR` and `Hits@k`):**
   - For each ground-truth pair $(e_s, e_t^*)$, locates the rank $\text{rank}(e_t^*)$ of the true target entity in the retriever's candidate list:
     $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}, \quad \text{Hits@}k = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}(\text{rank}_q \le k)$$
4. **17-Point Multi-Tier Comparison (`scripts/generate_phase5_comparisons.py`):**
   - Compares **Tier 1** (Paper GPT-4o & Llama-3-8B reference), **Tier 2** (Local historical `llama3:8b` & `gemma4:12b`), **Tier 3** (Compliant ≤4B adapted configuration: `qwen2.5:3b` + `nomic-embed-text:latest`, $F_1 = 0.6207$), and **Tier 4** (Phase 6 ablations `E1`–`E7`: determinism across 3 repetitions, embedding swap to `mxbai-embed-large`, prompt format ablation, threshold sweep $\tau \in \{0.85, 0.875, 0.90\}$, and `deepseek-r1:1.5b` reasoner evaluation).
5. **Scientific Figure Generation:**
   - Renders 6 high-resolution PNG charts (`300 DPI`) into [`5_Results/figures/`](../../5_Results/figures/).

---

## 4. Output Data
- **Per-Run Manifests (`manifest.json`):** Complete JSON record of hyperparameters, GGUF parameter counts, $\text{TP}/\text{FP}/\text{FN}$ lists, $P/R/F_1$, MRR, Hits@$k$, and stage latencies in [`5_Results/manifests/`](../../5_Results/manifests/).
- **Structured Comparison Matrices:**
  - [`5_Results/comparisons/phase5_17point_comparison.json`](../../5_Results/comparisons/phase5_17point_comparison.json) & `.md`
  - [`5_Results/comparisons/phase6_ablation_matrix.json`](../../5_Results/comparisons/phase6_ablation_matrix.json) & `.md`
  - [`5_Results/scientific_evaluation/SCIENTIFIC_EVALUATION_REPORT.md`](../../5_Results/scientific_evaluation/SCIENTIFIC_EVALUATION_REPORT.md)
- **Publication Figures (`5_Results/figures/`):**
  - `fig1_precision_recall_f1_tiers.png`
  - `fig2_f1_vs_parameter_count.png`
  - `fig3_latency_stage_breakdown.png`
  - `fig4_error_profile_tp_fp_fn.png`
  - `fig5_retrieval_mrr_hits_comparison.png`
  - `fig6_phase6_ablation_summary.png`

---

## 5. Main Implementation Files
- [`1_Source/evaluation/metrics.py`](../../1_Source/evaluation/metrics.py) — Precision, Recall, $F_1$, MRR, Hits@$k$, and TP/FP/FN computation.
- [`scripts/generate_phase5_comparisons.py`](../../scripts/generate_phase5_comparisons.py) — 17-point comparator and Matplotlib figure generator.
- [`scripts/run_phase6_ablations.py`](../../scripts/run_phase6_ablations.py) — Automated runner for the Phase 6 experimental sweep (`E1`–`E7`).

---

## 6. Configuration Options
- `SIMILARITY_THRESHOLD` ($\tau$): Swept across $\{0.50, 0.70, 0.85, 0.875, 0.90\}$.
- `TOP_K` ($k$): Default `3` (`Hits@1`, `Hits@3`, `Hits@5` tracked).

---

## 7. Dependencies
- `numpy` (`2.2.4`), `pandas` (`2.2.3`), `matplotlib` (`3.11.2`).

---

## 8. Relevant Tests
- [`2_Tests/unit/test_Metrics.py`](../../2_Tests/unit/test_Metrics.py) — Verifies exact Precision, Recall, $F_1$, MRR, and Hits@$k$ calculations against known reference alignments.
- [`2_Tests/integration/test_algorithmic_parity.py`](../../2_Tests/integration/test_algorithmic_parity.py) — Verifies 100% deterministic parity of the evaluation formulas against the upstream reference implementation.

---

## 9. Known Limitations
- The primary OAEI benchmark evaluated in this replication is the **CMT–ConfOf** conference track ($16$ ground-truth equivalence pairs across $162 \times 162$ classes and $206 \times 258$ properties). Extending evaluation to additional OAEI tracks requires placing their OWL/RDF `.xml` files in `3_Dataset/original/` and their gold-standard reference alignments in `3_Dataset/references/`.
