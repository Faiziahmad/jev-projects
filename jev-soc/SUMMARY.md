# jev-soc

SOC alert triage powered by TypeSafe Jev. Every alert gets a fast triage pass (true positive probability, severity, category, action) then runs through a lifecycle FSM built on jev-fsm. Auto-closes noise, auto-pages critical threats, routes everything else to the right human.

$40/day to triage 1M alerts.

## Status
Working. CLI ships. Simulation with 5 real-world scenarios passing.

## Usage
```bash
pip install -e .
export TYPESAFE_API_KEY=...

# single alert
jev-soc alert --alert '{"alert_id":"ALT-001","source":"crowdstrike","rule":"PsExec lateral movement","host":"WS-04","user":"jsmith","indicators":["psexec.exe","admin$"]}'

# from file
jev-soc alert --alert-file alert.json

# batch
jev-soc batch alerts.json

# simulation (5 built-in scenarios)
jev-soc simulate

# JSON output for SIEM integration
jev-soc simulate --json
```

## QA Results
| Alert | TP Prob | Severity | Category | Action | Result |
|---|---|---|---|---|---|
| SIM-001: Login from known IP | 0.05 | INFO | other | ✓ AUTO-CLOSE | ✓ |
| SIM-002: Ransomware file changes | 0.96 | CRITICAL | malware | 🚨 IMMEDIATE | ✓ |
| SIM-003: SSH brute force 847 attempts | 0.91 | HIGH | brute_force | ↑ L2 → resolved | ✓ |
| SIM-004: Insider data exfil (resigned user) | 0.74 | HIGH | data_exfiltration | ↑ L2 → resolved | ✓ |
| SIM-005: PsExec lateral movement | 0.81 | HIGH | lateral_movement | 🚨 IMMEDIATE → escalated | ✓ |

## Architecture
```
alert input
    ↓
triage_alert()          ← Jev: tp_prob + severity + category + action (1 API call)
    ↓
auto-close?  ──yes──→  done (skip FSM)
auto-page?   ──yes──→  done (skip FSM)
    ↓ no
run_lifecycle()         ← jev-fsm: new → triaging → investigating → escalated → resolved
    ↓
SOCResult
```

## Ship targets
- [ ] SIEM webhook listener — ingest Splunk/Sentinel/CrowdStrike alerts in real time
- [ ] Slack/PagerDuty integration — post triage results, page on critical
- [ ] Dashboard — live alert queue with Jev scores
- [ ] Tune thresholds per alert source/rule type

## Files
```
jev-soc/
├── jevsoc/
│   ├── __init__.py
│   ├── triage.py      Jev triage pass (4 questions in 1 call)
│   ├── lifecycle.py   FSM built on jev-fsm
│   ├── pipeline.py    process_alert(), process_batch()
│   └── cli.py         alert / batch / simulate commands
└── pyproject.toml
```

## Dependency
Built on jev-fsm. Alert lifecycle = probabilistic state machine.
