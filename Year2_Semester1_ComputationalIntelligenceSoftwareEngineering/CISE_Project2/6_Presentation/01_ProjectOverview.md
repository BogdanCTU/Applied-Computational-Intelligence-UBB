# Slide 1 — Project Overview: C# Source-Code Bug Detection (`v5.0.0`)

- **Goal:** Classify individual C# methods as `BUG`, `CLEAN`, or `UNCERTAIN` directly from source code using a trained `RandomForestClassifier`.
- **Architectural Reset:** Replaces legacy `v1`–`v4` defect-proneness / SZZ risk-scoring code (archived in `0_LegacyArchive_v1_v4/`).
- **Stack:** `.NET 9.0` Microsoft Roslyn (`Microsoft.CodeAnalysis.CSharp 4.12.0`) + Python `3.13` (`scikit-learn 1.9.1`, `pydantic 2.14`, `SQLite 3` WAL, `Streamlit 1.67`).
- **Artifacts:** `1_Database/SQLite/bug_detector_v5.db`, `1_Database/Datasets/v5/csharp_bug_detection_v5.0.0.parquet`, `4_AppBuild/Models/v5/rf_I_v5.0.0_20261126_150933/`.
