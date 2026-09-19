from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Union


def parse(content: str) -> list[dict]:
    """Parse nmap XML output into structured findings."""
    findings = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        # try as plain text grepable output
        return _parse_gnmap(content)

    for host in root.findall("host"):
        addr_el = host.find("address")
        if addr_el is None:
            continue
        addr = addr_el.get("addr", "unknown")

        hostname = ""
        hn_el = host.find("hostnames/hostname")
        if hn_el is not None:
            hostname = hn_el.get("name", "")

        for port in host.findall("ports/port"):
            state_el = port.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue

            portid = int(port.get("portid", 0))
            protocol = port.get("protocol", "tcp")

            svc = port.find("service")
            service = svc.get("name", "") if svc is not None else ""
            product = svc.get("product", "") if svc is not None else ""
            version = svc.get("version", "") if svc is not None else ""
            extra   = svc.get("extrainfo", "") if svc is not None else ""
            tunnel  = svc.get("tunnel", "") if svc is not None else ""

            version_str = " ".join(filter(None, [product, version, extra])).strip()
            display = f"{portid}/{protocol} open {service} {version_str}".strip()

            findings.append({
                "tool":     "nmap",
                "type":     "port",
                "host":     addr,
                "hostname": hostname,
                "port":     portid,
                "protocol": protocol,
                "service":  service,
                "version":  version_str,
                "tunnel":   tunnel,
                "raw":      display,
            })

    return findings


def _parse_gnmap(content: str) -> list[dict]:
    findings = []
    for line in content.splitlines():
        if "open" not in line or not line.startswith("Host:"):
            continue
        parts = line.split()
        host = parts[1] if len(parts) > 1 else "unknown"
        for token in parts:
            if "/open/" in token:
                segments = token.split("/")
                portid   = int(segments[0]) if segments[0].isdigit() else 0
                protocol = segments[1] if len(segments) > 1 else "tcp"
                service  = segments[4] if len(segments) > 4 else ""
                findings.append({
                    "tool": "nmap", "type": "port",
                    "host": host, "hostname": "", "port": portid,
                    "protocol": protocol, "service": service,
                    "version": "", "tunnel": "",
                    "raw": f"{portid}/{protocol} open {service}",
                })
    return findings
