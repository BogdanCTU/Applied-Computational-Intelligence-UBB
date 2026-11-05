"""Official Python MCP stdio server for the Local Report SQL Agent.

Exposes six local-only tools over JSON-RPC stdio:
1. ``inspect_database_schema``
2. ``get_table_sample``
3. ``prepare_sql_query``
4. ``execute_readonly_sql``
5. ``generate_pdf_report``
6. ``generate_csv_report``

Run as a standalone subprocess:
    python -m mcp_layer.server
"""

from __future__ import annotations

import logging
from typing import Callable

from mcp.server.fastmcp import FastMCP

from config.logging_setup import setup_logging
from config.settings import AppSettings, load_settings
from mcp_layer.tools.database_tools import register_database_tools
from mcp_layer.tools.reporting_tools import register_reporting_tools
from mcp_layer.tools.sql_tools import register_sql_tools

log = logging.getLogger(__name__)

SERVER_NAME = "local-report-sql-agent-mcp"
SERVER_INSTRUCTIONS = (
    "Local Report SQL Agent MCP server. Provides strictly read-only SQLite "
    "schema inspection, SQL preparation/validation, bounded read-only query "
    "execution, and local PDF/CSV report generation."
)


def create_mcp_server(
    settings: AppSettings | None = None,
    *,
    settings_provider: Callable[[], AppSettings] | None = None,
) -> FastMCP:
    """Create and configure the ``FastMCP`` instance with all six tools."""
    if settings_provider is not None:
        get_settings = settings_provider
    elif settings is not None:
        get_settings = lambda: settings  # noqa: E731
    else:
        get_settings = load_settings

    mcp = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        log_level="WARNING",
    )

    register_database_tools(mcp, get_settings)
    register_sql_tools(mcp, get_settings)
    register_reporting_tools(mcp, get_settings)
    return mcp


def run_stdio_server(settings: AppSettings | None = None) -> int:
    """Initialise file-only logging and run the MCP server over stdio."""
    initial_settings = settings or load_settings()
    # CRITICAL: console=False ensures zero log output pollutes stdout/stderr JSON-RPC pipes
    setup_logging(initial_settings, process_name="mcp_server", console=False)

    provider = (lambda: settings) if settings is not None else load_settings
    server = create_mcp_server(settings_provider=provider)
    log.info("Starting MCP stdio server '%s'", SERVER_NAME)
    server.run(transport="stdio")
    return 0


def main() -> int:
    return run_stdio_server()


if __name__ == "__main__":
    raise SystemExit(main())

