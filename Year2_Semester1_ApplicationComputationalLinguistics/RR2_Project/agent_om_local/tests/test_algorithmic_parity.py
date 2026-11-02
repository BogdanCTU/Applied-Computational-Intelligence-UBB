"""Comprehensive Phase 4 algorithmic parity, safety, and mini-ontology integration tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from langchain_core.language_models import FakeListChatModel
from langchain_core.messages import AIMessage

from src.agents.matching_agent import MatchingAgent
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.tool_router import LLMJsonToolRouter
from src.config import VALID_PROFILES, AppConfig
from src.db.database_manager import DatabaseManager
from src.matching.validator import MatchingValidator
from src.ontology.entity_extractor import EntityExtractor
from src.ontology.parser import OntologyGraph, load_ontology
from src.retrieval.lexical_retriever import LexicalRetriever
from src.retrieval.semantic_retriever import SemanticRetriever

TEST_DB_DSN = "postgresql://postgres@127.0.0.1:5432/agent_om_test"
ORIGINAL_CMT_CONFOF_DIR = (
    Path(__file__).resolve().parents[2]
    / "original_repo"
    / "data"
    / "conference"
    / "cmt-confof"
    / "component"
)


class DeterministicHashEmbeddings:
    """Deterministic unit-norm embeddings keyed by text SHA-256."""

    def __init__(self, dim: int = 16):
        self.dim = dim

    def embed_documents(self, texts):
        vecs = []
        for t in texts:
            clean = str(t).strip().lower()
            digest = hashlib.sha256(clean.encode("utf-8")).digest()
            arr = np.frombuffer(digest * ((self.dim // 32) + 1), dtype=np.uint8)[: self.dim].astype(
                np.float32
            )
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            vecs.append(arr.tolist())
        return vecs

    def embed_query(self, text):
        return self.embed_documents([text])[0]


@pytest.fixture
def isolated_test_db():
    db = DatabaseManager(connection_string=TEST_DB_DSN)
    db.ensure_database_exists()
    db.init_extensions()
    return db


class TestPhase4EmptySemanticChunks:
    """4.1 — Verify empty / placeholder semantic text yields 0 chunks and no false 1.0 matches."""

    def test_empty_and_null_placeholder_produce_zero_chunks(self, isolated_test_db):
        df = pd.DataFrame(
            [
                {
                    "entity_id": "1-Source-Class-IsolatedA",
                    "entity_uri": "http://src#IsolatedA",
                    "source_or_target": "Source",
                    "entity_type": "Class",
                    "syntactic_matching": "isolated a",
                    "lexical_matching": "Meaning of A",
                    "semantic_matching": "Information is not available.",
                },
                {
                    "entity_id": "2-Target-Class-IsolatedB",
                    "entity_uri": "http://tgt#IsolatedB",
                    "source_or_target": "Target",
                    "entity_type": "Class",
                    "syntactic_matching": "isolated b",
                    "lexical_matching": "Meaning of B",
                    "semantic_matching": "Information is not available.",
                },
            ]
        )
        emb = DeterministicHashEmbeddings(dim=8)
        isolated_test_db.create_ontology_matching_table(df)
        sem_chunks = isolated_test_db.create_embedding_table(
            "semantic_matching",
            df,
            emb,
            vector_length=8,
            skip_empty_chunks=True,
        )
        assert sem_chunks == 0

        # Querying an entity with 0 semantic chunks must return Entity-Dummy, NOT false 1.0 match
        cands = isolated_test_db.query_strategy(
            "1-Source-Class-IsolatedA",
            "semantic_matching",
            similarity_threshold=0.90,
        )
        assert cands == ["Entity-Dummy"]


class TestPhase4CodeIRILabelResolution:
    """4.2 — Verify o1_is_code and o2_is_code resolve rdfs:label -> skos:prefLabel -> URI in both directions."""

    def test_code_iri_resolution_and_bypass_symmetric(self, isolated_test_db):
        src_ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://ncit.org/#> .
        ex:NCI_C001 a owl:Class ; rdfs:label "Heart" .
        ex:NCI_C002 a owl:Class ; rdfs:label "Cardiac Muscle" .
        ex:NCI_C999 a owl:Class .
        """
        tgt_ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ma: <http://ma.org/#> .
        ma:MA_00072 a owl:Class ; skos:prefLabel "heart" .
        ma:MA_00073 a owl:Class ; skos:prefLabel "Cardiac Muscle" .
        ma:MA_00999 a owl:Class .
        """
        src_ont = OntologyGraph.from_string(src_ttl, format="turtle")
        tgt_ont = OntologyGraph.from_string(tgt_ttl, format="turtle")

        df = pd.DataFrame(
            [
                {
                    "entity_id": "1-Source-Class-Heart",
                    "entity_uri": "http://ncit.org/#NCI_C001",
                    "source_or_target": "Source",
                    "entity_type": "Class",
                    "syntactic_matching": "heart",
                    "lexical_matching": "organ heart",
                    "semantic_matching": "Information is not available.",
                },
                {
                    "entity_id": "2-Source-Class-Cardiac Muscle",
                    "entity_uri": "http://ncit.org/#NCI_C002",
                    "source_or_target": "Source",
                    "entity_type": "Class",
                    "syntactic_matching": "cardiac muscle",
                    "lexical_matching": "heart muscle tissue",
                    "semantic_matching": "Information is not available.",
                },
                {
                    "entity_id": "3-Target-Class-heart",
                    "entity_uri": "http://ma.org/#MA_00072",
                    "source_or_target": "Target",
                    "entity_type": "Class",
                    "syntactic_matching": "heart",
                    "lexical_matching": "organ heart",
                    "semantic_matching": "Information is not available.",
                },
                {
                    "entity_id": "4-Target-Class-Cardiac Muscle",
                    "entity_uri": "http://ma.org/#MA_00073",
                    "source_or_target": "Target",
                    "entity_type": "Class",
                    "syntactic_matching": "cardiac muscle",
                    "lexical_matching": "heart muscle tissue",
                    "semantic_matching": "Information is not available.",
                },
            ]
        )
        emb = DeterministicHashEmbeddings(dim=16)
        isolated_test_db.create_ontology_matching_table(df)
        for tbl in ("syntactic_matching", "lexical_matching", "semantic_matching"):
            isolated_test_db.create_embedding_table(tbl, df, emb, vector_length=16)

        mock_llm = MagicMock()
        validator = MatchingValidator(llm=mock_llm, context="anatomy")
        matcher = MatchingAgent(
            db_manager=isolated_test_db,
            validator=validator,
            source_ontology=src_ont,
            target_ontology=tgt_ont,
            o1_is_code=True,
            o2_is_code=True,
            context="anatomy",
            similarity_threshold=0.90,
        )

        # Fallback check for unlabeled entity
        assert matcher.resolve_entity_display_name("http://ncit.org/#NCI_C999", "Source") == "NCI_C999"

        res = matcher.run_pipeline(experiment_id="code_iri_test", validate=True, reciprocal_merger=True)
        assert res.final_predictions == {
            ("http://ncit.org/#NCI_C001", "http://ma.org/#MA_00072"),
            ("http://ncit.org/#NCI_C002", "http://ma.org/#MA_00073"),
        }
        # Both pairs matched via exact-name bypass on resolved labels in BOTH directions (zero LLM calls)
        assert res.total_bypasses == 4
        assert res.total_validation_calls == 0
        mock_llm.invoke.assert_not_called()


class TestPhase4PropertySortingParity:
    """4.3 — Verify combined alphabetical URI sorting of ObjectProperty and DatatypeProperty."""

    def test_combined_property_uri_order_matches_upstream_cmt_confof(self):
        cmt_ont = load_ontology(ORIGINAL_CMT_CONFOF_DIR / "source.xml")
        extractor = EntityExtractor(combine_properties_sort=True)
        entities, summary = extractor.extract_entities(cmt_ont, "Source")
        assert summary.total_classes == 29
        assert summary.total_properties == 59

        prop_uris = [e.uri for e in entities if e.entity_type.value == "Property"]
        assert prop_uris == sorted(prop_uris)

        # Verify legacy separate sorting differs when combine_properties_sort=False
        entities_sep, _ = extractor.extract_entities(
            cmt_ont, "Source", combine_properties_sort=False
        )
        prop_uris_sep = [e.uri for e in entities_sep if e.entity_type.value == "Property"]
        assert prop_uris_sep != prop_uris


class TestPhase4DimensionsProfilesAndEnv:
    """4.4, 4.5, 4.7, 4.8, 4.10 — Profiles, dimensions, .env loading, and DB protection."""

    def test_llama3_8b_dimension_and_no_silent_768_fallback(self):
        parity_cfg = AppConfig.from_profile("upstream_lite_parity")
        assert parity_cfg.vector_length == 4096
        assert parity_cfg.temperature == 0.0
        assert parity_cfg.seed == 42
        assert parity_cfg.llm_top_k == 1
        assert parity_cfg.top_p == 1.0
        assert parity_cfg.repeat_penalty == 1.0

        unknown_cfg = AppConfig.from_profile(
            "experimental", default_embedding_model="unknown-custom-embedder"
        )
        with pytest.raises(ValueError, match="silent fallback to 768 is prohibited"):
            _ = unknown_cfg.vector_length

    def test_runtime_dimension_mismatch_raises(self, isolated_test_db):
        df = pd.DataFrame(
            [
                {
                    "entity_id": "1-Source-Class-A",
                    "entity_uri": "http://src#A",
                    "source_or_target": "Source",
                    "entity_type": "Class",
                    "syntactic_matching": "a",
                    "lexical_matching": "a",
                    "semantic_matching": "a",
                }
            ]
        )
        isolated_test_db.create_ontology_matching_table(df)
        wrong_emb = DeterministicHashEmbeddings(dim=8)
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            isolated_test_db.create_embedding_table(
                "syntactic_matching", df, wrong_emb, vector_length=4096
            )

    def test_all_four_profiles_and_reference_only_guard(self):
        for p in VALID_PROFILES:
            cfg = AppConfig.from_profile(p)
            assert cfg.profile_name == p

        ref_cfg = AppConfig.from_profile("upstream_product_reference")
        assert ref_cfg.reference_only is True
        assert ref_cfg.vector_length == 1536
        with pytest.raises(PermissionError, match="reference-only"):
            ref_cfg.build_chat_llm()

        adapted_cfg = AppConfig.from_profile("local_adapted")
        chat_llm = adapted_cfg.build_chat_llm()
        assert chat_llm.model == "qwen3.5:9b"
        assert chat_llm.reasoning is False
        assert chat_llm.seed == 42

    def test_env_loading_and_loopback_enforcement(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DB_HOST=127.0.0.1\nDB_PORT=5432\nDB_NAME=agent_om_test\n"
            "DEFAULT_CHAT_MODEL=llama3:8b\nDEFAULT_EMBEDDING_MODEL=llama3:8b\n"
            "SEED=99\nTEMPERATURE=0.0\n",
            encoding="utf-8",
        )
        cfg = AppConfig.from_env(env_file=env_file, environ={})
        assert cfg.db_name == "agent_om_test"
        assert cfg.default_llm == "llama3:8b"
        assert cfg.vector_length == 4096
        assert cfg.seed == 99

        with pytest.raises(ValueError, match="Non-loopback"):
            AppConfig(db_host="192.168.1.50")
        with pytest.raises(ValueError, match="Non-loopback"):
            AppConfig(ollama_host="https://api.openai.com")

    def test_protected_agent_om_local_db_blocks_destructive_writes(self):
        protected_db = DatabaseManager("postgresql://postgres@127.0.0.1:5432/agent_om_local")
        dummy_df = pd.DataFrame([{"entity_id": "1", "entity_uri": "u", "source_or_target": "Source", "entity_type": "Class"}])
        with pytest.raises(PermissionError, match="agent_om_local"):
            protected_db.create_ontology_matching_table(dummy_df)


class TestPhase4PromptsAndToolRouter:
    """4.6, 4.9, 4.11 — Prompt indentation, predicate scope, JSON tool router, and end-to-end mini pipeline."""

    def test_validation_prompt_indentation_and_predicate_scopes(self):
        v_parity = MatchingValidator(llm=MagicMock(), indent_prompt=True)
        p_parity = v_parity.format_prompt("author", "writer", "conference")
        assert "\n                            Context: conference\n" in p_parity
        assert p_parity.endswith("                            ")

        v_clean = MatchingValidator(llm=MagicMock(), indent_prompt=False)
        p_clean = v_clean.format_prompt("author", "writer", "conference")
        assert "\nContext: conference\n" in p_clean

        ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ex: <http://example.org/#> .
        ex:Paper a owl:Class ;
            rdfs:comment "Academic paper." ;
            skos:definition "Formal scholarly work." ;
            skos:broader ex:Work ;
            owl:equivalentClass [ a owl:Restriction ; owl:onProperty ex:writtenBy ; owl:someValuesFrom ex:Author ] .
        ex:Work a owl:Class .
        ex:Author a owl:Class .
        ex:writtenBy a owl:ObjectProperty .
        """
        ont = OntologyGraph.from_string(ttl, format="turtle")
        lex_head = LexicalRetriever(predicate_scope="head")
        lex_v1 = LexicalRetriever(predicate_scope="pvl_v1")
        assert "Formal scholarly work." in lex_head.extract_extra_information("http://example.org/#Paper", ont.graph)
        assert "Formal scholarly work." not in lex_v1.extract_extra_information("http://example.org/#Paper", ont.graph)

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Verbalized.")
        sem_v1 = SemanticRetriever(llm=mock_llm, predicate_scope="pvl_v1")
        ans_v1, meta_v1 = sem_v1.retrieve_semantic_representation("http://example.org/#Paper", ont)
        # In pvl_v1, skos:broader and blank-node closure are both absent
        assert ans_v1 == "Information is not available."
        assert meta_v1["has_complex_bnode"] is False

    def test_end_to_end_mini_pipeline_deterministic_vs_llm_json_router(self, isolated_test_db):
        src_ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix cmt: <http://cmt#> .
        cmt:Author a owl:Class ; rdfs:comment "Writes a conference paper." .
        cmt:PaperFullVersion a owl:Class ; rdfs:subClassOf cmt:Document .
        cmt:Document a owl:Class .
        """
        tgt_ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix confOf: <http://confOf#> .
        confOf:Author a owl:Class ; rdfs:comment "Writes a conference contribution." .
        confOf:Paper a owl:Class ; rdfs:subClassOf confOf:Contribution .
        confOf:Contribution a owl:Class .
        """
        src_ont = OntologyGraph.from_string(src_ttl, format="turtle")
        tgt_ont = OntologyGraph.from_string(tgt_ttl, format="turtle")
        extractor = EntityExtractor()
        src_ents, _ = extractor.extract_entities(src_ont, "Source")
        tgt_ents, _ = extractor.extract_entities(tgt_ont, "Target")

        # Deterministic retrieval
        det_llm = MagicMock()
        det_llm.invoke.return_value = AIMessage(content="Academic conference concept explanation.")
        emb = DeterministicHashEmbeddings(dim=16)
        cfg_det = AppConfig.from_profile(
            "experimental", db_name="agent_om_test", embedding_dim=16, tool_routing_mode="deterministic"
        )
        ret_det = RetrievalAgent(
            db_manager=isolated_test_db, llm=det_llm, embeddings_service=emb, app_config=cfg_det
        )
        s_rec = ret_det.extract_representations_for_entities(src_ents, src_ont)
        t_rec = ret_det.extract_representations_for_entities(tgt_ents, tgt_ont)
        df = ret_det.build_features_dataframe(s_rec, t_rec)
        stats = ret_det.ingest_features_to_database(df, embeddings_service=emb, vector_length=16)
        assert stats["total_entities"] == 6
        # Isolated classes Document and Contribution have incoming subClassOf triples -> 4 semantic entities
        assert stats["semantic_chunks"] == 4

        # Matching in deterministic mode vs llm_json router mode
        val_llm = MagicMock()
        val_llm.invoke.return_value = AIMessage(content="Yes, PaperFullVersion is equivalent to Paper.")
        match_det = MatchingAgent(
            db_manager=isolated_test_db,
            llm=val_llm,
            similarity_threshold=0.0,
            top_k=3,
            app_config=cfg_det,
        )
        res_det = match_det.run_pipeline(experiment_id="mini_det")

        # Now run MatchingAgent with tool_routing_mode='llm_json'
        def router_and_validator_responder(messages_or_prompt):
            if isinstance(messages_or_prompt, list) and messages_or_prompt:
                text = str(messages_or_prompt[-1].content)
            else:
                text = str(messages_or_prompt)
            if text.startswith("Syntactic matching for "):
                eid = text.removeprefix("Syntactic matching for ").strip()
                return AIMessage(content=f'{{"name": "syntactic", "arguments": {{"entity": "{eid}"}}}}')
            if text.startswith("Lexical matching for "):
                eid = text.removeprefix("Lexical matching for ").strip()
                # Exercise tolerant 'tool' alias handling as well
                return AIMessage(content=f'{{"tool": "lexical", "arguments": {{"entity": "{eid}"}}}}')
            if text.startswith("Semantic matching for "):
                eid = text.removeprefix("Semantic matching for ").strip()
                return AIMessage(content=f'{{"name": "semantic", "arguments": {{"entity": "{eid}"}}}}')
            if text.strip() == "Validate matching.":
                return AIMessage(content='{"name": "validate", "arguments": {}}')
            return AIMessage(content="Yes, PaperFullVersion is equivalent to Paper.")

        router_llm = MagicMock()
        router_llm.invoke.side_effect = router_and_validator_responder
        cfg_json = AppConfig.from_profile(
            "experimental", db_name="agent_om_test", embedding_dim=16, tool_routing_mode="llm_json"
        )
        match_json = MatchingAgent(
            db_manager=isolated_test_db,
            llm=router_llm,
            similarity_threshold=0.0,
            top_k=3,
            app_config=cfg_json,
        )
        res_json = match_json.run_pipeline(experiment_id="mini_json")

        assert res_det.final_predictions == res_json.final_predictions
        assert ("http://cmt#Author", "http://confOf#Author") in res_json.final_predictions
        assert res_json.router_calls >= 18  # 6 entities * 3 retrieval router calls + validation router calls
        assert res_json.router_errors == 0
