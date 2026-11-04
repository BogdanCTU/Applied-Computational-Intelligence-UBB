"""Verify the local runtime environment for the Local Report SQL Agent.

Checks (all local, no external network calls):
  * Python version (3.13 expected)
  * Required Python packages and the official MCP SDK
  * Ollama server reachability and the configured model
  * SQLite database presence

Usage:
    python scripts/verify_environment.py
Exit code 0 = all required checks passed, 1 = at least one failed.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import load_settings  # noqa: E402

OK, WARN, FAIL = "[ OK ]", "[WARN]", "[FAIL]"
REQUIRED_PACKAGES = {
    "PySide6": "PySide6",
    "mcp": "mcp",
    "httpx": "httpx",
    "reportlab": "reportlab",
    "pytest": "pytest",
}


def check_python() -> bool:
    v = sys.version_info
    good = (v.major, v.minor) == (3, 13)
    print(f"{OK if good else FAIL} Python {sys.version.split()[0]} ({sys.executable})")
    return good


def check_packages() -> bool:
    all_ok = True
    for module, dist in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module)
            print(f"{OK} {dist} {md.version(dist)}")
        except Exception as exc:  # noqa: BLE001
            print(f"{FAIL} {dist}: {exc}")
            all_ok = False
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
        from mcp.client.stdio import stdio_client  # noqa: F401
        from mcp import ClientSession, StdioServerParameters  # noqa: F401

        print(f"{OK} MCP SDK exposes FastMCP server + stdio client APIs")
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} MCP SDK API check: {exc}")
        all_ok = False
    return all_ok


def _get_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (local URL)
        return json.loads(resp.read().decode("utf-8"))


def check_ollama(host: str, model: str) -> tuple[bool, bool]:
    try:
        version = _get_json(f"{host}/api/version").get("version", "?")
        print(f"{OK} Ollama reachable at {host} (version {version})")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"{FAIL} Ollama not reachable at {host}: {exc}")
        return False, False
    names = [m.get("name", "") for m in _get_json(f"{host}/api/tags").get("models", [])]
    wanted = model if ":" in model else f"{model}:latest"
    if wanted in names:
        print(f"{OK} Model '{model}' is installed")
        return True, True
    print(f"{FAIL} Model '{model}' is NOT installed. Installed: {names or 'none'}")
    print(f"       Run:  ollama pull {model}")
    return True, False


EXPECTED_DB_SHA256 = "c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934"


def check_database(path: Path) -> bool:
    if not path.exists():
        print(f"{WARN} Database not found at {path} (run scripts/import_dataset.py)")
        return False

    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()

    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        row_count = sum(
            con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] for t in tables
        )
        print(f"{OK} Database {path.name}: {len(tables)} tables, {row_count:,} total records")
    finally:
        con.close()

    if actual_hash == EXPECTED_DB_SHA256:
        print(f"{OK} SHA-256 integrity verified: {actual_hash[:16]}...")
        return True
    else:
        print(f"{WARN} SHA-256 checksum mismatch: {actual_hash} (expected {EXPECTED_DB_SHA256})")
        return False


def main() -> int:
    settings = load_settings()
    print("== Local Report SQL Agent: environment verification ==")
    py = check_python()
    pk = check_packages()
    ol, model = check_ollama(settings.ollama.host.rstrip("/"), settings.ollama.model)
    check_database(settings.database_path)  # warning only
    required_ok = py and pk and ol and model
    print("== RESULT:", "PASS" if required_ok else "FAIL", "==")
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

