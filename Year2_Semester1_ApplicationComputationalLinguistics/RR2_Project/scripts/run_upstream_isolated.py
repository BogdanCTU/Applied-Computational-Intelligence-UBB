"""Hermetically isolated execution harness for the upstream Agent-OM repository.

Executes `original_repo/` (`om_ontology_to_csv.py`, `om_csv_to_database.py`,
`om_database_matching.py`) using `.venv_upstream` and the isolated PostgreSQL
database `agent_om_upstream` without creating, modifying, or deleting a single
file inside `original_repo/` or touching the `agent_om_local` database.

Isolation layers enforced simultaneously:
1. Pre- and post-run SHA-256 verification of `original_repo/` and historical outputs.
2. Separate working directory `agent_om_local/output/replication_runs/<experiment_id>/`.
3. `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPYCACHEPREFIX` inside `<run_dir>/_pycache`.
4. `sitecustomize.py` AST-level `MetaPathFinder` on `run_config` replacing OpenAI
   constructors, paths, and DB connection string in memory prior to execution.
5. `sys.addaudithook` kernel/interpreter guard blocking any filesystem write to
   `original_repo/` or historical `output/step*` artifacts, and blocking any
   non-loopback (`!= 127.0.0.1` / `::1`) socket connection.
6. Local loopback `LlamaEmbeddingBridge` serving genuine 4096-dim `llama3:8b`
   embeddings on Ollama 0.40.13 while sequencing VRAM usage cleanly within 8 GB.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2

SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = LOCAL_ROOT.parent
ORIGINAL_REPO = WORKSPACE_ROOT / "original_repo"

if str(LOCAL_ROOT) not in sys.path:
    sys.path.insert(0, str(LOCAL_ROOT))

from scripts.verify_repo_integrity import build_directory_manifest, compare_manifests  # noqa: E402
from src.utils.llama_embed_bridge import LlamaEmbeddingBridge  # noqa: E402

PROTECTED_DB_NAME = "agent_om_local"
DEFAULT_UPSTREAM_DB = "agent_om_upstream"
DEFAULT_STAGE_SCRIPTS = (
    "om_ontology_to_csv.py",
    "om_csv_to_database.py",
    "om_database_matching.py",
)

SITECUSTOMIZE_TEMPLATE = '''"""Auto-loaded isolation bootstrap for upstream Agent-OM subprocesses."""
from __future__ import annotations

import ast
import importlib.abc
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

_BOOTSTRAP_DIR = Path(__file__).resolve().parent
_OVERRIDES = json.loads((_BOOTSTRAP_DIR / "overrides.json").read_text(encoding="utf-8"))
_PROTECTED_ROOTS = [Path(p).resolve() for p in _OVERRIDES["protected_roots"]]
_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost", ""}
_STAGE_NAME = os.environ.get("AGENT_OM_UPSTREAM_STAGE", "unknown")
_TELEMETRY_PATH = Path(_OVERRIDES["telemetry_path"])


def _is_under_protected(candidate: str | os.PathLike[str]) -> bool:
    try:
        resolved = Path(candidate).resolve()
    except Exception:
        return False
    for root in _PROTECTED_ROOTS:
        if resolved == root or root in resolved.parents:
            return True
    return False


def _audit_guard(event: str, args: tuple[object, ...]) -> None:
    if event == "open" and len(args) >= 2:
        path_arg, mode_arg = args[0], args[1]
        if isinstance(path_arg, (str, os.PathLike)) and isinstance(mode_arg, str):
            if any(flag in mode_arg for flag in ("w", "a", "x", "+")):
                if _is_under_protected(path_arg):
                    raise PermissionError(
                        f"Audit guard blocked write open({path_arg!r}, {mode_arg!r}) inside protected path."
                    )
    elif event in ("os.mkdir", "os.remove", "os.rmdir", "os.unlink") and len(args) >= 1:
        path_arg = args[0]
        if isinstance(path_arg, (str, os.PathLike)) and _is_under_protected(path_arg):
            raise PermissionError(f"Audit guard blocked {event}({path_arg!r}) inside protected path.")
    elif event == "os.rename" and len(args) >= 2:
        for path_arg in (args[0], args[1]):
            if isinstance(path_arg, (str, os.PathLike)) and _is_under_protected(path_arg):
                raise PermissionError(f"Audit guard blocked os.rename targeting protected path: {path_arg!r}")
    elif event == "socket.connect" and len(args) >= 2:
        address = args[1]
        if isinstance(address, tuple) and len(address) >= 1:
            host = str(address[0])
            if host not in _ALLOWED_HOSTS and not host.startswith("127."):
                raise PermissionError(
                    f"Audit guard blocked external socket connection to {address!r}; loopback only."
                )


sys.addaudithook(_audit_guard)


def _make_telemetry_callback():
    from langchain_core.callbacks import BaseCallbackHandler

    class _TelemetryCallback(BaseCallbackHandler):
        def __init__(self) -> None:
            super().__init__()
            self._t0: float = 0.0

        def on_llm_start(self, serialized, prompts, **kwargs) -> None:
            self._t0 = time.perf_counter()

        def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
            self._t0 = time.perf_counter()

        def on_llm_end(self, response, **kwargs) -> None:
            elapsed_ms = (time.perf_counter() - self._t0) * 1000.0 if self._t0 else 0.0
            prompt_tokens = 0
            completion_tokens = 0
            text_preview = ""
            try:
                for gen_list in response.generations:
                    for gen in gen_list:
                        if not text_preview:
                            text_preview = str(getattr(gen, "text", ""))[:160]
                        msg = getattr(gen, "message", None)
                        meta = getattr(msg, "response_metadata", None) or getattr(gen, "generation_info", None) or {}
                        prompt_tokens += int(meta.get("prompt_eval_count") or 0)
                        completion_tokens += int(meta.get("eval_count") or 0)
            except Exception:
                pass
            record = {
                "stage": _STAGE_NAME,
                "ts_utc": time.time(),
                "elapsed_ms": round(elapsed_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "preview": text_preview,
            }
            with _TELEMETRY_PATH.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\\n")

    return _TelemetryCallback()


def _build_override_llm():
    from langchain_community.chat_models import ChatOllama

    kwargs = {
        "model": _OVERRIDES["llm_model"],
        "base_url": _OVERRIDES["ollama_chat_base_url"],
        "temperature": float(_OVERRIDES["temperature"]),
        "seed": int(_OVERRIDES["seed"]),
        "top_p": float(_OVERRIDES["top_p"]),
        "top_k": int(_OVERRIDES["llm_top_k"]),
        "repeat_penalty": float(_OVERRIDES["repeat_penalty"]),
        "callbacks": [_make_telemetry_callback()],
    }
    if _OVERRIDES.get("num_ctx"):
        kwargs["num_ctx"] = int(_OVERRIDES["num_ctx"])
    return ChatOllama(**kwargs)


def _build_override_embeddings():
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=_OVERRIDES["embedding_model"],
        base_url=_OVERRIDES["ollama_embed_base_url"],
    )


class _RunConfigTransformer(ast.NodeTransformer):
    def __init__(self, scalar_overrides: dict[str, object]) -> None:
        super().__init__()
        self.scalar_overrides = scalar_overrides

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "llm":
                new_val = ast.parse("_build_override_llm()", mode="eval").body
                return ast.copy_location(ast.Assign(targets=node.targets, value=new_val), node)
            if name == "embeddings_service":
                new_val = ast.parse("_build_override_embeddings()", mode="eval").body
                return ast.copy_location(ast.Assign(targets=node.targets, value=new_val), node)
            if name in self.scalar_overrides:
                new_val = ast.Constant(value=self.scalar_overrides[name])
                return ast.copy_location(ast.Assign(targets=node.targets, value=new_val), node)
        return node


class _RunConfigLoader(importlib.abc.Loader):
    def __init__(self, origin: Path) -> None:
        self.origin = origin

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        source_text = self.origin.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(self.origin))
        transformer = _RunConfigTransformer(_OVERRIDES["scalars"])
        patched_tree = ast.fix_missing_locations(transformer.visit(tree))
        module.__dict__["_build_override_llm"] = _build_override_llm
        module.__dict__["_build_override_embeddings"] = _build_override_embeddings
        code = compile(patched_tree, str(self.origin), "exec")
        exec(code, module.__dict__)

        smoke_limit = int(_OVERRIDES.get("smoke_limit") or 0)
        if smoke_limit > 0:
            import util as _util

            if not getattr(_util, "_smoke_wrapped", False):
                _orig_remove = _util.remove_exceptions

                def _smoke_remove(c1, c2, p1, p2):
                    c1, c2, p1, p2 = _orig_remove(c1, c2, p1, p2)
                    return c1[:smoke_limit], c2[:smoke_limit], [], []

                _util.remove_exceptions = _smoke_remove
                _util._smoke_wrapped = True


class _RunConfigFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        if fullname != "run_config":
            return None
        origin = Path(_OVERRIDES["original_repo"]) / "run_config.py"
        if not origin.is_file():
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _RunConfigLoader(origin),
            origin=str(origin),
        )


sys.meta_path.insert(0, _RunConfigFinder())
'''


def _verify_postgres_isolation(
    host: str,
    port: int,
    user: str,
    target_db: str,
) -> dict[str, Any]:
    if host != "127.0.0.1":
        raise ValueError(f"PostgreSQL host must be strictly 127.0.0.1, got {host!r}")
    if target_db == PROTECTED_DB_NAME:
        raise PermissionError(
            f"Refusing to run upstream pipeline against protected database {PROTECTED_DB_NAME!r}!"
        )

    conn = psycopg2.connect(host=host, port=port, user=user, dbname="postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SHOW listen_addresses;")
    listen_addr = cur.fetchone()[0]
    if listen_addr != "127.0.0.1":
        conn.close()
        raise PermissionError(f"PostgreSQL listen_addresses is {listen_addr!r}, expected '127.0.0.1'")

    cur.execute(
        "SELECT pid, state, query FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();",
        (target_db,),
    )
    other_sessions = [
        {"pid": r[0], "state": r[1], "query": (r[2] or "")[:120]}
        for r in cur.fetchall()
        if r[1] not in (None, "idle")
    ]
    if other_sessions:
        conn.close()
        raise RuntimeError(
            f"Database {target_db!r} has active concurrent sessions; aborting: {other_sessions}"
        )

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{target_db}";')
    conn.close()

    # Snapshot protected agent_om_local table counts read-only
    local_counts: dict[str, int] = {}
    conn_local = psycopg2.connect(host=host, port=port, user=user, dbname=PROTECTED_DB_NAME)
    conn_local.set_session(readonly=True, autocommit=True)
    cur_local = conn_local.cursor()
    cur_local.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
    for (tbl,) in cur_local.fetchall():
        cur_local.execute(f'SELECT COUNT(*) FROM "{tbl}";')
        local_counts[tbl] = int(cur_local.fetchone()[0])
    conn_local.close()

    return {
        "host": host,
        "port": port,
        "listen_addresses": listen_addr,
        "target_db": target_db,
        "protected_db": PROTECTED_DB_NAME,
        "protected_db_counts": local_counts,
    }


def _archive_upstream_db_tables(
    host: str,
    port: int,
    user: str,
    dbname: str,
    run_dir: Path,
) -> dict[str, Any]:
    conn = psycopg2.connect(host=host, port=port, user=user, dbname=dbname)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
    tables = [r[0] for r in cur.fetchall()]
    counts: dict[str, int] = {}
    dims: dict[str, int | None] = {}
    for tbl in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{tbl}";')
        counts[tbl] = int(cur.fetchone()[0])
        if tbl in ("syntactic_matching", "lexical_matching", "semantic_matching") and counts[tbl] > 0:
            cur.execute(f'SELECT vector_dims(embedding) FROM "{tbl}" LIMIT 1;')
            row = cur.fetchone()
            dims[tbl] = int(row[0]) if row else None

    if "ontology_matching" in tables:
        cur.execute(
            "SELECT entity_id, entity_uri, source_or_target, entity_type, "
            "syntactic_matching, lexical_matching, semantic_matching "
            "FROM ontology_matching ORDER BY entity_id;"
        )
        rows = cur.fetchall()
        dump_csv = run_dir / "db_ontology_matching_snapshot.csv"
        with dump_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "entity_id",
                    "entity_uri",
                    "source_or_target",
                    "entity_type",
                    "syntactic_matching",
                    "lexical_matching",
                    "semantic_matching",
                ]
            )
            writer.writerows(rows)

    for tbl in ("syntactic_matching", "lexical_matching", "semantic_matching"):
        if tbl in tables:
            cur.execute(f'SELECT entity_id, content FROM "{tbl}" ORDER BY entity_id;')
            chunk_rows = cur.fetchall()
            chunk_csv = run_dir / f"db_{tbl}_chunks.csv"
            with chunk_csv.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["entity_id", "content"])
                writer.writerows(chunk_rows)

    conn.close()
    return {"tables": tables, "row_counts": counts, "embedding_dimensions": dims}


def _compute_alignment_metrics(true_csv: Path, pred_csv: Path) -> dict[str, Any]:
    if not true_csv.is_file() or not pred_csv.is_file():
        return {"exists": False}

    def _read_pairs(path: Path) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                e1 = (row.get("Entity1") or "").strip()
                e2 = (row.get("Entity2") or "").strip()
                if e1 and e2:
                    pairs.add((e1, e2))
        return pairs

    gold = _read_pairs(true_csv)
    pred = _read_pairs(pred_csv)
    tp_pairs = sorted(gold & pred)
    fp_pairs = sorted(pred - gold)
    fn_pairs = sorted(gold - pred)

    tp = len(tp_pairs)
    fp = len(fp_pairs)
    fn = len(fn_pairs)
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "exists": True,
        "gold_count": len(gold),
        "predicted_count": len(pred),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "precision_pct": round(precision * 100.0, 2),
        "recall_pct": round(recall * 100.0, 2),
        "f1_pct": round(f1 * 100.0, 2),
        "tp_pairs": tp_pairs,
        "fp_pairs": fp_pairs,
        "fn_pairs": fn_pairs,
    }


def _summarize_telemetry(telemetry_path: Path) -> dict[str, Any]:
    if not telemetry_path.is_file():
        return {"total_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "by_stage": {}}
    by_stage: dict[str, dict[str, Any]] = {}
    total_calls = 0
    total_prompt = 0
    total_completion = 0
    with telemetry_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            stage = rec.get("stage", "unknown")
            st = by_stage.setdefault(
                stage,
                {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "elapsed_ms": 0.0},
            )
            st["calls"] += 1
            st["prompt_tokens"] += int(rec.get("prompt_tokens", 0))
            st["completion_tokens"] += int(rec.get("completion_tokens", 0))
            st["elapsed_ms"] = round(st["elapsed_ms"] + float(rec.get("elapsed_ms", 0.0)), 2)
            total_calls += 1
            total_prompt += int(rec.get("prompt_tokens", 0))
            total_completion += int(rec.get("completion_tokens", 0))
    return {
        "total_calls": total_calls,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "by_stage": by_stage,
    }


def _sample_hardware() -> dict[str, Any]:
    hw: dict[str, Any] = {}
    try:
        smi = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader",
            ],
            text=True,
            timeout=5,
        ).strip()
        hw["nvidia_smi"] = smi
    except Exception as exc:
        hw["nvidia_smi_error"] = str(exc)
    return hw


def execute_upstream_run(
    experiment_id: str | None = None,
    alignment: str = "conference/cmt-confof/component/",
    context: str = "conference",
    o1_is_code: bool = False,
    o2_is_code: bool = False,
    llm_model: str = "llama3:8b",
    embedding_model: str = "llama3:8b",
    vector_length: int = 4096,
    temperature: float = 0.0,
    seed: int = 42,
    llm_top_k: int = 1,
    top_p: float = 1.0,
    repeat_penalty: float = 1.0,
    num_ctx: int | None = None,
    similarity_threshold: float = 0.90,
    top_k: int = 3,
    num_matches: int = 50,
    db_host: str = "127.0.0.1",
    db_port: int = 5432,
    db_user: str = "postgres",
    dbname: str = DEFAULT_UPSTREAM_DB,
    ollama_chat_base_url: str = "http://127.0.0.1:11434",
    use_llama_embed_bridge: bool = True,
    smoke_limit: int = 0,
    stages: tuple[str, ...] = DEFAULT_STAGE_SCRIPTS,
    venv_python: Path | None = None,
) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    exp_id = experiment_id or f"upstream_lite_{ts}"
    if not alignment.endswith("/"):
        alignment = alignment + "/"

    run_dir = (LOCAL_ROOT / "output" / "replication_runs" / exp_id).resolve()
    if (run_dir / "run_summary.json").exists():
        raise FileExistsError(
            f"Run directory {run_dir} already contains run_summary.json; refusing to overwrite."
        )
    run_dir.mkdir(parents=True, exist_ok=True)

    python_exe = (
        venv_python or (LOCAL_ROOT / ".venv_upstream" / "Scripts" / "python.exe")
    ).resolve()
    if not python_exe.is_file():
        raise FileNotFoundError(f"Isolated upstream Python interpreter missing: {python_exe}")

    # 1. Verify original_repo baseline manifest before running
    manifests_dir = LOCAL_ROOT / "output" / "replication_runs" / "manifests"
    orig_baseline_path = manifests_dir / "original_repo_baseline_sha256.json"
    if orig_baseline_path.is_file():
        orig_baseline = json.loads(orig_baseline_path.read_text(encoding="utf-8"))
    else:
        orig_baseline = build_directory_manifest(ORIGINAL_REPO)
    pre_check = compare_manifests(orig_baseline, build_directory_manifest(ORIGINAL_REPO))
    if not pre_check["identical"]:
        raise RuntimeError(
            f"Pre-flight integrity check failed on original_repo/: {json.dumps(pre_check, indent=2)}"
        )

    # 2. Verify PostgreSQL isolation and snapshot protected agent_om_local DB
    pg_pre = _verify_postgres_isolation(db_host, db_port, db_user, dbname)

    # 3. Prepare isolated folders and CSV headers inside run_dir
    bootstrap_dir = run_dir / "_bootstrap"
    pycache_dir = run_dir / "_pycache"
    align_folder = run_dir / "alignment" / alignment
    logs_dir = run_dir / "stage_logs"
    for d in (bootstrap_dir, pycache_dir, align_folder, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    result_csv = run_dir / "result.csv"
    cost_csv = run_dir / "cost.csv"
    telemetry_path = run_dir / "llm_telemetry.jsonl"
    if not result_csv.exists():
        with result_csv.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["LLM", "Alignment", "Precision", "Recall", "F1"])
    if not cost_csv.exists():
        with cost_csv.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["LLM", "Alignment", "Tokens", "Cost"])

    protected_roots = [str(ORIGINAL_REPO.resolve())]
    for existing in sorted((LOCAL_ROOT / "output").glob("step*")):
        protected_roots.append(str(existing.resolve()))
    for existing_doc in sorted((LOCAL_ROOT / "docs").glob("step*")):
        protected_roots.append(str(existing_doc.resolve()))

    stage_results: list[dict[str, Any]] = []
    times_ms: list[str] = []
    bridge_cm = (
        LlamaEmbeddingBridge(
            model_name=embedding_model,
            expected_dim=vector_length,
            ollama_base_url=ollama_chat_base_url,
        )
        if use_llama_embed_bridge
        else None
    )

    total_t0 = time.perf_counter()
    overall_error: str | None = None

    try:
        embed_base_url = bridge_cm.start() if bridge_cm is not None else ollama_chat_base_url

        # Verify embedding vector length BEFORE running database table creation
        if bridge_cm is not None:
            probe_vecs = bridge_cm.embed_texts(["dimension verification probe"])
            actual_dim = len(probe_vecs[0])
            bridge_cm.stop_backend()  # Immediately release VRAM before Stage 1 chat calls
        else:
            req = urllib.request.Request(
                f"{embed_base_url.rstrip('/')}/api/embed",
                data=json.dumps({"model": embedding_model, "input": ["dimension verification probe"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                actual_dim = len(json.loads(resp.read().decode("utf-8"))["embeddings"][0])

        if actual_dim != vector_length:
            raise ValueError(
                f"Verified embedding dimension {actual_dim} for {embedding_model!r} != configured vector_length {vector_length}"
            )

        overrides = {
            "original_repo": str(ORIGINAL_REPO.resolve()),
            "protected_roots": protected_roots,
            "telemetry_path": str(telemetry_path),
            "llm_model": llm_model,
            "embedding_model": embedding_model,
            "ollama_chat_base_url": ollama_chat_base_url,
            "ollama_embed_base_url": embed_base_url,
            "temperature": temperature,
            "seed": seed,
            "llm_top_k": llm_top_k,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "num_ctx": num_ctx,
            "smoke_limit": smoke_limit,
            "scalars": {
                "vector_length": vector_length,
                "similarity_threshold": similarity_threshold,
                "top_k": top_k,
                "num_matches": num_matches,
                "context": context,
                "alignment": alignment,
                "o1_is_code": o1_is_code,
                "o2_is_code": o2_is_code,
                "data_folder": (ORIGINAL_REPO / "data" / alignment).resolve().as_posix(),
                "align_folder": align_folder.resolve().as_posix() + "/",
                "result_path": result_csv.resolve().as_posix(),
                "cost_path": cost_csv.resolve().as_posix(),
                "connection_string": f"postgresql://{db_user}@{db_host}:{db_port}/{dbname}",
            },
        }
        (bootstrap_dir / "overrides.json").write_text(
            json.dumps(overrides, indent=2), encoding="utf-8"
        )
        (bootstrap_dir / "sitecustomize.py").write_text(
            SITECUSTOMIZE_TEMPLATE, encoding="utf-8"
        )

        base_env = os.environ.copy()
        base_env["PYTHONPATH"] = f"{bootstrap_dir}{os.pathsep}{ORIGINAL_REPO}"
        base_env["PYTHONDONTWRITEBYTECODE"] = "1"
        base_env["PYTHONPYCACHEPREFIX"] = str(pycache_dir)
        base_env["PYTHONIOENCODING"] = "utf-8"
        base_env["OPENAI_API_KEY"] = "LOCAL_DISABLED"
        base_env["ANTHROPIC_API_KEY"] = "LOCAL_DISABLED"
        base_env["OPENAI_BASE_URL"] = "http://127.0.0.1:9"
        base_env["OLLAMA_HOST"] = ollama_chat_base_url
        base_env["OLLAMA_NO_CLOUD"] = "true"
        base_env["PATH"] = f"{python_exe.parent}{os.pathsep}{base_env.get('PATH', '')}"

        for script_name in stages:
            script_path = (ORIGINAL_REPO / script_name).resolve()
            if not script_path.is_file():
                raise FileNotFoundError(f"Upstream stage script not found: {script_path}")

            stage_env = base_env.copy()
            stage_env["AGENT_OM_UPSTREAM_STAGE"] = script_name
            stdout_log = logs_dir / f"{Path(script_name).stem}.stdout.log"
            stderr_log = logs_dir / f"{Path(script_name).stem}.stderr.log"

            hw_before = _sample_hardware()
            st_t0 = time.perf_counter()
            with stdout_log.open("w", encoding="utf-8") as out_fh, stderr_log.open(
                "w", encoding="utf-8"
            ) as err_fh:
                proc = subprocess.run(
                    [str(python_exe), str(script_path)],
                    cwd=str(run_dir),
                    env=stage_env,
                    stdout=out_fh,
                    stderr=err_fh,
                    text=True,
                    check=False,
                )
            st_ms = (time.perf_counter() - st_t0) * 1000.0
            hw_after = _sample_hardware()

            # Release embedding backend VRAM immediately after Stage 2 completes
            if script_name == "om_csv_to_database.py" and bridge_cm is not None:
                bridge_cm.stop_backend()

            stage_rec = {
                "script": script_name,
                "returncode": proc.returncode,
                "elapsed_ms": round(st_ms, 2),
                "elapsed_sec": round(st_ms / 1000.0, 3),
                "stdout_log": str(stdout_log.relative_to(run_dir).as_posix()),
                "stderr_log": str(stderr_log.relative_to(run_dir).as_posix()),
                "hw_before": hw_before,
                "hw_after": hw_after,
            }
            if proc.returncode != 0:
                err_tail = stderr_log.read_text(encoding="utf-8", errors="replace")[-3000:]
                stage_rec["stderr_tail"] = err_tail
                stage_results.append(stage_rec)
                times_ms.append("ERROR")
                overall_error = f"Stage {script_name} exited with code {proc.returncode}: {err_tail}"
                break

            stage_results.append(stage_rec)
            times_ms.append(f"{st_ms:.2f}")

    finally:
        if bridge_cm is not None:
            bridge_cm.close()

    total_ms = (time.perf_counter() - total_t0) * 1000.0

    # Write upstream-compatible time.csv in run_dir
    time_csv = run_dir / "time.csv"
    padded_times = list(times_ms)
    while len(padded_times) < 3:
        padded_times.append("")
    with time_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["LLM", "Alignment", "Retrieving", "Embedding", "Matching", "Total"])
        writer.writerow([llm_model, alignment, *padded_times[:3], f"{total_ms:.2f}"])

    # Archive database snapshot if DB tables exist
    db_snapshot = _archive_upstream_db_tables(db_host, db_port, db_user, dbname, run_dir)

    # Compute exact metrics across all 6 prediction CSVs
    true_csv = align_folder / "true.csv"
    eval_variants = {
        "source_no_validation": align_folder / "predict_source_no_validation.csv",
        "source": align_folder / "predict_source.csv",
        "target_no_validation": align_folder / "predict_target_no_validation.csv",
        "target": align_folder / "predict_target.csv",
        "no_validation": align_folder / "predict_no_validation.csv",
        "llm_with_agent": align_folder / "predict.csv",
    }
    metrics = {k: _compute_alignment_metrics(true_csv, p) for k, p in eval_variants.items()}

    # Post-run integrity checks on original_repo and protected agent_om_local DB
    post_orig_check = compare_manifests(orig_baseline, build_directory_manifest(ORIGINAL_REPO))
    pg_post = _verify_postgres_isolation(db_host, db_port, db_user, dbname)
    protected_db_unchanged = pg_pre["protected_db_counts"] == pg_post["protected_db_counts"]

    summary = {
        "experiment_id": exp_id,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED" if overall_error is None else "FAILED",
        "error": overall_error,
        "run_dir": str(run_dir),
        "configuration": {
            "implementation": "original_repo (Agent-OM upstream)",
            "alignment": alignment,
            "context": context,
            "o1_is_code": o1_is_code,
            "o2_is_code": o2_is_code,
            "llm_model": llm_model,
            "embedding_model": embedding_model,
            "vector_length": vector_length,
            "verified_embedding_dim": actual_dim if "actual_dim" in locals() else None,
            "temperature": temperature,
            "seed": seed,
            "llm_top_k": llm_top_k,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
            "num_ctx": num_ctx,
            "similarity_threshold": similarity_threshold,
            "top_k": top_k,
            "num_matches": num_matches,
            "dbname": dbname,
            "smoke_limit": smoke_limit,
            "use_llama_embed_bridge": use_llama_embed_bridge,
        },
        "total_elapsed_ms": round(total_ms, 2),
        "total_elapsed_sec": round(total_ms / 1000.0, 3),
        "stages": stage_results,
        "llm_telemetry": _summarize_telemetry(telemetry_path),
        "embedding_bridge_stats": {
            "requests": bridge_cm.total_requests if bridge_cm else 0,
            "texts_embedded": bridge_cm.total_texts_embedded if bridge_cm else 0,
        },
        "database_snapshot": db_snapshot,
        "metrics": metrics,
        "integrity_verification": {
            "original_repo_unchanged": post_orig_check["identical"],
            "original_repo_aggregate_sha256": post_orig_check["current_aggregate_sha256"],
            "protected_agent_om_local_db_unchanged": protected_db_unchanged,
            "protected_agent_om_local_counts": pg_post["protected_db_counts"],
        },
    }

    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe isolated launcher for upstream Agent-OM.")
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument("--alignment", default="conference/cmt-confof/component/")
    parser.add_argument("--context", default="conference")
    parser.add_argument("--o1-is-code", action="store_true", default=False)
    parser.add_argument("--o2-is-code", action="store_true", default=False)
    parser.add_argument("--llm-model", default="llama3:8b")
    parser.add_argument("--embedding-model", default="llama3:8b")
    parser.add_argument("--vector-length", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--llm-top-k", type=int, default=1)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--repeat-penalty", type=float, default=1.0)
    parser.add_argument("--num-ctx", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=0.90)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--num-matches", type=int, default=50)
    parser.add_argument("--dbname", default=DEFAULT_UPSTREAM_DB)
    parser.add_argument("--smoke-limit", type=int, default=0)
    parser.add_argument(
        "--stages",
        default=",".join(DEFAULT_STAGE_SCRIPTS),
        help="Comma-separated upstream stage scripts to execute.",
    )
    parser.add_argument(
        "--no-embed-bridge",
        action="store_true",
        help="Connect OllamaEmbeddings directly to 127.0.0.1:11434 instead of LlamaEmbeddingBridge.",
    )

    args = parser.parse_args(argv)
    stages = tuple(s.strip() for s in args.stages.split(",") if s.strip())
    summary = execute_upstream_run(
        experiment_id=args.experiment_id,
        alignment=args.alignment,
        context=args.context,
        o1_is_code=args.o1_is_code,
        o2_is_code=args.o2_is_code,
        llm_model=args.llm_model,
        embedding_model=args.embedding_model,
        vector_length=args.vector_length,
        temperature=args.temperature,
        seed=args.seed,
        llm_top_k=args.llm_top_k,
        top_p=args.top_p,
        repeat_penalty=args.repeat_penalty,
        num_ctx=args.num_ctx,
        similarity_threshold=args.similarity_threshold,
        top_k=args.top_k,
        num_matches=args.num_matches,
        dbname=args.dbname,
        use_llama_embed_bridge=not args.no_embed_bridge,
        smoke_limit=args.smoke_limit,
        stages=stages,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())

