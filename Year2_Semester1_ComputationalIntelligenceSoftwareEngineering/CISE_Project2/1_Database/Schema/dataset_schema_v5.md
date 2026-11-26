# Dataset Schema v5.0.0 (`csharp_bug_detection_v5.0.0`)

**Artifacts:**
- Parquet: `1_Database/Datasets/v5/csharp_bug_detection_v5.0.0.parquet`
- CSV: `1_Database/Datasets/v5/csharp_bug_detection_v5.0.0.csv`
- Audit Report: `1_Database/Datasets/v5/dataset_audit_report_v5.0.0.json`

## Label Definitions

- `1` (`BUG`): Method state immediately prior to a verified defect fix (InferSharp static-analyzer verified fix in InferredBugs, or commit-verified defect correction in GitHub history).
- `0` (`CLEAN`): Post-fix corrected method (`inferredbugs_post_fix`, `github_post_fix`) or test-backed verified complex correct method (`verified_hard_negative`).

## Required Metadata & Provenance Columns

| Column | Type | Description |
| --- | --- | --- |
| `sample_id` | string | Unique deterministic record identifier |
| `repository_id` | string | Canonical repository identifier (`inferredbugs/<repo>` or `<owner>/<repo>`) |
| `repository_url` | string | Upstream GitHub URL |
| `commit_sha` | string | Commit SHA (or `<fix_sha>^` for pre-fix state) |
| `parent_commit_sha` | string / null | Parent commit SHA for post-fix records |
| `file_path` | string | Repository-relative C# path |
| `class_name` | string | Enclosing type chain (`Outer.Inner`) |
| `method_name` | string | Extracted method or constructor name |
| `method_signature` | string | Full Roslyn signature |
| `source_code` | string | Raw C# method source |
| `label` | int (`0`/`1`) | Binary defect label (`BUG=1`, `CLEAN=0`) |
| `label_source` | string | Origin (`inferredbugs_infersharp`, `inferredbugs_post_fix`, `github_bugfix_commit`, `github_post_fix`, `verified_hard_negative`) |
| `verification_status` | string | Verification evidence level (`static_analyzer_verified_fix`, `post_fix_verified`, `commit_verified_bugfix`, `test_backed_verified`) |
| `bug_type` | string | Defect category (e.g., `DOTNET_RESOURCE_LEAK`, `NULL_DEREFERENCE`, `NONE`) |
| `bug_fix_reference` | string / null | Issue/PR/commit/test provenance reference |
| `source_hash` | string | SHA-256 of Roslyn-normalized method source |
| `collection_timestamp` | string | UTC ISO-8601 collection timestamp |
| `dataset_version` | string | Version tag (`v5.0.0`) |

Additional partitioning & structural columns: `normalized_source`, `structural_hash`, `pair_id`, `commit_timestamp`, `extraction_mode`, `split_partition` (`dev`, `independent_test`, `hard_negative_test`), `features_json`.
