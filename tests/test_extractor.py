"""Unit and property-based tests for DataExtractor."""

import re
from unittest.mock import MagicMock, PropertyMock

import pytest

from src.extractor import AccountInfo, DataExtractor


# --- Helper to create a mock driver ---


def make_mock_driver(page_html: str, elements: dict = None):
    """Create a mock WebDriver that returns elements based on CSS selectors.

    Args:
        page_html: The page source HTML string.
        elements: Dict mapping CSS selectors to mock element return values.
                  Each value is a dict with optional keys: 'text', 'attributes'.
    """
    from selenium.common.exceptions import NoSuchElementException

    driver = MagicMock()
    driver.page_source = page_html

    if elements is None:
        elements = {}

    def find_element_side_effect(by, selector):
        if selector in elements:
            elem_data = elements[selector]
            mock_elem = MagicMock()
            mock_elem.text = elem_data.get("text", "")

            def get_attr(name):
                return elem_data.get("attributes", {}).get(name)

            mock_elem.get_attribute = get_attr
            return mock_elem
        raise NoSuchElementException(f"Element not found: {selector}")

    driver.find_element = MagicMock(side_effect=find_element_side_effect)
    return driver


# --- Unit Tests ---


class TestAccountInfoDataclass:
    """Tests for AccountInfo dataclass."""

    def test_default_values_are_none(self):
        """All fields default to None."""
        info = AccountInfo()
        assert info.email is None
        assert info.user_id is None
        assert info.credits_used is None
        assert info.credits_total is None
        assert info.plan_name is None
        assert info.reset_date is None

    def test_fields_can_be_set(self):
        """Fields can be set via constructor."""
        info = AccountInfo(
            email="test@example.com",
            user_id="usr-123",
            credits_used=1578.41,
            credits_total=2000.0,
            plan_name="Pro",
            reset_date="2024-02-01",
        )
        assert info.email == "test@example.com"
        assert info.user_id == "usr-123"
        assert info.credits_used == 1578.41
        assert info.credits_total == 2000.0
        assert info.plan_name == "Pro"
        assert info.reset_date == "2024-02-01"


class TestExtractEmail:
    """Tests for extract_email()."""

    def test_extracts_email_from_matching_element(self):
        """Email is extracted from p[data-variant='semibold'][data-size='sm']."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'p[data-variant="semibold"][data-size="sm"]': {
                    "text": "user@example.com"
                }
            },
        )
        extractor = DataExtractor(driver)
        assert extractor.extract_email() == "user@example.com"

    def test_returns_none_when_element_missing(self):
        """Returns None when the email element is not found."""
        driver = make_mock_driver("<html></html>", {})
        extractor = DataExtractor(driver)
        assert extractor.extract_email() is None

    def test_strips_whitespace(self):
        """Whitespace is stripped from the email text."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'p[data-variant="semibold"][data-size="sm"]': {
                    "text": "  user@example.com  "
                }
            },
        )
        extractor = DataExtractor(driver)
        assert extractor.extract_email() == "user@example.com"


class TestExtractUserId:
    """Tests for extract_user_id()."""

    def test_extracts_user_id_from_meta_tag(self):
        """User ID is extracted from meta[name='user-id'] content attribute."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'meta[name="user-id"]': {
                    "text": "",
                    "attributes": {"content": "usr-abc-123"},
                }
            },
        )
        extractor = DataExtractor(driver)
        assert extractor.extract_user_id() == "usr-abc-123"

    def test_returns_none_when_meta_missing(self):
        """Returns None when the meta tag is not found."""
        driver = make_mock_driver("<html></html>", {})
        extractor = DataExtractor(driver)
        assert extractor.extract_user_id() is None


class TestExtractCredits:
    """Tests for extract_credits()."""

    def test_extracts_integer_credits(self):
        """Parses integer credits from aria-label."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'p[aria-label*="credits used out of"]': {
                    "text": "",
                    "attributes": {
                        "aria-label": "500 credits used out of 2000"
                    },
                }
            },
        )
        extractor = DataExtractor(driver)
        used, total = extractor.extract_credits()
        assert used == 500.0
        assert total == 2000.0

    def test_extracts_decimal_credits(self):
        """Parses decimal credits from aria-label."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'p[aria-label*="credits used out of"]': {
                    "text": "",
                    "attributes": {
                        "aria-label": "1578.41 credits used out of 2000"
                    },
                }
            },
        )
        extractor = DataExtractor(driver)
        used, total = extractor.extract_credits()
        assert used == 1578.41
        assert total == 2000.0

    def test_returns_none_tuple_when_element_missing(self):
        """Returns (None, None) when the credits element is not found."""
        driver = make_mock_driver("<html></html>", {})
        extractor = DataExtractor(driver)
        used, total = extractor.extract_credits()
        assert used is None
        assert total is None

    def test_returns_none_tuple_when_label_doesnt_match(self):
        """Returns (None, None) when aria-label doesn't match expected pattern."""
        driver = make_mock_driver(
            "<html></html>",
            {
                'p[aria-label*="credits used out of"]': {
                    "text": "",
                    "attributes": {"aria-label": "some other text"},
                }
            },
        )
        extractor = DataExtractor(driver)
        used, total = extractor.extract_credits()
        assert used is None
        assert total is None


class TestExtractPlanName:
    """Tests for extract_plan_name()."""

    def test_extracts_plan_name(self):
        """Plan name is extracted from .acme-Badge-label element."""
        driver = make_mock_driver(
            "<html></html>",
            {".acme-Badge-label": {"text": "Pro"}},
        )
        extractor = DataExtractor(driver)
        assert extractor.extract_plan_name() == "Pro"

    def test_returns_none_when_element_missing(self):
        """Returns None when the plan badge element is not found."""
        driver = make_mock_driver("<html></html>", {})
        extractor = DataExtractor(driver)
        assert extractor.extract_plan_name() is None


class TestExtractResetDate:
    """Tests for extract_reset_date()."""

    def test_extracts_reset_date(self):
        """Reset date is extracted from page source containing 'resets on'."""
        html = '<html><body><p>Estimated Usage resets on 2024-02-01</p></body></html>'
        driver = make_mock_driver(html, {})
        extractor = DataExtractor(driver)
        assert extractor.extract_reset_date() == "2024-02-01"

    def test_returns_none_when_no_reset_text(self):
        """Returns None when page source doesn't contain 'resets on'."""
        html = "<html><body><p>No reset info here</p></body></html>"
        driver = make_mock_driver(html, {})
        extractor = DataExtractor(driver)
        assert extractor.extract_reset_date() is None


class TestExtractAll:
    """Tests for extract_all()."""

    def test_extracts_all_fields(self):
        """All fields are extracted when all elements are present."""
        html = '<html><body><p>Estimated Usage resets on 2024-03-15</p></body></html>'
        elements = {
            'p[data-variant="semibold"][data-size="sm"]': {
                "text": "admin@kiro.dev"
            },
            'meta[name="user-id"]': {
                "text": "",
                "attributes": {"content": "usr-xyz-789"},
            },
            'p[aria-label*="credits used out of"]': {
                "text": "",
                "attributes": {
                    "aria-label": "750.5 credits used out of 1500"
                },
            },
            ".acme-Badge-label": {"text": "Enterprise"},
        }
        driver = make_mock_driver(html, elements)
        extractor = DataExtractor(driver)
        info = extractor.extract_all()

        assert info.email == "admin@kiro.dev"
        assert info.user_id == "usr-xyz-789"
        assert info.credits_used == 750.5
        assert info.credits_total == 1500.0
        assert info.plan_name == "Enterprise"
        assert info.reset_date == "2024-03-15"

    def test_returns_none_for_missing_fields(self):
        """Missing fields are set to None."""
        html = "<html><body></body></html>"
        driver = make_mock_driver(html, {})
        extractor = DataExtractor(driver)
        info = extractor.extract_all()

        assert info.email is None
        assert info.user_id is None
        assert info.credits_used is None
        assert info.credits_total is None
        assert info.plan_name is None
        assert info.reset_date is None


class TestParseCreditsFromLabel:
    """Tests for the static parse_credits_from_label method."""

    def test_parses_integer_values(self):
        """Parses integer credits correctly."""
        used, total = DataExtractor.parse_credits_from_label(
            "500 credits used out of 2000"
        )
        assert used == 500.0
        assert total == 2000.0

    def test_parses_decimal_values(self):
        """Parses decimal credits correctly."""
        used, total = DataExtractor.parse_credits_from_label(
            "1578.41 credits used out of 2000"
        )
        assert used == 1578.41
        assert total == 2000.0

    def test_returns_none_for_invalid_format(self):
        """Returns (None, None) for non-matching text."""
        used, total = DataExtractor.parse_credits_from_label("invalid text")
        assert used is None
        assert total is None

    def test_returns_none_for_empty_string(self):
        """Returns (None, None) for empty string."""
        used, total = DataExtractor.parse_credits_from_label("")
        assert used is None
        assert total is None


class TestParseResetDateFromText:
    """Tests for the static parse_reset_date_from_text method."""

    def test_parses_date_from_text(self):
        """Parses date from text containing 'resets on'."""
        result = DataExtractor.parse_reset_date_from_text(
            "Estimated Usage resets on 2024-02-01 some other text"
        )
        assert result == "2024-02-01"

    def test_returns_none_for_no_match(self):
        """Returns None when text doesn't contain 'resets on'."""
        result = DataExtractor.parse_reset_date_from_text("no reset info here")
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Returns None for empty string."""
        result = DataExtractor.parse_reset_date_from_text("")
        assert result is None


# --- Property-Based Tests ---

from hypothesis import given, settings, assume
from hypothesis import strategies as st


def credits_value_strategy():
    """Strategy for credit values as they appear on the page.

    Credits are displayed as decimal numbers (e.g., 1578.41, 2000, 0.5).
    We generate values with up to 2 decimal places to match real-world display.
    """
    return st.integers(min_value=0, max_value=1_000_000).map(
        lambda x: round(x / 100.0, 2)
    )


@given(
    used=credits_value_strategy(),
    total=credits_value_strategy(),
)
@settings(max_examples=200)
def test_property_credits_parsing_round_trip(used, total):
    """
    Feature: kiro-account-scraper, Property 2: Credits parsing round-trip

    **Validates: Requirements 4.3**

    For any pair of non-negative floats (used, total), formatting them as
    "{used} credits used out of {total}" and then parsing with the credits
    extractor SHALL return the original (used, total) pair.
    """
    # Format as the expected aria-label pattern
    # Use a format that matches what the page would produce (decimal notation)
    label = f"{used} credits used out of {total}"

    # Parse using the static method
    parsed_used, parsed_total = DataExtractor.parse_credits_from_label(label)

    # The parsed values should match the originals
    assert parsed_used is not None
    assert parsed_total is not None
    assert parsed_used == pytest.approx(used, rel=1e-6)
    assert parsed_total == pytest.approx(total, rel=1e-6)


@given(
    date_str=st.from_regex(r"[A-Za-z0-9\-/]+", fullmatch=True).filter(
        lambda s: len(s) > 0 and " " not in s
    )
)
@settings(max_examples=200)
def test_property_reset_date_extraction_round_trip(date_str):
    """
    Feature: kiro-account-scraper, Property 3: Reset date extraction

    **Validates: Requirements 4.5**

    For any date string (non-empty, no whitespace), embedding it in text as
    "resets on {date}" and parsing with the reset date extractor SHALL return
    the original date string.
    """
    # Embed the date in text
    text = f"Estimated Usage resets on {date_str} and more text"

    # Parse using the static method
    result = DataExtractor.parse_reset_date_from_text(text)

    assert result == date_str


@given(
    email=st.text(
        alphabet=st.characters(blacklist_characters="\n\r\t"),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip() != ""),
    user_id=st.text(
        alphabet=st.characters(blacklist_characters="\n\r\t"),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip() != ""),
    plan_name=st.text(
        alphabet=st.characters(blacklist_characters="\n\r\t"),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip() != ""),
)
@settings(max_examples=200)
def test_property_dom_field_extraction_correctness(email, user_id, plan_name):
    """
    Feature: kiro-account-scraper, Property 4: DOM field extraction correctness

    **Validates: Requirements 4.1, 4.2, 4.4**

    For any valid HTML document containing elements matching the expected selectors
    with arbitrary text content, the extractor SHALL return the exact text content
    of those elements.
    """
    elements = {
        'p[data-variant="semibold"][data-size="sm"]': {"text": email},
        'meta[name="user-id"]': {
            "text": "",
            "attributes": {"content": user_id},
        },
        ".acme-Badge-label": {"text": plan_name},
    }
    driver = make_mock_driver("<html></html>", elements)
    extractor = DataExtractor(driver)

    assert extractor.extract_email() == email.strip()
    assert extractor.extract_user_id() == user_id
    assert extractor.extract_plan_name() == plan_name.strip()


@given(
    include_email=st.booleans(),
    include_user_id=st.booleans(),
    include_credits=st.booleans(),
    include_plan=st.booleans(),
    include_reset_date=st.booleans(),
)
@settings(max_examples=200)
def test_property_missing_fields_yield_none(
    include_email, include_user_id, include_credits, include_plan, include_reset_date
):
    """
    Feature: kiro-account-scraper, Property 5: Missing fields yield None

    **Validates: Requirements 4.6**

    For any subset of expected DOM selectors that are absent from an HTML document,
    the corresponding fields in the extracted AccountInfo SHALL be None, while
    present fields are correctly extracted.
    """
    elements = {}
    html = "<html><body>"

    if include_email:
        elements['p[data-variant="semibold"][data-size="sm"]'] = {
            "text": "test@example.com"
        }
    if include_user_id:
        elements['meta[name="user-id"]'] = {
            "text": "",
            "attributes": {"content": "usr-123"},
        }
    if include_credits:
        elements['p[aria-label*="credits used out of"]'] = {
            "text": "",
            "attributes": {"aria-label": "100 credits used out of 500"},
        }
    if include_plan:
        elements[".acme-Badge-label"] = {"text": "Pro"}
    if include_reset_date:
        html = '<html><body><p>resets on 2024-01-15</p>'

    html += "</body></html>"
    driver = make_mock_driver(html, elements)
    extractor = DataExtractor(driver)
    info = extractor.extract_all()

    # Check that missing fields are None and present fields are not None
    if include_email:
        assert info.email == "test@example.com"
    else:
        assert info.email is None

    if include_user_id:
        assert info.user_id == "usr-123"
    else:
        assert info.user_id is None

    if include_credits:
        assert info.credits_used == 100.0
        assert info.credits_total == 500.0
    else:
        assert info.credits_used is None
        assert info.credits_total is None

    if include_plan:
        assert info.plan_name == "Pro"
    else:
        assert info.plan_name is None

    if include_reset_date:
        assert info.reset_date == "2024-01-15"
    else:
        assert info.reset_date is None
