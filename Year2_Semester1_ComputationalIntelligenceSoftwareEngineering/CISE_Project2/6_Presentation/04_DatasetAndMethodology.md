# Slide 4 — Dataset Construction and Validation (`v5.0.0`)

| Source | BUG (`1`) | CLEAN (`0`) | Repos | Verification Status |
| --- | --- | --- | --- | --- |
| Microsoft `InferredBugs` | `1,383` | `1,368` | `536` | `static_analyzer_verified_fix` / `post_fix_verified` |
| GitHub Bug-Fix Commits | `881` | `887` | `56` | `commit_verified_bugfix` / `post_fix_verified` |
| Verified Hard Negatives | `0` | `756` | `45` | `test_backed_verified` |
| **Total Retained** | **`2,264`** | **`3,011`** | **`637`** | **`5,275` valid (`6,755` excluded)** |

- **1,334 cross-label hash conflicts** and **274 same-label duplicates** removed.
- **233 complex hard negatives** (`12` disjoint repos) isolated strictly in `hard_negative_test`.
