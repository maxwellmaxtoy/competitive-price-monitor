import os
import sys


# =========================================
# MARK THIS EXECUTION AS A TEST
# =========================================

os.environ[
    "PRICE_MONITOR_RUN_TYPE"
] = "TEST"


# IMPORTANT:
# Set the environment variable BEFORE
# importing price_monitor.
import price_monitor


# =========================================
# SAVE REAL PAGE LOADER
# =========================================

original_load_page = (
    price_monitor.load_page_with_retries
)


# =========================================
# FORCE PAGE 3 FAILURE
# =========================================

def test_load_page(
    page,
    url,
    page_number
):

    if page_number == 3:

        print()

        print(
            "TEST MODE: Forcing page 3 "
            "to use an invalid URL."
        )

        url = (
            "http://books.toscrape.invalid/"
        )


    return original_load_page(
        page,
        url,
        page_number
    )


# Replace function only for this process.
price_monitor.load_page_with_retries = (
    test_load_page
)


# =========================================
# RUN REAL MONITOR
# =========================================

exit_code = (
    price_monitor.main()
)


print()

print(
    "Partial failure test exit code:",
    exit_code
)


sys.exit(
    exit_code
)