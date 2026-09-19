# jevops Blueprint

## Problem
Pentest workflows are manual and noisy. nmap dumps 300 lines, you eyeball it. ffuf returns 400 paths, you grep for juicy ones. Hydra runs blind. No calibrated signal — just raw output and human intuition.

## Solution
jevops reads tool output, classifies every finding with Jev, and routes the engagement forward. Jev never hallucinates a vuln — it returns calibrated probability. You get a ranked, typed signal from every tool run.

---

## Architecture

```
tool run → raw output → parser → finding objects → Jev classify → ranked results + next action
```

Three layers:

### 1. Parsers (per-tool)
Each tool gets a lightweight parser that pulls structured findings from raw output.
- `nmap_parser`   → list of {port, service, version, state}
- `ffuf_parser`   → list of {path, status_code, size, words}
- `gobuster_parser` → list of {path, status_code}
- `wpscan_parser` → list of {vuln, cve, severity}
- `hydra_parser`  → list of {credential, service, host}
- `curl_parser`   → {headers, status, tech_stack}

### 2. Classifiers (Jev calls)
Each finding type gets a Jev classification:

**Port/Service finding:**
- `interesting`: Score — how interesting is this for attack?
- `attack_vector`: Choice — web/ssh/smb/database/iot/other
- `next_tool`: Choice — ffuf/gobuster/hydra/burp/manual/skip

**Directory/Path finding:**
- `juicy`: Noul — does this path look like a high-value target?
- `tier`: Choice — admin/api/backup/upload/config/standard
- `action`: Choice — investigate_manually/fuzz_further/add_to_wordlist/skip

**Vulnerability finding:**
- `exploitable`: Noul — likely exploitable given context?
- `severity`: Score — info/low/medium/high/critical
- `effort`: Choice — trivial/moderate/complex/needs_research

**Credential finding:**
- `reuse_risk`: Noul — likely reused elsewhere?
- `privilege_level`: Choice — admin/user/service/unknown

### 3. Campaign Router
After classifying all findings, Jev picks the next move for the whole engagement:
- Which target to hit next
- Which tool to run
- Whether to pause for human review
- Whether engagement is complete

---

## CLI Design

```bash
# classify nmap output
jevops nmap scan.xml
jevops nmap scan.xml --target 192.168.1.1 --json

# classify ffuf/gobuster output
jevops paths ffuf_output.json
jevops paths gobuster.txt --format gobuster

# classify wpscan
jevops wpscan wpscan_output.json

# classify raw curl headers
jevops headers --url https://target.com

# route: given all findings so far, what next?
jevops next --findings session.json

# full campaign session
jevops session start --target 192.168.1.1
jevops session add-finding --file nmap.xml --tool nmap
jevops session route   # Jev decides next move
jevops session report  # full ranked finding list
```

---

## Finding Schema
```json
{
  "id": "F-001",
  "tool": "nmap",
  "type": "port",
  "raw": "80/tcp open http Apache 2.2.34",
  "data": {"port": 80, "service": "http", "version": "Apache 2.2.34"},
  "classification": {
    "interesting": 0.94,
    "attack_vector": "web",
    "next_tool": "ffuf",
    "confidence": 0.88
  },
  "tier": "high"
}
```

---

## File Structure
```
jevops/
├── BLUEPRINT.md
├── SUMMARY.md
├── pyproject.toml
└── jevops/
    ├── __init__.py
    ├── classify.py      Jev classifiers per finding type
    ├── session.py       Campaign session — findings store + routing
    ├── parsers/
    │   ├── __init__.py
    │   ├── nmap.py
    │   ├── ffuf.py
    │   ├── gobuster.py
    │   ├── wpscan.py
    │   └── generic.py   fallback line parser
    └── cli.py           nmap/paths/wpscan/headers/next/session commands
```

---

## QA Test Cases
1. nmap XML with mixed ports → interesting ones ranked high, ssh/smb flagged
2. ffuf output → /admin, /backup, /.git ranked above /index, /favicon
3. wpscan vuln → exploitable probability returned, severity correct
4. gobuster plain text → parsed and classified correctly
5. Campaign router — given nmap + ffuf findings, Jev picks next tool
6. Gate test — hydra suggested, Jev gates: needs_authorization before proceeding
7. Credential finding — admin cred flagged for reuse check
8. Empty/no-findings input → degrades gracefully
