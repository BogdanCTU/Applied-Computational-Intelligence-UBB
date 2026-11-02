"""Retrieval Agent coordinating syntactic, lexical, and semantic retrieval strategies."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from langchain_core.language_models import BaseChatModel

from ..config import config
from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import EntityExtractor, EntityType, OntologyEntity
from ..retrieval.syntactic_retriever import SyntacticRetriever
from ..retrieval.lexical_retriever import LexicalRetriever
from ..retrieval.semantic_retriever import SemanticRetriever
from ..retrieval.rank_fusion import reciprocal_rank_fusion
from ..db.database_manager import DatabaseManager
from ..utils.text_processing import uri_to_name


class RetrievalAgent:
    """
    Coordinates multi-strategy feature representation generation and
    candidate retrieval for ontology matching.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        llm: Optional[BaseChatModel] = None,
        embeddings_service: Optional[Any] = None,
        context: str = config.context,
        ontology_is_code: bool = False,
        similarity_threshold: float = config.similarity_threshold,
        top_k: int = config.top_k,
        num_matches: int = config.num_matches,
        rrf_k: int = 0,
    ):
        self.db = db_manager or DatabaseManager()
        self.llm = llm
        self.embeddings = embeddings_service
        self.context = context
        self.ontology_is_code = ontology_is_code
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.num_matches = num_matches
        self.rrf_k = rrf_k

        # Sub-retrievers
        self.syntactic = SyntacticRetriever(ontology_is_code=ontology_is_code)
        self.lexical = LexicalRetriever(
            llm=self.llm, context=context, ontology_is_code=ontology_is_code
        )
        self.semantic = SemanticRetriever(
            llm=self.llm, ontology_is_code=ontology_is_code
        )

    def extract_representations_for_entities(
        self,
        entities: List[OntologyEntity],
        ontology: OntologyGraph,
        progress_callback: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates syntactic, lexical, and semantic representations for a list of entities.
        """
        records: List[Dict[str, Any]] = []
        total = len(entities)

        for idx, ent in enumerate(entities, start=1):
            t0 = time.perf_counter()

            # 1. Syntactic representation (deterministic)
            syn_text = self.syntactic.retrieve_syntactic_representation(ent, ontology)

            # 2. Lexical representation (LLM meaning explanation)
            lex_text, lex_meta = self.lexical.retrieve_lexical_representation(ent, ontology)

            # 3. Semantic representation (18-predicates + blank node verbalization)
            sem_text, sem_meta = self.semantic.retrieve_semantic_representation(ent, ontology)

            duration_s = time.perf_counter() - t0

            record = {
                "entity_uri": ent.uri,
                "source_or_target": ent.source_or_target,
                "entity_type": ent.entity_type.value,
                "syntactic_matching": syn_text,
                "lexical_matching": lex_text,
                "semantic_matching": sem_text,
                "duration_s": duration_s,
            }
            records.append(record)

            if progress_callback:
                progress_callback(idx, total, ent.uri, duration_s)

        return records

    def build_features_dataframe(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Combines records and generates formatted entity_id matching Agent-OM conventions.
        Format: {index_padded}-{Source/Target}-{Class/Property}-{local_name}
        """
        combined = source_records + target_records
        df = pd.DataFrame(combined)

        num_digits = len(str(len(df)))
        df["entity_id"] = [
            f"{i + 1:0{num_digits}d}-{row['source_or_target']}-{row['entity_type']}-{uri_to_name(row['entity_uri'])}"
            for i, row in df.iterrows()
        ]

        # Reorder columns to standard schema
        cols = [
            "entity_id",
            "entity_uri",
            "source_or_target",
            "entity_type",
            "syntactic_matching",
            "lexical_matching",
            "semantic_matching",
        ]
        return df[cols]

    def ingest_features_to_database(
        self,
        df: pd.DataFrame,
        embeddings_service: Optional[Any] = None,
        vector_length: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Ingests features into PostgreSQL and populates vector tables for all 3 strategies.
        """
        emb = embeddings_service or self.embeddings
        if emb is None:
            from langchain_ollama import OllamaEmbeddings

            emb = OllamaEmbeddings(model=config.default_embedding_model)

        # 1. Main table
        self.db.create_ontology_matching_table(df)

        # 2. Embedding vector tables
        v_len = vector_length or config.vector_length
        syn_chunks = self.db.create_embedding_table(
            "syntactic_matching", df, emb, vector_length=v_len
        )
        lex_chunks = self.db.create_embedding_table(
            "lexical_matching", df, emb, vector_length=v_len
        )
        sem_chunks = self.db.create_embedding_table(
            "semantic_matching", df, emb, vector_length=v_len
        )

        return {
            "total_entities": len(df),
            "syntactic_chunks": syn_chunks,
            "lexical_chunks": lex_chunks,
            "semantic_chunks": sem_chunks,
        }

    def retrieve_strategy_candidates(
        self,
        entity_id: str,
        strategy_name: str,
    ) -> List[str]:
        """
        Executes vector similarity search for a single retrieval strategy
        (syntactic_matching, lexical_matching, or semantic_matching) without any rank fusion.
        """
        return self.db.query_strategy(
            entity_id=entity_id,
            table_name=strategy_name,
            similarity_threshold=self.similarity_threshold,
            num_matches=self.num_matches,
            top_k=self.top_k,
        )

    def retrieve_all_strategy_candidates(
        self,
        entity_id: str,
    ) -> Dict[str, List[str]]:
        """
        Queries each of the three retrieval strategies independently.
        Reproduces find_all_matching_candidate() from om_database_matching.py lines 233-246.
        Returns raw rankings dictionary before any rank fusion.
        """
        return {
            "syntactic_matching": self.retrieve_strategy_candidates(entity_id, "syntactic_matching"),
            "lexical_matching": self.retrieve_strategy_candidates(entity_id, "lexical_matching"),
            "semantic_matching": self.retrieve_strategy_candidates(entity_id, "semantic_matching"),
        }

    def retrieve_candidates_for_entity(
        self,
        entity_id: str,
        k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes syntactic, lexical, and semantic vector similarity search
        and fuses candidate rankings using Reciprocal Rank Fusion (RRF).
        
        Reproduces find_all_matching_candidate() and the RRF step of
        find_most_relevant_entity() from om_database_matching.py lines 249-285.
        """
        rrf_constant = self.rrf_k if k is None else k

        # 1. Query the 3 vector tables independently
        raw_rankings = self.retrieve_all_strategy_candidates(entity_id)
        syn_matches = raw_rankings["syntactic_matching"]
        lex_matches = raw_rankings["lexical_matching"]
        sem_matches = raw_rankings["semantic_matching"]

        # 2. Exclude dummy matches and fuse rankings
        exclude = [config.null_value_matching]
        fused = reciprocal_rank_fusion(
            syn_matches,
            lex_matches,
            sem_matches,
            k=rrf_constant,
            exclude_items=exclude,
        )

        # Map candidate entity_ids to URIs
        flat_candidates: List[str] = []
        for score, items in fused:
            for item in items:
                uri = self.db.find_entity_uri(item)
                if uri and uri not in flat_candidates:
                    flat_candidates.append(uri)

        query_uri = self.db.find_entity_uri(entity_id) or ""

        return {
            "query_entity_id": entity_id,
            "query_entity_uri": query_uri,
            "syntactic_ranking": syn_matches,
            "lexical_ranking": lex_matches,
            "semantic_ranking": sem_matches,
            "fused_ranking": fused,
            "candidate_uris": flat_candidates,
            "top_candidate_uri": flat_candidates[0] if flat_candidates else None,
        }

    def retrieve_directional_candidates(
        self,
        source_or_target: str = "Source",
        k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidates for all entities in a given direction:
        - If source_or_target == 'Source': generates candidates for Source -> Target
        - If source_or_target == 'Target': generates candidates for Target -> Source
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT entity_id FROM ontology_matching
                    WHERE source_or_target = %s
                    ORDER BY entity_id ASC;
                    """,
                    (source_or_target,),
                )
                entity_ids = [r[0] for r in cur.fetchall()]

        results = []
        for eid in entity_ids:
            res = self.retrieve_candidates_for_entity(eid, k=k)
            results.append(res)
        return results

