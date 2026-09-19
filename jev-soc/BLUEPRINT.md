# jev-soc Blueprint

## Problem
SOC alert queues are brutal. 1000s of alerts/day, 80%+ are false positives. L1 analysts spend hours on noise. LLM triage is too slow and expensive at scale. Rule-based filters miss novel attacks.

## Solution
jev-soc sits in front of the alert queue. Every alert hits Jev first:
- True positive probability
- Severity tier
- Attack category
- Recommended action
- Confidence gate → auto-close / auto-escalate / human review

Built ON TOP of jev-fsm. Alert lifecycle is a state machine:
new → triaging → investigating → escalated → resolved / false_positive

At $0.00004/call: triage 1M alerts/day for $40.

---

## Alert Lifecycle (FSM states)

```
new → triaging → investigating → escalated → resolved
                              ↘ false_positive
                 ↘ false_positive
```

## Triage Decision Layer (direct Jev calls, not FSM)

Before the FSM runs, a fast triage pass scores the raw alert:

```
true_positive    Noul   — is this a real threat?
severity         Score  — info / low / medium / high / critical
category         Choice — malware/phishing/brute_force/data_exfil/insider/lateral_movement/recon/other
action           Choice — auto_close / l1_investigate / l2_escalate / l3_page / immediate_response
```

If true_positive < 0.15 → auto_close (don't even enter FSM)
If true_positive > 0.90 AND severity = critical → immediate_response
Otherwise → enter FSM at triaging state

---

## Input: Alert Schema
```json
{
  "alert_id": "ALT-1234",
  "source": "crowdstrike",
  "rule": "Possible lateral movement via PsExec",
  "severity_raw": "high",
  "host": "WORKSTATION-04",
  "user": "jsmith",
  "timestamp": "2026-09-18T02:14:00Z",
  "indicators": ["psexec.exe", "admin$", "WORKSTATION-07"],
  "context": {
    "user_role": "developer",
    "is_admin": false,
    "recent_logins": 3,
    "peer_behavior": "unusual"
  }
}
```

## Output: TriageResult
```json
{
  "alert_id": "ALT-1234",
  "true_positive_prob": 0.87,
  "severity": "high",
  "severity_score": 3.4,
  "category": "lateral_movement",
  "action": "l2_escalate",
  "confidence": 0.81,
  "auto_actioned": false,
  "fsm_path": ["new", "triaging", "investigating", "escalated"],
  "audit": [...]
}
```

---

## File Structure
```
jev-soc/
├── BLUEPRINT.md
├── SUMMARY.md
├── pyproject.toml
└── jevsoc/
    ├── __init__.py
    ├── triage.py      fast Jev triage pass (true_pos, severity, category, action)
    ├── lifecycle.py   FSM lifecycle built on jev-fsm
    ├── pipeline.py    triage() → lifecycle() combined entry point
    ├── batch.py       process list of alerts, parallel where possible
    └── cli.py         alert / batch / simulate commands
```

---

## QA Test Cases (planned)
1. Obvious false positive (auth from known IP, business hours) → auto_close
2. Critical ransomware indicator → immediate_response, no human needed
3. Ambiguous lateral movement → l2_escalate, human review
4. Brute force → l1_investigate
5. Insider threat indicators (off-hours, large data download) → l3_page
6. Batch of 5 mixed alerts → correct routing split
7. Low-confidence alert → pauses at triaging, awaits human
8. Alert with no context → degrades gracefully
