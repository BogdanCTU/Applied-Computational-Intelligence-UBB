# Agent Intelligence Layer

This document details the intermediate intelligence architecture implemented between the user, the local Ollama LLM (`qwen3.5:4b`), and MCP tools in the **Local Report SQL Agent**.

---

## 1. Architectural Overview

The Agent Intelligence Layer provides structured task planning, persistent working/episodic/semantic memory, checkpointing and recovery, domain skills, and context construction under small local LLM context budgets.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User & Desktop GUI (PySide6)                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Agent Intelligence Layer                        │
│                                                                        │
│  Phase 1: Task Models & Task Manager (task_models.py, task_manager.py) │
│  Phase 2: Persistent SQLite Memory (data/agent_memory.db, WAL mode)    │
│  Phase 3: Checkpointing & Recovery (checkpoint_manager.py)             │
│  Phase 4: Domain Skill System (skills/, skill_manager.py)              │
│  Phase 5: Context Builder (context_builder.py, context_models.py)      │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
      HTTP / JSON   │                                │ Tool Execution
                    ▼                                ▼
┌───────────────────────────────┐  ┌─────────────────────────────────────┐
│    Local Ollama (qwen3.5:4b)  │  │        MCP Server Subprocess        │
└───────────────────────────────┘  └─────────────────────────────────────┘
```

---

## 2. Phase 5: Context Builder

### Architectural Decision
Phase 5 implements **exactly one architectural component**:
- [`agent/context_builder.py`](file:///Users/stefanapopa/Documents/8%29%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/context_builder.py) (`ContextBuilder`)
- Supporting models in [`agent/context_models.py`](file:///Users/stefanapopa/Documents/8%29%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/agent/context_models.py)

**No separate Token Budget Manager or subsystem is introduced.** All token estimation, budget allocation, section prioritization, and context-window protections are internal private responsibilities of `ContextBuilder`.

### Token Budgeting & Window Allocation
- **Token Estimator:** Reuses the deterministic `estimate_tokens()` function from `agent.skill_models` (~3.8 chars/token) with zero duplication.
- **Context Space Equation:**
  $$\text{Available Input Budget} = \text{effective\_context\_window} - \text{reserved\_output\_tokens} - \text{safety\_margin\_tokens}$$
  - Default: `agent_context_window = 131072` (128K default), `reserved_output_tokens = 1024`, `safety_margin_tokens = 256` $\rightarrow$ 129,792 available input tokens.
- **Supported Window Tiers:** 32K (`32768`), 64K (`65536`), 128K (`131072` — Default), and 256K (`262144`).
- **Section Priorities:**
  - `MANDATORY` (100): System operating boundaries, stage instructions, sanitized `<user_request>`. Must fit; raises `ContextBudgetExceededError` if exceeded.
  - `HIGH` (75): Stage domain skills, relevant table schemas.
  - `MEDIUM` (50): Task/step state, checkpoints, working memory, recent tool results, recent conversation history.
  - `LOW` (25): Semantic domain facts, completed step history, older conversation history.
- **No Silent Truncation:** If an optional section cannot fit in the remaining budget, it is safely excluded in whole and documented in `ContextBuildReport.excluded_sections`. Tool outputs are bounded with an explicit notice (`... [truncated for context budget: N characters omitted]`).

---

## 3. Phase 6: Configurable Agent Context Window & Integration

### Centralized Authority & Configuration
- **Authoritative Configuration:** `settings.agent.agent_context_window: int = 131072` in `config/settings.py`.
- **Validation:** Enforces `ALLOWED_CONTEXT_WINDOWS = (32768, 65536, 131072, 262144)`.
- **Automatic Migration:** Legacy configuration files without `agent_context_window` automatically receive the 128K default.
- **Live Reconfiguration:** Desktop settings UI exposes 32K, 64K, 128K (Default), and 256K. Changes take effect on subsequent requests without requiring an application restart.

### Ollama Model Capability Validation
Before executing requests, `agent/ollama_client.py` inspects `/api/show` model metadata:
- **Compatible:** If model context $\ge$ configured window, the configured window is used.
- **Incompatible:** If model context $<$ configured window, execution is halted with `ModelContextIncompatibleError`. The application never silently pretends a smaller context is larger.
- **Unknown:** If metadata cannot be resolved, safe fallback policy of 32K (`32768`) is applied.
- **Context Size Rejection:** Ollama runtime context rejections or OOM errors surface as `OllamaContextSizeRejectedError`.

### Runtime Observability
The PySide6 desktop Activity Inspector records:
- Configured vs effective context window.
- Model capability validation status.
- Token breakdown (estimated input, reserved output, safety margin).
- Included and excluded context categories with detailed reasons.


### Stage-Specific Context Profiles
ContextBuilder constructs tailored profiles for 8 execution stages:
1. `REQUEST_PLANNING`: Planning guidelines, schema summary, user request.
2. `SCHEMA_DISCOVERY`: Schema introspection rules, table list, SQL generation skill.
3. `SQL_GENERATION`: Read-only rules, targeted schema, KPI definitions, SQL generation skill.
4. `SQL_VALIDATION`: Validation checklist, proposed SQL query, referenced schema.
5. `DATA_ANALYSIS`: E-commerce analysis skill, dataset statistics/sample.
6. `CHART_PLANNING`: Executive report design skill, chart selection matrix, dataset profile.
7. `REPORT_GENERATION`: Report design & data validation skills, reconciliation checklist, PDF/CSV parameters.
8. `FINAL_RESPONSE`: Synthesis instructions, task state, generated artifact pointers.

### Security and Untrusted-Data Handling
- User inputs are wrapped in `<user_request>...</user_request>` boundaries.
- Attempted role spoofing headers (`System:`, `Assistant:`, `### SYSTEM INSTRUCTIONS`) are sanitized.
- Closing delimiter breakouts (`</user_request>`, `</tool_result>`) are escaped.
- System instructions are strictly in `system` role messages; user data is in `user` messages.
- Oversized tool outputs are bounded at 3,000 characters with an explicit truncation notice.

