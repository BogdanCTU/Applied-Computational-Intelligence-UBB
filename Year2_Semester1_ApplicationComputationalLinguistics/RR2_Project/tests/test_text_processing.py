"""Unit tests verifying syntactic normalization parity with original Agent-OM."""

import pytest
from src.utils.text_processing import (
    cleaning,
    change_to_snake_case,
    repair_acronyms,
    uri_to_name,
    uri_to_prefix_name,
    change_british_to_american,
    change_phrase_british_to_american,
)


class TestTextProcessing:
    """Test suite for syntactic text processing and normalization."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("ProgramCommitteeMember", "program committee member"),
            ("Chair_PC", "chair pc"),
            ("writtenBy", "written by"),
            ("siteURL", "site url"),
            ("colour", "color"),
            ("behaviour", "behavior"),
            ("hasCo-author", "hasco author"),
            ("hasEmail", "has email"),
            ("Al", "al"),
            ("paperID", "paper id"),
            ("Reviewer_1", "reviewer 1"),
            ("HTTPClient", "http client"),
            ("URL", "url"),
            ("Person", "person"),
            ("Administrator", "administrator"),
            ("SubjectArea", "subject area"),
            ("PaperFullVersion", "paper full version"),
        ],
    )
    def test_cleaning_cases(self, input_name, expected):
        """Verify cleaning produces exact expected strings."""
        assert cleaning(input_name) == expected

    def test_acronym_repair(self):
        """Verify that single letter split sequences are reassembled into acronyms."""
        assert repair_acronyms("U R L") == "URL"
        assert repair_acronyms("site U R L") == "site URL"
        assert repair_acronyms("Chair P C") == "Chair PC"
        assert repair_acronyms("H T T P Client") == "HTTP Client"

    def test_camel_to_snake_case(self):
        """Verify camelCase / PascalCase splitting."""
        assert change_to_snake_case("Author") == "Author"
        assert change_to_snake_case("hasAuthor") == "has Author"
        assert change_to_snake_case("programCommitteeMember") == "program Committee Member"
        assert change_to_snake_case("PaperFullVersion") == "Paper Full Version"

    def test_british_to_american(self):
        """Verify British spelling conversion via breame."""
        assert change_british_to_american("colour") == "color"
        assert change_british_to_american("programme") == "program"
        assert change_phrase_british_to_american("favourite colour programme") == "favorite color program"

    def test_uri_to_name(self):
        """Verify URI extraction matching '#' and '/' formats."""
        assert uri_to_name("http://cmt#Author") == "Author"
        assert uri_to_name("http://confOf/Member") == "Member"
        assert uri_to_name("http://cmt#hasAuthor") == "hasAuthor"
        assert uri_to_prefix_name("http://cmt#Author", "Source") == "Source:Author"

