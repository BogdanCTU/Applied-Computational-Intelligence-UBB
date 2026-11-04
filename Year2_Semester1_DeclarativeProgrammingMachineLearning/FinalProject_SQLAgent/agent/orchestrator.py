"""Agent Orchestrator managing Ollama inference, MCP tools, and SQL approval gates."""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Sequence

from config.settings import AppSettings
from mcp_layer.client import MCPStdioClient
from reporting import ReportHistoryManager

from .conversation import ConversationManager, compact_tool_result_for_llm
from .ollama_client import (
    OllamaChatResponse,
    OllamaClient,
    OllamaClientError,
    OllamaToolCall,
)
from .system_prompt import build_system_prompt
from .tool_handler import PERMITTED_TOOLS, ToolHandler

log = logging.getLogger(__name__)

_CSV_INTENT_RE = re.compile(r"\b(?:csv|to\s+csv|as\s+csv|in\s+csv|\.csv)\b", re.IGNORECASE)


class AgentEventType(str, Enum):
    THINKING = "thinking"
    TOOL_CALL_PROPOSED = "tool_call_proposed"
    SQL_PROPOSED = "sql_proposed"
    SQL_APPROVAL_REQUESTED = "sql_approval_requested"
    SQL_APPROVED = "sql_approved"
    SQL_DENIED = "sql_denied"
    TOOL_RESULT = "tool_result"
    REPORT_GENERATED = "report_generated"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"


@dataclass
class AgentEvent:
    event_type: AgentEventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


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
                logger.warning("Ollama connection check failed: %s", exc)
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
        """Clear conversation history."""
        self.conversation.clear()

    async def _emit_event(
        self,
        event_type: AgentEventType,
        data: dict[str, Any],
        callback: ProgressCallbackType | None,
    ) -> None:
        event = AgentEvent(event_type=event_type, data=data)
        if callback is not None:
            try:
                res = callback(event)
                if inspect.isawaitable(res):
                    await res
            except Exception as exc:  # noqa: BLE001
                log.warning("Progress callback raised exception: %s", exc)

    async def process_message(
        self,
        user_message: str,
        *,
        approval_callback: ApprovalCallbackType | None = None,
        progress_callback: ProgressCallbackType | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AgentRunResult:
        """Execute a complete natural-language reporting workflow.

        Parameters
        ----------
        user_message:
            The natural language reporting or analytical request.
        approval_callback:
            Async or sync function ``(sql_query, explanation) -> bool``. Required when
            SQL approval is enabled and a query is to be executed.
        progress_callback:
            Optional event listener receiving ``AgentEvent`` notifications.
        cancel_event:
            Optional asyncio.Event allowing cooperative cancellation of the run.
        """
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

        # Add user message to conversation history
        self.conversation.add_user_message(
            cleaned_user_msg,
            metadata={"target_format": target_format},
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
                overall_status = "error"
                error_msg = f"Ollama error: {exc}"
                final_message = error_msg
                await self._emit_event(
                    AgentEventType.ERROR, {"error": error_msg}, progress_callback
                )
                break

            # Emit thinking reasoning if provided by model
            if response.thinking:
                await self._emit_event(
                    AgentEventType.THINKING,
                    {"thinking": response.thinking},
                    progress_callback,
                )

            # Case A: Model produced final message with no tool calls
            if not response.has_tool_calls:
                final_message = response.content or ""
                self.conversation.add_assistant_message(
                    final_message,
                    thinking=response.thinking,
                )
                await self._emit_event(
                    AgentEventType.FINAL_ANSWER,
                    {"message": final_message},
                    progress_callback,
                )
                break

            # Case B: Model called one or more MCP tools
            tool_calls_payload = [tc.to_dict() for tc in response.tool_calls]
            self.conversation.add_assistant_message(
                response.content or "",
                tool_calls=tool_calls_payload,
                thinking=response.thinking,
            )

            # Process tool calls sequentially
            for tool_call in response.tool_calls:
                t_name = tool_call.name
                t_args = dict(tool_call.arguments)

                await self._emit_event(
                    AgentEventType.TOOL_CALL_PROPOSED,
                    {"tool": t_name, "arguments": t_args},
                    progress_callback,
                )

                # Track proposed SQL
                if t_name == "prepare_sql_query":
                    proposed_sql = t_args.get("sql_query")
                    await self._emit_event(
                        AgentEventType.SQL_PROPOSED,
                        {
                            "sql_query": proposed_sql,
                            "explanation": response.content or "Proposed query",
                        },
                        progress_callback,
                    )

                # -------------------------------------------------------------
                # MANDATORY USER APPROVAL GATE FOR execute_readonly_sql
                # -------------------------------------------------------------
                if t_name == "execute_readonly_sql":
                    query_to_execute = str(t_args.get("sql_query", "")).strip()

                    if self.settings.agent.require_sql_approval:
                        if query_to_execute not in approved_queries:
                            # Approval gate check
                            await self._emit_event(
                                AgentEventType.SQL_APPROVAL_REQUESTED,
                                {
                                    "sql_query": query_to_execute,
                                    "explanation": response.content or "",
                                },
                                progress_callback,
                            )

                            if approval_callback is None:
                                # Policy: Missing callback is NEVER approval
                                err = (
                                    "SQL execution blocked: user approval is required by policy, "
                                    "but no approval callback was provided."
                                )
                                log.warning(err)
                                overall_status = "approval_denied"
                                final_message = err
                                await self._emit_event(
                                    AgentEventType.SQL_DENIED,
                                    {"sql_query": query_to_execute, "reason": "missing_callback"},
                                    progress_callback,
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
                                    query_to_execute,
                                    response.content or "Proposed SQL query execution",
                                )
                                is_approved = (
                                    await cb_res if inspect.isawaitable(cb_res) else bool(cb_res)
                                )
                            except Exception as exc:  # noqa: BLE001
                                log.warning("Approval callback error: %s", exc)
                                is_approved = False

                            if not is_approved:
                                log.info("User denied approval for SQL: %s", query_to_execute[:80])
                                overall_status = "approval_denied"
                                final_message = (
                                    f"SQL query execution was denied by user: {query_to_execute}"
                                )
                                await self._emit_event(
                                    AgentEventType.SQL_DENIED,
                                    {"sql_query": query_to_execute, "reason": "user_denied"},
                                    progress_callback,
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

                            approved_queries.add(query_to_execute)
                            await self._emit_event(
                                AgentEventType.SQL_APPROVED,
                                {"sql_query": query_to_execute},
                                progress_callback,
                            )

                # Format correction safety net: if user asked for CSV, steer report tool
                if target_format == "CSV" and t_name == "generate_pdf_report":
                    t_name = "generate_csv_report"
                    t_args.pop("summary", None)
                elif target_format == "PDF" and t_name == "generate_csv_report":
                    t_name = "generate_pdf_report"
                    t_args.setdefault("description", t_args.get("title", "Report"))
                    t_args.setdefault("sql_query", executed_sql or proposed_sql or "")

                # Inject full query results into report tools if omitted by LLM
                if t_name in {"generate_pdf_report", "generate_csv_report"}:
                    if not t_args.get("columns") and sql_columns:
                        t_args["columns"] = sql_columns
                    if not t_args.get("rows") and sql_rows:
                        t_args["rows"] = sql_rows
                    if not t_args.get("sql_query") and executed_sql:
                        t_args["sql_query"] = executed_sql
                    t_args["user_request"] = cleaned_user_msg

                # Execute permitted tool through MCP handler
                tool_res = await self.tool_handler.execute_tool(t_name, t_args)

                # Capture executed SQL results
                if t_name == "execute_readonly_sql" and not tool_res.is_error:
                    executed_sql = t_args.get("sql_query")
                    sql_columns = tool_res.data.get("columns", [])
                    sql_rows = tool_res.data.get("rows", [])

                # Capture generated report metadata
                if t_name in {"generate_pdf_report", "generate_csv_report"} and not tool_res.is_error:
                    generated_reports.append(tool_res.data)
                    await self._emit_event(
                        AgentEventType.REPORT_GENERATED,
                        tool_res.data,
                        progress_callback,
                    )

                await self._emit_event(
                    AgentEventType.TOOL_RESULT,
                    {"tool": t_name, "is_error": tool_res.is_error, "data": tool_res.data},
                    progress_callback,
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

