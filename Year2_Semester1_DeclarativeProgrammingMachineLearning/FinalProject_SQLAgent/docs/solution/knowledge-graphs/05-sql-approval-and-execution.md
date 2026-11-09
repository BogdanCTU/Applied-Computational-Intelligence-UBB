# Knowledge Graph 05 — SQL Validation, Approval, and Execution Flow

## 1. Multi-Gate SQL Validation and Execution Flowchart

```mermaid
flowchart TD
    Start["Candidate SQL Query from LLM<br/>(prepare_sql_query or execute_readonly_sql)"]

    subgraph Gate1["Gate 1: Lexical & AST Token Validation (validate_readonly_sql)"]
        Strip["_strip_comments_and_literals()<br/>Remove --, /* */, '...', \"...\", `...`, [...]"]
        Single{"Single non-empty<br/>statement?"}
        Prefix{"Starts with<br/>SELECT or WITH?"}
        Keywords{"Contains any of 23<br/>_FORBIDDEN_KEYWORDS?"}
        SysTables{"References internal<br/>sqlite_* tables?"}
    end

    subgraph Gate2["Gate 2: Human-in-the-Loop Governance (When Executing)"]
        CheckCfg{"require_sql_approval<br/>== True?"}
        Modal["SqlApprovalDialog on Qt Main Thread<br/>(via WorkerSignals + queue.Queue)"]
        UserChoice{"User Approved?"}
    end

    subgraph Gate3["Gate 3: SQLite Engine Sandbox (execute_readonly_query)"]
        URI["connect_readonly()<br/>file:ecommerce.db?mode=ro + PRAGMA query_only=ON"]
        Auth["con.set_authorizer(_readonly_authorizer)<br/>Allow ONLY: SELECT(21), READ(20), FUNCTION(31), RECURSIVE(33)"]
        Watchdog["con.set_progress_handler(_progress_watchdog, 5000)<br/>Enforce query_timeout_s (120s) & cancel_event"]
        Fetch["cursor.fetchmany(max_rows + 1)<br/>Bounded memory fetch & truncation flag"]
    end

    RejectSQL["Raise UnsafeQueryError / InvalidQueryError<br/>(Return structured error for LLM self-correction)"]
    RejectUser["Return status='approval_denied'<br/>(Halt workflow immediately)"]
    Success["Return QueryExecutionResult<br/>(columns, full_rows, 50-row LLM preview, duration_ms)"]

    Start --> Strip --> Single
    Single -->|"No"| RejectSQL
    Single -->|"Yes"| Prefix
    Prefix -->|"No"| RejectSQL
    Prefix -->|"Yes"| Keywords
    Keywords -->|"Yes"| RejectSQL
    Keywords -->|"No"| SysTables
    SysTables -->|"Yes"| RejectSQL
    SysTables -->|"No"| CheckCfg

    CheckCfg -->|"False (Default)"| URI
    CheckCfg -->|"True"| Modal --> UserChoice
    UserChoice -->|"Rejected"| RejectUser
    UserChoice -->|"Approved"| URI

    URI --> Auth --> Watchdog --> Fetch --> Success
```

The flowchart above details the three major security and governance stages—Lexical/Token Validation, Human-in-the-Loop Approval, and SQLite Engine Sandboxing—that every SQL statement traverses before any rows are fetched.

---

## 2. Forbidden SQL Keywords & Authorizer Rules Reference

### A. Forbidden Keywords Blocked by `validate_readonly_sql()`
`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `REINDEX`, `ANALYZE`, `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`, `RELEASE`, `GRANT`, `REVOKE`, `MERGE`, `UPSERT`.

### B. SQLite VM Authorizer Whitelist (`_readonly_authorizer`)

| SQLite Action Code | Constant Name | Policy in `_readonly_authorizer` | Security Rationale |
| :--- | :--- | :--- | :--- |
| `21` | `sqlite3.SQLITE_SELECT` | `SQLITE_OK` | Permits `SELECT` query execution. |
| `20` | `sqlite3.SQLITE_READ` | `SQLITE_OK` (unless table starts with `sqlite_` and is not `sqlite_master`/`sqlite_schema`) | Permits reading user table columns while blocking internal SQLite shadow/stat tables. |
| `31` | `sqlite3.SQLITE_FUNCTION` | `SQLITE_OK` (unless function is `load_extension` or `fts3_tokenizer`) | Permits analytical functions (`SUM`, `AVG`, `STRFTIME`, `JULIANDAY`, `ROUND`) while blocking arbitrary shared-library code execution. |
| `33` | `SQLITE_RECURSIVE` | `SQLITE_OK` | Permits recursive Common Table Expressions (`WITH RECURSIVE`). |
| *All Other Action Codes* | `SQLITE_INSERT`, `SQLITE_UPDATE`, `SQLITE_DELETE`, `SQLITE_PRAGMA`, `SQLITE_ATTACH`, etc. | `SQLITE_DENY` | Enforces engine-level immutability even if a statement bypassed lexical checks. |
