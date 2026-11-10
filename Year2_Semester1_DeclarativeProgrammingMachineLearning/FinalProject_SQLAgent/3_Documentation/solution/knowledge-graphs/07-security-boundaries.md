# Knowledge Graph 07 — Security Boundaries and Trust Zones

## 1. System Trust Zones and Security Enforcement Graph

```mermaid
flowchart TB
    subgraph ZoneUntrusted["Zone 1: Untrusted / Probabilistic Inputs"]
        UserPrompt["User Natural-Language Prompt"]
        LLMOutput["Local LLM Output (qwen3.5:4b)<br/>• Proposed Tool Calls & SQL<br/>• Free-text Markdown & <think> tags"]
        SkillFiles["External / Modified SKILL.md Files"]
    end

    subgraph ZoneSanitizers["Zone 2: Input & Boundary Sanitizers"]
        CtxSan["ContextBuilder.sanitize_text()<br/>• Strip ASCII control chars<br/>• Redact prompt injection tokens"]
        SkillScan["SkillManager._scan_security()<br/>• Block <script>, eval/exec, os.system<br/>• Block destructive SQL DDL/DML"]
        HTMLSan["MessageWidget._format_content()<br/>• Escape all HTML in user messages<br/>• Whitelist safe tags, block on* & javascript:"]
        MaskSan["events.mask_sensitive_data()<br/>• Redact password/token/secret/api_key"]
    end

    subgraph ZoneGovernance["Zone 3: Tool, Network & Approval Governance"]
        LoopbackGuard["Loopback Policy (LOCAL_HOSTS)<br/>• Allow only localhost, 127.0.0.1, ::1<br/>• httpx trust_env=False"]
        RegGate["ToolRegistry Validation<br/>• Verify tool in EXPECTED_MCP_TOOLS<br/>• Verify required_params"]
        HitlGate["SqlApprovalDialog (When require_sql_approval=True)<br/>• Cross-thread modal review<br/>• Default focus on 'Reject Execution'"]
    end

    subgraph ZoneSandbox["Zone 4: Deterministic Execution Sandboxes (MCP Subprocess)"]
        SQLSandbox["Read-Only SQLite Sandbox<br/>1. validate_readonly_sql() (23 forbidden keywords)<br/>2. URI file:ecommerce.db?mode=ro<br/>3. PRAGMA query_only = ON<br/>4. set_authorizer(_readonly_authorizer)<br/>5. set_progress_handler(5000) timeout/cancel"]
        MemIso["Memory DB Isolation Guard<br/>SQLiteMemoryRepository blocks<br/>pointing db_path to ecommerce.db"]
        PathSandbox["Report Path Sandbox (resolve_safe_report_path)<br/>1. Reject NUL bytes<br/>2. Strip /, \\, .., unsafe chars<br/>3. Prefix Windows reserved names<br/>4. Verify candidate.is_relative_to(base_dir)"]
    end

    subgraph ZoneProtected["Zone 5: Protected Local Assets"]
        EcomDB[("data/ecommerce.db<br/>(Immutable 499,385 Rows)")]
        MemDB[("data/agent_memory.db<br/>(Isolated Agent State)")]
        RepDir[("reports/<br/>(Confined Output Directory)")]
    end

    UserPrompt --> CtxSan & HTMLSan
    LLMOutput --> HTMLSan & MaskSan & RegGate
    SkillFiles --> SkillScan
    RegGate --> HitlGate --> SQLSandbox --> EcomDB
    RegGate --> PathSandbox --> RepDir
    LoopbackGuard -.->|"Confines HTTP"| LLMOutput
    MemIso --> MemDB
```

The trust-zone diagram above maps all five security zones—from untrusted/probabilistic inputs (Zone 1) through input sanitizers (Zone 2), governance gates (Zone 3), and execution sandboxes (Zone 4) to protected local storage assets (Zone 5).

---

## 2. Security Boundary Summary Table

| Boundary | Source Module | Enforced Invariant | Exception Raised on Violation |
| :--- | :--- | :--- | :--- |
| **Network Loopback Boundary** | `config/settings.py`, `agent/ollama_client.py` | `hostname in {"localhost", "127.0.0.1", "::1", "[::1]"}` and `trust_env=False` | `ValueError` / `OllamaSecurityError` |
| **Database Separation Boundary** | `memory/repository.py` | `agent_memory.db` path must never equal `data/ecommerce.db` | `ValueError("Critical security violation...")` |
| **SQL Lexical & Keyword Boundary** | `database/query_executor.py` | Single `SELECT`/`WITH` statement; zero `_FORBIDDEN_KEYWORDS`; zero `sqlite_*` tables | `UnsafeQueryError` / `InvalidQueryError` |
| **SQLite Engine Authorizer Boundary** | `database/query_executor.py` | `_readonly_authorizer` allows only action codes `21`, `20`, `31` (safe functions), `33` | `UnsafeQueryError("Statement blocked by read-only authorizer...")` |
| **Query Resource Boundary** | `database/query_executor.py` | `_progress_watchdog` every 5,000 opcodes (`120s` timeout) + `fetchmany(max_rows + 1)` | `QueryTimeoutError` / `QueryCancelledError` |
| **Report Filesystem Boundary** | `reporting/report_manager.py` | `candidate.resolve().is_relative_to(base_dir.resolve())`; no NUL bytes or `..` | `ReportSecurityError` |
| **Skill Injection Boundary** | `agent/skill_manager.py` | No `<script>`, `eval(`, `os.system`, destructive SQL, or prompt injection phrases | `SkillSecurityError` |

