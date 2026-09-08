# Competitive Price Monitor

An automated competitive price monitoring system built with Python, Playwright, SQLite, Telegram alerts, and Windows Task Scheduler.

The project scrapes product prices on a recurring schedule, stores historical snapshots, detects significant price changes, sends alerts, handles scraper failures, and records operational run history.

## Features

- Automated browser-based scraping with Playwright
- Multi-page pagination
- Monitors up to 100 products per configured run
- SQLite price-history storage
- Current vs previous price comparison
- Configurable percentage-change threshold
- Telegram notifications for significant changes
- Minor price-change filtering
- Retry and timeout handling
- Partial scraper failure detection
- Run-history auditing
- Production health reporting
- TEST and PRODUCTION data isolation
- TEST-mode Telegram suppression
- Scheduled execution with Windows Task Scheduler
- Runtime logging
- Process exit codes for scheduler monitoring

## Tech Stack

- Python
- Playwright
- SQLite
- JSON configuration
- Telegram Bot API
- Windows Task Scheduler
- Windows Batch

## Architecture

```text
Windows Task Scheduler
        |
        v
run_monitor.bat
        |
        v
price_monitor.py
        |
        +----------------------+
        |                      |
        v                      v
Playwright Scraper         config.json
        |
        v
Pagination
        |
        v
Product Data
        |
        v
SQLite
        |
        +----------------------+
        |                      |
        v                      v
price_history            run_history
        |
        v
Price Comparison
        |
        v
Threshold Detection
        |
        v
Telegram Alerts
```

## Workflow

Each production run performs the following process:

1. Load configuration.
2. Create a `RUNNING` audit record.
3. Launch Chromium through Playwright.
4. Scrape configured pages.
5. Retry failed page loads.
6. Parse product names, prices, and URLs.
7. Save price snapshots to SQLite.
8. Compare current prices against the previous run.
9. Calculate percentage price changes.
10. Identify significant increases or decreases.
11. Send eligible Telegram alerts.
12. Store final run metrics and status.
13. Return an appropriate process exit code.

## Price Change Logic

The default significant-change threshold is:

```text
5%
```

Example behavior:

```text
Previous price: £51.00
Current price:  £51.77
Change:         +1.51%
Detected:       Yes
Significant:    No
Telegram:       No
```

A significant change:

```text
Previous price: £48.00
Current price:  £51.77
Change:         +7.85%
Detected:       Yes
Significant:    Yes
Telegram:       Yes in PRODUCTION
```

## Resilience

The scraper includes several failure-handling mechanisms:

- Configurable page timeout
- Multiple retry attempts
- Retry delay
- Minimum-product validation
- Individual product parsing protection
- Partial-run preservation
- Structured failure statuses
- Non-zero exit codes for failed runs

For example:

```text
Page 3 fails
    |
    v
Retry attempt 1
    |
    v
Retry attempt 2
    |
    v
Retry attempt 3
    |
    v
Failure recorded
    |
    v
Previously scraped products preserved
    |
    v
Run status: PARTIAL_FAILURE
    |
    v
Exit code: 1
```

## TEST and PRODUCTION Isolation

Test runs are separated from production runs.

```text
PRODUCTION
    |
    +-- Production price history
    +-- Production run history
    +-- Real Telegram delivery
TEST
    |
    +-- Test price history
    +-- Test run history
    +-- Telegram delivery suppressed
```

The run mode is controlled by:

```text
PRICE_MONITOR_RUN_TYPE
```

Valid values are:

```text
PRODUCTION
TEST
```

If no value is provided, the monitor defaults to `PRODUCTION`.

### Telegram Test Safety

TEST mode can still detect significant price changes and record them for validation, but external Telegram delivery is blocked.

Verified test result:

```text
Run type: TEST
Alerts detected: 1
Telegram eligible: 1
Telegram sent: 0
Telegram failed: 0
Exit code: 0
```

## Run Auditing

Every monitor execution creates a record in the SQLite `run_history` table.

Tracked information includes:

- Run ID
- Source
- Start time
- Finish time
- Run status
- Run type
- Expected pages
- Successful pages
- Products scraped
- Failed pages
- Price changes detected
- Telegram-eligible alerts
- Telegram alerts sent
- Telegram failures
- Exit code
- Error message

Example verified production run:

```text
Run ID: 10
Run type: PRODUCTION
Status: SUCCESS
Pages expected: 5
Pages successful: 5
Products scraped: 100
Failed pages: []
Alerts detected: 0
Telegram eligible: 0
Telegram sent: 0
Telegram failed: 0
Exit code: 0
```

## Health Reporting

The included `monitor_health.py` script provides operational information such as:

- Production run count
- Production success rate
- Partial failures
- Scraper failures
- Telegram failures
- Average runtime
- Average products processed
- Total products processed
- Latest production run
- Last successful production run
- TEST-run statistics

Run it with:

```bat
.venv\Scripts\python.exe monitor_health.py
```

## Configuration

Scraper behavior is controlled by `config.json`.

Configuration includes:

- Source website
- Currency
- CSS selectors
- Attribute selectors
- Price symbol
- Pagination
- Maximum pages
- Significant-change threshold
- Telegram alert behavior
- Page timeout
- Retry attempts
- Retry delay
- Minimum products per page

This keeps most operational settings separate from application logic.

## Installation

Clone the repository:

```bat
git clone https://github.com/maxwellmaxtoy/competitive-price-monitor.git
cd competitive-price-monitor
```

Create a virtual environment:

```bat
python -m venv .venv
```

Install the Python dependencies:

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install the Playwright Chromium browser:

```bat
.venv\Scripts\python.exe -m playwright install chromium
```

## Telegram Configuration

Telegram credentials are not stored in the source code.

Set these environment variables on Windows:

```bat
setx TELEGRAM_BOT_TOKEN "YOUR_BOT_TOKEN"
setx TELEGRAM_CHAT_ID "YOUR_CHAT_ID"
```

Open a new terminal after using `setx`.

Do not commit real credentials to Git.

## Running the Monitor

Run directly:

```bat
.venv\Scripts\python.exe price_monitor.py
```

Or use:

```bat
run_monitor.bat
```

The batch file automatically runs from the project directory and propagates the Python process exit code.

## Scheduling

The project was tested with Windows Task Scheduler.

The portfolio deployment schedule runs the monitor:

```text
Every 6 hours
```

The scheduled task launches:

```text
run_monitor.bat
```

The batch script executes the project's virtual-environment Python interpreter directly.

## Logging

Scheduled execution output is written to:

```text
logs/monitor.log
```

Example:

```text
Run ID: 11
Run type: PRODUCTION
Pages scraped successfully: 5
Total products scraped: 100
Inserted: 100 PRODUCTION products into SQLite
No price changes detected.
Run status: SUCCESS
Run finished successfully
```

The `logs` directory is intentionally excluded from Git.

## Database

Runtime data is stored locally in:

```text
price_monitor.db
```

The database contains two primary tables:

```text
price_history
run_history
```

The database is excluded from Git because it contains runtime-generated data.

## Security

The repository uses `.gitignore` to exclude local or sensitive files such as:

```text
.venv/
.env
*.db
logs/
archive/
__pycache__/
```

Telegram credentials are loaded from environment variables rather than being hard-coded.

## Testing

The project includes dedicated validation scripts for important failure and safety scenarios.

### Partial Failure Test

```bat
.venv\Scripts\python.exe test_partial_failure.py
```

This intentionally causes one scraper page to fail and verifies that:

- Retry logic executes
- Successfully scraped products are preserved
- The failed page is recorded
- The run is classified as `PARTIAL_FAILURE`
- The process returns exit code `1`

### Telegram Suppression Test

```bat
.venv\Scripts\python.exe test_telegram_suppression.py
```

This generates a significant TEST price change and verifies that:

- The price change is detected
- It is classified as significant
- It is eligible for Telegram
- No real Telegram message is sent
- TEST data remains isolated from PRODUCTION

## Verified Results

The final production verification successfully processed:

```text
Run type: PRODUCTION
Pages successful: 5/5
Products scraped: 100
Failed pages: 0
Exit code: 0
```

The TEST safety verification successfully produced:

```text
Significant price changes detected: 1
Telegram eligible: 1
Telegram sent: 0
Exit code: 0
```

## What This Project Demonstrates

This project demonstrates practical experience with:

- Python automation
- Browser automation
- Web scraping
- SQLite
- SQL queries
- API integration
- Configuration-driven software
- Retry strategies
- Failure handling
- Logging
- Environment variables
- Test/production isolation
- Scheduled automation
- Operational monitoring
- ETL-style data workflows

## Project Status

**Version 1.0 — Complete**

Built as a portfolio project demonstrating an end-to-end automated competitive price monitoring workflow.
