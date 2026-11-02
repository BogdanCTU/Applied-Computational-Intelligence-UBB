"""Retrieval Agent coordinating syntactic, lexical, and semantic retrieval strategies."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from ..config import AppConfig, config
from ..ontology.parser import OntologyGraph
from ..ontology.entity_extractor import OntologyEntity
from ..retrieval.syntactic_retriever import SyntacticRetriever
from ..retrieval.lexical_retriever import LexicalRetriever
from ..retrieval.semantic_retriever import SemanticRetriever
from ..retrieval.rank_fusion import reciprocal_rank_fusion
from ..db.database_manager import DatabaseManager
from ..utils.text_processing import uri_to_name
from .tool_router import LLMJsonToolRouter, ToolRouterStats


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
        o1_is_code: Optional[bool] = None,
        o2_is_code: Optional[bool] = None,
        similarity_threshold: float = config.similarity_threshold,
        top_k: int = config.top_k,
        num_matches: int = config.num_matches,
        rrf_k: int = 0,
        tool_routing_mode: Optional[str] = None,
        strict_tool_router: bool = False,
        skip_empty_chunks: Optional[bool] = None,
        app_config: Optional[AppConfig] = None,
    ):
        self.app_config = app_config or config
        self.db = db_manager or DatabaseManager(connection_string=self.app_config.connection_string)
        self.llm = llm
        self.embeddings = embeddings_service
        self.context = context
        self.ontology_is_code = ontology_is_code
        self.o1_is_code = o1_is_code
        self.o2_is_code = o2_is_code
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.num_matches = num_matches
        self.rrf_k = rrf_k
        self.tool_routing_mode = tool_routing_mode or self.app_config.tool_routing_mode
        self.strict_tool_router = strict_tool_router
        self.skip_empty_chunks = (
            self.app_config.skip_empty_chunks if skip_empty_chunks is None else skip_empty_chunks
        )

        # Sub-retrievers honoring parity flags from app_config
        self.syntactic = SyntacticRetriever(ontology_is_code=ontology_is_code)
        self.lexical = LexicalRetriever(
            llm=self.llm,
            context=context,
            ontology_is_code=ontology_is_code,
            predicate_scope=self.app_config.predicate_scope,
            sort_annotations=self.app_config.sort_lexical_annotations,
            strip_response=self.app_config.strip_llm_responses,
            app_config=self.app_config,
        )
        self.semantic = SemanticRetriever(
            llm=self.llm,
            ontology_is_code=ontology_is_code,
            null_value_sentence=self.app_config.null_value_sentence,
            predicate_scope=self.app_config.predicate_scope,
            concat_separator=self.app_config.semantic_concat_separator,
            strip_response=self.app_config.strip_llm_responses,
            sort_bnode_triples=self.app_config.sort_bnode_triples,
            app_config=self.app_config,
        )
        self.router_stats = ToolRouterStats()
        self.last_extraction_telemetry: Dict[str, Any] = {
            "llm_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "router_calls": 0,
            "router_prompt_tokens": 0,
            "router_completion_tokens": 0,
            "router_errors": 0,
        }

    def _resolve_is_code_for_entity(
        self,
        ent: OntologyEntity,
        override_is_code: Optional[bool] = None,
    ) -> bool:
        if override_is_code is not None:
            return override_is_code
        if ent.source_or_target == "Source" and self.o1_is_code is not None:
            return self.o1_is_code
        if ent.source_or_target == "Target" and self.o2_is_code is not None:
            return self.o2_is_code
        return self.ontology_is_code

    def _ensure_llm(self) -> BaseChatModel:
        if self.llm is None:
            self.llm = self.app_config.build_chat_llm()
        return self.llm

    def extract_representations_for_entities(
        self,
        entities: List[OntologyEntity],
        ontology: OntologyGraph,
        progress_callback: Optional[Any] = None,
        ontology_is_code: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates syntactic, lexical, and semantic representations for a list of entities.
        Supports both deterministic Python orchestration (`tool_routing_mode='deterministic'`)
        and upstream LLM JSON tool routing (`tool_routing_mode='llm_json'`).
        """
        records: List[Dict[str, Any]] = []
        total = len(entities)
        total_llm_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0

        router: Optional[LLMJsonToolRouter] = None
        active_state: Dict[str, Any] = {"ent": None, "lex_meta": {}, "sem_meta": {}}

        if self.tool_routing_mode == "llm_json" and entities:
            agent_self = self

            @tool
            def syntactic(entity: str) -> str:
                """Retrieve syntactic information."""
                target_ent = active_state["ent"] or entity
                return agent_self.syntactic.retrieve_syntactic_representation(target_ent, ontology)

            @tool
            def lexical(entity: str) -> str:
                """Retrieve lexical information."""
                target_ent = active_state["ent"] or entity
                txt, meta = agent_self.lexical.retrieve_lexical_representation(target_ent, ontology)
                active_state["lex_meta"] = meta
                return txt

            @tool
            def semantic(entity: str) -> str:
                """Retrieve semantic information."""
                target_ent = active_state["ent"] or entity
                txt, meta = agent_self.semantic.retrieve_semantic_representation(target_ent, ontology)
                active_state["sem_meta"] = meta
                return txt

            router = LLMJsonToolRouter(
                llm=self._ensure_llm(),
                tools=[syntactic, lexical, semantic],
                strict=self.strict_tool_router,
                allow_fallback=not self.strict_tool_router,
            )

        for idx, ent in enumerate(entities, start=1):
            t0 = time.perf_counter()
            is_code = self._resolve_is_code_for_entity(ent, ontology_is_code)
            self.syntactic.ontology_is_code = is_code
            self.lexical.ontology_is_code = is_code
            self.semantic.ontology_is_code = is_code

            if router is not None:
                active_state["ent"] = ent
                active_state["lex_meta"] = {}
                active_state["sem_meta"] = {}
                syn_text = str(
                    router.invoke(
                        f"Retrieve syntactic information for {ent.uri}",
                        expected_tool_name="syntactic",
                        fallback_args={"entity": ent.uri},
                    )
                )
                lex_text = str(
                    router.invoke(
                        f"Retrieve lexical information for {ent.uri}",
                        expected_tool_name="lexical",
                        fallback_args={"entity": ent.uri},
                    )
                )
                sem_text = str(
                    router.invoke(
                        f"Retrieve semantic information for {ent.uri}",
                        expected_tool_name="semantic",
                        fallback_args={"entity": ent.uri},
                    )
                )
                lex_meta = active_state["lex_meta"]
                sem_meta = active_state["sem_meta"]
            else:
                # 1. Syntactic representation (deterministic)
                syn_text = self.syntactic.retrieve_syntactic_representation(ent, ontology)
                # 2. Lexical representation (LLM meaning explanation)
                lex_text, lex_meta = self.lexical.retrieve_lexical_representation(ent, ontology)
                # 3. Semantic representation (18-predicates + blank node verbalization)
                sem_text, sem_meta = self.semantic.retrieve_semantic_representation(ent, ontology)

            duration_s = time.perf_counter() - t0
            ent_llm_calls = int(lex_meta.get("llm_calls", 1)) + int(sem_meta.get("llm_calls", 0))
            ent_p_tok = int(lex_meta.get("prompt_tokens", 0)) + int(sem_meta.get("prompt_tokens", 0))
            ent_c_tok = int(lex_meta.get("completion_tokens", 0)) + int(sem_meta.get("completion_tokens", 0))
            total_llm_calls += ent_llm_calls
            total_prompt_tokens += ent_p_tok
            total_completion_tokens += ent_c_tok

            record = {
                "entity_uri": ent.uri,
                "source_or_target": ent.source_or_target,
                "entity_type": ent.entity_type.value,
                "syntactic_matching": syn_text,
                "lexical_matching": lex_text,
                "semantic_matching": sem_text,
                "duration_s": duration_s,
                "llm_calls": ent_llm_calls,
                "prompt_tokens": ent_p_tok,
                "completion_tokens": ent_c_tok,
            }
            records.append(record)

            if progress_callback:
                progress_callback(idx, total, ent.uri, duration_s)

        if router is not None:
            self.router_stats.total_calls += router.stats.total_calls
            self.router_stats.total_duration_ms += router.stats.total_duration_ms
            self.router_stats.total_prompt_tokens += router.stats.total_prompt_tokens
            self.router_stats.total_completion_tokens += router.stats.total_completion_tokens
            self.router_stats.parse_or_schema_errors += router.stats.parse_or_schema_errors
            self.router_stats.fallback_invocations += router.stats.fallback_invocations
            self.router_stats.error_messages.extend(router.stats.error_messages)

        self.last_extraction_telemetry = {
            "llm_calls": total_llm_calls + (router.stats.total_calls if router else 0),
            "feature_llm_calls": total_llm_calls,
            "prompt_tokens": total_prompt_tokens + (router.stats.total_prompt_tokens if router else 0),
            "completion_tokens": total_completion_tokens + (router.stats.total_completion_tokens if router else 0),
            "router_calls": router.stats.total_calls if router else 0,
            "router_prompt_tokens": router.stats.total_prompt_tokens if router else 0,
            "router_completion_tokens": router.stats.total_completion_tokens if router else 0,
            "router_errors": router.stats.parse_or_schema_errors if router else 0,
        }

        return records

    def build_features_dataframe(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        source_ontology: Optional[OntologyGraph] = None,
        target_ontology: Optional[OntologyGraph] = None,
    ) -> pd.DataFrame:
        """
        Combines records and generates formatted entity_id matching Agent-OM conventions.
        Format: {index_padded}-{Source/Target}-{Class/Property}-{entity_name}
        Reproduces `om_ontology_to_csv.py:345` (`get_entity_name` when `ontology_is_code=True`).
        """
        combined = source_records + target_records
        df = pd.DataFrame(combined)
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "entity_id",
                    "entity_uri",
                    "source_or_target",
                    "entity_type",
                    "syntactic_matching",
                    "lexical_matching",
                    "semantic_matching",
                ]
            )

        num_digits = len(str(len(df)))
        entity_ids: List[str] = []
        for i, row in df.iterrows():
            uri = str(row["entity_uri"])
            side = str(row["source_or_target"])
            if side == "Source" and (self.o1_is_code or self.ontology_is_code) and source_ontology is not None:
                name_part = source_ontology.resolve_entity_name(uri, ontology_is_code=True)
            elif side == "Target" and (self.o2_is_code or self.ontology_is_code) and target_ontology is not None:
                name_part = target_ontology.resolve_entity_name(uri, ontology_is_code=True)
            else:
                name_part = uri_to_name(uri)
            entity_ids.append(f"{i + 1:0{num_digits}d}-{side}-{row['entity_type']}-{name_part}")

        df["entity_id"] = entity_ids

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
        skip_empty_chunks: Optional[bool] = None,
    ) -> Dict[str, int]:
        """
        Ingests features into PostgreSQL and populates vector tables for all 3 strategies.
        """
        emb = embeddings_service or self.embeddings
        created_temporarily = False
        if emb is None:
            emb = self.app_config.build_embeddings_service()
            created_temporarily = True

        use_skip_empty = self.skip_empty_chunks if skip_empty_chunks is None else skip_empty_chunks
        v_len = int(vector_length) if vector_length is not None else self.app_config.vector_length

        try:
            # 1. Main table
            self.db.create_ontology_matching_table(df)

            # 2. Embedding vector tables
            syn_chunks = self.db.create_embedding_table(
                "syntactic_matching",
                df,
                emb,
                vector_length=v_len,
                chunk_size=self.app_config.chunk_size,
                chunk_overlap=self.app_config.chunk_overlap,
                skip_empty_chunks=use_skip_empty,
                null_value_sentence=self.app_config.null_value_sentence,
            )
            lex_chunks = self.db.create_embedding_table(
                "lexical_matching",
                df,
                emb,
                vector_length=v_len,
                chunk_size=self.app_config.chunk_size,
                chunk_overlap=self.app_config.chunk_overlap,
                skip_empty_chunks=use_skip_empty,
                null_value_sentence=self.app_config.null_value_sentence,
            )
            sem_chunks = self.db.create_embedding_table(
                "semantic_matching",
                df,
                emb,
                vector_length=v_len,
                chunk_size=self.app_config.chunk_size,
                chunk_overlap=self.app_config.chunk_overlap,
                skip_empty_chunks=use_skip_empty,
                null_value_sentence=self.app_config.null_value_sentence,
            )
        finally:
            if hasattr(emb, "release_vram"):
                emb.release_vram()
            if created_temporarily and hasattr(emb, "close"):
                emb.close()

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

        # 1. Query the 3 vector tables independently (with scores for inspection)
        syn_scored = self.db.query_strategy_with_scores(
            entity_id, "syntactic_matching", self.similarity_threshold, self.num_matches, self.top_k
        )
        lex_scored = self.db.query_strategy_with_scores(
            entity_id, "lexical_matching", self.similarity_threshold, self.num_matches, self.top_k
        )
        sem_scored = self.db.query_strategy_with_scores(
            entity_id, "semantic_matching", self.similarity_threshold, self.num_matches, self.top_k
        )

        syn_matches = [eid for eid, _ in syn_scored]
        lex_matches = [eid for eid, _ in lex_scored]
        sem_matches = [eid for eid, _ in sem_scored]

        # 2. Exclude dummy matches and fuse rankings
        exclude = [self.app_config.null_value_matching]
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
            "syntactic_scores": [
                {"entity_id": eid, "similarity": sim}
                for eid, sim in syn_scored
                if eid != self.app_config.null_value_matching
            ],
            "lexical_scores": [
                {"entity_id": eid, "similarity": sim}
                for eid, sim in lex_scored
                if eid != self.app_config.null_value_matching
            ],
            "semantic_scores": [
                {"entity_id": eid, "similarity": sim}
                for eid, sim in sem_scored
                if eid != self.app_config.null_value_matching
            ],
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
