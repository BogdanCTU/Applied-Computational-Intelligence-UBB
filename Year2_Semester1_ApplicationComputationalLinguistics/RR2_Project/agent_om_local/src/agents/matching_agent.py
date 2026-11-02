"""Matching Agent coordinating RRF candidate selection, LLM validation, and reciprocal merger."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from langchain_core.language_models import BaseChatModel

from ..config import config
from ..db.database_manager import DatabaseManager
from ..matching.merger import ReciprocalMerger
from ..matching.validator import MatchingValidator, ValidationRecord
from ..retrieval.rank_fusion import reciprocal_rank_fusion
from ..utils.text_processing import uri_to_name


@dataclass
class DirectionalMatchResult:
    """Result of directional matching (Source->Target or Target->Source)."""
    direction: str
    query_entity_count: int
    matched_entity_count: int
    predicted_pairs: Set[Tuple[str, str]]
    validation_records: List[ValidationRecord] = field(default_factory=list)
    duration_s: float = 0.0


@dataclass
class PipelineResult:
    """Complete result of an ontology matching run across all pipeline stages."""
    experiment_id: str
    validation_enabled: bool
    reciprocal_merger_enabled: bool
    final_predictions: Set[Tuple[str, str]]
    source_to_target: DirectionalMatchResult
    target_to_source: DirectionalMatchResult
    merger_details: Optional[Dict[str, Any]] = None
    total_duration_s: float = 0.0
    total_validation_calls: int = 0
    total_bypasses: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0


class MatchingAgent:
    """
    Coordinates RRF ranking, matching validation, and reciprocal merging
    with configurable ablation toggles.
    
    Reproduces om_database_matching.py end-to-end pipeline.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        validator: Optional[MatchingValidator] = None,
        merger: Optional[ReciprocalMerger] = None,
        llm: Optional[BaseChatModel] = None,
        context: str = config.context,
        similarity_threshold: float = config.similarity_threshold,
        top_k: int = config.top_k,
        num_matches: int = config.num_matches,
        rrf_k: int = 0,
    ):
        self.db = db_manager or DatabaseManager()
        self.validator = validator or MatchingValidator(llm=llm, context=context)
        self.merger = merger or ReciprocalMerger()
        self.context = context
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.num_matches = num_matches
        self.rrf_k = rrf_k
        self.strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

    def retrieve_entity_rankings(self, entity_id: str) -> List[List[str]]:
        """
        Retrieves raw top_k candidate lists from each of the three vector tables.
        Reproduces find_all_matching_candidate() in om_database_matching.py.
        """
        rankings = []
        for strat in self.strategies:
            cands = self.db.query_strategy(
                entity_id=entity_id,
                table_name=strat,
                similarity_threshold=self.similarity_threshold,
                num_matches=self.num_matches,
                top_k=self.top_k,
            )
            valid_cands = [c for c in cands if c != config.null_value_matching]
            if valid_cands:
                rankings.append(valid_cands)
        return rankings

    def match_entity(
        self,
        query_entity_id: str,
        validate: bool = True,
        direction: Optional[str] = None,
    ) -> Tuple[List[str], List[ValidationRecord]]:
        """
        Generates candidate matches for a single entity.
        
        1. Fuses three-strategy rankings using RRF (k=0).
        2. If validate == False:
           - Takes all candidates in the top score group (predict_entity_list[0]).
        3. If validate == True:
           - Iterates score groups in predict_entity_list[:top_k].
           - Checks exact-name bypass first.
           - Prompts validator LLM if not bypassed.
           - Breaks at the first score group yielding accepted matches.
        """
        rankings = self.retrieve_entity_rankings(query_entity_id)
        if not rankings:
            return [], []

        fused_scores_and_groups = reciprocal_rank_fusion(
            *rankings,
            k=self.rrf_k,
            exclude_items=[config.null_value_matching],
        )
        if not fused_scores_and_groups:
            return [], []

        matched_entity_ids: List[str] = []
        validation_records: List[ValidationRecord] = []

        query_uri = self.db.find_entity_uri(query_entity_id) or ""
        query_name = uri_to_name(query_uri)

        if not validate:
            # Without validation: select all entities in the first score group
            _, top_group_entities = fused_scores_and_groups[0]
            matched_entity_ids = list(top_group_entities)
            return matched_entity_ids, []

        # With validation: evaluate candidates group-by-group up to top_k
        for score, cand_ids in fused_scores_and_groups[: self.top_k]:
            accepted_in_group: List[str] = []
            for cand_id in cand_ids:
                cand_uri = self.db.find_entity_uri(cand_id) or ""
                cand_name = uri_to_name(cand_uri)

                rec = self.validator.validate_candidate_pair(
                    source_uri=query_uri,
                    target_uri=cand_uri,
                    source_name=query_name,
                    target_name=cand_name,
                    context=self.context,
                    direction=direction,
                )
                validation_records.append(rec)

                if rec.decision == "yes":
                    accepted_in_group.append(cand_id)

            if accepted_in_group:
                matched_entity_ids.extend(accepted_in_group)
                # Break at the first score group with accepted candidates
                break

        return matched_entity_ids, validation_records

    def run_directional_matching(
        self,
        source_or_target: str = "Source",
        validate: bool = True,
    ) -> DirectionalMatchResult:
        """
        Runs candidate retrieval and validation for all entities in a given direction.
        - If source_or_target == 'Source': generates pairs (Source_URI, Target_URI).
        - If source_or_target == 'Target': generates pairs (Source_URI, Target_URI) (normalized).
        """
        t0 = time.perf_counter()
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT entity_id, entity_uri FROM ontology_matching
                    WHERE source_or_target = %s
                    ORDER BY entity_id ASC;
                    """,
                    (source_or_target,),
                )
                rows = cur.fetchall()

        all_pairs: Set[Tuple[str, str]] = set()
        all_records: List[ValidationRecord] = []
        matched_queries = 0
        direction_label = "Source->Target" if source_or_target == "Source" else "Target->Source"

        for eid, e_uri in rows:
            cand_ids, records = self.match_entity(eid, validate=validate, direction=direction_label)
            all_records.extend(records)

            if cand_ids:
                matched_queries += 1
                for cid in cand_ids:
                    cand_uri = self.db.find_entity_uri(cid)
                    if cand_uri:
                        if source_or_target == "Source":
                            all_pairs.add((e_uri, cand_uri))
                        else:
                            # Normalize Target->Source to canonical (Source_URI, Target_URI)
                            all_pairs.add((cand_uri, e_uri))

        duration_s = time.perf_counter() - t0
        direction_label = "Source->Target" if source_or_target == "Source" else "Target->Source"

        return DirectionalMatchResult(
            direction=direction_label,
            query_entity_count=len(rows),
            matched_entity_count=matched_queries,
            predicted_pairs=all_pairs,
            validation_records=all_records,
            duration_s=duration_s,
        )

    def run_pipeline(
        self,
        experiment_id: str = "E1",
        validate: bool = True,
        reciprocal_merger: bool = True,
    ) -> PipelineResult:
        """
        Executes complete end-to-end matching pipeline across both directions.
        Supports ablation experiments by toggling validate and reciprocal_merger.
        """
        t_start = time.perf_counter()

        # 1. Source -> Target matching
        s2t_res = self.run_directional_matching(source_or_target="Source", validate=validate)

        # 2. Target -> Source matching
        t2s_res = self.run_directional_matching(source_or_target="Target", validate=validate)

        # 3. Reciprocal merger
        if reciprocal_merger:
            merger_details = self.merger.analyze_merger(
                s2t_res.predicted_pairs,
                t2s_res.predicted_pairs,
                target_to_source_is_reversed=False,  # Already normalized to (Source, Target)
            )
            final_predictions = set(merger_details["merged_pairs"])
        else:
            # Without reciprocal merger, use Source -> Target predictions
            merger_details = None
            final_predictions = set(s2t_res.predicted_pairs)

        total_duration = time.perf_counter() - t_start

        all_records = s2t_res.validation_records + t2s_res.validation_records
        bypasses = sum(1 for r in all_records if r.bypassed)
        llm_calls = sum(1 for r in all_records if not r.bypassed)
        p_tokens = sum(r.prompt_tokens for r in all_records)
        c_tokens = sum(r.completion_tokens for r in all_records)

        return PipelineResult(
            experiment_id=experiment_id,
            validation_enabled=validate,
            reciprocal_merger_enabled=reciprocal_merger,
            final_predictions=final_predictions,
            source_to_target=s2t_res,
            target_to_source=t2s_res,
            merger_details=merger_details,
            total_duration_s=total_duration,
            total_validation_calls=llm_calls,
            total_bypasses=bypasses,
            total_prompt_tokens=p_tokens,
            total_completion_tokens=c_tokens,
        )
