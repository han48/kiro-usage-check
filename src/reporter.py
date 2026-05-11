"""Summary Reporter module for Kiro Account Scraper.

Provides ScrapingResult dataclass and SummaryReporter class for tracking
and displaying scraping progress and final summary.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapingResult:
    """Represents the result of scraping a single profile."""

    profile: str
    success: bool
    error: Optional[str] = None


class SummaryReporter:
    """Tracks scraping results and displays progress and summary information."""

    def __init__(self):
        self.results: list[ScrapingResult] = []

    def add_result(self, result: ScrapingResult) -> None:
        """Record a scraping result."""
        self.results.append(result)

    def print_progress(self, current: int, total: int, profile: str) -> None:
        """Print current progress."""
        print(f"[{current}/{total}] Processing: {profile}")

    def print_summary(self) -> None:
        """Print final summary with totals."""
        total = len(self.results)
        successes = sum(1 for r in self.results if r.success)
        failures = total - successes

        print("\n--- Scraping Summary ---")
        print(f"Total profiles processed: {total}")
        print(f"Successful: {successes}")
        print(f"Failed: {failures}")

        if failures > 0:
            print("\nFailed profiles:")
            for r in self.results:
                if not r.success:
                    error_msg = f" - {r.error}" if r.error else ""
                    print(f"  - {r.profile}{error_msg}")
