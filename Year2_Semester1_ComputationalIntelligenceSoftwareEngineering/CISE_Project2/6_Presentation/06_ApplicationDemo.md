# Slide 6 — Application Demo (CLI & Minimal 6-Page Streamlit GUI)

- **CLI Smoke Verification (`python -m bug_detector detect ...`):**
  - `verified_buggy.cs`: `ReadFirstLineLeak` -> `BUG` (`p=0.6518`), `UnsafeCastLength` -> `BUG` (`p=0.5655`), `GetUserNameLength` -> `UNCERTAIN` (`p=0.5241`).
  - `verified_fixed.cs`: all 3 fixed methods classified `UNCERTAIN` (`p=0.4503`–`0.4834`, zero false-positive `BUG`s).
  - `complex_clean_hard_negative.cs`: `BoundedLineProcessor.ParseValidEntries` -> `CLEAN` (`p=0.3865`).
  - `malformed_syntax.cs`: `ANALYSIS_ERROR` (`Detected 2 C# syntax error(s)`).
- **Streamlit UI (`streamlit run app.py`):** 6 pages (`Dashboard`, `Manual Detection`, `Results`, `Dataset Explorer`, `Model Training`, `Model Configuration`) with line-highlighted source inspection and Saabas tree-path local evidence.
