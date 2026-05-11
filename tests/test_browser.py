"""Unit tests for Browser Launcher and Page Navigator modules."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from src.browser import BrowserLauncher, ProfileNotFoundError
from src.navigator import PageNavigator, ACCOUNT_SETTINGS_URL, PAGE_LOAD_TIMEOUT


class TestBrowserLauncher:
    """Tests for BrowserLauncher class."""

    def test_launch_sets_user_data_dir_and_profile_directory(self, tmp_path):
        """Verify that launch() sets --user-data-dir and --profile-directory correctly."""
        # Create a profile subfolder
        profile_sub = tmp_path / "Profile 1"
        profile_sub.mkdir()

        launcher = BrowserLauncher(str(profile_sub))

        with patch("src.browser.webdriver.Chrome") as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            driver = launcher.launch()

            # Verify Chrome was called with correct options
            mock_chrome.assert_called_once()
            call_kwargs = mock_chrome.call_args
            options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
            assert options is not None
            assert f"--user-data-dir={str(tmp_path)}" in options.arguments
            assert "--profile-directory=Profile 1" in options.arguments

    def test_launch_with_pipe_separator_format(self, tmp_path):
        """Verify pipe-separated format: 'user_data_dir|profile_dir'."""
        profile_sub = tmp_path / "Profile 2"
        profile_sub.mkdir()

        pipe_path = f"{str(tmp_path)}|Profile 2"
        launcher = BrowserLauncher(pipe_path)

        with patch("src.browser.webdriver.Chrome") as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            driver = launcher.launch()

            mock_chrome.assert_called_once()
            call_kwargs = mock_chrome.call_args
            options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
            assert f"--user-data-dir={str(tmp_path)}" in options.arguments
            assert "--profile-directory=Profile 2" in options.arguments

    def test_launch_raises_profile_not_found_error(self):
        """Verify that launch() raises ProfileNotFoundError for non-existent directory."""
        non_existent_path = "/non/existent/chrome/profile/path"
        launcher = BrowserLauncher(non_existent_path)

        with pytest.raises(ProfileNotFoundError) as exc_info:
            launcher.launch()

        assert "path" in str(exc_info.value)

    def test_launch_returns_webdriver_instance(self, tmp_path):
        """Verify that launch() returns a WebDriver instance."""
        profile_sub = tmp_path / "Default"
        profile_sub.mkdir()

        launcher = BrowserLauncher(str(profile_sub))

        with patch("src.browser.webdriver.Chrome") as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            result = launcher.launch()

            assert result is mock_driver

    def test_launch_copy_mode(self, tmp_path):
        """Verify copy mode copies profile and uses local directory."""
        # Create source profile with a file
        profile_sub = tmp_path / "source" / "Profile 1"
        profile_sub.mkdir(parents=True)
        (profile_sub / "Cookies").write_text("cookie data")
        (profile_sub / "Preferences").write_text("{}")

        # Also create Local State in parent
        (tmp_path / "source" / "Local State").write_text("{}")

        local_dir = str(tmp_path / "local_profiles")
        launcher = BrowserLauncher(
            str(profile_sub),
            copy_to_local=True,
            local_profiles_dir=local_dir,
        )

        with patch("src.browser.webdriver.Chrome") as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            driver = launcher.launch()

            # Verify Chrome was called with local copy path
            mock_chrome.assert_called_once()
            call_kwargs = mock_chrome.call_args
            options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
            # Should use local_profiles_dir, not original path
            user_data_arg = [a for a in options.arguments if "--user-data-dir=" in a][0]
            assert local_dir in user_data_arg
            assert "--profile-directory=Profile 1" in options.arguments

        # Verify files were copied
        copied_cookies = os.path.join(local_dir, "Profile_1", "Profile 1", "Cookies")
        assert os.path.isfile(copied_cookies)

    def test_close_calls_driver_quit(self):
        """Verify that close() calls driver.quit()."""
        launcher = BrowserLauncher("/some/path")
        mock_driver = MagicMock()

        launcher.close(mock_driver)

        mock_driver.quit.assert_called_once()

    def test_close_handles_none_driver(self):
        """Verify that close() handles None driver gracefully."""
        launcher = BrowserLauncher("/some/path")

        # Should not raise any exception
        launcher.close(None)

    def test_close_handles_quit_exception(self):
        """Verify that close() handles exceptions from driver.quit() gracefully."""
        launcher = BrowserLauncher("/some/path")
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = Exception("Browser already closed")

        # Should not raise any exception
        launcher.close(mock_driver)


class TestPageNavigator:
    """Tests for PageNavigator class."""

    def test_navigate_to_settings_uses_correct_url(self):
        """Verify that navigate_to_settings() navigates to the correct URL."""
        mock_driver = MagicMock()

        # Mock WebDriverWait to simulate successful page load
        with patch("src.navigator.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True

            navigator = PageNavigator(mock_driver)
            result = navigator.navigate_to_settings()

            mock_driver.get.assert_called_once_with(ACCOUNT_SETTINGS_URL)
            assert result is True

    def test_navigate_to_settings_waits_for_element(self):
        """Verify that navigate_to_settings() waits for the email element."""
        mock_driver = MagicMock()

        with patch("src.navigator.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True

            navigator = PageNavigator(mock_driver)
            navigator.navigate_to_settings()

            # Verify WebDriverWait was called with correct timeout
            mock_wait.assert_called_once_with(mock_driver, PAGE_LOAD_TIMEOUT)
            # Verify until was called (waiting for element)
            mock_wait_instance.until.assert_called_once()

    def test_navigate_to_settings_raises_timeout_error(self):
        """Verify that navigate_to_settings() raises TimeoutError on timeout."""
        mock_driver = MagicMock()

        with patch("src.navigator.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            # Simulate timeout by raising an exception from until()
            mock_wait_instance.until.side_effect = Exception("Timeout")

            navigator = PageNavigator(mock_driver)

            with pytest.raises(TimeoutError) as exc_info:
                navigator.navigate_to_settings()

            assert str(PAGE_LOAD_TIMEOUT) in str(exc_info.value)

    def test_navigate_to_settings_returns_true_on_success(self):
        """Verify that navigate_to_settings() returns True when page loads."""
        mock_driver = MagicMock()

        with patch("src.navigator.WebDriverWait") as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True

            navigator = PageNavigator(mock_driver)
            result = navigator.navigate_to_settings()

            assert result is True
