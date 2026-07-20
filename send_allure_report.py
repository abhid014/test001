"""
send_allure_report.py
=====================
Standalone script — run this AFTER `allure generate` to zip and
email the full Allure HTML report to your recipients.

Usage:
    python send_allure_report.py

Or from the project root after tests:
    pytest && allure generate allure-results --clean -o allure-report && python send_allure_report.py
"""

import os
import sys
import zipfile
import smtplib
import datetime
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ── Config — edit these ───────────────────────────────────────────────────────

SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
SENDER_EMAIL    = "us23qa@gmail.com"
SENDER_PASSWORD = "hogt ugbe kfrc mymh"   # Gmail App Password

RECIPIENTS = [
    "adalvi@smartapp.com",
]

ALLURE_RESULTS = "allure-results"
ALLURE_REPORT  = "allure-report"
ZIP_PATH       = "allure-report.zip"

# ── Step 1 — Generate Allure report ──────────────────────────────────────────

def generate_report():
    print("⚙️  Generating Allure report...")
    result = subprocess.run(
        ["allure", "generate", ALLURE_RESULTS, "--clean", "-o", ALLURE_REPORT],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅  Report generated at: {ALLURE_REPORT}/")
    else:
        print(f"❌  Allure generate failed:\n{result.stderr}")
        sys.exit(1)

# ── Step 2 — Zip the report ───────────────────────────────────────────────────

def zip_report():
    if not os.path.exists(ALLURE_REPORT):
        print(f"❌  Allure report folder not found: {ALLURE_REPORT}")
        sys.exit(1)

    print(f"📦  Zipping {ALLURE_REPORT}/ → {ZIP_PATH} ...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(ALLURE_REPORT):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_name = os.path.relpath(abs_path, ALLURE_REPORT)
                zf.write(abs_path, arc_name)

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"✅  Zipped: {ZIP_PATH} ({size_mb:.1f} MB)")
    return ZIP_PATH

# ── Step 3 — Parse quick stats from allure-results ───────────────────────────

def _quick_stats():
    """Read JSON result files to compute quick pass/fail counts."""
    import json, glob
    passed = failed = broken = skipped = 0
    for f in glob.glob(os.path.join(ALLURE_RESULTS, "*-result.json")):
        try:
            data   = json.load(open(f, encoding="utf-8"))
            status = data.get("status", "")
            if status == "passed":   passed  += 1
            elif status == "failed": failed  += 1
            elif status == "broken": broken  += 1
            elif status == "skipped":skipped += 1
        except Exception:
            continue
    total = passed + failed + broken + skipped
    rate  = round((passed / total) * 100) if total else 0
    return total, passed, failed + broken, skipped, rate

# ── Step 4 — Build email HTML ─────────────────────────────────────────────────

def _build_email_html(total, passed, failed, skipped, rate, zip_name):
    now    = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    all_ok = failed == 0
    status_color = "#22c55e" if all_ok else "#ef4444"
    status_label = "✓ All Tests Passed" if all_ok else "✗ Failures Detected"
    bar_color    = "#22c55e" if rate >= 90 else "#f59e0b" if rate >= 70 else "#ef4444"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Allure Report</title></head>
<body style="margin:0;padding:0;background:#080a12;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;background:#080a12">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0"
       style="max-width:620px;background:#0f1117;border-radius:16px;
              border:1px solid #2e3250;overflow:hidden;
              box-shadow:0 0 40px rgba(99,102,241,.2)">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#1e2140 0%,#12142a 100%);
               padding:32px 36px;border-bottom:1px solid #2e3250">
      <div style="font-size:11px;font-weight:700;color:#64748b;
                  letter-spacing:.15em;text-transform:uppercase;margin-bottom:14px">
        ● SmartApp · QA Automation
      </div>
      <div style="font-size:26px;font-weight:800;color:#ffffff;margin-bottom:6px">
        Allure Test Report
      </div>
      <div style="font-size:13px;color:#64748b;margin-bottom:18px">
        Finance → Budget Add Flow &nbsp;·&nbsp; {now}
      </div>
      <div style="display:inline-flex;align-items:center;gap:8px;
                  background:{status_color}22;border:1px solid {status_color}44;
                  border-radius:20px;padding:5px 16px">
        <div style="width:7px;height:7px;border-radius:50%;background:{status_color}"></div>
        <span style="font-size:12px;font-weight:700;color:{status_color}">{status_label}</span>
      </div>
    </td>
  </tr>

  <!-- Stats -->
  <tr>
    <td style="padding:0;border-bottom:1px solid #2e3250">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
        <tr>
          <td align="center" style="padding:20px 8px;background:#1a1d27;
                                     border-right:1px solid #2e3250">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                        letter-spacing:.1em;margin-bottom:6px">📋 Total</div>
            <div style="font-size:28px;font-weight:800;color:#6366f1">{total}</div>
          </td>
          <td align="center" style="padding:20px 8px;background:#1a1d27;
                                     border-right:1px solid #2e3250">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                        letter-spacing:.1em;margin-bottom:6px">✅ Passed</div>
            <div style="font-size:28px;font-weight:800;color:#22c55e">{passed}</div>
          </td>
          <td align="center" style="padding:20px 8px;background:#1a1d27;
                                     border-right:1px solid #2e3250">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                        letter-spacing:.1em;margin-bottom:6px">❌ Failed</div>
            <div style="font-size:28px;font-weight:800;color:#ef4444">{failed}</div>
          </td>
          <td align="center" style="padding:20px 8px;background:#1a1d27">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;
                        letter-spacing:.1em;margin-bottom:6px">⏭️ Skipped</div>
            <div style="font-size:28px;font-weight:800;color:#94a3b8">{skipped}</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Pass rate -->
  <tr>
    <td style="padding:18px 28px 22px;background:#1a1d27;border-bottom:1px solid #2e3250">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:12px;font-weight:600;color:#64748b">Pass Rate</td>
          <td align="right" style="font-size:14px;font-weight:800;color:{bar_color}">{rate}%</td>
        </tr>
      </table>
      <div style="height:8px;background:#22263a;border-radius:4px;
                  overflow:hidden;margin-top:10px">
        <div style="height:100%;width:{rate}%;background:{bar_color};
                    border-radius:4px;box-shadow:0 0 8px {bar_color}66"></div>
      </div>
    </td>
  </tr>

  <!-- What's inside -->
  <tr>
    <td style="padding:24px 28px;background:#0f1117">
      <div style="font-size:10px;font-weight:700;color:#6366f1;
                  letter-spacing:.12em;text-transform:uppercase;margin-bottom:14px">
        📊 What's Inside the Report
      </div>
      <table width="100%" cellpadding="0" cellspacing="0">
        {''.join(f"""
        <tr>
          <td style="padding:6px 0;font-size:13px;color:#94a3b8;
                     border-bottom:1px solid #1a1d27">{item}</td>
        </tr>""" for item in [
            "🗂️ Dashboard — overall pass/fail summary",
            "🧪 Test Results — per-test status and steps",
            "📸 Screenshots — attached on failure",
            "🎥 Videos — recorded on failure",
            "🗂️ Categories — failures grouped by type",
            "📈 Trend Charts — historical run trends",
            "📋 Historical Results — previous runs",
            "🎯 Severity Levels — Blocker → Trivial",
            "👤 Owners & Tags — team breakdown",
            "⏱️ Timeline View — test execution order",
        ])}
      </table>
    </td>
  </tr>

  <!-- Instructions -->
  <tr>
    <td style="padding:0 28px 24px;background:#0f1117">
      <div style="padding:16px 20px;background:#1a1d27;
                  border:1px solid #6366f144;border-radius:8px;
                  border-left:3px solid #6366f1">
        <div style="font-size:12px;font-weight:700;color:#6366f1;margin-bottom:8px">
          📂 How to open the report
        </div>
        <div style="font-size:12px;color:#64748b;line-height:1.8">
          1. Download <strong style="color:#e2e8f0">{zip_name}</strong> attached below<br>
          2. Extract the ZIP to any folder<br>
          3. Open <code style="color:#38bdf8;background:#22263a;
                               padding:2px 6px;border-radius:4px">index.html</code>
             in your browser<br>
          4. Use the left sidebar to navigate all sections
        </div>
      </div>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:14px 28px;background:#12142a;border-top:1px solid #2e3250">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:11px;color:#334155">SmartApp QA · Playwright Suite</td>
          <td align="right" style="font-size:11px;color:#334155">
            Auto-generated · Do not reply
          </td>
        </tr>
      </table>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

# ── Step 5 — Send email ───────────────────────────────────────────────────────

def send_email(zip_path: str):
    total, passed, failed, skipped, rate = _quick_stats()
    now       = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    subject   = f"[SmartApp QA] Allure Report — Finance Flow — {now} — {rate}% Pass"
    zip_name  = os.path.basename(zip_path)
    html_body = _build_email_html(total, passed, failed, skipped, rate, zip_name)

    msg            = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENTS)

    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    plain = (
        f"SmartApp QA — Allure Report\n"
        f"{'=' * 40}\n"
        f"Date:     {now}\n"
        f"Total:    {total}\n"
        f"Passed:   {passed}\n"
        f"Failed:   {failed}\n"
        f"Skipped:  {skipped}\n"
        f"Pass Rate:{rate}%\n\n"
        f"Extract {zip_name} and open index.html to view the full report."
    )
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(html_body, "html"))

    # Attach ZIP
    with open(zip_path, "rb") as f:
        part = MIMEBase("application", "zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={zip_name}")
    msg.attach(part)

    print(f"📧  Sending to: {', '.join(RECIPIENTS)} ...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
    print("✅  Email sent successfully!")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_report()
    zip_path = zip_report()
    send_email(zip_path)
