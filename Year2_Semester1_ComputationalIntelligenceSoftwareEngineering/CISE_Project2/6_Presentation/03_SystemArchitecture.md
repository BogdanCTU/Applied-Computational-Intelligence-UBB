# Slide 3 — System Architecture (`v3.0.0`)

## Layered Pipeline & Runtime Flow

1. **Data Collection & Mining Layer (`2_SourceCode/Python/repositories/` & `services/mining/`):**
   - `GitHubClient` (star-stratified paginated discovery) $\rightarrow$ `RepositoryManager` (full-history clone & timeout safety) $\rightarrow$ `CommitCollector` (fast `git log --numstat`) $\rightarrow$ `BugFixDetector(..., strict_mode=True)` $\rightarrow$ `SZZAnalyzer` (cached `git blame -w -M -C`).
2. **Roslyn `v3.0.0` Static Analyzer (`2_SourceCode/RoslynAnalyzer/Program.cs`):**
   - `.NET 9.0` CLI (`LanguageVersion.Latest`), supports single JSON + `--batch-stdin` NDJSON streaming.
   - Extracts **40 isolated class metrics** (`GetTypeOwnedNodes<T>` excluding nested types, nested LOC subtracted) alongside legacy **26 method metrics**.
3. **Persistence Layer (`1_Database/SQLite/bug_detection.db`):**
   - Non-destructive schema preserving `877` legacy method `observations` & Datasets `1–2`, plus new `class_observations` (`5,745`), `class_features` (`5,745`), `file_observations` (`5,260`), `dataset_class_observations` (`5,711`), and `repository_collection_runs`.
4. **ML Engine & Streamlit App (`2_SourceCode/Python/ml/` & `application/pages/`):**
   - Authoritative `ModelManager.list_saved_models()` registry (`12` models: `8` class + `4` method) serving all `8` Streamlit pages.
   - `BugPredictor` scores single classes and multi-class `.cs` files via `predict_proba() >= stored_decision_threshold`.

---

*Previous:* [Problem & Objectives](02_ProblemAndObjectives.md) | *Next:* [Dataset & Methodology](04_DatasetAndMethodology.md)
