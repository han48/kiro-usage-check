"""Unit and property-based tests for ProfileReader."""

import os
import tempfile

import pytest

from src.profile_reader import ProfileReader


class TestProfileReaderUnit:
    """Unit tests for ProfileReader."""

    def test_file_not_found_raises_error(self):
        """FileNotFoundError is raised when the profile file does not exist."""
        reader = ProfileReader("/nonexistent/path/profiles.txt")
        with pytest.raises(FileNotFoundError, match="Profile list file not found"):
            reader.read_profiles()

    def test_empty_file_returns_empty_list(self, tmp_path):
        """An empty file returns an empty list."""
        file = tmp_path / "profiles.txt"
        file.write_text("")
        reader = ProfileReader(str(file))
        assert reader.read_profiles() == []

    def test_comments_only_file_returns_empty_list(self, tmp_path):
        """A file with only comments and empty lines returns an empty list."""
        content = "# This is a comment\n\n# Another comment\n   \n"
        file = tmp_path / "profiles.txt"
        file.write_text(content)
        reader = ProfileReader(str(file))
        assert reader.read_profiles() == []

    def test_valid_entries_returned(self, tmp_path):
        """Valid profile paths are returned, comments and blanks skipped."""
        content = (
            "# Comment\n"
            "/home/user/.config/google-chrome/Profile 1\n"
            "\n"
            "# Another comment\n"
            "/home/user/.config/google-chrome/Profile 2\n"
            "   \n"
            "C:\\Users\\user\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 3\n"
        )
        file = tmp_path / "profiles.txt"
        file.write_text(content)
        reader = ProfileReader(str(file))
        result = reader.read_profiles()
        assert result == [
            "/home/user/.config/google-chrome/Profile 1",
            "/home/user/.config/google-chrome/Profile 2",
            "C:\\Users\\user\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 3",
        ]

    def test_whitespace_stripped_from_entries(self, tmp_path):
        """Leading and trailing whitespace is stripped from valid entries."""
        content = "  /home/user/profile1  \n\t/home/user/profile2\t\n"
        file = tmp_path / "profiles.txt"
        file.write_text(content)
        reader = ProfileReader(str(file))
        result = reader.read_profiles()
        assert result == ["/home/user/profile1", "/home/user/profile2"]

    def test_line_starting_with_hash_after_spaces_is_comment(self, tmp_path):
        """Lines that start with '#' after stripping are treated as comments."""
        content = "  # indented comment\n/valid/path\n"
        file = tmp_path / "profiles.txt"
        file.write_text(content)
        reader = ProfileReader(str(file))
        result = reader.read_profiles()
        assert result == ["/valid/path"]


# --- Property-Based Tests ---

from hypothesis import given, settings
from hypothesis import strategies as st


def make_line_strategy():
    """Strategy that generates lines of three types: empty, comment, or valid path."""
    # Exclude newlines, carriage returns, and surrogate characters (can't be encoded to UTF-8)
    safe_chars = st.characters(
        blacklist_characters="\n\r",
        blacklist_categories=("Cs",),  # Exclude surrogates
    )
    empty_line = st.just("")
    whitespace_line = st.text(
        alphabet=st.sampled_from([" ", "\t"]), min_size=0, max_size=5
    )
    comment_line = st.text(
        alphabet=safe_chars,
        min_size=0,
        max_size=50,
    ).map(lambda s: "#" + s)
    valid_line = st.text(
        alphabet=st.characters(
            blacklist_characters="\n\r#",
            blacklist_categories=("Cs",),
        ),
        min_size=1,
        max_size=80,
    ).filter(lambda s: s.strip() != "" and not s.strip().startswith("#"))
    return st.one_of(empty_line, whitespace_line, comment_line, valid_line)


@given(lines=st.lists(make_line_strategy(), min_size=0, max_size=50))
@settings(max_examples=200)
def test_property_profile_filtering_preserves_valid_entries(lines, tmp_path_factory):
    """
    Feature: kiro-account-scraper, Property 1: Profile filtering preserves only valid entries

    **Validates: Requirements 1.1, 1.2**

    For any text file content consisting of arbitrary lines (empty lines, lines
    starting with "#", and non-empty/non-comment lines), the profile reader SHALL
    return exactly the lines that are non-empty and do not start with "#", in their
    original order.
    """
    # Write lines to a temp file
    tmp_dir = tmp_path_factory.mktemp("profiles")
    file_path = tmp_dir / "profiles.txt"
    file_content = "\n".join(lines)
    file_path.write_text(file_content, encoding="utf-8")

    # Read profiles using ProfileReader
    reader = ProfileReader(str(file_path))
    result = reader.read_profiles()

    # Compute expected: non-empty, non-comment lines after stripping
    expected = []
    for line in lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        expected.append(stripped)

    assert result == expected
