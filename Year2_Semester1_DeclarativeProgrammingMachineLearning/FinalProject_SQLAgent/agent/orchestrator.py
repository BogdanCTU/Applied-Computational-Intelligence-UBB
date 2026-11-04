"""Agent Orchestrator managing Ollama inference, MCP tools, and SQL approval gates."""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Sequence

from agent.events import ActivityCategory, ActivityEvent, mask_sensitive_data
from config.settings import AppSettings
from database.connection import DatabaseNotFoundError
from mcp_layer.client import MCPStdioClient
from mcp_layer.tools.sql_tools import SQLValidationError, validate_and_prepare_sql
from reporting import ReportHistoryManager

from .conversation import ConversationManager, compact_tool_result_for_llm
from .ollama_client import (
    OllamaChatResponse,
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaToolCall,
)
from .system_prompt import build_system_prompt
from .tool_handler import PERMITTED_TOOLS, ToolHandler

log = logging.getLogger(__name__)

_CSV_INTENT_RE = re.compile(r"\b(?:csv|to\s+csv|as\s+csv|in\s+csv|\.csv)\b", re.IGNORECASE)
_USER_WANTS_SQL_RE = re.compile(
    r"\b(?:include\s+sql|with\s+sql|show\s+sql|sql\s+queries|sql\s+appendix|append\s+sql|display\s+sql|embed\s+sql)\b",
    re.IGNORECASE,
)


class AgentEventType(str, Enum):
    USER_REQUEST = "user_request"
    STATUS_UPDATE = "status_update"
    REASONING_SUMMARY = "reasoning_summary"
    PLANNING = "planning"
    TOOL_CALL_PROPOSED = "tool_call_proposed"
    TOOL_ARGUMENTS = "tool_arguments"
    SQL_PROPOSED = "sql_proposed"
    SQL_VALIDATED = "sql_validated"
    SQL_APPROVAL_REQUESTED = "sql_approval_requested"
    SQL_APPROVED = "sql_approved"
    SQL_DENIED = "sql_denied"
    SQL_EXECUTING = "sql_executing"
    SQL_RESULT = "sql_result"
    REPORT_PLANNING = "report_planning"
    TOOL_RESULT = "tool_result"
    REPORT_GENERATED = "report_generated"
    FINAL_ANSWER = "final_answer"
    COMPLETION = "completion"
    ERROR = "error"
    THINKING = "thinking"


@dataclass
class AgentEvent:
    event_type: AgentEventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    activity_event: ActivityEvent | None = None


@dataclass
class AgentRunResult:
    status: str  # "success", "approval_denied", "cancelled", "error"
    final_message: str
    proposed_sql: str | None = None
    executed_sql: str | None = None
    sql_columns: list[str] = field(default_factory=list)
    sql_rows: list[Any] = field(default_factory=list)
    generated_reports: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    total_duration_s: float = 0.0
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status == "success"


ApprovalCallbackType = Callable[[str, str], bool | Awaitable[bool]]
ProgressCallbackType = Callable[[AgentEvent], None | Awaitable[None]]


def detect_requested_report_format(text: str) -> str:
    """Return 'CSV' if text explicitly mentions CSV format; otherwise default 'PDF'."""
    return "CSV" if _CSV_INTENT_RE.search(text or "") else "PDF"


def _synthesize_charts_from_intent(
    user_prompt: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Synthesize vector chart configurations from user prompt keywords and dataset columns."""
    if not columns or not rows:
        return []

    charts: list[dict[str, Any]] = []
    p_lower = user_prompt.lower()
    cols_lower = [c.lower() for c in columns]

    # Find candidate date/time column
    date_col = next(
        (
            c
            for c, cl in zip(columns, cols_lower)
            if any(k in cl for k in ["date", "month", "year", "time", "day", "period"])
        ),
        None,
    )
    # Find candidate category column
    cat_col = next(
        (
            c
            for c, cl in zip(columns, cols_lower)
            if any(k in cl for k in ["status", "name", "category", "country", "type", "group", "product"])
        ),
        None,
    )
    # Find candidate numeric columns
    num_cols = [
        c
        for c, cl in zip(columns, cols_lower)
        if any(
            k in cl
            for k in ["revenue", "sales", "total", "count", "amount", "price", "orders", "quantity", "val"]
        )
    ]
    if not num_cols:
        sample_row = rows[0]
        if isinstance(sample_row, dict):
            num_cols = [c for c in columns if isinstance(sample_row.get(c), (int, float))]
        else:
            num_cols = [
                c
                for idx, c in enumerate(columns)
                if idx < len(sample_row) and isinstance(sample_row[idx], (int, float))
            ]

    want_historical = any(
        k in p_lower for k in ["historical", "trend", "timeline", "over time", "monthly", "daily"]
    )
    want_pie = any(k in p_lower for k in ["pie", "distribution", "share", "proportion", "breakdown"])
    want_multi = any(
        k in p_lower for k in ["multi-series", "multi series", "compare categories", "comparison across"]
    )
    want_bar = any(k in p_lower for k in ["bar", "ranking", "top 10", "top 5", "compare"])

    if want_historical and date_col and num_cols:
        charts.append(
            {
                "chart_type": "historical_line",
                "title": "Historical Trend",
                "x_column": date_col,
                "y_columns": [num_cols[0]],
            }
        )

    if want_pie and (cat_col or date_col) and num_cols:
        label_c = cat_col or date_col
        charts.append(
            {
                "chart_type": "pie",
                "title": f"Distribution by {label_c.replace('_', ' ').title()}",
                "x_column": label_c,
                "y_columns": [num_cols[0]],
            }
        )

    if want_multi and date_col and len(num_cols) >= 2:
        charts.append(
            {
                "chart_type": "multi_line",
                "title": "Multi-Series Metric Comparison",
                "x_column": date_col,
                "y_columns": num_cols[:3],
            }
        )
    elif want_multi and date_col and cat_col and num_cols:
        charts.append(
            {
                "chart_type": "multi_line",
                "title": f"Comparison by {cat_col.replace('_', ' ').title()}",
                "x_column": date_col,
                "y_columns": [num_cols[0]],
                "series_column": cat_col,
            }
        )

    if want_bar and not charts and (cat_col or date_col) and num_cols:
        charts.append(
            {
                "chart_type": "vertical_bar",
                "title": f"Comparison by {(cat_col or date_col).replace('_', ' ').title()}",
                "x_column": cat_col or date_col,
                "y_columns": [num_cols[0]],
            }
        )

    return charts


class AgentOrchestrator:
    """Central orchestrator coordinating Ollama, conversation state, and MCP tools."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        ollama_client: OllamaClient | None = None,
        mcp_client: MCPStdioClient | None = None,
        tool_handler: ToolHandler | None = None,
    ) -> None:
        self.settings = settings
        self.ollama_client = ollama_client or OllamaClient(settings.ollama)
        self.mcp_client = mcp_client or MCPStdioClient(settings)
        self.tool_handler = tool_handler or ToolHandler(
            self.mcp_client,
            default_tool_timeout_s=settings.database.query_timeout_s + 15.0,
        )
        self.conversation = ConversationManager(
            max_history_messages=settings.agent.max_history_messages
        )
        self.history_manager = ReportHistoryManager(settings.output_dir)
        self.active_tool_mode = settings.ollama.tool_mode
        self.session_datasets: dict[str, dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Establish MCP connection and determine optimal tool mode ('native' vs 'json')."""
        if self._initialized:
            return

        # 1. Connect MCP client and initialize permitted tools
        await self.tool_handler.initialize()

        # 2. Determine tool mode (auto / native / json)
        if self.settings.ollama.tool_mode == "auto":
            try:
                conn_res = await self.ollama_client.check_connection()
                if isinstance(conn_res, (tuple, list)) and len(conn_res) >= 1:
                    is_connected = bool(conn_res[0])
                else:
                    is_connected = bool(conn_res)
            except Exception as exc:  # noqa: BLE001
                log.warning("Ollama connection check failed: %s", exc)
                is_connected = False

            if is_connected:
                self.active_tool_mode = await self.ollama_client.probe_tool_capability()
            else:
                self.active_tool_mode = "native"
        else:
            self.active_tool_mode = self.settings.ollama.tool_mode

        log.info(
            "AgentOrchestrator initialized (active_tool_mode=%s)", self.active_tool_mode
        )
        self._initialized = True

    async def close(self) -> None:
        """Shut down MCP client subprocess cleanly."""
        if self.mcp_client.is_connected:
            await self.mcp_client.close()
        self._initialized = False

    async def __aenter__(self) -> "AgentOrchestrator":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    def reset_conversation(self) -> None:
        """Clear conversation history, session datasets, and reset tool mode."""
        self.conversation.clear()
        self.session_datasets.clear()
        self.active_tool_mode = "native"

    async def _emit_event(
        self,
        event_type: AgentEventType,
        data: dict[str, Any],
        callback: ProgressCallbackType | None,
        *,
        activity_event: ActivityEvent | None = None,
    ) -> None:
        event = AgentEvent(
            event_type=event_type,
            data=data,
            activity_event=activity_event,
        )
        if callback is not None:
            try:
                res = callback(event)
                if inspect.isawaitable(res):
                    await res
            except Exception as exc:  # noqa: BLE001
                log.warning("Progress callback raised exception: %s", exc)

    async def _emit_activity(
        self,
        category: ActivityCategory | str,
        title: str,
        description: str = "",
        *,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        result_summary: str | None = None,
        duration_ms: float | None = None,
        status: str = "success",
        metadata: dict[str, Any] | None = None,
        callback: ProgressCallbackType | None = None,
        legacy_type: AgentEventType = AgentEventType.STATUS_UPDATE,
        extra_data: dict[str, Any] | None = None,
    ) -> ActivityEvent:
        act_event = ActivityEvent.create(
            category=category,
            title=title,
            description=description,
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata,
        )
        data = dict(extra_data or {})
        data["activity_event"] = act_event
        await self._emit_event(legacy_type, data, callback, activity_event=act_event)
        return act_event

    async def process_message(
        self,
        user_message: str,
        *,
        approval_callback: ApprovalCallbackType | None = None,
        progress_callback: ProgressCallbackType | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentRunResult:
        """Execute a complete natural-language reporting workflow."""
        start_time = time.perf_counter()
        if not self._initialized:
            await self.initialize()

        cleaned_user_msg = (user_message or "").strip()
        if not cleaned_user_msg:
            return AgentRunResult(
                status="error",
                final_message="User message cannot be empty.",
                error="Empty input",
            )

        # Detect user's explicit report format preference
        target_format = detect_requested_report_format(cleaned_user_msg)
        user_explicitly_wants_sql = bool(_USER_WANTS_SQL_RE.search(cleaned_user_msg))

        # Add user message to conversation history
        self.conversation.add_user_message(
            cleaned_user_msg,
            metadata={"target_format": target_format},
        )

        # 1. Emit USER_REQUEST event
        await self._emit_activity(
            ActivityCategory.USER_REQUEST,
            title="User Request Received",
            description=cleaned_user_msg,
            status="success",
            callback=progress_callback,
            legacy_type=AgentEventType.USER_REQUEST,
            extra_data={"message": cleaned_user_msg},
        )

        system_prompt = build_system_prompt(
            self.settings,
            tool_mode=self.active_tool_mode,
        )

        ollama_tools = (
            self.tool_handler.get_ollama_tools_schema()
            if self.active_tool_mode == "native"
            else None
        )

        max_iterations = int(self.settings.agent.max_iterations)
        iterations = 0
        proposed_sql: str | None = None
        executed_sql: str | None = None
        sql_columns: list[str] = []
        sql_rows: list[Any] = []
        approved_queries: set[str] = set()
        generated_reports: list[dict[str, Any]] = []
        final_message = ""
        overall_status = "success"
        error_msg: str | None = None

        while iterations < max_iterations:
            if cancel_event and cancel_event.is_set():
                overall_status = "cancelled"
                final_message = "Agent execution was cancelled by user."
                break

            iterations += 1

            # 2. Emit AGENT_STATUS event
            await self._emit_activity(
                ActivityCategory.AGENT_STATUS,
                title="Agent Reasoning",
                description=f"Consulting Ollama with {self.settings.ollama.model} (Iteration {iterations}/{max_iterations})...",
                status="in_progress",
                callback=progress_callback,
                legacy_type=AgentEventType.THINKING,
            )

            messages_for_llm = self.conversation.get_messages_for_llm(
                system_prompt=system_prompt
            )

            try:
                response: OllamaChatResponse = await self.ollama_client.chat(
                    messages=messages_for_llm,
                    tools=ollama_tools,
                    tool_mode=self.active_tool_mode,
                )
            except OllamaClientError as exc:
                if self.active_tool_mode == "native" and (
                    "XML" in str(exc)
                    or "500" in str(exc)
                    or "element <function>" in str(exc)
                    or "syntax" in str(exc).lower()
                ):
                    log.warning(
                        "Ollama native tool calling failed (%s); switching to structured JSON mode",
                        exc,
                    )
                    self.active_tool_mode = "json"
                    system_prompt = build_system_prompt(self.settings, tool_mode="json")
                    ollama_tools = None
                    messages_for_llm = self.conversation.get_messages_for_llm(
                        system_prompt=system_prompt
                    )
                    try:
                        response = await self.ollama_client.chat(
                            messages=messages_for_llm,
                            tools=None,
                            tool_mode="json",
                        )
                    except Exception as retry_exc:
                        overall_status = "error"
                        error_msg = self._format_friendly_error(retry_exc)
                        final_message = error_msg
                        await self._emit_activity(
                            ActivityCategory.ERROR,
                            title="LLM Connection Error",
                            description=error_msg,
                            status="failed",
                            callback=progress_callback,
                            legacy_type=AgentEventType.ERROR,
                            extra_data={"error": error_msg},
                        )
                        break
                else:
                    overall_status = "error"
                    error_msg = self._format_friendly_error(exc)
                    final_message = error_msg
                    await self._emit_activity(
                        ActivityCategory.ERROR,
                        title="LLM Connection Error",
                        description=error_msg,
                        status="failed",
                        callback=progress_callback,
                        legacy_type=AgentEventType.ERROR,
                        extra_data={"error": error_msg},
                    )
                    break

            # If client automatically used JSON fallback, switch orchestrator to json mode
            if response.used_fallback:
                log.info("Switching orchestrator active_tool_mode to 'json' following client fallback")
                self.active_tool_mode = "json"
                system_prompt = build_system_prompt(self.settings, tool_mode="json")
                ollama_tools = None

            # 3. Emit REASONING_SUMMARY if provided by model
            if response.thinking:
                clean_thinking = response.thinking.strip()
                first_line = clean_thinking.split("\n\n")[0].split("\n")[0]
                reasoning_snippet = first_line[:220] + ("..." if len(first_line) > 220 else "")
                await self._emit_activity(
                    ActivityCategory.REASONING_SUMMARY,
                    title="Reasoning Summary",
                    description=reasoning_snippet or "Formulating reporting approach",
                    status="success",
                    callback=progress_callback,
                    legacy_type=AgentEventType.REASONING_SUMMARY,
                    extra_data={"thinking": response.thinking},
                )

            # Case A: Model produced final message with no tool calls
            if not response.has_tool_calls:
                final_message = response.content or ""
                self.conversation.add_assistant_message(
                    final_message,
                    thinking=response.thinking,
                )
                await self._emit_activity(
                    ActivityCategory.COMPLETION,
                    title="Final Response Ready",
                    description=final_message[:150] + ("..." if len(final_message) > 150 else ""),
                    status="success",
                    callback=progress_callback,
                    legacy_type=AgentEventType.FINAL_ANSWER,
                    extra_data={"message": final_message},
                )
                break

            # Case B: Model called one or more MCP tools
            tool_calls_payload = [tc.to_dict() for tc in response.tool_calls]
            self.conversation.add_assistant_message(
                response.content or "",
                tool_calls=tool_calls_payload,
                thinking=response.thinking,
            )

            # 4. Emit PLANNING event summarizing the proposed tool sequence
            tools_plan = [tc.name for tc in response.tool_calls]
            await self._emit_activity(
                ActivityCategory.PLANNING,
                title="Execution Plan",
                description=f"Agent planned {len(tools_plan)} action(s): {', '.join(tools_plan)}",
                status="success",
                metadata={"planned_tools": tools_plan},
                callback=progress_callback,
                legacy_type=AgentEventType.PLANNING,
            )

            # Process tool calls sequentially
            for tool_call in response.tool_calls:
                t_name = tool_call.name
                t_args = dict(tool_call.arguments)

                # 5. Emit TOOL_CALL event
                await self._emit_activity(
                    ActivityCategory.TOOL_CALL,
                    title=f"Tool Call: {t_name}",
                    description=f"Initiating MCP tool '{t_name}'",
                    tool_name=t_name,
                    arguments=t_args,
                    status="in_progress",
                    callback=progress_callback,
                    legacy_type=AgentEventType.TOOL_CALL_PROPOSED,
                    extra_data={"tool": t_name, "arguments": t_args},
                )

                # 6. Emit TOOL_ARGUMENTS event
                await self._emit_activity(
                    ActivityCategory.TOOL_ARGUMENTS,
                    title=f"Tool Arguments: {t_name}",
                    description=f"Sanitized input arguments for {t_name}",
                    tool_name=t_name,
                    arguments=t_args,
                    status="success",
                    callback=progress_callback,
                    legacy_type=AgentEventType.TOOL_ARGUMENTS,
                )

                # Track proposed SQL
                if t_name == "prepare_sql_query":
                    q = (
                        t_args.get("sql_query")
                        or t_args.get("query")
                        or t_args.get("sql")
                        or t_args.get("statement")
                    )
                    if q:
                        proposed_sql = str(q).strip()
                        t_args["sql_query"] = proposed_sql
                        # 7. Emit SQL_GENERATION event
                        await self._emit_activity(
                            ActivityCategory.SQL_GENERATION,
                            title="SQL Generated",
                            description="AI agent formulated candidate SQL query",
                            metadata={"sql_query": proposed_sql},
                            status="success",
                            callback=progress_callback,
                            legacy_type=AgentEventType.SQL_PROPOSED,
                            extra_data={
                                "sql_query": proposed_sql,
                                "explanation": response.content or "Proposed query",
                            },
                        )

                # -------------------------------------------------------------
                # MANDATORY USER APPROVAL GATE FOR execute_readonly_sql
                # (With pre-approval SQL validation & argument normalization)
                # -------------------------------------------------------------
                if t_name == "execute_readonly_sql":
                    candidate_sql = (
                        t_args.get("sql_query")
                        or t_args.get("query")
                        or t_args.get("sql")
                        or t_args.get("statement")
                        or proposed_sql
                        or ""
                    )

                    # Step 1: Pre-validation - Check non-empty string
                    if not isinstance(candidate_sql, str) or not candidate_sql.strip():
                        err_msg = "SQL validation failed: SQL query is missing or empty. Please generate a valid read-only SQL query."
                        log.warning(err_msg)
                        await self._emit_activity(
                            ActivityCategory.SQL_VALIDATION,
                            title="SQL Validation Failed",
                            description="SQL query is missing or empty",
                            status="failed",
                            metadata={"error": err_msg, "error_code": "EMPTY_QUERY"},
                            callback=progress_callback,
                            legacy_type=AgentEventType.SQL_VALIDATED,
                        )
                        self.conversation.add_tool_message(
                            t_name,
                            {"status": "error", "error_code": "EMPTY_QUERY", "error": err_msg},
                            tool_call_id=tool_call.id,
                        )
                        # DO NOT show approval dialog!
                        continue

                    raw_query = candidate_sql.strip()

                    # Step 2: Pre-validation - Validate syntax and read-only compliance
                    try:
                        prepared = validate_and_prepare_sql(
                            raw_query,
                            db_path=self.settings.database_path,
                        )
                        validated_sql = prepared.sql_query
                        t_args["sql_query"] = validated_sql
                    except SQLValidationError as s_err:
                        log.warning("SQL pre-validation failed before approval: %s", s_err)
                        await self._emit_activity(
                            ActivityCategory.SQL_VALIDATION,
                            title="SQL Validation Failed",
                            description=f"Query rejected: {s_err}",
                            status="failed",
                            metadata={
                                "sql_query": raw_query,
                                "error": str(s_err),
                                "error_code": s_err.error_code,
                            },
                            callback=progress_callback,
                            legacy_type=AgentEventType.SQL_VALIDATED,
                        )
                        self.conversation.add_tool_message(
                            t_name,
                            {
                                "status": "error",
                                "error_code": s_err.error_code,
                                "error": f"SQL validation failed: {s_err}. Please generate a valid read-only SELECT or CTE query without modifications or forbidden clauses.",
                            },
                            tool_call_id=tool_call.id,
                        )
                        # DO NOT show approval dialog!
                        continue
                    except DatabaseNotFoundError as db_err:
                        log.error("Database not found during pre-validation: %s", db_err)
                        self.conversation.add_tool_message(
                            t_name,
                            {
                                "status": "error",
                                "error_code": "DATABASE_NOT_FOUND",
                                "error": str(db_err),
                            },
                            tool_call_id=tool_call.id,
                        )
                        continue

                    # 8. Emit SQL_VALIDATION success event
                    await self._emit_activity(
                        ActivityCategory.SQL_VALIDATION,
                        title="SQL Validation Passed",
                        description=f"Verified read-only {prepared.statement_type} on table(s): {', '.join(prepared.referenced_tables) or 'schema'}",
                        status="success",
                        metadata={
                            "sql_query": validated_sql,
                            "statement_type": prepared.statement_type,
                            "tables": prepared.referenced_tables,
                        },
                        callback=progress_callback,
                        legacy_type=AgentEventType.SQL_VALIDATED,
                    )

                    # Step 3: Approval gate check
                    if self.settings.agent.require_sql_approval:
                        if validated_sql not in approved_queries:
                            # 9. Emit APPROVAL_REQUIRED event
                            await self._emit_activity(
                                ActivityCategory.APPROVAL_REQUIRED,
                                title="SQL Approval Required",
                                description=f"Waiting for human review before execution on {Path(self.settings.database_path).name}",
                                status="waiting_approval",
                                metadata={
                                    "sql_query": validated_sql,
                                    "database": Path(self.settings.database_path).name,
                                },
                                callback=progress_callback,
                                legacy_type=AgentEventType.SQL_APPROVAL_REQUESTED,
                                extra_data={
                                    "sql_query": validated_sql,
                                    "explanation": response.content or "Proposed SQL query execution",
                                },
                            )

                            if approval_callback is None:
                                err = (
                                    "SQL execution blocked: user approval is required by policy, "
                                    "but no approval callback was provided."
                                )
                                log.warning(err)
                                overall_status = "approval_denied"
                                final_message = err
                                await self._emit_activity(
                                    ActivityCategory.APPROVAL_RESULT,
                                    title="Approval Denied",
                                    description="No approval callback provided by caller",
                                    status="rejected",
                                    metadata={"sql_query": validated_sql},
                                    callback=progress_callback,
                                    legacy_type=AgentEventType.SQL_DENIED,
                                    extra_data={"sql_query": validated_sql, "reason": "missing_callback"},
                                )
                                self.conversation.add_tool_message(
                                    t_name,
                                    {
                                        "status": "error",
                                        "error_code": "APPROVAL_REQUIRED",
                                        "error": err,
                                    },
                                    tool_call_id=tool_call.id,
                                )
                                continue

                            # Query the user approval callback
                            try:
                                cb_res = approval_callback(
                                    validated_sql,
                                    response.content or "Proposed SQL query execution",
                                )
                                is_approved = (
                                    await cb_res if inspect.isawaitable(cb_res) else bool(cb_res)
                                )
                            except Exception as exc:  # noqa: BLE001
                                log.warning("Approval callback error: %s", exc)
                                is_approved = False

                            if not is_approved:
                                log.info("User denied approval for SQL: %s", validated_sql[:80])
                                overall_status = "approval_denied"
                                final_message = (
                                    f"SQL query execution was denied by user: {validated_sql}"
                                )
                                # 10. Emit APPROVAL_RESULT (rejected) event
                                await self._emit_activity(
                                    ActivityCategory.APPROVAL_RESULT,
                                    title="Approval Denied",
                                    description="User rejected execution of proposed query",
                                    status="rejected",
                                    metadata={"sql_query": validated_sql},
                                    callback=progress_callback,
                                    legacy_type=AgentEventType.SQL_DENIED,
                                    extra_data={"sql_query": validated_sql, "reason": "user_denied"},
                                )
                                self.conversation.add_tool_message(
                                    t_name,
                                    {
                                        "status": "error",
                                        "error_code": "APPROVAL_DENIED",
                                        "error": (
                                            "The user explicitly denied approval to execute this query. "
                                            "Do not execute this query. Ask the user how they would like to modify it."
                                        ),
                                    },
                                    tool_call_id=tool_call.id,
                                )
                                continue

                            # User approved!
                            approved_queries.add(validated_sql)
                            # 10. Emit APPROVAL_RESULT (approved) event
                            await self._emit_activity(
                                ActivityCategory.APPROVAL_RESULT,
                                title="Approval Granted",
                                description="User explicitly approved SQL execution",
                                status="success",
                                metadata={"sql_query": validated_sql},
                                callback=progress_callback,
                                legacy_type=AgentEventType.SQL_APPROVED,
                                extra_data={"sql_query": validated_sql},
                            )

                    # 11. Emit SQL_EXECUTION event
                    await self._emit_activity(
                        ActivityCategory.SQL_EXECUTION,
                        title="Executing SQL Query",
                        description=f"Executing read-only statement on SQLite ({Path(self.settings.database_path).name})",
                        status="in_progress",
                        metadata={"sql_query": validated_sql},
                        callback=progress_callback,
                        legacy_type=AgentEventType.SQL_EXECUTING,
                    )

                # Format correction safety net: if user asked for CSV, steer report tool
                if target_format == "CSV" and t_name == "generate_pdf_report":
                    t_name = "generate_csv_report"
                    t_args.pop("summary", None)
                elif target_format == "PDF" and t_name == "generate_csv_report":
                    t_name = "generate_pdf_report"
                    t_args.setdefault("description", t_args.get("title", "Report"))

                # Inject full query results into report tools if omitted by LLM
                if t_name in {"generate_pdf_report", "generate_csv_report"}:
                    if not t_args.get("columns") and sql_columns:
                        t_args["columns"] = sql_columns
                    if not t_args.get("rows") and sql_rows:
                        t_args["rows"] = sql_rows
                    if not t_args.get("sql_query") and executed_sql:
                        t_args["sql_query"] = executed_sql
                    t_args["user_request"] = cleaned_user_msg

                    # Inject session datasets if multiple queries occurred
                    if not t_args.get("datasets") and self.session_datasets:
                        t_args["datasets"] = dict(self.session_datasets)

                    # SQL Visibility Policy: Include SQL ONLY if user explicitly requested it
                    t_args["include_sql"] = user_explicitly_wants_sql or bool(t_args.get("include_sql"))

                    # Auto-synthesize vector chart specifications if user requested charts and none supplied
                    if not t_args.get("charts"):
                        synth_charts = _synthesize_charts_from_intent(
                            cleaned_user_msg,
                            t_args.get("columns", sql_columns),
                            t_args.get("rows", sql_rows),
                        )
                        if synth_charts:
                            t_args["charts"] = synth_charts

                    # 13. Emit REPORT_PLANNING event
                    fmt = "PDF" if t_name == "generate_pdf_report" else "CSV"
                    await self._emit_activity(
                        ActivityCategory.REPORT_PLANNING,
                        title=f"Report Planning ({fmt})",
                        description=f"Preparing {fmt} report components, layout, and visual formatting",
                        status="in_progress",
                        metadata={
                            "format": fmt,
                            "title": t_args.get("title", "Report"),
                            "include_sql": t_args.get("include_sql", False),
                            "chart_count": len(t_args.get("charts", [])),
                        },
                        callback=progress_callback,
                        legacy_type=AgentEventType.REPORT_PLANNING,
                    )

                # Execute permitted tool through MCP handler
                t0 = time.perf_counter()
                tool_res = await self.tool_handler.execute_tool(t_name, t_args)
                duration_ms = round((time.perf_counter() - t0) * 1000, 2)

                # Defensive normalization if tool_res is a raw dictionary
                if isinstance(tool_res, dict):
                    from mcp_layer.client import MCPToolCallResult
                    is_err = tool_res.get("status") == "error"
                    tool_res = MCPToolCallResult(
                        tool_name=t_name,
                        is_error=is_err,
                        data=tool_res,
                        raw_text=str(tool_res),
                    )

                if tool_res.is_error and tool_res.data.get("error_code") == "QUERY_TIMEOUT":
                    timeout_msg = (
                        f"The database query exceeded the execution timeout ({int(self.settings.database.query_timeout_s)} seconds). "
                        "The query took too long to complete. Please try simplifying your query or filtering by a narrower date range."
                    )
                    tool_res.data["error"] = timeout_msg

                # Capture executed SQL results
                if t_name == "execute_readonly_sql" and not tool_res.is_error:
                    executed_sql = t_args.get("sql_query")
                    sql_columns = tool_res.data.get("columns", [])
                    sql_rows = tool_res.data.get("rows", [])

                    # Store into session datasets
                    ds_name = f"dataset_{len(self.session_datasets) + 1}"
                    self.session_datasets[ds_name] = {
                        "name": ds_name,
                        "columns": sql_columns,
                        "rows": sql_rows,
                        "record_count": len(sql_rows),
                        "sql_query": executed_sql,
                    }

                    # 12. Emit SQL_RESULT event
                    await self._emit_activity(
                        ActivityCategory.SQL_RESULT,
                        title="SQL Query Result",
                        description=f"Returned {len(sql_rows)} row(s) across {len(sql_columns)} column(s) ({duration_ms:.0f}ms)",
                        result_summary=f"Columns: {', '.join(sql_columns[:6])} | Total Rows: {len(sql_rows)}",
                        duration_ms=duration_ms,
                        status="success",
                        callback=progress_callback,
                        legacy_type=AgentEventType.SQL_RESULT,
                    )

                # Capture generated report metadata
                if t_name in {"generate_pdf_report", "generate_csv_report"} and not tool_res.is_error:
                    generated_reports.append(tool_res.data)
                    rep_path = tool_res.data.get("output_path", "")
                    rep_size = tool_res.data.get("file_size_bytes", 0)
                    # 14. Emit REPORT_GENERATION event
                    await self._emit_activity(
                        ActivityCategory.REPORT_GENERATION,
                        title="Report Generated",
                        description=f"Generated {Path(rep_path).name} ({rep_size} bytes)",
                        result_summary=f"File: {rep_path}\nSize: {rep_size} bytes\nRecords: {tool_res.data.get('record_count', 0)}",
                        duration_ms=duration_ms,
                        status="success",
                        metadata=tool_res.data,
                        callback=progress_callback,
                        legacy_type=AgentEventType.REPORT_GENERATED,
                        extra_data=tool_res.data,
                    )

                # 15. Emit TOOL_RESULT event
                await self._emit_activity(
                    ActivityCategory.TOOL_RESULT,
                    title=f"Tool Finished: {t_name}",
                    description="Execution succeeded" if not tool_res.is_error else f"Execution failed: {tool_res.data.get('error', 'Error')}",
                    result_summary=str(tool_res.data.get("message") or tool_res.data.get("error") or f"{len(tool_res.data.get('rows', []))} rows"),
                    duration_ms=duration_ms,
                    status="success" if not tool_res.is_error else "failed",
                    callback=progress_callback,
                    legacy_type=AgentEventType.TOOL_RESULT,
                    extra_data={"tool": t_name, "is_error": tool_res.is_error, "data": tool_res.data},
                )

                # Add tool message to conversation (compacted for LLM context bounds)
                compacted = compact_tool_result_for_llm(
                    t_name,
                    tool_res.data,
                    preview_rows_limit=int(self.settings.database.llm_preview_rows),
                )
                self.conversation.add_tool_message(
                    t_name,
                    compacted,
                    tool_call_id=tool_call.id,
                )

        if iterations >= max_iterations and overall_status == "success" and not final_message:
            overall_status = "error"
            error_msg = f"Agent reached maximum tool iterations limit ({max_iterations})."
            final_message = error_msg

        total_duration = round(time.perf_counter() - start_time, 2)

        # 16. Emit COMPLETION event (or ERROR)
        if overall_status == "success":
            await self._emit_activity(
                ActivityCategory.COMPLETION,
                title="Workflow Completed",
                description=f"Completed in {total_duration}s ({iterations} iteration(s))",
                result_summary=f"Reports generated: {len(generated_reports)} | SQL executed: {bool(executed_sql)}",
                status="success",
                callback=progress_callback,
                legacy_type=AgentEventType.COMPLETION,
            )
        elif overall_status == "error":
            await self._emit_activity(
                ActivityCategory.ERROR,
                title="Execution Error",
                description=error_msg or "Agent encountered an error",
                status="failed",
                callback=progress_callback,
                legacy_type=AgentEventType.ERROR,
                extra_data={"error": error_msg},
            )

        return AgentRunResult(
            status=overall_status,
            final_message=final_message,
            proposed_sql=proposed_sql,
            executed_sql=executed_sql,
            sql_columns=sql_columns,
            sql_rows=sql_rows,
            generated_reports=generated_reports,
            iterations=iterations,
            total_duration_s=total_duration,
            error=error_msg,
        )

    def _format_friendly_error(self, exc: Exception) -> str:
        """Translate runtime exceptions into clean, actionable user-facing messages."""
        if isinstance(exc, OllamaConnectionError):
            return "Cannot connect to Ollama. Please ensure Ollama is running (`ollama serve`)."
        if isinstance(exc, OllamaTimeoutError):
            return (
                f"Request to local Ollama timed out after {int(self.settings.ollama.request_timeout_s)} seconds. "
                "The model may be busy or processing an extensive prompt. Please try again or simplify your query."
            )
        if isinstance(exc, OllamaModelNotFoundError):
            return (
                f"Model '{self.settings.ollama.model}' is not available locally. "
                f"Please run `ollama pull {self.settings.ollama.model}` in your terminal."
            )
        err = str(exc)
        if "QUERY_TIMEOUT" in err or ("timed out" in err.lower() and "query" in err.lower()):
            return (
                f"The database query exceeded the execution timeout ({int(self.settings.database.query_timeout_s)} seconds). "
                "The query took too long to complete. Please try simplifying your query or filtering by a narrower date range."
            )
        if "ConnectError" in err or "Connection refused" in err:
            return "Cannot connect to Ollama. Please ensure Ollama is running (`ollama serve`)."
        return f"An error occurred during agent execution: {exc}"
