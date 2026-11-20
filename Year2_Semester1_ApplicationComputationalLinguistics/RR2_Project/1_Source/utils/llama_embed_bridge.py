"""Local loopback Ollama-compatible embedding bridge for causal GGUF models.

In Ollama >= 0.40.x, Ollama delegates model execution to its bundled
`llama-server` binary and only passes `--embeddings` when a model manifest
declares the `"embedding"` capability. Causal models such as `llama3:8b`
declare only `["completion"]`, causing `POST /api/embed` and
`POST /api/embeddings` on Ollama 0.40.13 to fail with:
`{"error": "This server does not support embeddings. Start it with --embeddings"}`.

`LlamaEmbeddingBridge` resolves the exact GGUF blob for `llama3:8b` from the
local `OLLAMA_MODELS` manifest directory, unloads any active Ollama chat runner
via `keep_alive=0` so GPU VRAM is not double-allocated on 8 GB GPUs, launches
Ollama's own bundled `llama-server.exe --embeddings --pooling mean` strictly on
`127.0.0.1`, and translates Ollama `/api/embed` and `/api/embeddings` requests
locally on loopback with zero external network calls and zero model substitution.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_APP_DIR = Path(r"E:\_1_Applications\Ollama")
DEFAULT_OLLAMA_MODELS_DIR = Path(r"E:\_1_Applications\Ollama\Models")


def _find_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def resolve_ollama_gguf_blob(
    model_name: str = "llama3:8b",
    models_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Resolve the on-disk GGUF weight blob and manifest for a local Ollama model."""
    env_dir = os.environ.get("OLLAMA_MODELS")
    root = Path(models_dir or env_dir or DEFAULT_OLLAMA_MODELS_DIR)
    if ":" in model_name:
        repo, tag = model_name.split(":", 1)
    else:
        repo, tag = model_name, "latest"

    manifest_path = root / "manifests" / "registry.ollama.ai" / "library" / repo / tag
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Ollama manifest for '{model_name}' not found at {manifest_path}. "
            f"Verify OLLAMA_MODELS points to {root}."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_layer = next(
        (
            layer
            for layer in manifest.get("layers", [])
            if layer.get("mediaType") == "application/vnd.ollama.image.model"
        ),
        None,
    )
    if not model_layer or "digest" not in model_layer:
        raise ValueError(f"No model weight layer found in manifest {manifest_path}")

    blob_name = str(model_layer["digest"]).replace(":", "-")
    blob_path = root / "blobs" / blob_name
    if not blob_path.is_file():
        raise FileNotFoundError(f"GGUF blob for '{model_name}' missing at {blob_path}")

    return blob_path, manifest


def resolve_llama_server_binary(ollama_app_dir: Path | None = None) -> Path:
    """Locate Ollama's bundled `llama-server.exe` binary."""
    candidates: list[Path] = []
    if ollama_app_dir:
        candidates.append(Path(ollama_app_dir) / "lib" / "ollama" / "llama-server.exe")
    candidates.append(DEFAULT_OLLAMA_APP_DIR / "lib" / "ollama" / "llama-server.exe")
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        candidates.append(Path(local_app) / "Programs" / "Ollama" / "lib" / "ollama" / "llama-server.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Bundled llama-server.exe not found in checked locations: {[str(c) for c in candidates]}"
    )


class LlamaEmbeddingBridge:
    """Loopback-only HTTP adapter serving Ollama `/api/embed` via `llama-server --embeddings`."""

    def __init__(
        self,
        model_name: str = "llama3:8b",
        expected_dim: int = 4096,
        pooling: str = "mean",
        ctx_size: int = 2048,
        ollama_base_url: str = "http://127.0.0.1:11434",
        models_dir: Path | None = None,
        ollama_app_dir: Path | None = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("LlamaEmbeddingBridge must bind strictly to 127.0.0.1.")
        self.model_name = model_name
        self.expected_dim = expected_dim
        self.pooling = pooling
        self.ctx_size = ctx_size
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.gguf_blob, self.manifest = resolve_ollama_gguf_blob(model_name, models_dir)
        self.llama_server_bin = resolve_llama_server_binary(ollama_app_dir)
        self.host = host
        self.port = port or _find_free_loopback_port()
        self._backend_port: int = 0
        self._backend_proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._http_server: ThreadingHTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self.total_requests: int = 0
        self.total_texts_embedded: int = 0

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _unload_ollama_chat_runner(self) -> None:
        """Ask Ollama on 127.0.0.1:11434 to release VRAM before starting embedding runner."""
        payload = json.dumps({"model": self.model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            logger.debug("Optional Ollama runner unload skipped: %s", exc)

    def _ensure_backend_started(self) -> None:
        with self._lock:
            if self._backend_proc is not None and self._backend_proc.poll() is None:
                return
            self._unload_ollama_chat_runner()
            self._backend_port = _find_free_loopback_port()
            lib_dir = self.llama_server_bin.parent
            env = os.environ.copy()
            for cuda_subdir in ("cuda_v13", "cuda_v12"):
                cuda_dll = lib_dir / cuda_subdir / "ggml-cuda.dll"
                if cuda_dll.is_file():
                    env["GGML_BACKEND_PATH"] = str(cuda_dll)
                    env["PATH"] = f"{cuda_dll.parent};{lib_dir};{env.get('PATH', '')}"
                    break
            cmd = [
                str(self.llama_server_bin),
                "-m",
                str(self.gguf_blob),
                "--embeddings",
                "--pooling",
                self.pooling,
                "--host",
                "127.0.0.1",
                "--port",
                str(self._backend_port),
                "--no-webui",
                "--offline",
                "--load-mode",
                "none",
                "--flash-attn",
                "auto",
                "-b",
                "512",
                "-ub",
                "512",
                "-ngl",
                "99",
                "-c",
                str(self.ctx_size),
            ]
            self._backend_proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            health_url = f"http://127.0.0.1:{self._backend_port}/health"
            deadline = time.monotonic() + 45.0
            while time.monotonic() < deadline:
                if self._backend_proc.poll() is not None:
                    raise RuntimeError(
                        f"llama-server exited prematurely with code {self._backend_proc.returncode}"
                    )
                try:
                    with urllib.request.urlopen(health_url, timeout=1.5) as resp:
                        if resp.status == 200:
                            return
                except Exception:
                    time.sleep(0.25)
            self.stop_backend()
            raise TimeoutError("Timed out waiting for local llama-server embedding backend on 127.0.0.1.")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_backend_started()
        payload = json.dumps({"input": texts}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self._backend_port}/v1/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        items = sorted(body.get("data", []), key=lambda d: int(d.get("index", 0)))
        vectors = [list(item["embedding"]) for item in items]
        for idx, vec in enumerate(vectors):
            if self.expected_dim and len(vec) != self.expected_dim:
                raise ValueError(
                    f"Vector dimension mismatch at item {idx}: expected {self.expected_dim}, got {len(vec)}"
                )
        self.total_requests += 1
        self.total_texts_embedded += len(vectors)
        return vectors

    def stop_backend(self) -> None:
        with self._lock:
            if self._backend_proc is not None:
                if self._backend_proc.poll() is None:
                    self._backend_proc.terminate()
                    try:
                        self._backend_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._backend_proc.kill()
                self._backend_proc = None

    def start(self) -> str:
        bridge = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

            def _send_json(self, status: int, data: dict[str, Any]) -> None:
                raw = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.path in ("/api/version", "/health"):
                    self._send_json(
                        200,
                        {
                            "status": "ok",
                            "model": bridge.model_name,
                            "expected_dim": bridge.expected_dim,
                            "requests": bridge.total_requests,
                            "texts_embedded": bridge.total_texts_embedded,
                        },
                    )
                elif self.path == "/api/tags":
                    self._send_json(200, {"models": [{"name": bridge.model_name}]})
                else:
                    self._send_json(404, {"error": f"Unknown path {self.path}"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    self._send_json(400, {"error": f"Invalid JSON: {exc}"})
                    return

                try:
                    if self.path == "/api/embed":
                        inp = body.get("input", [])
                        texts = [inp] if isinstance(inp, str) else list(inp)
                        vecs = bridge.embed_texts(texts)
                        self._send_json(
                            200,
                            {"model": bridge.model_name, "embeddings": vecs},
                        )
                    elif self.path == "/api/embeddings":
                        prompt = str(body.get("prompt", ""))
                        vecs = bridge.embed_texts([prompt])
                        self._send_json(200, {"embedding": vecs[0] if vecs else []})
                    elif self.path == "/api/release_vram":
                        bridge.stop_backend()
                        self._send_json(200, {"released": True})
                    else:
                        self._send_json(404, {"error": f"Unknown endpoint {self.path}"})
                except Exception as exc:
                    logger.exception("Embedding bridge error on %s", self.path)
                    self._send_json(500, {"error": str(exc)})

        self._http_server = ThreadingHTTPServer((self.host, self.port), _Handler)
        self.port = int(self._http_server.server_address[1])
        self._http_thread = threading.Thread(
            target=self._http_server.serve_forever,
            name="LlamaEmbeddingBridgeHTTP",
            daemon=True,
        )
        self._http_thread.start()
        return self.base_url

    def close(self) -> None:
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
        if self._http_thread is not None:
            self._http_thread.join(timeout=3)
            self._http_thread = None
        self.stop_backend()

    def __enter__(self) -> "LlamaEmbeddingBridge":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


class LlamaBridgeEmbeddings:
    """LangChain Embeddings-compatible wrapper over `LlamaEmbeddingBridge`.

    Used by `agent_om_local` in `upstream_lite_parity` mode when Ollama >= 0.40.x
    disables `/api/embed` on causal models (`llama3:8b`). Automatically unloads
    the Ollama chat runner before embedding and exposes `release_vram()` so the
    embedding subprocess can be stopped before downstream LLM validation starts.
    """

    def __init__(
        self,
        model_name: str = "llama3:8b",
        expected_dim: int = 4096,
        pooling: str = "mean",
        ctx_size: int = 2048,
        ollama_base_url: str = "http://127.0.0.1:11434",
        models_dir: Path | None = None,
        ollama_app_dir: Path | None = None,
    ) -> None:
        self.model = model_name
        self.expected_dim = expected_dim
        self._bridge = LlamaEmbeddingBridge(
            model_name=model_name,
            expected_dim=expected_dim,
            pooling=pooling,
            ctx_size=ctx_size,
            ollama_base_url=ollama_base_url,
            models_dir=models_dir,
            ollama_app_dir=ollama_app_dir,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents into `expected_dim`-dimensional float vectors."""
        return self._bridge.embed_texts(list(texts))

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        vecs = self._bridge.embed_texts([text])
        return vecs[0] if vecs else []

    def release_vram(self) -> None:
        """Stop the underlying `llama-server` process to free GPU VRAM."""
        self._bridge.stop_backend()

    def close(self) -> None:
        """Shut down bridge resources."""
        self._bridge.close()

    def __enter__(self) -> "LlamaBridgeEmbeddings":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

