"""
conftest.py
===========
- Fresh browser context per test (no shared cookies / auth state)
- Screenshot saved on failure into screenshots/
- Collects PASSED / FAILED / ERROR per test via hooks
- Sends dark-themed HTML email report at session end
- Supports headed/headless via HEADLESS env var (CI) or --headed flag (local)
"""

import os
import re
import time
import pytest
from playwright.sync_api import sync_playwright

from utils.email_reporter import send_report
from config import (
    SMTP_HOST,
    SMTP_PORT,
    SENDER_EMAIL,
    SENDER_PASSWORD,
    EMAIL_RECIPIENTS,
    EMAIL_SUBJECT,
    VIEWPORT_W,
    VIEWPORT_H,
    SCREENSHOTS_DIR,
)

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SS_DIR   = os.path.join(BASE_DIR, SCREENSHOTS_DIR)
os.makedirs(SS_DIR, exist_ok=True)

# ── Session-level collectors ──────────────────────────────────────────────────
_results: list[dict] = []
_session_start: float = 0.0


# ── Browser fixture (one process per session) ─────────────────────────────────
@pytest.fixture(scope="session")
def browser(request):
    with sync_playwright() as p:
        # CI: HEADLESS env var always takes priority
        env_value = os.environ.get("HEADLESS", "").strip().lower()

        if env_value:
            # Explicitly set via environment variable (used in CI)
            headless = env_value == "true"
        else:
            # Fall back to --headed flag from pytest.ini / command line (local)
            headed_flag = request.config.getoption("--headed", default=False)
            headless = not headed_flag

        b = p.chromium.launch(headless=headless)
        yield b
        b.close()


# ── Page fixture (fresh context per test) ─────────────────────────────────────
@pytest.fixture(scope="function")
def page(browser, request):
    """
    Each test gets a brand-new browser context — no shared cookies,
    localStorage, or auth state between tests.
    """
    context = browser.new_context(
        viewport={"width": VIEWPORT_W, "height": VIEWPORT_H}
    )
    pg = context.new_page()
    yield pg

    # ── Screenshot on failure ─────────────────────────────────────────────────
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call is not None and rep_call.failed:
        safe = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in request.node.name
        )
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SS_DIR, f"{safe}_{ts}.png")
        try:
            pg.screenshot(path=path, full_page=True)
            print(f"\n📸  Screenshot saved: {path}")
            request.node.screenshot_path = path
        except Exception as e:
            print(f"\n⚠️  Screenshot failed: {e}")

    context.close()  # wipes all cookies → next test starts completely clean


# ── Pytest hooks ──────────────────────────────────────────────────────────────
def pytest_sessionstart(session):
    global _session_start
    _session_start = time.time()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture result of every test body (call phase only)."""
    outcome = yield
    report  = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when == "call":
        status = (
            "PASSED" if report.passed else
            "FAILED" if report.failed else "ERROR"
        )
        message = ""
        if report.failed and report.longrepr:
            lines   = str(report.longrepr).strip().splitlines()
            message = lines[-1] if lines else ""

        _results.append({
            "name":            item.name,
            "status":          status,
            "duration":        round(report.duration, 2),
            "message":         message,
            "screenshot_path": None,
            "_item":           item,
        })


def pytest_runtest_teardown(item, nextitem):
    """After fixture teardown, link screenshot path to its result entry."""
    ss = getattr(item, "screenshot_path", None)
    if ss:
        for r in _results:
            if r.get("_item") is item:
                r["screenshot_path"] = ss
                break


def pytest_sessionfinish(session, exitstatus):
    """Build and send the HTML email report once all tests finish (local runs only)."""
    if not _results:
        print("\nNo results collected — skipping email.")
        return

    if os.environ.get("CI"):
        print("\nCI run detected — skipping email report (local-only feature).")
        return

    if not SENDER_PASSWORD:
        print("\n⚠️  SENDER_PASSWORD not set — skipping email. Check your .env file.")
        return

    duration = round(time.time() - _session_start, 2)
    clean    = [
        {k: v for k, v in r.items() if not k.startswith("_")}
        for r in _results
    ]

    try:
        send_report(
            results          = clean,
            duration         = duration,
            smtp_host        = SMTP_HOST,
            smtp_port        = SMTP_PORT,
            sender_email     = SENDER_EMAIL,
            sender_password  = SENDER_PASSWORD,
            recipients       = EMAIL_RECIPIENTS,
            subject          = EMAIL_SUBJECT,
        )
    except Exception as e:
        print(f"\n⚠️  Email failed: {e}")
        print("    Check SENDER_PASSWORD in your .env file")


def pytest_collection_modifyitems(config, items):
    """Strip parametrize bracket IDs from test names for cleaner output."""
    for item in items:
        item._nodeid = re.sub(r"\[.*\]$", "", item.nodeid)
        item.name    = re.sub(r"\[.*\]$", "", item.name)