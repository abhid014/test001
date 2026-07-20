"""
utils/constants.py
==================
Re-exports everything from config.py.
Any file that does `from utils.constants import X` keeps working unchanged.
Do NOT add values here — edit config.py only.
"""

from config import (
    BASE_URL,
    PROJECT_NAME,
    APP_NAME,
    ENVIRONMENT,
    BROWSER,
    HEADLESS,
    VIEWPORT_W,
    VIEWPORT_H,
    SLOW_MO,
    DEFAULT_WAIT_TIMEOUT,
    NAVIGATION_TIMEOUT,
    NETWORK_IDLE_TIMEOUT,
    EXCEL_FILE,
    FINANCE_SHEET,
    LOGIN_SHEET,
    PROJECT_NAME_SHEET,
    PROJECT_NAME_ROW,
    SCREENSHOTS_DIR,
    SMTP_HOST,
    SMTP_PORT,
    SENDER_EMAIL,
    SENDER_PASSWORD,
    EMAIL_RECIPIENTS,
    EMAIL_SUBJECT,
)