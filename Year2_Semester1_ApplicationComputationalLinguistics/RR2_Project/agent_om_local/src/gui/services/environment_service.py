"""Environment diagnostics service for OS, Python/exe runtime, GPU, and workspace integrity."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from ..paths import ProjectPaths, resolve_project_paths


class EnvironmentService:
    """Inspects local runtime environment, hardware, and read-only upstream repository status."""

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or resolve_project_paths()

    def get_runtime_summary(self) -> Dict[str, Any]:
        """Lightweight runtime summary without querying network sockets."""
        return {
            "is_frozen": self.paths.is_frozen,
            "python_version": platform.python_version(),
            "executable": sys.executable,
            "os": f"{platform.system()} {platform.release()}",
            "project_root": str(self.paths.project_root),
            "original_repo_dir": str(self.paths.original_repo_dir),
        }

    def get_gpu_info(self) -> Dict[str, Any]:
        """Query NVIDIA GPU model and VRAM via `nvidia-smi` without raising if absent."""
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.free,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if proc.returncode == 0 and proc.stdout.strip():
                line = proc.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    return {
                        "detected": True,
                        "name": parts[0],
                        "vram_total_mib": int(float(parts[1])),
                        "vram_free_mib": int(float(parts[2])),
                        "driver_version": parts[3],
                    }
        except Exception:
            pass
        return {"detected": False, "name": "Not detected", "vram_total_mib": 0, "vram_free_mib": 0}

    def check_original_repo_status(self) -> Dict[str, Any]:
        """Check presence and baseline manifest status of read-only `original_repo/`."""
        orig = self.paths.original_repo_dir
        exists = orig.is_dir()
        manifest_path = (
            self.paths.replication_runs_dir / "manifests" / "original_repo_baseline_sha256.json"
        )
        baseline_hash = None
        baseline_files = None
        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                baseline_hash = data.get("aggregate_sha256")
                baseline_files = data.get("total_files")
            except Exception:
                pass
        return {
            "exists": exists,
            "path": str(orig),
            "read_only_policy": "STRICT READ-ONLY",
            "baseline_manifest_present": manifest_path.is_file(),
            "baseline_aggregate_sha256": baseline_hash,
            "baseline_file_count": baseline_files,
        }

    def run_full_diagnostics(
        self,
        db_service: Any | None = None,
        ollama_service: Any | None = None,
    ) -> Dict[str, Any]:
        """Collect comprehensive system, workspace, database, and Ollama health report."""
        gpu = self.get_gpu_info()
        orig = self.check_original_repo_status()
        db_status = db_service.check_server_health() if db_service else {}
        ollama_status = ollama_service.check_health() if ollama_service else {}

        checks: List[Dict[str, str]] = [
            {
                "component": "Runtime Mode",
                "status": "OK",
                "detail": (
                    f"Packaged Windows Executable ({sys.executable})"
                    if self.paths.is_frozen
                    else f"Python {platform.python_version()} ({sys.executable})"
                ),
            },
            {
                "component": "Operating System",
                "status": "OK",
                "detail": f"{platform.system()} {platform.release()} ({platform.version()})",
            },
            {
                "component": "GPU Accelerator",
                "status": "OK" if gpu["detected"] else "WARN",
                "detail": (
                    f"{gpu['name']} — {gpu['vram_total_mib']} MiB VRAM ({gpu['vram_free_mib']} MiB free, Driver {gpu.get('driver_version', '')})"
                    if gpu["detected"]
                    else "No NVIDIA GPU detected via nvidia-smi",
                )
                if isinstance(gpu["detected"], bool)
                else "",
            },
            {
                "component": "Upstream Repository (original_repo/)",
                "status": "OK" if orig["exists"] else "WARN",
                "detail": (
                    f"Present (Read-Only) — {orig['baseline_file_count'] or '?'} baseline files, SHA-256={str(orig['baseline_aggregate_sha256'] or '')[:16]}..."
                    if orig["exists"]
                    else f"Not found at {orig['path']}"
                ),
            },
            {
                "component": "Isolated Upstream Venv (.venv_upstream)",
                "status": "OK" if self.paths.venv_upstream_python.is_file() else "INFO",
                "detail": (
                    str(self.paths.venv_upstream_python)
                    if self.paths.venv_upstream_python.is_file()
                    else "Optional (.venv_upstream not found; local replication runs natively)"
                ),
            },
        ]
        # Normalize detail tuple if any
        for item in checks:
            if isinstance(item["detail"], tuple):
                item["detail"] = item["detail"][0]

        if db_status:
            checks.append(
                {
                    "component": "PostgreSQL + pgvector (127.0.0.1:5432)",
                    "status": "OK" if db_status.get("reachable") else "ERROR",
                    "detail": (
                        f"{db_status.get('server_version', '')} | pgvector {db_status.get('pgvector_version', 'installed')} | DBs: {', '.join(db_status.get('databases', []))}"
                        if db_status.get("reachable")
                        else f"Unreachable: {db_status.get('error', 'Start portable PostgreSQL on 127.0.0.1:5432')}"
                    ),
                }
            )

        if ollama_status:
            checks.append(
                {
                    "component": "Local Ollama (127.0.0.1:11434)",
                    "status": "OK" if ollama_status.get("reachable") else "ERROR",
                    "detail": (
                        f"Ollama {ollama_status.get('version', '')} | Models: {', '.join(ollama_status.get('models', []))}"
                        if ollama_status.get("reachable")
                        else f"Unreachable: {ollama_status.get('error', 'Start Ollama on 127.0.0.1:11434')}"
                    ),
                }
            )
            checks.append(
                {
                    "component": "Llama-3 8B 4096-dim Embedding Bridge",
                    "status": "OK" if ollama_status.get("llama3_bridge_ready") else "WARN",
                    "detail": str(ollama_status.get("llama3_bridge_detail", "")),
                }
            )

        return {
            "is_frozen": self.paths.is_frozen,
            "python_version": platform.python_version(),
            "executable": sys.executable,
            "project_root": str(self.paths.project_root),
            "original_repo": orig,
            "gpu": gpu,
            "postgresql": db_status,
            "ollama": ollama_status,
            "checks": checks,
        }
