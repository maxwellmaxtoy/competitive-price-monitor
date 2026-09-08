import os
import sqlite3


# =========================================
# FORCE TEST MODE
# =========================================

os.environ["PRICE_MONITOR_RUN_TYPE"] = "TEST"


# Import AFTER setting TEST mode
import price_monitor


DATABASE = "price_monitor.db"

PRODUCT_NAME = "A Light in the Attic"

SOURCE = "books.toscrape.com"

TEST_PRICE = 48.00


# =========================================
# MODIFY LATEST TEST PRICE
# =========================================

connection = sqlite3.connect(DATABASE)

cursor = connection.cursor()


cursor.execute("""
    SELECT
        id,
        price
    FROM price_history
    WHERE product_name = ?
    AND source = ?
    AND run_type = 'TEST'
    ORDER BY
        scraped_at DESC,
        id DESC
    LIMIT 1
""", (
    PRODUCT_NAME,
    SOURCE
))


row = cursor.fetchone()


if row is None:

    print(
        "ERROR: No TEST price history "
        "found for the product."
    )

    connection.close()

    raise SystemExit(1)


record_id = row[0]

original_price = row[1]


print(
    "Latest TEST record ID:",
    record_id
)

print(
    "Original TEST price:",
    original_price
)


cursor.execute("""
    UPDATE price_history
    SET price = ?
    WHERE id = ?
""", (
    TEST_PRICE,
    record_id
))


connection.commit()

connection.close()


print(
    "Temporary TEST price:",
    TEST_PRICE
)

print(
    "Significant TEST price change prepared."
)

print()
print(
    "Starting monitor in TEST mode..."
)

print()


# =========================================
# RUN REAL MONITOR
# =========================================

exit_code = price_monitor.main()


print()
print(
    "TEST Telegram suppression "
    "exit code:",
    exit_code
)


raise SystemExit(
    exit_code
)