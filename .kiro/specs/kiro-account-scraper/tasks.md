# Tasks: Kiro Account Scraper

## Task 1: Project Setup and Configuration

- [x] 1.1 Create project directory structure with `src/` and `tests/` folders
- [x] 1.2 Create `requirements.txt` with dependencies: selenium, hypothesis, pytest
- [x] 1.3 Create `profiles_sample.txt` with example entries showing Windows and Linux/macOS paths, comments, and format documentation
- [x] 1.4 Create `src/__init__.py` and `tests/__init__.py`

## Task 2: Profile Reader Module

- [x] 2.1 Create `src/profile_reader.py` with `ProfileReader` class
- [x] 2.2 Implement `read_profiles()` method that reads file, skips empty lines and lines starting with "#", returns list of valid paths
- [x] 2.3 Implement error handling: raise `FileNotFoundError` if file doesn't exist, return empty list if no valid entries
- [x] 2.4 Create `tests/test_profile_reader.py` with unit tests for file not found, empty file, comments-only file, valid entries
- [x] 2.5 [PBT] Write property test: For any text file content, profile reader returns exactly the non-empty, non-comment lines in order (Property 1)

## Task 3: Data Extractor Module

- [x] 3.1 Create `src/extractor.py` with `AccountInfo` dataclass and `DataExtractor` class
- [x] 3.2 Implement `extract_email()` using selector `p[data-variant="semibold"][data-size="sm"]`
- [x] 3.3 Implement `extract_user_id()` using selector `meta[name="user-id"]` content attribute
- [x] 3.4 Implement `extract_credits()` parsing "X credits used out of Y" from `p[aria-label*="credits used out of"]` aria-label
- [x] 3.5 Implement `extract_plan_name()` using selector `.acme-Badge-label`
- [x] 3.6 Implement `extract_reset_date()` parsing date from text containing "resets on"
- [x] 3.7 Implement `extract_all()` that calls all extractors, returns AccountInfo with None for missing fields, logs warnings
- [x] 3.8 Create `tests/test_extractor.py` with unit tests using sample HTML snippets
- [x] 3.9 [PBT] Write property test: For any (used, total) integer pair, formatting as "X credits used out of Y" and parsing returns original pair (Property 2)
- [x] 3.10 [PBT] Write property test: For any date string, embedding in "resets on {date}" text and parsing returns original date (Property 3)
- [x] 3.11 [PBT] Write property test: For any HTML with expected selectors containing arbitrary text, extractor returns exact text content (Property 4)
- [x] 3.12 [PBT] Write property test: For any subset of missing selectors, corresponding AccountInfo fields are None (Property 5)

## Task 4: Database Writer Module

- [x] 4.1 Create `src/database.py` with `DatabaseWriter` class
- [x] 4.2 Implement `__init__()` that creates SQLite database and both tables (`accounts` + `credits_history`) if not exists
- [x] 4.3 Implement `save_account()` using INSERT OR REPLACE on `accounts` table, and INSERT into `credits_history` for each extraction
- [x] 4.4 Implement `get_history()` to retrieve credits history for a profile ordered by timestamp
- [x] 4.5 Implement `close()` to close database connection
- [x] 4.6 Create `tests/test_database.py` with unit tests for schema creation, insert, update, and history retrieval
- [x] 4.7 [PBT] Write property test: For any sequence of saves for same profile, reading back from accounts returns last saved data with exactly one record; credits_history contains all records in order (Property 6)

## Task 5: Browser Launcher and Page Navigator

- [x] 5.1 Create `src/browser.py` with `BrowserLauncher` class
- [x] 5.2 Implement `launch()` that creates Chrome WebDriver with `--user-data-dir` option pointing to profile path
- [x] 5.3 Implement profile directory existence check, raising `ProfileNotFoundError` if not found
- [x] 5.4 Implement `close()` to quit driver and release resources
- [x] 5.5 Create `src/navigator.py` with `PageNavigator` class
- [x] 5.6 Implement `navigate_to_settings()` that navigates to Account Settings URL and waits up to 30 seconds for page content
- [x] 5.7 Create `tests/test_browser.py` with unit tests verifying Chrome options and error handling (mocked WebDriver)

## Task 6: Summary Reporter Module

- [x] 6.1 Create `src/reporter.py` with `ScrapingResult` dataclass and `SummaryReporter` class
- [x] 6.2 Implement `add_result()`, `print_progress()`, and `print_summary()` methods
- [x] 6.3 Create `tests/test_reporter.py` with unit tests for progress and summary output
- [x] 6.4 [PBT] Write property test: For any list of ScrapingResults, summary totals satisfy total = successes + failures (Property 7)

## Task 7: Main Orchestrator

- [x] 7.1 Create `src/main.py` as CLI entry point with argument parsing (`num_profiles`, optional `--db-path`, `--profiles-dir`, `--headless`, `--login`)
- [x] 7.2 Implement main loop: read profiles → for each profile: launch browser → navigate → extract → save → close browser
- [x] 7.3 Implement error resilience: catch exceptions per profile, log errors, continue to next profile
- [x] 7.4 Integrate SummaryReporter for progress and final summary output
- [x] 7.5 Handle edge cases: file not found (exit 1), no valid profiles (warning + exit 0)

## Task 8: Web Dashboard (Static HTML)

- [x] 8.1 Create `dashboard/index.html` with basic layout: left panel (table), right panel (chart area), time range selector, detailed toggle
- [x] 8.2 Integrate sql.js (CDN) to load and query SQLite `.db` file fetched from public path (same directory)
- [x] 8.3 Implement accounts table rendering: query `accounts` table, display username, plan, credits used/total, remaining, daily usage, last extracted time
- [x] 8.3.1 Implement `getDailyUsageMap()` function that calculates daily credit consumption per profile by comparing today's `credits_used` with previous day's last record from `credits_history`
- [x] 8.3.2 Handle credit reset edge case (negative delta) by showing today's `credits_used` as daily usage
- [x] 8.3.3 Add "Daily Usage" sortable column header with sort logic
- [x] 8.4 Integrate Chart.js (CDN) with mixed chart: line for credits remaining, bar for credits consumed per interval (dual y-axis)
- [x] 8.5 Implement time range filtering logic: calculate date cutoff for week/month/3months/6months/year, filter SQL query by `extracted_at`
- [x] 8.6 Implement daily deduplication: by default GROUP BY date and take last record per day per profile (show date only); when detailed toggle is on, show all records with full datetime
- [x] 8.7 Implement account checkbox selection: unselect all = aggregated view; select accounts = one line per account on chart
- [x] 8.8 Highlight weekend dates on chart using chartjs-plugin-annotation
- [x] 8.9 Style the dashboard with basic CSS (responsive layout, table hover, header controls styled for dark background)
- [x] 8.10 Adjust grid layout to 3fr/4fr ratio and responsive breakpoint to 1100px to accommodate additional columns without layout overflow
- [x] 8.11 Add `white-space: nowrap` and compact font/padding to table cells to prevent text wrapping in multi-column layout

## Task 9: Integration and Final Verification

- [x] 9.1 Create `tests/test_integration.py` with end-to-end test using mocked browser
- [x] 9.2 Verify all property tests pass with `pytest tests/ -v`
- [x] 9.3 Add README.md with usage instructions, requirements, and example commands (including web dashboard startup)

## Task 10: Retry Queue và Error Logging

- [x] 10.1 Add retry queue logic to `src/main.py`: extract `process_profile()` helper, implement retry loop with max 5 attempts and 2s delay
- [x] 10.2 Add `log_persistent_failure()` function to write errors to `scraper_errors.log`
- [x] 10.3 Add `scrape_errors` table to `src/database.py` schema (id, profile_name, error_message, attempts, failed_at)
- [x] 10.4 Add `save_error()` method to `DatabaseWriter` class
- [x] 10.5 Add error warning banner to `dashboard/index.html` that queries `scrape_errors` table and displays recent errors
- [x] 10.6 Update `tests/test_integration.py` with retry logic tests (retry succeeds, retry exhausted, mixed)
- [x] 10.7 Add `TestSaveError` tests to `tests/test_database.py` for scrape_errors table and save_error method
- [x] 10.8 Update README.md with error handling documentation
