"""Collect a weekly snapshot of public domain facts, then compare it with last
week's to produce plain-English findings."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from types import ModuleType
from typing import Callable, Optional

from . import lookalike
from . import net as default_net

GOOD, WARN, BAD, INFO = "good", "warn", "bad", "info"


@dataclass
class Finding:
    key: str
    title: str
    status: str
    summary: str
    fix: str = ""
    details: list[str] = field(default_factory=list)
    new: bool = False  # changed since last week

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- collect

def collect(domain: str, net: ModuleType = default_net, check_lookalikes: bool = True, workers: int = 8) -> dict:
    """Gather public facts about a domain. Each item fails on its own without stopping the rest."""
    snap: dict = {"domain": domain, "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "errors": {}}

    def safe(key: str, fn: Callable, *args):
        try:
            snap[key] = fn(*args)
        except Exception as e:  # recorded, reported as "couldn't check"
            snap[key] = None
            snap["errors"][key] = str(e)[:200]

    def root_txt():
        r = net.txt(domain)
        if r["status"] == 3:
            raise ValueError("domain not found")
        return r

    def mx():
        return sorted(net.dns(domain, "MX")["answers"])

    def ns():
        return sorted(net.dns(domain, "NS")["answers"])

    def dmarc():
        return [t for t in net.txt("_dmarc." + domain)["answers"] if t.lower().startswith("v=dmarc1")]

    def mta_sts():
        return [t for t in net.txt("_mta-sts." + domain)["answers"] if t.lower().startswith("v=stsv1")]

    tasks = {
        "root_txt": root_txt, "mx": mx, "ns": ns, "dmarc": dmarc, "mta_sts": mta_sts,
        "cert": lambda: net.cert_info(domain),
        "https_redirect": lambda: net.http_upgrades_to_https(domain),
        "domain_expiry": lambda: net.rdap_expiry(domain),
        "web_addresses": lambda: net.ct_names(domain),
    }
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {k: ex.submit(safe, k, fn) for k, fn in tasks.items()}
        for f in futs.values():
            f.result()

    rt = snap.pop("root_txt")
    snap["spf"] = [t for t in (rt or {}).get("answers", []) if t.lower().startswith("v=spf1")] if rt else None
    snap["dnssec"] = bool(rt and rt.get("ad"))
    if rt is None and "root_txt" in snap["errors"]:
        snap["errors"]["spf"] = snap["errors"].pop("root_txt")

    if check_lookalikes:
        cands = lookalike.variants(domain)
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                hits = list(ex.map(net.resolves, cands))
            snap["lookalikes"] = sorted(d for d, hit in zip(cands, hits) if hit)
        except Exception as e:
            snap["lookalikes"] = None
            snap["errors"]["lookalikes"] = str(e)[:200]
    return snap


# ---------------------------------------------------------------- evaluate

def _days_until(iso: str, now: datetime) -> int:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - now).days


def _email(snap: dict) -> Finding:
    f = Finding("email", "Protection against fake emails in your name", INFO, "")
    spf, dmarc = snap.get("spf"), snap.get("dmarc")
    if spf is None or dmarc is None:
        f.summary = "We couldn't check this week. We'll try again next week."
        return f
    policy = ""
    if dmarc:
        m = re.search(r"(?:^|;)\s*p\s*=\s*(\w+)", dmarc[0], re.I)
        policy = m.group(1).lower() if m else ""
    spf_ok = len(spf) == 1 and re.search(r"[~-]all\b", spf[0], re.I) is not None
    f.details = spf + dmarc
    if spf_ok and policy in ("reject", "quarantine"):
        f.status = GOOD
        f.summary = "Fake emails pretending to be you get " + ("blocked." if policy == "reject" else "sent to spam.")
    elif not dmarc or not spf:
        f.status = BAD
        missing = " and ".join(x for x, ok in (("sender list (SPF)", bool(spf)), ("fake-email rule (DMARC)", bool(dmarc))) if not ok)
        f.summary = f"Anyone could send emails that look like they're from you. Missing: {missing}."
        f.fix = "Add the missing records at your domain provider. Reply to this email and I'll send the exact values or set it up for you."
    else:
        f.status = WARN
        f.summary = "Partly protected: fake emails can still get through."
        f.fix = "Tighten your settings: make the SPF record end in ~all or -all, and set DMARC to p=quarantine, then p=reject."
    return f


def _cert(snap: dict, now: datetime) -> Finding:
    f = Finding("cert", "Website padlock certificate", INFO, "")
    c = snap.get("cert")
    if not c:
        f.summary = "We couldn't open your website securely this week. It may be down, or the certificate may have a problem."
        f.status = WARN
        f.fix = "Open your website in a browser and check for a padlock. If there's a warning, contact your web host."
        return f
    days = _days_until(c["expires"], now)
    f.details = [f"Expires {c['expires'][:10]}" + (f" · issued by {c['issuer']}" if c.get("issuer") else "")]
    if days < 0:
        f.status, f.summary = BAD, "Your padlock certificate has expired. Visitors see a security warning."
    elif days <= 14:
        f.status, f.summary = BAD, f"Your padlock certificate expires in {days} days."
    elif days <= 30:
        f.status, f.summary = WARN, f"Your padlock certificate expires in {days} days."
    else:
        f.status, f.summary = GOOD, f"Valid for another {days} days."
    if f.status != GOOD:
        f.fix = "Renew it with your web host, or turn on automatic renewal (free with Let's Encrypt)."
    return f


def _redirect(snap: dict) -> Finding:
    v = snap.get("https_redirect")
    if v is True:
        return Finding("https", "Visitors are sent to the secure version", GOOD, "People who type your address without https:// still get the padlock.")
    if v is False:
        return Finding("https", "Visitors are sent to the secure version", WARN, "People who type your address without https:// get an unprotected page.",
                       fix="Ask your web host to redirect all http:// visits to https:// (usually a single setting).")
    return Finding("https", "Visitors are sent to the secure version", INFO, "We couldn't confirm this week.")


def _domain_expiry(snap: dict, now: datetime) -> Finding:
    f = Finding("domain", "Domain name registration", INFO, "")
    exp = snap.get("domain_expiry")
    if not exp and "domain_expiry" in snap.get("errors", {}):
        f.summary = "We couldn't reach the public registration records this week."
        return f
    if not exp:
        f.summary = "Your domain provider doesn't publish the renewal date, so we can't track it."
        return f
    days = _days_until(exp, now)
    f.details = [f"Renews by {exp[:10]}"]
    if days <= 30:
        f.status, f.summary = BAD, f"Your domain name expires in {days} days. If it lapses, your website and email stop working."
    elif days <= 60:
        f.status, f.summary = WARN, f"Your domain name expires in {days} days."
    else:
        f.status, f.summary = GOOD, f"Registered for another {days} days."
    if f.status != GOOD:
        f.fix = "Renew it at your domain provider and switch on auto-renew."
    return f


def _web_addresses(snap: dict, prev: Optional[dict]) -> Finding:
    cur = snap.get("web_addresses")
    f = Finding("addresses", "Public web addresses for your domain", INFO, "")
    if cur is None:
        f.summary = "The public certificate log didn't respond this week. We'll check again next week."
        return f
    before = (prev or {}).get("web_addresses")
    if before is None:
        f.summary = f"We found {len(cur)} public web address{'es' if len(cur) != 1 else ''}. We'll let you know when new ones appear."
        f.details = cur[:25] + ([f"…and {len(cur) - 25} more"] if len(cur) > 25 else [])
        return f
    new = sorted(set(cur) - set(before))
    if new:
        f.status, f.new = WARN, True
        f.summary = f"{len(new)} new web address{'es' if len(new) != 1 else ''} appeared this week."
        f.details = new
        f.fix = "Make sure you recognise these. Forgotten test or old sites are a common weak spot."
    else:
        f.status, f.summary = GOOD, "No new web addresses this week."
    return f


def _lookalikes(snap: dict, prev: Optional[dict]) -> Finding:
    cur = snap.get("lookalikes")
    f = Finding("lookalikes", "Look-alike domains", INFO, "")
    if cur is None:
        f.summary = "We couldn't check look-alike domains this week."
        return f
    before = (prev or {}).get("lookalikes")
    new = sorted(set(cur) - set(before or []))
    if before is not None and new:
        f.status, f.new = BAD, True
        f.summary = f"{len(new)} new look-alike domain{'s were' if len(new) != 1 else ' was'} registered this week. These are often used to trick customers."
        f.details = new
        f.fix = "Warn your team and customers to double-check email addresses. If one is copying your brand, you can report it to the domain provider."
    elif cur:
        f.status = INFO
        f.summary = f"{len(cur)} look-alike domain{'s exist' if len(cur) != 1 else ' exists'}. We'll alert you if more appear."
        f.details = cur
    else:
        f.status, f.summary = GOOD, "No look-alike domains found."
    return f


def _changes(snap: dict, prev: Optional[dict]) -> Optional[Finding]:
    if not prev:
        return None
    labels = {"mx": "Where your email is delivered (MX)", "ns": "Who controls your domain settings (NS)", "spf": "Your email sender list (SPF)", "dmarc": "Your fake-email rule (DMARC)"}
    changed = []
    for k, label in labels.items():
        a, b = prev.get(k), snap.get(k)
        if a is not None and b is not None and sorted(a) != sorted(b):
            changed.append(f"{label}: {', '.join(a) or 'none'} → {', '.join(b) or 'none'}")
    if not changed:
        return Finding("changes", "Important settings", GOOD, "No changes since last week.")
    return Finding("changes", "Important settings changed", WARN,
                   "Some important domain settings changed this week.", details=changed, new=True,
                   fix="If you or your IT person made this change, all good. If not, look into it straight away.")


def evaluate(snap: dict, prev: Optional[dict] = None, now: Optional[datetime] = None) -> list[Finding]:
    now = now or datetime.now(timezone.utc)
    out = [_email(snap), _cert(snap, now), _redirect(snap), _domain_expiry(snap, now), _web_addresses(snap, prev)]
    if "lookalikes" in snap:  # absent when the look-alike search was switched off
        out.append(_lookalikes(snap, prev))
    ch = _changes(snap, prev)
    if ch:
        out.append(ch)
    return out


_WEIGHTS = {"email": 40, "cert": 20, "https": 10, "domain": 15, "lookalikes": 10, "addresses": 5}
_POINTS = {GOOD: 1.0, INFO: 0.7, WARN: 0.4, BAD: 0.0}


def score(findings: list[Finding]) -> int:
    total = got = 0.0
    for f in findings:
        w = _WEIGHTS.get(f.key)
        if w:
            total += w
            got += w * _POINTS[f.status]
    return round(100 * got / total) if total else 0
