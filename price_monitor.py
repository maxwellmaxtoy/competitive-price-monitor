from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from datetime import datetime
import sqlite3
import urllib.request
import urllib.parse
import traceback
import json
import os
import sys
import time


# =========================================
# LOAD CONFIGURATION
# =========================================

CONFIG_FILE = "config.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as file:
    config = json.load(file)


DATABASE = config["database"]

SIGNIFICANT_CHANGE_PERCENT = float(
    config["significant_change_percent"]
)

TELEGRAM_ALERT_ONLY_SIGNIFICANT = config.get(
    "telegram_alert_only_significant",
    True
)


# =========================================
# RUN TYPE
# =========================================

RUN_TYPE = os.getenv(
    "PRICE_MONITOR_RUN_TYPE",
    "PRODUCTION"
).upper()


if RUN_TYPE not in (
    "PRODUCTION",
    "TEST"
):
    RUN_TYPE = "PRODUCTION"


# =========================================
# SOURCE SETTINGS
# =========================================

SOURCE = config["source"]

SOURCE_NAME = SOURCE["name"]
SOURCE_URL = SOURCE["url"]
CURRENCY = SOURCE["currency"]
PRICE_SYMBOL = SOURCE["price_symbol"]

SELECTORS = SOURCE["selectors"]
ATTRIBUTES = SOURCE["attributes"]


# =========================================
# PAGINATION SETTINGS
# =========================================

PAGINATION = SOURCE.get(
    "pagination",
    {}
)

PAGINATION_ENABLED = PAGINATION.get(
    "enabled",
    False
)

NEXT_SELECTOR = PAGINATION.get(
    "next_selector",
    ""
)

MAX_PAGES = int(
    PAGINATION.get(
        "max_pages",
        1
    )
)


# =========================================
# RESILIENCE SETTINGS
# =========================================

RESILIENCE = SOURCE.get(
    "resilience",
    {}
)

PAGE_TIMEOUT_MS = int(
    RESILIENCE.get(
        "page_timeout_ms",
        30000
    )
)

RETRY_ATTEMPTS = max(
    1,
    int(
        RESILIENCE.get(
            "retry_attempts",
            3
        )
    )
)

RETRY_DELAY_SECONDS = float(
    RESILIENCE.get(
        "retry_delay_seconds",
        3
    )
)

MINIMUM_PRODUCTS_PER_PAGE = max(
    1,
    int(
        RESILIENCE.get(
            "minimum_products_per_page",
            1
        )
    )
)


# =========================================
# TELEGRAM SETTINGS
# =========================================

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)


# =========================================
# DATABASE SCHEMA
# =========================================

def ensure_database_schema():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    # -------------------------------------
    # PRICE HISTORY TABLE
    # -------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            source TEXT NOT NULL,
            product_url TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            run_type TEXT NOT NULL DEFAULT 'PRODUCTION'
        )
    """)


    # -------------------------------------
    # RUN HISTORY TABLE
    # -------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            pages_expected INTEGER,
            pages_successful INTEGER DEFAULT 0,
            products_scraped INTEGER DEFAULT 0,
            failed_pages TEXT,
            alerts_detected INTEGER DEFAULT 0,
            telegram_eligible INTEGER DEFAULT 0,
            telegram_sent INTEGER DEFAULT 0,
            telegram_failed INTEGER DEFAULT 0,
            exit_code INTEGER,
            error_message TEXT,
            run_type TEXT NOT NULL DEFAULT 'PRODUCTION'
        )
    """)


    # -------------------------------------
    # MIGRATE PRICE HISTORY IF NEEDED
    # -------------------------------------

    cursor.execute("""
        PRAGMA table_info(price_history)
    """)

    price_columns = [
        column[1]
        for column in cursor.fetchall()
    ]


    if "run_type" not in price_columns:

        cursor.execute("""
            ALTER TABLE price_history
            ADD COLUMN run_type TEXT
            NOT NULL
            DEFAULT 'PRODUCTION'
        """)


    # -------------------------------------
    # MIGRATE RUN HISTORY IF NEEDED
    # -------------------------------------

    cursor.execute("""
        PRAGMA table_info(run_history)
    """)

    run_columns = [
        column[1]
        for column in cursor.fetchall()
    ]


    if "run_type" not in run_columns:

        cursor.execute("""
            ALTER TABLE run_history
            ADD COLUMN run_type TEXT
            NOT NULL
            DEFAULT 'PRODUCTION'
        """)


    connection.commit()

    connection.close()


# =========================================
# CREATE RUN HISTORY
# =========================================

def create_run_history(
    started_at,
    pages_expected
):

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    cursor.execute("""
        INSERT INTO run_history (
            source,
            started_at,
            status,
            pages_expected,
            pages_successful,
            products_scraped,
            failed_pages,
            alerts_detected,
            telegram_eligible,
            telegram_sent,
            telegram_failed,
            run_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        SOURCE_NAME,
        started_at,
        "RUNNING",
        pages_expected,
        0,
        0,
        "[]",
        0,
        0,
        0,
        0,
        RUN_TYPE
    ))


    run_id = cursor.lastrowid


    connection.commit()

    connection.close()


    return run_id


# =========================================
# FINISH RUN HISTORY
# =========================================

def finish_run_history(
    run_id,
    status,
    pages_successful,
    products_scraped,
    failed_pages,
    alerts_detected,
    telegram_eligible,
    telegram_sent,
    telegram_failed,
    exit_code,
    error_message=None
):

    finished_at = (
        datetime.now().isoformat()
    )


    failed_page_numbers = [
        failure["page_number"]
        for failure in failed_pages
    ]


    failed_pages_json = json.dumps(
        failed_page_numbers
    )


    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    cursor.execute("""
        UPDATE run_history
        SET
            finished_at = ?,
            status = ?,
            pages_successful = ?,
            products_scraped = ?,
            failed_pages = ?,
            alerts_detected = ?,
            telegram_eligible = ?,
            telegram_sent = ?,
            telegram_failed = ?,
            exit_code = ?,
            error_message = ?
        WHERE id = ?
    """, (
        finished_at,
        status,
        pages_successful,
        products_scraped,
        failed_pages_json,
        alerts_detected,
        telegram_eligible,
        telegram_sent,
        telegram_failed,
        exit_code,
        error_message,
        run_id
    ))


    connection.commit()

    connection.close()


# =========================================
# SEND TELEGRAM MESSAGE
# =========================================

def send_telegram_message(message):

    if not BOT_TOKEN:

        print(
            "Telegram bot token is missing."
        )

        return False


    if not CHAT_ID:

        print(
            "Telegram chat ID is missing."
        )

        return False


    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )


    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message
    }).encode(
        "utf-8"
    )


    request = urllib.request.Request(
        url,
        data=data
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            result = json.loads(
                response
                .read()
                .decode("utf-8")
            )


        if result.get("ok"):

            print(
                "Telegram alert sent successfully."
            )

            return True


        print(
            "Telegram API returned an error."
        )

        print(result)

        return False


    except Exception as error:

        print(
            "Error sending Telegram message:"
        )

        print(error)

        return False


# =========================================
# LOAD PAGE WITH RETRIES
# =========================================

def load_page_with_retries(
    page,
    url,
    page_number
):

    for attempt in range(
        1,
        RETRY_ATTEMPTS + 1
    ):

        try:

            print(
                f"Loading page {page_number} "
                f"(attempt {attempt}/"
                f"{RETRY_ATTEMPTS})..."
            )


            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT_MS
            )


            products = page.locator(
                SELECTORS["product"]
            )


            product_count = (
                products.count()
            )


            if (
                product_count
                < MINIMUM_PRODUCTS_PER_PAGE
            ):

                raise RuntimeError(
                    f"Only {product_count} products "
                    f"found. Minimum required: "
                    f"{MINIMUM_PRODUCTS_PER_PAGE}"
                )


            print(
                f"Page {page_number} "
                f"loaded successfully."
            )


            return True


        except Exception as error:

            print(
                f"Page {page_number} "
                f"attempt {attempt} failed:"
            )

            print(error)


            if attempt < RETRY_ATTEMPTS:

                print(
                    f"Retrying in "
                    f"{RETRY_DELAY_SECONDS} "
                    f"seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )


    print(
        f"ERROR: Page {page_number} "
        f"failed after "
        f"{RETRY_ATTEMPTS} attempts."
    )


    return False


# =========================================
# SCRAPE CURRENT PAGE
# =========================================

def scrape_current_page(
    page,
    page_number,
    scraped_at
):

    results = []


    products = page.locator(
        SELECTORS["product"]
    )


    product_count = (
        products.count()
    )


    print(
        f"Products found on page "
        f"{page_number}: "
        f"{product_count}"
    )


    for i in range(
        product_count
    ):

        try:

            product = products.nth(i)


            name = product.locator(
                SELECTORS["name"]
            ).get_attribute(
                ATTRIBUTES["name"]
            )


            price_text = product.locator(
                SELECTORS["price"]
            ).text_content()


            relative_url = (
                product.locator(
                    SELECTORS["link"]
                ).get_attribute(
                    ATTRIBUTES["link"]
                )
            )


            if not name:

                raise ValueError(
                    "Product name is missing."
                )


            if price_text is None:

                raise ValueError(
                    "Product price is missing."
                )


            price = float(
                price_text
                .replace(
                    PRICE_SYMBOL,
                    ""
                )
                .strip()
            )


            if relative_url:

                product_url = urljoin(
                    page.url,
                    relative_url
                )

            else:

                product_url = page.url


            results.append({
                "product_name":
                    name,

                "price":
                    price,

                "currency":
                    CURRENCY,

                "source":
                    SOURCE_NAME,

                "product_url":
                    product_url,

                "scraped_at":
                    scraped_at,

                "run_type":
                    RUN_TYPE
            })


        except Exception as error:

            print(
                f"WARNING: Could not parse "
                f"product #{i + 1} "
                f"on page {page_number}:"
            )

            print(error)


    return results


# =========================================
# SCRAPE ALL PAGES
# =========================================

def scrape_products():

    results = []

    pages_scraped = 0

    failed_pages = []


    scraped_at = (
        datetime.now().isoformat()
    )


    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )


        page = browser.new_page()


        current_page = 1

        current_url = SOURCE_URL


        while True:

            print()

            print(
                f"Scraping page "
                f"{current_page}..."
            )


            page_loaded = (
                load_page_with_retries(
                    page,
                    current_url,
                    current_page
                )
            )


            if not page_loaded:

                failed_pages.append({
                    "page_number":
                        current_page,

                    "url":
                        current_url
                })

                break


            page_products = (
                scrape_current_page(
                    page,
                    current_page,
                    scraped_at
                )
            )


            if (
                len(page_products)
                < MINIMUM_PRODUCTS_PER_PAGE
            ):

                print(
                    f"ERROR: Page "
                    f"{current_page} produced "
                    f"only {len(page_products)} "
                    f"valid products."
                )


                failed_pages.append({
                    "page_number":
                        current_page,

                    "url":
                        current_url
                })


                break


            results.extend(
                page_products
            )


            pages_scraped += 1


            if not PAGINATION_ENABLED:

                break


            if (
                current_page
                >= MAX_PAGES
            ):

                print(
                    f"Reached max_pages "
                    f"limit: {MAX_PAGES}"
                )

                break


            next_link = page.locator(
                NEXT_SELECTOR
            )


            if next_link.count() == 0:

                print(
                    "No next page found."
                )

                break


            try:

                next_href = (
                    next_link
                    .first
                    .get_attribute("href")
                )


            except Exception as error:

                print(
                    "ERROR: Could not read "
                    "next page link:"
                )

                print(error)


                failed_pages.append({
                    "page_number":
                        current_page + 1,

                    "url":
                        "unknown"
                })


                break


            if not next_href:

                print(
                    "No next page URL found."
                )

                break


            current_url = urljoin(
                page.url,
                next_href
            )


            current_page += 1


        browser.close()


    return (
        results,
        pages_scraped,
        failed_pages
    )


# =========================================
# SAVE PRICE HISTORY
# =========================================

def save_to_database(products):

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    for product in products:

        cursor.execute("""
            INSERT INTO price_history (
                product_name,
                price,
                currency,
                source,
                product_url,
                scraped_at,
                run_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product["product_name"],
            product["price"],
            product["currency"],
            product["source"],
            product["product_url"],
            product["scraped_at"],
            product["run_type"]
        ))


    connection.commit()

    connection.close()


# =========================================
# COMPARE PRICES
# =========================================

def compare_prices(products):

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    alerts = []


    for product in products:

        cursor.execute("""
            SELECT
                price,
                product_url,
                scraped_at
            FROM price_history
            WHERE product_name = ?
            AND source = ?
            AND run_type = ?
            ORDER BY
                scraped_at DESC,
                id DESC
            LIMIT 2
        """, (
            product["product_name"],
            product["source"],
            product["run_type"]
        ))


        rows = cursor.fetchall()


        if len(rows) < 2:

            continue


        current_price = rows[0][0]

        previous_price = rows[1][0]

        product_url = rows[0][1]

        detected_at = rows[0][2]


        if previous_price == 0:

            continue


        price_difference = (
            current_price
            - previous_price
        )


        percentage_change = (
            price_difference
            / previous_price
        ) * 100


        is_significant = False


        if (
            percentage_change
            >= SIGNIFICANT_CHANGE_PERCENT
        ):

            status = (
                "SIGNIFICANT PRICE INCREASE"
            )

            is_significant = True


        elif (
            percentage_change
            <= -SIGNIFICANT_CHANGE_PERCENT
        ):

            status = (
                "SIGNIFICANT PRICE DECREASE"
            )

            is_significant = True


        elif percentage_change > 0:

            status = "PRICE INCREASE"


        elif percentage_change < 0:

            status = "PRICE DECREASE"


        else:

            continue


        alerts.append({
            "product_name":
                product["product_name"],

            "current_price":
                current_price,

            "previous_price":
                previous_price,

            "price_difference":
                price_difference,

            "percentage_change":
                percentage_change,

            "status":
                status,

            "is_significant":
                is_significant,

            "product_url":
                product_url,

            "detected_at":
                detected_at,

            "run_type":
                product["run_type"]
        })


    connection.close()


    return alerts


# =========================================
# PRINT PRICE CHANGES
# =========================================

def print_alerts(alerts):

    if not alerts:

        print(
            "No price changes detected."
        )

        return


    print()
    print("PRICE CHANGES DETECTED")
    print("======================")


    for alert in alerts:

        difference = (
            alert["price_difference"]
        )

        percentage = (
            alert["percentage_change"]
        )


        if difference > 0:

            difference_text = (
                f"+{PRICE_SYMBOL}"
                f"{difference:.2f}"
            )

        else:

            difference_text = (
                f"-{PRICE_SYMBOL}"
                f"{abs(difference):.2f}"
            )


        if percentage > 0:

            percentage_text = (
                f"+{percentage:.2f}%"
            )

        else:

            percentage_text = (
                f"{percentage:.2f}%"
            )


        print(
            f"Product: "
            f"{alert['product_name']}"
        )

        print(
            f"Current price: "
            f"{PRICE_SYMBOL}"
            f"{alert['current_price']:.2f}"
        )

        print(
            f"Previous price: "
            f"{PRICE_SYMBOL}"
            f"{alert['previous_price']:.2f}"
        )

        print(
            f"Price difference: "
            f"{difference_text}"
        )

        print(
            f"Percentage change: "
            f"{percentage_text}"
        )

        print(
            f"Status: "
            f"{alert['status']}"
        )

        print(
            f"Run type: "
            f"{alert['run_type']}"
        )

        print(
            f"URL: "
            f"{alert['product_url']}"
        )

        print(
            f"Detected at: "
            f"{alert['detected_at']}"
        )

        print(
            "----------------------"
        )


# =========================================
# BUILD TELEGRAM MESSAGE
# =========================================

def build_telegram_message(alert):

    difference = (
        alert["price_difference"]
    )

    percentage = (
        alert["percentage_change"]
    )


    if difference > 0:

        change_text = (
            f"+{PRICE_SYMBOL}"
            f"{difference:.2f}"
        )

    else:

        change_text = (
            f"-{PRICE_SYMBOL}"
            f"{abs(difference):.2f}"
        )


    if percentage > 0:

        percentage_text = (
            f"+{percentage:.2f}%"
        )

    else:

        percentage_text = (
            f"{percentage:.2f}%"
        )


    return (
        "🚨 PRICE ALERT\n\n"

        f"Product: "
        f"{alert['product_name']}\n\n"

        f"Current price: "
        f"{PRICE_SYMBOL}"
        f"{alert['current_price']:.2f}\n"

        f"Previous price: "
        f"{PRICE_SYMBOL}"
        f"{alert['previous_price']:.2f}\n"

        f"Change: "
        f"{change_text}\n"

        f"Percentage: "
        f"{percentage_text}\n\n"

        f"Status: "
        f"{alert['status']}\n\n"

        f"🔗 "
        f"{alert['product_url']}"
    )


# =========================================
# SEND TELEGRAM ALERTS
# =========================================

def send_telegram_alerts(alerts):

    # -------------------------------------
    # DETERMINE ELIGIBLE ALERTS
    # -------------------------------------

    if TELEGRAM_ALERT_ONLY_SIGNIFICANT:

        telegram_alerts = [
            alert
            for alert in alerts
            if alert["is_significant"]
        ]

    else:

        telegram_alerts = alerts


    # -------------------------------------
    # NO ELIGIBLE ALERTS
    # -------------------------------------

    if not telegram_alerts:

        if (
            alerts
            and TELEGRAM_ALERT_ONLY_SIGNIFICANT
        ):

            print(
                "No significant price changes "
                "for Telegram notification."
            )


        return {
            "success": True,
            "eligible": 0,
            "sent": 0,
            "failed": 0
        }


    # =====================================
    # TEST MODE SAFETY
    # =====================================

    if RUN_TYPE == "TEST":

        print()

        print(
            "TEST MODE: Telegram "
            "notifications suppressed."
        )

        print(
            "Eligible test alerts:",
            len(telegram_alerts)
        )

        print(
            "Real Telegram messages sent: 0"
        )


        return {
            "success": True,
            "eligible":
                len(telegram_alerts),
            "sent": 0,
            "failed": 0
        }


    # =====================================
    # PRODUCTION DELIVERY
    # =====================================

    successful_sends = 0

    failed_sends = 0


    for alert in telegram_alerts:

        message = (
            build_telegram_message(
                alert
            )
        )


        success = (
            send_telegram_message(
                message
            )
        )


        if success:

            successful_sends += 1

        else:

            failed_sends += 1


    print()

    print(
        "Telegram delivery summary:"
    )

    print(
        "Eligible alerts:",
        len(telegram_alerts)
    )

    print(
        "Successfully sent:",
        successful_sends
    )

    print(
        "Failed:",
        failed_sends
    )


    return {
        "success":
            failed_sends == 0,

        "eligible":
            len(telegram_alerts),

        "sent":
            successful_sends,

        "failed":
            failed_sends
    }


# =========================================
# FAILURE SUMMARY
# =========================================

def print_failure_summary(
    failed_pages
):

    if not failed_pages:

        return


    print()
    print("SCRAPER FAILURE SUMMARY")
    print("=======================")


    for failure in failed_pages:

        print(
            f"Failed page: "
            f"{failure['page_number']}"
        )

        print(
            f"URL: "
            f"{failure['url']}"
        )

        print(
            "-----------------------"
        )


# =========================================
# MAIN PROGRAM
# =========================================

def main():

    ensure_database_schema()


    started_at = (
        datetime.now().isoformat()
    )


    if PAGINATION_ENABLED:

        pages_expected = MAX_PAGES

    else:

        pages_expected = 1


    run_id = create_run_history(
        started_at,
        pages_expected
    )


    pages_scraped = 0

    products_scraped = 0

    failed_pages = []

    alerts_detected = 0

    telegram_eligible = 0

    telegram_sent = 0

    telegram_failed = 0


    print(
        f"Run ID: {run_id}"
    )

    print(
        f"Run type: {RUN_TYPE}"
    )

    print(
        f"Competitive Price Monitor - "
        f"{SOURCE_NAME}"
    )

    print(
        f"Alert threshold: "
        f"{SIGNIFICANT_CHANGE_PERCENT:.2f}%"
    )


    if TELEGRAM_ALERT_ONLY_SIGNIFICANT:

        print(
            "Telegram alerts: "
            "significant changes only"
        )

    else:

        print(
            "Telegram alerts: "
            "all price changes"
        )


    if PAGINATION_ENABLED:

        print(
            f"Pagination: enabled "
            f"(max {MAX_PAGES} pages)"
        )

    else:

        print(
            "Pagination: disabled"
        )


    print(
        f"Retry attempts: "
        f"{RETRY_ATTEMPTS}"
    )

    print(
        f"Retry delay: "
        f"{RETRY_DELAY_SECONDS} seconds"
    )

    print(
        f"Page timeout: "
        f"{PAGE_TIMEOUT_MS} ms"
    )


    try:

        (
            products,
            pages_scraped,
            failed_pages
        ) = scrape_products()


        products_scraped = len(
            products
        )


        print()

        print(
            "Pages scraped successfully:",
            pages_scraped
        )

        print(
            "Total products scraped:",
            products_scraped
        )


        # =====================================
        # TOTAL SCRAPER FAILURE
        # =====================================

        if not products:

            print(
                "ERROR: Scraper returned "
                "zero products."
            )


            print_failure_summary(
                failed_pages
            )


            finish_run_history(
                run_id=run_id,
                status="SCRAPER_FAILURE",
                pages_successful=
                    pages_scraped,
                products_scraped=
                    products_scraped,
                failed_pages=
                    failed_pages,
                alerts_detected=0,
                telegram_eligible=0,
                telegram_sent=0,
                telegram_failed=0,
                exit_code=1,
                error_message=
                    "Scraper returned zero products."
            )


            print()

            print(
                f"Run history saved. "
                f"Run ID: {run_id}"
            )

            print(
                "Run status: "
                "SCRAPER_FAILURE"
            )

            print(
                f"Run type: {RUN_TYPE}"
            )


            return 1


        # =====================================
        # SAVE PRICE HISTORY
        # =====================================

        save_to_database(
            products
        )


        print(
            "Inserted:",
            len(products),
            f"{RUN_TYPE} products into SQLite"
        )


        # =====================================
        # PRICE COMPARISON
        # =====================================

        alerts = compare_prices(
            products
        )


        alerts_detected = len(
            alerts
        )


        print_alerts(
            alerts
        )


        # =====================================
        # TELEGRAM
        # =====================================

        telegram_result = (
            send_telegram_alerts(
                alerts
            )
        )


        telegram_eligible = (
            telegram_result["eligible"]
        )

        telegram_sent = (
            telegram_result["sent"]
        )

        telegram_failed = (
            telegram_result["failed"]
        )


        print_failure_summary(
            failed_pages
        )


        # =====================================
        # FINAL STATUS
        # =====================================

        if not telegram_result["success"]:

            status = (
                "TELEGRAM_FAILURE"
            )

            exit_code = 1

            error_message = (
                "One or more Telegram "
                "notifications failed."
            )


        elif failed_pages:

            status = (
                "PARTIAL_FAILURE"
            )

            exit_code = 1


            failed_numbers = [
                failure["page_number"]
                for failure in failed_pages
            ]


            error_message = (
                f"Failed pages: "
                f"{failed_numbers}"
            )


            print(
                "WARNING: Run completed "
                "with scraper failures."
            )

            print(
                "Valid scraped products were saved, "
                "but this run will return "
                "a failure exit code."
            )


        else:

            status = "SUCCESS"

            exit_code = 0

            error_message = None


        # =====================================
        # SAVE RUN HISTORY
        # =====================================

        finish_run_history(
            run_id=run_id,
            status=status,
            pages_successful=
                pages_scraped,
            products_scraped=
                products_scraped,
            failed_pages=
                failed_pages,
            alerts_detected=
                alerts_detected,
            telegram_eligible=
                telegram_eligible,
            telegram_sent=
                telegram_sent,
            telegram_failed=
                telegram_failed,
            exit_code=
                exit_code,
            error_message=
                error_message
        )


        print()

        print(
            f"Run history saved. "
            f"Run ID: {run_id}"
        )

        print(
            f"Run status: {status}"
        )

        print(
            f"Run type: {RUN_TYPE}"
        )


        return exit_code


    # =========================================
    # UNHANDLED ERROR
    # =========================================

    except Exception as error:

        error_message = (
            f"{type(error).__name__}: "
            f"{error}"
        )


        print()

        print(
            "UNHANDLED MONITOR ERROR"
        )

        print(
            "======================="
        )

        print(
            error_message
        )

        traceback.print_exc()


        try:

            finish_run_history(
                run_id=run_id,
                status="UNHANDLED_ERROR",
                pages_successful=
                    pages_scraped,
                products_scraped=
                    products_scraped,
                failed_pages=
                    failed_pages,
                alerts_detected=
                    alerts_detected,
                telegram_eligible=
                    telegram_eligible,
                telegram_sent=
                    telegram_sent,
                telegram_failed=
                    telegram_failed,
                exit_code=1,
                error_message=
                    error_message
            )


            print()

            print(
                f"Run history saved. "
                f"Run ID: {run_id}"
            )

            print(
                "Run status: "
                "UNHANDLED_ERROR"
            )

            print(
                f"Run type: {RUN_TYPE}"
            )


        except Exception as history_error:

            print(
                "ERROR: Could not update "
                "run history:"
            )

            print(
                history_error
            )


        return 1


# =========================================
# START PROGRAM
# =========================================

if __name__ == "__main__":

    exit_code = main()

    sys.exit(exit_code)