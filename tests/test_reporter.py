"""Unit and property-based tests for SummaryReporter."""

import pytest

from src.reporter import ScrapingResult, SummaryReporter


class TestScrapingResult:
    """Unit tests for ScrapingResult dataclass."""

    def test_success_result(self):
        """A successful result has success=True and no error."""
        result = ScrapingResult(profile="/path/to/profile", success=True)
        assert result.profile == "/path/to/profile"
        assert result.success is True
        assert result.error is None

    def test_failure_result_with_error(self):
        """A failed result has success=False and an error message."""
        result = ScrapingResult(
            profile="/path/to/profile", success=False, error="Timeout"
        )
        assert result.profile == "/path/to/profile"
        assert result.success is False
        assert result.error == "Timeout"

    def test_failure_result_without_error(self):
        """A failed result can have no error message."""
        result = ScrapingResult(profile="/path/to/profile", success=False)
        assert result.success is False
        assert result.error is None


class TestSummaryReporterUnit:
    """Unit tests for SummaryReporter."""

    def test_initial_state_empty(self):
        """Reporter starts with an empty results list."""
        reporter = SummaryReporter()
        assert reporter.results == []

    def test_add_result(self):
        """add_result appends to the results list."""
        reporter = SummaryReporter()
        result = ScrapingResult(profile="profile1", success=True)
        reporter.add_result(result)
        assert len(reporter.results) == 1
        assert reporter.results[0] is result

    def test_add_multiple_results(self):
        """Multiple results are stored in order."""
        reporter = SummaryReporter()
        r1 = ScrapingResult(profile="p1", success=True)
        r2 = ScrapingResult(profile="p2", success=False, error="Error")
        r3 = ScrapingResult(profile="p3", success=True)
        reporter.add_result(r1)
        reporter.add_result(r2)
        reporter.add_result(r3)
        assert reporter.results == [r1, r2, r3]

    def test_print_progress(self, capsys):
        """print_progress outputs the current profile and progress."""
        reporter = SummaryReporter()
        reporter.print_progress(2, 5, "/home/user/Profile 2")
        captured = capsys.readouterr()
        assert "[2/5]" in captured.out
        assert "Processing:" in captured.out
        assert "/home/user/Profile 2" in captured.out

    def test_print_summary_all_success(self, capsys):
        """Summary shows correct totals when all profiles succeed."""
        reporter = SummaryReporter()
        reporter.add_result(ScrapingResult(profile="p1", success=True))
        reporter.add_result(ScrapingResult(profile="p2", success=True))
        reporter.add_result(ScrapingResult(profile="p3", success=True))
        reporter.print_summary()
        captured = capsys.readouterr()
        assert "Total profiles processed: 3" in captured.out
        assert "Successful: 3" in captured.out
        assert "Failed: 0" in captured.out
        assert "Failed profiles:" not in captured.out

    def test_print_summary_mixed_results(self, capsys):
        """Summary shows correct totals with mixed success/failure."""
        reporter = SummaryReporter()
        reporter.add_result(ScrapingResult(profile="p1", success=True))
        reporter.add_result(
            ScrapingResult(profile="p2", success=False, error="Timeout")
        )
        reporter.add_result(ScrapingResult(profile="p3", success=False))
        reporter.print_summary()
        captured = capsys.readouterr()
        assert "Total profiles processed: 3" in captured.out
        assert "Successful: 1" in captured.out
        assert "Failed: 2" in captured.out
        assert "Failed profiles:" in captured.out
        assert "p2 - Timeout" in captured.out
        assert "p3" in captured.out

    def test_print_summary_all_failures(self, capsys):
        """Summary shows correct totals when all profiles fail."""
        reporter = SummaryReporter()
        reporter.add_result(
            ScrapingResult(profile="p1", success=False, error="Error 1")
        )
        reporter.add_result(
            ScrapingResult(profile="p2", success=False, error="Error 2")
        )
        reporter.print_summary()
        captured = capsys.readouterr()
        assert "Total profiles processed: 2" in captured.out
        assert "Successful: 0" in captured.out
        assert "Failed: 2" in captured.out

    def test_print_summary_empty_results(self, capsys):
        """Summary handles empty results list."""
        reporter = SummaryReporter()
        reporter.print_summary()
        captured = capsys.readouterr()
        assert "Total profiles processed: 0" in captured.out
        assert "Successful: 0" in captured.out
        assert "Failed: 0" in captured.out


# --- Property-Based Tests ---

from hypothesis import given, settings
from hypothesis import strategies as st


# Strategy for generating ScrapingResult objects
scraping_result_strategy = st.builds(
    ScrapingResult,
    profile=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=100,
    ),
    success=st.booleans(),
    error=st.one_of(
        st.none(),
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=50,
        ),
    ),
)


@given(results=st.lists(scraping_result_strategy, min_size=0, max_size=50))
@settings(max_examples=200)
def test_property_summary_counts_accuracy(results):
    """
    Feature: kiro-account-scraper, Property 7: Summary counts accuracy

    **Validates: Requirements 6.2**

    For any list of ScrapingResult objects (mix of successes and failures),
    the summary reporter SHALL report totals where: total = len(results),
    successes = count where success=True, failures = count where success=False,
    and total = successes + failures.
    """
    reporter = SummaryReporter()
    for result in results:
        reporter.add_result(result)

    total = len(reporter.results)
    successes = sum(1 for r in reporter.results if r.success)
    failures = sum(1 for r in reporter.results if not r.success)

    # Property: total equals length of results
    assert total == len(results)

    # Property: successes count matches
    assert successes == sum(1 for r in results if r.success)

    # Property: failures count matches
    assert failures == sum(1 for r in results if not r.success)

    # Property: total = successes + failures
    assert total == successes + failures
