# Slide 3 — System Architecture (`v4.0.0`)

## Layered Pipeline & Runtime Flow

1. **Top-200 Discovery & Mining (`2_SourceCode/Python/repositories/` & `services/mining/`):**
   - `GitHubClient.discover_top_csharp_repositories_by_stars()` (`sort="stars"&order="desc"`) -> `RepositoryManager` (full-history clone) -> `CommitCollector` (`46,053` commits) -> `BugFixDetector` -> `SZZAnalyzer` (`24,166` `git blame -w -M -C` traces).
2. **Roslyn Static Analyzer (`2_SourceCode/RoslynAnalyzer/Program.cs`):**
   - `.NET 9.0` CLI (`LanguageVersion.Latest`, `--batch-stdin`) extracts **40 isolated class metrics**, **26 method metrics**, nested method bounds, and `parsing_diagnostics` syntax errors.
3. **Persistence & Localization (`1_Database/SQLite/bug_detection.db`):**
   - Preserves `877` legacy method rows & v1/v2/v3 datasets, while adding **`class_bug_localizations`** (`7,361` verified historical method/line records), `class_observations` (`9,648`), and `class_features` (`9,648`).
4. **Classifier + Method Localizer + Streamlit UI (`2_SourceCode/Python/ml/` & `application/`):**
   - Authoritative `ModelManager.list_saved_models()` registry serves primary classifiers (hiding `method_localizer` from classifier selectors).
   - `BugPredictor` produces `BUG` / `CLEAN`, pairs verified SZZ or ML suspicious methods (`method_localizer_top200_v4.joblib`), and enforces partial-analysis safety.

---

*Previous:* [Problem & Objectives](02_ProblemAndObjectives.md) | *Next:* [Dataset & Methodology](04_DatasetAndMethodology.md)
