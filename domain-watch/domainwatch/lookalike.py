"""Generate common look-alike versions of a domain (typos, swapped letters,
similar-looking characters, other endings). Only used for public DNS lookups."""
from __future__ import annotations

import re

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_GLYPHS = {"o": ["0"], "0": ["o"], "l": ["1", "i"], "i": ["1", "l"], "1": ["l", "i"], "m": ["rn"], "w": ["vv"], "e": ["3"], "a": ["4"], "s": ["5"]}
_MULTI = {"rn": "m", "vv": "w", "cl": "d"}
_TLDS = ["com", "net", "org", "co", "io", "info", "biz", "online", "shop"]


def split(domain: str) -> tuple[str, str]:
    """'shop.example.co.uk' is kept simple: the first label is the name, the rest is the ending."""
    name, _, tld = domain.partition(".")
    return name, tld


def variants(domain: str, limit: int = 80) -> list[str]:
    name, tld = split(domain.lower())
    if not name or not tld:
        return []
    out: list[str] = []

    def add(n: str, t: str = tld) -> None:
        if _LABEL.match(n) and (n, t) != (name, tld):
            d = f"{n}.{t}"
            if d not in out:
                out.append(d)

    # other endings first: these are the most commonly registered
    for t in _TLDS:
        add(name, t)
    for i, ch in enumerate(name):
        for g in _GLYPHS.get(ch, []):
            add(name[:i] + g + name[i + 1:])
    for pair, rep in _MULTI.items():
        if pair in name:
            add(name.replace(pair, rep, 1))
    for i in range(len(name)):
        add(name[:i] + name[i + 1:])                      # missing letter
    for i in range(len(name) - 1):
        add(name[:i] + name[i + 1] + name[i] + name[i + 2:])  # swapped letters
    for i in range(len(name)):
        add(name[:i] + name[i] + name[i:])                # doubled letter
    for extra in ("-online", "-support", "-billing", "-login", "-secure"):
        add(name + extra)
    return out[:limit]
