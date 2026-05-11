# Kiro Account Scraper

A Python CLI tool that automates extracting account information from the Kiro.dev Account Settings page. It uses Selenium WebDriver to launch Chrome with pre-logged-in profiles, navigates to the account settings page, extracts account data (email, user ID, credits, plan, reset date), and stores results in a SQLite database.

## Requirements

- Python 3.9+
- Google Chrome browser
- ChromeDriver (matching your Chrome version)
- Chrome profiles already logged in to kiro.dev

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd kiro-account-scraper
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure ChromeDriver is installed and available in your PATH. You can download it from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads) or install via your package manager.

## Setup

No additional setup needed beyond installing dependencies. Chrome profiles are managed automatically in a local `chrome_profiles/` directory.

On first run, use `--login` mode to log in to each profile manually. Subsequent runs reuse saved sessions.

## Usage

Run the scraper for 5 profiles:

```bash
python -m src.main 5
```

First-time login (opens browser for manual login):

```bash
python -m src.main 5 --login
```

Specify a custom database path:

```bash
python -m src.main 5 --db-path /path/to/my_accounts.db
```

Run headless (after profiles are already logged in):

```bash
python -m src.main 5 --headless
```

### Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `num_profiles` | Number of profiles to process | (required) |
| `--db-path` | Path to the SQLite database file | `dashboard/kiro_accounts.db` |
| `--profiles-dir` | Directory to store Chrome profiles | `chrome_profiles` |
| `--headless` | Run Chrome in headless mode | `False` |
| `--login` | Login mode: open browser for manual login | `False` |

## Web Dashboard

The project includes a static HTML dashboard for visualizing account data and credits history.

### Opening the Dashboard

Option 1 — Open directly in your browser:

```bash
# Copy the database to the dashboard directory first
cp kiro_accounts.db dashboard/

# Then open the HTML file
open dashboard/index.html        # macOS
xdg-open dashboard/index.html   # Linux
start dashboard\index.html       # Windows
```

Option 2 — Use a local HTTP server (recommended for proper file fetching):

```bash
python -m http.server 8000 --directory dashboard
```

Then open http://localhost:8000 in your browser.

### Dashboard Features

- **Accounts table**: Shows all scraped accounts with email, plan, credits used/total, and last extraction time
- **Credits chart**: Displays credits usage over time using Chart.js
- **Account filtering**: Click an account row to view its individual credits history
- **Time range selector**: Filter chart data by 1 week, 1 month, 3 months (default), 6 months, or 1 year
- **Detailed toggle**: Show all records per day or only the last record of each day

## Crontab (Auto-run every 1 hour)

To schedule the scraper to run automatically every hour, add the following crontab entry:

```bash
crontab -e
```

Then add this line:

```
0 * * * * cd /path/to/kiro-account-scraper && python -m src.main 24 --headless >> /tmp/kiro_scraper.log 2>&1
```

Replace `/path/to/kiro-account-scraper` with the actual path to your project directory.

This will run `python -m src.main 24 --headless` every hour (at minute 0 of every hour).

## Running Tests

Run the full test suite:

```bash
pytest tests/ -v
```

Run only integration tests:

```bash
pytest tests/test_integration.py -v
```

Run only property-based tests:

```bash
pytest tests/ -v -k "property"
```

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point and orchestrator
│   ├── profile_reader.py    # Reads Chrome profile paths from file
│   ├── browser.py           # Launches Chrome with specified profile
│   ├── navigator.py         # Navigates to Account Settings page
│   ├── extractor.py         # Extracts account data from DOM
│   ├── database.py          # SQLite database operations
│   └── reporter.py          # Progress and summary reporting
├── tests/
│   ├── __init__.py
│   ├── test_profile_reader.py
│   ├── test_extractor.py
│   ├── test_database.py
│   ├── test_browser.py
│   ├── test_reporter.py
│   └── test_integration.py
├── dashboard/
│   └── index.html           # Static web dashboard
├── requirements.txt         # Python dependencies
├── scraper_errors.log       # Error log for persistent failures (auto-generated)
└── README.md
```

## How It Works

1. **Read profiles**: Parses the profile list file to get Chrome profile paths
2. **Launch browser**: Opens Chrome using each profile's `--user-data-dir`
3. **Navigate**: Goes to `https://app.kiro.dev/settings/account`
4. **Extract**: Pulls email, user ID, credits, plan name, and reset date from the page DOM
5. **Save**: Upserts account data into SQLite and appends to credits history
6. **Report**: Displays progress and a final summary of successes/failures

## Error Handling

- If a profile fails during extraction (browser crash, timeout, DOM error), it is added to a **retry queue**
- The retry queue re-attempts failed profiles up to **5 times**
- Between retries, there is a short delay (2 seconds)
- If a profile still fails after all 5 attempts:
  - The error is logged to `scraper_errors.log` with timestamp, profile name, and error details
  - The error is saved to the `scrape_errors` table in the SQLite database
- The scraper always continues to the next profile after an error (no single failure stops the batch)
- The web dashboard displays a **warning banner** showing recent scraping errors from the database
