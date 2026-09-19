from . import nmap, ffuf, gobuster, wpscan

PARSERS = {
    "nmap":     nmap.parse,
    "ffuf":     ffuf.parse,
    "gobuster": gobuster.parse,
    "wpscan":   wpscan.parse,
}

def parse(content: str, tool: str) -> list[dict]:
    fn = PARSERS.get(tool)
    if not fn:
        raise ValueError(f"no parser for tool '{tool}'. available: {list(PARSERS)}")
    return fn(content)
