"""Local Ollama health, installed model inventory, and LlamaEmbeddingBridge check service."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ...config import validate_loopback_url
from ...utils.llama_embed_bridge import resolve_llama_server_binary, resolve_ollama_gguf_blob


class OllamaService:
    """Queries loopback Ollama (`127.0.0.1:11434`) and verifies local model availability."""

    REQUIRED_MODELS = ("llama3:8b", "qwen3.5:9b", "nomic-embed-text")

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = validate_loopback_url(base_url)

    def _get_json(self, path: str, timeout: float = 3.0) -> Dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def check_health(self) -> Dict[str, Any]:
        """Inspect Ollama daemon version, available models, active VRAM models, and bridge readiness."""
        result: Dict[str, Any] = {
            "reachable": False,
            "base_url": self.base_url,
            "version": None,
            "models": [],
            "model_details": [],
            "active_runners": [],
            "llama3_bridge_ready": False,
            "llama3_bridge_detail": "",
        }
        try:
            ver_data = self._get_json("/api/version")
            tags_data = self._get_json("/api/tags")
            ps_data = self._get_json("/api/ps")

            models_raw = tags_data.get("models", []) or []
            names = [str(m.get("name", "")) for m in models_raw]
            details: List[Dict[str, Any]] = []
            for m in models_raw:
                details.append(
                    {
                        "name": str(m.get("name", "")),
                        "size_gb": round(float(m.get("size", 0)) / (1024**3), 2),
                        "digest": str(m.get("digest", ""))[:16],
                        "family": str((m.get("details") or {}).get("family", "")),
                        "parameter_size": str((m.get("details") or {}).get("parameter_size", "")),
                        "quantization": str((m.get("details") or {}).get("quantization_level", "")),
                    }
                )

            active = [
                {
                    "name": str(r.get("name", "")),
                    "size_vram_mib": round(float(r.get("size_vram", 0)) / (1024**2), 1),
                }
                for r in (ps_data.get("models", []) or [])
            ]

            result["reachable"] = True
            result["version"] = str(ver_data.get("version", "unknown"))
            result["models"] = names
            result["model_details"] = details
            result["active_runners"] = active
        except Exception as exc:
            result["error"] = str(exc)

        # Check LlamaEmbeddingBridge prerequisites on disk
        try:
            blob_path, _ = resolve_ollama_gguf_blob("llama3:8b")
            server_bin = resolve_llama_server_binary()
            result["llama3_bridge_ready"] = True
            result["llama3_bridge_detail"] = (
                f"Ready ({server_bin.name} + {blob_path.name[:22]}... -> 4096-dim)"
            )
        except Exception as exc:
            result["llama3_bridge_ready"] = False
            result["llama3_bridge_detail"] = f"Unavailable: {exc}"

        return result

