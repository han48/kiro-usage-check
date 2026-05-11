"""Integration tests for the Kiro Account Scraper pipeline.

Tests the full end-to-end flow with mocked browser, including retry logic.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from src.main import main, process_profile, MAX_RETRIES, ERROR_LOG_FILE
from src.database import DatabaseWriter
from src.extractor import AccountInfo


def make_mock_driver_with_page():
    """Create a mock Chrome WebDriver that returns realistic page content."""
    from selenium.common.exceptions import NoSuchElementException

    mock_driver = MagicMock()
    mock_driver.page_source = '<html><body><p>resets on 2024-03-15</p></body></html>'

    def find_element_side_effect(by, selector):
        elements_map = {
            'p[data-variant="semibold"][data-size="sm"]': {"text": "testuser@kiro.dev", "attributes": {}},
            'meta[name="user-id"]': {"text": "", "attributes": {"content": "usr-test-abc-123"}},
            'p[aria-label*="credits used out of"]': {"text": "1250.5 / 2000", "attributes": {"aria-label": "1250.5 credits used out of 2000"}},
            '.acme-Badge-label': {"text": "Pro", "attributes": {}},
        }
        if selector in elements_map:
            elem_data = elements_map[selector]
            mock_elem = MagicMock()
            mock_elem.text = elem_data["text"]
            mock_elem.get_attribute = lambda name: elem_data["attributes"].get(name)
            return mock_elem
        raise NoSuchElementException(f"Element not found: {selector}")

    mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)
    return mock_driver


def patch_browser_success():
    """Context manager that patches BrowserLauncher to always succeed."""
    mock_driver = make_mock_driver_with_page()
    patcher_launcher = patch("src.main.BrowserLauncher")
    patcher_nav = patch("src.main.PageNavigator")

    MockLauncher = patcher_launcher.start()
    MockNavigator = patcher_nav.start()

    instance = MagicMock()
    instance.launch.return_value = mock_driver
    instance.close.return_value = None
    instance.is_logged_in.return_value = True
    MockLauncher.return_value = instance

    nav_instance = MagicMock()
    nav_instance.navigate_to_settings.return_value = True
    MockNavigator.return_value = nav_instance

    return patcher_launcher, patcher_nav


class TestEndToEndPipeline:
    """End-to-end integration tests with mocked browser."""

    def test_full_pipeline_single_profile(self, tmp_path):
        """Full pipeline with 1 profile extracts and saves data."""
        db_path = str(tmp_path / "test.db")
        p1, p2 = patch_browser_success()
        try:
            main(["1", "--db-path", db_path, "--profiles-dir", str(tmp_path / "profiles")])
        finally:
            p1.stop()
            p2.stop()

        db = DatabaseWriter(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM accounts")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "testuser@kiro.dev"
        assert rows[0][3] == 1250.5
        assert rows[0][4] == 2000.0
        assert rows[0][5] == "Pro"
        db.close()

    def test_full_pipeline_multiple_profiles(self, tmp_path):
        """Pipeline processes multiple profiles."""
        db_path = str(tmp_path / "test.db")
        p1, p2 = patch_browser_success()
        try:
            main(["3", "--db-path", db_path, "--profiles-dir", str(tmp_path / "profiles")])
        finally:
            p1.stop()
            p2.stop()

        db = DatabaseWriter(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute("SELECT count(*) FROM accounts")
        assert cursor.fetchone()[0] == 3
        cursor.execute("SELECT count(*) FROM credits_history")
        assert cursor.fetchone()[0] == 3
        db.close()


class TestRetryLogic:
    """Tests for retry queue mechanism."""

    def test_retry_succeeds_on_second_attempt(self, tmp_path):
        """Profile that fails once then succeeds is saved correctly."""
        db_path = str(tmp_path / "test.db")
        mock_driver = make_mock_driver_with_page()

        with patch("src.main.BrowserLauncher") as MockLauncher:
            instance = MagicMock()
            # First call fails, second succeeds
            instance.launch.side_effect = [Exception("timeout"), mock_driver]
            instance.close.return_value = None
            instance.is_logged_in.return_value = True
            MockLauncher.return_value = instance

            with patch("src.main.PageNavigator") as MockNav:
                nav = MagicMock()
                nav.navigate_to_settings.return_value = True
                MockNav.return_value = nav

                main(["1", "--db-path", db_path, "--profiles-dir", str(tmp_path / "p")])

        db = DatabaseWriter(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute("SELECT count(*) FROM accounts")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT count(*) FROM scrape_errors")
        assert cursor.fetchone()[0] == 0
        db.close()

    def test_retry_exhausted_saves_error(self, tmp_path, monkeypatch):
        """Profile that fails all 5 retries is logged to DB and file."""
        db_path = str(tmp_path / "test.db")
        error_log = str(tmp_path / "errors.log")
        monkeypatch.setattr("src.main.ERROR_LOG_FILE", error_log)

        with patch("src.main.BrowserLauncher") as MockLauncher:
            instance = MagicMock()
            instance.launch.side_effect = Exception("persistent error")
            instance.close.return_value = None
            MockLauncher.return_value = instance

            with patch("src.main.time.sleep"):  # skip delays
                main(["1", "--db-path", db_path, "--profiles-dir", str(tmp_path / "p")])

        # Check error saved to DB
        db = DatabaseWriter(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute("SELECT profile_name, error_message, attempts FROM scrape_errors")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Profile_1"
        assert "persistent error" in row[1]
        assert row[2] == MAX_RETRIES
        db.close()

        # Check error log file
        assert os.path.exists(error_log)
        content = open(error_log).read()
        assert "Profile_1" in content
        assert "persistent error" in content

    def test_retry_mixed_success_and_failure(self, tmp_path, monkeypatch):
        """With 2 profiles: one succeeds, one fails all retries."""
        db_path = str(tmp_path / "test.db")
        error_log = str(tmp_path / "errors.log")
        monkeypatch.setattr("src.main.ERROR_LOG_FILE", error_log)

        mock_driver = make_mock_driver_with_page()
        call_count = {"n": 0}

        with patch("src.main.BrowserLauncher") as MockLauncher:
            def make_instance(name, **kwargs):
                inst = MagicMock()
                inst.close.return_value = None
                inst.is_logged_in.return_value = True
                if name == "Profile_1":
                    inst.launch.return_value = mock_driver
                else:
                    inst.launch.side_effect = Exception("fail")
                return inst

            MockLauncher.side_effect = make_instance

            with patch("src.main.PageNavigator") as MockNav:
                nav = MagicMock()
                nav.navigate_to_settings.return_value = True
                MockNav.return_value = nav

                with patch("src.main.time.sleep"):
                    main(["2", "--db-path", db_path, "--profiles-dir", str(tmp_path / "p")])

        db = DatabaseWriter(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute("SELECT count(*) FROM accounts")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT count(*) FROM scrape_errors")
        assert cursor.fetchone()[0] == 1
        db.close()
