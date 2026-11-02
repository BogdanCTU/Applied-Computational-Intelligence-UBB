"""Unit and integration tests for RetrievalAgent and DatabaseManager."""

from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest

from src.db.database_manager import DatabaseManager
from src.agents.retrieval_agent import RetrievalAgent
from scripts.run_experiments_step6 import ensure_database_populated


class DummyEmbeddings:
    """Mock embeddings service producing deterministic unit vectors."""

    def __init__(self, dim: int = 4):
        self.dim = dim

    def embed_documents(self, texts):
        results = []
        for t in texts:
            # Deterministic vector based on text hash
            val = float(abs(hash(t)) % 100) / 100.0
            vec = np.zeros(self.dim, dtype=np.float32)
            vec[0] = val
            vec[1] = 1.0 - val
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())
        return results

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class TestRetrievalAgent:
    """Test suite for RetrievalAgent coordination and candidate retrieval."""

    @classmethod
    def teardown_class(cls):
        """Restore full 162 CMT-ConfOf entities after integration tests run."""
        db = DatabaseManager()
        ensure_database_populated(db)

    @pytest.fixture
    def test_df(self):
        """Create sample features DataFrame matching Agent-OM conventions."""
        data = [
            # Source entities
            {
                "entity_uri": "http://cmt#Author",
                "source_or_target": "Source",
                "entity_type": "Class",
                "syntactic_matching": "author",
                "lexical_matching": "A person who submits a paper to the conference.",
                "semantic_matching": "Author is a subclass of ConferenceMember.",
            },
            {
                "entity_uri": "http://cmt#Conference",
                "source_or_target": "Source",
                "entity_type": "Class",
                "syntactic_matching": "conference",
                "lexical_matching": "An academic meeting or event.",
                "semantic_matching": "Conference has participants and papers.",
            },
            # Target entities
            {
                "entity_uri": "http://confOf#Author",
                "source_or_target": "Target",
                "entity_type": "Class",
                "syntactic_matching": "author",
                "lexical_matching": "A person who submits a contribution to the event.",
                "semantic_matching": "Author writes Contribution.",
            },
            {
                "entity_uri": "http://confOf#Conference",
                "source_or_target": "Target",
                "entity_type": "Class",
                "syntactic_matching": "conference",
                "lexical_matching": "A scientific conference gathering.",
                "semantic_matching": "Conference has events and members.",
            },
        ]
        agent = RetrievalAgent()
        df = agent.build_features_dataframe(data[:2], data[2:])
        return df

    def test_build_features_dataframe_formatting(self, test_df):
        """Verify entity_id format: {id}-{source_or_target}-{entity_type}-{name}."""
        assert len(test_df) == 4
        expected_ids = [
            "1-Source-Class-Author",
            "2-Source-Class-Conference",
            "3-Target-Class-Author",
            "4-Target-Class-Conference",
        ]
        assert test_df["entity_id"].tolist() == expected_ids

    def test_database_ingestion_and_vector_query(self, test_df):
        """Verify ingestion into pgvector tables and vector similarity queries."""
        db = DatabaseManager()
        db.init_extensions()

        dim = 4
        emb_service = DummyEmbeddings(dim=dim)
        agent = RetrievalAgent(db_manager=db, embeddings_service=emb_service)

        # Ingest test records
        stats = agent.ingest_features_to_database(test_df, embeddings_service=emb_service, vector_length=dim)
        assert stats["total_entities"] == 4
        assert stats["syntactic_chunks"] == 4

        # Test querying a strategy directly
        matches = db.query_strategy(
            entity_id="1-Source-Class-Author",
            table_name="syntactic_matching",
            similarity_threshold=0.0,  # Lower threshold for dummy embeddings test
            num_matches=10,
            top_k=2,
        )
        assert len(matches) > 0
        # Matching candidate must be from Target and of type Class
        for m in matches:
            assert "Target-Class" in m

    def test_candidate_retrieval_and_rrf_coordination(self, test_df):
        """Verify complete candidate retrieval and ranking fusion for an entity."""
        db = DatabaseManager()
        dim = 4
        emb_service = DummyEmbeddings(dim=dim)
        agent = RetrievalAgent(
            db_manager=db,
            embeddings_service=emb_service,
            similarity_threshold=0.0,
            top_k=3,
            rrf_k=0,
        )

        agent.ingest_features_to_database(test_df, embeddings_service=emb_service, vector_length=dim)

        # Retrieve candidates for 1-Source-Class-Author
        result = agent.retrieve_candidates_for_entity("1-Source-Class-Author")
        assert result["query_entity_id"] == "1-Source-Class-Author"
        assert result["query_entity_uri"] == "http://cmt#Author"
        assert len(result["syntactic_ranking"]) > 0
        assert len(result["lexical_ranking"]) > 0
        assert len(result["semantic_ranking"]) > 0
        assert len(result["fused_ranking"]) > 0
        assert len(result["candidate_uris"]) > 0
        # All returned candidates should be ConfOf URIs
        for cand_uri in result["candidate_uris"]:
            assert "confOf" in cand_uri

    def test_directional_candidates_separation(self, test_df):
        """Verify that Source->Target and Target->Source candidates are kept strictly separate."""
        db = DatabaseManager()
        dim = 4
        emb_service = DummyEmbeddings(dim=dim)
        agent = RetrievalAgent(
            db_manager=db,
            embeddings_service=emb_service,
            similarity_threshold=0.0,
            top_k=2,
        )

        agent.ingest_features_to_database(test_df, embeddings_service=emb_service, vector_length=dim)

        source_results = agent.retrieve_directional_candidates(source_or_target="Source")
        target_results = agent.retrieve_directional_candidates(source_or_target="Target")

        assert len(source_results) == 2  # 2 Source entities
        assert len(target_results) == 2  # 2 Target entities

        # Source queries must produce Target candidates
        for res in source_results:
            assert "Source" in res["query_entity_id"]
            for cand in res["candidate_uris"]:
                assert "confOf" in cand

        # Target queries must produce Source candidates
        for res in target_results:
            assert "Target" in res["query_entity_id"]
            for cand in res["candidate_uris"]:
                assert "cmt" in cand

