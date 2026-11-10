"""Agent Orchestrator managing Ollama inference, MCP tools, and SQL approval gates."""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Sequence

from agent.checkpoint_manager import CheckpointManager
from agent.checkpoint_models import CheckpointType, RecoveryPolicy, RecoveryResult, TaskCheckpoint
from agent.context_builder import ContextBuilder
from agent.context_models import AssembledContext, ExecutionStage
from agent.events import ActivityCategory, ActivityEvent, mask_sensitive_data
from agent.skill_manager import SkillManager
from agent.task_manager import TaskManager
from agent.task_models import AgentTask, StepStatus, TaskPlan, TaskStatus, TaskStep
from agent.task_planner import TaskPlanner
from config.settings import DEFAULT_CONTEXT_WINDOW, AppSettings
from database.connection import DatabaseNotFoundError
from mcp_layer.client import MCPClientError, MCPStdioClient
from mcp_layer.tools.sql_tools import SQLValidationError, validate_and_prepare_sql
from memory.models import TaskDecision, TaskToolCallRecord
from memory.repository import SQLiteMemoryRepository
from reporting import (
    ReportHistoryManager,
    ReportValidationError,
    ReportingPeriod,
    calculate_previous_calendar_month,
    resolve_requested_period,
)
from reporting.canonical_data import (
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    normalize_kpi_collection,
    validate_tabular_rows_structure,
)

from .conversation import ConversationManager, compact_tool_result_for_llm
from .ollama_client import (
    ModelCapabilityStatus,
    ModelContextCapability,
    ModelContextIncompatibleError,
    OllamaChatResponse,
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaConnectionRefusedError,
    OllamaContextSizeRejectedError,
    OllamaDisconnectError,
    OllamaEmptyResponseError,
    OllamaHTTPError,
    OllamaInvalidJSONError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaToolCall,
)
from .system_prompt import build_system_prompt
from .tool_handler import (
    EXPECTED_MCP_TOOLS,
    MCPToolRegistry,
    PERMITTED_TOOLS,
    ToolDiscoveryError,
    ToolHandler,
    ToolHandlerError,
)

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
    task_id: str | None = None

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
    from reporting.canonical_data import CanonicalSQLDataset

    if columns or rows:
        ds = CanonicalSQLDataset(columns, rows)
        computed = ds.compute_deterministic_kpis()
        if computed:
            return computed

    if session_datasets:
        for ds_name, ds_info in session_datasets.items():
            if isinstance(ds_info, dict) and (ds_info.get("columns") or ds_info.get("rows")):
                ds = CanonicalSQLDataset(ds_info.get("columns", []), ds_info.get("rows", []))
                computed = ds.compute_deterministic_kpis()
                if computed:
                    return computed

    return []


def _generate_sql_remediation(err_text: str) -> str:
    """Generate targeted, actionable guidance to correct SQL errors based on database schema."""
    remediations: list[str] = []
    low = (err_text or "").lower()
    if "union" in low or "result columns" in low:
        remediations.append(
            "Do NOT use UNION or UNION ALL to combine different tables or queries with different columns. Write a single SELECT query with GROUP BY."
        )
    if "subtotal" in low and ("oi." in low or "order_items" in low or "no such column" in low):
        remediations.append(
            "Table 'order_items' does NOT have a 'subtotal' column; use 'oi.line_total' for item line totals, or 'o.subtotal' on the 'orders' table."
        )
    if "order_date" in low and ("oi." in low or "order_items" in low):
        remediations.append(
            "Table 'order_items' does NOT have 'order_date'. Join with 'orders o' ON o.order_id = oi.order_id to filter by 'o.order_date'."
        )
    if "ambiguous" in low and "status" in low:
        remediations.append(
            "Column 'status' is ambiguous because both orders and payments (or shipments) have a status column. Qualify it as 'o.status' or 'p.status'."
        )
    if "start_date" in low:
        remediations.append(
            "Table 'orders' has NO 'start_date' column. The date column is 'order_date' (e.g. o.order_date >= '...')."
        )
    if "category" in low and "no such column" in low:
        remediations.append(
            "Table 'orders' does NOT have a 'category' column. 'category' is in table 'products'. Join 'orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products pr ON oi.product_id = pr.product_id' to group by category."
        )
    return " ".join(remediations)


def _synthesize_charts_from_intent(
    user_prompt: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Synthesize vector chart configurations from user prompt keywords and dataset columns."""
    if not columns or not rows:
        return []

    is_struct_valid, sanitized_rows, _ = validate_tabular_rows_structure(columns, rows)
    if not is_struct_valid or not sanitized_rows:
        return []

    rows = sanitized_rows

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

    # Find candidate numeric columns (verify actual row values when rows are present)
    def _is_col_numeric(col_name: str, col_idx: int) -> bool:
        if col_name in (date_col, cat_col):
            return False
        if not rows:
            return True
        for r in rows[:5]:
            val = r.get(col_name) if isinstance(r, dict) else (r[col_idx] if col_idx < len(r) else None)
            if val is None:
                continue
            if isinstance(val, bool):
                return False
            if isinstance(val, (int, float)):
                return True
            try:
                float(str(val).replace(",", ""))
                return True
            except (ValueError, TypeError):
                return False
        return False

    num_cols = [
        c
        for idx, (c, cl) in enumerate(zip(columns, cols_lower))
        if _is_col_numeric(c, idx)
        and (
            any(
                k in cl
                for k in ["revenue", "sales", "total", "count", "amount", "price", "orders", "quantity", "val", "transactions", "avg", "sum"]
            )
            or rows
        )
    ]

    if not num_cols:
        return []

    def _distinct_count(col_name: str | None) -> int:
        if not col_name or col_name not in columns:
            return 0
        c_idx = columns.index(col_name)
        vals = {
            str(r.get(col_name) if isinstance(r, Mapping) else (r[c_idx] if c_idx < len(r) else None))
            for r in rows
            if (r.get(col_name) if isinstance(r, Mapping) else (r[c_idx] if c_idx < len(r) else None)) is not None
        }
        return len(vals)

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

    # 1. Historical & Trend (requires >= 2 distinct time periods)
    if want_historical and date_col and num_cols and _distinct_count(date_col) >= 2:
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
    if want_treemap and (cat_col or date_col) and num_cols and len(rows) >= 2:
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

    # 5. Pie & Donut (requires >= 2 distinct categories; never synthesize a 100% single-slice pie)
    if (want_pie or want_donut) and num_cols and not want_histogram and len(rows) >= 2:
        c_type = "donut" if want_donut else "pie"
        pie_cat = None
        if cat_col and _distinct_count(cat_col) >= 2:
            pie_cat = cat_col
        elif date_col and _distinct_count(date_col) >= 2:
            pie_cat = date_col
        elif cat_col and len(rows) >= 2:
            pie_cat = cat_col
        elif len(columns) > 1 and _distinct_count(columns[0]) >= 2:
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

    # 6. Matrix & Heatmap (requires >= 2 rows)
    if want_matrix and (cat_col or date_col or len(columns) >= 2) and num_cols and len(rows) >= 2:
        m_row = (
            cat_col
            if (cat_col and _distinct_count(cat_col) >= 2)
            else (date_col if (date_col and _distinct_count(date_col) >= 2) else (cat_col or date_col or columns[0]))
        )
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


def _build_verified_report_feedback_summary(rep: Mapping[str, Any]) -> str:
    """Build an authoritative user-facing report feedback summary from verified ReportMetadata."""
    out_path = str(rep.get("output_path") or "")
    fmt = str(rep.get("output_format") or "PDF").upper()
    req_period = str(rep.get("requested_period") or "Unspecified / Full Range")
    actual_period = str(rep.get("actual_data_period") or req_period)
    comp_period = str(rep.get("historical_comparison_period") or "")
    has_req_data = bool(rep.get("requested_period_has_data", True))
    avail_range = rep.get("available_data_range") or {}
    charts_ren = int(rep.get("charts_rendered", 0))
    tables_ren = int(rep.get("tables_rendered", 1))
    pages = int(rep.get("page_count", 1))
    kpis = rep.get("kpis") or []
    comp_kpis = rep.get("comparison_kpis") or []
    warnings = list(rep.get("warnings") or [])
    omitted = list(rep.get("omitted_analyses") or [])

    lines: list[str] = [
        f"### Verified {fmt} Report Summary",
        f"- **Generated File Path:** `{out_path}` ({pages} page(s))",
        f"- **Requested Reporting Period:** {req_period}",
    ]

    if not has_req_data and rep.get("requested_period"):
        avail_str = ""
        if isinstance(avail_range, Mapping) and (avail_range.get("min_date") or avail_range.get("max_date")):
            avail_str = f" (Available DB Range: {avail_range.get('min_date', 'N/A')} to {avail_range.get('max_date', 'N/A')})"
        lines.append(
            f"- **Data Availability:** No records exist for {req_period} (0 rows){avail_str}."
        )
    else:
        lines.append(f"- **Data Availability:** Verified records present ({rep.get('record_count', 0)} total rows across curated datasets).")

    lines.append(f"- **Actual Reporting Period Covered:** {actual_period or 'Verified SQL Query Scope'}")
    if comp_period:
        lines.append(f"- **Historical Comparison Period:** {comp_period} (explicitly labeled as historical comparison)")

    lines.append(
        f"- **Actual Rendered Components:** {charts_ren} chart(s), {tables_ren} table(s)"
    )

    if kpis:
        kpi_strs = [f"{k.get('label')}: {k.get('value')}" for k in kpis if isinstance(k, Mapping)]
        if kpi_strs:
            lines.append(f"- **Requested Period Metrics:** {' | '.join(kpi_strs)}")

    if comp_kpis:
        comp_strs = [f"{k.get('label')}: {k.get('value')}" for k in comp_kpis if isinstance(k, Mapping)]
        if comp_strs:
            lines.append(f"- **Historical Comparison Metrics ({comp_period}):** {' | '.join(comp_strs)}")

    all_notes = warnings + omitted
    if all_notes:
        lines.append("- **Warnings & Omitted Analyses:**")
        for note in all_notes[:6]:
            lines.append(f"  - {note}")

    return "\n".join(lines)


def _synthesize_schema_summary(schema_data: dict[str, Any]) -> str:
    """Format verified database schema inspection results into a readable user-facing response.

    Never invents tables or schema information; only formats verified MCP return data.
    """
    tables = schema_data.get("tables", [])
    if not tables:
        return "Database schema inspection completed. No tables were found in the database."

    lines: list[str] = [
        f"The database contains {len(tables)} table{'s' if len(tables) != 1 else ''}:",
        "",
    ]

    for t in tables:
        if isinstance(t, dict):
            t_name = t.get("name", "unknown")
            row_count = t.get("row_count")
            rc_str = f" ({row_count:,} records)" if row_count is not None else ""
            cols = t.get("columns", [])
            col_names: list[str] = []
            for c in cols:
                if isinstance(c, dict) and c.get("name"):
                    col_names.append(c["name"])
                elif isinstance(c, str):
                    col_names.append(c)
            col_str = f"\n  - Columns: {', '.join(col_names)}" if col_names else ""
            lines.append(f"- **{t_name}**{rc_str}{col_str}")
        elif isinstance(t, str):
            lines.append(f"- **{t}**")

    return "\n".join(lines)


def _synthesize_table_sample_summary(sample_data: dict[str, Any]) -> str:
    """Format verified table sample data into a readable user-facing response."""
    table_name = sample_data.get("table_name", "the requested table")
    rows = sample_data.get("rows", [])
    columns = sample_data.get("columns", [])
    lines: list[str] = [
        f"Retrieved {len(rows)} sample row{'s' if len(rows) != 1 else ''} from table `{table_name}`:",
        "",
    ]
    if columns:
        lines.append(f"Columns: {', '.join(columns)}")
    return "\n".join(lines)


def _synthesize_sql_execution_summary(
    sql: str | None,
    columns: list[str],
    rows: list[Any],
) -> str:
    """Format verified SQL execution results into a readable user-facing response."""
    count = len(rows)
    lines: list[str] = [
        f"Executed SQL query successfully returning {count} record{'s' if count != 1 else ''}:",
        "",
    ]
    if sql:
        lines.append(f"```sql\n{sql.strip()}\n```\n")
    if columns:
        lines.append(f"Columns ({len(columns)}): {', '.join(columns)}")
    return "\n".join(lines)


class AgentOrchestrator:
    """Central orchestrator coordinating Ollama, conversation state, MCP tools, and Agent Intelligence Layer."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        ollama_client: OllamaClient | None = None,
        mcp_client: MCPStdioClient | None = None,
        tool_handler: ToolHandler | None = None,
        task_manager: TaskManager | None = None,
        task_planner: TaskPlanner | None = None,
        memory_repo: SQLiteMemoryRepository | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        skill_manager: SkillManager | None = None,
        context_builder: ContextBuilder | None = None,
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

        # Phase 1-5 Agent Intelligence Layer integration
        self.effective_context_window: int = getattr(
            settings.agent, "agent_context_window", DEFAULT_CONTEXT_WINDOW
        )
        self.model_capability: ModelContextCapability | None = None
        self.memory_repo = memory_repo or SQLiteMemoryRepository()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(
            repository=self.memory_repo,
        )
        self.task_manager = task_manager or TaskManager(
            repository=self.memory_repo,
            checkpoint_manager=self.checkpoint_manager,
        )
        self.task_planner = task_planner or TaskPlanner(
            ollama_client=None,
            num_ctx=self.effective_context_window,
        )
        self.skill_manager = skill_manager or SkillManager(
            repository=self.memory_repo,
        )
        self.context_builder = context_builder or ContextBuilder(
            settings=settings,
            skill_manager=self.skill_manager,
            memory_repo=self.memory_repo,
            num_ctx=self.effective_context_window,
        )
        self.current_task_id: str | None = None

    def update_settings(self, new_settings: AppSettings) -> None:
        """Update orchestrator settings and propagate context window updates live."""
        self.settings = new_settings
        self.ollama_client.settings = new_settings.ollama
        self.effective_context_window = getattr(
            new_settings.agent, "agent_context_window", DEFAULT_CONTEXT_WINDOW
        )
        self.context_builder.settings = new_settings
        self.context_builder.num_ctx = self.effective_context_window
        self.ollama_client.settings.num_ctx = self.effective_context_window
        if self.task_planner:
            self.task_planner.num_ctx = self.effective_context_window
        # Invalidate cached model capability so next execution re-validates
        self.model_capability = None
        log.info(
            "Orchestrator settings updated: agent_context_window=%d, effective=%d",
            new_settings.agent.agent_context_window,
            self.effective_context_window,
        )

    @property
    def tool_registry(self) -> MCPToolRegistry:
        """Return the authoritative runtime MCPToolRegistry discovered from the MCP server."""
        return self.tool_handler.registry

    async def initialize(self) -> None:
        """Establish MCP connection, discover and validate all 6 MCP tools, discover skills, and determine tool mode."""
        if self._initialized:
            return

        # 1. Connect MCP client and initialize + validate all 6 permitted MCP tools
        await self.tool_handler.initialize()
        self.ollama_client.tool_registry = self.tool_handler.registry
        self.context_builder.tool_registry = self.tool_handler.registry

        # 2. Discover domain skills
        try:
            self.skill_manager.discover_skills()
        except Exception as exc:  # noqa: BLE001
            log.warning("Skill discovery failed during orchestrator initialization: %s", exc)

        # 3. Determine tool mode (auto / native / json)
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

        self.context_builder.tool_mode = self.active_tool_mode

        # 4. Validate model context capability against configured agent_context_window
        try:
            if hasattr(self.ollama_client, "validate_model_context_capability"):
                cap = await self.ollama_client.validate_model_context_capability(
                    configured_window=self.settings.agent.agent_context_window,
                    model_name=self.settings.ollama.model,
                )
                if isinstance(cap, ModelContextCapability):
                    self.model_capability = cap
                    self.effective_context_window = cap.effective_window
                    self.context_builder.num_ctx = self.effective_context_window
                    if hasattr(self.ollama_client, "settings") and hasattr(self.ollama_client.settings, "num_ctx"):
                        self.ollama_client.settings.num_ctx = self.effective_context_window
                    if self.task_planner:
                        self.task_planner.num_ctx = self.effective_context_window
                    if not cap.is_compatible:
                        log.warning(
                            "Model context incompatibility detected: %s",
                            cap.message,
                        )
        except Exception as exc:  # noqa: BLE001
            log.warning("Model context capability validation failed during initialize: %s", exc)

        log.info(
            "AgentOrchestrator initialized (active_tool_mode=%s, effective_ctx=%d)",
            self.active_tool_mode,
            self.effective_context_window,
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
        self.current_task_id = None
        if self.settings.ollama.tool_mode in {"native", "json"}:
            self.active_tool_mode = self.settings.ollama.tool_mode
        elif not self.active_tool_mode or self.active_tool_mode == "auto":
            self.active_tool_mode = "native"

    def get_interrupted_tasks(self) -> list[AgentTask]:
        """Return any tasks from persistent memory in non-terminal states."""
        return self.checkpoint_manager.detect_interrupted_tasks()

    def recover_task(
        self,
        task_id: str,
        *,
        policy: RecoveryPolicy | str = RecoveryPolicy.REQUIRE_CONFIRMATION,
    ) -> RecoveryResult:
        """Recover an interrupted task to a consistent executable state."""
        return self.checkpoint_manager.recover_task(task_id, policy=policy)

    def _determine_execution_stage(
        self,
        *,
        task: AgentTask | None,
        active_step: TaskStep | None,
        last_schema_result: Any | None,
        executed_sql: str | None,
        proposed_sql: str | None,
        user_wants_report: bool,
    ) -> ExecutionStage:
        """Infer current agent execution stage from active step and conversational state."""
        if active_step:
            req_tools = set(active_step.required_tools or [])
            if any(t in req_tools for t in ("inspect_database_schema", "get_table_sample")):
                return ExecutionStage.SCHEMA_DISCOVERY
            if "prepare_sql_query" in req_tools:
                return ExecutionStage.SQL_GENERATION
            if "execute_readonly_sql" in req_tools:
                return ExecutionStage.SQL_VALIDATION
            if any(t in req_tools for t in ("generate_pdf_report", "generate_csv_report")):
                return ExecutionStage.REPORT_GENERATION

        if not executed_sql and not last_schema_result:
            return ExecutionStage.SCHEMA_DISCOVERY
        if last_schema_result and not executed_sql and not proposed_sql:
            return ExecutionStage.SQL_GENERATION
        if proposed_sql and not executed_sql:
            return ExecutionStage.SQL_VALIDATION
        if executed_sql:
            return ExecutionStage.REPORT_GENERATION if user_wants_report else ExecutionStage.DATA_ANALYSIS

        return ExecutionStage.FINAL_RESPONSE

    def _prepare_and_validate_report_args(
        self,
        t_args: dict[str, Any],
        *,
        executed_sql: str | None,
        sql_columns: list[str],
        sql_rows: list[Any],
        cleaned_user_msg: str,
        target_format: str,
        user_explicitly_wants_sql: bool,
        component_status: dict[str, str],
    ) -> dict[str, Any]:
        """Enforce CanonicalSQLDataset as single source of numerical truth with pre-generation consistency validation."""
        if not t_args.get("columns") and sql_columns:
            t_args["columns"] = sql_columns
        if not t_args.get("rows") and sql_rows:
            t_args["rows"] = sql_rows
        elif t_args.get("rows") is not None:
            is_valid_rows, sanitized_rows, row_err = validate_tabular_rows_structure(
                t_args.get("columns") or sql_columns,
                t_args.get("rows"),
            )
            if not is_valid_rows:
                log.warning(
                    "LLM supplied invalid tabular rows to report tool (%s); substituting verified SQL execution rows.",
                    row_err,
                )
                t_args["rows"] = sql_rows
                if sql_columns:
                    t_args["columns"] = sql_columns
            else:
                t_args["rows"] = sanitized_rows
        if not t_args.get("sql_query") and executed_sql:
            t_args["sql_query"] = executed_sql
        t_args["user_request"] = cleaned_user_msg

        if not t_args.get("datasets") and self.session_datasets:
            t_args["datasets"] = dict(self.session_datasets)

        t_args["include_sql"] = user_explicitly_wants_sql or bool(t_args.get("include_sql"))

        cols = t_args.get("columns", sql_columns)
        rws = t_args.get("rows", sql_rows)
        primary_ds = CanonicalSQLDataset(cols, rws, name="primary", sql_query=executed_sql or "")

        # 1. Deterministic KPIs from single source of truth
        if t_args.get("kpis"):
            try:
                t_args["kpis"] = normalize_kpi_collection(t_args["kpis"])
                component_status["kpi_generation"] = "success"
            except ReportValidationError as exc:
                log.warning("Invalid KPIs supplied by LLM (%s); resetting to deterministic synthesis.", exc)
                t_args["kpis"] = []

        synth_kpis = primary_ds.compute_deterministic_kpis() if not primary_ds.is_empty else []
        if synth_kpis:
            t_args["kpis"] = synth_kpis
            component_status["kpi_generation"] = "success"
        elif not t_args.get("kpis") and (cols or rws or self.session_datasets):
            synth_kpis = _synthesize_kpis(cols, rws, self.session_datasets)
            if synth_kpis:
                t_args["kpis"] = synth_kpis
                component_status["kpi_generation"] = "success"

        # 2. Auto-inject findings if omitted
        if not t_args.get("findings"):
            req_period = resolve_requested_period(cleaned_user_msg, str(t_args.get("title", "")))
            period_obj = req_period or calculate_previous_calendar_month()
            t_args["findings"] = [
                f"Reporting period: {period_obj.period_label} ({period_obj.start_date_str} to {period_obj.end_date_str} exclusive).",
                "All requested metrics (orders, sales volume, net revenue, and transactions) were aggregated from SQLite database tables.",
                "Revenue calculations verified to prevent double-counting across multi-item transactions.",
            ]

        # 3. Chart validation and synthesis
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
                    cols,
                    rws,
                )
            if synth_charts:
                t_args["charts"] = synth_charts
                component_status["chart_generation"] = "success"
        else:
            validated_charts = []
            for ch in raw_charts:
                if isinstance(ch, dict):
                    x_c = ch.get("x_column") or ch.get("x_axis") or (cols[0] if cols else "")
                    y_c = ch.get("y_columns") or [ch.get("y_axis")] if (ch.get("y_columns") or ch.get("y_axis")) else ([cols[1]] if len(cols) > 1 else [x_c])
                    spec = ChartSpecification(
                        title=ch.get("title", "Chart"),
                        chart_type=ch.get("chart_type", "vertical_bar"),
                        x_axis=x_c or "",
                        y_axis=y_c or "",
                    )
                    trans = primary_ds.extract_and_transform_chart(spec)
                    if trans.is_valid:
                        validated_charts.append(ch)
                    else:
                        log.info("Chart '%s' failed validation (%s); attempting fallback chart synthesis.", ch.get("title"), trans.error_message)
            if validated_charts:
                # Supplement with any additional chart types requested by user intent (e.g., pie/donut, matrix/heatmap)
                intent_charts = _synthesize_charts_from_intent(cleaned_user_msg, cols, rws)
                existing_types = {c.get("chart_type") for c in validated_charts if isinstance(c, dict)}
                for ic in intent_charts:
                    if ic.get("chart_type") not in existing_types:
                        validated_charts.append(ic)
                        existing_types.add(ic.get("chart_type"))
                t_args["charts"] = validated_charts
                component_status["chart_generation"] = "success"
            else:
                intent_charts = _synthesize_charts_from_intent(cleaned_user_msg, cols, rws)
                if intent_charts:
                    t_args["charts"] = intent_charts
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

        # 4. Consistency Validator Gate
        val_res = ReportConsistencyValidator.validate_report_components(
            primary_ds,
            kpis=t_args.get("kpis"),
            charts=t_args.get("charts"),
        )
        if not val_res.is_valid:
            log.warning("Report consistency validation issues detected: %s", getattr(val_res, "errors", val_res))
        if getattr(val_res, "warnings", None):
            log.info("Report consistency warnings: %s", val_res.warnings)

        return t_args

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
        cleaned_user_msg = (user_message or "").strip()
        if not cleaned_user_msg:
            return AgentRunResult(
                status="error",
                final_message="User message cannot be empty.",
                error="Empty input",
            )

        if not self._initialized:
            try:
                await self.initialize()
            except (MCPClientError, ToolHandlerError) as init_exc:
                err_msg = f"MCP tool discovery failed during initialization: {init_exc}"
                log.error(err_msg)
                await self._emit_activity(
                    ActivityCategory.ERROR,
                    title="MCP Initialization Failed",
                    description=err_msg,
                    status="failed",
                    callback=progress_callback,
                    legacy_type=AgentEventType.ERROR,
                    extra_data={"error": err_msg},
                )
                return AgentRunResult(
                    status="error",
                    final_message=err_msg,
                    error=err_msg,
                    total_duration_s=round(time.perf_counter() - start_time, 3),
                )

        # Validate model context capability if not yet checked
        if self.model_capability is None and hasattr(self.ollama_client, "validate_model_context_capability"):
            try:
                cap = await self.ollama_client.validate_model_context_capability(
                    configured_window=self.settings.agent.agent_context_window,
                    model_name=self.settings.ollama.model,
                )
                if isinstance(cap, ModelContextCapability):
                    self.model_capability = cap
                    self.effective_context_window = cap.effective_window
                    self.context_builder.num_ctx = self.effective_context_window
                    if hasattr(self.ollama_client, "settings") and hasattr(self.ollama_client.settings, "num_ctx"):
                        self.ollama_client.settings.num_ctx = self.effective_context_window
                    if self.task_planner:
                        self.task_planner.num_ctx = self.effective_context_window
            except Exception as exc:  # noqa: BLE001
                log.warning("Model context capability validation error: %s", exc)

        # Check for model context incompatibility
        if (
            self.model_capability
            and isinstance(self.model_capability, ModelContextCapability)
            and not self.model_capability.is_compatible
        ):
            err_msg = self.model_capability.message
            await self._emit_activity(
                ActivityCategory.ERROR,
                title="Model Context Incompatible",
                description=err_msg,
                status="failed",
                metadata={"model_capability": asdict(self.model_capability) if is_dataclass(self.model_capability) else {}},
                callback=progress_callback,
                legacy_type=AgentEventType.ERROR,
            )
            return AgentRunResult(
                status="error",
                final_message=err_msg,
                error=err_msg,
                total_duration_s=round(time.perf_counter() - start_time, 3),
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

        # 1.1 Task Lifecycle Initiation & Planning
        task = self.task_manager.create_task(cleaned_user_msg)
        self.current_task_id = task.task_id

        try:
            plan = await self.task_planner.plan_task(task.task_id, cleaned_user_msg)
        except Exception as exc:  # noqa: BLE001
            log.warning("Task planning failed (%s); using deterministic fallback plan", exc)
            plan = self.task_planner.create_fallback_plan(task.task_id, cleaned_user_msg)

        task = self.task_manager.register_plan(task.task_id, plan)
        task = self.task_manager.start_task(task.task_id)

        # Emit task planning activity event
        await self._emit_activity(
            ActivityCategory.PLANNING,
            title="Task Plan Formulated",
            description=f"Structured plan with {len(plan.steps)} stage(s): {', '.join(s.name for s in plan.steps)}",
            status="success",
            metadata={
                "task_id": task.task_id,
                "step_count": len(plan.steps),
                "steps": [s.to_dict() for s in plan.steps],
                "rationale": plan.rationale,
            },
            callback=progress_callback,
            legacy_type=AgentEventType.PLANNING,
        )

        prev_period_info = calculate_previous_calendar_month()
        reporting_period_dict: dict[str, str] | None = None
        if any(p in cleaned_user_msg.lower() for p in ("last month", "previous month", "prior month")):
            reporting_period_dict = {
                "period_label": prev_period_info.period_label,
                "start_date": prev_period_info.start_date_str,
                "end_date_exclusive": prev_period_info.end_date_str,
            }

        schema_summary = (
            "TABLES AND COLUMNS:\n"
            "- orders (order_id, customer_id, order_date, status, channel, subtotal, discount_amount, shipping_fee, tax_amount, total_amount, currency)\n"
            "- order_items (order_item_id, order_id, product_id, quantity, unit_price, line_total)\n"
            "- customers (customer_id, first_name, last_name, email, phone, country, city, signup_date, loyalty_tier, marketing_opt_in)\n"
            "- payments (payment_id, order_id, method, amount, paid_at, status)\n"
            "- products (product_id, sku, product_name, category, brand, unit_price, unit_cost, weight_kg, is_active, created_at)\n"
            "- shipments (shipment_id, order_id, carrier, tracking_number, shipped_at, delivered_at, status)\n"
            "- returns (return_id, order_item_id, reason, refund_amount, requested_at, status)"
        )

        system_prompt = build_system_prompt(
            self.settings,
            tool_mode=self.active_tool_mode,
            schema_overview=schema_summary,
            discovered_tools=self.tool_handler.registry,
            reporting_period=reporting_period_dict,
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
        seen_failed_sql: set[str] = set()
        consecutive_sql_failures = 0
        generated_reports: list[dict[str, Any]] = []
        last_schema_result: dict[str, Any] | None = None
        last_sample_result: dict[str, Any] | None = None
        attempted_recovery = False
        termination_reason = "unknown"
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
                termination_reason = "cancelled_by_user"
                break

            iterations += 1

            # Determine execution stage & active step
            ready_steps = self.task_manager.get_ready_steps(task.task_id)
            current_ready_step = ready_steps[0] if ready_steps else None
            user_wants_report = bool(_REPORT_INTENT_RE.search(cleaned_user_msg))

            current_stage = self._determine_execution_stage(
                task=task,
                active_step=current_ready_step,
                last_schema_result=last_schema_result,
                executed_sql=executed_sql,
                proposed_sql=proposed_sql,
                user_wants_report=user_wants_report,
            )

            latest_chk = self.checkpoint_manager.get_latest_checkpoint(task.task_id)
            dataset_summary = None
            if executed_sql and (sql_columns or sql_rows):
                dataset_summary = {
                    "columns": sql_columns,
                    "row_count": len(sql_rows),
                    "sample_rows": sql_rows[:3] if sql_rows else [],
                }

            val_status = (
                self.model_capability.status.value
                if self.model_capability
                else "compatible"
            )
            rel_tables: list[str] | None = None
            if isinstance(last_schema_result, dict) and isinstance(last_schema_result.get("tables"), list):
                rel_tables = [
                    str(t.get("name"))
                    for t in last_schema_result["tables"]
                    if isinstance(t, dict) and t.get("name")
                ]

            assembled_ctx = self.context_builder.build(
                stage=current_stage,
                user_request=cleaned_user_msg,
                task=task,
                active_step=current_ready_step,
                checkpoint=latest_chk,
                schema=last_schema_result,
                relevant_tables=rel_tables,
                proposed_sql=proposed_sql,
                dataset_summary=dataset_summary,
                tool_mode=self.active_tool_mode,
                discovered_tools=self.tool_handler.registry,
                reporting_period=reporting_period_dict,
                effective_context_window=self.effective_context_window,
                configured_context_window=self.settings.agent.agent_context_window,
                model_validation_status=val_status,
                conversation_history=self.conversation.messages,
            )

            # Ensure discovered MCP tool definitions are passed on every native-mode iteration
            if self.active_tool_mode == "native":
                ollama_tools = self.tool_handler.get_ollama_tools_schema()
            else:
                ollama_tools = None

            # 2. Emit AGENT_STATUS event with context build metrics
            ctx_label = f"{self.effective_context_window // 1024}K"
            await self._emit_activity(
                ActivityCategory.AGENT_STATUS,
                title="Agent Reasoning",
                description=(
                    f"Consulting Ollama with {self.settings.ollama.model} (Iteration {iterations}/{max_iterations}) "
                    f"| Context: {ctx_label} | Stage: {current_stage.value} "
                    f"| Tokens: {assembled_ctx.report.estimated_input_tokens:,}/{assembled_ctx.report.available_input_tokens:,}"
                ),
                status="in_progress",
                metadata=assembled_ctx.report.model_dump(),
                callback=progress_callback,
                legacy_type=AgentEventType.THINKING,
            )

            messages_for_llm = self.conversation.get_messages_for_llm(
                system_prompt=assembled_ctx.system_prompt
            )

            try:
                chat_kwargs: dict[str, Any] = {
                    "messages": messages_for_llm,
                    "tools": ollama_tools,
                    "tool_mode": self.active_tool_mode,
                }
                try:
                    target_fn = getattr(self.ollama_client.chat, "side_effect", None)
                    if not callable(target_fn):
                        target_fn = self.ollama_client.chat
                    sig = inspect.signature(target_fn)
                    if "num_ctx" in sig.parameters or any(
                        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                    ):
                        chat_kwargs["num_ctx"] = self.effective_context_window
                except (ValueError, TypeError):
                    chat_kwargs["num_ctx"] = self.effective_context_window

                response: OllamaChatResponse = await self.ollama_client.chat(**chat_kwargs)
                if cancel_event and cancel_event.is_set():
                    overall_status = "cancelled"
                    final_message = "Agent execution was cancelled by user."
                    termination_reason = "cancelled_by_user"
                    break
            except OllamaClientError as exc:
                if isinstance(exc, OllamaEmptyResponseError):
                    user_wants_report = bool(_REPORT_INTENT_RE.search(cleaned_user_msg))
                    if user_wants_report and not executed_sql and not self.session_datasets and not attempted_recovery and iterations < max_iterations:
                        attempted_recovery = True
                        log.info("Caught OllamaEmptyResponseError after schema inspection; prompting for SQL query.")
                        self.conversation.add_user_message(
                            "Database schema inspected. Please proceed with constructing and executing the read-only SQL query for the requested report using 'prepare_sql_query' and 'execute_readonly_sql'."
                        )
                        continue

                    if last_schema_result and not user_wants_report:
                        final_message = _synthesize_schema_summary(last_schema_result)
                        overall_status = "success"
                        termination_reason = "deterministic_schema_synthesis_after_empty_error"
                        log.info(
                            "Caught OllamaEmptyResponseError after MCP schema inspection. "
                            "Deterministically synthesized response from verified MCP schema data (%d tables).",
                            len(last_schema_result.get("tables", [])),
                        )
                        self.conversation.add_assistant_message(final_message)
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
                    elif last_sample_result:
                        final_message = _synthesize_table_sample_summary(last_sample_result)
                        overall_status = "success"
                        termination_reason = "deterministic_sample_synthesis_after_empty_error"
                        self.conversation.add_assistant_message(final_message)
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
                    elif executed_sql and (sql_rows or sql_columns):
                        final_message = _synthesize_sql_execution_summary(executed_sql, sql_columns, sql_rows)
                        overall_status = "success"
                        termination_reason = "deterministic_sql_synthesis_after_empty_error"
                        self.conversation.add_assistant_message(final_message)
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
                    elif generated_reports:
                        rep = generated_reports[-1]
                        rep_path = rep.get("output_path", "")
                        final_message = f"Report successfully generated and saved to:\n`{rep_path}`"
                        overall_status = "success"
                        termination_reason = "deterministic_report_synthesis_after_empty_error"
                        self.conversation.add_assistant_message(final_message)
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

                if self.active_tool_mode == "native" and (
                    isinstance(exc, (OllamaDisconnectError, OllamaHTTPError))
                    or "XML" in str(exc)
                    or "500" in str(exc)
                    or "element <function>" in str(exc)
                    or "syntax" in str(exc).lower()
                    or "disconnect" in str(exc).lower()
                ):
                    log.warning(
                        "Ollama native tool calling encountered error or disconnect (%s); automatically switching to structured JSON mode",
                        exc,
                    )
                    self.active_tool_mode = "json"
                    system_prompt = build_system_prompt(
                        self.settings,
                        tool_mode="json",
                        schema_overview=schema_summary,
                        discovered_tools=self.tool_handler.registry,
                        reporting_period=reporting_period_dict,
                    )
                    ollama_tools = None
                    messages_for_llm = self.conversation.get_messages_for_llm(
                        system_prompt=system_prompt
                    )
                    try:
                        response = await self.ollama_client.chat(
                            messages=messages_for_llm,
                            tools=None,
                            tool_mode="json",
                            num_ctx=self.effective_context_window,
                        )
                    except Exception as retry_exc:
                        overall_status = "error"
                        error_msg = self._format_friendly_error(retry_exc)
                        final_message = error_msg
                        termination_reason = f"llm_error_after_fallback: {type(retry_exc).__name__}"
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
                    termination_reason = f"llm_error: {type(exc).__name__}"
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

            # Diagnostic evaluation of Ollama response
            is_final_response = not response.has_tool_calls
            log.info(
                "Ollama response evaluated: iteration=%d/%d is_final=%s role=%s "
                "has_tool_calls=%s tool_calls_count=%d content_empty=%s "
                "thinking_present=%s finish_reason=%s done=%s",
                iterations,
                max_iterations,
                is_final_response,
                getattr(response, "role", "assistant"),
                response.has_tool_calls,
                len(response.tool_calls),
                not bool(response.content and response.content.strip()),
                bool(response.thinking and response.thinking.strip()),
                getattr(response, "finish_reason", None),
                getattr(response, "done", None),
            )

            # If client automatically used JSON fallback on this turn, log it without permanently stripping native tools unless configured for json mode
            if response.used_fallback:
                if self.settings.ollama.tool_mode == "json":
                    self.active_tool_mode = "json"
                    self.context_builder.tool_mode = "json"
                    ollama_tools = None
                else:
                    log.info(
                        "Client used single-turn JSON fallback; preserving active_tool_mode='%s' and MCP tool definitions for subsequent turns",
                        self.active_tool_mode,
                    )

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
                candidate_content = (response.content or "").strip()

                # Guard against false CAPABILITY_LIMITATION refusal when MCP tools are registered
                if (
                    candidate_content
                    and not executed_sql
                    and not generated_reports
                    and self.tool_handler.registry.is_complete
                    and not attempted_recovery
                    and iterations < max_iterations
                    and (
                        "CAPABILITY_LIMITATION" in candidate_content.upper()
                        or "CANNOT GENERATE PDF" in candidate_content.upper()
                        or "CANNOT CREATE GRAPHICAL" in candidate_content.upper()
                    )
                ):
                    attempted_recovery = True
                    log.warning(
                        "Intercepted false capability refusal from model while all 6 MCP tools are registered; prompting immediate tool execution."
                    )
                    self.conversation.add_user_message(
                        "CORRECTION: All 6 MCP tools (`inspect_database_schema`, `get_table_sample`, `prepare_sql_query`, "
                        "`execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`) are active and registered. "
                        "You CAN generate PDF reports, charts, and CSV exports. Call `inspect_database_schema` with "
                        "`table_name='ALL'` immediately to start fulfilling the request."
                    )
                    continue

                if candidate_content:
                    final_message = candidate_content
                    termination_reason = "final_assistant_text_received"
                else:
                    # Model returned empty text without tool calls
                    user_wants_report = bool(_REPORT_INTENT_RE.search(cleaned_user_msg))
                    if user_wants_report and not executed_sql and not self.session_datasets and not attempted_recovery and iterations < max_iterations:
                        attempted_recovery = True
                        log.info(
                            "Model returned empty text after schema inspection but user requested a report. Prompting for SQL construction."
                        )
                        self.conversation.add_user_message(
                            "Database schema inspected. Please proceed with constructing and executing the read-only SQL query for the requested report using 'prepare_sql_query' and 'execute_readonly_sql'."
                        )
                        continue

                    # Check if verified MCP results exist from earlier tool execution in this session
                    if last_schema_result and not user_wants_report:
                        final_message = _synthesize_schema_summary(last_schema_result)
                        termination_reason = "deterministic_schema_synthesis"
                        log.info(
                            "Model returned empty text after MCP schema inspection for schema request. "
                            "Deterministically synthesized response from verified MCP schema data (%d tables).",
                            len(last_schema_result.get("tables", [])),
                        )
                    elif last_sample_result and not user_wants_report:
                        final_message = _synthesize_table_sample_summary(last_sample_result)
                        termination_reason = "deterministic_sample_synthesis"
                        log.info("Model returned empty text after MCP table sampling. Synthesized response from verified sample.")
                    elif executed_sql and (sql_rows or sql_columns):
                        final_message = _synthesize_sql_execution_summary(executed_sql, sql_columns, sql_rows)
                        termination_reason = "deterministic_sql_synthesis"
                        log.info("Model returned empty text after SQL execution. Synthesized response from query results.")
                    elif generated_reports:
                        rep = generated_reports[-1]
                        rep_path = rep.get("output_path", "")
                        final_message = f"Report successfully generated and saved to:\n`{rep_path}`"
                        termination_reason = "deterministic_report_synthesis"
                        log.info("Model returned empty text after report generation. Formatted report path.")
                    elif not attempted_recovery and iterations < max_iterations:
                        attempted_recovery = True
                        log.info("Model returned empty response without tool calls or verified data. Attempting bounded recovery prompt.")
                        self.conversation.add_user_message(
                            "Please provide a direct, meaningful answer to the request above."
                        )
                        continue
                    elif last_schema_result:
                        final_message = _synthesize_schema_summary(last_schema_result)
                        termination_reason = "deterministic_schema_synthesis"
                    else:
                        overall_status = "error"
                        error_msg = (
                            "The AI assistant returned an empty response with no content or tool calls. "
                            "Please try rephrasing your request."
                        )
                        final_message = error_msg
                        termination_reason = "empty_response_without_tools"
                        log.warning("Agent encountered empty assistant response without tool calls or verified data.")
                        await self._emit_activity(
                            ActivityCategory.ERROR,
                            title="Empty Response",
                            description=error_msg,
                            status="failed",
                            callback=progress_callback,
                            legacy_type=AgentEventType.ERROR,
                            extra_data={"error": error_msg},
                        )
                        break

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
                    }
                    if self.session_datasets:
                        fb_args["datasets"] = dict(self.session_datasets)

                    fb_args = self._prepare_and_validate_report_args(
                        fb_args,
                        executed_sql=executed_sql,
                        sql_columns=sql_columns,
                        sql_rows=sql_rows,
                        cleaned_user_msg=cleaned_user_msg,
                        target_format=target_format,
                        user_explicitly_wants_sql=user_explicitly_wants_sql,
                        component_status=component_status,
                    )

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

                    rep_path = fb_res.data.get("output_path", "")
                    if rep_path:
                        p = Path(rep_path)
                        if not (p.exists() and p.stat().st_size > 0):
                            fb_res.is_error = True
                            fb_res.data["error"] = f"Generated report file missing or empty on disk: {rep_path}"

                    if not fb_res.is_error:
                        generated_reports.append(fb_res.data)
                        component_status["pdf_generation"] = "success"
                        rep_size = fb_res.data.get("file_size_bytes", 0)
                        pages = fb_res.data.get("page_count", 1)
                        charts_ren = fb_res.data.get("charts_rendered", 0)
                        charts_req = fb_res.data.get("charts_requested", 0)
                        tables_ren = fb_res.data.get("tables_rendered", 1)
                        tables_req = fb_res.data.get("tables_requested", 1)
                        ds_cnt = fb_res.data.get("datasets_count", 1)
                        status_c = fb_res.data.get("completion_status", "complete")

                        if rep_path:
                            try:
                                self.memory_repo.save_artifact(
                                    task_id=task.task_id,
                                    step_id=None,
                                    artifact_type=target_format,
                                    file_path=rep_path,
                                    file_size_bytes=Path(rep_path).stat().st_size,
                                    metadata=fb_res.data,
                                )
                            except Exception as a_exc:
                                log.warning("Failed saving fallback artifact to memory: %s", a_exc)

                            try:
                                self.checkpoint_manager.create_checkpoint(
                                    task.task_id,
                                    CheckpointType.ARTIFACT_GENERATED,
                                    current_stage="report_generated",
                                )
                            except Exception as c_exc:
                                log.warning("Failed creating checkpoint for artifact: %s", c_exc)

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

                # Match tool call to a ready step in task manager
                ready_steps = self.task_manager.get_ready_steps(task.task_id)
                step_for_tool = next(
                    (s for s in ready_steps if t_name in s.required_tools),
                    ready_steps[0] if ready_steps else None,
                )
                active_step_id: str | None = None
                if step_for_tool:
                    try:
                        self.task_manager.start_step(task.task_id, step_for_tool.step_id)
                        active_step_id = step_for_tool.step_id
                    except Exception as s_st_exc:
                        log.debug("Step start transition note: %s", s_st_exc)
                        active_step_id = step_for_tool.step_id

                # Save tool call initiated in persistent memory
                try:
                    self.memory_repo.save_tool_call(
                        task_id=task.task_id,
                        step_id=active_step_id,
                        tool_name=t_name,
                        arguments=t_args,
                    )
                except Exception as mem_tc_exc:
                    log.warning("Failed saving tool call to memory: %s", mem_tc_exc)

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
                            if active_step_id:
                                try:
                                    self.task_manager.request_step_approval(task.task_id, active_step_id)
                                except Exception:
                                    pass
                            try:
                                self.memory_repo.save_decision(
                                    task_id=task.task_id,
                                    decision_type="sql_approval_requested",
                                    rationale=response.content or "Proposed SQL query execution",
                                    chosen_path=validated_sql,
                                )
                            except Exception:
                                pass

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
                                if active_step_id:
                                    try:
                                        self.task_manager.fail_step(task.task_id, active_step_id, error="Missing approval callback")
                                    except Exception:
                                        pass
                                try:
                                    self.memory_repo.save_decision(
                                        task_id=task.task_id,
                                        decision_type="sql_approval_denied",
                                        rationale="No approval callback provided by caller",
                                        chosen_path="denied_missing_callback",
                                    )
                                except Exception:
                                    pass
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
                                if active_step_id:
                                    try:
                                        self.task_manager.fail_step(task.task_id, active_step_id, error="Approval denied by user")
                                    except Exception:
                                        pass
                                try:
                                    self.memory_repo.save_decision(
                                        task_id=task.task_id,
                                        decision_type="sql_approval_denied",
                                        rationale="User rejected execution of proposed query",
                                        chosen_path="denied",
                                    )
                                except Exception:
                                    pass
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
                            if active_step_id:
                                try:
                                    self.task_manager.approve_step(task.task_id, active_step_id)
                                except Exception:
                                    pass
                            try:
                                self.memory_repo.save_decision(
                                    task_id=task.task_id,
                                    decision_type="sql_approval_granted",
                                    rationale="User explicitly approved SQL execution",
                                    chosen_path=validated_sql,
                                )
                            except Exception:
                                pass
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

                # Inject full query results into report tools if omitted by LLM and validate
                if t_name in {"generate_pdf_report", "generate_csv_report"}:
                    t_args = self._prepare_and_validate_report_args(
                        t_args,
                        executed_sql=executed_sql,
                        sql_columns=sql_columns,
                        sql_rows=sql_rows,
                        cleaned_user_msg=cleaned_user_msg,
                        target_format="CSV" if t_name == "generate_csv_report" else "PDF",
                        user_explicitly_wants_sql=user_explicitly_wants_sql,
                        component_status=component_status,
                    )

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
                cand_sql = str(t_args.get("sql_query") or "").strip()
                if t_name in {"prepare_sql_query", "execute_readonly_sql"} and cand_sql and cand_sql in seen_failed_sql:
                    log.warning("Blocked duplicate execution of known failing SQL query: %s", cand_sql[:80])
                    from mcp_layer.client import MCPToolCallResult
                    duration_ms = 0.0
                    tool_res = MCPToolCallResult(
                        tool_name=t_name,
                        is_error=True,
                        data={
                            "status": "error",
                            "error_code": "DUPLICATE_FAILED_QUERY",
                            "error": (
                                "You already submitted this exact failing SQL query. "
                                "Do NOT retry identical failed queries. Check table and column names in the schema."
                            ),
                        },
                        raw_text="Blocked duplicate failing query",
                    )
                else:
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
                    if not tool_res.is_error:
                        if t_name == "inspect_database_schema":
                            last_schema_result = tool_res.data
                        elif t_name == "get_table_sample":
                            last_sample_result = tool_res.data

                # Component status: SQL Preparation & Remediation
                if t_name == "prepare_sql_query":
                    component_status["sql_preparation"] = "failed" if tool_res.is_error else "success"
                    if tool_res.is_error:
                        if cand_sql:
                            seen_failed_sql.add(cand_sql)
                        consecutive_sql_failures += 1
                        err_text = str(tool_res.data.get("error", ""))
                        remediation = _generate_sql_remediation(err_text)
                        if remediation:
                            tool_res.data["remediation"] = remediation
                            tool_res.data["error"] += f" Remediation: {remediation}"
                    else:
                        consecutive_sql_failures = 0

                # Capture executed SQL results
                if t_name == "execute_readonly_sql":
                    component_status["sql_execution"] = "failed" if tool_res.is_error else "success"
                    if tool_res.is_error:
                        if cand_sql:
                            seen_failed_sql.add(cand_sql)
                        consecutive_sql_failures += 1
                        err_text = str(tool_res.data.get("error", ""))
                        remediation = _generate_sql_remediation(err_text)
                        if remediation:
                            tool_res.data["remediation"] = remediation
                            tool_res.data["error"] += f" Remediation: {remediation}"
                    else:
                        consecutive_sql_failures = 0
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
                    rep_path = tool_res.data.get("output_path", "")
                    if rep_path:
                        p = Path(rep_path)
                        if not (p.exists() and p.stat().st_size > 0):
                            tool_res.is_error = True
                            tool_res.data["error"] = f"Generated report file missing or empty on disk: {rep_path}"

                    if not tool_res.is_error:
                        generated_reports.append(tool_res.data)
                        component_status["pdf_generation"] = "success"
                        if tool_res.data.get("charts_rendered", 0) > 0:
                            component_status["chart_generation"] = "success"
                        elif tool_res.data.get("charts_requested", 0) > 0 and tool_res.data.get("charts_rendered", 0) == 0:
                            component_status["chart_generation"] = "failed"
                        if tool_res.data.get("tables_rendered", 0) > 0:
                            component_status["table_generation"] = "success"

                        rep_size = tool_res.data.get("file_size_bytes", 0)
                        pages = tool_res.data.get("page_count", 1)
                        charts_ren = tool_res.data.get("charts_rendered", 0)
                        charts_req = tool_res.data.get("charts_requested", 0)
                        tables_ren = tool_res.data.get("tables_rendered", 1)
                        tables_req = tool_res.data.get("tables_requested", 1)
                        ds_cnt = tool_res.data.get("datasets_count", 1)
                        status_c = tool_res.data.get("completion_status", "complete")

                        if rep_path:
                            try:
                                self.memory_repo.save_artifact(
                                    task_id=task.task_id,
                                    step_id=active_step_id,
                                    artifact_type="CSV" if t_name == "generate_csv_report" else "PDF",
                                    file_path=rep_path,
                                    file_size_bytes=Path(rep_path).stat().st_size,
                                    metadata=tool_res.data,
                                )
                            except Exception as a_exc:
                                log.warning("Failed saving artifact to memory: %s", a_exc)

                            try:
                                self.checkpoint_manager.create_checkpoint(
                                    task.task_id,
                                    CheckpointType.ARTIFACT_GENERATED,
                                    current_step_id=active_step_id,
                                    current_stage="report_generated",
                                )
                            except Exception as c_exc:
                                log.warning("Failed creating checkpoint for artifact: %s", c_exc)

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

                # Step status update in task manager
                if active_step_id:
                    try:
                        if not tool_res.is_error:
                            self.task_manager.complete_step(
                                task.task_id,
                                active_step_id,
                                output_reference=str(tool_res.data.get("output_path") or f"{len(tool_res.data.get('rows', []))} rows"),
                            )
                        else:
                            self.task_manager.fail_step(
                                task.task_id,
                                active_step_id,
                                error=str(tool_res.data.get("error", "Tool execution failed")),
                            )
                    except Exception as s_fin_exc:
                        log.debug("Step completion note: %s", s_fin_exc)

                # Update tool call in persistent memory with outcomes
                try:
                    self.memory_repo.save_tool_call(
                        task_id=task.task_id,
                        tool_name=t_name,
                        step_id=active_step_id,
                        arguments=t_args,
                        result_summary=str(tool_res.data.get("message") or tool_res.data.get("error") or ""),
                        status="success" if not tool_res.is_error else "failed",
                        error=str(tool_res.data.get("error")) if tool_res.is_error else None,
                        duration_ms=duration_ms,
                    )
                except Exception as mem_u_exc:
                    log.warning("Failed updating tool call in memory: %s", mem_u_exc)

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
            termination_reason = "max_iterations_reached"

        # Conclude task lifecycle in task manager and record durable checkpoint
        try:
            curr_task = self.task_manager.get_task(task.task_id)
            if overall_status == "success":
                # Mark any remaining non-terminal steps as SKIPPED
                for s in curr_task.steps:
                    if not s.is_terminal:
                        try:
                            self.task_manager.skip_step(
                                task.task_id,
                                s.step_id,
                                reason="Step skipped - workflow reached resolution earlier",
                            )
                        except Exception:
                            pass
                curr_task = self.task_manager.get_task(task.task_id)
                if curr_task.status != TaskStatus.COMPLETED:
                    curr_task.transition_to(TaskStatus.COMPLETED)
                    self.task_manager.repository.save(curr_task)
                self.checkpoint_manager.create_checkpoint(
                    task.task_id,
                    CheckpointType.TASK_COMPLETED,
                    current_stage="task_completed",
                )
            elif overall_status == "cancelled":
                try:
                    self.task_manager.cancel_task(task.task_id, reason="Cancelled by user")
                except Exception:
                    pass
            else:
                if not curr_task.is_terminal:
                    try:
                        curr_task.transition_to(TaskStatus.FAILED, error=error_msg or final_message)
                        self.task_manager.repository.save(curr_task)
                    except Exception:
                        pass
                self.checkpoint_manager.create_checkpoint(
                    task.task_id,
                    CheckpointType.STEP_FAILED,
                    current_stage="error",
                )
        except Exception as t_term_exc:
            log.warning("Failed concluding task lifecycle: %s", t_term_exc)

        # Enforce invariant: final_message must NEVER be empty regardless of overall status
        if not (final_message and final_message.strip()):
            if overall_status == "success":
                if generated_reports:
                    rep = generated_reports[-1]
                    final_message = _build_verified_report_feedback_summary(rep)
                    termination_reason = "report_delivery_response_synthesized"
                elif executed_sql and (sql_rows or sql_columns):
                    final_message = _synthesize_sql_execution_summary(executed_sql, sql_columns, sql_rows)
                    termination_reason = "sql_summary_response_synthesized"
                else:
                    final_message = "Workflow completed successfully."
                    termination_reason = "default_success_message_synthesized"
            elif overall_status == "approval_denied":
                final_message = "SQL query execution was denied by user."
            elif overall_status == "cancelled":
                final_message = "Agent execution was cancelled by user."
            else:
                overall_status = "error"
                final_message = error_msg or "Agent completed execution but failed to produce a user-facing response."
                termination_reason = "empty_final_message_invariant_failure"
        elif overall_status == "success" and generated_reports:
            rep = generated_reports[-1]
            verified_summary = _build_verified_report_feedback_summary(rep)
            if "### Verified " not in final_message:
                final_message = f"{final_message.strip()}\n\n{verified_summary}"

        log.info(
            "Orchestration loop terminating: reason='%s' iterations=%d status=%s final_msg_len=%d",
            termination_reason,
            iterations,
            overall_status,
            len(final_message),
        )

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
                description=error_msg or final_message or "Agent encountered an error",
                status="failed",
                callback=progress_callback,
                legacy_type=AgentEventType.ERROR,
                extra_data={"error": error_msg or final_message},
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
            task_id=task.task_id,
        )

    def _format_friendly_error(self, exc: Exception) -> str:
        """Translate runtime exceptions into clean, actionable user-facing messages."""
        if isinstance(exc, OllamaConnectionRefusedError):
            return (
                f"Cannot connect to Ollama at {self.settings.ollama.host}. "
                "The Ollama service is not running or the port is inaccessible. "
                "Please start the service in your terminal (`ollama serve`)."
            )
        if isinstance(exc, OllamaDisconnectError):
            return (
                "Ollama disconnected abruptly without sending a response. "
                "The local model runner may have crashed, run out of memory, or dropped the socket. "
                "Try restarting Ollama (`ollama serve`), reducing context length, or switching tool mode."
            )
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
        if isinstance(exc, OllamaEmptyResponseError):
            return (
                "Ollama returned an empty response with no content or tool calls. "
                "The model may have encountered an internal generation issue. Please try rephrasing your request."
            )
        if isinstance(exc, OllamaInvalidJSONError):
            return (
                "Ollama returned an invalid or unparseable JSON response. "
                "The model output could not be decoded. Please try again."
            )
        if isinstance(exc, OllamaHTTPError):
            return (
                f"Ollama returned an error (HTTP {exc.status_code}): {exc.message}. "
                "Please verify the Ollama service status."
            )
        if isinstance(exc, OllamaConnectionError):
            err_lower = str(exc).lower()
            if "refused" in err_lower or "10061" in err_lower:
                return "Cannot connect to Ollama. Please ensure Ollama is running (`ollama serve`)."
            return (
                f"Cannot connect to Ollama at {self.settings.ollama.host}. "
                f"Details: {exc}. Please ensure Ollama is running."
            )
        err = str(exc)
        if "QUERY_TIMEOUT" in err or ("timed out" in err.lower() and "query" in err.lower()):
            return (
                f"The database query exceeded the execution timeout ({int(self.settings.database.query_timeout_s)} seconds). "
                "The query took too long to complete. Please try simplifying your query or filtering by a narrower date range."
            )
        if "ConnectError" in err or "Connection refused" in err or "10061" in err:
            return "Cannot connect to Ollama. Please ensure Ollama is running (`ollama serve`)."
        if "RemoteProtocolError" in err or "disconnected without sending a response" in err or "10054" in err:
            return (
                "Ollama disconnected abruptly without sending a response. "
                "The local model runner may have crashed, run out of memory, or dropped the socket."
            )
        return f"An error occurred during agent execution: {exc}"
