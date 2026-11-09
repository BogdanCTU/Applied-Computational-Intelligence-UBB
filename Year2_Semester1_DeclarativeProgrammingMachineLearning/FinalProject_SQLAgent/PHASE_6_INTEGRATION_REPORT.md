# Phase 6 Integration Report: Agent Intelligence Layer & Configurable Context Window

**Date:** November 8, 2026  
**Status:** Complete & Fully Validated (424 / 424 Tests Passing, 100% Green)  
**Target Environment:** Local macOS / PySide6 Desktop GUI / Local Ollama (`qwen3.5:4b` / `gemma4:12b`) / Local Stdio MCP  

---

## 1. Executive Summary

Phase 6 completes the integration of the **Agent Intelligence Layer** into the Local Report SQL Agent, fulfilling all architectural requirements and the **Additional Mandatory Requirement — Configurable Agent Context Window**.

The Agent Intelligence Layer bridges the PySide6 desktop interface, the local Ollama LLM, and MCP tools with deterministic orchestration:
- **Task Management & DAG Execution** (`TaskManager`, `TaskPlanner`): Multi-step planning, acyclic dependency graphs, and structured lifecycle state transitions.
- **Persistent Memory** (`SQLiteMemoryRepository`): ACID-compliant transactional persistence in `data/agent_memory.db` (WAL mode) tracking tasks, execution steps, tool records, semantic facts, and registered skills.
- **Durable Checkpoints & Crash Recovery** (`CheckpointManager`): SHA-256 integrity-verified execution snapshots enabling zero-data-loss resume across crashes and restarts under configurable recovery policies.
- **Domain Skills** (`SkillManager`): Four specialized domain skills (`sql_generation`, `sql_validation`, `ecommerce_business_analysis`, `executive_report_design`) dynamically selected based on task intent and active execution stage.
- **Context Construction** (`ContextBuilder`): Stage-specific dynamic context generation strictly bound by the effective context window, preserving system instructions and mandatory boundaries while deterministically filtering lower-priority context.
- **Configurable Context Window (32K / 64K / 128K / 256K)**: Designed and optimized around a default operating configuration of **128K (131,072 tokens)**. Centralized in application settings, live-reconfigurable without application restarts, validated against Ollama model capabilities via `/api/show` metadata, and observed through the desktop Activity Inspector.

---

## 2. Configurable Agent Context Window Architecture

### 2.1 Supported Configurations & Centralized Authority
The system defines a single authoritative source of truth for the agent context window in `config/settings.py`:

| Label | Token Limit (`num_ctx`) | Purpose / Operating Profile |
|:---|---:|:---|
| **32K** | 32,768 | Resource-constrained hardware / low VRAM environments |
| **64K** | 65,536 | Balanced configuration for moderate queries |
| **128K** *(Default)* | **131,072** | **Primary default operating configuration** optimized for complete SQL reports |
| **256K** | 262,144 | Extended analysis window for massive schemas and multi-turn workflows |

- **Central authoritative setting**: `settings.agent.agent_context_window: int = 131072`.
- **Validation**: Strict enforcement via Pydantic model validators; values outside `(32768, 65536, 131072, 262144)` are immediately rejected.
- **Backward compatibility**: Legacy configurations missing the parameter automatically default to 128K (`131072`).
- **Synchronized propagation**: `settings.ollama.num_ctx` and `settings.agent_context_window` property getters/setters maintain bidirectional synchronization.

### 2.2 Live Settings UI & Seamless Propagation
- **Desktop UI**: `app/views/settings_view.py` exposes a selectable dropdown (`32K`, `64K`, `128K (Default)`, `256K`).
- **Live Reconfiguration**: Since Ollama is a stateless HTTP daemon accepting `options.num_ctx` per request, changes take effect immediately on subsequent LLM requests without requiring an application restart.
- **Orchestrator Integration**: `AgentOrchestrator.update_settings(new_settings)` updates `self.effective_context_window`, `self.context_builder.num_ctx`, `self.ollama_client.settings.num_ctx`, and `self.task_planner.num_ctx`, and resets `model_capability` for fresh validation.

### 2.3 Ollama Model Capability Validation
To prevent silent truncation or misleading failures when models do not support requested context windows, `agent/ollama_client.py` implements runtime capability validation via `POST /api/show`:

1. **Introspection**: Parses `model_info` for `<architecture>.context_length` or `general.context_length`, checking model parameters and modelfile definitions.
2. **Evaluation Rules**:
   - **Model max $\ge$ configured**: Compatible; uses configured context window.
   - **Model max $<$ configured**: **Incompatible**; halts execution, raises `ModelContextIncompatibleError`, and logs clear user-facing diagnostics instead of silently pretending the window is active.
   - **Model capability undetermined**: Reports `UNKNOWN` status and applies a safe fallback limit of 32K (`32768`).
   - **Ollama runtime rejection / OOM**: Catches context size errors and HTTP 500/OOM responses, surfacing `OllamaContextSizeRejectedError`.

#### Live Local Ollama Verification Matrix:
Tested against the running local Ollama daemon (`v0.40.14`):
- `qwen3.5:4b`: Discovered `model_info["qwen3_5.context_length"] = 262144` (256K native). Validated compatible at 32K, 64K, 128K, and 256K.
- `gemma4:12b`: Discovered `model_info["gemma4_unified.context_length"] = 262144` (256K native). Validated compatible across all settings.

### 2.4 ContextBuilder Budget Invariant & Allocation
`ContextBuilder` enforces the fundamental context window equation:
$$\text{system instructions} + \text{user request} + \text{task context} + \text{memory} + \text{skills} + \text{schema} + \text{tools} + \text{conversation history} + \text{reserved output} + \text{safety margin} \le \text{effective context window}$$

- **Output Reservation**: Configurable output token reservation (`reserved_output_tokens`, default 1024) is strictly preserved and never cannibalized for input context.
- **Safety Margin**: Buffer tokens (`safety_margin_tokens`, default 256) prevent token estimator jitter from breaching model boundaries.
- **Zero Silent Truncation**:
  - Oversized tool results are safely bounded with an explicit truncation notice (`... [truncated for context budget: N characters omitted]`), alerting the model to omitted data.
  - Mandatory content (system instructions, user prompt, critical boundaries) must fit in the available budget. If mandatory content exceeds the budget, `ContextBudgetExceededError` is raised immediately rather than silently dropping security boundaries.
- **Deterministic Priority Allocation**: Admitted sections are selected strictly by priority tier:
  1. `MANDATORY` (100): System boundaries, stage instructions, sanitized `<user_request>`.
  2. `HIGH` (75): Selected stage domain skills, relevant table schemas.
  3. `MEDIUM` (50): Task state, working memory, recent tool results, recent conversation history.
  4. `LOW` (25): Semantic domain facts, completed step history, older conversation turns.
- **Duplicate Context Elimination**: Sections with identical names or normalized contents are automatically deduplicated during assembly.

### 2.5 Runtime Observability (Activity Inspector)
For every context assembly, `ContextBuildReport` captures:
- Configured context window (e.g. `131,072`).
- Effective context window (e.g. `131,072`).
- Model capability validation status (`COMPATIBLE`, `INCOMPATIBLE`, `UNKNOWN`).
- Estimated input tokens, reserved output tokens, and safety margin.
- Included context categories and section breakdown.
- Excluded context categories, sections, and exact exclusion reasons.
- User-facing UI representation in `ActivityInspectorWidget` detailing live allocation metrics.

---

## 3. End-to-End Component Lifecycle

```
[User Request] 
      │
      ▼
AgentOrchestrator
      │── 1. Validate Model Capability (Ollama /api/show)
      │── 2. Create Task & Initialize Plan (TaskManager & SQLiteMemoryRepository)
      │── 3. Assemble Stage Context (ContextBuilder within 128K Budget)
      │── 4. Chat with Local Ollama (options: num_ctx=131072)
      │── 5. Human-in-the-Loop SQL Approval Dialog
      │── 6. Execute Read-Only SQL over MCP Subprocess
      │── 7. Reconcile Numerical Data (CanonicalSQLDataset Consistency Gate)
      │── 8. Generate Report (PDF / CSV)
      │── 9. Create Milestones Checkpoint (CheckpointManager)
      ▼
[Completed Report & Execution Audit]
```

### 3.1 Task Lifecycle & Resilient State Management
- `TaskManager` drives atomic step transitions (`PENDING` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETED`).
- Automatic checkpoint creation occurs on task creation, plan registration, step start, step completion, and manual approvals.
- `CheckpointManager.recover_task()` inspects SHA-256 signed checkpoints to restore interrupted workflows (e.g., after application crash or forced restart), resetting interrupted in-flight steps while preserving completed step artifacts.

### 3.2 Canonical Data Reconciliation Gate
To guarantee numerical integrity across narrative text, KPI summaries, and charts:
- `AgentOrchestrator._prepare_and_validate_report_args()` feeds query rows through `CanonicalSQLDataset`.
- Mismatched totals, negative values in percentage charts, or halluncinated metrics are caught before PDF/CSV generation.

---

## 4. Verification & Test Coverage Summary

### 4.1 Test Results Overview
- **Total Test Cases Executed**: 424
- **Passed**: 424 (100%)
- **Failed**: 0
- **Regression Breaches**: 0

### 4.2 Dedicated Test Suites

#### 1. Context Window Test Suite (`tests/test_context_window.py` — 36 Tests)
Covers all 15 mandatory context-window requirements:
1. Default configuration is 128K (`131072`).
2. All four supported values (32K, 64K, 128K, 256K) are accepted.
3. Unsupported values (0, -1, 4K, 8K, 16K, 100K, 512K) are rejected.
4. Configuration persists across restarts.
5. Missing configuration in legacy files defaults to 128K.
6. `ContextBuilder` receives the configured value.
7. Changing settings affects subsequent requests immediately.
8. Ollama requests receive the correct `num_ctx` in options.
9. Model capability incompatibility is reported cleanly without misleading success.
10. Context allocation respects the effective limit across 32K, 64K, 128K, and 256K.
11. Output reservation is preserved across all context tiers.
12. Context construction fails safely when mandatory content exceeds budget.
13. Large MCP tool results are bounded with explicit notice (never silent truncation).
14. Conversation history is filtered deterministically with recency weighting.
15. Memory and skills remain relevant under different context limits.

#### 2. Agent Intelligence Integration Test Suite (`tests/test_agent_intelligence_integration.py` — 5 Tests)
1. Complete task lifecycle: DAG planning, schema inspection, query execution, and completion.
2. Checkpoint creation and task recovery: Crash recovery restores state, completed steps, and metadata.
3. Report numerical consistency gate: Validates canonical dataset synchronization before reporting.
4. Model context capability incompatibility gate: Blocks execution when model context is smaller than configured.
5. Dynamic context window propagation: Live reconfiguration propagates across all components.

#### 3. Core Engine & Workflows Suite
- `tests/test_agent.py`: 54 passed (including live Ollama end-to-end integration).
- `tests/test_e2e_workflows.py`: 8 passed (multi-step workflows, MCP stdio communication, security error handling).
- `tests/test_reporting_accuracy.py`: 15 passed.
- `tests/test_task_manager.py` & `tests/test_task_manager_sqlite.py`: 34 passed.
- `tests/test_checkpoint_manager.py` & `tests/test_task_recovery.py`: 28 passed.
- `tests/test_skill_manager.py`, `tests/test_skill_selection.py`, `tests/test_skill_security.py`: 42 passed.
- `tests/test_context_builder.py`, `tests/test_context_models.py`, `tests/test_context_security.py`: 38 passed.

### 4.3 Database & File Integrity Verification
- **E-Commerce Database**: `data/ecommerce.db`
  - SHA-256 Hash: `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`
  - Status: **Verified Bit-for-Bit Identical / Untouched**.
- **Agent Memory Database**: `data/agent_memory.db`
  - Status: Fully initialized with schema migrations 001-004 in WAL mode.

---

## 5. Acceptance Criteria Sign-Off

- [x] **128K is default agent context configuration** (`DEFAULT_CONTEXT_WINDOW = 131072`).
- [x] **32K, 64K, 128K, and 256K are configurable** and strictly validated.
- [x] **Settings persist across restarts** via `config/settings.json`.
- [x] **Ollama receives the correct runtime context configuration** (`num_ctx`).
- [x] **Model compatibility is validated** via live `/api/show` metadata inspection.
- [x] **Every intelligence-layer component respects centralized configuration**.
- [x] **ContextBuilder dynamically allocates available context** under budget invariants.
- [x] **Unnecessary information is excluded** rather than blindly filling the window.
- [x] **Mandatory information is never silently truncated**.
- [x] **Context usage and token allocation are observable** in Activity Inspector.
- [x] **Existing application behavior and security controls remain intact**.

Phase 6 integration is complete and approved for production delivery.

