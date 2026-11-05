"""MCP SQL validation, preparation, and read-only execution tools.

Security architecture:
* ``validate_and_prepare_sql`` performs pure-Python lexical/structural analysis
  followed by SQLite ``EXPLAIN QUERY PLAN`` compilation on a read-only
  authorizer-guarded connection — validating syntax, table names, and column
  names in sub-millisecond time WITHOUT executing the SQL query.
* ``execute_readonly_sql`` ALWAYS re-runs ``validate_and_prepare_sql`` before
  delegating to ``execute_readonly_query`` (which enforces ``mode=ro``,
  ``PRAGMA query_only=ON``, C-level authorizer, execution timeout, and row cap).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from config.settings import AppSettings
from database.connection import DatabaseNotFoundError, connect_readonly
from database.query_executor import (
    QueryCancelledError,
    QueryExecutionError,
    QueryTimeoutError,
    _readonly_authorizer,
    execute_readonly_query,
)

log = logging.getLogger(__name__)

# Complexity & safety limits
MAX_SQL_LENGTH = 8_000
MAX_JOINS = 12
MAX_SUBQUERY_DEPTH = 10
MAX_PAREN_DEPTH = 30
MAX_COMPOUND_OPS = 6

FORBIDDEN_KEYWORDS: frozenset[str] = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "VACUUM",
        "REINDEX",
        "ANALYZE",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "TRANSACTION",
        "RETURNING",
        "INTO",
        "EXPLAIN",
    }
)

BLOCKED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "LOAD_EXTENSION",
        "FTS3_TOKENIZER",
    }
)


# ---------------------------------------------------------------------------
# Pure-Python SQLite lexical scanner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SQLToken:
    kind: str  # "WORD", "STRING", "QIDENT", "SEMI", "LPAREN", "RPAREN", "COMMA", "OTHER"
    value: str
    upper: str


class SQLValidationError(ValueError):
    """Structured SQL validation error carrying an ``error_code``."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


def _tokenize_sql(sql: str) -> list[_SQLToken]:
    """Scan ``sql`` into tokens while stripping comments and checking quote balance."""
    tokens: list[_SQLToken] = []
    n = len(sql)
    i = 0

    while i < n:
        ch = sql[i]

        # Whitespace
        if ch.isspace():
            i += 1
            continue

        # Single-line comment: -- ... \n
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            nl = sql.find("\n", i + 2)
            i = n if nl == -1 else nl + 1
            continue

        # Block comment: /* ... */
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            end = sql.find("*/", i + 2)
            if end == -1:
                raise SQLValidationError(
                    "Unclosed block comment '/*' in SQL query",
                    error_code="SYNTAX_ERROR",
                )
            i = end + 2
            continue

        # Single-quoted string literal: '...' with '' escape
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                raise SQLValidationError(
                    "Unclosed string literal in SQL query",
                    error_code="SYNTAX_ERROR",
                )
            lit = sql[i : j + 1]
            tokens.append(_SQLToken("STRING", lit, ""))
            i = j + 1
            continue

        # Double-quoted or backtick-quoted identifier
        if ch in {'"', "`"}:
            quote_ch = ch
            j = i + 1
            parts: list[str] = []
            while j < n:
                if sql[j] == quote_ch:
                    if j + 1 < n and sql[j + 1] == quote_ch:
                        parts.append(quote_ch)
                        j += 2
                        continue
                    break
                parts.append(sql[j])
                j += 1
            if j >= n:
                raise SQLValidationError(
                    f"Unclosed quoted identifier ({quote_ch}) in SQL query",
                    error_code="SYNTAX_ERROR",
                )
            ident = "".join(parts)
            tokens.append(_SQLToken("QIDENT", ident, ident.upper()))
            i = j + 1
            continue

        # Bracket-quoted identifier: [...]
        if ch == "[":
            end = sql.find("]", i + 1)
            if end == -1:
                raise SQLValidationError(
                    "Unclosed bracket identifier '[' in SQL query",
                    error_code="SYNTAX_ERROR",
                )
            ident = sql[i + 1 : end]
            tokens.append(_SQLToken("QIDENT", ident, ident.upper()))
            i = end + 1
            continue

        # Punctuation of structural interest
        if ch == ";":
            tokens.append(_SQLToken("SEMI", ";", ";"))
            i += 1
            continue
        if ch == "(":
            tokens.append(_SQLToken("LPAREN", "(", "("))
            i += 1
            continue
        if ch == ")":
            tokens.append(_SQLToken("RPAREN", ")", ")"))
            i += 1
            continue
        if ch == ",":
            tokens.append(_SQLToken("COMMA", ",", ","))
            i += 1
            continue

        # Unquoted identifier / keyword
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] in {"_", "$"}):
                j += 1
            word = sql[i:j]
            tokens.append(_SQLToken("WORD", word, word.upper()))
            i = j
            continue

        # Numbers & operators
        j = i + 1
        while (
            j < n
            and not sql[j].isspace()
            and not sql[j].isalpha()
            and sql[j] not in {"_", "'", '"', "`", "[", ";", "(", ")", ",", "-", "/"}
        ):
            j += 1
        sym = sql[i:j]
        tokens.append(_SQLToken("OTHER", sym, sym.upper()))
        i = j

    return tokens


def _verify_cte_leads_to_select(tokens: list[_SQLToken]) -> None:
    """Verify a ``WITH ...`` query defines CTEs and concludes with ``SELECT``."""
    idx = 1  # skip 'WITH'
    n = len(tokens)
    if idx < n and tokens[idx].kind == "WORD" and tokens[idx].upper == "RECURSIVE":
        idx += 1

    while True:
        # Expect CTE name
        if idx >= n or tokens[idx].kind not in {"WORD", "QIDENT"}:
            raise SQLValidationError(
                "Malformed CTE: expected CTE table name after WITH/comma",
                error_code="SYNTAX_ERROR",
            )
        idx += 1

        # Optional column list: ( col1, col2, ... )
        if idx < n and tokens[idx].kind == "LPAREN":
            depth = 1
            idx += 1
            while idx < n and depth > 0:
                if tokens[idx].kind == "LPAREN":
                    depth += 1
                elif tokens[idx].kind == "RPAREN":
                    depth -= 1
                idx += 1
            if depth != 0:
                raise SQLValidationError(
                    "Unbalanced parentheses in CTE column list",
                    error_code="SYNTAX_ERROR",
                )

        # Expect AS
        if idx >= n or tokens[idx].kind != "WORD" or tokens[idx].upper != "AS":
            raise SQLValidationError(
                "Malformed CTE: expected AS before CTE subquery",
                error_code="SYNTAX_ERROR",
            )
        idx += 1

        # Optional [NOT] MATERIALIZED in SQLite 3.35+
        if idx < n and tokens[idx].kind == "WORD" and tokens[idx].upper == "NOT":
            idx += 1
        if idx < n and tokens[idx].kind == "WORD" and tokens[idx].upper == "MATERIALIZED":
            idx += 1

        # Expect ( <cte query> )
        if idx >= n or tokens[idx].kind != "LPAREN":
            raise SQLValidationError(
                "Malformed CTE: expected '(' starting CTE subquery",
                error_code="SYNTAX_ERROR",
            )
        depth = 1
        idx += 1
        while idx < n and depth > 0:
            if tokens[idx].kind == "LPAREN":
                depth += 1
            elif tokens[idx].kind == "RPAREN":
                depth -= 1
            idx += 1
        if depth != 0:
            raise SQLValidationError(
                "Unbalanced parentheses in CTE body",
                error_code="SYNTAX_ERROR",
            )

        # Comma means another CTE follows; otherwise main statement must start
        if idx < n and tokens[idx].kind == "COMMA":
            idx += 1
            continue
        break

    if idx >= n or tokens[idx].kind != "WORD" or tokens[idx].upper != "SELECT":
        got = tokens[idx].value if idx < n else "<end of query>"
        raise SQLValidationError(
            f"CTE query must be followed by a SELECT statement; got '{got}'",
            error_code="FORBIDDEN_STATEMENT",
        )


def _strip_trailing_semicolons(sql: str) -> str:
    """Remove trailing semicolon (and trailing comments/whitespace around it)."""
    s = sql.strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    return s


# ---------------------------------------------------------------------------
# Public SQL validator & preparer
# ---------------------------------------------------------------------------


@dataclass
class PreparedSQL:
    valid: bool
    sql_query: str
    statement_type: str  # "SELECT" or "CTE_SELECT"
    referenced_tables: list[str] = field(default_factory=list)
    referenced_columns: list[str] = field(default_factory=list)
    query_plan: list[str] = field(default_factory=list)
    join_count: int = 0
    subquery_depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = "ok" if self.valid else "error"
        return payload


def validate_and_prepare_sql(
    sql_query: str,
    db_path: str | Path | None = None,
    *,
    max_sql_length: int = MAX_SQL_LENGTH,
    max_joins: int = MAX_JOINS,
    max_subquery_depth: int = MAX_SUBQUERY_DEPTH,
    max_compound_ops: int = MAX_COMPOUND_OPS,
) -> PreparedSQL:
    """Validate ``sql_query`` without executing it; raise ``SQLValidationError`` on failure."""
    if not isinstance(sql_query, str):
        raise SQLValidationError(
            "SQL query must be a string", error_code="EMPTY_QUERY"
        )
    if "\x00" in sql_query:
        raise SQLValidationError(
            "SQL query must not contain NUL bytes", error_code="INVALID_CHARACTER"
        )

    raw_stripped = sql_query.strip()
    if not raw_stripped:
        raise SQLValidationError(
            "SQL query must not be empty", error_code="EMPTY_QUERY"
        )
    if len(raw_stripped) > max_sql_length:
        raise SQLValidationError(
            f"SQL query length ({len(raw_stripped)} chars) exceeds maximum allowed ({max_sql_length} chars)",
            error_code="COMPLEXITY_LIMIT",
        )

    tokens = _tokenize_sql(raw_stripped)
    if not tokens:
        raise SQLValidationError(
            "SQL query contains only comments or whitespace",
            error_code="EMPTY_QUERY",
        )

    # Reject multiple statements; allow at most one trailing semicolon
    semi_positions = [idx for idx, tok in enumerate(tokens) if tok.kind == "SEMI"]
    if len(semi_positions) > 1 or (
        len(semi_positions) == 1 and semi_positions[0] != len(tokens) - 1
    ):
        raise SQLValidationError(
            "Multiple SQL statements are prohibited; submit a single SELECT query",
            error_code="MULTIPLE_STATEMENTS",
        )
    if semi_positions:
        tokens = tokens[:-1]
        if not tokens:
            raise SQLValidationError(
                "SQL query must not be empty", error_code="EMPTY_QUERY"
            )

    # First token must be SELECT or WITH
    first = tokens[0]
    if first.kind != "WORD" or first.upper not in {"SELECT", "WITH"}:
        raise SQLValidationError(
            f"Only read-only SELECT or WITH (CTE) queries are allowed; got '{first.value}'",
            error_code="FORBIDDEN_STATEMENT",
        )

    statement_type = "CTE_SELECT" if first.upper == "WITH" else "SELECT"

    # Scan all tokens for forbidden keywords, blocked functions, paren balance, and complexity
    paren_depth = 0
    max_seen_paren = 0
    subquery_stack: list[bool] = []
    max_seen_subquery = 0
    join_count = 0
    compound_count = 0

    for idx, tok in enumerate(tokens):
        if tok.kind == "WORD":
            if tok.upper in FORBIDDEN_KEYWORDS:
                raise SQLValidationError(
                    f"Forbidden SQL keyword '{tok.upper}' is not allowed in read-only mode",
                    error_code="FORBIDDEN_STATEMENT",
                )
            if tok.upper == "JOIN":
                join_count += 1
            elif tok.upper in {"UNION", "INTERSECT", "EXCEPT"}:
                compound_count += 1

        if tok.kind in {"WORD", "QIDENT"} and tok.upper in BLOCKED_FUNCTIONS:
            if idx + 1 < len(tokens) and tokens[idx + 1].kind == "LPAREN":
                raise SQLValidationError(
                    f"Blocked SQLite function '{tok.value}' is not permitted",
                    error_code="FORBIDDEN_FUNCTION",
                )

        if tok.kind == "LPAREN":
            paren_depth += 1
            max_seen_paren = max(max_seen_paren, paren_depth)
            is_subq = (
                idx + 1 < len(tokens)
                and tokens[idx + 1].kind == "WORD"
                and tokens[idx + 1].upper in {"SELECT", "WITH"}
            )
            subquery_stack.append(is_subq)
            cur_subq = sum(1 for flag in subquery_stack if flag)
            max_seen_subquery = max(max_seen_subquery, cur_subq)
        elif tok.kind == "RPAREN":
            paren_depth -= 1
            if paren_depth < 0:
                raise SQLValidationError(
                    "Unbalanced closing parenthesis ')' in SQL query",
                    error_code="SYNTAX_ERROR",
                )
            if subquery_stack:
                subquery_stack.pop()

    if paren_depth != 0:
        raise SQLValidationError(
            "Unbalanced opening parenthesis '(' in SQL query",
            error_code="SYNTAX_ERROR",
        )

    if statement_type == "CTE_SELECT":
        _verify_cte_leads_to_select(tokens)

    if max_seen_paren > MAX_PAREN_DEPTH:
        raise SQLValidationError(
            f"Expression parenthesis nesting ({max_seen_paren}) exceeds limit ({MAX_PAREN_DEPTH})",
            error_code="COMPLEXITY_LIMIT",
        )
    if max_seen_subquery > max_subquery_depth:
        raise SQLValidationError(
            f"Subquery nesting depth ({max_seen_subquery}) exceeds limit ({max_subquery_depth})",
            error_code="COMPLEXITY_LIMIT",
        )
    if join_count > max_joins:
        raise SQLValidationError(
            f"Query JOIN count ({join_count}) exceeds safety limit ({max_joins})",
            error_code="COMPLEXITY_LIMIT",
        )
    if compound_count > max_compound_ops:
        raise SQLValidationError(
            f"Compound SELECT operations ({compound_count}) exceed limit ({max_compound_ops})",
            error_code="COMPLEXITY_LIMIT",
        )

    normalized_sql = _strip_trailing_semicolons(raw_stripped)

    # Zero-execution SQLite compiler & schema check via EXPLAIN QUERY PLAN
    ref_tables: list[str] = []
    ref_columns: list[str] = []
    plan_steps: list[str] = []

    if db_path is not None:
        seen_tables: set[str] = set()
        seen_cols: set[str] = set()

        def _capturing_authorizer(
            action: int,
            arg1: str | None,
            arg2: str | None,
            dbname: str | None,
            source: str | None,
        ) -> int:
            verdict = _readonly_authorizer(action, arg1, arg2, dbname, source)
            if verdict == sqlite3.SQLITE_OK and action == sqlite3.SQLITE_READ and arg1:
                if not arg1.lower().startswith("sqlite_"):
                    if arg1 not in seen_tables:
                        seen_tables.add(arg1)
                        ref_tables.append(arg1)
                    if arg2:
                        qual = f"{arg1}.{arg2}"
                        if qual not in seen_cols:
                            seen_cols.add(qual)
                            ref_columns.append(qual)
            return verdict

        con = connect_readonly(db_path)
        try:
            con.set_authorizer(_capturing_authorizer)
            raw_plan = con.execute("EXPLAIN QUERY PLAN " + normalized_sql).fetchall()
            plan_steps = [str(row[3]) for row in raw_plan if len(row) >= 4]
        except sqlite3.OperationalError as exc:
            msg = str(exc)
            low = msg.lower()
            if any(
                phrase in low
                for phrase in ("no such table", "no such column", "ambiguous column")
            ):
                raise SQLValidationError(
                    f"Schema validation error: {msg}",
                    error_code="SCHEMA_ERROR",
                ) from exc
            if "not authorized" in low:
                raise SQLValidationError(
                    f"Query blocked by read-only authorizer: {msg}",
                    error_code="FORBIDDEN_STATEMENT",
                ) from exc
            raise SQLValidationError(
                f"SQL syntax/compilation error: {msg}",
                error_code="SYNTAX_ERROR",
            ) from exc
        except sqlite3.DatabaseError as exc:
            msg = str(exc)
            if "not authorized" in msg.lower():
                raise SQLValidationError(
                    f"Query blocked by read-only authorizer: {msg}",
                    error_code="FORBIDDEN_STATEMENT",
                ) from exc
            raise SQLValidationError(
                f"SQL validation failed: {msg}",
                error_code="SYNTAX_ERROR",
            ) from exc
        finally:
            con.close()

    return PreparedSQL(
        valid=True,
        sql_query=normalized_sql,
        statement_type=statement_type,
        referenced_tables=ref_tables,
        referenced_columns=ref_columns,
        query_plan=plan_steps,
        join_count=join_count,
        subquery_depth=max_seen_subquery,
    )


# ---------------------------------------------------------------------------
# MCP tool implementations
# ---------------------------------------------------------------------------


def prepare_sql_query_impl(
    settings: AppSettings,
    sql_query: str,
) -> dict[str, Any]:
    """Validate and prepare ``sql_query`` without executing it."""
    try:
        prepared = validate_and_prepare_sql(
            sql_query,
            db_path=settings.database_path,
        )
        return prepared.to_dict()
    except DatabaseNotFoundError as exc:
        return {
            "status": "error",
            "valid": False,
            "sql_query": sql_query,
            "error_code": "DATABASE_NOT_FOUND",
            "error": str(exc),
        }
    except SQLValidationError as exc:
        return {
            "status": "error",
            "valid": False,
            "sql_query": sql_query,
            "error_code": exc.error_code,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error during prepare_sql_query")
        return {
            "status": "error",
            "valid": False,
            "sql_query": sql_query,
            "error_code": "VALIDATION_ERROR",
            "error": f"Unexpected SQL validation error: {exc}",
        }


def execute_readonly_sql_impl(
    settings: AppSettings,
    sql_query: str,
    row_limit: int | None = None,
) -> dict[str, Any]:
    """Independently validate ``sql_query`` and execute it in read-only mode."""
    max_configured = int(settings.database.max_result_rows)
    if row_limit is not None:
        if not isinstance(row_limit, int) or isinstance(row_limit, bool) or row_limit < 1:
            return {
                "status": "error",
                "error_code": "INVALID_ARGUMENT",
                "error": "row_limit must be a positive integer (>= 1)",
                "columns": [],
                "rows": [],
                "record_count": 0,
            }
        effective_limit = min(row_limit, max_configured)
    else:
        effective_limit = max_configured

    # Mandatory independent SQL validation prior to execution
    try:
        prepared = validate_and_prepare_sql(
            sql_query,
            db_path=settings.database_path,
        )
    except DatabaseNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "DATABASE_NOT_FOUND",
            "error": str(exc),
            "columns": [],
            "rows": [],
            "record_count": 0,
        }
    except SQLValidationError as exc:
        return {
            "status": "error",
            "error_code": exc.error_code,
            "error": str(exc),
            "columns": [],
            "rows": [],
            "record_count": 0,
        }

    try:
        result = execute_readonly_query(
            settings.database_path,
            prepared.sql_query,
            max_rows=effective_limit,
            timeout_s=float(settings.database.query_timeout_s),
        )
    except QueryTimeoutError as exc:
        return {
            "status": "error",
            "error_code": "QUERY_TIMEOUT",
            "error": str(exc),
            "sql_query": prepared.sql_query,
            "columns": [],
            "rows": [],
            "record_count": 0,
        }
    except (QueryCancelledError, QueryExecutionError, DatabaseNotFoundError) as exc:
        return {
            "status": "error",
            "error_code": "EXECUTION_ERROR",
            "error": str(exc),
            "sql_query": prepared.sql_query,
            "columns": [],
            "rows": [],
            "record_count": 0,
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error during execute_readonly_sql")
        return {
            "status": "error",
            "error_code": "EXECUTION_ERROR",
            "error": f"Unexpected SQL execution error: {exc}",
            "sql_query": prepared.sql_query,
            "columns": [],
            "rows": [],
            "record_count": 0,
        }

    return {
        "status": "ok",
        "sql_query": result.sql,
        "columns": result.columns,
        "rows": result.rows,
        "record_count": result.row_count,
        "truncated": result.truncated,
        "effective_row_limit": effective_limit,
        "duration_ms": result.duration_ms,
        "referenced_tables": prepared.referenced_tables,
    }


def register_sql_tools(
    mcp: FastMCP,
    get_settings: Callable[[], AppSettings],
) -> None:
    """Register ``prepare_sql_query`` and ``execute_readonly_sql`` on ``mcp``."""

    @mcp.tool(
        name="prepare_sql_query",
        description=(
            "Validate a proposed SQL query for read-only safety, single-statement compliance, "
            "SQLite syntax, and valid table/column references WITHOUT executing the query. "
            "Always call this before executing SQL."
        ),
    )
    def prepare_sql_query(sql_query: str) -> dict[str, Any]:
        return prepare_sql_query_impl(get_settings(), sql_query=sql_query)

    @mcp.tool(
        name="execute_readonly_sql",
        description=(
            "Independently validate and execute a read-only SELECT/CTE SQL query against "
            "the local SQLite database with timeout and row-limit protections. "
            "Returns column names, rows, record_count, and duration_ms."
        ),
    )
    def execute_readonly_sql(
        sql_query: str,
        row_limit: int | None = None,
    ) -> dict[str, Any]:
        return execute_readonly_sql_impl(
            get_settings(),
            sql_query=sql_query,
            row_limit=row_limit,
        )

