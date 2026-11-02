"""Configuration settings for Agent-OM Local reproduction."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application and experiment configuration."""
    
    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = project_root / "data"
    output_dir: Path = project_root / "output"
    
    # PostgreSQL Configuration
    db_host: str = os.getenv("PGHOST", "127.0.0.1")
    db_port: int = int(os.getenv("PGPORT", "5432"))
    db_name: str = os.getenv("PGDATABASE", "agent_om_local")
    db_user: str = os.getenv("PGUSER", "postgres")
    db_password: str = os.getenv("PGPASSWORD", "")
    
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

    # Ollama Models
    default_llm: str = os.getenv("AGENT_OM_LLM", "qwen3.5:9b")
    default_embedding_model: str = os.getenv("AGENT_OM_EMBEDDING", "nomic-embed-text")
    alternative_embedding_model: str = "bge-m3"
    
    # Model Embedding Dimensions
    embedding_dimensions = {
        "nomic-embed-text": 768,
        "nomic-embed-text:latest": 768,
        "bge-m3": 1024,
        "bge-m3:latest": 1024,
    }

    @property
    def vector_length(self) -> int:
        return self.embedding_dimensions.get(self.default_embedding_model, 768)

    # Retrieval & Matching Settings (matching Agent-OM defaults)
    similarity_threshold: float = 0.90
    top_k: int = 3
    num_matches: int = 50
    chunk_size: int = 500
    chunk_overlap: int = 0
    
    # Context & Null Placeholders
    context: str = "conference"
    null_value_sentence: str = "Information is not available."
    null_value_matching: str = "Entity-Dummy"
    
    # LLM Parameters
    temperature: float = 0.0
    num_ctx: int = 2048


# Default singleton instance
config = AppConfig()

