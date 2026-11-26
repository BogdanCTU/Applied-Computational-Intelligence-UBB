# Dataset Methodology — CISE Bug Detector v5.0.0

## 1. Corpus Overview (`v5.0.0`)

| Metric | Value |
| --- | --- |
| Total candidate records/commits inspected | `12,030` |
| Excluded records (with documented reasons) | `6,755` |
| Retained valid methods | `5,275` |
| `BUG` (`1`) methods | `2,264` (`42.92%`) |
| `CLEAN` (`0`) methods | `3,011` (`57.08%`) |
| Distinct repositories | `637` (`536` InferredBugs + `56` GitHub bug-fix + `45` hard-negative) |
| Missing required metadata fields | `0` across all `18` required columns |
| Export SHA-256 (`csharp_bug_detection_v5.0.0.csv`) | `923bec441606b003c85dc4d7f9333f080b0b1d30937417d4f1a0a7fe5a9da8a6` |

## 2. Data Sources & Verification Status

### 2.1 Primary Source: Microsoft InferredBugs (`inferredbugs/csharp`)
- **Repository:** `https://github.com/microsoft/InferredBugs` (MIT License), sparse-cloned (`225 MB`) to `1_Database/External/InferredBugs/`.
- **Raw Scale:** `641` C# repositories, `2,891` bug instances (`DOTNET_RESOURCE_LEAK`: `1,727`; `NULL_DEREFERENCE`: `911`; `NULLPTR_DEREFERENCE`: `159`; `PULSE_UNINITIALIZED_VALUE`: `77`; `THREAD_SAFETY_VIOLATION`: `15`; `STACK_VARIABLE_ADDRESS_ESCAPE`: `2`).
- **Validation Findings:** Inspection confirmed real records where `method_after.txt` refactored the body into a 1–2 line delegation stub (e.g., `AADConnectConfigDocumenter/1`), or pointed to unit tests/generated files. Strict Roslyn filtering retained `4,074` raw samples (`2,037` pairs) and logged `854` exclusions before cross-source deduplication.
- **Final Retained After Deduplication:** `1,383` `BUG` (`static_analyzer_verified_fix`) and `1,368` `CLEAN` (`post_fix_verified`) across `536` repositories.

### 2.2 Secondary Source: Verified GitHub Bug-Fix Pairs
- **Pipeline:** `2_SourceCode/bug_detector/collection/github_bugfix_collector.py` (dual-mode: local full-history GitHub clones in `1_Database/Repositories/` and rate-limit-aware GitHub REST API v3 client).
- **Filtering:** Positive correctness-fix commit message classifier (`fix`, `null`, `crash`, `leak`, `race`, `exception`, etc.) paired with explicit rejection of merge/revert (`74`), dependency updates (`1,225`), documentation (`709`), CI/build (`446`), pure refactoring (`346`), formatting (`120` message + `82` normalization-identical diffs), performance-only (`96`), unfocused (`693`), and multi-method ambiguous (`405`) changes.
- **Final Retained After Deduplication:** `881` `BUG` (`commit_verified_bugfix`) and `887` `CLEAN` (`post_fix_verified`) across `56` disjoint repositories.

### 2.3 Hard Negatives: Verified Complex Correct Methods
- **Pipeline:** `2_SourceCode/bug_detector/collection/hard_negative_collector.py`.
- **Criteria:** Production C# methods with `cyclomatic_complexity >= 4` and `logical_loc >= 12` whose enclosing class/method is referenced by repository unit tests (`*Test*.cs`) and whose file had zero bug-fix commits in the last `200` commits.
- **Final Retained After Deduplication:** `756` `CLEAN` (`test_backed_verified`) across `45` disjoint repositories, with `233` methods across `12` repositories strictly isolated in `hard_negative_test`.

## 3. Defect-Category & Verification Breakdown

| Category / Verification | Count |
| --- | --- |
| `NONE` (`CLEAN`) | `3,011` |
| `DOTNET_RESOURCE_LEAK` | `956` |
| `LOGIC_OR_CORRECTNESS_DEFECT` | `727` |
| `NULL_DEREFERENCE` | `360` |
| `NULLPTR_DEREFERENCE` | `67` |
| `EXCEPTION_HANDLING` | `58` |
| `RESOURCE_LEAK` | `36` |
| `PULSE_UNINITIALIZED_VALUE` | `22` |
| `CONCURRENCY_DEFECT` | `15` |
| `THREAD_SAFETY_VIOLATION` | `14` |
| `BOUNDARY_OR_INDEX_ERROR` | `9` |

| Verification Status | Count |
| --- | --- |
| `post_fix_verified` | `2,255` |
| `static_analyzer_verified_fix` | `1,383` |
| `commit_verified_bugfix` | `881` |
| `test_backed_verified` | `756` |

## 4. Deduplication & Contamination Protection

- Exact `source_hash` (SHA-256 of Roslyn-normalized method text) and `structural_hash` deduplication (`2_SourceCode/bug_detector/collection/deduplicator.py`):
  - **Cross-label hash conflicts (`1,334` excluded):** Whenever identical normalized or structural hashes appear under both `BUG=1` and `CLEAN=0`, **both** conflicting sides are removed.
  - **Same-label duplicates (`274` removed):** Redundant identical copies within the same label are collapsed to a single canonical sample.
