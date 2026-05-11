"""Browser Launcher module for Chrome WebDriver management.

Uses local Selenium-managed profiles stored in a local directory.
On first run, user logs in manually. Subsequent runs reuse the saved session.
"""

import os
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

# Default local directory for profiles
DEFAULT_PROFILES_DIR = "chrome_profiles"


class BrowserLauncher:
    """Launches Chrome with a local profile managed by Selenium.

    Each profile is a subdirectory under the profiles directory (e.g.
    chrome_profiles/Profile_1/). Chrome stores cookies, local storage,
    and session data there, so logins persist between runs.
    """

    def __init__(self, profile_name: str, headless: bool = False,
                 profiles_dir: str = DEFAULT_PROFILES_DIR):
        """Initialize with a profile name.

        Args:
            profile_name: Name of the profile (e.g. "Profile_1").
            headless: If True, run Chrome in headless mode.
            profiles_dir: Directory to store all profiles (default: "chrome_profiles").
        """
        self.profile_name = profile_name
        self.headless = headless
        self.profiles_dir = profiles_dir
        self.profile_path = os.path.abspath(
            os.path.join(profiles_dir, profile_name)
        )

    def is_logged_in(self) -> bool:
        """Check if this profile has been used before (likely logged in).

        Returns:
            True if the profile directory exists and has data.
        """
        return os.path.isdir(self.profile_path)

    def launch(self) -> webdriver.Chrome:
        """Launch Chrome with the local profile.

        Creates the profile directory if it doesn't exist. Chrome will
        persist session data there automatically.

        Returns:
            WebDriver instance for the launched Chrome browser.
        """
        # Ensure profile directory exists
        os.makedirs(self.profile_path, exist_ok=True)

        options = Options()
        options.add_argument(f"--user-data-dir={self.profile_path}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")

        # Don't wait for full page load during browser init
        options.page_load_strategy = "none"

        if self.headless:
            options.add_argument("--headless=new")

        logger.info(f"Launching Chrome with profile: {self.profile_name}")
        driver = webdriver.Chrome(options=options)
        return driver

    def close(self, driver: webdriver.Chrome) -> None:
        """Close browser and release resources.

        Args:
            driver: The WebDriver instance to close.
        """
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed successfully.")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
