# Slide 7 — Conclusions, Limitations & Future Work (`v4.0.0`)

## Key Achievements

1. **Top-200 Star-Ranked C# Corpus:** Discovered `500` repos, processed **`200` repositories** (`4,409`–`121,429` stars; `179` documented exclusions, `0` failed), yielding **`9,588` classes** (**`4,425` BUG** / **`5,163` CLEAN**) and **`7,361` verified SZZ localization records**.
2. **High-Precision Binary Classifier:** Random Forest champion (`class_bug_classifier_top200_v4`, $\tau = 0.520$) achieves **`79.47%` untouched holdout precision**, **`62.02%` recall**, **`69.67%` F1**, **`0.8180` ROC-AUC**, **`15.71%` FPR**, and **`37.98%` FNR** across `40` unseen repositories (`2,042` classes), beating `DummyClassifier` by `+27.54 pp` precision.
3. **Honest Localization & Partial-Analysis Guard:** Separate ML Method Localizer reaches **`68.64%` Top-3 class hit rate** (`0.6611` ROC-AUC), unseen exact lines are explicitly marked **`unavailable`**, and syntax-broken files never render `CLEAN`.

## Remaining Limitations & Future Work

- **Open-World Labels & Base-Rate Shift:** Expected PPV drops to `17.20%–49.67%` at `5%–20%` real-world defect rates -> triage aid, not automated blocker.
- **Structural Blind Spots:** Semantic bugs inside short classes drive false negatives (`37.98%` FNR); exact line localization remains unavailable statically on unseen code; pre-existing binary `.pptx`/`.docx`/`.pdf` defense files remain archival v2 snapshots.
- **Future Work:** Add git change-churn/ownership entropy and lightweight semantic dataflow/nullability indicators.

---

*Previous:* [Application Demo](06_ApplicationDemo.md)
