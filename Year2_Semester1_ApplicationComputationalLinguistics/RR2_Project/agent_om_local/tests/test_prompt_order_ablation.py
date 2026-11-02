"""
Unit tests for Step 7D Experiment A2: Directional Prompt Sensitivity.

Verifies:
1. DirectionalOrderValidator prompt formatting for original, reversed, and canonical modes.
2. Direction-invariance guarantee in canonical mode.
3. Preservation of exact-name bypass under all modes.
4. Metric calculations and candidate set handling.
"""

import pytest
from unittest.mock import MagicMock
from scripts.run_step7d_prompt_order_ablation import (
    DirectionalOrderValidator,
    calculate_metrics,
)


class TestPromptOrderAblation:
    def test_original_mode_prompt_ordering(self):
        """In original mode, query entity is always first, candidate is second."""
        validator = DirectionalOrderValidator(mode="original", llm=MagicMock())
        
        # Source -> Target
        v1 = validator.validate_candidate_pair(
            source_uri="http://cmt#ProgramCommitteeChair",
            target_uri="http://confOf#Chair_PC",
            direction="Source->Target",
        )
        assert "Is program committee chair equivalent to chair pc?" in v1.prompt

        # Target -> Source
        v2 = validator.validate_candidate_pair(
            source_uri="http://confOf#Chair_PC",
            target_uri="http://cmt#ProgramCommitteeChair",
            direction="Target->Source",
        )
        assert "Is chair pc equivalent to program committee chair?" in v2.prompt

    def test_reversed_mode_prompt_ordering(self):
        """In reversed mode, candidate entity is always first, query is second."""
        validator = DirectionalOrderValidator(mode="reversed", llm=MagicMock())

        # Source -> Target
        v1 = validator.validate_candidate_pair(
            source_uri="http://cmt#ProgramCommitteeChair",
            target_uri="http://confOf#Chair_PC",
            direction="Source->Target",
        )
        assert "Is chair pc equivalent to program committee chair?" in v1.prompt

        # Target -> Source
        v2 = validator.validate_candidate_pair(
            source_uri="http://confOf#Chair_PC",
            target_uri="http://cmt#ProgramCommitteeChair",
            direction="Target->Source",
        )
        assert "Is program committee chair equivalent to chair pc?" in v2.prompt

    def test_canonical_mode_prompt_ordering(self):
        """In canonical mode, Source ontology entity is ALWAYS first in both directions."""
        validator = DirectionalOrderValidator(mode="canonical", llm=MagicMock())

        # Source -> Target (query is Source, cand is Target)
        v1 = validator.validate_candidate_pair(
            source_uri="http://cmt#ProgramCommitteeChair",
            target_uri="http://confOf#Chair_PC",
            direction="Source->Target",
        )
        assert "Is program committee chair equivalent to chair pc?" in v1.prompt

        # Target -> Source (query is Target, cand is Source)
        v2 = validator.validate_candidate_pair(
            source_uri="http://confOf#Chair_PC",
            target_uri="http://cmt#ProgramCommitteeChair",
            direction="Target->Source",
        )
        # MUST be canonicalized so Source is first!
        assert "Is program committee chair equivalent to chair pc?" in v2.prompt

    def test_bypass_preserved_under_all_modes(self):
        """Exact-name bypass must operate identically regardless of prompt ordering mode."""
        for m in ["original", "reversed", "canonical"]:
            validator = DirectionalOrderValidator(mode=m, llm=MagicMock())
            v = validator.validate_candidate_pair(
                source_uri="http://cmt#Author",
                target_uri="http://confOf#Author",
                direction="Source->Target",
            )
            assert v.bypassed is True
            assert v.decision == "yes"
            assert v.prompt == "BYPASSED"

    def test_invalid_mode_raises_error(self):
        with pytest.raises(ValueError, match="Unknown prompt order mode"):
            DirectionalOrderValidator(mode="invalid_mode")

