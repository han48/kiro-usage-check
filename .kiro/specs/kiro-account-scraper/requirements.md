# Requirements Document

## Introduction

Công cụ Python tự động hóa việc trích xuất thông tin tài khoản từ trang "Account Settings" của Kiro.dev. Tool sử dụng các Chrome profile đã đăng nhập sẵn để mở trang web, lấy thông tin email, user ID và credits còn lại, sau đó lưu kết quả vào cơ sở dữ liệu SQLite. Tool xử lý hàng loạt các profile được định nghĩa trong file cấu hình.

## Glossary

- **Scraper**: Chương trình Python chính thực hiện việc trích xuất thông tin tài khoản từ trang web Kiro.dev
- **Chrome_Profile**: Một profile trình duyệt Chrome được quản lý trong thư mục local (`chrome_profiles/`), mỗi profile tương ứng một tài khoản Kiro.dev
- **Account_Info**: Tập hợp thông tin tài khoản bao gồm email, user ID, credits used, credits total, plan name và reset date
- **Database**: Cơ sở dữ liệu SQLite lưu trữ kết quả trích xuất từ tất cả các profile
- **Account_Settings_Page**: Trang "Account Settings | Kiro Web" trên kiro.dev chứa thông tin tài khoản người dùng

## Requirements

### Requirement 1: Quản lý Chrome Profile

**User Story:** As a user, I want to specify the number of profiles to process, so that the tool can manage multiple accounts in batch using auto-generated local profiles.

#### Acceptance Criteria

1. WHEN the Scraper is started with a `num_profiles` argument, THE Scraper SHALL generate profile names (Profile_1, Profile_2, ..., Profile_N)
2. THE Scraper SHALL store Chrome profiles in a local `chrome_profiles/` directory (configurable via `--profiles-dir`)
3. IF `num_profiles` is less than 1, THEN THE Scraper SHALL display an error message and exit gracefully
4. WHEN `--login` flag is provided, THE Scraper SHALL open Chrome for each profile and wait for manual login

### Requirement 2: Khởi chạy Chrome với Profile có sẵn

**User Story:** As a user, I want the tool to launch Chrome using my pre-logged-in profiles, so that no manual login is required.

#### Acceptance Criteria

1. WHEN processing a Chrome_Profile, THE Scraper SHALL launch a Chrome browser instance using the specified profile directory via Selenium WebDriver
2. THE Scraper SHALL use the `--user-data-dir` Chrome argument to load the specified Chrome_Profile
3. IF the Chrome_Profile directory does not exist, THEN THE Scraper SHALL log an error for that profile and continue processing the next profile
4. WHEN a Chrome browser instance is no longer needed, THE Scraper SHALL close the browser instance and release associated resources

### Requirement 3: Điều hướng đến trang Account Settings

**User Story:** As a user, I want the tool to automatically navigate to the Account Settings page, so that account information can be extracted.

#### Acceptance Criteria

1. WHEN a Chrome browser instance is launched successfully, THE Scraper SHALL navigate to the Account_Settings_Page URL
2. WHEN the Account_Settings_Page is loaded, THE Scraper SHALL wait for the page content to be fully rendered before extracting data
3. IF the Account_Settings_Page fails to load within 30 seconds, THEN THE Scraper SHALL log a timeout error for that profile and proceed to the next profile

### Requirement 4: Trích xuất thông tin tài khoản

**User Story:** As a user, I want to extract email, user ID, credits, plan, and reset date from the Account Settings page, so that I can monitor my accounts.

#### Acceptance Criteria

1. WHEN the Account_Settings_Page is fully loaded, THE Scraper SHALL extract the email address using DOM selector `p[data-variant="semibold"][data-size="sm"]`
2. WHEN the Account_Settings_Page is fully loaded, THE Scraper SHALL extract the user ID from the meta tag `meta[name="user-id"]`
3. WHEN the Account_Settings_Page is fully loaded, THE Scraper SHALL extract credits used and credits total from the element `p[aria-label*="credits used out of"]` using the aria-label attribute
4. WHEN the Account_Settings_Page is fully loaded, THE Scraper SHALL extract the plan name from the element `.acme-Badge-label`
5. WHEN the Account_Settings_Page is fully loaded, THE Scraper SHALL extract the reset date from the text containing "resets on" near the "Estimated Usage" heading
6. IF any Account_Info field cannot be found on the page, THEN THE Scraper SHALL log a warning indicating which field is missing and set that field to null

### Requirement 5: Lưu kết quả vào SQLite

**User Story:** As a user, I want results stored in a SQLite database, so that I can query and analyze account data easily.

#### Acceptance Criteria

1. THE Database SHALL contain a table `accounts` with columns for: profile name, email, user ID, credits used, credits total, plan name, reset date, and extraction timestamp
2. THE Database SHALL contain a table `credits_history` that stores each extraction as a new record with: profile name, credits used, credits total, plan name, and extraction timestamp
3. WHEN Account_Info is successfully extracted, THE Scraper SHALL upsert the `accounts` table and INSERT a new record into `credits_history`
4. WHEN the Scraper is started, THE Database SHALL be created automatically if it does not already exist
5. IF a record for the same profile already exists in the `accounts` table, THEN THE Scraper SHALL update the existing record with the new information

### Requirement 6: Xử lý hàng loạt và báo cáo

**User Story:** As a user, I want the tool to process all profiles sequentially and report results, so that I can see the overall status.

#### Acceptance Criteria

1. THE Scraper SHALL process each Chrome_Profile sequentially
2. WHEN all profiles have been processed, THE Scraper SHALL display a summary showing the total number of profiles processed, successful extractions, and failures
3. IF an error occurs while processing one Chrome_Profile, THEN THE Scraper SHALL continue processing the remaining profiles
4. WHEN processing each Chrome_Profile, THE Scraper SHALL display progress information indicating the current profile being processed

### Requirement 8: Web Dashboard để xem thông tin và biểu đồ

**User Story:** As a user, I want a web dashboard to view all accounts and their credits history charts, so that I can visually monitor usage trends.

#### Acceptance Criteria

1. THE tool SHALL provide a static HTML dashboard (`dashboard/index.html`) that fetches the SQLite DB file from the same public directory
2. THE dashboard SHALL display a table of all accounts on the left panel showing: email, plan, credits used/total, last extracted time
3. WHEN the dashboard loads, THE right panel SHALL display a chart showing total credits remaining and total credits across all accounts over time
4. WHEN a user clicks on an account in the left panel, THE right panel SHALL display the credits history chart for that specific account
5. THE chart SHALL default to showing data from the last 3 months
6. WHEN displaying daily data, THE dashboard SHALL show only the last record of each day by default
7. THE dashboard SHALL provide a "detailed" toggle that shows all records within a day when enabled
8. THE dashboard SHALL provide time range selection options: 1 week, 1 month, 3 months (default), 6 months, 1 year
9. WHEN a time range is selected, THE chart SHALL update to show data within the selected period
10. THE dashboard SHALL display a warning banner showing recent scraping errors from the `scrape_errors` table in the database
11. THE dashboard SHALL provide an email filter input above the accounts table that filters rows by email substring match in real-time

### Requirement 9: Retry Queue và Error Logging

**User Story:** As a user, I want failed profile extractions to be retried automatically and persistent failures logged, so that transient errors don't cause data loss and I'm aware of persistent issues.

#### Acceptance Criteria

1. IF a profile fails during extraction (browser crash, timeout, DOM error), THEN THE Scraper SHALL add that profile to a retry queue
2. THE Scraper SHALL re-attempt failed profiles up to 5 times
3. BETWEEN retries, THE Scraper SHALL wait 2 seconds before the next attempt
4. IF a profile still fails after all 5 retry attempts, THEN THE Scraper SHALL log the error to `scraper_errors.log` with timestamp, profile name, and error details
5. IF a profile still fails after all 5 retry attempts, THEN THE Scraper SHALL save the error to the `scrape_errors` table in the SQLite database
6. THE Database SHALL contain a table `scrape_errors` with columns: id, profile_name, error_message, attempts, failed_at
7. THE Scraper SHALL always continue to the next profile after an error (no single failure stops the batch)
