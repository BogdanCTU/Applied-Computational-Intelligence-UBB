"""Auto-loaded isolation bootstrap for upstream Agent-OM subprocesses."""
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
                fh.write(json.dumps(record) + "\n")

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
