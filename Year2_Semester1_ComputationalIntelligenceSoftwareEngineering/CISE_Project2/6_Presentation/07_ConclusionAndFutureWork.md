# Slide 7 — Conclusions, Limitations & Future Work

## Key Achievements

1. **106-Repository Corpus:** Expanded empirical training and evaluation data from `5` to **`106` distinct public C# repositories** (`5,711` classes, `28,972` commits, `16,161` SZZ blame traces, `0` missing feature values).
2. **Class & File Roslyn Architecture:** `.NET 9.0` Roslyn `v3.0.0` computes `40` isolated class/struct/record metrics (excluding nested type double-counting) and supports batch NDJSON streaming plus multi-class `.cs` file scoring.
3. **High-Precision Benchmark Target Exceeded:** Inner-CV thresholded Random Forest (`class_precision_champion_v3`, $\tau = 0.600$) achieves **`82.30%` Nested CV precision** and **`83.43%` untouched holdout precision** (`+13.82 pp` over legacy v2 holdout precision `69.61%`) with `61.99%` recall and `0.8449` ROC-AUC.
4. **Full Reproducibility & Compatibility:** Preserved all legacy method datasets, 4 historical models, and SQLite method rows untouched (`bug_detection_method_v2_archive.db`).

## Scientific Limitations & Threats to Validity

- **Open-World Negative Labels:** Candidate-clean classes lack recorded SZZ history in the `250`-commit window; this is not formal verification of zero bugs.
- **Short Semantic Bugs:** Compact classes (`median_loc = 48.0`) with subtle contract or logic errors account for False Negatives (`n=176`).
- **Base-Rate Prevalence Shift:** Under lower real-world defect rates (`10%–20%`), Bayesian PPV shifts (`38.50%–58.48%`), reinforcing human-in-the-loop triage.

## Future Directions

- Incorporate Git change churn, developer entropy, and inter-class dependency graph centrality alongside AST complexity.
- Extend Roslyn diagnostics with lightweight nullability/exception-flow semantic indicators.

---

*Previous:* [Live Application & Class/File Demo](06_ApplicationDemo.md)
