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
import allure
import shutil
import subprocess
import pytest_html  

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
        # Priority: explicit HEADLESS env var > CI auto-detect > default (headed, local)
        env_value = os.environ.get("HEADLESS", "").strip().lower()

        if env_value:
            # Explicitly set — always wins, whether local or CI
            headless = env_value == "true"
        elif os.environ.get("CI"):
            # GitHub Actions sets CI=true automatically — no manual config needed
            headless = True
        else:
            # Local run, nothing set — default to headed so you can watch it
            headless = False

        b = p.chromium.launch(headless=headless)
        yield b
        b.close()


# ── Page fixture (fresh context per test) ─────────────────────────────────────


# ── Directories (add these near your existing SS_DIR line) ───────────────────
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
TRACES_DIR = os.path.join(BASE_DIR, "traces")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(TRACES_DIR, exist_ok=True)


@pytest.fixture(scope="function")
def page(browser, request):
    context = browser.new_context(
        viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
        record_video_dir=VIDEOS_DIR,
        record_video_size={"width": VIEWPORT_W, "height": VIEWPORT_H},
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    pg = context.new_page()
    yield pg

    rep_call = getattr(request.node, "rep_call", None)
    failed = rep_call is not None and rep_call.failed

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.node.name)
    ts   = time.strftime("%Y%m%d_%H%M%S")

    # ── Screenshot (only on failure) ──────────────────────────────────────────
    if failed:
        ss_path = os.path.join(SS_DIR, f"{safe}_{ts}.png")
        try:
            pg.screenshot(path=ss_path, full_page=True)
            print(f"\n📸  Screenshot saved: {ss_path}")
            request.node.screenshot_path = ss_path
            allure.attach.file(ss_path, name="Screenshot", attachment_type=allure.attachment_type.PNG)

            # ── Attach to pytest-html report ──────────────────────────────────
            if rep_call is not None:
                extra = getattr(rep_call, "extra", [])
                extra.append(pytest_html.extras.image(ss_path))
                rep_call.extra = extra
        except Exception as e:
            print(f"\n⚠️  Screenshot failed: {e}")

    # ── Tracing: stop and keep only if failed ─────────────────────────────────
    trace_path = os.path.join(TRACES_DIR, f"{safe}_{ts}_trace.zip")
    try:
        if failed:
            context.tracing.stop(path=trace_path)
            allure.attach.file(trace_path, name="Trace", attachment_type="application/zip")
        else:
            context.tracing.stop()  # discard, no path = don't save
    except Exception as e:
        print(f"\n⚠️  Trace handling failed: {e}")

    video = pg.video  # grab reference before closing context
    context.close()   # video file is only finalized after this

    # ── Video: keep only if failed, delete otherwise ──────────────────────────
    if video:
        try:
            if failed:
                video_path = os.path.join(VIDEOS_DIR, f"{safe}_{ts}.webm")
                os.replace(video.path(), video_path)
                allure.attach.file(video_path, name="Video", attachment_type=allure.attachment_type.WEBM)
            else:
                os.remove(video.path())
        except Exception as e:
            print(f"\n⚠️  Video handling failed: {e}")


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
    if not _results:
        print("\nNo results collected — skipping email.")
        return

    if os.environ.get("CI"):
        print("\nCI run detected — skipping email report (local-only feature).")
    elif not SENDER_PASSWORD:
        print("\n⚠️  SENDER_PASSWORD not set — skipping email. Check your .env file.")
    else:
        duration = round(time.time() - _session_start, 2)
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in _results]
        try:
            send_report(
                results=clean, duration=duration,
                smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
                sender_email=SENDER_EMAIL, sender_password=SENDER_PASSWORD,
                recipients=EMAIL_RECIPIENTS, subject=EMAIL_SUBJECT,
            )
        except Exception as e:
            print(f"\n⚠️  Email failed: {e}")
            print("    Check SENDER_PASSWORD in your .env file")

    _generate_allure_zip()  


def pytest_collection_modifyitems(config, items):
    """Strip parametrize bracket IDs from test names for cleaner output."""
    for item in items:
        item._nodeid = re.sub(r"\[.*\]$", "", item.nodeid)
        item.name    = re.sub(r"\[.*\]$", "", item.name)
        
ALLURE_RESULTS_DIR = os.path.join(BASE_DIR, "allure-results")
ALLURE_REPORT_DIR  = os.path.join(BASE_DIR, "allure-report")
ALLURE_ZIP_PATH    = os.path.join(BASE_DIR, "allure-report")  # shutil adds .zip automatically


def _generate_allure_zip():
    """Generate the Allure HTML report and zip it into allure-report.zip."""
    if not os.path.exists(ALLURE_RESULTS_DIR):
        print("\n⚠️  No allure-results found — skipping Allure zip.")
        return

    try:
        subprocess.run(
            ["allure", "generate", ALLURE_RESULTS_DIR, "--clean", "-o", ALLURE_REPORT_DIR],
            check=True,
            shell=True,  # needed on Windows so it finds allure.bat / allure.cmd on PATH
        )
        shutil.make_archive(ALLURE_ZIP_PATH, "zip", ALLURE_REPORT_DIR)
        print(f"\n📦  Allure report zipped: {ALLURE_ZIP_PATH}.zip")
    except FileNotFoundError:
        print("\n⚠️  'allure' command not found — is Allure commandline installed and on PATH?")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Allure generate failed: {e}")
    except Exception as e:
        print(f"\n⚠️  Allure zip step failed: {e}")