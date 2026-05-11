"""Main orchestrator for Kiro Account Scraper.

CLI entry point that launches Chrome with local profiles, navigates to
Account Settings, extracts account information, and saves results to SQLite.

On first run for a profile, Chrome opens and user logs in manually.
Subsequent runs reuse the saved session automatically.
"""

import argparse
import logging
import os
import sys
import time

from colorama import init as colorama_init, Fore, Style

from src.browser import BrowserLauncher
from src.navigator import PageNavigator, ACCOUNT_SETTINGS_URL, PAGE_LOAD_TIMEOUT
from src.extractor import DataExtractor
from src.database import DatabaseWriter
from src.reporter import SummaryReporter, ScrapingResult

# Initialize colorama for Windows ANSI support
colorama_init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Kiro Account Scraper - Extract account info from Kiro.dev"
    )
    parser.add_argument(
        "num_profiles",
        type=int,
        help="Number of profiles to process",
    )
    parser.add_argument(
        "--db-path",
        default=os.path.join("dashboard", "kiro_accounts.db"),
        help="Path to the SQLite database file (default: dashboard/kiro_accounts.db)",
    )
    parser.add_argument(
        "--profiles-dir",
        default="chrome_profiles",
        help="Directory to store Chrome profiles (default: chrome_profiles)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode (no visible browser window). "
             "Only use after profiles are already logged in.",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        default=False,
        help="Login mode: open Chrome for each profile and wait for manual login. "
             "Use this on first run or when sessions have expired.",
    )
    return parser.parse_args(argv)


def wait_for_login(driver, profile_name: str) -> None:
    """Wait for user to manually log in.

    Opens the Kiro sign-in page, clicks "Your organization", fills in
    Start URL and Region from .env, then waits for user to complete login.

    Args:
        driver: WebDriver instance.
        profile_name: Name of the profile (for display).
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import WebDriverException
    from dotenv import load_dotenv

    load_dotenv()
    start_url = os.environ.get("START_URL", "")
    region = os.environ.get("REGION", "")

    print(
        f"\n{Fore.YELLOW}[{profile_name}] Opening Kiro sign-in page...{Style.RESET_ALL}"
    )

    driver.get("https://app.kiro.dev/signin")

    try:
        # Wait for and click "Your organization" button
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Your organization')]")
            )
        ).click()
        logger.info("Clicked 'Your organization' button.")
        time.sleep(0.5)

        # Wait for and fill in "Start URL" input
        start_url_input = WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//label[contains(., 'Start URL')]/following::input[1]")
            )
        )
        start_url_input.clear()
        start_url_input.send_keys(start_url)
        logger.info("Filled in Start URL.")
        time.sleep(0.5)

        # Wait for and fill in "Region" input
        region_input = WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//label[contains(., 'Region')]/following::input[1]")
            )
        )
        region_input.clear()
        region_input.send_keys(region)
        logger.info("Filled in Region.")
        time.sleep(0.5)

        # Click "Continue" button
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Continue')]")
            )
        ).click()
        logger.info("Clicked 'Continue' button.")
        time.sleep(0.5)

    except Exception as e:
        logger.warning(f"Error during sign-in form automation: {e}")

    print(
        f"{Fore.YELLOW}[{profile_name}] Please complete the login in the browser window.{Style.RESET_ALL}"
    )

    # Wait for login to complete (poll current page for redirect to account settings)
    timeout = 300  # 5 minutes to log in
    start = time.time()
    while time.time() - start < timeout:
        try:
            current_url = driver.current_url
            if "settings/account" in current_url:
                elem = driver.find_element(
                    By.CSS_SELECTOR, 'p[data-variant="semibold"][data-size="sm"]'
                )
                if elem and elem.text.strip():
                    print(f"{Fore.GREEN}[{profile_name}] Login detected! ✓{Style.RESET_ALL}")
                    return
        except WebDriverException:
            # Browser was closed by user, skip to next profile
            print(f"{Fore.YELLOW}[{profile_name}] Browser closed. Skipping.{Style.RESET_ALL}")
            raise
        except Exception:
            pass
        time.sleep(2)

    print(f"{Fore.RED}[{profile_name}] Login timeout (5 min). Skipping.{Style.RESET_ALL}")


MAX_RETRIES = 5
ERROR_LOG_FILE = "scraper_errors.log"


def process_profile(profile_name, args, db, reporter, run_timestamp, launcher=None):
    """Process a single profile. Returns (success, error_message, skip_retry)."""
    from selenium.common.exceptions import WebDriverException

    launcher = BrowserLauncher(
        profile_name,
        headless=args.headless,
        profiles_dir=args.profiles_dir,
    )
    try:
        driver = launcher.launch()
        try:
            if args.login or not launcher.is_logged_in():
                wait_for_login(driver, profile_name)
            else:
                navigator = PageNavigator(driver)
                navigator.navigate_to_settings()

            extractor = DataExtractor(driver)
            account_info = extractor.extract_all()

            email_str = f"{Fore.CYAN}{account_info.email or 'N/A'}{Style.RESET_ALL}"
            plan_str = f"{Fore.MAGENTA}{account_info.plan_name or 'N/A'}{Style.RESET_ALL}"
            credits_used = account_info.credits_used
            credits_total = account_info.credits_total
            if credits_total and credits_total > 0 and credits_used is not None:
                ratio = credits_used / credits_total
                if ratio >= 1.0:
                    credits_color = Fore.MAGENTA
                elif ratio > 0.8:
                    credits_color = Fore.RED
                elif ratio > 0.5:
                    credits_color = Fore.YELLOW
                elif ratio > 0:
                    credits_color = Fore.GREEN
                else:
                    credits_color = Fore.CYAN
            else:
                credits_color = Fore.GREEN
            used_str = str(credits_used) if credits_used is not None else "?"
            total_str = str(credits_total) if credits_total is not None else "?"
            credits_str = f"{credits_color}{used_str}/{total_str}{Style.RESET_ALL}"
            reset_str = f"{Fore.BLUE}{account_info.reset_date or 'N/A'}{Style.RESET_ALL}"
            logger.info(
                f"  Email: {email_str} | Plan: {plan_str} | Credits: {credits_str} | Reset: {reset_str}"
            )

            db.save_account(profile_name, account_info, run_timestamp)
            return True, None, False
        finally:
            launcher.close(driver)
    except WebDriverException as e:
        # Browser was closed by user — skip without retry
        return False, "Browser closed by user", True
    except Exception as e:
        return False, str(e), False


def log_persistent_failure(profile_name, error, attempts):
    """Log to file when a profile fails all retry attempts."""
    from datetime import datetime
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] FAILED after {attempts} attempts | Profile: {profile_name} | Error: {error}\n")


def main(argv=None):
    """Main entry point for the Kiro Account Scraper."""
    from datetime import datetime

    args = parse_args(argv)

    if args.num_profiles < 1:
        logger.error("Number of profiles must be at least 1.")
        sys.exit(1)

    profiles = [f"Profile_{i}" for i in range(1, args.num_profiles + 1)]

    # Capture run timestamp once at CLI start
    run_timestamp = datetime.now().isoformat()

    db = DatabaseWriter(args.db_path)
    reporter = SummaryReporter()
    total = len(profiles)

    # retry_queue: list of (profile_name, attempt_count)
    retry_queue = []

    try:
        # First pass
        for idx, profile_name in enumerate(profiles, start=1):
            reporter.print_progress(idx, total, profile_name)
            success, error, skip_retry = process_profile(profile_name, args, db, reporter, run_timestamp)
            if success:
                reporter.add_result(ScrapingResult(profile=profile_name, success=True))
                logger.info(f"Successfully extracted data for: {profile_name}")
            elif skip_retry:
                logger.info(f"Skipped '{profile_name}': {error}")
                reporter.add_result(ScrapingResult(profile=profile_name, success=False, error=error))
            else:
                logger.warning(f"Failed '{profile_name}' (attempt 1/{MAX_RETRIES}): {error}")
                retry_queue.append((profile_name, 1, error))

        # Retry loop
        while retry_queue:
            current_batch = retry_queue[:]
            retry_queue = []
            for profile_name, attempts, last_error in current_batch:
                if attempts >= MAX_RETRIES:
                    # Exhausted all retries
                    logger.error(f"Profile '{profile_name}' failed after {MAX_RETRIES} attempts: {last_error}")
                    log_persistent_failure(profile_name, last_error, MAX_RETRIES)
                    db.save_error(profile_name, last_error, MAX_RETRIES)
                    reporter.add_result(ScrapingResult(profile=profile_name, success=False, error=last_error))
                    continue

                logger.info(f"Retrying '{profile_name}' (attempt {attempts + 1}/{MAX_RETRIES})...")
                time.sleep(2)
                success, error, skip_retry = process_profile(profile_name, args, db, reporter, run_timestamp)
                if success:
                    reporter.add_result(ScrapingResult(profile=profile_name, success=True))
                    logger.info(f"Retry succeeded for: {profile_name}")
                elif skip_retry:
                    logger.info(f"Skipped '{profile_name}' on retry: {error}")
                    reporter.add_result(ScrapingResult(profile=profile_name, success=False, error=error))
                else:
                    retry_queue.append((profile_name, attempts + 1, error))

    finally:
        db.close()

    reporter.print_summary()


if __name__ == "__main__":
    main()
