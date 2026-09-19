from __future__ import annotations


def parse(content: str) -> list[dict]:
    """Parse gobuster plaintext output."""
    findings = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("=") or line.startswith("/usr") or "Error" in line:
            continue
        if not line.startswith("/"):
            continue

        # format: /path  (Status: 200) [Size: 1234]
        # or:     /path  (Status: 301) [--> /path/]
        parts = line.split()
        path = parts[0]
        status = 0
        length = 0
        redirect = ""

        for i, p in enumerate(parts):
            if p.startswith("(Status:"):
                try:
                    status = int(p.replace("(Status:", "").strip(",)"))
                except ValueError:
                    pass
            if p == "[Size:":
                try:
                    length = int(parts[i + 1].strip("]"))
                except (IndexError, ValueError):
                    pass
            if p == "[-->":
                redirect = parts[i + 1].strip("]") if i + 1 < len(parts) else ""

        findings.append({
            "tool":     "gobuster",
            "type":     "path",
            "path":     path,
            "url":      path,
            "status":   status,
            "length":   length,
            "redirect": redirect,
            "words":    0,
            "lines":    0,
            "raw":      f"{status} {path}" + (f" → {redirect}" if redirect else ""),
        })
    return findings
