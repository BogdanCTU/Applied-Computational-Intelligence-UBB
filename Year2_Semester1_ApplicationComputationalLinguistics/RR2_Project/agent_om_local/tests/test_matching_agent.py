"""
Unit tests for MatchingAgent.
Uses mocks to verify candidate retrieval orchestration, RRF score group break logic,
exact-name bypass integration, and ablation flag toggling (E1, E5, E6, E7).
"""

from unittest.mock import MagicMock
import pytest

from src.agents.matching_agent import MatchingAgent, DirectionalMatchResult, PipelineResult
from src.matching.validator import ValidationRecord


class TestMatchingAgent:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        # Mock URI lookups
        uri_map = {
            "s1": "http://cmt#Author",
            "s2": "http://cmt#Reviewer",
            "t1": "http://confOf#Author",
            "t2": "http://confOf#Reviewer",
            "t3": "http://confOf#Participant",
        }
        db.find_entity_uri.side_effect = lambda eid: uri_map.get(eid, f"http://onto#{eid}")
        return db

    @pytest.fixture
    def mock_validator(self):
        validator = MagicMock()
        return validator

    @pytest.fixture
    def mock_merger(self):
        from src.matching.merger import ReciprocalMerger
        return ReciprocalMerger()

    def test_match_entity_no_validation(self, mock_db, mock_validator, mock_merger):
        """Ablation E5: validate=False returns all candidates in top score group."""
        agent = MatchingAgent(db_manager=mock_db, validator=mock_validator, merger=mock_merger)

        # Mock retrieval returning rankings across 3 strategies
        # Candidate t1 is rank 1 in strategy 1 and 2, t2 is rank 2
        agent.retrieve_entity_rankings = MagicMock(return_value=[
            ["t1", "t2"],
            ["t1", "t3"],
        ])

        cands, records = agent.match_entity("s1", validate=False)
        assert cands == ["t1"]
        assert len(records) == 0
        mock_validator.validate_candidate_pair.assert_not_called()

    def test_match_entity_score_group_break(self, mock_db, mock_validator, mock_merger):
        """When first score group produces an accepted candidate, second group is not evaluated."""
        agent = MatchingAgent(db_manager=mock_db, validator=mock_validator, merger=mock_merger)

        # 2 score groups: top group has t1, second group has t2
        agent.retrieve_entity_rankings = MagicMock(return_value=[
            ["t1", "t2"],
        ])

        mock_validator.validate_candidate_pair.side_effect = [
            ValidationRecord(
                source_uri="http://cmt#Author",
                target_uri="http://confOf#Author",
                source_name="Author",
                target_name="Author",
                cleaned_source_name="author",
                cleaned_target_name="author",
                decision="yes",
                raw_response="Yes",
                bypassed=True,
            )
        ]

        cands, records = agent.match_entity("s1", validate=True)
        assert cands == ["t1"]
        assert len(records) == 1
        assert records[0].decision == "yes"
        # t2 was never validated because loop broke after group 1
        assert mock_validator.validate_candidate_pair.call_count == 1

    def test_match_entity_fallback_to_second_score_group(self, mock_db, mock_validator, mock_merger):
        """When first score group is rejected, evaluation continues to second score group."""
        agent = MatchingAgent(db_manager=mock_db, validator=mock_validator, merger=mock_merger)

        agent.retrieve_entity_rankings = MagicMock(return_value=[
            ["t1", "t2"],
        ])

        mock_validator.validate_candidate_pair.side_effect = [
            # Group 1 (t1) rejected
            ValidationRecord(
                source_uri="http://cmt#Author",
                target_uri="http://confOf#Author",
                source_name="Author",
                target_name="Author",
                cleaned_source_name="author",
                cleaned_target_name="author",
                decision="no",
                raw_response="No",
                bypassed=False,
            ),
            # Group 2 (t2) accepted
            ValidationRecord(
                source_uri="http://cmt#Author",
                target_uri="http://confOf#Reviewer",
                source_name="Author",
                target_name="Reviewer",
                cleaned_source_name="author",
                cleaned_target_name="reviewer",
                decision="yes",
                raw_response="Yes",
                bypassed=False,
            ),
        ]

        cands, records = agent.match_entity("s1", validate=True)
        assert cands == ["t2"]
        assert len(records) == 2
        assert mock_validator.validate_candidate_pair.call_count == 2

    def test_run_pipeline_e1_and_e6_ablation(self, mock_db, mock_validator, mock_merger):
        """Tests that run_pipeline accurately toggles merger and validation."""
        agent = MatchingAgent(db_manager=mock_db, validator=mock_validator, merger=mock_merger)

        # Mock directional results
        s2t_res = DirectionalMatchResult(
            direction="Source->Target",
            query_entity_count=2,
            matched_entity_count=2,
            predicted_pairs={("http://cmt#Author", "http://confOf#Author"), ("http://cmt#Paper", "http://confOf#Contribution")},
            validation_records=[],
            duration_s=0.1,
        )
        t2s_res = DirectionalMatchResult(
            direction="Target->Source",
            query_entity_count=2,
            matched_entity_count=1,
            predicted_pairs={("http://cmt#Author", "http://confOf#Author")},
            validation_records=[],
            duration_s=0.1,
        )

        agent.run_directional_matching = MagicMock(side_effect=[s2t_res, t2s_res])

        # Test E1 (Merger enabled)
        res_e1 = agent.run_pipeline(experiment_id="E1", validate=True, reciprocal_merger=True)
        assert res_e1.reciprocal_merger_enabled is True
        assert res_e1.final_predictions == {("http://cmt#Author", "http://confOf#Author")}

        # Test E6 (Merger disabled -> returns S->T directly)
        agent.run_directional_matching = MagicMock(side_effect=[s2t_res, t2s_res])
        res_e6 = agent.run_pipeline(experiment_id="E6", validate=True, reciprocal_merger=False)
        assert res_e6.reciprocal_merger_enabled is False
        assert res_e6.final_predictions == {
            ("http://cmt#Author", "http://confOf#Author"),
            ("http://cmt#Paper", "http://confOf#Contribution"),
        }
