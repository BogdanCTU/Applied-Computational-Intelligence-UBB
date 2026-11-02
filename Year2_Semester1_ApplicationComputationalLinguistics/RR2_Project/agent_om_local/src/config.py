"""Configuration settings and explicit execution profiles for Agent-OM Local."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VALID_PROFILES = (
    "upstream_product_reference",
    "upstream_lite_parity",
    "local_adapted",
    "experimental",
)

PROTECTED_DATABASES = frozenset({"agent_om_local"})

CLOUD_MODEL_PREFIXES = (
    "gpt-",
    "o1-",
    "o3-",
    "text-embedding-ada",
    "text-embedding-3",
    "claude-",
)

DEFAULT_EMBEDDING_DIMENSIONS: Dict[str, int] = {
    "nomic-embed-text": 768,
    "nomic-embed-text:latest": 768,
    "bge-m3": 1024,
    "bge-m3:latest": 1024,
    "llama3:8b": 4096,
    "llama3:latest": 4096,
    # Reference-only metadata for upstream product baseline reporting (never executed):
    "text-embedding-ada-002": 1536,
}


def load_env_values(
    env_file: Optional[Path] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Load `.env` file values deterministically and overlay OS environment variables."""
    target_env = env_file if env_file is not None else (PROJECT_ROOT / ".env")
    merged: Dict[str, str] = {}
    if target_env.is_file():
        raw = dotenv_values(target_env)
        for k, v in raw.items():
            if k and v is not None:
                merged[k] = str(v)
    env_source = environ if environ is not None else os.environ
    for k, v in env_source.items():
        if v is not None:
            merged[k] = str(v)
    return merged


def _pick_env(values: Mapping[str, str], keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        if key in values and values[key] != "":
            return values[key]
        if key in values and key in ("DB_PASSWORD", "PGPASSWORD"):
            return values[key]
    return default


def validate_loopback_host(host: str) -> str:
    """Ensure PostgreSQL or local service host is strictly loopback."""
    cleaned = str(host).strip()
    if cleaned not in ("127.0.0.1", "localhost"):
        raise ValueError(
            f"Non-loopback host '{cleaned}' is prohibited. Only '127.0.0.1' or 'localhost' is permitted."
        )
    return cleaned


def validate_loopback_url(url: str) -> str:
    """Ensure Ollama base URL points strictly to loopback."""
    cleaned = str(url).strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError(
            f"Non-loopback Ollama URL '{cleaned}' is prohibited. Use http://127.0.0.1:11434."
        )
    return cleaned


@dataclass
class AppConfig:
    """Application, parity, and experiment configuration."""

    # Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"

    # Profile metadata
    profile_name: str = "local_adapted"
    reference_only: bool = False

    # PostgreSQL Configuration (harmonized DB_* and PG* env names)
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "agent_om_local"
    db_user: str = "postgres"
    db_password: str = ""

    # Ollama Configuration (harmonized DEFAULT_* and AGENT_OM_* env names)
    ollama_host: str = "http://127.0.0.1:11434"
    default_llm: str = "qwen3.5:9b"
    default_embedding_model: str = "nomic-embed-text"
    alternative_embedding_model: str = "bge-m3"
    embedding_dim: Optional[int] = None
    embedding_dimensions: Dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_EMBEDDING_DIMENSIONS)
    )

    # Retrieval & Matching Settings (matching Agent-OM defaults)
    similarity_threshold: float = 0.90
    top_k: int = 3
    num_matches: int = 50
    rrf_k: int = 0
    chunk_size: int = 500
    chunk_overlap: int = 0

    # Ontology Code-IRI Settings
    o1_is_code: bool = False
    o2_is_code: bool = False

    # Context & Null Placeholders
    context: str = "conference"
    null_value_sentence: str = "Information is not available."
    null_value_matching: str = "Entity-Dummy"

    # Explicit LLM Sampling & Context Parameters
    temperature: float = 0.0
    seed: Optional[int] = 42
    llm_top_k: Optional[int] = 1
    top_p: Optional[float] = 1.0
    repeat_penalty: Optional[float] = 1.0
    num_ctx: int = 2048
    reasoning: Optional[bool] = False

    # Algorithmic Parity Flags (Phase 4)
    skip_empty_chunks: bool = True
    combine_properties_sort: bool = True
    indent_validation_prompt: bool = False
    semantic_concat_separator: str = "\n"
    strip_llm_responses: bool = True
    sort_lexical_annotations: bool = True
    sort_bnode_triples: bool = True
    predicate_scope: str = "head"  # "head" (10 lex + 18 sem + bnode) or "pvl_v1" (2 lex + 7 sem)
    tool_routing_mode: str = "deterministic"  # "deterministic" or "llm_json"

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        self.data_dir = Path(self.data_dir)
        self.output_dir = Path(self.output_dir)
        self.db_host = validate_loopback_host(self.db_host)
        self.db_port = int(self.db_port)
        self.ollama_host = validate_loopback_url(self.ollama_host)
        if self.profile_name not in VALID_PROFILES:
            raise ValueError(
                f"Invalid profile_name '{self.profile_name}'. Must be one of {VALID_PROFILES}."
            )
        if self.tool_routing_mode not in ("deterministic", "llm_json"):
            raise ValueError(
                f"Invalid tool_routing_mode '{self.tool_routing_mode}'. Expected 'deterministic' or 'llm_json'."
            )
        if self.predicate_scope not in ("head", "pvl_v1"):
            raise ValueError(
                f"Invalid predicate_scope '{self.predicate_scope}'. Expected 'head' or 'pvl_v1'."
            )

    @classmethod
    def from_env(
        cls,
        env_file: Optional[Path] = None,
        environ: Optional[Mapping[str, str]] = None,
        **overrides: Any,
    ) -> "AppConfig":
        """Construct AppConfig deterministically from `.env` + environment + overrides."""
        vals = load_env_values(env_file=env_file, environ=environ)
        profile_name = overrides.pop(
            "profile_name",
            _pick_env(vals, ("CONFIG_PROFILE", "AGENT_OM_PROFILE"), "local_adapted"),
        )
        kwargs: Dict[str, Any] = {
            "profile_name": profile_name,
            "db_host": _pick_env(vals, ("DB_HOST", "PGHOST"), "127.0.0.1"),
            "db_port": int(_pick_env(vals, ("DB_PORT", "PGPORT"), "5432")),
            "db_name": _pick_env(vals, ("DB_NAME", "PGDATABASE"), "agent_om_local"),
            "db_user": _pick_env(vals, ("DB_USER", "PGUSER"), "postgres"),
            "db_password": _pick_env(vals, ("DB_PASSWORD", "PGPASSWORD"), ""),
            "ollama_host": _pick_env(vals, ("OLLAMA_HOST",), "http://127.0.0.1:11434"),
            "default_llm": _pick_env(
                vals, ("DEFAULT_CHAT_MODEL", "AGENT_OM_LLM"), "qwen3.5:9b"
            ),
            "default_embedding_model": _pick_env(
                vals, ("DEFAULT_EMBEDDING_MODEL", "AGENT_OM_EMBEDDING"), "nomic-embed-text"
            ),
            "temperature": float(_pick_env(vals, ("TEMPERATURE",), "0.0")),
            "num_ctx": int(_pick_env(vals, ("NUM_CTX",), "2048")),
            "seed": int(_pick_env(vals, ("SEED",), "42")),
            "llm_top_k": int(_pick_env(vals, ("LLM_TOP_K",), "1")),
            "top_p": float(_pick_env(vals, ("TOP_P",), "1.0")),
            "repeat_penalty": float(_pick_env(vals, ("REPEAT_PENALTY",), "1.0")),
        }
        kwargs.update(overrides)
        return cls(**kwargs)

    @classmethod
    def from_profile(
        cls,
        profile_name: str,
        env_file: Optional[Path] = None,
        environ: Optional[Mapping[str, str]] = None,
        **overrides: Any,
    ) -> "AppConfig":
        """Construct one of the four explicit scientific replication profiles."""
        if profile_name not in VALID_PROFILES:
            raise ValueError(
                f"Unknown profile '{profile_name}'. Valid profiles: {VALID_PROFILES}"
            )

        vals = load_env_values(env_file=env_file, environ=environ)
        base_db: Dict[str, Any] = {
            "db_host": _pick_env(vals, ("DB_HOST", "PGHOST"), "127.0.0.1"),
            "db_port": int(_pick_env(vals, ("DB_PORT", "PGPORT"), "5432")),
            "db_user": _pick_env(vals, ("DB_USER", "PGUSER"), "postgres"),
            "db_password": _pick_env(vals, ("DB_PASSWORD", "PGPASSWORD"), ""),
            "ollama_host": _pick_env(vals, ("OLLAMA_HOST",), "http://127.0.0.1:11434"),
        }

        if profile_name == "upstream_product_reference":
            profile_defaults: Dict[str, Any] = {
                **base_db,
                "profile_name": "upstream_product_reference",
                "reference_only": True,
                "db_name": "agent_om_reference_readonly",
                "default_llm": "gpt-4o-2024-05-13",
                "default_embedding_model": "text-embedding-ada-002",
                "embedding_dim": 1536,
                "temperature": 0.0,
                "seed": 42,
                "llm_top_k": None,
                "top_p": 1.0,
                "repeat_penalty": None,
                "num_ctx": 2048,
                "reasoning": None,
                "skip_empty_chunks": True,
                "combine_properties_sort": True,
                "indent_validation_prompt": True,
                "semantic_concat_separator": "",
                "strip_llm_responses": False,
                "sort_lexical_annotations": False,
                "sort_bnode_triples": False,
                "predicate_scope": "head",
                "tool_routing_mode": "llm_json",
            }
        elif profile_name == "upstream_lite_parity":
            profile_defaults = {
                **base_db,
                "profile_name": "upstream_lite_parity",
                "reference_only": False,
                "db_name": "agent_om_parity",
                "default_llm": "llama3:8b",
                "default_embedding_model": "llama3:8b",
                "embedding_dim": 4096,
                "temperature": 0.0,
                "seed": 42,
                "llm_top_k": 1,
                "top_p": 1.0,
                "repeat_penalty": 1.0,
                "num_ctx": 2048,
                "reasoning": None,
                "skip_empty_chunks": True,
                "combine_properties_sort": True,
                "indent_validation_prompt": True,
                "semantic_concat_separator": "",
                "strip_llm_responses": False,
                "sort_lexical_annotations": True,
                "sort_bnode_triples": True,
                "predicate_scope": "head",
                "tool_routing_mode": "deterministic",
            }
        elif profile_name == "local_adapted":
            profile_defaults = {
                **base_db,
                "profile_name": "local_adapted",
                "reference_only": False,
                "db_name": "agent_om_adapted",
                "default_llm": "qwen3.5:9b",
                "default_embedding_model": "nomic-embed-text",
                "embedding_dim": 768,
                "temperature": 0.0,
                "seed": 42,
                "llm_top_k": 1,
                "top_p": 1.0,
                "repeat_penalty": 1.0,
                "num_ctx": 2048,
                "reasoning": False,
                "skip_empty_chunks": True,
                "combine_properties_sort": True,
                "indent_validation_prompt": False,
                "semantic_concat_separator": "\n",
                "strip_llm_responses": True,
                "sort_lexical_annotations": True,
                "sort_bnode_triples": True,
                "predicate_scope": "head",
                "tool_routing_mode": "deterministic",
            }
        else:  # experimental
            profile_defaults = {
                **base_db,
                "profile_name": "experimental",
                "reference_only": False,
                "db_name": "agent_om_experimental",
                "default_llm": _pick_env(
                    vals, ("DEFAULT_CHAT_MODEL", "AGENT_OM_LLM"), "qwen3.5:9b"
                ),
                "default_embedding_model": _pick_env(
                    vals, ("DEFAULT_EMBEDDING_MODEL", "AGENT_OM_EMBEDDING"), "nomic-embed-text"
                ),
                "embedding_dim": None,
                "temperature": 0.0,
                "seed": 42,
                "llm_top_k": 1,
                "top_p": 1.0,
                "repeat_penalty": 1.0,
                "num_ctx": 2048,
                "reasoning": False,
                "skip_empty_chunks": True,
                "combine_properties_sort": True,
                "indent_validation_prompt": False,
                "semantic_concat_separator": "\n",
                "strip_llm_responses": True,
                "sort_lexical_annotations": True,
                "sort_bnode_triples": True,
                "predicate_scope": "head",
                "tool_routing_mode": "deterministic",
            }

        profile_defaults.update(overrides)
        return cls(**profile_defaults)

    @property
    def connection_string(self) -> str:
        """Construct synchronous psycopg2 connection DSN."""
        if self.db_password:
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return f"postgresql://{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_connection_string(self) -> str:
        """Construct asynchronous asyncpg connection DSN."""
        return self.connection_string

    @property
    def vector_length(self) -> int:
        """Resolve exact vector dimension; raise ValueError rather than silently falling back to 768."""
        if self.embedding_dim is not None:
            if int(self.embedding_dim) <= 0:
                raise ValueError(f"Invalid embedding_dim={self.embedding_dim}; must be positive.")
            return int(self.embedding_dim)
        model_key = str(self.default_embedding_model).strip()
        if model_key in self.embedding_dimensions:
            return int(self.embedding_dimensions[model_key])
        raise ValueError(
            f"Unknown embedding dimension for model '{model_key}'. "
            f"Known models: {sorted(self.embedding_dimensions.keys())}. "
            f"Pass embedding_dim explicitly; silent fallback to 768 is prohibited."
        )

    def ensure_executable(self) -> None:
        """Verify this configuration is safe and permitted for local inference execution."""
        if self.reference_only or self.profile_name == "upstream_product_reference":
            raise PermissionError(
                f"Profile '{self.profile_name}' is reference-only (committed upstream artifacts). "
                "Cloud LLM and paid API execution are strictly prohibited."
            )
        for model_field in (self.default_llm, self.default_embedding_model):
            lower = str(model_field).strip().lower()
            if any(lower.startswith(prefix) for prefix in CLOUD_MODEL_PREFIXES):
                raise PermissionError(
                    f"Cloud model '{model_field}' is prohibited. Only local Ollama models on 127.0.0.1 are allowed."
                )
        validate_loopback_host(self.db_host)
        validate_loopback_url(self.ollama_host)

    def build_chat_llm(self, **overrides: Any) -> Any:
        """Instantiate a configured local `ChatOllama` model with explicit sampling parameters."""
        self.ensure_executable()
        from langchain_ollama import ChatOllama

        kwargs: Dict[str, Any] = {
            "model": self.default_llm,
            "base_url": self.ollama_host,
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed
        if self.llm_top_k is not None:
            kwargs["top_k"] = self.llm_top_k
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        if self.repeat_penalty is not None:
            kwargs["repeat_penalty"] = self.repeat_penalty
        if self.reasoning is not None:
            kwargs["reasoning"] = self.reasoning
        kwargs.update(overrides)
        return ChatOllama(**kwargs)

    def build_embeddings_service(self, **overrides: Any) -> Any:
        """Instantiate local embeddings service (`LlamaBridgeEmbeddings` for `llama3*`, else `OllamaEmbeddings`)."""
        self.ensure_executable()
        v_len = self.vector_length
        model_name = str(self.default_embedding_model).strip()
        if model_name.lower().startswith("llama3"):
            from .utils.llama_embed_bridge import LlamaBridgeEmbeddings

            return LlamaBridgeEmbeddings(
                model_name=model_name,
                expected_dim=v_len,
                ctx_size=self.num_ctx,
                ollama_base_url=self.ollama_host,
                **overrides,
            )
        from langchain_ollama import OllamaEmbeddings

        kwargs: Dict[str, Any] = {
            "model": model_name,
            "base_url": self.ollama_host,
        }
        kwargs.update(overrides)
        return OllamaEmbeddings(**kwargs)

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable configuration snapshot with password redacted."""
        resolved_dim: Optional[int]
        try:
            resolved_dim = self.vector_length
        except ValueError:
            resolved_dim = None
        return {
            "profile_name": self.profile_name,
            "reference_only": self.reference_only,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "ollama_host": self.ollama_host,
            "default_llm": self.default_llm,
            "default_embedding_model": self.default_embedding_model,
            "vector_length": resolved_dim,
            "similarity_threshold": self.similarity_threshold,
            "top_k": self.top_k,
            "num_matches": self.num_matches,
            "rrf_k": self.rrf_k,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "o1_is_code": self.o1_is_code,
            "o2_is_code": self.o2_is_code,
            "context": self.context,
            "temperature": self.temperature,
            "seed": self.seed,
            "llm_top_k": self.llm_top_k,
            "top_p": self.top_p,
            "repeat_penalty": self.repeat_penalty,
            "num_ctx": self.num_ctx,
            "reasoning": self.reasoning,
            "skip_empty_chunks": self.skip_empty_chunks,
            "combine_properties_sort": self.combine_properties_sort,
            "indent_validation_prompt": self.indent_validation_prompt,
            "semantic_concat_separator": self.semantic_concat_separator,
            "strip_llm_responses": self.strip_llm_responses,
            "sort_lexical_annotations": self.sort_lexical_annotations,
            "sort_bnode_triples": self.sort_bnode_triples,
            "predicate_scope": self.predicate_scope,
            "tool_routing_mode": self.tool_routing_mode,
        }


# Default singleton instance loaded deterministically from .env / environment
config = AppConfig.from_env()
