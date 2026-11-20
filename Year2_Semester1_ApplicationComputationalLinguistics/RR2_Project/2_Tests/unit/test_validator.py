"""Unit tests for MatchingValidator and name bypass logic."""

from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage

from src.matching.validator import MatchingValidator, ValidationRecord


class TestMatchingValidator:
    """Test suite for MatchingValidator."""

    def test_extract_yes_no(self):
        """Verify regex extraction of yes/no decisions."""
        assert MatchingValidator.extract_yes_no("Yes, they are equivalent.") == "yes"
        assert MatchingValidator.extract_yes_no("YES") == "yes"
        assert MatchingValidator.extract_yes_no("No, an author is not a conference.") == "no"
        assert MatchingValidator.extract_yes_no("NO.") == "no"
        assert MatchingValidator.extract_yes_no("Answer: yes.") == "yes"
        assert MatchingValidator.extract_yes_no("They might be related.") is None
        assert MatchingValidator.extract_yes_no("") is None

    def test_check_name_bypass_identical_strings(self):
        """Verify exact-name bypass on identical cleaned names."""
        is_bypass, clean_a, clean_b = MatchingValidator.check_name_bypass("Author", "author")
        assert is_bypass is True
        assert clean_a == "author"
        assert clean_b == "author"

        is_bypass, clean_a, clean_b = MatchingValidator.check_name_bypass("Conference", "Conference")
        assert is_bypass is True

    def test_check_name_bypass_acronyms_and_spelling(self):
        """Verify bypass handles acronym repair and British/American spelling."""
        # breame normalizes colour to color
        is_bypass, clean_a, clean_b = MatchingValidator.check_name_bypass("colour", "color")
        assert is_bypass is True
        assert clean_a == "color"
        assert clean_b == "color"

        # Acronyms repair
        is_bypass, clean_a, clean_b = MatchingValidator.check_name_bypass("siteURL", "site url")
        assert is_bypass is True

    def test_check_name_bypass_distinct_names(self):
        """Verify non-identical names are not bypassed."""
        is_bypass, clean_a, clean_b = MatchingValidator.check_name_bypass("ProgramCommitteeChair", "Chair_PC")
        assert is_bypass is False
        assert clean_a == "program committee chair"
        assert clean_b == "chair pc"

        is_bypass, _, _ = MatchingValidator.check_name_bypass("Paper", "Contribution")
        assert is_bypass is False

    def test_validate_candidate_pair_bypass_path(self):
        """Verify bypassed candidates return yes immediately without LLM invocation."""
        mock_llm = MagicMock()
        validator = MatchingValidator(llm=mock_llm, context="conference")

        record = validator.validate_candidate_pair(
            source_uri="http://cmt#Author",
            target_uri="http://confOf#Author",
            source_name="Author",
            target_name="Author",
        )
        assert record.bypassed is True
        assert record.decision == "yes"
        assert record.duration_ms == 0.0
        assert not mock_llm.invoke.called

    def test_validate_candidate_pair_llm_yes(self):
        """Verify non-bypassed candidate evaluated with yes."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(
            content="Yes, in the context of an academic conference, Chair_PC is equivalent to ProgramCommitteeChair."
        )
        validator = MatchingValidator(llm=mock_llm, context="conference")

        record = validator.validate_candidate_pair(
            source_uri="http://cmt#ProgramCommitteeChair",
            target_uri="http://confOf#Chair_PC",
            source_name="ProgramCommitteeChair",
            target_name="Chair_PC",
        )
        assert record.bypassed is False
        assert record.decision == "yes"
        assert "Question: Is program committee chair equivalent to chair pc?" in record.prompt
        assert mock_llm.invoke.called

    def test_validate_candidate_pair_llm_no(self):
        """Verify non-bypassed candidate evaluated with no."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(
            content="No, a paper is a written work while a person is an individual."
        )
        validator = MatchingValidator(llm=mock_llm, context="conference")

        record = validator.validate_candidate_pair(
            source_uri="http://cmt#Paper",
            target_uri="http://confOf#Person",
            source_name="Paper",
            target_name="Person",
        )
        assert record.bypassed is False
        assert record.decision == "no"
        assert mock_llm.invoke.called

    def test_validate_candidate_pair_error_handling(self):
        """Verify inference exceptions are caught and recorded as error."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("Ollama connection timed out")
        validator = MatchingValidator(llm=mock_llm, context="conference")

        record = validator.validate_candidate_pair(
            source_uri="http://cmt#Review",
            target_uri="http://confOf#Paper",
        )
        assert record.bypassed is False
        assert record.decision == "error"
        assert "Ollama connection timed out" in record.error_message

