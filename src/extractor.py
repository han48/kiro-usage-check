"""Data Extractor module for extracting account information from Kiro.dev Account Settings page."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Account information extracted from the Kiro.dev Account Settings page."""

    email: Optional[str] = None
    user_id: Optional[str] = None
    credits_used: Optional[float] = None
    credits_total: Optional[float] = None
    plan_name: Optional[str] = None
    reset_date: Optional[str] = None


class DataExtractor:
    """Extracts account information from the Kiro.dev Account Settings page using Selenium."""

    # DOM Selectors
    EMAIL_SELECTOR = 'p[data-variant="semibold"][data-size="sm"]'
    USER_ID_META = 'meta[name="user-id"]'
    CREDITS_SELECTOR = 'p[aria-label*="credits used out of"]'
    PLAN_SELECTOR = '.acme-Badge-label'

    # Parsing patterns
    CREDITS_PATTERN = re.compile(r"(\d+\.?\d*)\s+credits used out of\s+(\d+\.?\d*)")
    RESET_DATE_PATTERN = re.compile(r"resets on\s+([^\s<]+)")

    def __init__(self, driver: webdriver.Chrome):
        """Initialize with active WebDriver instance.

        Args:
            driver: A Selenium Chrome WebDriver instance with the page loaded.
        """
        self.driver = driver

    def extract_email(self) -> Optional[str]:
        """Extract email from p[data-variant='semibold'][data-size='sm'].

        Returns:
            The email address text, or None if the element is not found.
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, self.EMAIL_SELECTOR)
            return element.text.strip()
        except NoSuchElementException:
            return None

    def extract_user_id(self) -> Optional[str]:
        """Extract user ID from meta[name='user-id'] content attribute.

        Returns:
            The user ID string, or None if the meta tag is not found.
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, self.USER_ID_META)
            return element.get_attribute("content")
        except NoSuchElementException:
            return None

    def extract_credits(self) -> tuple[Optional[float], Optional[float]]:
        """Extract credits used and total from aria-label.

        Parses 'X credits used out of Y' pattern from the aria-label attribute.

        Returns:
            A tuple of (credits_used, credits_total), or (None, None) if not found.
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, self.CREDITS_SELECTOR)
            label = element.get_attribute("aria-label")
            if label:
                return self.parse_credits_from_label(label)
        except NoSuchElementException:
            pass
        return (None, None)

    def extract_plan_name(self) -> Optional[str]:
        """Extract plan name from .acme-Badge-label element.

        Returns:
            The plan name text, or None if the element is not found.
        """
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, self.PLAN_SELECTOR)
            return element.text.strip()
        except NoSuchElementException:
            return None

    def extract_reset_date(self) -> Optional[str]:
        """Extract reset date from text containing 'resets on'.

        Searches the page source for text matching 'resets on {date}'.

        Returns:
            The reset date string, or None if not found.
        """
        try:
            page_source = self.driver.page_source
            return self.parse_reset_date_from_text(page_source)
        except Exception:
            return None

    def extract_all(self) -> AccountInfo:
        """Extract all account information from the current page.

        Calls all individual extractors and returns an AccountInfo dataclass.
        Logs warnings for any fields that could not be found.

        Returns:
            AccountInfo with None for any fields that couldn't be found.
        """
        email = self.extract_email()
        if email is None:
            logger.warning("Could not extract email from page")

        user_id = self.extract_user_id()
        if user_id is None:
            logger.warning("Could not extract user_id from page")

        credits_used, credits_total = self.extract_credits()
        if credits_used is None:
            logger.warning("Could not extract credits from page")

        plan_name = self.extract_plan_name()
        if plan_name is None:
            logger.warning("Could not extract plan_name from page")

        reset_date = self.extract_reset_date()
        if reset_date is None:
            logger.warning("Could not extract reset_date from page")

        return AccountInfo(
            email=email,
            user_id=user_id,
            credits_used=credits_used,
            credits_total=credits_total,
            plan_name=plan_name,
            reset_date=reset_date,
        )

    @staticmethod
    def parse_credits_from_label(label: str) -> tuple[Optional[float], Optional[float]]:
        """Parse credits used and total from an aria-label string.

        Args:
            label: The aria-label text, e.g. "1578.41 credits used out of 2000"

        Returns:
            A tuple of (credits_used, credits_total), or (None, None) if parsing fails.
        """
        match = DataExtractor.CREDITS_PATTERN.search(label)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        return (None, None)

    @staticmethod
    def parse_reset_date_from_text(text: str) -> Optional[str]:
        """Parse reset date from text containing 'resets on'.

        Args:
            text: Text content that may contain 'resets on {date}'.

        Returns:
            The date string, or None if not found.
        """
        match = DataExtractor.RESET_DATE_PATTERN.search(text)
        if match:
            return match.group(1)
        return None
