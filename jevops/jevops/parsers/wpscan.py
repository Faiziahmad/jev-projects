from __future__ import annotations

import json


def parse(content: str) -> list[dict]:
    """Parse wpscan JSON output."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return _parse_plain(content)

    findings = []

    # wordpress version
    wp = data.get("version", {})
    if wp:
        ver = wp.get("number", "unknown")
        status = wp.get("status", "")
        findings.append({
            "tool":       "wpscan",
            "type":       "version",
            "component":  "wordpress",
            "version":    ver,
            "status":     status,
            "cves":       [],
            "references": [],
            "raw":        f"WordPress {ver} ({status})",
        })

    # plugins
    for slug, plugin in (data.get("plugins") or {}).items():
        plugin_ver = (plugin.get("version") or {}).get("number", "unknown")
        for vuln in (plugin.get("vulnerabilities") or []):
            cves = vuln.get("references", {}).get("cve", [])
            findings.append({
                "tool":       "wpscan",
                "type":       "vulnerability",
                "component":  f"plugin:{slug}",
                "version":    plugin_ver,
                "title":      vuln.get("title", ""),
                "fixed_in":   vuln.get("fixed_in", ""),
                "cves":       cves,
                "references": vuln.get("references", {}).get("url", []),
                "raw":        f"{slug} {plugin_ver} — {vuln.get('title', '')}",
            })

    # themes
    for slug, theme in (data.get("themes") or {}).items():
        theme_ver = (theme.get("version") or {}).get("number", "unknown")
        for vuln in (theme.get("vulnerabilities") or []):
            cves = vuln.get("references", {}).get("cve", [])
            findings.append({
                "tool":       "wpscan",
                "type":       "vulnerability",
                "component":  f"theme:{slug}",
                "version":    theme_ver,
                "title":      vuln.get("title", ""),
                "fixed_in":   vuln.get("fixed_in", ""),
                "cves":       cves,
                "references": vuln.get("references", {}).get("url", []),
                "raw":        f"theme:{slug} {theme_ver} — {vuln.get('title', '')}",
            })

    # users
    for user, info in (data.get("users") or {}).items():
        findings.append({
            "tool":      "wpscan",
            "type":      "user",
            "username":  user,
            "found_by":  info.get("found_by", ""),
            "cves":      [],
            "raw":       f"user: {user}",
        })

    return findings


def _parse_plain(content: str) -> list[dict]:
    findings = []
    for line in content.splitlines():
        line = line.strip()
        if "[!]" in line or "[+]" in line:
            findings.append({
                "tool": "wpscan", "type": "raw_line",
                "component": "", "version": "", "title": line,
                "cves": [], "references": [], "fixed_in": "",
                "raw": line,
            })
    return findings
