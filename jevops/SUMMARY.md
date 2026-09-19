# jevops

Pentest findings classifier powered by TypeSafe Jev. Reads tool output, classifies every finding with calibrated probability, routes the engagement forward. One Jev API call per tool run regardless of finding count — batch classification.

## Status
Working. Parsers for nmap/gobuster/ffuf/wpscan. Campaign session with routing.

## Usage
```bash
pip install -e .
export TYPESAFE_API_KEY=...

# classify nmap XML
jevops nmap scan.xml --target 10.0.0.5

# classify gobuster/ffuf output
jevops paths gobuster.txt --format gobuster --target 10.0.0.5
jevops paths ffuf_output.json --format ffuf

# classify wpscan
jevops wpscan wpscan.json --target 10.0.0.5

# full campaign session
jevops session start --target 10.0.0.5
jevops session add --tool nmap --file scan.xml
jevops session add --tool gobuster --file paths.txt
jevops session route          # Jev recommends next phase
jevops session report         # full ranked findings

# JSON output for scripting
jevops nmap scan.xml --json | jq '.[] | select(.classification.tier == "critical")'
```

## QA Results
| Test | Result |
|---|---|
| nmap: MySQL 3306 ranked HIGH above Apache 80/443 | ✓ |
| gobuster: /.git, /config.php.bak, /admin CRITICAL | ✓ |
| gobuster: /favicon.ico, /index.html INFO → skip | ✓ |
| wpscan: wp-file-manager RCE → CRITICAL exploit | ✓ |
| wpscan: WP version outdated → LOW, needs_research | ✓ |
| Campaign session accumulates findings correctly | ✓ |
| Route: with .git + admin + mysql → exploitation 0.80 | ✓ |
| needs_human: 0.82 — correctly flags human review | ✓ |

## Key Behaviors
- **Batch classification**: all findings in ONE Jev API call — ~200ms regardless of count
- **Ranked output**: critical → high → medium → low → info
- **Campaign session**: findings accumulate across tools, route() reads full picture
- **needs_human flag**: Jev tells you when to pause for human review
- No hallucinated vulns — calibrated probability only

## Files
```
jevops/
├── jevops/
│   ├── classify.py      batch Jev classifiers (ports/paths/vulns/route)
│   ├── session.py       campaign session management
│   ├── parsers/
│   │   ├── nmap.py      XML + grepable
│   │   ├── ffuf.py      JSON + plaintext
│   │   ├── gobuster.py  plaintext
│   │   └── wpscan.py    JSON + plaintext
│   └── cli.py           nmap/paths/wpscan/session commands
├── tests/               sample tool outputs for QA
└── pyproject.toml
```
