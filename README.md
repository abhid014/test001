# SmartApp QA — Allure Report Setup

## Install Everything

```bash
# 1. Java (required by Allure CLI)
#    Download from https://www.java.com and install, then verify:
java -version

# 2. Scoop (Windows package manager)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# 3. Allure CLI via Scoop
scoop install allure
allure --version

# 4. Python packages
pip install allure-pytest playwright pytest-playwright
playwright install chromium
```

---

## Project Structure

```
project/
├── conftest.py                  ← fixtures, video, screenshot, allure env
├── pytest.ini                   ← allure-results dir config
├── send_allure_report.py        ← standalone email sender script
├── allure-results/
│   └── categories.json          ← failure category definitions
├── tests/
│   └── test_finance_mode.py     ← fully decorated with Allure metadata
├── pages/
│   ├── login_page.py
│   ├── finance_page.py
│   └── finance_budgets_page.py
└── utils/
    ├── email_reporter.py        ← dark-themed HTML email builder
    ├── constants.py
    └── excel_reader.py
```

---

## Run Tests + Generate Report + Send Email

### Option A — All in one (auto-sends email at session end)
```bash
pytest
```
conftest.py automatically generates the Allure report and sends the email
when the pytest session finishes.

### Option B — Manual control
```bash
# Step 1: Run tests
pytest

# Step 2: Generate Allure HTML report
allure generate allure-results --clean -o allure-report

# Step 3: Open in browser (optional)
allure open allure-report

# Step 4: Send email with ZIP attached
python send_allure_report.py
```

### Option C — Serve live report (no email)
```bash
pytest
allure serve allure-results
```

---

## What's in the Allure Report

| Section | Description |
|---|---|
| Dashboard | Pass/fail donut, pass rate, severity breakdown |
| Test Results | Per-test status, steps, duration |
| Steps | Each `allure.step()` block as expandable tree |
| Screenshots | PNG attached inline on failure |
| Videos | .webm recorded on failure, attached to test |
| Categories | Failures grouped: Timeouts, Assertions, Element Not Found, Navigation |
| Trend Charts | Pass rate across historical runs (needs history folder) |
| Historical Results | Previous run comparison |
| Severity Levels | Blocker / Critical / Normal / Minor / Trivial |
| Owners & Tags | Grouped by `@allure.label("owner", ...)` and `@allure.label("tag", ...)` |
| Timeline View | Tests on a time axis showing parallel/sequential execution |

---

## Keep Trend History (for Trend Charts)

Allure trend charts require the `history/` folder from the previous run.
Add this to your CI pipeline or run script:

```bash
# Before generating new report, copy history from previous report
cp -r allure-report/history allure-results/history

# Then generate
allure generate allure-results --clean -o allure-report
```

---

## Email Configuration

Edit `send_allure_report.py` or `utils/constants.py`:

```python
SENDER_EMAIL    = "us23qa@gmail.com"
SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password
RECIPIENTS      = ["adalvi@smartapp.com"]
```

Gmail App Password setup:
1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification
3. Search "App passwords" → create one for "Mail"
4. Use the 16-character password (spaces don't matter)
