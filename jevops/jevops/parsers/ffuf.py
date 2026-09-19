from __future__ import annotations

import json


def parse(content: str) -> list[dict]:
    """Parse ffuf JSON output."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return _parse_plain(content)

    results = data.get("results", [])
    findings = []
    for r in results:
        url    = r.get("url", "")
        status = r.get("status", 0)
        length = r.get("length", 0)
        words  = r.get("words", 0)
        lines  = r.get("lines", 0)
        path   = url.split("://", 1)[-1].split("/", 1)[-1] if "/" in url else url
        path   = "/" + path.lstrip("/")

        findings.append({
            "tool":    "ffuf",
            "type":    "path",
            "url":     url,
            "path":    path,
            "status":  status,
            "length":  length,
            "words":   words,
            "lines":   lines,
            "raw":     f"{status} {path} [{length}b]",
        })
    return findings


def _parse_plain(content: str) -> list[dict]:
    """Parse ffuf plain text output."""
    findings = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # format: /path  [Status: 200, Size: 1234, Words: 42]
        parts = line.split()
        if not parts:
            continue
        path = parts[0]
        status = 0
        length = 0
        for p in parts:
            if p.startswith("[Status:"):
                try:
                    status = int(p.replace("[Status:", "").strip(",]"))
                except ValueError:
                    pass
            if p.startswith("Size:"):
                try:
                    length = int(p.replace("Size:", "").strip(",]"))
                except ValueError:
                    pass
        findings.append({
            "tool": "ffuf", "type": "path",
            "url": path, "path": path,
            "status": status, "length": length,
            "words": 0, "lines": 0,
            "raw": f"{status} {path} [{length}b]",
        })
    return findings
