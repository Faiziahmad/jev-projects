from __future__ import annotations

import argparse
import json
import os
import re
import sys

import yaml

from . import __version__, checks, mailer, report
from .store import Store

_DOMAIN = re.compile(r"^(?=.{3,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")

_EXAMPLE = """\
# Businesses you watch. Only public information is checked.
# Add a client only after they've agreed to the service (consent: yes).
sender: Faizi Ahmad
clients:
  - name: Sarah
    business: Bright Smile Dental
    domain: brightsmile.example
    email: sarah@brightsmile.example
    consent: yes
"""


def _clean(d: str) -> str:
    d = d.strip().lower()
    d = re.sub(r"^[a-z]+://", "", d).split("/")[0].split(":")[0].rstrip(".")
    return d[4:] if d.startswith("www.") else d


def _one(domain: str, store: Store, lookalikes: bool) -> tuple[dict, list]:
    prev = store.last(domain)
    snap = checks.collect(domain, check_lookalikes=lookalikes)
    findings = checks.evaluate(snap, prev)
    store.save(snap, prev)
    return snap, findings


def cmd_check(a: argparse.Namespace) -> int:
    domain = _clean(a.domain)
    if not _DOMAIN.match(domain):
        print(f"Not a valid domain: {a.domain}", file=sys.stderr)
        return 2
    snap, findings = _one(domain, Store(a.state), not a.no_lookalikes)
    if a.json:
        print(json.dumps({"domain": domain, "score": checks.score(findings), "findings": [f.to_dict() for f in findings], "errors": snap["errors"]}, indent=2))
    else:
        print(report.text(domain, findings))
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    with open(a.clients) as f:
        cfg = yaml.safe_load(f) or {}
    sender = cfg.get("sender", "Faizi")
    store = Store(a.state)
    os.makedirs(a.out, exist_ok=True)
    failures = 0
    for c in cfg.get("clients", []):
        domain = _clean(str(c.get("domain", "")))
        if c.get("consent") is not True:
            print(f"skip  {domain or '?'}: no consent recorded")
            continue
        if not _DOMAIN.match(domain):
            print(f"skip  {domain or '?'}: invalid domain")
            continue
        try:
            snap, findings = _one(domain, store, not a.no_lookalikes)
        except Exception as e:
            failures += 1
            print(f"fail  {domain}: {e}")
            continue
        name = c.get("name", "")
        txt = report.text(domain, findings, client=name, sender=sender)
        htm = report.html_report(domain, findings, client=name, sender=sender)
        base = os.path.join(a.out, domain)
        with open(base + ".txt", "w") as f:
            f.write(txt)
        with open(base + ".html", "w") as f:
            f.write(htm)
        status = f"{checks.score(findings):>3}/100  {report.headline(findings)}"
        if a.send and c.get("email"):
            try:
                mailer.send(c["email"], report.subject(domain, findings), txt, htm)
                status += "  (emailed)"
            except Exception as e:
                failures += 1
                status += f"  (email failed: {e})"
        print(f"done  {domain}  {status}")
    return 1 if failures else 0


def cmd_init(a: argparse.Namespace) -> int:
    if os.path.exists(a.path):
        print(f"{a.path} already exists", file=sys.stderr)
        return 1
    with open(a.path, "w") as f:
        f.write(_EXAMPLE)
    print(f"Wrote {a.path}. Edit it, then run: domain-watch run")
    return 0


def run(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="domain-watch", description="Weekly plain-English domain health reports (public information only).")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--state", default="state", help="folder that keeps last week's results (default: state)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check one domain now and print the report")
    c.add_argument("domain")
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-lookalikes", action="store_true", help="skip the look-alike domain search (faster)")
    c.set_defaults(fn=cmd_check)

    r = sub.add_parser("run", help="check every client in the clients file")
    r.add_argument("--clients", default="clients.yaml")
    r.add_argument("--out", default="reports", help="where to save reports (default: reports)")
    r.add_argument("--send", action="store_true", help="email each report (needs DW_SMTP_* settings)")
    r.add_argument("--no-lookalikes", action="store_true")
    r.set_defaults(fn=cmd_run)

    i = sub.add_parser("init", help="create an example clients.yaml")
    i.add_argument("path", nargs="?", default="clients.yaml")
    i.set_defaults(fn=cmd_init)

    a = p.parse_args(argv)
    sys.exit(a.fn(a))


if __name__ == "__main__":
    run()
