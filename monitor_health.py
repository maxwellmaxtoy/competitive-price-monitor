import sqlite3
from datetime import datetime


DATABASE = "price_monitor.db"


# =========================================
# DATABASE
# =========================================

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()


cursor.execute("""
    SELECT
        id,
        started_at,
        finished_at,
        status,
        run_type,
        pages_expected,
        pages_successful,
        products_scraped,
        alerts_detected,
        telegram_sent,
        telegram_failed,
        exit_code
    FROM run_history
    ORDER BY id ASC
""")


all_runs = cursor.fetchall()


# =========================================
# NO RUNS
# =========================================

if not all_runs:

    print("No run history available.")

    connection.close()

    raise SystemExit(0)


# =========================================
# SEPARATE PRODUCTION AND TEST
# =========================================

production_runs = [
    run
    for run in all_runs
    if run[4] == "PRODUCTION"
]


test_runs = [
    run
    for run in all_runs
    if run[4] == "TEST"
]


# =========================================
# ANALYZE RUNS
# =========================================

def analyze_runs(runs):

    result = {
        "total": len(runs),
        "completed": 0,
        "success": 0,
        "partial_failure": 0,
        "scraper_failure": 0,
        "telegram_failure": 0,
        "unhandled_error": 0,
        "running": 0,
        "products": 0,
        "alerts": 0,
        "telegram_sent": 0,
        "telegram_failed": 0,
        "durations": [],
        "latest": None,
        "last_success": None
    }


    for run in runs:

        run_id = run[0]
        started_at = run[1]
        finished_at = run[2]
        status = run[3]
        products_scraped = run[7]
        alerts_detected = run[8]
        telegram_sent = run[9]
        telegram_failed = run[10]


        # -------------------------------------
        # STATUS COUNTS
        # -------------------------------------

        if status == "SUCCESS":

            result["success"] += 1
            result["last_success"] = run


        elif status == "PARTIAL_FAILURE":

            result["partial_failure"] += 1


        elif status == "SCRAPER_FAILURE":

            result["scraper_failure"] += 1


        elif status == "TELEGRAM_FAILURE":

            result["telegram_failure"] += 1


        elif status == "UNHANDLED_ERROR":

            result["unhandled_error"] += 1


        elif status == "RUNNING":

            result["running"] += 1


        # -------------------------------------
        # TOTALS
        # -------------------------------------

        result["products"] += (
            products_scraped or 0
        )

        result["alerts"] += (
            alerts_detected or 0
        )

        result["telegram_sent"] += (
            telegram_sent or 0
        )

        result["telegram_failed"] += (
            telegram_failed or 0
        )


        # -------------------------------------
        # RUNTIME
        # -------------------------------------

        if started_at and finished_at:

            try:

                start = datetime.fromisoformat(
                    started_at
                )

                finish = datetime.fromisoformat(
                    finished_at
                )

                duration = (
                    finish - start
                ).total_seconds()

                result["durations"].append(
                    duration
                )

            except ValueError:

                pass


    result["completed"] = (
        result["total"]
        - result["running"]
    )


    if runs:

        result["latest"] = runs[-1]


    return result


# =========================================
# DERIVED METRICS
# =========================================

def success_rate(data):

    if data["completed"] == 0:
        return 0.0

    return (
        data["success"]
        / data["completed"]
    ) * 100


def average_products(data):

    if data["completed"] == 0:
        return 0.0

    return (
        data["products"]
        / data["completed"]
    )


def average_runtime(data):

    if not data["durations"]:
        return 0.0

    return (
        sum(data["durations"])
        / len(data["durations"])
    )


# =========================================
# CALCULATE REPORTS
# =========================================

production = analyze_runs(
    production_runs
)

tests = analyze_runs(
    test_runs
)


production_rate = success_rate(
    production
)

production_avg_products = average_products(
    production
)

production_avg_runtime = average_runtime(
    production
)


# =========================================
# REPORT
# =========================================

print()
print("========================================")
print("COMPETITIVE PRICE MONITOR - HEALTH REPORT")
print("========================================")


# =========================================
# PRODUCTION HEALTH
# =========================================

print()
print("PRODUCTION HEALTH")
print("-----------------")

print(
    "Production runs:",
    production["total"]
)

print(
    "Completed production runs:",
    production["completed"]
)

print(
    "Successful production runs:",
    production["success"]
)

print(
    "Production success rate:",
    f"{production_rate:.2f}%"
)


# =========================================
# PRODUCTION FAILURES
# =========================================

print()
print("PRODUCTION FAILURES")
print("-------------------")

print(
    "Partial failures:",
    production["partial_failure"]
)

print(
    "Scraper failures:",
    production["scraper_failure"]
)

print(
    "Telegram failures:",
    production["telegram_failure"]
)

print(
    "Unhandled errors:",
    production["unhandled_error"]
)

print(
    "Currently running:",
    production["running"]
)


# =========================================
# PERFORMANCE
# =========================================

print()
print("PRODUCTION PERFORMANCE")
print("----------------------")

print(
    "Average runtime:",
    f"{production_avg_runtime:.2f} seconds"
)

print(
    "Average products per run:",
    f"{production_avg_products:.2f}"
)

print(
    "Total products processed:",
    production["products"]
)


# =========================================
# ALERTING
# =========================================

print()
print("PRODUCTION ALERTING")
print("-------------------")

print(
    "Price changes detected:",
    production["alerts"]
)

print(
    "Telegram alerts sent:",
    production["telegram_sent"]
)

print(
    "Telegram alerts failed:",
    production["telegram_failed"]
)


# =========================================
# LATEST PRODUCTION RUN
# =========================================

print()
print("LATEST PRODUCTION RUN")
print("---------------------")

if production["latest"]:

    latest = production["latest"]

    print(
        "Run ID:",
        latest[0]
    )

    print(
        "Status:",
        latest[3]
    )

    print(
        "Products scraped:",
        latest[7]
    )

    print(
        "Exit code:",
        latest[11]
    )

else:

    print(
        "No production runs recorded."
    )


# =========================================
# LAST SUCCESSFUL PRODUCTION RUN
# =========================================

print()
print("LAST SUCCESSFUL PRODUCTION RUN")
print("------------------------------")

if production["last_success"]:

    last_success = (
        production["last_success"]
    )

    print(
        "Run ID:",
        last_success[0]
    )

    print(
        "Started:",
        last_success[1]
    )

    print(
        "Finished:",
        last_success[2]
    )

    print(
        "Products scraped:",
        last_success[7]
    )

else:

    print(
        "No successful production runs recorded."
    )


# =========================================
# TEST RUN SUMMARY
# =========================================

print()
print("TEST RUN SUMMARY")
print("----------------")

print(
    "Test runs:",
    tests["total"]
)

print(
    "Successful tests:",
    tests["success"]
)

print(
    "Intentional partial failures:",
    tests["partial_failure"]
)

print(
    "Scraper failure tests:",
    tests["scraper_failure"]
)

print(
    "Telegram failure tests:",
    tests["telegram_failure"]
)

print(
    "Unhandled error tests:",
    tests["unhandled_error"]
)


print()
print("========================================")


connection.close()