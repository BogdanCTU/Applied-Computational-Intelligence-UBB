# Security Architecture & Data Privacy

This document outlines the security architecture, local-only execution boundaries, multi-layer SQL protections, tool constraints, and data privacy guarantees of the **Local Report SQL Agent**.

---

## 1. Security Architecture Summary

```
                      [ External Internet / Cloud Services ]
                                        │
                                        ▼
                                 [ BLOCKED / DISALLOWED ]
                                        │
========================================================================================
                          LOCAL MACHINE BOUNDARY (127.0.0.1)
========================================================================================

  1. Host & Network Isolation
     • OllamaClient validates host against LOCAL_HOSTS whitelist
     • MCP communication runs over anonymous stdio pipes (no open TCP ports)
     • Zero telemetry, third-party tracking, or cloud API calls
                                        │
                                        ▼
  2. Mandatory Human Approval Gate
     • Every execute_readonly_sql call pauses execution
     • Modal review dialog shows exact query text
     • Default action is Reject; Esc or closing window cancels query
                                        │
                                        ▼
  3. Pre-Execution SQL Inspection
     • Lexical & structural token validation (mcp_layer/tools/sql_tools.py)
     • Strictly allows SELECT and WITH ... SELECT
     • Blocks INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, ATTACH, DETACH
     • EXPLAIN QUERY PLAN validation catches syntax & schema errors
                                        │
                                        ▼
  4. SQLite Engine Read-Only Enforcement
     • Opened via URI: file:ecommerce.db?mode=ro
     • Enforces PRAGMA query_only = ON
     • Low-level SQLite C Authorizer hook denies write/admin action codes
                                        │
                                        ▼
  5. File System & Output Sanitization
     • Filename sanitization prevents path traversal (../, \, /)
     • Report files strictly confined to reports/
     • data/raw/ remains untouched and read-only
```

---

## 2. Local-Only Execution & Network Boundary

The application is explicitly designed to operate 100% offline with zero cloud transmission:

### A. Strict Localhost Hostname Enforcement
* **Whitelist**: `LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}`.
* **Validation**:
  In `config/settings.py` and `agent/ollama_client.py`:
  ```python
  parsed = urlparse(settings.host)
  hostname = (parsed.hostname or "").lower()
  if hostname not in LOCAL_HOSTS:
      raise OllamaConnectionError(
          f"Refusing to connect to remote host '{hostname}'. "
          "The application operates strictly locally for data privacy."
      )
  ```
* **Remote Host Rejection**: If a user attempts to configure a remote IP address or cloud domain in `settings.json` or the Settings dialog, validation fails immediately, preventing network transmission.

### B. Anonymous Stdio IPC Transport
The MCP server operates as an isolated child subprocess communicating through standard anonymous input/output streams (`sys.stdin` / `sys.stdout`). No local TCP ports or network sockets are opened for MCP communication, preventing local network sniffing or unauthorized remote access.

---

## 3. Defense-in-Depth SQL Security

The application employs four independent defensive barriers to guarantee that the database cannot be modified or corrupted by model hallucination or prompt injection:

### Layer 1: Lexical & Structural Token Validation (`mcp_layer/tools/sql_tools.py`)
Before any query reaches SQLite, `validate_and_prepare_sql` (using custom tokenizer `_tokenize_sql`) inspects the SQL text:
* **Token Scanning**: Scans for prohibited keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `BEGIN`, `COMMIT`, `EXPLAIN`).
* **Statement Whitelisting**: Verifies that the statement begins strictly with `SELECT` or `WITH`.
* **Single Statement Enforcement**: Blocks statement stacking (`SELECT 1; DROP TABLE users;`) by disallowing semicolons outside string literals.
* **Prohibited SQLite Functions**: Blocks dangerous SQLite extensions and administrative functions (e.g., `load_extension`, `writefile`, `readfile`).

### Layer 2: Pre-Execution Schema Validation
The `prepare_sql_query` tool runs `EXPLAIN QUERY PLAN <sql_query>` against SQLite using a read-only authorizer connection:
* Confirms the query is syntactically valid and all referenced tables and columns exist.
* Does **not** execute the query or fetch records.
* Provides structured feedback to the LLM if a table name was misspelled, enabling automated correction without executing invalid SQL.

### Layer 3: Engine-Level Read-Only Connection (`database/connection.py`)
When executing approved queries:
* **URI Read-Only Mode**: Opened using `file:<path>?mode=ro`. The SQLite C engine will refuse any write operation with `attempt to write a readonly database`.
* **Query-Only Pragma**: Calls `PRAGMA query_only = ON` immediately upon opening the connection.

### Layer 4: Low-Level SQLite C Authorizer Hook
Python's SQLite driver registers an authorizer callback (`sqlite3_set_authorizer`):
```python
def _authorizer_callback(action_code, param1, param2, db_name, trigger_name):
    if action_code in ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY
```
* **Allowed Actions**: `SQLITE_SELECT`, `SQLITE_READ`, `SQLITE_FUNCTION`.
* **Denied Actions**: `SQLITE_INSERT`, `SQLITE_UPDATE`, `SQLITE_DELETE`, `SQLITE_CREATE_TABLE`, `SQLITE_DROP_TABLE`, `SQLITE_ALTER_TABLE`, `SQLITE_PRAGMA`, `SQLITE_ATTACH`, `SQLITE_DETACH`.
* **Effect**: Even if a malicious or hallucinated statement bypasses the Python validator, SQLite's internal compilation engine blocks the operation at the C level before execution.

---

## 4. Mandatory Human-in-the-Loop Approval Gate

* **Enforcement by Policy**: Automated query execution is forbidden when `require_sql_approval` is enabled (default: `True`).
* **Modal Review Card**: The user is presented with the formatted query, natural language explanation, database name, and security indicators.
* **Safe Default**: The dialog focuses on **Reject** by default. Pressing `Esc`, clicking outside, or closing the dialog (`X`) immediately halts query execution.
* **Exact String Matching**: Approval is cached strictly against the exact query string. If the agent changes the query in any way, a new approval request is required.

---

## 5. Filesystem & Path Traversal Protections

### A. Filename Sanitization (`reporting/report_manager.py`)
User-provided report titles are sanitized before constructing filesystem paths:
```python
clean_name = re.sub(r"[^a-zA-Z0-9_\-\s]", "", title).strip()
clean_name = re.sub(r"\s+", "_", clean_name).lower()
```
Path traversal sequences (`../`, `..\\`, `/`, `\`) and null bytes (`\x00`) are stripped completely.

### B. Directory Containment Verification
The destination path is resolved and validated to ensure it resides strictly inside the configured `reports/` directory:
```python
target_path = resolve_path(filename, base=output_dir)
if not str(target_path).startswith(str(output_dir)):
    raise ReportSecurityError("Path traversal attempt detected outside reports directory.")
```

### C. Source Data Preservation
* The raw dataset directory `data/raw/` is treated strictly as read-only.
* The application database `data/ecommerce.db` is built in an isolated location.
* Database checksum integrity is verified using SHA-256 (`c5a5965e000becdb...`).

---

## 6. Resource Limits & Denial-of-Service Defense

To prevent runaway queries or memory exhaustion:
* **Row Cap**: Results are limited to `max_result_rows` (default: 1,000, capped at 100,000 max).
* **Execution Timeout**: Query execution is monitored against `query_timeout_s` (default: 120.0s). If exceeded, `connection.interrupt()` is called immediately to terminate the running statement.
* **Agent Iteration Cap**: Multi-turn tool execution is strictly capped at `max_iterations` (default: 8, max: 50) to prevent infinite loops.

---

## 7. Data Privacy & Confidentiality Guarantee

* **Zero External Telemetry**: No tracking, usage metrics, or error telemetry are transmitted to third-party servers.
* **Zero Cloud Inference**: All prompt tokens, database schemas, table sample rows, and analytical outputs remain on `localhost`.
* **Zero Persistent Secrets**: The application requires no API keys, tokens, or credit card configurations.

