import sqlite3


DATABASE = "price_monitor.db"


# =========================================
# CONNECT TO DATABASE
# =========================================

connection = sqlite3.connect(DATABASE)

cursor = connection.cursor()


# =========================================
# GET LATEST RUN HISTORY
# =========================================

cursor.execute("""
    SELECT
        id,
        source,
        started_at,
        finished_at,
        status,
        run_type,
        pages_expected,
        pages_successful,
        products_scraped,
        failed_pages,
        alerts_detected,
        telegram_eligible,
        telegram_sent,
        telegram_failed,
        exit_code,
        error_message
    FROM run_history
    ORDER BY id DESC
    LIMIT 10
""")


rows = cursor.fetchall()


# =========================================
# DISPLAY RESULTS
# =========================================

if not rows:

    print("No run history records found.")

else:

    for row in rows:

        print()
        print("==============================")
        print("RUN HISTORY")
        print("==============================")

        print("Run ID:", row[0])
        print("Source:", row[1])
        print("Started:", row[2])
        print("Finished:", row[3])
        print("Status:", row[4])
        print("Run type:", row[5])
        print("Pages expected:", row[6])
        print("Pages successful:", row[7])
        print("Products scraped:", row[8])
        print("Failed pages:", row[9])
        print("Alerts detected:", row[10])
        print("Telegram eligible:", row[11])
        print("Telegram sent:", row[12])
        print("Telegram failed:", row[13])
        print("Exit code:", row[14])
        print("Error message:", row[15])


connection.close()