"""SQLite connection helpers.

Two kinds of connection are used in the application:

* ``connect_readonly`` - used by the agent / MCP tools. Opened through a
  ``file:`` URI with ``mode=ro`` so SQLite itself refuses any write.
* ``connect_readwrite`` - used only by the dataset importer to build a *new*
  database file. Foreign key enforcement is always switched on.

Paths may contain spaces and characters such as ``)`` (the project lives in
such a folder), so URIs are always percent-encoded.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseNotFoundError(FileNotFoundError):
    """Raised when a database file that must exist is missing."""


def sqlite_uri(path: str | Path, **params: str) -> str:
    """Build a percent-encoded ``file:`` URI for ``path`` with query ``params``."""
    abs_path = Path(path).expanduser().resolve().as_posix()
    uri = "file:" + quote(abs_path, safe="/:")
    if params:
        uri += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return uri


def connect_readonly(path: str | Path, *, immutable: bool = False,
                     check_same_thread: bool = True) -> sqlite3.Connection:
    """Open ``path`` strictly read-only.

    ``immutable=True`` additionally tells SQLite the file cannot change, which
    guarantees no journal/lock files are created. Use it for reference data
    that must never be touched (e.g. ``data/raw/ecommerce.sqlite``).
    """
    p = Path(path)
    if not p.is_file():
        raise DatabaseNotFoundError(f"Database not found: {p}")
    params = {"mode": "ro"}
    if immutable:
        params["immutable"] = "1"
    con = sqlite3.connect(sqlite_uri(p, **params), uri=True,
                          check_same_thread=check_same_thread)
    con.execute("PRAGMA query_only = ON")
    return con


def connect_readwrite(path: str | Path) -> sqlite3.Connection:
    """Open (or create) ``path`` for writing with manual transaction control.

    ``isolation_level=None`` disables Python's implicit transactions so the
    importer controls ``BEGIN`` / ``SAVEPOINT`` / ``COMMIT`` explicitly.
    """
    con = sqlite3.connect(str(Path(path)), isolation_level=None)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def is_valid_identifier(name: str) -> bool:
    """True if ``name`` is a plain SQL identifier (letters, digits, underscore)."""
    return bool(_IDENTIFIER_RE.match(name or ""))


def quote_identifier(name: str) -> str:
    """Quote an identifier for safe interpolation into SQL."""
    if "\x00" in name:
        raise ValueError("Identifier contains NUL byte")
    return '"' + name.replace('"', '""') + '"'

