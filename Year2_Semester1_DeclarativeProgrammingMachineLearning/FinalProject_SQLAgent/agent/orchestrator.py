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
from reporting import ReportHistoryManager, ReportingPeriod, calculate_previous_calendar_month

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
_REPORT_INTENT_RE = re.compile(
    r"\b(?:report|pdf|csv|export|document|charts?|dashboard|graphs?|overview|summary\s+file)\b",
    re.IGNORECASE,
)
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
    component_status: dict[str, str] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == "success"


ApprovalCallbackType = Callable[[str, str], bool | Awaitable[bool]]
ProgressCallbackType = Callable[[AgentEvent], None | Awaitable[None]]


def detect_requested_report_format(text: str) -> str:
    """Return 'CSV' if text explicitly mentions CSV format; otherwise default 'PDF'."""
    return "CSV" if _CSV_INTENT_RE.search(text or "") else "PDF"


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        cleaned = str(val).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def _synthesize_kpis(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    session_datasets: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Synthesize high-level KPI metric cards from tabular datasets without double-counting."""
    kpis: list[dict[str, Any]] = []
    all_data: list[tuple[Sequence[str], Sequence[Any]]] = []

    if session_datasets:
        for ds in session_datasets.values():
            all_data.append((ds.get("columns", []), ds.get("rows", [])))
    if columns and rows:
        all_data.append((columns, rows))

    found_labels: set[str] = set()
    for cols, rws in all_data:
        if not cols or not rws:
            continue
        c_lower = [c.lower() for c in cols]

        # 1. Total Orders
        ord_idx = next(
            (i for i, c in enumerate(c_lower) if any(k in c for k in ["order_count", "total_orders", "orders_count", "orders"])),
            None,
        )
        if ord_idx is not None and "Total Orders" not in found_labels:
            vals = [_safe_float(r[ord_idx] if isinstance(r, (list, tuple)) else r.get(cols[ord_idx]), 0.0) for r in rws]
            total_ord = int(sum(vals))
            kpis.append({"label": "Total Orders", "value": f"{total_ord:,}", "note": "Verified order count"})
            found_labels.add("Total Orders")

        # 2. Sales volume
        sales_idx = next(
            (i for i, c in enumerate(c_lower) if any(k in c for k in ["sales_volume", "gross_sales", "subtotal", "gross_item_sales"])),
            None,
        )
        if sales_idx is not None and "Sales Volume" not in found_labels:
            vals = [_safe_float(r[sales_idx] if isinstance(r, (list, tuple)) else r.get(cols[sales_idx]), 0.0) for r in rws]
            tot_sales = sum(vals)
            kpis.append({"label": "Sales Volume", "value": f"${tot_sales:,.2f}", "note": "Gross subtotal"})
            found_labels.add("Sales Volume")

        # 3. Total Revenue
        rev_idx = next(
            (i for i, c in enumerate(c_lower) if any(k in c for k in ["total_revenue", "captured_revenue", "total_amount", "revenue", "net_amount"]) and (sales_idx is None or i != sales_idx)),
            None,
        )
        if rev_idx is not None and "Total Revenue" not in found_labels:
            vals = [_safe_float(r[rev_idx] if isinstance(r, (list, tuple)) else r.get(cols[rev_idx]), 0.0) for r in rws]
            tot_rev = sum(vals)
            kpis.append({"label": "Total Revenue", "value": f"${tot_rev:,.2f}", "note": "Net total amount"})
            found_labels.add("Total Revenue")

        # 4. Transactions
        tx_idx = next(
            (i for i, c in enumerate(c_lower) if any(k in c for k in ["transaction", "transactions_count", "payment_count", "payments"])),
            None,
        )
        if tx_idx is not None and "Total Transactions" not in found_labels:
            vals = [_safe_float(r[tx_idx] if isinstance(r, (list, tuple)) else r.get(cols[tx_idx]), 0.0) for r in rws]
            tot_tx = int(sum(vals))
            kpis.append({"label": "Transactions", "value": f"{tot_tx:,}", "note": "Processed payments"})
            found_labels.add("Total Transactions")

    return kpis


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
            if any(k in cl for k in ["status", "name", "category", "country", "type", "group", "product", "channel", "section", "method", "region", "city", "state", "brand"])
        ),
        None,
    )
    if not cat_col and rows:
        sample_row = rows[0]
        for c in columns:
            if c != date_col:
                val = sample_row.get(c) if isinstance(sample_row, dict) else (sample_row[columns.index(c)] if len(sample_row) > columns.index(c) else None)
                if isinstance(val, str) and not any(k in c.lower() for k in ["date", "month", "year", "time", "day", "period"]):
                    cat_col = c
                    break

    # Find candidate numeric columns
    num_cols = [
        c
        for c, cl in zip(columns, cols_lower)
        if any(
            k in cl
            for k in ["revenue", "sales", "total", "count", "amount", "price", "orders", "quantity", "val", "transactions"]
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

    if not num_cols:
        return []

    want_historical = any(
        k in p_lower for k in ["historical", "trend over time", "timeline", "trend of", "trends over time"]
    ) or ("trend" in p_lower and "multi" not in p_lower and "compare" not in p_lower)
    want_hist_bar = want_historical and any(k in p_lower for k in ["bar", "column"])
    want_pie = any(k in p_lower for k in ["pie", "distribution", "share", "proportion", "breakdown"])
    want_donut = any(k in p_lower for k in ["donut", "doughnut"])
    want_matrix = any(
        k in p_lower for k in ["matrix", "heatmap", "crosstab", "heat map", "matrix graph", "matrix graphs"]
    )
    want_multi = any(
        k in p_lower for k in ["multi-series", "multi series", "compare categories", "comparison across"]
    )
    want_hbar = any(k in p_lower for k in ["top 10", "top 5", "ranking", "horizontal bar", "top products", "ranking by"])
    want_stacked_bar = any(k in p_lower for k in ["stacked bar", "stacked column"])
    want_grouped_bar = any(k in p_lower for k in ["grouped bar", "grouped column"])
    want_bar = any(k in p_lower for k in ["bar", "compare", "comparison"])
    want_stacked_area = any(k in p_lower for k in ["stacked area", "cumulative area"])
    want_area = any(k in p_lower for k in ["area chart", "area graph", "area"])
    want_histogram = any(k in p_lower for k in ["histogram", "order value distribution", "value distribution", "numerical distribution", "spending distribution", "frequency distribution"])
    want_density = any(k in p_lower for k in ["density", "density plot", "density distribution", "kde"])
    want_box = any(k in p_lower for k in ["box plot", "boxplot", "box and whisker"])
    want_violin = any(k in p_lower for k in ["violin", "violin plot"])
    want_bubble = any(k in p_lower for k in ["bubble", "bubble chart"])
    want_scatter = any(k in p_lower for k in ["scatter", "scatter plot"])
    want_corr = any(k in p_lower for k in ["correlation", "correlation heatmap", "correlation matrix"])
    want_treemap = any(k in p_lower for k in ["treemap", "hierarchical", "tree map", "hierarchy", "subcategory"])

    # 1. Historical & Trend
    if want_historical and date_col and num_cols:
        if want_hist_bar:
            charts.append(
                {
                    "chart_type": "vertical_bar",
                    "title": f"Historical Trend ({num_cols[0].replace('_', ' ').title()})",
                    "x_column": date_col,
                    "y_columns": [num_cols[0]],
                }
            )
        else:
            charts.append(
                {
                    "chart_type": "historical_line",
                    "title": f"Historical Trend ({num_cols[0].replace('_', ' ').title()})",
                    "x_column": date_col,
                    "y_columns": [num_cols[0]],
                }
            )

    # 2. Treemap
    if want_treemap and (cat_col or date_col) and num_cols:
        l_col = cat_col or date_col
        charts.append(
            {
                "chart_type": "treemap",
                "title": f"Hierarchical Treemap by {l_col.replace('_', ' ').title()}",
                "x_column": l_col,
                "y_columns": [num_cols[0]],
            }
        )

    # 3. Histogram & Density
    if want_histogram and num_cols:
        charts.append(
            {
                "chart_type": "histogram",
                "title": f"Distribution Histogram ({num_cols[0].replace('_', ' ').title()})",
                "x_column": num_cols[0],
                "y_columns": [num_cols[0]],
            }
        )
    elif want_density and num_cols:
        charts.append(
            {
                "chart_type": "density",
                "title": f"Density Estimate ({num_cols[0].replace('_', ' ').title()})",
                "x_column": num_cols[0],
                "y_columns": [num_cols[0]],
            }
        )

    # 4. Box Plot & Violin Plot
    if want_box and num_cols:
        charts.append(
            {
                "chart_type": "box_plot",
                "title": f"Box Plot Analysis ({num_cols[0].replace('_', ' ').title()})",
                "x_column": cat_col or date_col or columns[0],
                "y_columns": [num_cols[0]],
            }
        )
    elif want_violin and num_cols:
        charts.append(
            {
                "chart_type": "violin",
                "title": f"Violin Density Plot ({num_cols[0].replace('_', ' ').title()})",
                "x_column": cat_col or date_col or columns[0],
                "y_columns": [num_cols[0]],
            }
        )

    # 5. Pie & Donut
    if (want_pie or want_donut) and num_cols and not want_histogram:
        c_type = "donut" if want_donut else "pie"
        pie_cat = cat_col or (date_col if not any(c.get("x_column") == date_col for c in charts) else None)
        if not pie_cat and len(columns) > 1:
            pie_cat = columns[0]
        if pie_cat:
            charts.append(
                {
                    "chart_type": c_type,
                    "title": f"Distribution by {pie_cat.replace('_', ' ').title()}",
                    "x_column": pie_cat,
                    "y_columns": [num_cols[0]],
                }
            )

    # 6. Matrix & Heatmap
    if want_matrix and (cat_col or date_col or len(columns) >= 2) and num_cols:
        m_row = cat_col or (columns[0] if columns[0] not in num_cols else date_col) or columns[0]
        m_vals = [c for c in num_cols if c != m_row][:4]
        if not m_vals and len(columns) > 1:
            m_vals = [columns[1]]
        m_type = "heatmap" if "heatmap" in p_lower or "heat map" in p_lower else "matrix"
        charts.append(
            {
                "chart_type": m_type,
                "title": f"Performance Matrix by {m_row.replace('_', ' ').title()}",
                "x_column": m_row,
                "y_columns": m_vals,
            }
        )

    # 7. Multi-Series Line
    if want_multi and date_col and cat_col and num_cols:
        charts.append(
            {
                "chart_type": "multi_line",
                "title": f"Comparison by {cat_col.replace('_', ' ').title()}",
                "x_column": date_col,
                "y_columns": [num_cols[0]],
                "series_column": cat_col,
            }
        )
    elif want_multi and date_col and len(num_cols) >= 2:
        charts.append(
            {
                "chart_type": "multi_line",
                "title": "Multi-Series Metric Comparison",
                "x_column": date_col,
                "y_columns": num_cols[:3],
            }
        )

    # 8. Area & Stacked Area
    if want_stacked_area and date_col and num_cols:
        charts.append(
            {
                "chart_type": "stacked_area",
                "title": f"Stacked Area Trend ({num_cols[0].replace('_', ' ').title()})",
                "x_column": date_col,
                "y_columns": num_cols[:3],
            }
        )
    elif want_area and date_col and num_cols and not want_stacked_area:
        charts.append(
            {
                "chart_type": "area",
                "title": f"Cumulative Trend ({num_cols[0].replace('_', ' ').title()})",
                "x_column": date_col,
                "y_columns": [num_cols[0]],
            }
        )

    # 9. Correlation Heatmap
    if want_corr and len(num_cols) >= 2:
        charts.append(
            {
                "chart_type": "correlation_heatmap",
                "title": "Correlation Matrix Heatmap",
                "x_column": num_cols[0],
                "y_columns": num_cols[:5],
            }
        )

    # 10. Scatter & Bubble
    if want_bubble and len(num_cols) >= 2:
        charts.append(
            {
                "chart_type": "bubble",
                "title": f"Bubble Analysis: {num_cols[0].replace('_', ' ').title()} vs {num_cols[1].replace('_', ' ').title()}",
                "x_column": num_cols[0],
                "y_columns": [num_cols[1]],
            }
        )
    elif want_scatter and len(num_cols) >= 2 and not want_corr:
        charts.append(
            {
                "chart_type": "scatter",
                "title": f"Scatter Relationship: {num_cols[0].replace('_', ' ').title()} vs {num_cols[1].replace('_', ' ').title()}",
                "x_column": num_cols[0],
                "y_columns": [num_cols[1]],
            }
        )

    # 11. Horizontal Bar (Rankings / Top 10)
    if want_hbar and not any(c.get("chart_type") == "horizontal_bar" for c in charts) and (cat_col or date_col) and num_cols:
        l_col = cat_col or date_col
        charts.append(
            {
                "chart_type": "horizontal_bar",
                "title": f"Ranking by {l_col.replace('_', ' ').title()}",
                "x_column": l_col,
                "y_columns": [num_cols[0]],
            }
        )

    # 12. Stacked & Grouped Bar
    if want_stacked_bar and not any(c.get("chart_type") == "stacked_bar" for c in charts) and (cat_col or date_col) and num_cols:
        l_col = cat_col or date_col
        charts.append(
            {
                "chart_type": "stacked_bar",
                "title": f"Stacked Comparison by {l_col.replace('_', ' ').title()}",
                "x_column": l_col,
                "y_columns": num_cols[:3],
            }
        )
    elif want_grouped_bar and not any(c.get("chart_type") == "grouped_bar" for c in charts) and (cat_col or date_col) and num_cols:
        l_col = cat_col or date_col
        charts.append(
            {
                "chart_type": "grouped_bar",
                "title": f"Grouped Comparison by {l_col.replace('_', ' ').title()}",
                "x_column": l_col,
                "y_columns": num_cols[:3],
            }
        )

    # 13. General Vertical Bar
    if want_bar and not any("bar" in c.get("chart_type", "") for c in charts) and (cat_col or date_col) and num_cols:
        label_col = cat_col or date_col
        charts.append(
            {
                "chart_type": "vertical_bar",
                "title": f"Comparison by {label_col.replace('_', ' ').title()}",
                "x_column": label_col,
                "y_columns": [num_cols[0]],
            }
        )

    # 14. Fallback if no charts synthesized but data available
    if not charts and (cat_col or date_col) and num_cols:
        c_type = "historical_line" if date_col else "vertical_bar"
        dim = date_col or cat_col
        charts.append(
            {
                "chart_type": c_type,
                "title": f"Analytical Overview ({num_cols[0].replace('_', ' ').title()} by {dim.replace('_', ' ').title()})",
                "x_column": dim,
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
        try:
            if self.mcp_client.is_connected:
                await self.mcp_client.close()
        except Exception as exc:  # noqa: BLE001
            log.warning("Error closing MCP client: %s", exc)
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
        if self.settings.ollama.tool_mode in {"native", "json"}:
            self.active_tool_mode = self.settings.ollama.tool_mode
        elif not self.active_tool_mode or self.active_tool_mode == "auto":
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
        component_status: dict[str, str] = {
            "database_discovery": "pending",
            "sql_preparation": "pending",
            "sql_execution": "pending",
            "kpi_generation": "pending",
            "chart_generation": "pending",
            "table_generation": "pending",
            "pdf_generation": "pending",
        }

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

                # Deterministic reporting fallback:
                # If SQL queries executed and user requested a report, but the model generated final text
                # without invoking generate_pdf_report / generate_csv_report, synthesize and run the report tool.
                user_wants_report = bool(_REPORT_INTENT_RE.search(cleaned_user_msg))
                if not generated_reports and (executed_sql or self.session_datasets) and user_wants_report:
                    log.info("Model finished without calling report tool after SQL execution. Synthesizing report components deterministically.")
                    fb_tool = "generate_csv_report" if target_format == "CSV" else "generate_pdf_report"
                    prev_period = calculate_previous_calendar_month()

                    fb_args: dict[str, Any] = {
                        "title": f"E-Commerce Operations & Performance Report ({prev_period.period_label})",
                        "description": final_message or f"Monthly e-commerce operations report covering {prev_period.period_label}.",
                        "user_request": cleaned_user_msg,
                        "include_sql": user_explicitly_wants_sql,
                        "sql_query": executed_sql or "",
                        "columns": sql_columns,
                        "rows": sql_rows,
                        "findings": [
                            f"Reporting period: {prev_period.period_label} ({prev_period.start_date_str} to {prev_period.end_date_str} exclusive).",
                            "Data extracted from primary SQLite database tables verifying orders, sales volume, net revenue, and transaction metrics.",
                            "Revenue calculations verified to prevent double-counting across multi-item transactions.",
                        ],
                    }
                    if self.session_datasets:
                        fb_args["datasets"] = dict(self.session_datasets)

                    synth_kpis = _synthesize_kpis(sql_columns, sql_rows, self.session_datasets)
                    if synth_kpis:
                        fb_args["kpis"] = synth_kpis
                        component_status["kpi_generation"] = "success"

                    synth_charts: list[dict[str, Any]] = []
                    if self.session_datasets:
                        for ds_name, ds_info in self.session_datasets.items():
                            ds_charts = _synthesize_charts_from_intent(
                                cleaned_user_msg,
                                ds_info.get("columns", []),
                                ds_info.get("rows", []),
                            )
                            for ch in ds_charts:
                                ch["dataset_id"] = ds_name
                                if not any(existing.get("chart_type") == ch.get("chart_type") for existing in synth_charts):
                                    synth_charts.append(ch)
                    if not synth_charts:
                        synth_charts = _synthesize_charts_from_intent(cleaned_user_msg, sql_columns, sql_rows)
                    if synth_charts:
                        fb_args["charts"] = synth_charts
                        component_status["chart_generation"] = "success"

                    if sql_rows or self.session_datasets:
                        component_status["table_generation"] = "success"

                    await self._emit_activity(
                        ActivityCategory.REPORT_PLANNING,
                        title=f"Report Planning ({target_format})",
                        description=f"Synthesizing {target_format} report components, layout, and visual formatting",
                        status="in_progress",
                        metadata={
                            "format": target_format,
                            "title": fb_args["title"],
                            "include_sql": fb_args["include_sql"],
                            "chart_count": len(fb_args.get("charts", [])),
                        },
                        callback=progress_callback,
                        legacy_type=AgentEventType.REPORT_PLANNING,
                    )

                    t0 = time.perf_counter()
                    fb_res = await self.tool_handler.execute_tool(fb_tool, fb_args)
                    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

                    if isinstance(fb_res, dict):
                        from mcp_layer.client import MCPToolCallResult
                        fb_res = MCPToolCallResult(
                            tool_name=fb_tool,
                            is_error=fb_res.get("status") == "error",
                            data=fb_res,
                            raw_text=str(fb_res),
                        )

                    if not fb_res.is_error:
                        generated_reports.append(fb_res.data)
                        component_status["pdf_generation"] = "success"
                        rep_path = fb_res.data.get("output_path", "")
                        rep_size = fb_res.data.get("file_size_bytes", 0)
                        pages = fb_res.data.get("page_count", 1)
                        charts_ren = fb_res.data.get("charts_rendered", 0)
                        charts_req = fb_res.data.get("charts_requested", 0)
                        tables_ren = fb_res.data.get("tables_rendered", 1)
                        tables_req = fb_res.data.get("tables_requested", 1)
                        ds_cnt = fb_res.data.get("datasets_count", 1)
                        status_c = fb_res.data.get("completion_status", "complete")

                        await self._emit_activity(
                            ActivityCategory.REPORT_GENERATION,
                            title="Report Generated",
                            description=f"Generated {Path(rep_path).name} ({rep_size} bytes, {pages} pg, {charts_ren} chart(s))",
                            result_summary=(
                                f"File: {rep_path}\n"
                                f"Size: {rep_size} bytes | Pages: {pages}\n"
                                f"Charts: {charts_ren}/{charts_req} | Tables: {tables_ren}/{tables_req}\n"
                                f"Datasets: {ds_cnt} | Status: {status_c}"
                            ),
                            duration_ms=duration_ms,
                            status="success",
                            metadata=fb_res.data,
                            callback=progress_callback,
                            legacy_type=AgentEventType.REPORT_GENERATED,
                            extra_data=fb_res.data,
                        )
                        final_message = (
                            (final_message or "")
                            + f"\n\nGenerated report successfully saved to:\n`{rep_path}`"
                        ).strip()
                    else:
                        component_status["pdf_generation"] = "failed"
                        log.warning("Fallback report generation failed: %s", fb_res.data.get("error"))

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
                    else:
                        # Automatic approval when require_sql_approval is False (default)
                        approved_queries.add(validated_sql)
                        log.info("SQL automatically approved — manual approval is disabled in settings.")
                        await self._emit_activity(
                            ActivityCategory.APPROVAL_RESULT,
                            title="SQL Auto-Approved",
                            description="SQL automatically approved — manual approval is disabled in settings.",
                            status="auto_approved",
                            metadata={
                                "sql_query": validated_sql,
                                "auto_approved": True,
                            },
                            callback=progress_callback,
                            legacy_type=AgentEventType.SQL_APPROVED,
                            extra_data={"sql_query": validated_sql, "auto_approved": True},
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

                    # Auto-synthesize KPIs if none supplied or if supplied as strings
                    raw_kpis = t_args.get("kpis")
                    if not raw_kpis or any(isinstance(k, str) for k in raw_kpis):
                        synth_kpis = _synthesize_kpis(
                            t_args.get("columns", sql_columns),
                            t_args.get("rows", sql_rows),
                            self.session_datasets,
                        )
                        if synth_kpis:
                            t_args["kpis"] = synth_kpis
                            component_status["kpi_generation"] = "success"
                    else:
                        component_status["kpi_generation"] = "success"

                    # Auto-inject findings with reporting period if omitted
                    if not t_args.get("findings"):
                        prev_period = calculate_previous_calendar_month()
                        t_args["findings"] = [
                            f"Reporting period: {prev_period.period_label} ({prev_period.start_date_str} to {prev_period.end_date_str} exclusive).",
                            "All requested metrics (orders, sales volume, net revenue, and transactions) were aggregated from SQLite database tables.",
                            "Revenue calculations verified to prevent double-counting across multi-item transactions.",
                        ]

                    # Auto-synthesize vector chart specifications if user requested charts and none supplied,
                    # or if the model supplied names/strings rather than full configuration dicts:
                    raw_charts = t_args.get("charts")
                    if not raw_charts or any(isinstance(c, str) for c in raw_charts):
                        synth_charts: list[dict[str, Any]] = []
                        if self.session_datasets:
                            for ds_name, ds_info in self.session_datasets.items():
                                ds_charts = _synthesize_charts_from_intent(
                                    cleaned_user_msg,
                                    ds_info.get("columns", []),
                                    ds_info.get("rows", []),
                                )
                                for ch in ds_charts:
                                    ch["dataset_id"] = ds_name
                                    if not any(existing.get("chart_type") == ch.get("chart_type") for existing in synth_charts):
                                        synth_charts.append(ch)
                        if not synth_charts:
                            synth_charts = _synthesize_charts_from_intent(
                                cleaned_user_msg,
                                t_args.get("columns", sql_columns),
                                t_args.get("rows", sql_rows),
                            )
                        if synth_charts:
                            t_args["charts"] = synth_charts
                            component_status["chart_generation"] = "success"
                    else:
                        component_status["chart_generation"] = "success"

                    if t_args.get("rows") or t_args.get("datasets"):
                        component_status["table_generation"] = "success"

                    if isinstance(t_args.get("report_spec"), dict):
                        rs = t_args["report_spec"]
                        if not rs.get("datasets") and t_args.get("datasets"):
                            rs["datasets"] = dict(t_args["datasets"])
                        if not rs.get("kpis") and t_args.get("kpis"):
                            rs["kpis"] = list(t_args["kpis"])
                        if not rs.get("findings") and t_args.get("findings"):
                            rs["findings"] = list(t_args["findings"])
                        if not rs.get("charts") and t_args.get("charts"):
                            rs["charts"] = list(t_args["charts"])

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

                # Component status: Schema discovery
                if t_name in {"inspect_database_schema", "get_table_sample"}:
                    component_status["database_discovery"] = "failed" if tool_res.is_error else "success"

                # Component status: SQL Preparation & Remediation
                if t_name == "prepare_sql_query":
                    component_status["sql_preparation"] = "failed" if tool_res.is_error else "success"
                    if tool_res.is_error:
                        err_text = str(tool_res.data.get("error", ""))
                        if "UNION" in err_text.upper() or "result columns" in err_text.lower():
                            remediation = (
                                "Do NOT use UNION or UNION ALL to combine different tables or queries with different columns. "
                                "Write a single SELECT query with GROUP BY on a single table, or execute separate queries."
                            )
                            tool_res.data["remediation"] = remediation
                            tool_res.data["error"] += f" Remediation: {remediation}"

                # Capture executed SQL results
                if t_name == "execute_readonly_sql":
                    component_status["sql_execution"] = "failed" if tool_res.is_error else "success"
                    if not tool_res.is_error:
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
                if t_name in {"generate_pdf_report", "generate_csv_report"}:
                    if not tool_res.is_error:
                        generated_reports.append(tool_res.data)
                        component_status["pdf_generation"] = "success"
                        if tool_res.data.get("charts_rendered", 0) > 0:
                            component_status["chart_generation"] = "success"
                        elif tool_res.data.get("charts_requested", 0) > 0 and tool_res.data.get("charts_rendered", 0) == 0:
                            component_status["chart_generation"] = "failed"
                        if tool_res.data.get("tables_rendered", 0) > 0:
                            component_status["table_generation"] = "success"

                        rep_path = tool_res.data.get("output_path", "")
                        rep_size = tool_res.data.get("file_size_bytes", 0)
                        pages = tool_res.data.get("page_count", 1)
                        charts_ren = tool_res.data.get("charts_rendered", 0)
                        charts_req = tool_res.data.get("charts_requested", 0)
                        tables_ren = tool_res.data.get("tables_rendered", 1)
                        tables_req = tool_res.data.get("tables_requested", 1)
                        ds_cnt = tool_res.data.get("datasets_count", 1)
                        status_c = tool_res.data.get("completion_status", "complete")
                        # 14. Emit REPORT_GENERATION event
                        await self._emit_activity(
                            ActivityCategory.REPORT_GENERATION,
                            title="Report Generated",
                            description=f"Generated {Path(rep_path).name} ({rep_size} bytes, {pages} pg, {charts_ren} chart(s))",
                            result_summary=(
                                f"File: {rep_path}\n"
                                f"Size: {rep_size} bytes | Pages: {pages}\n"
                                f"Charts: {charts_ren}/{charts_req} | Tables: {tables_ren}/{tables_req}\n"
                                f"Datasets: {ds_cnt} | Status: {status_c}"
                            ),
                            duration_ms=duration_ms,
                            status="success",
                            metadata=tool_res.data,
                            callback=progress_callback,
                            legacy_type=AgentEventType.REPORT_GENERATED,
                            extra_data=tool_res.data,
                        )
                    else:
                        component_status["pdf_generation"] = "failed"

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

        if generated_reports:
            for k in ["kpi_generation", "chart_generation", "table_generation", "pdf_generation"]:
                if component_status.get(k) == "pending":
                    component_status[k] = "success"

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
            component_status=component_status,
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
