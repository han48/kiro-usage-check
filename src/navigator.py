"""Page Navigator module for navigating to Kiro account settings."""

import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

ACCOUNT_SETTINGS_URL = "https://app.kiro.dev/settings/account"
PAGE_LOAD_TIMEOUT = 30  # seconds


class PageNavigator:
    """Navigates to and waits for the Kiro Account Settings page."""

    def __init__(self, driver: webdriver.Chrome):
        """Initialize with active WebDriver instance.

        Args:
            driver: An active Chrome WebDriver instance.
        """
        self.driver = driver

    def navigate_to_settings(self) -> bool:
        """Navigate to Account Settings page and wait for content.

        Navigates to the Account Settings URL and waits for the page to be
        fully rendered by checking for the email element
        (p[data-variant="semibold"][data-size="sm"]).

        Returns:
            True if page loaded successfully.

        Raises:
            TimeoutError: If page doesn't load within PAGE_LOAD_TIMEOUT seconds.
        """
        logger.info(f"Navigating to {ACCOUNT_SETTINGS_URL}")
        self.driver.get(ACCOUNT_SETTINGS_URL)

        try:
            WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'p[data-variant="semibold"][data-size="sm"]')
                )
            )
            logger.info("Account Settings page loaded successfully.")
            return True
        except Exception:
            raise TimeoutError(
                f"Page did not load within {PAGE_LOAD_TIMEOUT} seconds."
            )
