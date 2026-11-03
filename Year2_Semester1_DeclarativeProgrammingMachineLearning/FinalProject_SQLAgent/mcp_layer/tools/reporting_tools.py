"""MCP report generation tools (PDF via ReportLab and UTF-8 CSV).

These tools strictly consume structured ``columns`` and ``rows`` supplied by the
caller and delegate formatting/persistence to ``reporting/``. They never connect
to SQLite or execute SQL queries.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from config.settings import AppSettings
from reporting import (
    ReportMetadata,
    ReportSecurityError,
    ReportValidationError,
    generate_csv_file,
    generate_pdf_file,
)

log = logging.getLogger(__name__)


def _metadata_to_tool_response(meta: ReportMetadata) -> dict[str, Any]:
    return {
        "status": "ok",
        "generation_status": meta.status,
        "report_id": meta.report_id,
        "output_path": meta.output_path,
        "file_name": meta.file_name,
        "output_format": meta.output_format,
        "record_count": meta.record_count,
        "total_input_records": meta.total_input_records,
        "truncated": meta.truncated,
        "column_names": meta.column_names,
        "file_size_bytes": meta.file_size_bytes,
        "created_at": meta.created_at,
        "title": meta.title,
    }


def generate_pdf_report_impl(
    settings: AppSettings,
    *,
    title: str,
    description: str,
    sql_query: str,
    columns: list[str],
    rows: list[Any],
    summary: str | None = None,
    user_request: str | None = None,
) -> dict[str, Any]:
    """Generate a formatted PDF report in ``settings.output_dir``."""
    try:
        meta = generate_pdf_file(
            title=title,
            description=description,
            sql_query=sql_query,
            columns=columns,
            rows=rows,
            output_dir=settings.output_dir,
            summary=summary,
            user_request=user_request or description or title,
            page_size_name=settings.reports.page_size,
            max_pdf_rows=settings.reports.max_pdf_rows,
            include_sql=settings.reports.include_sql_in_pdf,
            record_history=True,
        )
        return _metadata_to_tool_response(meta)
    except ReportSecurityError as exc:
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "SECURITY_ERROR",
            "error": str(exc),
        }
    except ReportValidationError as exc:
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "VALIDATION_ERROR",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error generating PDF report '%s'", title)
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "REPORT_GENERATION_ERROR",
            "error": f"Failed to generate PDF report: {exc}",
        }


def generate_csv_report_impl(
    settings: AppSettings,
    *,
    title: str,
    columns: list[str],
    rows: list[Any],
    description: str | None = None,
    sql_query: str | None = None,
    user_request: str | None = None,
) -> dict[str, Any]:
    """Generate a UTF-8 CSV report in ``settings.output_dir``."""
    try:
        meta = generate_csv_file(
            title=title,
            columns=columns,
            rows=rows,
            output_dir=settings.output_dir,
            description=description or "",
            sql_query=sql_query or "",
            user_request=user_request or description or title,
            max_rows=settings.reports.max_report_rows,
            record_history=True,
        )
        return _metadata_to_tool_response(meta)
    except ReportSecurityError as exc:
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "SECURITY_ERROR",
            "error": str(exc),
        }
    except ReportValidationError as exc:
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "VALIDATION_ERROR",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error generating CSV report '%s'", title)
        return {
            "status": "error",
            "generation_status": "failed",
            "error_code": "REPORT_GENERATION_ERROR",
            "error": f"Failed to generate CSV report: {exc}",
        }


def register_reporting_tools(
    mcp: FastMCP,
    get_settings: Callable[[], AppSettings],
) -> None:
    """Register ``generate_pdf_report`` and ``generate_csv_report`` on ``mcp``."""

    @mcp.tool(
        name="generate_pdf_report",
        description=(
            "Generate a professionally formatted, paginated PDF report (default output format) "
            "from structured query results and save it in the configured reports directory. "
            "Does not execute SQL."
        ),
    )
    def generate_pdf_report(
        title: str,
        description: str,
        sql_query: str,
        columns: list[str],
        rows: list[Any],
        summary: str | None = None,
        user_request: str | None = None,
    ) -> dict[str, Any]:
        return generate_pdf_report_impl(
            get_settings(),
            title=title,
            description=description,
            sql_query=sql_query,
            columns=columns,
            rows=rows,
            summary=summary,
            user_request=user_request,
        )

    @mcp.tool(
        name="generate_csv_report",
        description=(
            "Generate a UTF-8 CSV report from structured column names and query results "
            "and save it in the configured reports directory. Use only when the user "
            "explicitly requests CSV output. Does not execute SQL."
        ),
    )
    def generate_csv_report(
        title: str,
        columns: list[str],
        rows: list[Any],
        description: str | None = None,
        sql_query: str | None = None,
        user_request: str | None = None,
    ) -> dict[str, Any]:
        return generate_csv_report_impl(
            get_settings(),
            title=title,
            columns=columns,
            rows=rows,
            description=description,
            sql_query=sql_query,
            user_request=user_request,
        )

