"""MCP database inspection and sampling tools."""

from __future__ import annotations

import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from config.settings import AppSettings
from database.connection import DatabaseNotFoundError
from database.schema_inspector import (
    TableNotFoundError,
    get_table_sample as db_get_table_sample,
    inspect_schema,
)

log = logging.getLogger(__name__)

MAX_SAMPLE_RECORDS = 50
DEFAULT_SAMPLE_RECORDS = 10


def inspect_database_schema_impl(
    settings: AppSettings,
    table_name: str | None = None,
) -> dict[str, Any]:
    """Inspect full database schema or a single ``table_name``."""
    cleaned_table = (table_name or "").strip() or None
    try:
        schema = inspect_schema(
            settings.database_path,
            table_name=cleaned_table,
            include_counts=True,
        )
    except DatabaseNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "DATABASE_NOT_FOUND",
            "error": str(exc),
        }
    except TableNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "TABLE_NOT_FOUND",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error inspecting database schema")
        return {
            "status": "error",
            "error_code": "INSPECTION_ERROR",
            "error": f"Failed to inspect database schema: {exc}",
        }

    payload = schema.to_dict()
    payload["status"] = "ok"
    return payload


def get_table_sample_impl(
    settings: AppSettings,
    table_name: str,
    num_records: int = DEFAULT_SAMPLE_RECORDS,
) -> dict[str, Any]:
    """Fetch bounded sample records and column metadata for ``table_name``."""
    cleaned_table = (table_name or "").strip()
    if not cleaned_table:
        return {
            "status": "error",
            "error_code": "INVALID_ARGUMENT",
            "error": "table_name must be a non-empty string",
        }
    if not isinstance(num_records, int) or isinstance(num_records, bool) or num_records < 1:
        return {
            "status": "error",
            "error_code": "INVALID_ARGUMENT",
            "error": "num_records must be a positive integer (>= 1)",
        }

    try:
        sample = db_get_table_sample(
            settings.database_path,
            table_name=cleaned_table,
            limit=num_records,
            max_limit=MAX_SAMPLE_RECORDS,
        )
    except DatabaseNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "DATABASE_NOT_FOUND",
            "error": str(exc),
        }
    except TableNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "TABLE_NOT_FOUND",
            "error": str(exc),
        }
    except ValueError as exc:
        return {
            "status": "error",
            "error_code": "INVALID_ARGUMENT",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error sampling table '%s'", cleaned_table)
        return {
            "status": "error",
            "error_code": "SAMPLE_ERROR",
            "error": f"Failed to sample table '{cleaned_table}': {exc}",
        }

    sample["status"] = "ok"
    sample["max_allowed_sample_size"] = MAX_SAMPLE_RECORDS
    return sample


def register_database_tools(
    mcp: FastMCP,
    get_settings: Callable[[], AppSettings],
) -> None:
    """Register ``inspect_database_schema`` and ``get_table_sample`` on ``mcp``."""

    @mcp.tool(
        name="inspect_database_schema",
        description=(
            "Inspect the SQLite database schema. Optionally pass 'table_name' to inspect "
            "a single table; omit 'table_name' to list all tables, columns, SQLite types, "
            "primary keys, foreign keys, indexes, row counts, and table relationships."
        ),
    )
    def inspect_database_schema(table_name: str | None = None) -> dict[str, Any]:
        return inspect_database_schema_impl(get_settings(), table_name=table_name)

    @mcp.tool(
        name="get_table_sample",
        description=(
            "Return sample rows and column metadata from 'table_name'. "
            f"'num_records' defaults to {DEFAULT_SAMPLE_RECORDS} and is capped at {MAX_SAMPLE_RECORDS}."
        ),
    )
    def get_table_sample(
        table_name: str,
        num_records: int = DEFAULT_SAMPLE_RECORDS,
    ) -> dict[str, Any]:
        return get_table_sample_impl(
            get_settings(),
            table_name=table_name,
            num_records=num_records,
        )

