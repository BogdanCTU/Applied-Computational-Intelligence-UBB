"""Configuration profile management, validation, and JSON preset import/export service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ...config import PROTECTED_DATABASES, VALID_PROFILES, AppConfig
from ..paths import ProjectPaths, resolve_project_paths


class ConfigurationService:
    """Manages replication configuration profiles and enforces safety/loopback constraints."""

    PROFILE_DESCRIPTIONS: Dict[str, str] = {
        "upstream_product_reference": (
            "Read-Only Reference Profile — Documents upstream Agent-OM product settings "
            "(gpt-4o-2024-05-13 + text-embedding-ada-002, 1536-dim). Cloud execution is disabled."
        ),
        "upstream_lite_parity": (
            "Upstream Agent-OM-Lite Parity — Local llama3:8b chat + llama3:8b 4096-dim embeddings, "
            "temp=0.0, seed=42, top_k=1, repeat_penalty=1.0, 28-space prompt, skip_empty_chunks=True."
        ),
        "local_adapted": (
            "Local Adapted Configuration — Local qwen3.5:9b (reasoning=False) + nomic-embed-text "
            "768-dim embeddings, deterministic orchestration, isolated DB agent_om_adapted."
        ),
        "experimental": (
            "Experimental / Ablation Profile — Customizable similarity threshold, top_k, rrf_k, "
            "predicate scope (head vs pvl_v1), and tool routing mode (deterministic vs llm_json)."
        ),
    }

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or resolve_project_paths()

    def list_profiles(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p,
                "description": self.PROFILE_DESCRIPTIONS.get(p, ""),
                "reference_only": p == "upstream_product_reference",
            }
            for p in VALID_PROFILES
        ]

    def build_config(self, profile_name: str, **overrides: Any) -> AppConfig:
        return AppConfig.from_profile(profile_name, **overrides)

    def validate_for_execution(self, cfg: AppConfig) -> Dict[str, Any]:
        """Validate whether `cfg` can safely execute locally without touching protected DBs."""
        issues: List[str] = []
        if cfg.reference_only or cfg.profile_name == "upstream_product_reference":
            issues.append(
                "Profile 'upstream_product_reference' is read-only reference metadata; select an executable local profile."
            )
        else:
            try:
                cfg.ensure_executable()
            except Exception as exc:
                issues.append(str(exc))

        try:
            _ = cfg.vector_length
        except Exception as exc:
            issues.append(str(exc))

        if cfg.db_name in PROTECTED_DATABASES:
            issues.append(
                f"Target database '{cfg.db_name}' is protected to preserve historical results. "
                "Specify an isolated database (e.g. agent_om_parity, agent_om_adapted, agent_om_experimental)."
            )

        if not (0.0 <= cfg.similarity_threshold <= 1.0):
            issues.append("similarity_threshold must be between 0.0 and 1.0.")
        if cfg.top_k < 1:
            issues.append("top_k must be >= 1.")

        return {"valid": len(issues) == 0, "issues": issues, "metadata": cfg.to_metadata_dict()}

    def save_preset(self, cfg: AppConfig, preset_path: str | Path) -> Path:
        out = Path(preset_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(cfg.to_metadata_dict(), indent=2), encoding="utf-8")
        return out

    def load_preset(self, preset_path: str | Path) -> AppConfig:
        data = json.loads(Path(preset_path).read_text(encoding="utf-8"))
        profile = str(data.pop("profile_name", "experimental"))
        # Remove computed vector_length key before passing overrides
        vec_len = data.pop("vector_length", None)
        if vec_len is not None and "embedding_dim" not in data:
            data["embedding_dim"] = int(vec_len)
        data.pop("reference_only", None)
        return AppConfig.from_profile(profile, **data)

