"""Bidirectional Ollama <-> MLX-LM safetensors converter for Qwen3.5 4B (nvfp4)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import mlx.core as mx
from safetensors import safe_open
from safetensors.numpy import save_file as np_save_file

from source.utils.hashing import sha256_file
from source.utils.logging_utils import get_logger

logger = get_logger("mlx_converter")

DEFAULT_OLLAMA_HOME = Path.home() / ".ollama" / "models"


class OllamaMLXConverter:
    """Reconstructs a local MLX-LM checkpoint from Ollama nvfp4 blobs and exports fused LoRA models back to Ollama."""

    def __init__(self, ollama_models_dir: Optional[Path] = None):
        self.ollama_models_dir = ollama_models_dir or Path(os.environ.get("OLLAMA_MODELS", str(DEFAULT_OLLAMA_HOME)))

    def get_manifest_path(self, model_identifier: str) -> Path:
        """Resolve ~/.ollama/models/manifests/registry.ollama.ai/library/<repo>/<tag>."""
        if ":" in model_identifier:
            repo, tag = model_identifier.split(":", 1)
        else:
            repo, tag = model_identifier, "latest"
        if "/" not in repo:
            repo = f"library/{repo}"
        return self.ollama_models_dir / "manifests" / "registry.ollama.ai" / repo / tag

    def _blob_path(self, digest: str) -> Path:
        return self.ollama_models_dir / "blobs" / digest.replace(":", "-")

    def export_ollama_to_mlx(
        self,
        model_identifier: str,
        target_mlx_dir: Path,
    ) -> Dict[str, Any]:
        """Reconstruct a local MLX-LM loadable directory from Ollama's local safetensors blobs."""
        manifest_path = self.get_manifest_path(model_identifier)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Ollama manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target_mlx_dir.mkdir(parents=True, exist_ok=True)

        copied_jsons: List[str] = []
        lm_layers: List[dict] = []
        for layer in manifest.get("layers", []):
            mtype = layer.get("mediaType", "")
            name = layer.get("name", "")
            blob = self._blob_path(layer["digest"])
            if not blob.exists():
                raise FileNotFoundError(f"Missing Ollama blob {blob} for {name}")
            if mtype == "application/vnd.ollama.image.json":
                dest = target_mlx_dir / name
                shutil.copy2(blob, dest)
                copied_jsons.append(name)
            elif mtype == "application/vnd.ollama.image.tensor" and name.startswith("language_model."):
                lm_layers.append(layer)

        # Patch config.json with explicit MLX nvfp4 quantization descriptor
        cfg_path = target_mlx_dir / "config.json"
        if not cfg_path.exists():
            raise FileNotFoundError(f"config.json missing from Ollama manifest for {model_identifier}")
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["quantization"] = {"group_size": 16, "bits": 4, "mode": "nvfp4"}
        cfg["quantization_config"] = {"group_size": 16, "bits": 4, "mode": "nvfp4"}
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        # Assemble single model.safetensors translating *.weight.scale -> *.scales for mlx_lm
        mlx_tensors: Dict[str, mx.array] = {}
        orig_layer_digest_map: Dict[str, str] = {}
        for layer in lm_layers:
            blob = self._blob_path(layer["digest"])
            orig_layer_digest_map[layer["name"]] = layer["digest"]
            loaded = mx.load(str(blob), format="safetensors")
            for k, arr in loaded.items():
                if k.endswith(".weight.scale"):
                    mlx_key = k[: -len(".weight.scale")] + ".scales"
                else:
                    mlx_key = k
                mlx_tensors[mlx_key] = arr

        weights_out = target_mlx_dir / "model.safetensors"
        mx.save_safetensors(str(weights_out), mlx_tensors)
        logger.info(
            f"Exported {len(mlx_tensors)} MLX tensors ({len(lm_layers)} Ollama layers) to {target_mlx_dir}"
        )
        return {
            "source_model": model_identifier,
            "target_mlx_dir": str(target_mlx_dir),
            "json_files": copied_jsons,
            "ollama_lm_layers": len(lm_layers),
            "mlx_tensors": len(mlx_tensors),
            "weights_file": str(weights_out),
            "weights_size_bytes": weights_out.stat().st_size,
        }

    def export_fused_mlx_to_ollama(
        self,
        base_ollama_model: str,
        target_ollama_model: str,
        fused_mlx_dir: Path,
        staging_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Convert fused MLX weights back to Ollama nvfp4 blobs + manifest, reusing unchanged base blobs."""
        base_manifest_path = self.get_manifest_path(base_ollama_model)
        base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))

        fused_weights_path = fused_mlx_dir / "model.safetensors"
        if not fused_weights_path.exists():
            # Support sharded safetensors if present
            shards = sorted(fused_mlx_dir.glob("model*.safetensors"))
            if not shards:
                raise FileNotFoundError(f"No fused safetensors found in {fused_mlx_dir}")
        else:
            shards = [fused_weights_path]

        fused_tensors: Dict[str, Tuple[Path, str]] = {}
        loaded_arrays: Dict[str, Any] = {}
        for sf in shards:
            # Load raw numpy/safetensors or mx arrays so BF16/U32/U8 stay exact
            arrs = mx.load(str(sf))
            for k, v in arrs.items():
                loaded_arrays[k] = v

        # Compare each language_model layer against the original Ollama blob; only write new blobs for changed layers
        if staging_dir:
            staging_dir.mkdir(parents=True, exist_ok=True)
        new_blobs_written = 0
        reused_blobs = 0
        updated_layers: List[dict] = []

        for layer in base_manifest.get("layers", []):
            mtype = layer.get("mediaType", "")
            layer_name = layer.get("name", "")

            if mtype != "application/vnd.ollama.image.tensor" or not layer_name.startswith("language_model."):
                updated_layers.append(dict(layer))
                continue

            # Determine expected MLX key(s) for this Ollama layer
            base_blob_path = self._blob_path(layer["digest"])
            orig_blob_tensors = mx.load(str(base_blob_path), format="safetensors")
            orig_keys = list(orig_blob_tensors.keys())

            # Map Ollama keys -> MLX keys
            mapped_new: Dict[str, mx.array] = {}
            changed = False
            with safe_open(str(base_blob_path), framework="numpy") as f:
                orig_meta = f.metadata() or {}

            for ok in orig_keys:
                mk = ok[: -len(".weight.scale")] + ".scales" if ok.endswith(".weight.scale") else ok
                if mk not in loaded_arrays:
                    raise KeyError(f"Fused MLX weights missing expected tensor '{mk}' for Ollama key '{ok}'")
                new_arr = loaded_arrays[mk]
                orig_arr = orig_blob_tensors[ok]
                mapped_new[ok] = new_arr
                if new_arr.shape != orig_arr.shape or not bool(mx.array_equal(new_arr, orig_arr).item()):
                    changed = True

            if not changed:
                updated_layers.append(dict(layer))
                reused_blobs += 1
                continue

            # Serialize modified single-layer safetensors matching Ollama's exact metadata format
            tmp_file = (staging_dir or fused_mlx_dir) / f"_tmp_{layer_name.replace('.', '_')}.safetensors"
            mx.save_safetensors(str(tmp_file), mapped_new, metadata=orig_meta)
            digest_hex = sha256_file(tmp_file)
            digest = f"sha256:{digest_hex}"
            dest_blob = self._blob_path(digest)
            dest_blob.parent.mkdir(parents=True, exist_ok=True)
            if not dest_blob.exists():
                shutil.move(str(tmp_file), str(dest_blob))
            else:
                tmp_file.unlink(missing_ok=True)

            new_size = dest_blob.stat().st_size
            new_layer = dict(layer)
            new_layer["digest"] = digest
            new_layer["size"] = new_size
            updated_layers.append(new_layer)
            new_blobs_written += 1

        # Update manifest config digest and write target manifest
        new_manifest = dict(base_manifest)
        new_manifest["layers"] = updated_layers
        target_manifest_path = self.get_manifest_path(target_ollama_model)
        target_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        target_manifest_path.write_text(json.dumps(new_manifest, separators=(",", ":")), encoding="utf-8")

        # Also copy manifest to staging_dir for reproducibility documentation
        if staging_dir:
            (staging_dir / "ollama_manifest.json").write_text(json.dumps(new_manifest, indent=2), encoding="utf-8")

        # Verify Ollama recognizes the registered model
        show_proc = subprocess.run(
            ["ollama", "show", target_ollama_model],
            capture_output=True,
            text=True,
            check=False,
        )
        if show_proc.returncode != 0:
            raise RuntimeError(f"Ollama failed to inspect exported model '{target_ollama_model}': {show_proc.stderr}")

        logger.info(
            f"Registered Ollama model '{target_ollama_model}' "
            f"(modified blobs={new_blobs_written}, reused blobs={reused_blobs})"
        )
        return {
            "target_ollama_model": target_ollama_model,
            "manifest_path": str(target_manifest_path),
            "modified_blobs_written": new_blobs_written,
            "reused_blobs": reused_blobs,
            "ollama_show_verified": True,
        }
