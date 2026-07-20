"""
utils/email_reporter.py
========================
Sends a dark-themed HTML email report via Gmail SMTP.

What it includes
  - Header with pass/fail status pill
  - Stat cards  (Total / Passed / Failed / Skipped / Duration)
  - Pass rate progress bar
  - Failure categories  (Timeouts / Assertions / Element Not Found / Navigation)
  - Timeline  (per-test horizontal bar showing relative duration)
  - Full test results table  (failed rows highlighted, error message shown)
  - Footer

What it does NOT include
  - No allure
  - No PDF
  - No ZIP
  - No screenshots / videos as attachments
  - No <script> or <style> blocks  (Gmail-safe inline styles only)
"""

from __future__ import annotations
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ── Colour tokens (light theme) ──────────────────────────────────────────────
# Page background / surface / cards use light neutrals so email appears bright
_BG      = "#f6f8fa"   # page background
_SURF    = "#ffffff"   # main container surface
_CARD    = "#ffffff"   # primary card background
_CARD2   = "#f8fafc"   # alternate card / row background
_BORDER  = "#e6e9ef"   # subtle borders
_INDIGO  = "#2563eb"   # primary accent
_VIOLET  = "#8b5cf6"
_GREEN   = "#16a34a"
_ROSE    = "#ef4444"
_AMBER   = "#f59e0b"
_SKY     = "#38bdf8"
_CYAN    = "#06b6d4"
_SLATE   = "#475569"   # headline / muted text
_MUTED   = "#94a3b8"
_TEXT    = "#0f172a"   # primary text
_WHITE   = "#ffffff"

_SEV_CLR = {
    "BLOCKER":  "#f43f5e",
    "CRITICAL": "#f97316",
    "NORMAL":   "#6366f1",
    "MINOR":    "#38bdf8",
    "TRIVIAL":  "#94a3b8",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _pct(a: int, b: int) -> int:
    return round((a / b) * 100) if b else 0

def _fmt(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(int(s), 60)
    return f"{m}m {sec}s"

def _rate_clr(r: int) -> str:
    if r >= 90: return _GREEN
    if r >= 70: return _AMBER
    return _ROSE

def _st_clr(st: str) -> str:
    if st == "PASSED":            return _GREEN
    if st in ("FAILED", "ERROR"): return _ROSE
    return _MUTED

def _st_icon(st: str) -> str:
    if st == "PASSED":            return "✓"
    if st in ("FAILED", "ERROR"): return "✗"
    return "—"


# ── Reusable HTML snippets ────────────────────────────────────────────────────
def _section_label(title: str) -> str:
    """Simple section heading with a small colored accent bar."""
    return (
        f'<tr><td style="padding:20px 28px 8px;background:{_BG}">'
        f'<table cellpadding="0" cellspacing="0" role="presentation"><tr>'
        f'<td style="width:4px;height:12px;background:{_INDIGO};border-radius:2px"></td>'
        f'<td style="padding-left:8px;font-size:12px;font-weight:700;color:{_SLATE};'
        f'letter-spacing:.08em;text-transform:uppercase">{title}</td>'
        f'</tr></table>'
        f'</td></tr>'
    )

def _tbl_wrap(headers: list[str], rows_html: str) -> str:
    """Light-themed table wrapper used across sections."""
    ths = "".join(
        f'<th style="padding:10px 12px;font-size:11px;font-weight:700;'
        f'color:{_SLATE};text-align:{"left" if i == 0 else "center"};'
        f'border-bottom:1px solid {_BORDER}">{h}</th>'
        for i, h in enumerate(headers)
    )
    return (
        f'<tr><td style="padding:0 28px 18px;background:{_BG}">'
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;background:{_SURF};'
        f'border:1px solid {_BORDER};border-radius:10px;overflow:hidden">'
        f'<tr style="background:{_SURF}">{ths}</tr>'
        f'{rows_html}'
        f'</table></td></tr>'
    )

def _badge(text: str, color: str) -> str:
    return (
        f'<span style="display:inline-block;padding:5px 10px;border-radius:999px;'
        f'font-size:12px;font-weight:700;color:{_WHITE};background:{color}">'
        f'{text}</span>'
    )


# ── Section builders ──────────────────────────────────────────────────────────
def _build_header(all_ok: bool, now: str) -> str:
        # left: logo/title, right: status pill
        status_text = "All Tests Passed" if all_ok else "Failures Detected"
        status_color = _GREEN if all_ok else _ROSE
        pill = f'<div style="padding:8px 16px;border-radius:999px;background:{_WHITE};color:{status_color};font-weight:700;font-size:13px">{status_text}</div>'
        return f"""
<tr>
    <td style="padding:24px 28px;background-color:{_INDIGO};">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
            <tr>
                <td style="vertical-align:middle">
                    <table cellpadding="0" cellspacing="0" role="presentation">
                        <tr>
                            <td style="width:44px;height:44px;border-radius:10px;background-color:{_WHITE};text-align:center;vertical-align:middle;font-size:18px;font-weight:800;color:{_INDIGO};font-family:Georgia,'Times New Roman',serif">S</td>
                            <td style="padding-left:14px;vertical-align:middle">
                                <div style="font-size:17px;font-weight:700;color:{_WHITE};letter-spacing:.01em">SmartApp Automation</div>
                                <div style="font-size:12px;color:{_WHITE};opacity:0.85;margin-top:2px">{now}</div>
                            </td>
                        </tr>
                    </table>
                </td>
                <td align="right" style="vertical-align:middle">{pill}</td>
            </tr>
        </table>
    </td>
</tr>"""


def _build_stat_cards(total, passed, failed, skipped, duration) -> str:
        # modern card layout: 4 cards
        def card(val, label, color):
                return (
                        f'<td style="padding:8px;background:{_BG};vertical-align:top">'
                        f'<div style="border-radius:10px;background:{_SURF};border:1px solid {_BORDER};'
                        f'border-top:3px solid {color};padding:14px;box-shadow:0 2px 6px rgba(16,24,40,0.05)">'
                        f'<div style="font-size:11px;color:{_SLATE};font-weight:700;text-transform:uppercase;letter-spacing:.05em">{label}</div>'
                        f'<div style="font-size:22px;font-weight:800;color:{_TEXT};margin-top:6px">{val}</div>'
                        f'</div></td>'
                )
        return f"""
<tr><td style="padding:18px 28px 4px;background:{_BG}">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
        <tr>
            {card(total, 'Total', _INDIGO)}
            {card(passed, 'Passed', _GREEN)}
            {card(failed, 'Failed', _ROSE)}
            {card(_fmt(duration), 'Duration', _CYAN)}
        </tr>
    </table>
</td></tr>"""


def _build_pass_rate(rate: int) -> str:
    rc = _rate_clr(rate)
    return f"""
<tr>
    <td style="padding:18px 28px;background:{_BG};border-bottom:1px solid {_BORDER}">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td style="font-size:13px;font-weight:700;color:{_SLATE}">Pass Rate</td>
                <td align="right" style="font-size:20px;font-weight:900;color:{rc}">{rate}%</td>
            </tr>
        </table>
        <div style="height:12px;background:{_CARD2};border-radius:6px;overflow:hidden;margin-top:10px;border:1px solid {_BORDER}">
            <div style="width:{rate}%;height:100%;background:{rc};border-radius:6px;box-shadow:0 4px 10px {rc}33"></div>
        </div>
    </td>
</tr>"""


def _build_categories(results: list[dict]) -> str:
    cats: dict[str, dict] = {
        "Timeouts":            {"color": _AMBER,  "tests": []},
        "Assertion Failures":  {"color": _ROSE,   "tests": []},
        "Element Not Found":   {"color": _VIOLET, "tests": []},
        "Navigation Errors":   {"color": _SKY,    "tests": []},
        "Other Errors":        {"color": _MUTED,  "tests": []},
    }
    for r in results:
        if r["status"] not in ("FAILED", "ERROR"):
            continue
        msg = r.get("message", "")
        if   "imeout" in msg or "timed"   in msg.lower(): cats["Timeouts"]["tests"].append(r["name"])
        elif "ssert"  in msg or "assert"  in msg.lower(): cats["Assertion Failures"]["tests"].append(r["name"])
        elif "ocator" in msg or "element" in msg.lower(): cats["Element Not Found"]["tests"].append(r["name"])
        elif "avigat" in msg or "goto"    in msg.lower(): cats["Navigation Errors"]["tests"].append(r["name"])
        else:                                              cats["Other Errors"]["tests"].append(r["name"])

    # render a compact failure list (most useful in emails)
    items = []
    for cat, d in cats.items():
        if d["tests"]:
            for t in d["tests"]:
                items.append((cat, d["color"], t))

    if not items:
        return _section_label("No Failures Detected") + (
            f'<tr><td style="padding:12px 28px 18px;background:{_BG}">'
            f'<div style="padding:14px;border-radius:10px;background:{_CARD2};border:1px solid {_BORDER};'
            f'border-left:3px solid {_GREEN};text-align:center;color:{_GREEN};font-weight:700">All tests passed</div>'
            f'</td></tr>'
        )

    rows = ''
    for cat, clr, test in items[:6]:
        rows += (
            f'<tr><td style="padding:10px 28px;background:{_BG};">'
            f'<div style="display:flex;align-items:center;gap:12px">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{clr}"></div>'
            f'<div style="font-size:13px;color:{_TEXT};font-weight:700">{test}</div>'
            f'<div style="margin-left:auto;color:{_SLATE};font-size:12px">{cat}</div>'
            f'</div></td></tr>'
        )

    if len(items) > 6:
        rows += f'<tr><td style="padding:8px 28px;background:{_BG};color:{_SLATE};font-size:12px">+{len(items)-6} more failing tests</td></tr>'

    return _section_label("Top Failures") + rows


def _build_timeline(results: list[dict]) -> str:
    max_dur = max((r["duration"] for r in results), default=1) or 1
    rows = ""
    for r in results:
        clr   = _st_clr(r["status"])
        width = max(3, int((r["duration"] / max_dur) * 100))
        short = (r["name"][:44] + "…") if len(r["name"]) > 44 else r["name"]
        rows += (
            f'<tr style="border-bottom:1px solid {_BORDER}22">'
            f'<td style="padding:5px 8px 5px 14px;font-size:10px;'
            f'color:{_SLATE};white-space:nowrap;width:230px"'
            f' title="{r["name"]}">{short}</td>'
            f'<td style="padding:5px 14px 5px 0">'
            f'<div style="height:14px;width:{width}%;background:{clr}30;'
            f'border-left:3px solid {clr};border-radius:4px;'
            f'min-width:4px;display:flex;align-items:center;padding-left:6px">'
            f'<span style="font-size:9px;color:{clr};font-weight:700;'
            f'white-space:nowrap">{_fmt(r["duration"])}</span>'
            f'</div></td>'
            f'</tr>'
        )
    # render a compact timeline list
    if not rows:
        return ''
    return _section_label('Timeline') + f'<tr><td style="padding:0 28px 18px;background:{_BG}"><table width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>'


def _build_results(results: list[dict]) -> str:
    rows = ""
    for i, r in enumerate(results):
        st   = r["status"]
        clr  = _st_clr(st)
        ico  = _st_icon(st)
        # use a soft failure background for failed rows, otherwise alternate
        bg = (
            ("#fff5f5" if st in ("FAILED", "ERROR") else (_CARD if i % 2 == 0 else _CARD2))
        )

        err = ""
        if r.get("message"):
            short = r["message"][:110] + ("…" if len(r["message"]) > 110 else "")
            err = f"""<div style="margin-top:5px;padding:6px 10px;background:{_CARD2};border-left:3px solid {_ROSE};border-radius:6px;font-family:Courier New,monospace;font-size:12px;color:{_ROSE};line-height:1.4">{short}</div>"""

        rows += (
            f'<tr style="border-bottom:1px solid {_BORDER};background:{bg}">'
            # index
            f'<td style="padding:11px 6px 11px 14px;font-size:11px;'
            f'color:{_SLATE};font-weight:600;width:24px;vertical-align:top">'
            f'{i+1:02d}</td>'
            # test name + optional error
            f'<td style="padding:11px 8px;vertical-align:top">'
            f'<div style="font-size:12px;font-weight:600;color:{_TEXT}">'
            f'{r["name"]}</div>{err}</td>'
            # status badge
            f'<td align="center" style="padding:11px 8px;'
            f'white-space:nowrap;vertical-align:top">'
            f'{_badge(f"{ico} {st}", clr)}</td>'
            # duration
            f'<td style="padding:11px 14px 11px 8px;text-align:right;'
            f'font-size:11px;color:{_SLATE};white-space:nowrap;vertical-align:top">'
            f'{_fmt(r["duration"])}</td>'
            f'</tr>'
        )

    # compact results table
    return _section_label("Test Results") + _tbl_wrap(["#", "Test Name", "Status", "Time"], rows)


def _build_footer(now: str) -> str:
        return f"""
<tr>
    <td style="padding:14px 28px;background:{_CARD2};
                         border-top:1px solid {_BORDER}">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="font-size:11px;color:{_SLATE}">
          SmartApp QA &nbsp;&middot;&nbsp; Playwright Automation Suite
        </td>
        <td align="right" style="font-size:11px;color:{_SLATE}">
          Auto-generated &nbsp;&middot;&nbsp; {now}
        </td>
      </tr>
    </table>
  </td>
</tr>"""


# ── Full HTML assembler ───────────────────────────────────────────────────────
def _build_html(results: list[dict], duration: float) -> str:
    total   = len(results)
    passed  = sum(1 for r in results if r["status"] == "PASSED")
    failed  = sum(1 for r in results if r["status"] in ("FAILED", "ERROR"))
    skipped = total - passed - failed
    rate    = _pct(passed, total)
    all_ok  = failed == 0
    now     = datetime.datetime.now().strftime("%d %b %Y  %I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>SmartApp QA Report</title>
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;color:{_TEXT};line-height:1.5">

<table width="100%" cellpadding="0" cellspacing="0" style="padding:28px 16px;background:{_BG}">
<tr><td align="center">

<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;background:{_SURF};border-radius:16px;overflow:hidden;border:1px solid {_BORDER};box-shadow:0 6px 18px rgba(16,24,40,0.06)">

    {_build_header(all_ok, now)}
    {_build_stat_cards(total, passed, failed, skipped, duration)}
    {_build_pass_rate(rate)}
    {_build_categories(results)}
    {_build_timeline(results)}
    {_build_results(results)}
    {_build_footer(now)}

</table>

</td></tr>
</table>
</body>
</html>"""


# ── Plain-text fallback ───────────────────────────────────────────────────────
def _build_plain(results: list[dict], duration: float, now: str) -> str:
    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = total - passed
    rate   = _pct(passed, total)
    lines  = [
        "SmartApp QA — Automated Test Report",
        "=" * 46,
        f"Date:      {now}",
        f"Total:     {total}",
        f"Passed:    {passed}",
        f"Failed:    {failed}",
        f"Pass Rate: {rate}%",
        f"Duration:  {_fmt(duration)}",
        "",
        "-" * 46,
        "TEST RESULTS",
        "-" * 46,
    ]
    for r in results:
        lines.append(
            f"[{r['status']:7}]  {r['name']}  ({_fmt(r['duration'])})"
            + (f"\n           ↳ {r['message'][:80]}" if r.get("message") else "")
        )
    lines += [
        "",
        "=" * 46,
        "SmartApp QA  ·  Playwright Automation Suite",
        "Auto-generated — do not reply.",
    ]
    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────
def send_report(
    results:         list[dict],
    duration:        float,
    smtp_host:       str,
    smtp_port:       int,
    sender_email:    str,
    sender_password: str,
    recipients:      list[str],
    subject:         str,
    **_kwargs,       # silently absorb any extra keyword args
) -> None:
    now  = datetime.datetime.now().strftime("%d %b %Y  %I:%M %p")
    html = _build_html(results, duration)
    text = _build_plain(results, duration, now)

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender_email
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    total  = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    print(f"\n📧  Sending to: {', '.join(recipients)}")
    print(f"📊  {passed}/{total} passed  ({_pct(passed, total)}%)")

    with smtplib.SMTP(smtp_host, smtp_port) as srv:
        srv.ehlo()
        srv.starttls()
        srv.login(sender_email, sender_password)
        srv.sendmail(sender_email, recipients, msg.as_string())

    print("✅  Email sent successfully.") 