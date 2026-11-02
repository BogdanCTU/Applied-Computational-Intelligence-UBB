"""Database and pgvector manager reproducing Agent-OM storage and similarity retrieval."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import sql as pgsql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import PROTECTED_DATABASES, config, validate_loopback_host

VALID_VECTOR_TABLES = frozenset({"syntactic_matching", "lexical_matching", "semantic_matching"})


class DatabaseManager:
    """Manages PostgreSQL tables and pgvector similarity queries for ontology matching."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        allow_protected_db_write: bool = False,
    ):
        self.connection_string = connection_string or config.connection_string
        self.allow_protected_db_write = allow_protected_db_write
        parsed = urlparse(self.connection_string)
        if parsed.hostname:
            validate_loopback_host(parsed.hostname)

    @property
    def database_name(self) -> str:
        """Extract target database name from the PostgreSQL DSN."""
        parsed = urlparse(self.connection_string)
        return parsed.path.lstrip("/")

    def _assert_writable(self) -> None:
        """Prevent accidental DROP/TRUNCATE on protected historical database."""
        db_name = self.database_name
        if db_name in PROTECTED_DATABASES and not self.allow_protected_db_write:
            raise PermissionError(
                f"Destructive table recreation on protected database '{db_name}' is prohibited. "
                "Use an isolated database (e.g. 'agent_om_test', 'agent_om_parity', 'agent_om_adapted') "
                "or pass allow_protected_db_write=True explicitly when authorized."
            )

    @staticmethod
    def _validate_vector_table_name(table_name: str) -> str:
        if table_name not in VALID_VECTOR_TABLES:
            raise ValueError(
                f"Invalid vector table name '{table_name}'. Must be one of {sorted(VALID_VECTOR_TABLES)}."
            )
        return table_name

    def ensure_database_exists(self) -> None:
        """Create the target database if it does not already exist (for isolated test/run DBs)."""
        target_db = self.database_name
        if not target_db:
            raise ValueError("Cannot determine database name from connection_string.")
        parsed = urlparse(self.connection_string)
        admin_dsn = urlunparse(parsed._replace(path="/postgres"))
        conn = psycopg2.connect(admin_dsn)
        try:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
                if cur.fetchone() is None:
                    cur.execute(
                        pgsql.SQL("CREATE DATABASE {}").format(pgsql.Identifier(target_db))
                    )
        finally:
            conn.close()

    def get_connection(self):
        """Creates and configures a psycopg2 connection with vector registered."""
        conn = psycopg2.connect(self.connection_string)
        try:
            register_vector(conn)
        except psycopg2.ProgrammingError:
            # Extension may not yet be created on a brand-new isolated database
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            register_vector(conn)
        return conn

    def init_extensions(self) -> None:
        """Ensures the pgvector extension is created."""
        conn = psycopg2.connect(self.connection_string)
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
        finally:
            conn.close()

    def create_ontology_matching_table(self, df: pd.DataFrame) -> None:
        """
        Creates and populates the primary metadata table 'ontology_matching'.
        Reproduces create_ontology_matching_table in om_csv_to_database.py.
        """
        self._assert_writable()
        self.init_extensions()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS ontology_matching CASCADE;")
                cur.execute(
                    """
                    CREATE TABLE ontology_matching (
                        entity_id VARCHAR(1024) PRIMARY KEY,
                        entity_uri TEXT,
                        source_or_target TEXT,
                        entity_type TEXT,
                        syntactic_matching TEXT,
                        lexical_matching TEXT,
                        semantic_matching TEXT
                    );
                    """
                )

                records = [
                    (
                        row["entity_id"],
                        row["entity_uri"],
                        row["source_or_target"],
                        row["entity_type"],
                        "" if pd.isna(row.get("syntactic_matching", "")) else str(row.get("syntactic_matching", "")),
                        "" if pd.isna(row.get("lexical_matching", "")) else str(row.get("lexical_matching", "")),
                        "" if pd.isna(row.get("semantic_matching", "")) else str(row.get("semantic_matching", "")),
                    )
                    for _, row in df.iterrows()
                ]

                if records:
                    sql = """
                        INSERT INTO ontology_matching (
                            entity_id, entity_uri, source_or_target, entity_type,
                            syntactic_matching, lexical_matching, semantic_matching
                        ) VALUES %s;
                    """
                    execute_values(cur, sql, records)
            conn.commit()

    def create_embedding_table(
        self,
        table_name: str,
        df: pd.DataFrame,
        embeddings_service: Any,
        vector_length: Optional[int] = None,
        chunk_size: int = config.chunk_size,
        chunk_overlap: int = config.chunk_overlap,
        batch_size: int = 16,
        skip_empty_chunks: bool = True,
        null_value_sentence: str = config.null_value_sentence,
    ) -> int:
        """
        Splits matching representations, generates embeddings, validates dimensions,
        and populates vector table.

        Reproduces create_embedding_table in om_csv_to_database.py:
        When `skip_empty_chunks=True` (upstream parity default), `null_value_sentence`
        ("Information is not available.") and empty strings yield 0 chunks instead of
        storing identical placeholder embeddings that would produce false 1.0 matches.
        """
        self._assert_writable()
        self._validate_vector_table_name(table_name)
        v_len = int(vector_length) if vector_length is not None else config.vector_length
        if v_len <= 0:
            raise ValueError(f"Invalid vector_length={v_len}; must be positive.")

        text_splitter = RecursiveCharacterTextSplitter(
            separators=[".", "\n"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

        chunked: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            entity_id = row["entity_id"]
            raw_val = row.get(table_name, "")
            matching_text = "" if (raw_val is None or pd.isna(raw_val)) else str(raw_val)

            if skip_empty_chunks:
                if null_value_sentence:
                    matching_text = matching_text.replace(null_value_sentence, "")
                if not matching_text.strip():
                    continue
            else:
                if not matching_text.strip():
                    matching_text = null_value_sentence

            splits = text_splitter.create_documents([matching_text])
            for s in splits:
                if skip_empty_chunks and not s.page_content.strip():
                    continue
                chunked.append({"entity_id": entity_id, "content": s.page_content})

        # Batch embed documents and enforce strict runtime dimension verification
        for i in range(0, len(chunked), batch_size):
            batch = chunked[i : i + batch_size]
            texts = [item["content"] for item in batch]
            vectors = embeddings_service.embed_documents(texts)
            if len(vectors) != len(texts):
                raise ValueError(
                    f"Embedding count mismatch for '{table_name}': sent {len(texts)} texts, "
                    f"received {len(vectors)} vectors."
                )
            for item, vec in zip(batch, vectors):
                if len(vec) != v_len:
                    raise ValueError(
                        f"Embedding dimension mismatch for table '{table_name}' "
                        f"(entity_id='{item['entity_id']}'): expected {v_len}, got {len(vec)}."
                    )
                item["embedding"] = np.array(vec, dtype=np.float32)

        # Store in PostgreSQL
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table_name};")
                cur.execute(
                    f"""
                    CREATE TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        entity_id VARCHAR(1024) NOT NULL REFERENCES ontology_matching(entity_id),
                        content TEXT,
                        embedding vector({v_len})
                    );
                    """
                )

                records = [
                    (item["entity_id"], item["content"], item["embedding"])
                    for item in chunked
                ]

                if records:
                    sql = f"INSERT INTO {table_name} (entity_id, content, embedding) VALUES %s;"
                    execute_values(cur, sql, records)
            conn.commit()

        return len(chunked)

    def query_strategy_with_scores(
        self,
        entity_id: str,
        table_name: str,
        similarity_threshold: float = config.similarity_threshold,
        num_matches: int = config.num_matches,
        top_k: int = config.top_k,
    ) -> List[Tuple[str, float]]:
        """
        Executes vector similarity search and returns deduplicated `(entity_id, similarity)` pairs.
        Returns `[(config.null_value_matching, 0.0)]` when the query has 0 chunks or 0 matches.
        """
        self._validate_vector_table_name(table_name)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                fetch_sql = f"""
                    SELECT m.embedding, o.source_or_target, o.entity_type
                    FROM ontology_matching o, {table_name} m
                    WHERE o.entity_id = m.entity_id
                    AND o.entity_id = %s
                    ORDER BY m.id ASC
                    LIMIT 1;
                """
                cur.execute(fetch_sql, (entity_id,))
                result = cur.fetchone()
                if not result:
                    return [(config.null_value_matching, 0.0)]

                content_embedding = result[0]
                source_or_target = result[1]
                entity_type = result[2]
                opposing_source_or_target = "Target" if source_or_target == "Source" else "Source"

                search_sql = f"""
                    WITH vector_matches AS (
                        SELECT entity_id, 1 - (embedding <=> %s) AS similarity
                        FROM {table_name}
                        WHERE 1 - (embedding <=> %s) >= %s
                    )
                    SELECT o.entity_id, v.similarity AS similarity
                    FROM ontology_matching o, vector_matches v
                    WHERE o.entity_id = v.entity_id
                    AND o.source_or_target = %s
                    AND o.entity_type = %s
                    ORDER BY v.similarity DESC, o.entity_id ASC
                    LIMIT %s;
                """
                cur.execute(
                    search_sql,
                    (
                        content_embedding,
                        content_embedding,
                        similarity_threshold,
                        opposing_source_or_target,
                        entity_type,
                        num_matches,
                    ),
                )
                rows = cur.fetchall()

        if not rows:
            return [(config.null_value_matching, 0.0)]

        seen = set()
        deduped: List[Tuple[str, float]] = []
        for r in rows:
            eid = str(r[0])
            sim = float(r[1])
            if eid not in seen:
                seen.add(eid)
                deduped.append((eid, sim))
                if len(deduped) >= top_k:
                    break

        return deduped if deduped else [(config.null_value_matching, 0.0)]

    def query_strategy(
        self,
        entity_id: str,
        table_name: str,
        similarity_threshold: float = config.similarity_threshold,
        num_matches: int = config.num_matches,
        top_k: int = config.top_k,
    ) -> List[str]:
        """
        Executes vector similarity search for an entity against opposing entities of same type.
        Reproduces entity_matching() and syntactic/lexical/semantic tools in om_database_matching.py.
        """
        scored = self.query_strategy_with_scores(
            entity_id=entity_id,
            table_name=table_name,
            similarity_threshold=similarity_threshold,
            num_matches=num_matches,
            top_k=top_k,
        )
        return [eid for eid, _ in scored]

    def get_table_row_counts(self) -> Dict[str, int]:
        """Return row counts for `ontology_matching` and the three vector tables."""
        counts: Dict[str, int] = {}
        tables = ("ontology_matching", "syntactic_matching", "lexical_matching", "semantic_matching")
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for tbl in tables:
                    cur.execute(
                        "SELECT to_regclass(%s);",
                        (f"public.{tbl}",),
                    )
                    exists = cur.fetchone()[0]
                    if exists is None:
                        counts[tbl] = 0
                    else:
                        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                        counts[tbl] = int(cur.fetchone()[0])
        return counts

    def find_entity_uri(self, entity_id: str) -> Optional[str]:
        """Lookup entity_uri by entity_id."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT entity_uri FROM ontology_matching WHERE entity_id = %s;",
                    (entity_id,),
                )
                res = cur.fetchone()
                return res[0] if res else None

    def find_entity_id(self, entity_uri: str, source_or_target: str) -> Optional[str]:
        """Lookup entity_id by entity_uri and source_or_target."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT entity_id FROM ontology_matching
                    WHERE entity_uri = %s AND source_or_target = %s;
                    """,
                    (entity_uri, source_or_target),
                )
                res = cur.fetchone()
                return res[0] if res else None
