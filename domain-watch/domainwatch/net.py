"""Public lookups only: DNS over HTTPS, the public certificate log, RDAP, and
one ordinary HTTPS visit to the homepage. Nothing here probes or tests a site."""
from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

USER_AGENT = "domain-watch/0.1 (weekly domain health report)"
TIMEOUT = 12

_RESOLVERS = [
    "https://dns.google/resolve?name={name}&type={type}&do=1",
    "https://cloudflare-dns.com/dns-query?name={name}&type={type}&do=1",
]
_TYPE_NUM = {"A": 1, "NS": 2, "MX": 15, "TXT": 16, "AAAA": 28, "CAA": 257}


class LookupError_(Exception):
    """A public lookup service could not be reached."""


def http_json(url: str, timeout: int = TIMEOUT, headers: Optional[dict] = None) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def dns(name: str, rtype: str) -> dict:
    """Return {'status': int, 'answers': [str], 'ad': bool}. Status 3 = name does not exist."""
    last: Exception | None = None
    for tmpl in _RESOLVERS:
        try:
            data = http_json(tmpl.format(name=name, type=rtype), headers={"Accept": "application/dns-json"})
            answers = [a["data"] for a in data.get("Answer", []) if a.get("type") == _TYPE_NUM[rtype]]
            return {"status": data.get("Status", 2), "answers": answers, "ad": bool(data.get("AD"))}
        except Exception as e:  # try the next resolver
            last = e
    raise LookupError_(f"DNS lookup failed for {name} {rtype}: {last}")


def txt_join(data: str) -> str:
    """'"v=spf1 " "include:x"' -> 'v=spf1 include:x'"""
    parts, cur, inq, esc = [], "", False, False
    for ch in data:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            if inq:
                parts.append(cur)
                cur = ""
            inq = not inq
        elif inq:
            cur += ch
    return "".join(parts) if parts else data


def txt(name: str) -> dict:
    r = dns(name, "TXT")
    r["answers"] = [txt_join(a) for a in r["answers"]]
    return r


def resolves(name: str) -> bool:
    """True if the name has a web (A) or mail (MX) record."""
    for t in ("A", "MX"):
        try:
            if dns(name, t)["answers"]:
                return True
        except LookupError_:
            pass
    return False


def cert_info(host: str, port: int = 443, timeout: int = TIMEOUT) -> dict:
    """One normal HTTPS handshake, the same as a browser visit. Returns expiry and issuer."""
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            cert = s.getpeercert()
    not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), tz=timezone.utc)
    issuer = dict(x[0] for x in cert.get("issuer", ()))
    return {"expires": not_after.isoformat(), "issuer": issuer.get("organizationName", "")}


def http_upgrades_to_https(domain: str, timeout: int = TIMEOUT) -> Optional[bool]:
    """Visit http://domain once and see whether it sends visitors to https://."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(f"http://{domain}/", headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        r = opener.open(req, timeout=timeout)
        return False if r.status < 300 else None
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            return (e.headers.get("Location") or "").lower().startswith("https://")
        return None
    except Exception:
        return None


def ct_names(domain: str, timeout: int = 40) -> list[str]:
    """Web addresses listed in the public certificate log (crt.sh) for this domain."""
    data = http_json(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=timeout)
    names: set[str] = set()
    for row in data if isinstance(data, list) else []:
        for n in str(row.get("name_value", "")).lower().split("\n"):
            n = n.strip().lstrip("*.").rstrip(".")
            if n == domain or n.endswith("." + domain):
                names.add(n)
    return sorted(names)


def rdap_expiry(domain: str) -> Optional[str]:
    """Registration expiry date from public RDAP data, if published."""
    data = http_json(f"https://rdap.org/domain/{domain}")
    for ev in data.get("events", []) if isinstance(data, dict) else []:
        if ev.get("eventAction") == "expiration" and ev.get("eventDate"):
            return ev["eventDate"]
    return None
