"""
config.py
=========
Single source of truth for ALL project settings.
Edit ONLY this file — every other file reads from here.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in local dev; no-op in CI (env vars come from GitHub Secrets)

# ── Application ───────────────────────────────────────────────────────────────
BASE_URL     = "https://central.smartappqa.com/"
PROJECT_NAME = "Beachfront Gates"
APP_NAME     = "SmartApp"
ENVIRONMENT  = "QA"

# ── Browser ───────────────────────────────────────────────────────────────────
BROWSER    = "chromium"   # chromium | firefox | webkit
HEADLESS   = False
VIEWPORT_W = 1440
VIEWPORT_H = 900
SLOW_MO    = 0            # ms delay between actions (0 = off)

# ── Timeouts (milliseconds) ───────────────────────────────────────────────────
DEFAULT_WAIT_TIMEOUT = 20000   # general expect() calls in page objects
NAVIGATION_TIMEOUT   = 30000   # after page navigation / zone loading
NETWORK_IDLE_TIMEOUT = 15000   # wait_for_load_state("networkidle") cap

# ── Test data ─────────────────────────────────────────────────────────────────
EXCEL_FILE         = "test_data/test_automation_data.xlsx"
FINANCE_SHEET      = "FinanceLoginTests"
LOGIN_SHEET        = "LoginTests"
PROJECT_NAME_SHEET = "ProjectName"
PROJECT_NAME_ROW   = 2    # row number in ProjectName sheet to read from

# ── Screenshots ───────────────────────────────────────────────────────────────
SCREENSHOTS_DIR = "screenshots"   # relative to project root

# ── Email / SMTP ──────────────────────────────────────────────────────────────
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "us23qa@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")   # no default — must come from .env or GitHub Secret

EMAIL_RECIPIENTS = [
    r.strip() for r in os.environ.get(
        "EMAIL_RECIPIENTS", "abhigit014@gmail.com"
    ).split(",") if r.strip()
]

EMAIL_SUBJECT = f"[{APP_NAME} QA] Test Report — {PROJECT_NAME} — Finance Flow"