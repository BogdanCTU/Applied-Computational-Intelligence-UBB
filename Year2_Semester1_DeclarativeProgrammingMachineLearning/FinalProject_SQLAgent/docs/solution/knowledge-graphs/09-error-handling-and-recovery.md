# Knowledge Graph 09 — Error Handling, Self-Correction, and Retries

## 1. Multi-Tier Error Recovery and Self-Correction State Machine

```mermaid
stateDiagram-v2
    [*] --> LLMInference : AgentOrchestrator calls OllamaClient.chat()

    state "Tier 1: Ollama HTTP Resilience" as Tier1 {
        LLMInference --> HTTPRetry : RemoteProtocolError (Runner Disconnect)
        HTTPRetry --> LLMInference : Exponential Backoff (1s, 2s - max 2 retries)
        LLMInference --> JSONFallback : HTTP 400 (Tool Schema Unsupported in 'auto' mode)
        JSONFallback --> LLMInference : Re-send without payload['tools']
    }

    LLMInference --> ParseResponse : HTTP 200 OK
    ParseResponse --> ToolDispatch : response.has_tool_calls == True
    ParseResponse --> RawSQLRecovery : No tool_call, but raw SELECT block in text

    state "Tier 2: Orchestrator Prompt Nudges" as Tier2 {
        RawSQLRecovery --> LLMInference : Nudge LLM to invoke execute_readonly_sql (max 2x)
        MissingReportNudge --> LLMInference : SQL executed + report requested, nudge generate_pdf_report
        MissingReportNudge --> FallbackReportSynth : Nudge exhausted -> _synthesize_fallback_report()
    }

    state "Tier 3: MCP & SQL Self-Correction" as Tier3 {
        ToolDispatch --> MCPRetry : BrokenPipe / EOFError on stdio pipe
        MCPRetry --> ToolDispatch : _reset_session() & respawn subprocess (max 2x)
        ToolDispatch --> SQLSelfCorrection : SQL syntax / column error (sql_retries < 3)
        SQLSelfCorrection --> LLMInference : Return exact SQLite error + schema hints in role='tool'
    }

    ToolDispatch --> ReportGenerated : generate_pdf_report / generate_csv_report succeeds
    FallbackReportSynth --> ReportGenerated : Deterministic report synthesized from _latest_sql_result
    ReportGenerated --> [*] : AgentRunResult(status="success")
```

The state machine diagram above illustrates the three concentric resilience tiers:
1. **Tier 1 (Ollama HTTP Resilience)**: Retries transient `RemoteProtocolError` socket drops with exponential backoff and automatically downgrades from native `tools` to JSON fallback mode if a model returns HTTP 400.
2. **Tier 2 (Orchestrator Prompt Nudges & Deterministic Synthesis)**: Recovers when a small model outputs raw SQL instead of a tool call (`_extract_raw_sql_from_text`) or forgets to invoke `generate_pdf_report` after fetching SQL rows (`_synthesize_fallback_report`).
3. **Tier 3 (MCP Reconnection & SQL Self-Correction)**: Automatically respawns broken MCP stdio sessions (`_reset_session`) and feeds SQLite syntax/column errors back to the model for up to `max_sql_retries = 3` self-correction turns.

---

## 2. Error Classification and Containment Table

| Error Class | Raised By | Contained By | User-Visible Outcome |
| :--- | :--- | :--- | :--- |
| `OllamaConnectionError` | `OllamaClient._post_chat_with_retry()` | `AgentOrchestrator.process_message()` → `MainWindow._on_agent_error()` | Friendly chat system message: *"Cannot connect to Ollama. Please ensure Ollama is running (`ollama serve`)."* |
| `OllamaModelNotFoundError` | `OllamaClient._post_chat_with_retry()` | `AgentOrchestrator.process_message()` | Actionable prompt to run `ollama pull qwen3.5:4b`. |
| `MCPConnectionError` / `MCPToolExecutionError` | `MCPClientManager` / `ToolHandler` | `_reset_session()` retry (2x); if fatal, surfaces in `AgentRunResult(status="error")` | Clear error message in chat + red `Error` card in `AgentActivityInspectorWidget`. |
| `UnsafeQueryError` / `InvalidQueryError` | `validate_readonly_sql()` / `execute_readonly_query()` | Caught in `mcp_layer/tools/sql_tools.py`, returned as `{"status": "error", "error": ...}` | LLM self-corrects SQL query on next iteration (up to `3` retries). |
| `QueryTimeoutError` | `_progress_watchdog()` in `database/query_executor.py` | Returned as structured tool error | Prevents runaway joins from hanging the app; LLM simplifies query. |
| `QueryCancelledError` / `asyncio.CancelledError` | `cancel_event.is_set()` in `AgentWorker` / `AgentOrchestrator` | Transitions task to `TaskStatus.CANCELLED` | Chat displays `"⏹️ Workflow was cancelled by user."` |
