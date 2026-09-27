"""Turn findings into a short plain-English weekly email (text + HTML)."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Optional

from .checks import BAD, GOOD, INFO, WARN, Finding, score

_ICON = {GOOD: "✓", WARN: "!", BAD: "✕", INFO: "•"}
_COLOR = {GOOD: "#12a150", WARN: "#d97706", BAD: "#e5484d", INFO: "#737987"}
_ORDER = {BAD: 0, WARN: 1, INFO: 2, GOOD: 3}


def headline(findings: list[Finding]) -> str:
    bad = sum(f.status == BAD for f in findings)
    warn = sum(f.status == WARN for f in findings)
    new = sum(f.new for f in findings)
    if not bad and not warn:
        return "All good this week. Nothing needs your attention."
    parts = []
    if bad:
        parts.append(f"{bad} thing{'s' if bad != 1 else ''} to fix soon")
    if warn:
        parts.append(f"{warn} to keep an eye on")
    tail = f" ({new} new this week)" if new else ""
    return ", ".join(parts).capitalize() + tail + "."


def subject(domain: str, findings: list[Finding]) -> str:
    bad = sum(f.status == BAD for f in findings)
    new = sum(f.new for f in findings)
    if bad:
        return f"{domain}: {bad} thing{'s' if bad != 1 else ''} need{'s' if bad == 1 else ''} attention"
    if new:
        return f"{domain}: something changed this week"
    return f"{domain}: all good this week"


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (_ORDER[f.status], not f.new))


def text(domain: str, findings: list[Finding], client: str = "", sender: str = "Faizi", when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    lines = [f"Hi {client}," if client else "Hi,", "",
             f"Here's your weekly domain health report for {domain} ({when:%d %b %Y}).",
             f"Score: {score(findings)}/100. {headline(findings)}", ""]
    for f in _sorted(findings):
        lines.append(f"{_ICON[f.status]} {f.title}{'  [NEW]' if f.new else ''}")
        lines.append(f"  {f.summary}")
        for d in f.details[:10]:
            lines.append(f"    - {d}")
        if f.fix:
            lines.append(f"  What to do: {f.fix}")
        lines.append("")
    lines += ["Questions? Just reply to this email.", "", sender,
              "", "This report only uses public information. Nothing on your website was tested."]
    return "\n".join(lines)


def html_report(domain: str, findings: list[Finding], client: str = "", sender: str = "Faizi", when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    e = html.escape
    sc = score(findings)
    ring = "#12a150" if sc >= 85 else "#d97706" if sc >= 60 else "#e5484d"
    rows = []
    for f in _sorted(findings):
        c = _COLOR[f.status]
        det = "".join(f'<div style="font:12px/1.5 Menlo,monospace;color:#737987">{e(d)}</div>' for d in f.details[:10])
        fix = f'<div style="margin-top:8px;padding:10px 12px;background:#f3f4f7;border-radius:8px;font-size:13px"><b>What to do:</b> {e(f.fix)}</div>' if f.fix else ""
        new = ' <span style="font-size:11px;font-weight:700;color:#fff;background:#2f74f5;border-radius:99px;padding:2px 7px">NEW</span>' if f.new else ""
        rows.append(
            f'<tr><td style="padding:14px 0;border-top:1px solid #eceef2;vertical-align:top;width:34px">'
            f'<div style="width:26px;height:26px;border-radius:8px;background:{c}1f;color:{c};font-weight:700;text-align:center;line-height:26px">{_ICON[f.status]}</div></td>'
            f'<td style="padding:14px 0;border-top:1px solid #eceef2"><div style="font-weight:600">{e(f.title)}{new}</div>'
            f'<div style="color:#454a55;font-size:14px;margin-top:2px">{e(f.summary)}</div>{det}{fix}</td></tr>')
    return f"""<!doctype html><html><body style="margin:0;background:#f5f6f8;font:15px/1.55 -apple-system,Segoe UI,Inter,Arial,sans-serif;color:#0f1115">
<div style="max-width:600px;margin:0 auto;padding:24px 16px">
<div style="background:#fff;border:1px solid #e6e8ee;border-radius:16px;padding:24px">
<div style="font:12px Menlo,monospace;color:#737987">WEEKLY DOMAIN HEALTH · {when:%d %b %Y}</div>
<h1 style="font-size:22px;margin:6px 0 4px">{e(domain)}</h1>
<p style="margin:0 0 16px;color:#454a55">{e(f"Hi {client}, " if client else "")}{e(headline(findings))}</p>
<div style="display:inline-block;padding:8px 14px;border-radius:10px;background:{ring}1a;color:{ring};font-weight:700">Score {sc}/100</div>
<table style="width:100%;border-collapse:collapse;margin-top:16px">{''.join(rows)}</table>
<p style="margin:18px 0 0;color:#454a55">Questions? Just reply to this email.<br>{e(sender)}</p>
</div>
<p style="text-align:center;color:#8a90a0;font-size:12px;margin-top:14px">This report only uses public information. Nothing on your website was tested.</p>
</div></body></html>"""
