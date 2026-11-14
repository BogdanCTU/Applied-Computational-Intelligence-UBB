# Data Collection Methodology

## 1. GitHub Repository Discovery Criteria

Repositories are queried via the GitHub REST API (`GET /search/repositories`) and filtered automatically according to empirical software engineering standards:

- **Target Language**: `language:csharp`
- **Quality & Activity Thresholds**:
  - Minimum Stars: $\ge 100$ stars (filters out transient homework or trivial toys).
  - Minimum Size: $\ge 100$ KB (filters out empty skeleton projects).
  - Exclusion of Forks: `fork:false` avoids duplicate code bases across the dataset.
  - Exclusion of Archived Repositories: `archived:false` ensures active or maintainable software.
- **Licensing Considerations**:
  - We extract SPDX identifiers (e.g. `MIT`, `Apache-2.0`, `BSD-3-Clause`).
  - *Academic / Research Use*: Repository source code is analyzed strictly locally for metric calculation and defect identification. Original source code is never redistributed externally or commercialized.

## 2. Full-History Repository Cloning Architecture

- **Path Storage & Isolation**: Repositories are stored at `data/repositories/{owner}/{name}`.
- **Path Sanitization**: Repository names and owner slugs are checked against `^[a-zA-Z0-9_\-\.]+$` to strictly prevent directory traversal attacks (`..`).
- **Full History Guarantee**: Cloning is performed using `GitPython` without `--depth` constraints. SZZ defect analysis strictly requires complete commit histories and full `git blame` parent walks.
- **Idempotency & Interruption Recovery**:
  - If a clone operation is interrupted, the directory state is detected as invalid and cleared before recloning.
  - If a valid clone already exists, `clone_or_update()` executes `git fetch origin` and cleanly checks out the default branch.
  - If local uncommitted changes exist (`repo.is_dirty()`), update operations abort immediately to avoid destroying user modifications.

## 3. Commit History Extraction & Incremental Sync

Commit metadata is extracted by `CommitCollector` and stored in SQLite:

### Commit Metadata Schema (`commits` table)
- `commit_sha`: 40-character hexadecimal Git commit hash.
- `parent_sha` & `parent_shas`: Primary parent hash and comma-separated parent list to preserve merge commit topology.
- `author_name`, `author_email`, `committed_date`: Identity and timestamp of the author.
- `committer_date`: Timestamp of the commit application.
- `message`: Full commit message.
- `files_changed_count`: Number of files modified in the commit diff.
- `insertions` & `deletions`: Line additions and deletions.
- `modifies_csharp`: Binary flag (1 if any modified file ends with `.cs`, else 0).

### File Diff Level Schema (`commit_files` table)
- `commit_id`: Foreign key referencing parent commit.
- `file_path`: Path of modified file relative to repository root.
- `change_type`: Git status character (`A` = Added, `M` = Modified, `D` = Deleted, `R` = Renamed).
- `insertions`, `deletions`: Line counts per file.
- `is_csharp`: Flag identifying C# compilation units.

### Incremental Synchronization Strategy
1. The collector queries `SELECT commit_sha FROM commits WHERE repository_id = ?`.
2. Existing SHAs are placed in an in-memory hash set.
3. Commits reachable from `HEAD` are traversed. Any SHA already present is skipped.
4. New commits and their file diffs are persisted in transactions (batches of 100), ensuring interrupted operations can resume without duplicating records.

## 4. API Rate Limit & Error Handling

- **Authentication**: Supports unauthenticated requests (60 requests/hour) and GitHub Personal Access Tokens (5,000 requests/hour). Tokens are loaded from environment variables (`GITHUB_TOKEN`) or `.env` and are never logged.
- **Backoff & Retries**: Transient HTTP errors (500, 502, 503, 504) and network dropouts trigger exponential backoff with jitter up to 3 retries.
- **Rate Limit Exhaustion**: Headers `X-RateLimit-Remaining` and `X-RateLimit-Reset` are monitored. When limits are exceeded, a structured `RateLimitExceededError` informs the user of the exact reset epoch.
