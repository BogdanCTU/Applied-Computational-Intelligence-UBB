"""Database and pgvector manager reproducing Agent-OM storage and similarity retrieval."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import config
from ..utils.text_processing import uri_to_name


class DatabaseManager:
    """Manages PostgreSQL tables and pgvector similarity queries for ontology matching."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or config.connection_string

    def get_connection(self):
        """Creates and configures a psycopg2 connection with vector registered."""
        conn = psycopg2.connect(self.connection_string)
        register_vector(conn)
        return conn

    def init_extensions(self) -> None:
        """Ensures the pgvector extension is created."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()

    def create_ontology_matching_table(self, df: pd.DataFrame) -> None:
        """
        Creates and populates the primary metadata table 'ontology_matching'.
        Reproduces create_ontology_matching_table in om_csv_to_database.py.
        """
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
                        row.get("syntactic_matching", ""),
                        row.get("lexical_matching", ""),
                        row.get("semantic_matching", ""),
                    )
                    for _, row in df.iterrows()
                ]

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
    ) -> int:
        """
        Splits matching representations, generates embeddings, and populates vector table.
        Reproduces create_embedding_table in om_csv_to_database.py.
        """
        v_len = vector_length or config.vector_length
        text_splitter = RecursiveCharacterTextSplitter(
            separators=[".", "\n"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

        chunked: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            entity_id = row["entity_id"]
            matching_text = str(row.get(table_name, "") or "")
            if not matching_text.strip():
                # Provide dummy placeholder if empty so an embedding entry exists
                matching_text = config.null_value_sentence

            splits = text_splitter.create_documents([matching_text])
            for s in splits:
                chunked.append({"entity_id": entity_id, "content": s.page_content})

        # Batch embed documents
        for i in range(0, len(chunked), batch_size):
            batch = chunked[i : i + batch_size]
            texts = [item["content"] for item in batch]
            vectors = embeddings_service.embed_documents(texts)
            for item, vec in zip(batch, vectors):
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

                sql = f"INSERT INTO {table_name} (entity_id, content, embedding) VALUES %s;"
                execute_values(cur, sql, records)
            conn.commit()

        return len(chunked)

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
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Fetch query entity's embedding, source_or_target, and entity_type
                fetch_sql = f"""
                    SELECT m.embedding, o.source_or_target, o.entity_type
                    FROM ontology_matching o, {table_name} m
                    WHERE o.entity_id = m.entity_id
                    AND o.entity_id = %s;
                """
                cur.execute(fetch_sql, (entity_id,))
                result = cur.fetchone()
                if not result:
                    return [config.null_value_matching]

                content_embedding = result[0]
                source_or_target = result[1]
                entity_type = result[2]

                # Target opposing ontology
                opposing_source_or_target = "Target" if source_or_target == "Source" else "Source"

                # 2. Cosine similarity search using pgvector
                # Note: 1 - (embedding <=> query_vec) gives cosine similarity
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
                    ORDER BY v.similarity DESC
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
            return [config.null_value_matching]

        # Deduplicate while preserving rank order, then take top_k
        seen = set()
        deduped = []
        for r in rows:
            eid = r[0]
            if eid not in seen:
                seen.add(eid)
                deduped.append(eid)
                if len(deduped) >= top_k:
                    break

        return deduped if deduped else [config.null_value_matching]

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

