# Appendix D — Configuration Reference

## 1. Configuration File & Precedence

- **Default Settings File**: `settings.json` (in project root during development, or `~/Library/Application Support/ReportSQLAgent/settings.json` on macOS / `%APPDATA%\ReportSQLAgent\settings.json` on Windows when frozen).
- **Environment Variable Template**: `.env.example` (loaded via `config/settings.py` `ENV_OVERRIDES`).
- **Precedence Order**: Dataclass defaults (`config/settings.py`) < `settings.json` < `REPORT_AGENT_*` environment variables.

---

## 2. Complete `settings.json` Schema Example

```json
{
  "ollama": {
    "host": "http://localhost:11434",
    "model": "qwen3.5:4b",
    "temperature": 0.1,
    "top_p": 0.9,
    "num_ctx": 131072,
    "request_timeout_s": 600.0,
    "keep_alive": "10m",
    "tool_mode": "auto"
  },
  "database": {
    "path": "data/ecommerce.db",
    "max_result_rows": 1000,
    "llm_preview_rows": 50,
    "query_timeout_s": 120.0
  },
  "agent": {
    "max_iterations": 20,
    "max_tool_calls": 40,
    "max_sql_retries": 3,
    "max_history_messages": 30,
    "require_sql_approval": false,
    "agent_context_window": 131072
  },
  "reports": {
    "output_dir": "reports",
    "page_size": "A4",
    "max_pdf_rows": 5000,
    "max_report_rows": 100000,
    "include_sql_in_pdf": false
  },
  "logging": {
    "level": "INFO",
    "directory": "logs",
    "file_name": "report_agent.log"
  }
}
```

---

## 3. Environment Variable Overrides (`ENV_OVERRIDES`)

| Environment Variable | Target `(section, field)` | Parser / Coercion | Default |
| :--- | :--- | :--- | :--- |
| `REPORT_AGENT_OLLAMA_HOST` | `("ollama", "host")` | `str` (must be in `LOCAL_HOSTS`) | `"http://localhost:11434"` |
| `REPORT_AGENT_OLLAMA_MODEL` | `("ollama", "model")` | `str` | `"qwen3.5:4b"` |
| `REPORT_AGENT_OLLAMA_TIMEOUT_S` | `("ollama", "request_timeout_s")` | `float` (`> 0`) | `600.0` |
| `REPORT_AGENT_OLLAMA_TEMPERATURE` | `("ollama", "temperature")` | `float` | `0.1` |
| `REPORT_AGENT_DB_PATH` | `("database", "path")` | `str` | `"data/ecommerce.db"` |
| `REPORT_AGENT_MAX_ROWS` | `("database", "max_result_rows")` | `int` (`>= 1`) | `1000` |
| `REPORT_AGENT_QUERY_TIMEOUT_S` | `("database", "query_timeout_s")` | `float` (`> 0`) | `120.0` |
| `REPORT_AGENT_MAX_ITERATIONS` | `("agent", "max_iterations")` | `int` (`>= 1`) | `20` |
| `REPORT_AGENT_REQUIRE_SQL_APPROVAL` | `("agent", "require_sql_approval")` | `_parse_bool` (`1/true/yes/on` vs `0/false/no/off`) | `False` |
| `REPORT_AGENT_CONTEXT_WINDOW` | `("agent", "agent_context_window")` | `_parse_context_window` (`32768`/`32k`, `65536`/`64k`, `131072`/`128k`, `262144`/`256k`) | `131072` |
| `REPORT_AGENT_OUTPUT_DIR` | `("reports", "output_dir")` | `str` | `"reports"` |
| `REPORT_AGENT_PAGE_SIZE` | `("reports", "page_size")` | `str` (`"A4"` or `"LETTER"`) | `"A4"` |
| `REPORT_AGENT_MAX_PDF_ROWS` | `("reports", "max_pdf_rows")` | `int` (`>= 1`) | `5000` |
| `REPORT_AGENT_MAX_CSV_ROWS` | `("reports", "max_report_rows")` | `int` (`>= 1`) | `100000` |
| `REPORT_AGENT_INCLUDE_SQL_IN_PDF` | `("reports", "include_sql_in_pdf")` | `_parse_bool` | `False` |
| `REPORT_AGENT_LOG_LEVEL` | `("logging", "level")` | `str` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `"INFO"` |

